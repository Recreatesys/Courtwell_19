from odoo import _, api, fields, models
from odoo.exceptions import UserError


# Statuses that represent "goods physically leaving" or "post-load".
# The gate fires when transitioning INTO any of these from a pre-load
# state. Tightening point: if cw_shipment evolves its statusbar, update
# this set rather than hunting through write() code.
POST_LOAD_STATUSES = ('shipped', 'arrived', 'delivered')


class CwShipment(models.Model):
    _inherit = 'cw.shipment'

    # ------------------------------------------------------------------
    # Linked inspections — resolved through sale.order linkage.
    # Computed-stored so it can drive smart-button counts and the
    # banner without per-render search overhead.
    # ------------------------------------------------------------------
    # NOTE: not stored. A stored compute would go stale because the
    # natural Odoo invalidation watches THIS record's fields, not the
    # related sourcing.inspection model's create/write events. Recompute
    # on every read is cheap (single SQL) and always correct — the gate
    # check is correctness-critical so we choose fresh over fast.
    inspection_ids = fields.Many2many(
        'sourcing.inspection',
        compute='_compute_inspection_ids',
        store=False,
        string='Linked Inspections',
        help='Inspections that share a sale order with this shipment '
             '(either the shipment\'s own sale_order_id, or any of its '
             'containers\' sale_order_ids in consolidation scenarios).',
    )
    inspection_count = fields.Integer(
        string='Inspections',
        compute='_compute_inspection_aggregates',
        store=False,
    )
    inspections_cleared_count = fields.Integer(
        string='Cleared for Loading',
        compute='_compute_inspection_aggregates',
        store=False,
    )
    inspections_blocking_count = fields.Integer(
        string='Blocking Loading',
        compute='_compute_inspection_aggregates',
        store=False,
        help='Inspections that exist but are NOT cleared for loading '
             '(Hold / Reject / awaiting reviewer decision / still in '
             'draft or in_progress).',
    )
    inspection_gate_state = fields.Selection(
        [
            ('no_inspections',  'No Inspections'),
            ('all_cleared',     'All Cleared for Loading'),
            ('partial_cleared', 'Partially Cleared (Mixed)'),
            ('blocked',         'Blocked — Inspections Pending or Rejected'),
        ],
        string='Inspection Gate',
        compute='_compute_inspection_aggregates',
        store=False,
        help='Summary of whether linked inspections allow this shipment '
             'to advance past Booked.',
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends(
        'sale_order_id',
        'container_ids.sale_order_id',
    )
    def _compute_inspection_ids(self):
        Inspection = self.env['sourcing.inspection']
        for ship in self:
            so_ids = set()
            if ship.sale_order_id:
                so_ids.add(ship.sale_order_id.id)
            for c in ship.container_ids:
                if c.sale_order_id:
                    so_ids.add(c.sale_order_id.id)
            if so_ids:
                ship.inspection_ids = Inspection.search([
                    ('sale_order_id', 'in', list(so_ids)),
                ])
            else:
                ship.inspection_ids = [(5, 0, 0)]  # clear

    # NOTE: dependency on inspection_ids only, NOT on its nested fields.
    # Walking inspection_ids.merchandiser_decision causes Odoo's
    # dependency-trigger system to try a reverse-side SQL search on a
    # non-stored M2M, which fails. The aggregates run on form-open
    # against whatever inspection_ids resolves to at that moment, and
    # the gate check uses _resolve_linked_inspections() at write-time
    # for a fresh read independent of the form cache.
    @api.depends('inspection_ids')
    def _compute_inspection_aggregates(self):
        for ship in self:
            insps = ship.inspection_ids
            n = len(insps)
            cleared = insps.filtered(
                lambda i: i.merchandiser_decision == 'load_for_shipping'
            )
            blocking = insps - cleared
            ship.inspection_count = n
            ship.inspections_cleared_count = len(cleared)
            ship.inspections_blocking_count = len(blocking)
            if n == 0:
                ship.inspection_gate_state = 'no_inspections'
            elif not blocking:
                ship.inspection_gate_state = 'all_cleared'
            elif cleared:
                ship.inspection_gate_state = 'partial_cleared'
            else:
                ship.inspection_gate_state = 'blocked'

    # ------------------------------------------------------------------
    # Gate enforcement
    # ------------------------------------------------------------------
    def write(self, vals):
        # Only check when status is changing AND new value is post-load
        if 'status' in vals and vals['status'] in POST_LOAD_STATUSES:
            bypass = self.env.context.get('bypass_inspection_gate')
            if not bypass:
                for ship in self:
                    ship._check_inspection_gate(target_status=vals['status'])
        return super().write(vals)

    def _resolve_linked_inspections(self):
        """Direct search for inspections linked to this shipment.
        Used by the write-time gate so it doesn't rely on the
        recordset's possibly-stale compute cache."""
        self.ensure_one()
        Inspection = self.env['sourcing.inspection']
        so_ids = set()
        if self.sale_order_id:
            so_ids.add(self.sale_order_id.id)
        for c in self.container_ids:
            if c.sale_order_id:
                so_ids.add(c.sale_order_id.id)
        if not so_ids:
            return Inspection.browse()
        return Inspection.search([('sale_order_id', 'in', list(so_ids))])

    def _check_inspection_gate(self, target_status):
        """Raise UserError if any linked inspection is not cleared for
        loading. Skipped silently when there are no linked inspections."""
        self.ensure_one()
        inspections = self._resolve_linked_inspections()
        blocking = inspections.filtered(
            lambda i: i.merchandiser_decision != 'load_for_shipping'
        )
        if not blocking:
            return
        # Build a useful error message listing the offending inspections
        lines = []
        for insp in blocking[:10]:  # cap at 10 for readability
            if insp.merchandiser_decision:
                reason = dict(
                    insp._fields['merchandiser_decision'].selection,
                ).get(insp.merchandiser_decision)
            elif insp.state == 'submitted':
                reason = _('awaiting merchandiser review')
            else:
                reason = _('not yet submitted to merchandiser')
            lines.append(
                f"  • {insp.name} ({insp.supplier_id.name or '?'}): {reason}"
            )
        extra = ''
        if len(blocking) > 10:
            extra = _("\n  … and %d more.") % (len(blocking) - 10)
        raise UserError(_(
            "Cannot advance shipment %(ship)s to '%(target)s': "
            "%(n)d linked inspection(s) are not cleared for loading.\n"
            "\n%(lines)s%(extra)s\n\n"
            "Either:\n"
            "  • Have the merchandiser set the loading decision to "
            "'Load for Shipping' on each blocking inspection, OR\n"
            "  • An Admin can bypass this gate by passing the context "
            "key bypass_inspection_gate=True.",
            ship=self.display_name,
            target=target_status,
            n=len(blocking),
            lines='\n'.join(lines),
            extra=extra,
        ))

    # ------------------------------------------------------------------
    # Convenience action — view the linked inspections in a list
    # ------------------------------------------------------------------
    def action_view_linked_inspections(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Inspections for %s', self.display_name),
            'res_model': 'sourcing.inspection',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.inspection_ids.ids)],
        }
