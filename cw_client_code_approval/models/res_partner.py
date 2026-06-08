from odoo import _, api, fields, models
from odoo.exceptions import UserError


CLIENT_CODE_APPROVER_GROUP = 'cw_client_code_approval.group_client_code_approver'
ASSIGN_CLIENT_CODE_ACTIVITY = 'cw_client_code_approval.mail_activity_type_assign_client_code'


class ResPartner(models.Model):
    _inherit = 'res.partner'

    can_assign_client_code = fields.Boolean(
        compute='_compute_can_assign_client_code',
        help='True if the current user is in the Client Code Approver group. '
             'Used by the form view to toggle the client_code field between '
             'read-only (everyone) and editable (Howard, Eva).',
    )

    @api.depends_context('uid')
    def _compute_can_assign_client_code(self):
        approver = self.env.user.has_group(CLIENT_CODE_APPROVER_GROUP)
        for rec in self:
            rec.can_assign_client_code = approver

    # ------------------------------------------------------------------
    # Field-level write restriction + auto-request on create/save
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        approver = self.env.user.has_group(CLIENT_CODE_APPROVER_GROUP)
        if not approver and not self.env.su:
            for vals in vals_list:
                if vals.get('client_code') and vals.get('contact_type') == 'client':
                    raise UserError(_(
                        "Only members of the 'Client Code Approver' group "
                        "(Howard, Eva) may assign the Client Code. Save the "
                        "client without a code — an approval request will be "
                        "sent to the approvers automatically."
                    ))
        partners = super().create(vals_list)
        for partner in partners:
            if partner.contact_type == 'client' and not partner.client_code:
                partner._request_client_code_assignment()
        return partners

    def write(self, vals):
        if 'client_code' in vals:
            approver = self.env.user.has_group(CLIENT_CODE_APPROVER_GROUP)
            if not approver and not self.env.su:
                new_code = (vals.get('client_code') or '').strip().upper() or False
                changing = self.filtered(
                    lambda p: (p.client_code or False) != new_code
                )
                if changing:
                    raise UserError(_(
                        "Only members of the 'Client Code Approver' group "
                        "(Howard, Eva) may write the Client Code. Howard "
                        "and Eva have an open activity on this contact — "
                        "ask one of them to assign the code."
                    ))
        res = super().write(vals)
        if vals.get('client_code'):
            for partner in self:
                if partner.client_code:
                    partner._clear_client_code_activities()
        elif 'contact_type' in vals:
            for partner in self:
                if partner.contact_type == 'client' and not partner.client_code:
                    partner._request_client_code_assignment()
        return res

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_client_code_approvers(self):
        group = self.env.ref(CLIENT_CODE_APPROVER_GROUP, raise_if_not_found=False)
        if not group:
            return self.env['res.users']
        return group.sudo().users.filtered(lambda u: u.active and not u.share)

    def _request_client_code_assignment(self):
        """Idempotently raise a request for the GM to assign a 2-letter
        Client Code on this partner. Schedules a mail.activity assigned
        to the lowest-id approver (deterministic) and posts an @mention
        message tagging every approver so all of them are notified.

        Idempotent on activities: if an open Assign Client Code activity
        already exists on this partner, no new activity is scheduled, but
        a chatter message is still posted (so re-triggers from CRM stage
        transitions surface fresh notifications)."""
        for partner in self:
            if partner.contact_type != 'client' or partner.client_code:
                continue
            activity_type = self.env.ref(
                ASSIGN_CLIENT_CODE_ACTIVITY, raise_if_not_found=False,
            )
            approvers = partner._get_client_code_approvers()
            if not activity_type or not approvers:
                continue

            existing = self.env['mail.activity'].sudo().search([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', partner.id),
                ('activity_type_id', '=', activity_type.id),
            ], limit=1)

            if not existing:
                assignee = approvers.sorted('id')[:1]
                model_id = self.env['ir.model']._get('res.partner').id
                self.env['mail.activity'].sudo().create({
                    'res_model_id': model_id,
                    'res_id': partner.id,
                    'activity_type_id': activity_type.id,
                    'summary': _(
                        'Assign 2-letter Client Code for %s',
                        partner.display_name,
                    ),
                    'user_id': assignee.id,
                })

            approver_partner_ids = approvers.partner_id.ids
            if approver_partner_ids:
                partner.sudo().message_post(
                    body=_(
                        "Client created without a 2-letter Client Code. "
                        "Please assign one — the code is required to "
                        "generate the sourcing Reference ID and to advance "
                        "this client's opportunities past Proforma Invoice."
                    ),
                    partner_ids=approver_partner_ids,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )

    def _clear_client_code_activities(self):
        """When a code is assigned, mark all open Assign Client Code
        activities on this partner as Done. Uses action_feedback so the
        completion is recorded in chatter as audit trail."""
        for partner in self:
            activity_type = self.env.ref(
                ASSIGN_CLIENT_CODE_ACTIVITY, raise_if_not_found=False,
            )
            if not activity_type:
                continue
            activities = self.env['mail.activity'].sudo().search([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', partner.id),
                ('activity_type_id', '=', activity_type.id),
            ])
            if activities:
                activities.action_feedback(
                    feedback=_('Code assigned: %s', partner.client_code),
                )
