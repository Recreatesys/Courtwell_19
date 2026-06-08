"""Tests for supplier pool letter allocation and RFQ ID generation.

Covers the v19.0.1.2.0 reference-ID scheme:
  RQ-{Prov}-{Seg}-{Letter}-{NNN}

Where:
  - Letter is permanent per (supplier × pool); allocated A, B, …, Z, AA…
  - NNN is per-supplier RFQ count within that pool

Run from the Odoo root with:
    odoo-bin -d <db> --test-enable --stop-after-init \\
             -i sourcing_reference --test-tags cw_sourcing
"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'cw_sourcing')
class TestSupplierPoolAllocation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Clear any pre-existing pool / member rows for the (Province, Segment)
        # combos this test class uses. The legacy 19.0.1.1.0 schema kept a
        # cumulative `count` per pool, so a fresh-from-prod DB may already
        # carry e.g. ('GD', '50', count=N) from prior RFQ activity. Wiping
        # only the rows we touch keeps other pool history intact. These
        # deletes are inside the class savepoint and roll back at tearDownClass.
        pool_keys = [('GD', '50'), ('GD', '51'), ('ZJ', '50')]
        Pool = cls.env['sourcing.supplier.sequence']
        Member = cls.env['sourcing.supplier.pool.member']
        for prov, seg in pool_keys:
            domain = [('province_code', '=', prov), ('gpc_segment', '=', seg)]
            Member.search(domain).unlink()
            Pool.search(domain).unlink()

        Segment = cls.env['gpc.segment']
        cls.seg_50 = Segment.create({'code': '50', 'name': 'Test Seg 50'})
        cls.seg_51 = Segment.create({'code': '51', 'name': 'Test Seg 51'})

        Partner = cls.env['res.partner']
        cls.supplier_xyz = Partner.create({
            'name': 'XYZ Manufacturing',
            'is_company': True,
            'province_code': 'GD',
            'supplier_rank': 1,
        })
        cls.supplier_pqr = Partner.create({
            'name': 'PQR Industrial',
            'is_company': True,
            'province_code': 'GD',
            'supplier_rank': 1,
        })
        cls.supplier_abc = Partner.create({
            'name': 'ABC Trading',
            'is_company': True,
            'province_code': 'ZJ',
            'supplier_rank': 1,
        })

        # Product fixture used by tests that need to call button_confirm()
        # (super().button_confirm() requires at least one valid order line).
        cls.product = cls.env['product.product'].create({
            'name': 'Test Widget',
            'type': 'consu',
            'purchase_ok': True,
            'standard_price': 10.0,
        })

    def _make_rfq(self, supplier, segment=None, opportunity=None):
        vals = {'partner_id': supplier.id}
        if segment is not None:
            vals['gpc_segment_id'] = segment.id
        if opportunity is not None:
            vals['opportunity_id'] = opportunity.id
        return self.env['purchase.order'].create(vals)

    def _make_confirmable_rfq(self, supplier, segment=None, opportunity=None):
        """Create an RFQ that has the minimum order-line state needed for
        super().button_confirm() to succeed, so we can exercise the full
        confirmation flow (state transition + prefix flip) end-to-end."""
        vals = {
            'partner_id': supplier.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'product_qty': 1.0,
                'price_unit': 10.0,
            })],
        }
        if segment is not None:
            vals['gpc_segment_id'] = segment.id
        if opportunity is not None:
            vals['opportunity_id'] = opportunity.id
        return self.env['purchase.order'].create(vals)

    # ------------------------------------------------------------------
    # Letter allocation within a single pool
    # ------------------------------------------------------------------

    def test_first_supplier_in_pool_gets_letter_a_count_001(self):
        po = self._make_rfq(self.supplier_xyz, self.seg_50)
        self.assertEqual(po.sourcing_reference, 'RQ-GD-50-A-001')

    def test_second_supplier_same_pool_gets_letter_b(self):
        po1 = self._make_rfq(self.supplier_xyz, self.seg_50)
        po2 = self._make_rfq(self.supplier_pqr, self.seg_50)
        self.assertEqual(po1.sourcing_reference, 'RQ-GD-50-A-001')
        self.assertEqual(po2.sourcing_reference, 'RQ-GD-50-B-001')

    def test_same_supplier_reissued_reuses_letter_increments_count(self):
        po1 = self._make_rfq(self.supplier_xyz, self.seg_50)
        po2 = self._make_rfq(self.supplier_xyz, self.seg_50)
        po3 = self._make_rfq(self.supplier_xyz, self.seg_50)
        self.assertEqual(po1.sourcing_reference, 'RQ-GD-50-A-001')
        self.assertEqual(po2.sourcing_reference, 'RQ-GD-50-A-002')
        self.assertEqual(po3.sourcing_reference, 'RQ-GD-50-A-003')

    def test_letter_stable_when_interleaved_with_other_supplier(self):
        # XYZ takes A, PQR takes B, then XYZ's second RFQ still gets A-002
        # (not jumping to C). Confirms letters are bound to supplier, not
        # to RFQ order.
        po_xyz1 = self._make_rfq(self.supplier_xyz, self.seg_50)
        po_pqr1 = self._make_rfq(self.supplier_pqr, self.seg_50)
        po_xyz2 = self._make_rfq(self.supplier_xyz, self.seg_50)
        po_pqr2 = self._make_rfq(self.supplier_pqr, self.seg_50)
        self.assertEqual(po_xyz1.sourcing_reference, 'RQ-GD-50-A-001')
        self.assertEqual(po_pqr1.sourcing_reference, 'RQ-GD-50-B-001')
        self.assertEqual(po_xyz2.sourcing_reference, 'RQ-GD-50-A-002')
        self.assertEqual(po_pqr2.sourcing_reference, 'RQ-GD-50-B-002')

    # ------------------------------------------------------------------
    # Pool isolation
    # ------------------------------------------------------------------

    def test_different_province_independent_pool(self):
        po_gd = self._make_rfq(self.supplier_xyz, self.seg_50)
        po_zj = self._make_rfq(self.supplier_abc, self.seg_50)
        self.assertEqual(po_gd.sourcing_reference, 'RQ-GD-50-A-001')
        self.assertEqual(po_zj.sourcing_reference, 'RQ-ZJ-50-A-001')

    def test_different_segment_independent_pool(self):
        po_50 = self._make_rfq(self.supplier_xyz, self.seg_50)
        po_51 = self._make_rfq(self.supplier_xyz, self.seg_51)
        # Same supplier, different segment → letter is allocated per pool,
        # so XYZ is "A" in both pools (they're independent number-spaces).
        self.assertEqual(po_50.sourcing_reference, 'RQ-GD-50-A-001')
        self.assertEqual(po_51.sourcing_reference, 'RQ-GD-51-A-001')

    # ------------------------------------------------------------------
    # Validation guards
    # ------------------------------------------------------------------

    def test_missing_province_blocks_id_generation(self):
        supplier_no_prov = self.env['res.partner'].create({
            'name': 'No-Province Supplier',
            'is_company': True,
            'supplier_rank': 1,
        })
        po = self.env['purchase.order'].create({
            'partner_id': supplier_no_prov.id,
            'gpc_segment_id': self.seg_50.id,
        })
        # create() swallows the UserError so the draft PO still exists,
        # but no reference was generated.
        self.assertFalse(po.sourcing_reference)
        with self.assertRaises(UserError):
            po._generate_supplier_reference()

    def test_missing_segment_blocks_id_generation(self):
        po = self.env['purchase.order'].create({
            'partner_id': self.supplier_xyz.id,
        })
        self.assertFalse(po.sourcing_reference)
        with self.assertRaises(UserError):
            po._generate_supplier_reference()

    # ------------------------------------------------------------------
    # Opportunity inheritance
    # ------------------------------------------------------------------

    def test_segment_inherited_from_opportunity(self):
        client = self.env['res.partner'].create({'name': 'Client AB'})
        opp = self.env['crm.lead'].create({
            'name': 'Test Opp',
            'type': 'opportunity',
            'partner_id': client.id,
            'gpc_segment_id': self.seg_50.id,
        })
        # gpc_segment_id deliberately omitted — must be inherited from opp
        po = self._make_rfq(self.supplier_xyz, opportunity=opp)
        self.assertEqual(po.gpc_segment_id, self.seg_50)
        self.assertEqual(po.sourcing_reference, 'RQ-GD-50-A-001')

    def test_opportunity_smart_button_count(self):
        client = self.env['res.partner'].create({'name': 'Client AB'})
        opp = self.env['crm.lead'].create({
            'name': 'Test Opp',
            'type': 'opportunity',
            'partner_id': client.id,
            'gpc_segment_id': self.seg_50.id,
        })
        self.assertEqual(opp.purchase_order_count, 0)
        self._make_rfq(self.supplier_xyz, opportunity=opp)
        self._make_rfq(self.supplier_pqr, opportunity=opp)
        opp.invalidate_recordset(['purchase_order_ids', 'purchase_order_count'])
        self.assertEqual(opp.purchase_order_count, 2)

    # ------------------------------------------------------------------
    # Confirmation flip RQ → PO (end-to-end via real button_confirm)
    # ------------------------------------------------------------------

    def test_button_confirm_flips_rq_to_po_end_to_end(self):
        po = self._make_confirmable_rfq(self.supplier_xyz, self.seg_50)
        self.assertEqual(po.state, 'draft')
        self.assertEqual(po.sourcing_reference, 'RQ-GD-50-A-001')

        po.button_confirm()

        self.assertEqual(po.state, 'purchase',
                         "button_confirm() must advance state via super()")
        self.assertEqual(po.sourcing_reference, 'PO-GD-50-A-001',
                         "Prefix must flip RQ- → PO-, body preserved")

    def test_button_confirm_generates_reference_if_missing(self):
        # Edge case: RFQ created without segment (so create() skipped ID
        # generation), segment filled in later, then confirmed. The
        # confirm path must generate the reference before flipping.
        po = self.env['purchase.order'].create({
            'partner_id': self.supplier_xyz.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'product_qty': 1.0,
                'price_unit': 10.0,
            })],
        })
        self.assertFalse(po.sourcing_reference,
                         "No segment at create → no reference yet")

        po.gpc_segment_id = self.seg_50
        po.button_confirm()

        self.assertEqual(po.state, 'purchase')
        self.assertEqual(po.sourcing_reference, 'PO-GD-50-A-001',
                         "Confirmation must generate, then flip in one step")

    # ------------------------------------------------------------------
    # Pool / member row state
    # ------------------------------------------------------------------

    def test_pool_and_member_rows_created_correctly(self):
        self._make_rfq(self.supplier_xyz, self.seg_50)
        self._make_rfq(self.supplier_pqr, self.seg_50)
        self._make_rfq(self.supplier_xyz, self.seg_50)

        pool = self.env['sourcing.supplier.sequence'].search([
            ('province_code', '=', 'GD'),
            ('gpc_segment', '=', '50'),
        ])
        self.assertEqual(len(pool), 1)
        self.assertEqual(pool.next_letter_index, 2,
                         "Two distinct suppliers in pool → next index is 2")
        self.assertEqual(pool.count, 3, "Three RFQs total in pool")

        member_xyz = self.env['sourcing.supplier.pool.member'].search([
            ('province_code', '=', 'GD'),
            ('gpc_segment', '=', '50'),
            ('partner_id', '=', self.supplier_xyz.id),
        ])
        self.assertEqual(member_xyz.letter, 'A')
        self.assertEqual(member_xyz.count, 2)

        member_pqr = self.env['sourcing.supplier.pool.member'].search([
            ('province_code', '=', 'GD'),
            ('gpc_segment', '=', '50'),
            ('partner_id', '=', self.supplier_pqr.id),
        ])
        self.assertEqual(member_pqr.letter, 'B')
        self.assertEqual(member_pqr.count, 1)


@tagged('post_install', '-at_install', 'cw_sourcing')
class TestLetterEncoding(TransactionCase):
    """Boundary tests for the index → letter mapping."""

    def test_letter_encoding_boundaries(self):
        Member = self.env['sourcing.supplier.pool.member']
        cases = [
            (0,   'A'),
            (1,   'B'),
            (25,  'Z'),
            (26,  'AA'),
            (27,  'AB'),
            (51,  'AZ'),
            (52,  'BA'),
            (701, 'ZZ'),
        ]
        for idx, expected in cases:
            with self.subTest(idx=idx):
                self.assertEqual(Member._index_to_letter(idx), expected)

    def test_letter_encoding_rejects_out_of_range(self):
        Member = self.env['sourcing.supplier.pool.member']
        with self.assertRaises(ValueError):
            Member._index_to_letter(-1)
        with self.assertRaises(ValueError):
            Member._index_to_letter(702)
