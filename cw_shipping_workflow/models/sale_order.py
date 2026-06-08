import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    cw_deposit_received = fields.Boolean(
        string='Deposit Received',
        tracking=True,
        help="Accounting flips this on once the customer deposit has been "
             "confirmed in the bank account. Triggers Aris (Shipping) to "
             "coordinate packing details with the supplier.",
    )
    cw_deposit_received_date = fields.Date(
        string='Deposit Received Date',
        tracking=True,
    )
    cw_deposit_confirmed_by = fields.Many2one(
        'res.users',
        string='Deposit Confirmed By',
        readonly=True,
        tracking=True,
    )

    def write(self, vals):
        prior_flag = {so.id: so.cw_deposit_received for so in self}
        result = super().write(vals)
        if 'cw_deposit_received' in vals:
            for so in self:
                if so.cw_deposit_received and not prior_flag.get(so.id):
                    so._cw_on_deposit_confirmed()
        return result

    def _cw_on_deposit_confirmed(self):
        self.ensure_one()
        if not self.cw_deposit_received_date:
            self.sudo().cw_deposit_received_date = fields.Date.context_today(self)
        if not self.cw_deposit_confirmed_by:
            self.sudo().cw_deposit_confirmed_by = self.env.user.id

        Shipment = self.env['cw.shipment'].sudo()
        shipment = Shipment.search([('sale_order_id', '=', self.id)], limit=1)
        if not shipment and self.opportunity_id:
            shipment = Shipment.search(
                [('opportunity_id', '=', self.opportunity_id.id)],
                order='id desc', limit=1,
            )
            if shipment and not shipment.sale_order_id:
                shipment.sale_order_id = self.id
        if not shipment:
            _logger.info(
                "cw_shipping_workflow: deposit confirmed on SO %s but no linked "
                "cw.shipment found (no opportunity link?)",
                self.name,
            )
            return

        responsible = shipment.responsible_user_id or self.env.user
        shipment.activity_schedule(
            act_type_xmlid='cw_shipping_workflow.mail_activity_type_coordinate_packing',
            summary=_(
                "Coordinate packing list / CBM / crate sizes with "
                "Merchandiser + Supplier"
            ),
            note=_(
                "Deposit confirmed on %(so)s by %(user)s on %(date)s. "
                "Drill into packing details with the merchandiser and supplier: "
                "packing list, container packing plan, CBM, size of crates/cartons, "
                "wooden pallets."
            ) % {
                'so': self.name,
                'user': (self.cw_deposit_confirmed_by or self.env.user).name,
                'date': self.cw_deposit_received_date,
            },
            user_id=responsible.id,
        )
        _logger.info(
            "cw_shipping_workflow: scheduled coordination activity on shipment %s "
            "after deposit confirmation on SO %s",
            shipment.id, self.name,
        )
