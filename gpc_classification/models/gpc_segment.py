from odoo import fields, models
from .gpc_class import GPC_SEGMENTS


class GpcSegment(models.Model):
    _name = 'gpc.segment'
    _description = 'GS1 GPC Segment'
    _order = 'code'
    _rec_name = 'name'

    code = fields.Char(
        string='Segment Code',
        size=2,
        required=True,
        index=True,
    )
    name = fields.Char(
        string='Segment Name',
        required=True,
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'GPC Segment code must be unique.'),
    ]
