from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


SHIPMENT_STATUS = [
    ('draft', 'Draft'),
    ('cargo_ready', 'Cargo Ready'),
    ('booked', 'Booked'),
    ('shipped', 'Shipped'),
    ('arrived', 'Arrived'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
]

INCOTERMS = [
    ('FOB', 'FOB - Free On Board'),
    ('CIF', 'CIF - Cost, Insurance, Freight'),
    ('EXW', 'EXW - Ex Works'),
    ('FCA', 'FCA - Free Carrier'),
    ('CFR', 'CFR - Cost and Freight'),
    ('DAP', 'DAP - Delivered At Place'),
    ('DDP', 'DDP - Delivered Duty Paid'),
]


class CwShipment(models.Model):
    _name = 'cw.shipment'
    _description = 'Courtwell Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'earliest_etd desc, pi_no desc'
    _rec_names_search = ['pi_no', 'bl_numbers', 'cntr_numbers']

    pi_no = fields.Char(
        string='PI No.', required=True, copy=False, tracking=True,
        help='Proforma Invoice number. Primary identifier from the shipment log.',
    )
    fty_pi = fields.Char(string='Factory PI', tracking=True)

    customer_id = fields.Many2one(
        'res.partner', string='Customer', tracking=True,
        domain="[('customer_rank', '>', 0)]",
        help='Customer for this shipment. Optional — some legacy PIs were logged without a confirmed customer.',
    )
    supplier_id = fields.Many2one(
        'res.partner', string='Supplier', tracking=True,
        domain="[('supplier_rank', '>', 0)]",
        help='Supplier for this shipment. Optional — some legacy PIs were logged without a confirmed supplier.',
    )
    forwarder_id = fields.Many2one(
        'res.partner', string='Forwarder', tracking=True,
        help='Freight forwarder. Tagged with the Service Provider category.',
    )

    term = fields.Selection(INCOTERMS, string='Incoterm', default='FOB', tracking=True)

    freight_cost = fields.Monetary(string='Freight Cost (Forwarder)', currency_field='currency_id', tracking=True)
    invoice_amount = fields.Monetary(string='Invoice Amount', currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id,
    )

    invoice_no = fields.Char(string='Invoice No.', tracking=True)

    # Dates
    cargo_ready_date = fields.Date(string='Cargo Ready Date', tracking=True)
    inspection_date = fields.Date(string="Rec'd / Inspection Date", tracking=True)
    doc_to_customer_date = fields.Date(string='Doc. to Customer', tracking=True)
    telex_released_date = fields.Date(string='Telex Released')
    sent_doc_date = fields.Date(string='Sent Doc')

    courier = fields.Char(string='Courier')

    # Cargo summary (across all containers)
    description = fields.Char(string='Description')
    ctn_pkg = fields.Integer(string='CTN / PKG', help='Total cartons or packages.')
    gross_weight = fields.Float(string='Gross Weight (kg)', digits=(12, 2))
    total_cbm = fields.Float(string='Total CBM', digits=(12, 3))

    # Logistics
    port_of_loading_id = fields.Many2one('cw.port', string='Port of Loading', tracking=True)
    destination_port_id = fields.Many2one('cw.port', string='Destination Port', tracking=True)

    container_ids = fields.One2many(
        'cw.shipment.container', 'shipment_id', string='Containers', copy=True,
    )
    container_count = fields.Integer(compute='_compute_container_aggregates', store=True)
    cntr_numbers = fields.Char(compute='_compute_container_aggregates', store=True, string='CNTR Nos.')
    bl_numbers = fields.Char(compute='_compute_container_aggregates', store=True, string='BL Nos.')
    earliest_etd = fields.Date(compute='_compute_container_aggregates', store=True, string='ETD')
    latest_eta = fields.Date(compute='_compute_container_aggregates', store=True, string='ETA')

    status = fields.Selection(SHIPMENT_STATUS, string='Status', default='draft', required=True, tracking=True)

    remarks = fields.Text(string='Remarks')
    import_raw = fields.Text(
        string='Import Raw Data',
        help='Original raw values from the source spreadsheet, kept for traceability after normalization.',
    )

    _sql_constraints = [
        ('pi_no_uniq', 'UNIQUE(pi_no)', 'PI No. must be unique.'),
    ]

    @api.depends(
        'container_ids', 'container_ids.cntr_number', 'container_ids.bl_number',
        'container_ids.etd', 'container_ids.eta',
    )
    def _compute_container_aggregates(self):
        for ship in self:
            containers = ship.container_ids
            ship.container_count = len(containers)
            cntrs = [c.cntr_number for c in containers if c.cntr_number]
            ship.cntr_numbers = ', '.join(cntrs) if cntrs else False
            bls = sorted({c.bl_number for c in containers if c.bl_number})
            ship.bl_numbers = ', '.join(bls) if bls else False
            etds = [c.etd for c in containers if c.etd]
            etas = [c.eta for c in containers if c.eta]
            ship.earliest_etd = min(etds) if etds else False
            ship.latest_eta = max(etas) if etas else False

    @api.constrains('forwarder_id')
    def _check_forwarder_is_service_provider(self):
        cat = self.env.ref('cw_shipment.partner_cat_service_provider', raise_if_not_found=False)
        if not cat:
            return
        for ship in self:
            if ship.forwarder_id and cat not in ship.forwarder_id.category_id:
                raise ValidationError(_(
                    "Partner %s is not tagged as Service Provider — cannot be used as a Forwarder.",
                    ship.forwarder_id.display_name,
                ))

    @api.ondelete(at_uninstall=False)
    def _unlink_only_draft_or_cancelled(self):
        if any(s.status not in ('draft', 'cancelled') for s in self):
            raise ValidationError(_(
                "Only draft or cancelled shipments can be deleted. Cancel the shipment first."
            ))
