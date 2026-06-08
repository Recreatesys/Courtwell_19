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
        help='Format: RQ-{Province}-{Segment}-{Letter}-{NNN} while in RFQ; '
             'flips to PO- on confirmation. Letter is the supplier\'s permanent '
             'index within the (Province, Segment) pool (A, B, …, Z, AA, AB, …); '
             'NNN is the per-supplier RFQ count in that pool.',
    )

    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        index=True,
        ondelete='restrict',
        tracking=True,
        help='CRM opportunity this RFQ/PO serves. Auto-populated when the RFQ '
             'is created via the smart button on a CRM Opportunity. Drives '
             'inheritance of GS1 Segment from the opportunity.',
    )

    gpc_segment_id = fields.Many2one(
        'gpc.segment',
        string='GS1 Segment',
        index=True,
        tracking=True,
        help='GS1 GPC Segment for this RFQ/PO. Inherited from linked Opportunity '
             'where applicable; entered manually for standalone RFQs.',
    )

    def _inherit_segment_from_opportunity(self):
        """Fill `gpc_segment_id` from the linked opportunity if not set."""
        self.ensure_one()
        if self.gpc_segment_id or not self.opportunity_id:
            return
        if self.opportunity_id.gpc_segment_id:
            self.gpc_segment_id = self.opportunity_id.gpc_segment_id

    def _generate_supplier_reference(self):
        """Generate RQ-{prov}-{seg}-{letter}-{NNN} for this RFQ.

        Letter is allocated once per (supplier × pool) and reused on every
        subsequent RFQ to that supplier in that pool. NNN is the per-supplier
        count in the pool, incrementing per RFQ.

        Concurrency: SELECT … FOR UPDATE on the pool row serializes letter
        allocation; a second FOR UPDATE on the member row serializes count
        increments for the same supplier.
        """
        self.ensure_one()
        if self.sourcing_reference:
            return

        partner = self.partner_id
        prov = (partner.province_code or '').strip().upper() if partner else ''
        if not prov or len(prov) != 2 or not prov.isalpha():
            raise UserError(_(
                "Province Code missing on this supplier record (%(name)s). "
                "Update the supplier profile before issuing an RFQ.",
                name=partner.display_name if partner else '—',
            ))

        if not self.gpc_segment_id or not self.gpc_segment_id.code:
            raise UserError(_(
                "GS1 Segment must be set on the RFQ "
                "(inherited from the linked Opportunity, or selected manually)."
            ))
        seg = self.gpc_segment_id.code

        Pool = self.env['sourcing.supplier.sequence'].sudo()
        Member = self.env['sourcing.supplier.pool.member'].sudo()

        pool = Pool.search([
            ('province_code', '=', prov),
            ('gpc_segment', '=', seg),
        ], limit=1)
        if not pool:
            pool = Pool.create({
                'province_code': prov,
                'gpc_segment': seg,
                'count': 0,
                'next_letter_index': 0,
            })

        # Flush any pending ORM writes (pool/member updates from a prior
        # RFQ in the same transaction, or the Pool.create() just above)
        # so the raw SELECT FOR UPDATE below reads the latest values from
        # the database, not stale ORM cache. Required for correctness when
        # multiple RFQs are created in one DB transaction.
        self.env.flush_all()

        # Lock the pool row to serialize letter allocation and pool count.
        self.env.cr.execute(
            "SELECT next_letter_index, count "
            "FROM sourcing_supplier_sequence WHERE id = %s FOR UPDATE",
            (pool.id,),
        )
        pool_row = self.env.cr.fetchone()
        next_idx = pool_row[0] if pool_row else 0
        pool_count = pool_row[1] if pool_row else 0

        member = Member.search([
            ('province_code', '=', prov),
            ('gpc_segment', '=', seg),
            ('partner_id', '=', partner.id),
        ], limit=1)

        if member:
            # Existing supplier in this pool — reuse letter, bump count.
            self.env.cr.execute(
                "SELECT count FROM sourcing_supplier_pool_member "
                "WHERE id = %s FOR UPDATE",
                (member.id,),
            )
            member_row = self.env.cr.fetchone()
            new_member_count = (member_row[0] if member_row else 0) + 1
            member.write({'count': new_member_count})
            letter = member.letter
        else:
            # First RFQ to this supplier in this pool — allocate next letter.
            letter = Member._index_to_letter(next_idx)
            member = Member.create({
                'province_code': prov,
                'gpc_segment': seg,
                'partner_id': partner.id,
                'letter': letter,
                'count': 1,
            })
            new_member_count = 1
            pool.write({'next_letter_index': next_idx + 1})

        pool.write({'count': pool_count + 1})

        ref = f"RQ-{prov}-{seg}-{letter}-{new_member_count:03d}"
        self.sourcing_reference = ref
        self.message_post(body=_("Sourcing Reference generated: %s") % ref)
        _logger.info(
            "purchase.order %s: generated sourcing_reference %s "
            "(pool=%s-%s, supplier=%s, letter=%s, supplier_count=%s)",
            self.id, ref, prov, seg, partner.display_name, letter, new_member_count,
        )

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.sourcing_reference:
                continue
            order._inherit_segment_from_opportunity()
            if (
                order.partner_id
                and order.partner_id.province_code
                and order.gpc_segment_id
            ):
                try:
                    order._generate_supplier_reference()
                except UserError:
                    # Missing province/segment surfaces again at confirmation.
                    pass
        return orders

    def button_confirm(self):
        for order in self:
            if not order.sourcing_reference:
                order._inherit_segment_from_opportunity()
                order._generate_supplier_reference()
            # Always flip RQ- → PO- on confirmation, whether the reference
            # was pre-existing or just generated above.
            if order.sourcing_reference and order.sourcing_reference.startswith('RQ-'):
                order.sourcing_reference = 'PO-' + order.sourcing_reference[3:]
        return super().button_confirm()