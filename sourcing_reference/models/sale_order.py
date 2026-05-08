from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sourcing_reference = fields.Char(
        string='Sourcing Ref',
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        help='Inherited from the originating Opportunity. '
             'Format: QP-{ClientCode}-{SegmentCode}-{YY}-{NNN}.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.sourcing_reference or not order.opportunity_id:
                continue
            base = (order.opportunity_id.sourcing_reference or '').strip()
            if base.startswith('OP-'):
                order.sourcing_reference = 'QP-' + base[3:]
        return orders

    def write(self, vals):
        result = super().write(vals)
        for order in self:
            if order.sourcing_reference or not order.opportunity_id:
                continue
            base = (order.opportunity_id.sourcing_reference or '').strip()
            if base.startswith('OP-'):
                order.sourcing_reference = 'QP-' + base[3:]
        return result

    def _get_proforma_reference(self):
        """Return PI- prefix variant for proforma print rendering.

        Per spec §12.1.3: PI- is applied at document generation only,
        not as a separate stored field.
        """
        self.ensure_one()
        ref = (self.sourcing_reference or '').strip()
        if ref.startswith('QP-'):
            return 'PI-' + ref[3:]
        return ref
