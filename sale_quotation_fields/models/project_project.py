from odoo import api, fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    sale_order_count = fields.Integer(
        string='Sales Orders',
        compute='_compute_sale_order_count',
    )

    @api.depends('sale_order_count')
    def _compute_sale_order_count(self):
        data = self.env['sale.order'].read_group(
            [('project_id', 'in', self.ids)],
            ['project_id'],
            ['project_id'],
        )
        counts = {row['project_id'][0]: row['project_id_count'] for row in data}
        for project in self:
            project.sale_order_count = counts.get(project.id, 0)

    def action_view_sale_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Orders',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
