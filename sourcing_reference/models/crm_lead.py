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
             'Generated on first entry to the Sourcing stage.',
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

    def _is_sourcing_stage(self, stage):
        if not stage:
            return False
        target = self.env.ref('sourcing_reference.crm_stage_sourcing', raise_if_not_found=False)
        if target and stage.id == target.id:
            return True
        return (stage.name or '').strip().lower() == 'sourcing'

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

    def _generate_sourcing_reference(self):
        """Generate OP-{cc}-{seg}-{YY}-{NNN} on entry to Sourcing.

        Idempotent: if a reference already exists, returns silently.
        Concurrency-safe: uses a SELECT ... FOR UPDATE row lock on the
        sequence row to prevent duplicate sequence numbers under
        simultaneous transitions for the same (client, segment) pair.
        """
        self.ensure_one()
        if self.sourcing_reference:
            return
        self._validate_inquiry_exit()

        cc = self.partner_id.client_code.strip().upper()
        seg = self.gpc_segment_id.code

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
        _logger.info("crm.lead %s: generated sourcing_reference %s", self.id, ref)

    def write(self, vals):
        if 'stage_id' in vals and not self.env.context.get('skip_sourcing_validation'):
            new_stage = self.env['crm.stage'].browse(vals['stage_id']) if vals['stage_id'] else False
            for lead in self:
                old_stage = lead.stage_id
                if old_stage == new_stage:
                    continue
                from_inquiry = self._is_incoming_inquiry_stage(old_stage)
                to_lost = self._is_lost_stage(new_stage)
                to_sourcing = self._is_sourcing_stage(new_stage)
                if from_inquiry and not to_lost:
                    lead._validate_inquiry_exit()
                if to_sourcing and not lead.sourcing_reference:
                    pass

        result = super().write(vals)

        if 'stage_id' in vals and not self.env.context.get('skip_sourcing_validation'):
            for lead in self:
                if (
                    self._is_sourcing_stage(lead.stage_id)
                    and not lead.sourcing_reference
                    and lead.partner_id
                    and lead.gpc_segment_id
                ):
                    lead._generate_sourcing_reference()

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
