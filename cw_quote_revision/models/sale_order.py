from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ------------------------------------------------------------------
    # Revision tracking fields
    # ------------------------------------------------------------------
    revision_number = fields.Integer(
        string='Revision',
        default=1,
        copy=False,
        index=True,
        tracking=True,
        help='1 for the original quote. Each Revise click increments.',
    )

    parent_order_id = fields.Many2one(
        'sale.order',
        string='Previous Revision',
        copy=False,
        index=True,
        ondelete='restrict',
        help='The revision this one was copied from. Empty on Rev.1.',
    )

    revision_root_id = fields.Many2one(
        'sale.order',
        string='Quote Family',
        compute='_compute_revision_root_id',
        store=True,
        index=True,
        help='The Rev.1 ancestor of this revision chain. Used to group '
             'all revisions of the same quote together.',
    )

    revision_ids = fields.One2many(
        'sale.order', 'revision_root_id',
        string='All Revisions',
    )
    revision_count = fields.Integer(
        compute='_compute_revision_count',
        string='Revisions in Family',
    )

    is_latest_revision = fields.Boolean(
        compute='_compute_is_latest_revision',
        store=True,
        string='Latest Revision',
        help='True when no newer revision exists in this quote family.',
    )

    is_superseded = fields.Boolean(
        string='Superseded',
        default=False,
        copy=False,
        index=True,
        tracking=True,
        help='Set automatically when a newer revision of this quote is '
             'created. Confirming a superseded quote is blocked.',
    )

    # ------------------------------------------------------------------
    # Proforma Invoice document ID (stored in DB)
    #
    # The sourcing_reference module computes "PI-{base}" at render time
    # via _get_proforma_reference(). That's a Phase-1 simplification —
    # spec §7.1 requires the PI to be a tracked document with a status
    # and an issue date, and §12.1.3 was over-conservative in saying
    # "don't store it as a separate field".
    #
    # We store the PI ref as a computed-stored mirror of sourcing_reference
    # (QP- -> PI-), plus pi_status + pi_issued_date for lifecycle tracking.
    # Multi-PI per shipment (PI-AAA-A, PI-AAA-B) is intentionally out of
    # scope here — when needed it becomes its own model.
    # ------------------------------------------------------------------
    proforma_reference = fields.Char(
        string='Proforma Ref',
        compute='_compute_proforma_reference',
        store=True,
        index=True,
        copy=False,
        help='PI-{base} derived from sourcing_reference. Stored so the '
             'value is searchable and audit-traceable, not just rendered '
             'on the PDF.',
    )

    pi_status = fields.Selection(
        [
            ('not_issued', 'Not Issued'),
            ('issued',     'Issued'),
            ('superseded', 'Superseded'),
        ],
        string='Proforma Status',
        default='not_issued',
        copy=False,
        index=True,
        tracking=True,
        help='Lifecycle state of the Proforma Invoice for this order. '
             'Set to Issued via the "Mark PI as Issued" button after '
             'sending the PDF to the client. Automatically flipped to '
             'Superseded when the quote is revised.',
    )

    pi_issued_date = fields.Date(
        string='Proforma Issued Date',
        copy=False,
        tracking=True,
        help='Date the PI was marked as Issued.',
    )

    @api.depends('sourcing_reference')
    def _compute_proforma_reference(self):
        for order in self:
            ref = (order.sourcing_reference or '').strip()
            if ref.startswith('QP-'):
                order.proforma_reference = 'PI-' + ref[3:]
            else:
                order.proforma_reference = False

    def _get_proforma_reference(self):
        """Override sourcing_reference's compute-at-render version to
        return the stored field. PDF templates and any downstream code
        that calls this method continue to work; they just read from
        DB instead of recomputing."""
        self.ensure_one()
        return self.proforma_reference or super()._get_proforma_reference()

    def action_mark_pi_issued(self):
        for order in self:
            if order.is_superseded:
                raise UserError(_(
                    "Cannot mark PI as issued on %s — this revision "
                    "has been superseded. Issue the PI from the latest "
                    "revision instead.",
                    order.display_name,
                ))
            if order.pi_status == 'issued':
                raise UserError(_(
                    "PI is already marked as issued (date: %s).",
                    order.pi_issued_date,
                ))
            if not order.proforma_reference:
                raise UserError(_(
                    "Cannot mark PI as issued — no Proforma reference "
                    "available. This order needs a sourcing_reference "
                    "(generated from the linked Opportunity at Quotation "
                    "stage) before a PI can be issued."
                ))
            order.write({
                'pi_status': 'issued',
                'pi_issued_date': fields.Date.context_today(order),
            })
            order.message_post(body=_(
                "Proforma Invoice marked as issued: <b>%s</b>",
                order.proforma_reference,
            ))
        return True

    def action_reset_pi_status(self):
        """Undo a mistaken 'Issued' marking. GM-only in practice; access
        gated by permissions on the button in the view."""
        for order in self:
            if order.pi_status == 'superseded':
                raise UserError(_(
                    "Cannot reset PI status on a superseded revision. "
                    "The status follows the revision lifecycle."
                ))
            order.write({
                'pi_status': 'not_issued',
                'pi_issued_date': False,
            })
            order.message_post(body=_("PI status reset to Not Issued."))
        return True

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('parent_order_id', 'parent_order_id.revision_root_id')
    def _compute_revision_root_id(self):
        for order in self:
            if not order.parent_order_id:
                order.revision_root_id = order
            else:
                # Walk up the chain to the root. Bounded to 50 hops as a
                # safety net against accidental cycles (shouldn't happen
                # given Revise always points to a saved record).
                current = order.parent_order_id
                seen = set()
                for _ in range(50):
                    if not current.parent_order_id or current.id in seen:
                        break
                    seen.add(current.id)
                    current = current.parent_order_id
                order.revision_root_id = current

    @api.depends('revision_ids')
    def _compute_revision_count(self):
        for order in self:
            order.revision_count = len(order.revision_ids)

    @api.depends('revision_ids.revision_number', 'revision_number')
    def _compute_is_latest_revision(self):
        for order in self:
            siblings = order.revision_root_id.revision_ids
            if not siblings:
                order.is_latest_revision = True
                continue
            max_rev = max(siblings.mapped('revision_number') or [1])
            order.is_latest_revision = order.revision_number == max_rev

    # ------------------------------------------------------------------
    # Revise action
    # ------------------------------------------------------------------
    def action_revise_quotation(self):
        """Create the next revision of this quote.

        Copies the order with all lines, increments revision_number,
        sets parent_order_id, marks the current order as superseded.
        Logs the revision in the linked opportunity's chatter.
        """
        self.ensure_one()
        if self.state not in ('draft', 'sent'):
            raise UserError(_(
                "Only draft or sent quotations can be revised. "
                "Order %s is in state %s.",
                self.display_name, self.state,
            ))
        if self.is_superseded:
            raise UserError(_(
                "This quote is already superseded by a newer revision. "
                "Revise the latest version instead."
            ))

        new_order = self.copy({
            'revision_number': self.revision_number + 1,
            'parent_order_id': self.id,
            'is_superseded': False,
            # New revision starts with a fresh PI lifecycle. copy=False
            # on pi_status/pi_issued_date already drops them, but we set
            # explicitly to be defensive.
            'pi_status': 'not_issued',
            'pi_issued_date': False,
        })

        # Cascade PI status on the now-superseded revision:
        # if a PI was already issued for the prior revision, mark it
        # Superseded per spec §7.1 ("a new PI must be generated and the
        # previous PI marked superseded").
        pi_cascade_note = ''
        update_vals = {'is_superseded': True}
        if self.pi_status == 'issued':
            update_vals['pi_status'] = 'superseded'
            pi_cascade_note = _(
                " The previously-issued PI %s is now marked Superseded — "
                "issue a fresh PI on the new revision.",
                self.proforma_reference or '',
            )
        self.write(update_vals)

        body = _(
            "Quotation revised to <b>Rev.%(n)d</b> "
            "(<a href=# data-oe-model='sale.order' data-oe-id='%(id)d'>%(name)s</a>). "
            "Previous revision marked superseded.%(pi)s",
            n=new_order.revision_number,
            id=new_order.id,
            name=new_order.name,
            pi=pi_cascade_note,
        )
        self.message_post(body=body)
        if self.opportunity_id:
            self.opportunity_id.message_post(body=body)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': new_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_revisions(self):
        """Smart-button action: list all revisions sharing this root."""
        self.ensure_one()
        root = self.revision_root_id or self
        return {
            'type': 'ir.actions.act_window',
            'name': _('Revisions of %s', root.name),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('revision_root_id', '=', root.id)],
            'context': {'search_default_group_by_revision_family': 1},
        }

    # ------------------------------------------------------------------
    # Display + confirmation guard
    # ------------------------------------------------------------------
    def _compute_display_name(self):
        super()._compute_display_name()
        for order in self:
            if order.revision_number and order.revision_number > 1:
                order.display_name = f"{order.display_name} (Rev.{order.revision_number})"

    def action_confirm(self):
        for order in self:
            if order.is_superseded:
                latest = (
                    order.revision_root_id.revision_ids
                    .sorted('revision_number', reverse=True)[:1]
                )
                raise UserError(_(
                    "Cannot confirm %s — it has been superseded by a "
                    "newer revision (%s). Confirm the latest revision "
                    "instead.",
                    order.display_name,
                    latest.display_name if latest else _('(unknown)'),
                ))
        return super().action_confirm()
