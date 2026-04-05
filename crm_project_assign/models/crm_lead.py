from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        tracking=True,
    )
    project_count = fields.Integer(
        compute='_compute_project_count',
    )

    def _compute_project_count(self):
        for lead in self:
            lead.project_count = 1 if lead.project_id else 0

    def action_view_project(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': self.project_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_assign_project(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assign Project',
            'res_model': 'crm.project.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'default_project_id': self.project_id.id,
            },
        }
