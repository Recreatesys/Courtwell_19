from odoo import fields, models


class CwServiceProviderType(models.Model):
    _name = 'cw.service.provider.type'
    _description = 'Service Provider Type'
    _order = 'sequence, name'
    _rec_names_search = ['name', 'code']

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        help='Stable identifier for ETL / reporting. Optional but recommended '
             'on seeded values so external systems can reference a type without '
             'being affected by display-name changes.',
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Char(help='Short hint shown in the dropdown / tooltip.')

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)',
         'Service Provider Type code must be unique.'),
        ('name_uniq', 'UNIQUE(name)',
         'Service Provider Type name must be unique.'),
    ]
