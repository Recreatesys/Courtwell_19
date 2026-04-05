from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    line_image = fields.Image(
        string='Image',
        max_width=1920,
        max_height=1920,
        attachment=True,
    )
