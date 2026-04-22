from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    report_header_image = fields.Image(
        string='Report Header Image',
        max_width=1920,
        max_height=400,
        attachment=True,
    )
