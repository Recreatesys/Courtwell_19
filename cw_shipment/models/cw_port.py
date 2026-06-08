from odoo import api, fields, models


class CwPort(models.Model):
    _name = 'cw.port'
    _description = 'Shipping Port'
    _order = 'country_id, name'
    _rec_names_search = ['name', 'unlocode']

    name = fields.Char(string='Port Name', required=True, translate=False)
    unlocode = fields.Char(string='UN/LOCODE', size=5, help='5-letter UN/LOCODE, e.g. CNNGB for Ningbo')
    country_id = fields.Many2one('res.country', string='Country')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Port name must be unique.'),
    ]

    @api.depends('name', 'country_id')
    def _compute_display_name(self):
        for port in self:
            if port.country_id:
                port.display_name = f"{port.name} ({port.country_id.code})"
            else:
                port.display_name = port.name or ''
