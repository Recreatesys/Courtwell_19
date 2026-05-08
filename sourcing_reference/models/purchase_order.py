import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    sourcing_reference = fields.Char(
        string='Sourcing Ref',
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        help='Format: RQ-{Province}-{Segment}-{YY}-{NNN} while in RFQ; '
             'flips to PO- on confirmation. If linked to a Sale Order with '
             'an existing reference, inherits that reference with PO- prefix.',
    )

    gpc_segment_id = fields.Many2one(
        'gpc.segment',
        string='GS1 Segment',
        index=True,
        tracking=True,
        help='GS1 GPC Segment for this RFQ/PO. Inherited from linked Opportunity '
             'where applicable; entered manually for standalone RFQs.',
    )

    def _resolve_so_origin(self):
        """Return the originating sale.order for this PO, if any.

        Looks up via auto-created PO origin link (purchase.order_id field
        on sale.order in standard Odoo, or purchase.order.origin string).
        """
        self.ensure_one()
        Sale = self.env['sale.order']
        so = Sale.search([('name', '=', self.origin)], limit=1) if self.origin else Sale
        return so

    def _try_inherit_from_so(self):
        self.ensure_one()
        if self.sourcing_reference:
            return False
        so = self._resolve_so_origin()
        if not so or not so.sourcing_reference:
            return False
        base = so.sourcing_reference.strip()
        if base.startswith('QP-'):
            self.sourcing_reference = 'PO-' + base[3:]
            if not self.gpc_segment_id and so.opportunity_id and so.opportunity_id.gpc_segment_id:
                self.gpc_segment_id = so.opportunity_id.gpc_segment_id
            return True
        return False

    def _generate_supplier_reference(self):
        """Generate RQ-{prov}-{seg}-{YY}-{NNN} for standalone RFQs.

        Validates province_code on supplier and gpc_segment_id on order.
        Concurrency-safe via row-level lock on the sequence row.
        """
        self.ensure_one()
        if self.sourcing_reference:
            return
        partner = self.partner_id
        prov = (partner.province_code or '').strip().upper() if partner else ''
        if not prov or len(prov) != 2 or not prov.isalpha():
            raise UserError(_(
                "Province Code missing on this supplier record (%(name)s). "
                "Update the supplier profile before issuing an RFQ."
            ) % {'name': partner.display_name if partner else '—'})

        if not self.gpc_segment_id or not self.gpc_segment_id.code:
            raise UserError(_(
                "GS1 Segment must be set on the RFQ "
                "(inherited from the linked Opportunity, or selected manually)."
            ))
        seg = self.gpc_segment_id.code

        Seq = self.env['sourcing.supplier.sequence'].sudo()
        seq = Seq.search([
            ('province_code', '=', prov),
            ('gpc_segment', '=', seg),
        ], limit=1)
        if seq:
            self.env.cr.execute(
                "SELECT count FROM sourcing_supplier_sequence WHERE id = %s FOR UPDATE",
                (seq.id,),
            )
            row = self.env.cr.fetchone()
            new_count = (row[0] if row else 0) + 1
            seq.write({'count': new_count})
        else:
            seq = Seq.create({
                'province_code': prov,
                'gpc_segment': seg,
                'count': 1,
            })
            new_count = 1

        yy = fields.Date.context_today(self).strftime('%y')
        self.sourcing_reference = f"RQ-{prov}-{seg}-{yy}-{new_count:03d}"
        self.message_post(body=_("Sourcing Reference generated: %s") % self.sourcing_reference)

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.sourcing_reference:
                continue
            if order._try_inherit_from_so():
                continue
            if order.partner_id and order.partner_id.province_code and order.gpc_segment_id:
                try:
                    order._generate_supplier_reference()
                except UserError:
                    pass
        return orders

    def button_confirm(self):
        for order in self:
            if not order.sourcing_reference:
                order._try_inherit_from_so()
                if not order.sourcing_reference:
                    order._generate_supplier_reference()
            elif order.sourcing_reference.startswith('RQ-'):
                order.sourcing_reference = 'PO-' + order.sourcing_reference[3:]
        return super().button_confirm()
