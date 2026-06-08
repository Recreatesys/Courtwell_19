import re

from odoo import _, api, models
from odoo.exceptions import UserError


# Stages where client_code becomes mandatory. Entering any of these
# stages without a code is blocked. Matches the sourcing_reference
# pipeline definition (data/crm_stage_data.xml).
POST_PI_STAGE_REFS = (
    'sourcing_reference.crm_stage_qc',
    'sourcing_reference.crm_stage_enroute',
    'sourcing_reference.crm_stage_upsell_reorder',
)

# Stages where the sourcing reference should be auto-generated if the
# client_code is now available. Excludes Incoming Inquiry, Lost, and
# On Hold. Retries every stage transition until the ref is created.
POST_INQUIRY_STAGE_REFS = (
    'sourcing_reference.crm_stage_quotation',
    'sourcing_reference.crm_stage_proforma_invoice',
    'sourcing_reference.crm_stage_qc',
    'sourcing_reference.crm_stage_enroute',
    'sourcing_reference.crm_stage_upsell_reorder',
)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # ------------------------------------------------------------------
    # Relax the Incoming Inquiry exit gate: client_code is no longer
    # required there. GS1 Segment requirement is preserved.
    # ------------------------------------------------------------------
    def _validate_inquiry_exit(self):
        self.ensure_one()
        if not self.gpc_segment_id or not self.gpc_segment_id.code:
            raise UserError(_(
                "GS1 Segment must be selected before this Opportunity "
                "can progress past Incoming Inquiry."
            ))

    # ------------------------------------------------------------------
    # New gate: block entry to QC / Enroute / Upsell when client_code
    # is still missing. Also re-fires the assignment request on the
    # partner so approvers get a fresh notification.
    # ------------------------------------------------------------------
    def _validate_proforma_exit(self):
        self.ensure_one()
        partner = self.partner_id
        cc = (partner.client_code or '').strip() if partner else ''
        if not cc or not re.fullmatch(r'[A-Z]{2}', cc):
            if partner:
                partner._request_client_code_assignment()
            raise UserError(_(
                "Client Code is missing on '%(client)s'. The 2-letter "
                "code must be assigned by Howard or Eva before this "
                "Opportunity can move past Proforma Invoice. An "
                "assignment request has been (re-)sent to the approvers "
                "— they will see it in their activity inbox.",
                client=partner.display_name if partner else _('this client'),
            ))

    def _is_post_pi_stage(self, stage):
        if not stage:
            return False
        for ref in POST_PI_STAGE_REFS:
            target = self.env.ref(ref, raise_if_not_found=False)
            if target and stage.id == target.id:
                return True
        return (stage.name or '').strip().lower() in (
            'qc', 'enroute', 'upsell/reorder',
        )

    def _is_post_inquiry_stage(self, stage):
        if not stage:
            return False
        for ref in POST_INQUIRY_STAGE_REFS:
            target = self.env.ref(ref, raise_if_not_found=False)
            if target and stage.id == target.id:
                return True
        return (stage.name or '').strip().lower() in (
            'quotation', 'proforma invoice', 'qc', 'enroute', 'upsell/reorder',
        )

    # ------------------------------------------------------------------
    # write() hooks:
    #   1. Pre-write: block entry to a post-PI stage when client_code
    #      is missing (calls _validate_proforma_exit which also triggers
    #      a fresh activity request to the approvers).
    #   2. Post-write: try to generate sourcing_reference on entry to
    #      any post-Inquiry stage — retries each time the lead moves,
    #      so a lead stuck in Quotation without a code will auto-get
    #      its ref the moment the GM assigns the code and the
    #      merchandiser moves the lead again.
    # ------------------------------------------------------------------
    def write(self, vals):
        if 'stage_id' in vals and not self.env.context.get('skip_sourcing_validation'):
            new_stage = (
                self.env['crm.stage'].browse(vals['stage_id'])
                if vals['stage_id'] else False
            )
            if new_stage and self._is_post_pi_stage(new_stage):
                for lead in self:
                    if lead.stage_id.id == new_stage.id:
                        continue
                    lead._validate_proforma_exit()

        result = super().write(vals)

        if 'stage_id' in vals and not self.env.context.get('skip_sourcing_validation'):
            for lead in self:
                if lead.sourcing_reference:
                    continue
                if not lead.partner_id or not lead.gpc_segment_id:
                    continue
                if not (lead.partner_id.client_code or '').strip():
                    continue
                if lead._is_post_inquiry_stage(lead.stage_id):
                    lead._generate_sourcing_reference()

        return result

    # ------------------------------------------------------------------
    # Silent-skip when client_code missing instead of raising. This
    # lets the lead sit in Quotation / Proforma Invoice without a ref
    # until the code is assigned; the post-write hook above retries
    # generation on every later stage move.
    # ------------------------------------------------------------------
    def _generate_sourcing_reference(self):
        self.ensure_one()
        if self.sourcing_reference:
            return
        partner = self.partner_id
        cc = (partner.client_code or '').strip() if partner else ''
        if not cc or not re.fullmatch(r'[A-Z]{2}', cc):
            if partner:
                partner._request_client_code_assignment()
            return
        if not self.gpc_segment_id or not self.gpc_segment_id.code:
            return
        return super()._generate_sourcing_reference()
