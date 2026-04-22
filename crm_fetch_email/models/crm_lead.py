from odoo import models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def action_fetch_emails(self):
        """Trigger all active incoming mail servers to fetch emails immediately."""
        servers = self.env['fetchmail.server'].search([('state', '=', 'done')])
        if not servers:
            raise UserError('No active incoming mail servers found.')
        servers.fetch_mail()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Emails Fetched',
                'message': f'Fetched emails from {len(servers)} server(s). New leads will appear shortly.',
                'type': 'success',
                'sticky': False,
            },
        }
