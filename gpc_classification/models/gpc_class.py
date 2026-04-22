from odoo import api, fields, models

# Official GS1 GPC Segment codes (November 2025 publication, 45 segments).
# Exported so other modules can reuse: from odoo.addons.gpc_classification.models.gpc_class import GPC_SEGMENTS
GPC_SEGMENTS = [
    ('10', 'Pet Care/Food'),
    ('11', 'Industrial Fluid Pumps/Systems'),
    ('12', 'Tobacco/Cannabis'),
    ('13', 'Pest/Plant Control Products'),
    ('14', 'Lighting'),
    ('47', 'Cleaning/Hygiene Products'),
    ('50', 'Food/Beverage'),
    ('51', 'Healthcare'),
    ('53', 'Beauty/Personal Care/Hygiene'),
    ('58', 'Cross Segment'),
    ('60', 'Textual/Printed/Reference Materials'),
    ('61', 'Music'),
    ('62', 'Stationery/Office Machinery/Occasion Supplies'),
    ('63', 'Footwear'),
    ('64', 'Personal Accessories'),
    ('65', 'Computing'),
    ('66', 'Communications'),
    ('67', 'Clothing'),
    ('68', 'Audio Visual/Photography'),
    ('70', 'Arts/Crafts/Needlework'),
    ('71', 'Sports Equipment'),
    ('72', 'Home Appliances'),
    ('73', 'Kitchenware and Tableware'),
    ('74', 'Camping'),
    ('75', 'Household/Office Furniture/Furnishings'),
    ('77', 'Vehicle'),
    ('78', 'Electrical Supplies'),
    ('79', 'Plumbing/Heating/Ventilation/Air Conditioning'),
    ('80', 'Tools/Equipment'),
    ('81', 'Lawn/Garden Supplies'),
    ('83', 'Building Products'),
    ('84', 'Tool Storage/Workshop Aids'),
    ('85', 'Safety/Protection - DIY'),
    ('86', 'Toys/Games'),
    ('87', 'Fluids/Fuels/Gases'),
    ('88', 'Lubricants'),
    ('89', 'Live Animals'),
    ('91', 'Safety/Security/Surveillance'),
    ('92', 'Storage/Haulage Containers'),
    ('93', 'Horticulture Plants'),
    ('94', 'Crops'),
    ('95', 'Services/Vending Machines'),
    ('96', 'Monetary Assets'),
    ('98', 'Raw Materials (Non Food)'),
    ('99', 'Postmortem Products'),
]

# Dict for fast label lookup
GPC_SEGMENT_DICT = dict(GPC_SEGMENTS)


class GpcClass(models.Model):
    _name = 'gpc.class'
    _description = 'GS1 GPC Class'
    _order = 'segment_code, code'
    _rec_name = 'display_name'

    code = fields.Char(
        string='Class Code',
        size=4,
        required=True,
        index=True,
    )
    description = fields.Char(
        string='Description',
        required=True,
    )
    segment_code = fields.Selection(
        selection=GPC_SEGMENTS,
        string='Segment',
        required=True,
        index=True,
    )
    segment_label = fields.Char(
        string='Segment Name',
        compute='_compute_segment_label',
        store=True,
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )

    _sql_constraints = [
        (
            'segment_code_unique',
            'UNIQUE(segment_code, code)',
            'A GPC Class code must be unique within its Segment.',
        ),
    ]

    @api.depends('segment_code')
    def _compute_segment_label(self):
        for rec in self:
            rec.segment_label = GPC_SEGMENT_DICT.get(rec.segment_code, '')

    @api.depends('code', 'description', 'segment_code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'[{rec.segment_code}-{rec.code}] {rec.description}' if rec.code else rec.description
