from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SourcingInspection(models.Model):
    """Pre-shipment / DUPRO / factory inspection record.

    Schema mirrors Courtwell's existing paper QC form (six checklist
    categories with sub-item booleans + per-section pass/fail), with
    additional structured linkage to project / SO / PO / supplier so
    inspection cost and outcome flow into the same analytic-account
    architecture used by freight expenses.
    """
    _name = 'sourcing.inspection'
    _description = 'Sourcing QC Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'inspection_date desc, id desc'
    _rec_name = 'name'

    # ------------------------------------------------------------------
    # Identity + dates
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference',
        default=lambda self: _('New'),
        readonly=True,
        copy=False,
        index=True,
    )
    contract_number = fields.Char(
        string='Contract / PO No.',
        tracking=True,
        help='External contract or PO number printed on the inspection '
             'form (e.g. BC-1096). Free text — does not need to match '
             'the system PO sequence.',
    )
    inspection_date = fields.Date(
        string='Inspection Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    inspection_type = fields.Selection(
        [
            ('psi',         'Pre-Shipment Inspection (PSI)'),
            ('dupro',       'During-Production Inspection (DUPRO)'),
            ('factory_aud', 'Factory Audit'),
            ('loading',     'Loading Supervision'),
            ('lab_test',    'Lab Test'),
            ('reinspect',   'Re-Inspection'),
        ],
        string='Inspection Type',
        default='psi',
        required=True,
        tracking=True,
    )

    # ------------------------------------------------------------------
    # Parties
    # ------------------------------------------------------------------
    supplier_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        domain=[('contact_type', '=', 'supplier')],
        tracking=True,
        help='Supplier whose goods are being inspected. When set, the '
             'factory name and address default from the supplier record.',
    )
    factory_name = fields.Char(
        string='Factory Name',
        tracking=True,
        help='Display name printed on the inspection form. Defaults from '
             'the linked supplier; can be overridden for sub-factory '
             'scenarios.',
    )
    factory_address = fields.Char(
        string='Factory Address',
    )
    factory_contact_name = fields.Char(
        string='Factory Person in Charge',
        help='Factory-side signatory on the inspection report.',
    )
    inspector_user_id = fields.Many2one(
        'res.users',
        string='Inspector (Courtwell)',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    inspector_partner_id = fields.Many2one(
        'res.partner',
        string='3rd-Party Inspector',
        domain=[('contact_type', '=', 'service_provider')],
        help='Optional. Set when a third-party inspection company '
             '(SGS / Bureau Veritas / Intertek / etc.) is engaged. '
             'Leave blank for in-house Courtwell QC.',
    )

    # ------------------------------------------------------------------
    # Linkage to commercial chain
    # ------------------------------------------------------------------
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        tracking=True,
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        tracking=True,
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        tracking=True,
        help='Linked project. Used to derive the QCI- reference base and '
             'to receive any inspection_cost via the project analytic '
             'account.',
    )
    parent_inspection_id = fields.Many2one(
        'sourcing.inspection',
        string='Parent Inspection (for Re-Inspection)',
        help='When this is a re-inspection of a previously failed check, '
             'link to the original record.',
    )
    child_inspection_ids = fields.One2many(
        'sourcing.inspection', 'parent_inspection_id',
        string='Re-Inspections',
    )
    reinspection_count = fields.Integer(
        compute='_compute_reinspection_count',
    )

    # ------------------------------------------------------------------
    # 6 Inspection Categories — each has sub-item booleans + a per-
    # section pass/fail result
    # ------------------------------------------------------------------
    # Carton (紙箱檢驗)
    carton_check_shipping_marks = fields.Boolean(string='Shipping Marks')
    carton_check_paper_quality  = fields.Boolean(string='Paper Quality')
    carton_check_size_deviation = fields.Boolean(string='Size OK (no deviation)')
    carton_check_barcode        = fields.Boolean(string='Barcode')
    carton_check_sealing        = fields.Boolean(string='Sealing')
    carton_check_appearance     = fields.Boolean(string='Appearance / Printing')
    carton_result = fields.Selection(
        [('pass', 'Pass'), ('fail', 'Fail')],
        string='Carton Result',
    )

    # Packaging (包裝檢驗)
    packaging_check_method      = fields.Boolean(string='Packing Method')
    packaging_check_protection  = fields.Boolean(string='Well Protected')
    packaging_check_material    = fields.Boolean(string='Material Correct')
    packaging_check_color_card  = fields.Boolean(string='Color Card Correct')
    packaging_check_quantity    = fields.Boolean(string='Quantity Correct')
    packaging_result = fields.Selection(
        [('pass', 'Pass'), ('fail', 'Fail')],
        string='Packaging Result',
    )

    # Accessories (配件檢驗)
    accessories_check_nameplate    = fields.Boolean(string='Nameplate')
    accessories_check_hangtag      = fields.Boolean(string='Hangtag')
    accessories_check_origin_label = fields.Boolean(string='Country-of-Origin Label')
    accessories_check_position     = fields.Boolean(string='Position Correct')
    accessories_check_manual       = fields.Boolean(string='Instruction Manual')
    accessories_check_accessories  = fields.Boolean(string='Accessories Present')
    accessories_result = fields.Selection(
        [('pass', 'Pass'), ('fail', 'Fail')],
        string='Accessories Result',
    )

    # Component (分件檢測)
    component_check_quantity       = fields.Boolean(string='Quantity')
    component_check_material       = fields.Boolean(string='Material')
    component_check_dimensions     = fields.Boolean(string='Dimensions')
    component_check_color_matching = fields.Boolean(string='Color Matching')
    component_check_other          = fields.Boolean(string='Other Component Notes')
    component_result = fields.Selection(
        [('pass', 'Pass'), ('fail', 'Fail')],
        string='Component Result',
    )

    # Structural (結構檢測)
    structural_check_structure = fields.Boolean(string='Structural Test')
    structural_check_function  = fields.Boolean(string='Functional Test')
    structural_result = fields.Selection(
        [('pass', 'Pass'), ('fail', 'Fail')],
        string='Structural Result',
    )

    # Overall (整體檢測)
    overall_check_overall    = fields.Boolean(string='Overall Inspection')
    overall_check_appearance = fields.Boolean(string='Appearance Inspection')
    overall_result = fields.Selection(
        [('pass', 'Pass'), ('fail', 'Fail')],
        string='Overall Result',
    )

    # Other / catch-all
    other_notes = fields.Text(string='Other Inspection Notes')
    other_result = fields.Selection(
        [('pass', 'Pass'), ('fail', 'Fail')],
        string='Other Result',
    )

    # ------------------------------------------------------------------
    # Per-SKU detail lines (the bottom grid in the paper form)
    # ------------------------------------------------------------------
    sku_line_ids = fields.One2many(
        'sourcing.inspection.sku.line', 'inspection_id',
        string='SKU Detail Lines',
    )

    # ------------------------------------------------------------------
    # Free-text blocks (paper form: 驗貨評語/問題 + 備註/改進)
    # ------------------------------------------------------------------
    inspection_comments = fields.Text(
        string='Inspection Comments / Issues',
        help='Free text. Use for findings, measured-vs-spec deltas, '
             'observations, and anything not captured in the checklists.',
    )
    improvement_notes = fields.Text(
        string='Improvement Notes',
        help='Free text. Recommended actions, follow-ups, lessons for '
             'next batch.',
    )

    # ------------------------------------------------------------------
    # Final outcome
    # ------------------------------------------------------------------
    final_outcome = fields.Selection(
        [
            ('pass',    'Pass'),
            ('rework',  'Rework Required'),
            ('fail',    'Fail'),
            ('pending', 'Pending'),
        ],
        string='Quality Confirmation',
        tracking=True,
        help='Final inspection verdict, signed off by the Courtwell '
             'inspector. Drives downstream gating (shipment release, '
             're-inspection scheduling, etc.) in future iterations.',
    )
    bulk_completion_pct = fields.Float(
        string='Bulk Completion %',
        default=100.0,
        help='Percentage of the bulk order produced at the time of '
             'inspection. 100% for PSI; lower for DUPRO mid-production '
             'checks.',
    )

    # ------------------------------------------------------------------
    # Workflow state
    #
    # New `submitted` state sits between in_progress and completed:
    # QC personnel transition from in_progress -> submitted by clicking
    # "Submit to Merchandiser". The merchandiser must then act
    # (decision = load_for_shipping / hold / reject_load) which closes
    # the record to completed.
    # ------------------------------------------------------------------
    state = fields.Selection(
        [
            ('draft',       'Draft'),
            ('scheduled',   'Scheduled'),
            ('in_progress', 'In Progress'),
            ('submitted',   'Submitted (Pending Review)'),
            ('completed',   'Completed'),
            ('cancelled',   'Cancelled'),
        ],
        string='State',
        default='draft',
        tracking=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Merchandiser review (Phase 1: split UI + same-day review gate)
    # ------------------------------------------------------------------
    merchandiser_user_id = fields.Many2one(
        'res.users',
        string='Reviewer (Merchandiser)',
        tracking=True,
        help='Merchandiser responsible for reviewing this inspection '
             'after QC submits it. Defaults from the linked project '
             'or sale order. Receives a same-day activity on submit.',
    )
    qc_submitted_at = fields.Datetime(
        string='Submitted by QC',
        readonly=True,
        copy=False,
        tracking=True,
    )
    merchandiser_decision = fields.Selection(
        [
            ('load_for_shipping', 'Load for Shipping'),
            ('hold',              'Hold'),
            ('reject_load',       'Reject Loading'),
        ],
        string='Loading Decision',
        copy=False,
        tracking=True,
        help='Merchandiser\'s decision on whether the inspected goods '
             'can be loaded for shipping. Only "Load for Shipping" '
             'clears the goods for the shipment workflow.',
    )
    merchandiser_review_date = fields.Date(
        string='Reviewed On',
        readonly=True,
        copy=False,
        tracking=True,
    )
    merchandiser_review_notes = fields.Text(
        string='Reviewer Notes',
        help='Merchandiser\'s commentary on the inspection, sent back to '
             'QC if rework / re-inspection is required.',
    )
    is_overdue_review = fields.Boolean(
        string='Overdue Review',
        compute='_compute_is_overdue_review',
        search='_search_is_overdue_review',
        help='True when QC has submitted, no decision is set, and the '
             'submission date is before today.',
    )

    # ------------------------------------------------------------------
    # Photos (phone-captured inspection photos)
    #
    # Many2many to ir.attachment so the Odoo mobile app's attachment
    # button can append multiple photos directly from the device camera
    # or gallery. Separate from the chatter so the photo gallery is the
    # primary surface, not buried in conversation.
    # ------------------------------------------------------------------
    inspection_photo_ids = fields.Many2many(
        'ir.attachment',
        'sourcing_inspection_photo_rel',
        'inspection_id', 'attachment_id',
        string='Inspection Photos',
        help='Photos taken during the inspection. Use the mobile app\'s '
             'attachment button (paperclip) to capture from camera or '
             'pick from gallery — supports multiple uploads.',
    )
    inspection_photo_count = fields.Integer(
        compute='_compute_inspection_photo_count',
    )

    # ------------------------------------------------------------------
    # Cost (optional)
    # ------------------------------------------------------------------
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id,
    )
    inspection_cost = fields.Monetary(
        string='Inspection Cost',
        currency_field='currency_id',
        help='Fee paid to the third-party inspector (if applicable). '
             'Posts to the linked project\'s analytic account when '
             'inspection is completed — same flow as freight expenses.',
    )
    cost_posted = fields.Boolean(
        string='Cost Posted',
        default=False,
        copy=False,
        tracking=True,
        help='True once the inspection_cost has been posted as an '
             'hr.expense record against the linked project analytic.',
    )
    inspection_expense_id = fields.Many2one(
        'hr.expense',
        string='Inspection Expense',
        copy=False,
        ondelete='set null',
        help='The hr.expense record generated from this inspection.',
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('child_inspection_ids')
    def _compute_reinspection_count(self):
        for rec in self:
            rec.reinspection_count = len(rec.child_inspection_ids)

    @api.depends('inspection_photo_ids')
    def _compute_inspection_photo_count(self):
        for rec in self:
            rec.inspection_photo_count = len(rec.inspection_photo_ids)

    @api.depends('state', 'qc_submitted_at', 'merchandiser_decision')
    def _compute_is_overdue_review(self):
        today = fields.Date.context_today(self)
        for rec in self:
            submitted = rec.qc_submitted_at and rec.qc_submitted_at.date()
            rec.is_overdue_review = bool(
                rec.state == 'submitted'
                and not rec.merchandiser_decision
                and submitted
                and submitted < today
            )

    def _search_is_overdue_review(self, operator, value):
        """Lets the search filter "Overdue Reviews" work by translating
        the boolean compute into a real domain on stored fields."""
        today_dt = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        positive = (operator == '=' and value) or (operator == '!=' and not value)
        if positive:
            return [
                ('state', '=', 'submitted'),
                ('merchandiser_decision', '=', False),
                ('qc_submitted_at', '<', today_dt),
            ]
        return ['|', '|',
                ('state', '!=', 'submitted'),
                ('merchandiser_decision', '!=', False),
                ('qc_submitted_at', '>=', today_dt)]

    # ------------------------------------------------------------------
    # Onchanges
    # ------------------------------------------------------------------
    @api.onchange('supplier_id')
    def _onchange_supplier_id_defaults(self):
        for rec in self:
            if rec.supplier_id and not rec.factory_name:
                rec.factory_name = rec.supplier_id.name
            if rec.supplier_id and not rec.factory_address:
                # Build a one-line address from the supplier
                parts = [
                    rec.supplier_id.street,
                    rec.supplier_id.street2,
                    rec.supplier_id.city,
                    rec.supplier_id.state_id.name if rec.supplier_id.state_id else None,
                    rec.supplier_id.country_id.name if rec.supplier_id.country_id else None,
                ]
                rec.factory_address = ', '.join(p for p in parts if p)

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id_defaults(self):
        for rec in self:
            if rec.purchase_order_id:
                if not rec.contract_number:
                    rec.contract_number = rec.purchase_order_id.name
                if not rec.supplier_id:
                    rec.supplier_id = rec.purchase_order_id.partner_id

    @api.onchange('parent_inspection_id')
    def _onchange_parent_inspection_id(self):
        for rec in self:
            if rec.parent_inspection_id:
                rec.inspection_type = 'reinspect'
                # Inherit linkage from parent for convenience
                rec.supplier_id = rec.parent_inspection_id.supplier_id
                rec.purchase_order_id = rec.parent_inspection_id.purchase_order_id
                rec.sale_order_id = rec.parent_inspection_id.sale_order_id
                rec.project_id = rec.parent_inspection_id.project_id
                rec.merchandiser_user_id = rec.parent_inspection_id.merchandiser_user_id

    @api.onchange('project_id', 'sale_order_id')
    def _onchange_default_merchandiser(self):
        """Default the merchandiser from the project's user_id, falling
        back to the sale order's salesperson if no project."""
        for rec in self:
            if rec.merchandiser_user_id:
                continue
            if rec.project_id and rec.project_id.user_id:
                rec.merchandiser_user_id = rec.project_id.user_id
            elif rec.sale_order_id and rec.sale_order_id.user_id:
                rec.merchandiser_user_id = rec.sale_order_id.user_id

    # ------------------------------------------------------------------
    # Reference generation
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self._generate_inspection_ref(vals)
        return super().create(vals_list)

    @api.model
    def _generate_inspection_ref(self, vals):
        """Generate QCI reference.

        Format:
          - If project has sourcing_reference: QCI-{base}-{NN}
            where {NN} = count of inspections on the same project + 1
          - Otherwise: fallback to ir.sequence (QCI/YYYY/####)
        """
        project_id = vals.get('project_id')
        if project_id:
            project = self.env['project.project'].browse(project_id)
            base_ref = (
                project.sourcing_reference if hasattr(project, 'sourcing_reference')
                else False
            )
            if base_ref:
                base = base_ref.strip()
                # Strip the project-doctype prefix (PR-) if present
                if base.upper().startswith('PR-'):
                    base = base[3:]
                count = self.search_count([('project_id', '=', project_id)])
                return f"QCI-{base}-{(count + 1):02d}"
        return self.env['ir.sequence'].next_by_code(
            'sourcing.inspection'
        ) or _('New')

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_schedule(self):
        self.write({'state': 'scheduled'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        """Admin/reviewer bypass to skip the submit->review cycle.
        Kept for back-compat and full-control scenarios."""
        for rec in self:
            if not rec.final_outcome:
                raise UserError(_(
                    "Set a Quality Confirmation outcome before completing "
                    "inspection %s.", rec.name,
                ))
            rec.state = 'completed'
            rec.message_post(body=_(
                "Inspection completed. Outcome: <b>%s</b>. "
                "Bulk completion: %.1f%%.",
                dict(rec._fields['final_outcome'].selection).get(rec.final_outcome),
                rec.bulk_completion_pct,
            ))

    # ------------------------------------------------------------------
    # QC submission to Merchandiser
    # ------------------------------------------------------------------
    def action_submit_to_merchandiser(self):
        """Called by QC personnel when they finish inspection in the field.

        Validates that the QC outcome is set and a reviewer is assigned;
        transitions state to 'submitted'; auto-creates a same-day
        activity on the merchandiser so they review and decide on
        loading.
        """
        for rec in self:
            if rec.state not in ('draft', 'scheduled', 'in_progress'):
                raise UserError(_(
                    "Inspection %s is in state %s — only draft / "
                    "scheduled / in-progress inspections can be "
                    "submitted.",
                    rec.name, rec.state,
                ))
            if not rec.final_outcome:
                raise UserError(_(
                    "Set the Quality Confirmation (Pass / Rework / "
                    "Fail / Pending) before submitting inspection %s.",
                    rec.name,
                ))
            if not rec.merchandiser_user_id:
                raise UserError(_(
                    "Assign a Merchandiser (Reviewer) on inspection %s "
                    "before submitting. The reviewer receives an "
                    "activity to act on the inspection.",
                    rec.name,
                ))
            rec.write({
                'state': 'submitted',
                'qc_submitted_at': fields.Datetime.now(),
            })
            # Auto-create a same-day activity for the merchandiser
            try:
                act_type = rec.env.ref('mail.mail_activity_data_todo')
                rec.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=_('Review QC inspection %s and decide on loading',
                              rec.name),
                    note=_(
                        "Field QC submitted inspection <b>%(name)s</b> "
                        "(outcome: <b>%(out)s</b>, bulk: %(bulk).1f%%). "
                        "Open the inspection and set the Loading Decision: "
                        "Load for Shipping / Hold / Reject Loading.",
                        name=rec.name,
                        out=dict(rec._fields['final_outcome'].selection).get(
                            rec.final_outcome,
                        ),
                        bulk=rec.bulk_completion_pct,
                    ),
                    date_deadline=fields.Date.context_today(rec),
                    user_id=rec.merchandiser_user_id.id,
                )
            except Exception:
                # If mail.mail_activity_data_todo isn't found, fall back
                # to a chatter message — the workflow still progresses.
                rec.message_post(
                    body=_("Submitted by QC. Awaiting merchandiser review."),
                    partner_ids=rec.merchandiser_user_id.partner_id.ids,
                )
            rec.message_post(body=_(
                "Inspection submitted to <b>%s</b> for same-day review. "
                "Outcome from QC: <b>%s</b>.",
                rec.merchandiser_user_id.name,
                dict(rec._fields['final_outcome'].selection).get(
                    rec.final_outcome,
                ),
            ))
        return True

    # ------------------------------------------------------------------
    # Merchandiser decisions
    # ------------------------------------------------------------------
    def _apply_merchandiser_decision(self, decision):
        """Internal: record the decision and close the inspection.

        Server-side group check: even though the decision buttons are
        hidden from non-reviewers in the form view via `groups=`, the
        method can still be called via RPC. This block ensures the
        decision is genuinely reviewer-only at the server.

        Side-effect: when the inspection completes with a non-zero
        cost and a resolvable analytic account, the cost is auto-posted
        as an hr.expense (best-effort — failures are logged but don't
        block the decision).
        """
        self.ensure_one()
        if not (
            self.env.user.has_group('cw_sourcing_inspection.group_qc_reviewer')
            or self.env.user.has_group('base.group_system')
        ):
            raise UserError(_(
                "Only the QC Reviewer (Merchandiser) or an Admin can "
                "set the loading decision on inspection %s.",
                self.name,
            ))
        if self.state != 'submitted':
            raise UserError(_(
                "Inspection %s must be in 'Submitted' state for the "
                "reviewer to set a decision (currently: %s).",
                self.name, self.state,
            ))
        self.write({
            'merchandiser_decision': decision,
            'merchandiser_review_date': fields.Date.context_today(self),
            'state': 'completed',
        })
        # Mark related activity done
        activities = self.activity_ids.filtered(
            lambda a: a.user_id == self.merchandiser_user_id
        )
        if activities:
            activities.action_feedback(feedback=_('Decision: %s', decision))
        label = dict(self._fields['merchandiser_decision'].selection).get(decision)
        self.message_post(body=_(
            "Loading decision: <b>%s</b> by %s.",
            label, self.env.user.name,
        ))
        # Auto-post cost (best-effort). Fails silently with a chatter
        # note so the decision flow isn't blocked by an analytic issue.
        if self.inspection_cost > 0 and not self.cost_posted:
            try:
                self._do_post_inspection_cost()
            except UserError as e:
                self.message_post(body=_(
                    "Auto-post of inspection cost skipped: %s "
                    "Use the 'Post Cost' button on the inspection "
                    "form once the linkage is fixed.", str(e),
                ))

    # ------------------------------------------------------------------
    # Inspection cost -> hr.expense posting (same pattern as freight)
    # ------------------------------------------------------------------
    EXPENSE_PRODUCT_REF = 'cw_sourcing_inspection.product_inspection_qc_cost'

    def _resolve_inspection_analytic(self):
        """Resolve the analytic account that will receive the cost.

        Priority:
          1. project_id.account_id
          2. project found via sale.order line linkage (if sale_order_id set)
          3. False (caller decides how to handle)
        """
        self.ensure_one()
        if self.project_id and self.project_id.account_id:
            return self.project_id.account_id
        if self.sale_order_id:
            # SO -> any project via order_line.project_id
            line_projects = self.sale_order_id.order_line.mapped('project_id')
            if line_projects and line_projects[0].account_id:
                return line_projects[0].account_id
        return False

    def _resolve_inspection_expense_employee(self):
        """The hr.employee record to attach the expense to. Defaults to
        the inspector's employee link; falls back to current user's."""
        self.ensure_one()
        user = self.inspector_user_id or self.env.user
        emp = user.employee_id
        if not emp and user.employee_ids:
            emp = user.employee_ids[:1]
        return emp

    def _do_post_inspection_cost(self):
        """Internal: create the hr.expense record. Raises UserError on
        misconfigurations (used by both the manual action and the
        auto-trigger)."""
        self.ensure_one()
        if self.cost_posted:
            raise UserError(_(
                "Inspection %s already has a cost posted (expense %s). "
                "Reset first if you need to re-post.",
                self.name,
                self.inspection_expense_id.name if self.inspection_expense_id
                else _('(unknown)'),
            ))
        if self.inspection_cost <= 0:
            raise UserError(_(
                "No inspection cost to post on %s.", self.name,
            ))
        analytic = self._resolve_inspection_analytic()
        if not analytic:
            raise UserError(_(
                "No analytic account resolvable for %s. Link a project "
                "with an analytic account before posting cost.",
                self.name,
            ))
        employee = self._resolve_inspection_expense_employee()
        if not employee:
            user = self.inspector_user_id or self.env.user
            raise UserError(_(
                "Inspector %s has no linked Employee record. Configure "
                "in HR before posting inspection cost.",
                user.name,
            ))
        product_tmpl = self.env.ref(self.EXPENSE_PRODUCT_REF,
                                    raise_if_not_found=False)
        if not product_tmpl:
            raise UserError(_(
                "Expense product '%s' missing — module data file may not "
                "have loaded.", self.EXPENSE_PRODUCT_REF,
            ))
        variant = product_tmpl.product_variant_id
        if not variant:
            raise UserError(_(
                "Expense product '%s' has no active variant.",
                self.EXPENSE_PRODUCT_REF,
            ))
        expense = self.env['hr.expense'].create({
            'name': _('%s — Inspection Cost', self.name),
            'employee_id': employee.id,
            'product_id': variant.id,
            'quantity': 1.0,
            'price_unit': self.inspection_cost,
            'total_amount': self.inspection_cost,
            'currency_id': self.currency_id.id,
            'payment_mode': 'company_account',
            'analytic_distribution': {str(analytic.id): 100.0},
            'date': fields.Date.context_today(self),
        })
        self.write({
            'cost_posted': True,
            'inspection_expense_id': expense.id,
        })
        self.message_post(body=_(
            "Inspection cost <b>%(amt).2f %(curr)s</b> posted as expense "
            "<a href=# data-oe-model='hr.expense' data-oe-id='%(eid)d'>%(ename)s</a> "
            "on analytic account <b>%(acc)s</b>.",
            amt=self.inspection_cost,
            curr=self.currency_id.name,
            eid=expense.id, ename=expense.name,
            acc=analytic.display_name,
        ))
        return expense

    def action_post_inspection_cost(self):
        for rec in self:
            rec._do_post_inspection_cost()
        return True

    def action_reset_inspection_cost(self):
        """Undo cost posting. Deletes the expense only if still in draft."""
        for rec in self:
            if not rec.cost_posted:
                continue
            exp = rec.inspection_expense_id
            if exp and exp.state == 'draft':
                exp.unlink()
            elif exp:
                raise UserError(_(
                    "Cannot reset cost on %s — linked expense %s is in "
                    "state '%s', not draft. Void/refuse it in the "
                    "Expense app first.",
                    rec.name, exp.name, exp.state,
                ))
            rec.write({
                'cost_posted': False,
                'inspection_expense_id': False,
            })
            rec.message_post(body=_("Inspection cost posting reset."))
        return True

    def action_view_inspection_expense(self):
        self.ensure_one()
        if not self.inspection_expense_id:
            raise UserError(_("No expense posted for this inspection."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'res_id': self.inspection_expense_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_decision_load(self):
        for rec in self:
            rec._apply_merchandiser_decision('load_for_shipping')
        return True

    def action_decision_hold(self):
        for rec in self:
            rec._apply_merchandiser_decision('hold')
        return True

    def action_decision_reject(self):
        for rec in self:
            rec._apply_merchandiser_decision('reject_load')
        return True

    def action_send_back_to_qc(self):
        """Send inspection back to QC for rework / additional info,
        without recording a loading decision."""
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_(
                    "Can only send back inspections in 'Submitted' state."
                ))
            rec.write({'state': 'in_progress'})
            rec.message_post(body=_(
                "Sent back to QC (%s) by %s for additional work or "
                "clarification.",
                rec.inspector_user_id.name, rec.env.user.name,
            ))
            # Reassign the activity to QC
            rec.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=_('Review / amend inspection %s — sent back by '
                          'merchandiser', rec.name),
                date_deadline=fields.Date.context_today(rec),
                user_id=rec.inspector_user_id.id,
            )
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_create_reinspection(self):
        """Convenience action: clone this inspection as a re-inspection,
        with parent_inspection_id set."""
        self.ensure_one()
        if self.final_outcome not in ('fail', 'rework'):
            raise UserError(_(
                "Re-inspection is only meaningful when the prior outcome "
                "was Fail or Rework Required. Current outcome: %s.",
                self.final_outcome or _('(not set)'),
            ))
        new_insp = self.copy({
            'parent_inspection_id': self.id,
            'inspection_type': 'reinspect',
            'state': 'draft',
            'final_outcome': False,
            'inspection_date': fields.Date.context_today(self),
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sourcing.inspection',
            'res_id': new_insp.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_reinspections(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Re-Inspections of %s', self.name),
            'res_model': 'sourcing.inspection',
            'view_mode': 'list,form',
            'domain': [('parent_inspection_id', '=', self.id)],
            'context': {'default_parent_inspection_id': self.id},
        }
