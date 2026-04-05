from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    attention_to = fields.Many2one(
        'res.partner',
        string='Attention To',
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
    )

    def action_confirm(self):
        result = super().action_confirm()
        for order in self:
            if not order.project_id:
                continue
            for line in order.order_line:
                if line.display_type or not line.product_id:
                    continue
                # Avoid duplicate tasks if order is re-confirmed
                already_exists = self.env['project.task'].search([
                    ('sale_line_id', '=', line.id),
                    ('project_id', '=', order.project_id.id),
                ], limit=1)
                if already_exists:
                    continue
                self.env['project.task'].create({
                    'name': line.product_id.name,
                    'project_id': order.project_id.id,
                    'sale_line_id': line.id,
                    'description': line.name or '',
                })
        return result
