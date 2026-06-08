from collections import OrderedDict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


# (field_name, expense_product_xmlid, ui_label, selection_key)
# Order matters: drives both the form layout and the order expenses post.
FREIGHT_CATEGORIES = OrderedDict([
    ('inland_transport', (
        'inland_transport_cost',
        'cw_freight_expense.product_freight_inland_transport',
        'Inland Transport',
    )),
    ('export_clearance', (
        'export_clearance_cost',
        'cw_freight_expense.product_freight_export_clearance',
        'Export Clearance',
    )),
    ('customs_filing', (
        'customs_filing_cost',
        'cw_freight_expense.product_freight_customs_filing',
        'Customs Filing Fee',
    )),
    ('bl_fee', (
        'bl_fee_cost',
        'cw_freight_expense.product_freight_bl_fee',
        'BL Fee',
    )),
    ('cert_origin', (
        'cert_origin_cost',
        'cw_freight_expense.product_freight_cert_origin',
        'Certificate of Origin',
    )),
    ('documentation', (
        'documentation_cost',
        'cw_freight_expense.product_freight_documentation',
        'Documentation — Other',
    )),
    ('port_fees', (
        'port_fees_cost',
        'cw_freight_expense.product_freight_port_fees',
        'Port Fees',
    )),
    ('actual_freight', (
        'actual_freight_cost',
        'cw_freight_expense.product_freight_actual',
        'Actual Freight',
    )),
])

# Aliases for the @api.depends decorator — Python's @api.depends doesn't
# accept dynamic argument lists, so we list field names explicitly.
_FREIGHT_FIELD_NAMES = tuple(v[0] for v in FREIGHT_CATEGORIES.values())


class CwShipment(models.Model):
    _inherit = 'cw.shipment'

    # ------------------------------------------------------------------
    # 8 decomposed freight cost fields
    # ------------------------------------------------------------------
    inland_transport_cost = fields.Monetary(
        string='Inland Transport',
        help='Trucking / drayage from factory to origin port.',
    )
    export_clearance_cost = fields.Monetary(
        string='Export Clearance',
        help='Origin-side customs clearance act.',
    )
    customs_filing_cost = fields.Monetary(
        string='Customs Filing Fee',
        help='Fee for filing the customs declaration.',
    )
    bl_fee_cost = fields.Monetary(
        string='BL Fee',
        help='Bill of Lading issuance fee.',
    )
    cert_origin_cost = fields.Monetary(
        string='Certificate of Origin',
        help='Cost of obtaining the Certificate of Origin.',
    )
    documentation_cost = fields.Monetary(
        string='Documentation — Other',
        help='Misc paperwork: telex release, AMS, ENS, ISF, etc.',
    )
    port_fees_cost = fields.Monetary(
        string='Port Fees',
        help='THC, port handling, demurrage.',
    )
    actual_freight_cost = fields.Monetary(
        string='Actual Freight',
        help='The ocean/air freight leg itself.',
    )

    total_freight_cost = fields.Monetary(
        string='Total Freight Cost',
        compute='_compute_total_freight_cost',
        store=True,
        help='Sum of all 8 freight components. Single source of truth '
             'for project cost roll-up.',
    )

    # ------------------------------------------------------------------
    # Workflow flag + back-reference
    # ------------------------------------------------------------------
    freight_finalized = fields.Boolean(
        string='Freight Finalized',
        default=False,
        copy=False,
        tracking=True,
        help='True once Aris confirms the freight booking and posts the '
             'breakdown to the Expense app.',
    )

    freight_expense_ids = fields.One2many(
        'hr.expense', 'cw_shipment_id',
        string='Freight Expenses',
    )
    freight_expense_count = fields.Integer(
        string='Freight Expense Count',
        compute='_compute_freight_expense_count',
    )

    # ------------------------------------------------------------------
    # Consolidation / freight allocation
    #
    # When a shipment is a consolidated container shipment (goods from
    # multiple suppliers / multiple clients in containers going out on
    # the same vessel), the 8 freight cost categories must be split
    # across the constituent containers so each client's project takes
    # only its share of the cost.
    #
    # 'single' is the legacy single-supplier behaviour: all freight
    # routes to shipment.project_id (or sale_order_id's project).
    # The four split methods each compute container-level pcts based
    # on a dimension recorded on cw.shipment.container.
    # ------------------------------------------------------------------
    allocation_method = fields.Selection(
        [
            ('single',    'Single supplier (no split)'),
            ('by_value',  'By Order Value'),
            ('by_weight', 'By Weight'),
            ('by_volume', 'By Volume'),
            ('equal',     'Equal Split'),
        ],
        string='Freight Allocation Method',
        default='single',
        tracking=True,
        help='How the 8 freight cost categories are split across '
             'containers when this is a consolidated shipment. '
             '"Single" routes everything to the shipment-level project. '
             'The four split methods generate container-level percentages '
             'based on the dimension named.',
    )

    allocation_total_pct = fields.Float(
        string='Allocation Total %',
        compute='_compute_allocation_total_pct',
        help='Sum of container allocation percentages. Should be ~100 '
             'before finalization.',
    )

    @api.depends(*_FREIGHT_FIELD_NAMES)
    def _compute_total_freight_cost(self):
        for rec in self:
            rec.total_freight_cost = sum(
                rec[fname] or 0.0 for fname in _FREIGHT_FIELD_NAMES
            )

    @api.depends('freight_expense_ids')
    def _compute_freight_expense_count(self):
        for rec in self:
            rec.freight_expense_count = len(rec.freight_expense_ids)

    @api.depends('container_ids.allocated_freight_pct')
    def _compute_allocation_total_pct(self):
        for rec in self:
            rec.allocation_total_pct = sum(
                rec.container_ids.mapped('allocated_freight_pct') or [0.0]
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_analytic_account(self):
        """Find the analytic account for freight cost roll-up.

        Priority:
          1. Linked project.project's account_id
          2. project linked through sale_order_id
        Returns False if neither is available.
        """
        self.ensure_one()
        if self.project_id and self.project_id.account_id:
            return self.project_id.account_id
        if self.sale_order_id:
            project = self.env['project.project'].search(
                [('sale_order_id', '=', self.sale_order_id.id)],
                limit=1,
            )
            if project and project.account_id:
                return project.account_id
        return False

    def _resolve_expense_employee(self):
        """Map responsible_user_id to hr.employee. Returns False if no
        link exists (responsible user has no employee record)."""
        self.ensure_one()
        user = self.responsible_user_id or self.env.user
        employee = user.employee_id
        if not employee and user.employee_ids:
            employee = user.employee_ids[:1]
        return employee

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_recompute_freight_allocation(self):
        """Compute per-container `allocated_freight_pct` based on the
        shipment's `allocation_method`.

        - single:    all pcts zeroed; finalization routes to the
                     shipment-level project as a single bucket.
        - equal:     100 / N for each container.
        - by_value:  container.order_value / sum * 100.
        - by_weight: container.weight_kg / sum * 100.
        - by_volume: container.volume_cbm / sum * 100.

        Validation: dimension-based methods require the dimension to be
        populated on at least one container; total zero raises so the
        user fixes the missing values rather than silently allocating 0%.
        """
        for ship in self:
            containers = ship.container_ids
            n = len(containers)
            method = ship.allocation_method or 'single'
            if method == 'single' or n == 0:
                containers.write({'allocated_freight_pct': 0.0})
                continue
            if method == 'equal':
                pct = 100.0 / n
                for c in containers:
                    c.allocated_freight_pct = pct
                continue
            dim_field = {
                'by_value':  'order_value',
                'by_weight': 'weight_kg',
                'by_volume': 'volume_cbm',
            }[method]
            values = [c[dim_field] or 0.0 for c in containers]
            total = sum(values)
            if total <= 0:
                raise UserError(_(
                    "Cannot allocate '%(method)s' on %(ship)s — total "
                    "%(field)s across containers is zero. Fill in the "
                    "%(field)s on each container before recomputing.",
                    method=method, ship=ship.display_name, field=dim_field,
                ))
            for c, v in zip(containers, values):
                c.allocated_freight_pct = (v / total * 100.0)
        return True

    def _create_freight_expense_records(self, analytic, scale=1.0, label_suffix=''):
        """Internal: create the 1..8 hr.expense records for one target
        analytic account, scaled by `scale` (1.0 = full freight, 0.43 =
        43% of each category, etc.).
        """
        self.ensure_one()
        employee = self._resolve_expense_employee()
        Expense = self.env['hr.expense']
        posted = 0
        for key, (fname, prod_ref, label) in FREIGHT_CATEGORIES.items():
            amount = (self[fname] or 0.0) * scale
            if not amount:
                continue
            product_tmpl = self.env.ref(prod_ref, raise_if_not_found=False)
            if not product_tmpl:
                raise UserError(_(
                    "Expense product '%s' missing.", prod_ref,
                ))
            product_variant = product_tmpl.product_variant_id
            if not product_variant:
                raise UserError(_(
                    "Expense product '%s' has no active variant.", prod_ref,
                ))
            name = _('%(ship)s — %(cat)s', ship=self.display_name, cat=label)
            if label_suffix:
                name = f"{name} [{label_suffix}]"
            Expense.create({
                'name': name,
                'employee_id': employee.id,
                'product_id': product_variant.id,
                'quantity': 1.0,
                'price_unit': amount,
                'total_amount': amount,
                'currency_id': self.currency_id.id,
                'payment_mode': 'company_account',
                'analytic_distribution': {str(analytic.id): 100.0},
                'cw_shipment_id': self.id,
                'cw_freight_category': key,
                'date': fields.Date.context_today(self),
            })
            posted += 1
        return posted

    def action_finalize_freight(self):
        """Post the 8-category breakdown to the Expense app.

        Branches on `allocation_method`:
          - single: freight routes to one project (shipment.project_id
            or sale_order_id's project). Legacy single-supplier behaviour.
          - any split method: freight is scaled per container's
            allocated_freight_pct and posted once per container, to each
            container's project analytic account.
        """
        for rec in self:
            if rec.freight_finalized:
                raise UserError(_(
                    "Freight on %s is already finalized. Use "
                    "'Reset Freight Finalization' to re-post.",
                    rec.display_name,
                ))
            if rec.total_freight_cost <= 0:
                raise UserError(_(
                    "Cannot finalize freight on %s — no costs entered.",
                    rec.display_name,
                ))
            employee = rec._resolve_expense_employee()
            if not employee:
                user = rec.responsible_user_id or rec.env.user
                raise UserError(_(
                    "Cannot finalize freight on %s — responsible user (%s) "
                    "has no linked Employee record. Configure in HR before "
                    "posting freight expenses.",
                    rec.display_name, user.name,
                ))

            method = rec.allocation_method or 'single'
            total_posted = 0
            destinations = []

            if method == 'single' or not rec.container_ids:
                analytic = rec._resolve_analytic_account()
                if not analytic:
                    raise UserError(_(
                        "Cannot finalize freight on %s — no linked project "
                        "(with an analytic account). Link a project or "
                        "switch to a split allocation method with "
                        "per-container projects.",
                        rec.display_name,
                    ))
                total_posted += rec._create_freight_expense_records(
                    analytic, scale=1.0,
                )
                destinations.append(f"{analytic.display_name}: 100.0%")
            else:
                # Split route: validate first
                containers = rec.container_ids.filtered(
                    lambda c: c.allocated_freight_pct > 0
                )
                if not containers:
                    raise UserError(_(
                        "Allocation Method is '%(m)s' but no container has "
                        "a non-zero Allocated %%. Click 'Recompute "
                        "Allocation' first, or enter percentages manually.",
                        m=method,
                    ))
                pct_total = sum(containers.mapped('allocated_freight_pct'))
                if abs(pct_total - 100.0) > 0.5:
                    raise UserError(_(
                        "Container allocation percentages sum to "
                        "%(t).2f%%, expected 100%%. Recompute or fix "
                        "manually before finalizing.", t=pct_total,
                    ))
                missing = containers.filtered(
                    lambda c: not (c.project_id and c.project_id.account_id)
                )
                if missing:
                    details = ', '.join(
                        c.cntr_number or f"container #{c.sequence or c.id}"
                        for c in missing
                    )
                    raise UserError(_(
                        "Cannot finalize: these container(s) lack a "
                        "linked project with an analytic account: %s. "
                        "Set Sale Order on each container so its "
                        "project is resolved.", details,
                    ))
                for container in containers:
                    analytic = container.project_id.account_id
                    scale = container.allocated_freight_pct / 100.0
                    suffix = (
                        container.cntr_number
                        or f"container #{container.sequence or container.id}"
                    )
                    total_posted += rec._create_freight_expense_records(
                        analytic, scale=scale, label_suffix=suffix,
                    )
                    destinations.append(
                        f"{analytic.display_name}: "
                        f"{container.allocated_freight_pct:.1f}%"
                    )

            rec.freight_finalized = True
            rec.message_post(body=_(
                "Freight finalized (method: %(method)s). %(n)d expense "
                "record(s) posted, total %(total).2f %(curr)s.<br/>"
                "Destinations:<br/>%(dest)s",
                method=method,
                n=total_posted,
                total=rec.total_freight_cost,
                curr=rec.currency_id.name,
                dest='<br/>'.join(destinations),
            ))
        return True

    def action_reset_freight_finalization(self):
        """Undo a finalization. Deletes generated expenses still in
        draft state. Refuses if any expense has been advanced."""
        for rec in self:
            if not rec.freight_finalized:
                continue
            draft = rec.freight_expense_ids.filtered(
                lambda e: e.state == 'draft',
            )
            non_draft = rec.freight_expense_ids - draft
            if non_draft:
                raise UserError(_(
                    "Cannot reset freight on %s — %d expense(s) have been "
                    "submitted or approved. Void or refuse them in the "
                    "Expense app first, then reset here.",
                    rec.display_name, len(non_draft),
                ))
            draft.unlink()
            rec.freight_finalized = False
            rec.message_post(body=_(
                "Freight finalization reset. Draft expenses deleted; you "
                "can edit the breakdown and re-post."
            ))
        return True

    def action_view_freight_expenses(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Freight Expenses — %s', self.display_name),
            'res_model': 'hr.expense',
            'view_mode': 'list,form',
            'domain': [('cw_shipment_id', '=', self.id)],
            'context': {
                'default_cw_shipment_id': self.id,
                'search_default_group_by_category': 1,
            },
        }
