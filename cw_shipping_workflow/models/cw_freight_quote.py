from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


FREIGHT_MODE = [
    ('sea', 'Sea'),
    ('air', 'Air'),
    ('land', 'Land'),
    ('courier', 'Courier'),
]

CONTAINER_TYPE = [
    ('20gp', "20' GP"),
    ('40gp', "40' GP"),
    ('40hq', "40' HQ"),
    ('45hq', "45' HQ"),
    ('lcl', 'LCL'),
    ('air', 'Air (per kg)'),
    ('other', 'Other'),
]


class CwShipmentFreightQuote(models.Model):
    _name = 'cw.shipment.freight.quote'
    _description = 'Shipment Freight Quote'
    _order = 'shipment_id, sequence, id'

    shipment_id = fields.Many2one(
        'cw.shipment', string='Shipment',
        required=True, ondelete='cascade', index=True,
    )
    sequence = fields.Integer(default=10)

    forwarder_id = fields.Many2one(
        'res.partner', string='Forwarder', required=True,
        help='Freight forwarder providing this quote. Must be tagged Service Provider.',
    )
    mode = fields.Selection(FREIGHT_MODE, string='Mode', default='sea', required=True)
    container_type = fields.Selection(CONTAINER_TYPE, string='Container / Unit')

    port_of_loading_id = fields.Many2one('cw.port', string='Port of Loading')
    destination_port_id = fields.Many2one('cw.port', string='Destination Port')

    rate = fields.Monetary(string='Rate', currency_field='currency_id', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id,
    )

    quoted_on = fields.Date(string='Quoted On', default=fields.Date.context_today)
    valid_until = fields.Date(string='Valid Until')
    transit_days = fields.Integer(string='Transit (days)')

    notes = fields.Text(string='Notes')

    is_selected = fields.Boolean(
        string='Selected',
        help='Mark the winning quote. Auto-fills Forwarder, Freight Cost and Currency on the shipment.',
    )

    @api.constrains('forwarder_id')
    def _check_forwarder_is_service_provider(self):
        cat = self.env.ref('cw_shipment.partner_cat_service_provider', raise_if_not_found=False)
        if not cat:
            return
        for q in self:
            if q.forwarder_id and cat not in q.forwarder_id.category_id:
                raise ValidationError(_(
                    "Partner %s is not tagged as Service Provider — cannot be used as a Forwarder on a freight quote.",
                    q.forwarder_id.display_name,
                ))

    @api.constrains('valid_until', 'quoted_on')
    def _check_validity_window(self):
        for q in self:
            if q.valid_until and q.quoted_on and q.valid_until < q.quoted_on:
                raise ValidationError(_("'Valid Until' cannot be earlier than 'Quoted On'."))

    @api.constrains('rate')
    def _check_rate_positive(self):
        for q in self:
            if q.rate <= 0:
                raise ValidationError(_("Quote rate must be greater than zero."))

    @api.onchange('shipment_id')
    def _onchange_shipment_defaults(self):
        for q in self:
            if q.shipment_id and not q.port_of_loading_id:
                q.port_of_loading_id = q.shipment_id.port_of_loading_id
            if q.shipment_id and not q.destination_port_id:
                q.destination_port_id = q.shipment_id.destination_port_id
            if q.shipment_id and not q.currency_id:
                q.currency_id = q.shipment_id.currency_id

    def _sync_to_shipment(self):
        """For each newly-selected quote, unselect siblings and push values onto the shipment."""
        for quote in self.filtered('is_selected'):
            siblings = quote.shipment_id.freight_quote_ids - quote
            to_clear = siblings.filtered('is_selected')
            if to_clear:
                to_clear.with_context(skip_quote_sync=True).write({'is_selected': False})
            ship_vals = {
                'forwarder_id': quote.forwarder_id.id,
                'freight_cost': quote.rate,
                'currency_id': quote.currency_id.id,
            }
            quote.shipment_id.write(ship_vals)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('skip_quote_sync'):
            records._sync_to_shipment()
        return records

    def write(self, vals):
        res = super().write(vals)
        sync_triggers = {'is_selected', 'rate', 'forwarder_id', 'currency_id'}
        if not self.env.context.get('skip_quote_sync') and sync_triggers & vals.keys():
            self._sync_to_shipment()
        return res
