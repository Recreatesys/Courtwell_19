from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sourcing_orders_count = fields.Integer(
        string='Orders',
        compute='_compute_sourcing_orders_count',
    )

    @api.depends('contact_type')
    def _compute_sourcing_orders_count(self):
        Lead = self.env['crm.lead']
        Stage = self.env['crm.stage']
        lost_stage = self.env.ref('sourcing_reference.crm_stage_lost', raise_if_not_found=False)
        lost_ids = []
        if lost_stage:
            lost_ids.append(lost_stage.id)
        else:
            lost_ids = Stage.search([('name', '=ilike', 'lost')]).ids
        for partner in self:
            if not partner.id:
                partner.sourcing_orders_count = 0
                continue
            domain = [
                ('partner_id', '=', partner.id),
                ('type', '=', 'opportunity'),
                ('active', '=', True),
            ]
            if lost_ids:
                domain.append(('stage_id', 'not in', lost_ids))
            partner.sourcing_orders_count = Lead.search_count(domain)

    def action_view_sourcing_orders(self):
        self.ensure_one()
        lost_stage = self.env.ref('sourcing_reference.crm_stage_lost', raise_if_not_found=False)
        domain = [
            ('partner_id', '=', self.id),
            ('type', '=', 'opportunity'),
            ('active', '=', True),
        ]
        if lost_stage:
            domain.append(('stage_id', '!=', lost_stage.id))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orders for %s') % self.display_name,
            'res_model': 'crm.lead',
            'view_mode': 'list,kanban,form',
            'domain': domain,
            'context': {'default_partner_id': self.id, 'default_type': 'opportunity'},
        }
