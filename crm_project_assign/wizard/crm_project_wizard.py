from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CrmProjectWizard(models.TransientModel):
    _name = 'crm.project.wizard'
    _description = 'Assign or Create Project for CRM Opportunity'

    lead_id = fields.Many2one('crm.lead', required=True, readonly=True)
    action_type = fields.Selection(
        [('assign', 'Assign Existing Project'), ('create', 'Create New Project')],
        string='Action',
        default='assign',
        required=True,
    )

    # --- Assign existing ---
    project_id = fields.Many2one('project.project', string='Project')

    # --- Create new ---
    project_name = fields.Char(string='Project Name')
    template_id = fields.Many2one(
        'project.project',
        string='Project Template',
        domain=[('is_template', '=', True)],
    )
    follower_partner_ids = fields.Many2many(
        'res.partner',
        string='Followers',
        help='Users added as followers to the new project.',
    )

    @api.onchange('action_type')
    def _onchange_action_type(self):
        if self.action_type == 'create':
            self.project_id = False
        else:
            self.project_name = False
            self.template_id = False
            self.follower_partner_ids = False

    def action_confirm(self):
        self.ensure_one()
        if self.action_type == 'assign':
            if not self.project_id:
                raise UserError(_('Please select a project to assign.'))
            project = self.project_id
        else:
            if not self.project_name:
                raise UserError(_('Please enter a name for the new project.'))
            if self.template_id:
                project = self.template_id.with_context(copy_from_template=True).copy({
                    'name': self.project_name,
                    'is_template': False,
                })
            else:
                project = self.env['project.project'].create({
                    'name': self.project_name,
                })
            if self.follower_partner_ids:
                project.message_subscribe(partner_ids=self.follower_partner_ids.ids)

        self.lead_id.project_id = project
        return {'type': 'ir.actions.act_window_close'}
