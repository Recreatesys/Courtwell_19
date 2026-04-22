from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    line_image = fields.Image(
        string='Image',
        max_width=1920,
        max_height=1920,
        attachment=True,
    )

    @api.onchange('product_id')
    def _onchange_product_id_line_image(self):
        for line in self:
            if line.product_id:
                line.line_image = line.product_id.image_1920

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('product_id') and not vals.get('line_image'):
                product = self.env['product.product'].browse(vals['product_id'])
                vals['line_image'] = product.image_1920
        return super().create(vals_list)
