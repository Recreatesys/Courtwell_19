from odoo import api, fields, models


CONTAINER_SIZE = [
    ('20', "1 x 20'"),
    ('20_soc', "1 x 20' SOC"),
    ('40', "1 x 40'"),
    ('40hq', "1 x 40'HQ"),
    ('partial_40hq', "Part of 40'HQ"),
    ('lcl', 'LCL'),
    ('lcl_cy', 'LCL / CY'),
    ('air', 'Air Freight'),
    ('other', 'Other'),
]


class CwShipmentContainer(models.Model):
    _name = 'cw.shipment.container'
    _description = 'Shipment Container Line'
    _order = 'shipment_id, sequence, id'
    _rec_names_search = ['cntr_number', 'bl_number']

    shipment_id = fields.Many2one(
        'cw.shipment', string='Shipment', required=True, ondelete='cascade', index=True,
    )
    sequence = fields.Integer(default=10)

    container_size = fields.Selection(CONTAINER_SIZE, string='Container Size', required=True, default='40hq')
    container_size_raw = fields.Char(string='Container Size (raw)', help='Original size string from the source data.')
    cntr_number = fields.Char(string='Container No.')
    bl_number = fields.Char(string='BL No.')

    carrier_id = fields.Many2one(
        'res.partner', string='Carrier',
        help='Shipping line. Tagged with the Service Provider category.',
    )
    vessel_name = fields.Char(string='Vessel Name')

    # Vessel schedule
    open_date = fields.Date(string='Open')
    closing_date = fields.Date(string='Closing')
    si_cutoff = fields.Date(string='SI Cut-off')
    vgm_cutoff = fields.Date(string='VGM Cut-off')
    etd = fields.Date(string='ETD')
    eta_original = fields.Date(string='ETA (Original)')
    eta = fields.Date(string='ETA')

    # Per-line passthrough fields (denormalized from header for convenience)
    customer_id = fields.Many2one(related='shipment_id.customer_id', string='Customer', store=False)
    supplier_id = fields.Many2one(related='shipment_id.supplier_id', string='Supplier', store=False)

    @api.depends('cntr_number', 'container_size', 'shipment_id.pi_no')
    def _compute_display_name(self):
        for line in self:
            label = dict(CONTAINER_SIZE).get(line.container_size, line.container_size or '')
            parts = [p for p in (line.shipment_id.pi_no, label, line.cntr_number) if p]
            line.display_name = ' / '.join(parts)
