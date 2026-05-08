from odoo import models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def _find_internal_users_from_address_mail(self, emails, project_id=False):
        # Upstream addons/project/models/project_task.py:1685 calls
        # list.remove(project_alias_address) unconditionally, which raises
        # ValueError when the alias is not in unmatched_partner_emails
        # (the common case for mail routed via direct alias match rather
        # than via the To/Cc header). Delegate to super() with
        # project_id=False to skip the buggy block, then redo the
        # alias-removal step defensively.
        internal_user_ids, partner_emails_without_internal_users, unmatched_partner_emails = (
            super()._find_internal_users_from_address_mail(emails, project_id=False)
        )
        if project_id:
            project = self.env['project.project'].browse(project_id)
            project_alias_address = project.alias_name + '@' + project.alias_domain_id.name
            if project_alias_address in unmatched_partner_emails:
                unmatched_partner_emails.remove(project_alias_address)
        return internal_user_ids, partner_emails_without_internal_users, unmatched_partner_emails
