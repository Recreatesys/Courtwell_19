import re
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    sourcing_reference = fields.Char(
        string='Sourcing Ref',
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        help='Auto-generated immutable reference ID. Format: '
             'OP-{ClientCode}-{SegmentCode}-{YY}-{NNN}. '
             'Generated on first entry to the Quotation stage. '
             'When a Project Reference exists on this opportunity, '
             'OP- shares its NNN so the two IDs match.',
    )

    project_reference = fields.Char(
        string='Project Ref',
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        help='Auto-generated immutable project ID. Format: '
             'PR-{ClientCode}-{SegmentCode}-{YY}-{NNN}. '
             'Generated as soon as Client Code and GS1 Segment are '
             'both set on an opportunity — does not wait for Quotation, '
             'Sale Order, or Project creation. Becomes the '
             'project.project.sourcing_reference when a project is '
             'later linked. Shares the (Client, Segment) sequence '
             'with OP-/QP- so all references for one opportunity '
             'have the same NNN.',
    )

    gpc_segment_id = fields.Many2one(
        'gpc.segment',
        string='GS1 Segment',
        index=True,
        tracking=True,
        help='Primary GS1 GPC Segment for this opportunity. '
             'Required before exiting Incoming Inquiry.',
    )

    gpc_class_id = fields.Many2one(
        'gpc.class',
        string='GS1 Class',
        domain="[('segment_code', '=', gpc_segment_code)]",
        help='Optional sub-classification within the selected GS1 Segment.',
    )

    gpc_segment_code = fields.Char(
        related='gpc_segment_id.code',
        store=True,
        string='GS1 Segment Code',
    )

    purchase_order_ids = fields.One2many(
        'purchase.order',
        'opportunity_id',
        string='RFQs / POs',
    )
    purchase_order_count = fields.Integer(
        compute='_compute_purchase_order_count',
        string='RFQ Count',
    )

    @api.depends('purchase_order_ids')
    def _compute_purchase_order_count(self):
        for lead in self:
            lead.purchase_order_count = len(lead.purchase_order_ids)

    @api.onchange('gpc_segment_id')
    def _onchange_gpc_segment_clear_class(self):
        for lead in self:
            if lead.gpc_class_id and lead.gpc_class_id.segment_code != lead.gpc_segment_id.code:
                lead.gpc_class_id = False

    def _is_incoming_inquiry_stage(self, stage):
        if not stage:
            return False
        try:
            target = self.env.ref('sourcing_reference.crm_stage_incoming_inquiry', raise_if_not_found=False)
        except Exception:
            target = None
        if target and stage.id == target.id:
            return True
        return (stage.name or '').strip().lower() == 'incoming inquiry'

    def _is_quotation_stage(self, stage):
        if not stage:
            return False
        target = self.env.ref('sourcing_reference.crm_stage_quotation', raise_if_not_found=False)
        if target and stage.id == target.id:
            return True
        return (stage.name or '').strip().lower() == 'quotation'

    def _is_lost_stage(self, stage):
        if not stage:
            return False
        target = self.env.ref('sourcing_reference.crm_stage_lost', raise_if_not_found=False)
        if target and stage.id == target.id:
            return True
        return (stage.name or '').strip().lower() == 'lost'

    def _validate_inquiry_exit(self):
        """Block exit from Incoming Inquiry if Client Code or GS1 Segment missing."""
        self.ensure_one()
        partner = self.partner_id
        cc = (partner.client_code or '').strip() if partner else ''
        if not cc or not re.fullmatch(r'[A-Z]{2}', cc):
            raise UserError(_(
                "Client Code missing on this client record. "
                "Contact the General Manager to assign a code before proceeding."
            ))
        if not self.gpc_segment_id or not self.gpc_segment_id.code:
            raise UserError(_(
                "GS1 Segment must be selected before this Opportunity "
                "can progress past Incoming Inquiry."
            ))

    def _can_generate_project_reference(self):
        """True iff this lead has both prerequisites for PR- generation.

        Used as a guard so that automatic triggers (create/write) can
        silently skip incomplete records instead of raising. The user-
        facing validation path is `_validate_inquiry_exit`.
        """
        self.ensure_one()
        if not self.partner_id:
            return False
        cc = (self.partner_id.client_code or '').strip()
        if not cc or not re.fullmatch(r'[A-Z]{2}', cc):
            return False
        if not self.gpc_segment_id or not self.gpc_segment_id.code:
            return False
        return True

    def _generate_project_reference(self):
        """Generate PR-{cc}-{seg}-{YY}-{NNN} as soon as both client_code
        and gpc_segment are set on an opportunity.

        Shares the sourcing.client.sequence counter with OP-/QP- so all
        references for one opportunity have the same NNN. If a fresh PR-
        is generated before OP-, the OP-generator later reads from this
        PR- instead of incrementing the sequence again.

        Idempotent. Concurrency-safe via SELECT ... FOR UPDATE.
        """
        self.ensure_one()
        if self.project_reference:
            return
        if self.type != 'opportunity':
            return
        if not self._can_generate_project_reference():
            return

        cc = self.partner_id.client_code.strip().upper()
        seg = self.gpc_segment_id.code

        # Flush any pending ORM writes so the raw SELECT FOR UPDATE reads
        # the latest counter value.
        self.env.flush_all()

        Seq = self.env['sourcing.client.sequence'].sudo()
        seq = Seq.search([
            ('partner_id', '=', self.partner_id.id),
            ('gpc_segment', '=', seg),
        ], limit=1)

        if seq:
            self.env.cr.execute(
                "SELECT count FROM sourcing_client_sequence WHERE id = %s FOR UPDATE",
                (seq.id,),
            )
            row = self.env.cr.fetchone()
            new_count = (row[0] if row else 0) + 1
            seq.write({'count': new_count})
        else:
            seq = Seq.create({
                'partner_id': self.partner_id.id,
                'gpc_segment': seg,
                'count': 1,
            })
            new_count = 1

        yy = fields.Date.context_today(self).strftime('%y')
        ref = f"PR-{cc}-{seg}-{yy}-{new_count:03d}"
        self.project_reference = ref
        self.message_post(body=_("Project Reference generated: %s") % ref)
        _logger.info("crm.lead %s: generated project_reference %s", self.id, ref)

    def _generate_sourcing_reference(self):
        """Generate OP-{cc}-{seg}-{YY}-{NNN} on entry to Quotation.

        If a project_reference (PR-...) already exists on this lead — the
        normal case for new opportunities under v19.0.1.3.0+ — OP- inherits
        the same NNN by simple prefix-swap. No sequence increment.

        Otherwise (legacy opps with no PR-, or opps where PR- generation
        was skipped due to missing fields), fall back to the original
        behaviour: increment the (Client, Segment) sequence to get a
        fresh NNN.

        Idempotent. Concurrency-safe.
        """
        self.ensure_one()
        if self.sourcing_reference:
            return
        self._validate_inquiry_exit()

        # Path A — derive OP- from existing PR-, preserving the NNN.
        if self.project_reference and self.project_reference.startswith('PR-'):
            ref = 'OP-' + self.project_reference[3:]
            self.sourcing_reference = ref
            self.message_post(body=_("Sourcing Reference generated: %s") % ref)
            _logger.info(
                "crm.lead %s: derived sourcing_reference %s from project_reference",
                self.id, ref,
            )
            return

        # Path B — legacy fallback, increment the shared sequence.
        cc = self.partner_id.client_code.strip().upper()
        seg = self.gpc_segment_id.code

        self.env.flush_all()

        Seq = self.env['sourcing.client.sequence'].sudo()
        seq = Seq.search([
            ('partner_id', '=', self.partner_id.id),
            ('gpc_segment', '=', seg),
        ], limit=1)

        if seq:
            self.env.cr.execute(
                "SELECT count FROM sourcing_client_sequence WHERE id = %s FOR UPDATE",
                (seq.id,),
            )
            row = self.env.cr.fetchone()
            new_count = (row[0] if row else 0) + 1
            seq.write({'count': new_count})
        else:
            seq = Seq.create({
                'partner_id': self.partner_id.id,
                'gpc_segment': seg,
                'count': 1,
            })
            new_count = 1

        yy = fields.Date.context_today(self).strftime('%y')
        ref = f"OP-{cc}-{seg}-{yy}-{new_count:03d}"
        self.sourcing_reference = ref
        self.message_post(body=_("Sourcing Reference generated: %s") % ref)
        _logger.info("crm.lead %s: generated sourcing_reference %s (legacy path)", self.id, ref)

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        # PR- generation: as soon as both prerequisites are present on
        # creation of an opportunity. Quiet on failure — incomplete leads
        # are normal at this stage. `skip_sourcing_validation` context
        # bypasses for tooling that needs to create raw records.
        if not self.env.context.get('skip_sourcing_validation'):
            for lead in leads:
                if (
                    lead.type == 'opportunity'
                    and not lead.project_reference
                    and lead._can_generate_project_reference()
                ):
                    try:
                        lead._generate_project_reference()
                    except Exception as e:
                        _logger.warning(
                            "crm.lead %s: PR- generation skipped on create: %s",
                            lead.id, e,
                        )
        return leads

    def write(self, vals):
        if 'stage_id' in vals and not self.env.context.get('skip_sourcing_validation'):
            new_stage = self.env['crm.stage'].browse(vals['stage_id']) if vals['stage_id'] else False
            for lead in self:
                old_stage = lead.stage_id
                if old_stage == new_stage:
                    continue
                from_inquiry = self._is_incoming_inquiry_stage(old_stage)
                to_lost = self._is_lost_stage(new_stage)
                if from_inquiry and not to_lost:
                    lead._validate_inquiry_exit()

        result = super().write(vals)

        # Existing OP- trigger on Quotation stage entry.
        if 'stage_id' in vals and not self.env.context.get('skip_sourcing_validation'):
            for lead in self:
                if (
                    self._is_quotation_stage(lead.stage_id)
                    and not lead.sourcing_reference
                    and lead.partner_id
                    and lead.gpc_segment_id
                ):
                    lead._generate_sourcing_reference()

        # PR- trigger: fires whenever an existing opportunity's partner,
        # segment, or type changes such that it now qualifies. Covers:
        #   * lead -> opportunity conversion
        #   * partner assigned (and partner has client_code)
        #   * segment selected
        # Quiet on failure.
        pr_triggers = {'partner_id', 'gpc_segment_id', 'type'}
        if pr_triggers & set(vals.keys()) and not self.env.context.get('skip_sourcing_validation'):
            for lead in self:
                if (
                    lead.type == 'opportunity'
                    and not lead.project_reference
                    and lead._can_generate_project_reference()
                ):
                    try:
                        lead._generate_project_reference()
                    except Exception as e:
                        _logger.warning(
                            "crm.lead %s: PR- generation skipped on write: %s",
                            lead.id, e,
                        )

        return result

    def action_view_partner_opportunities(self):
        """Smart-button action invoked from res.partner — opens the lead
        list filtered to non-Lost opportunities for the partner."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orders'),
            'res_model': 'crm.lead',
            'view_mode': 'list,kanban,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('type', '=', 'opportunity'),
                ('active', '=', True),
            ],
            'context': {'default_partner_id': self.partner_id.id},
        }

    def action_view_rfqs(self):
        """Smart-button action — opens RFQs/POs linked to this opportunity.

        New RFQs created from this action pre-fill `opportunity_id` and
        `gpc_segment_id` via context defaults. `partner_id` is intentionally
        not defaulted — the PO partner is the supplier, not the client.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('RFQs / POs for %s') % (self.sourcing_reference or self.name or ''),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('opportunity_id', '=', self.id)],
            'context': {
                'default_opportunity_id': self.id,
                'default_gpc_segment_id': self.gpc_segment_id.id or False,
            },
        }
