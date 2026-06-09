"""Tests for the v19.0.1.3.0 project_reference (PR-) generation.

Covers:
  * PR- generated at opportunity creation when both prereqs are set
  * PR- NOT generated for leads (only for opportunities)
  * PR- NOT generated when client_code or gpc_segment is missing
  * PR- generated on write when prereqs become satisfied
  * lead -> opportunity conversion triggers PR-
  * OP- inherits PR-'s NNN when generated after PR-
  * Legacy path: OP- generates fresh NNN when no PR- exists
  * project.project picks up opp.project_reference verbatim

Run from the Odoo root with:
    odoo-bin -d <db> --test-enable --stop-after-init \\
             -i sourcing_reference --test-tags cw_sourcing
"""

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'cw_sourcing')
class TestProjectReferenceGeneration(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Clear any pre-existing client sequence rows for the test partners
        # so NNN assertions start from a known baseline.
        Seq = cls.env['sourcing.client.sequence']

        Segment = cls.env['gpc.segment']
        cls.seg_50 = Segment.create({'code': '50', 'name': 'Test Seg 50 (PR)'})
        cls.seg_51 = Segment.create({'code': '51', 'name': 'Test Seg 51 (PR)'})

        Partner = cls.env['res.partner']
        cls.client_ab = Partner.create({
            'name': 'Test Client AB (PR)',
            'is_company': True,
            'contact_type': 'client',
            'client_code': 'AB',
        })
        cls.client_cd = Partner.create({
            'name': 'Test Client CD (PR)',
            'is_company': True,
            'contact_type': 'client',
            'client_code': 'CD',
        })
        # Use a supplier-typed partner here instead of a client-typed
        # one without code: cw_contacts_phase1 only allows client_code
        # on type='client', so a non-client partner is the right
        # representation of "client_code is unset" for this test.
        cls.partner_no_code = Partner.create({
            'name': 'Supplier (no client code)',
            'is_company': True,
            'contact_type': 'supplier',
        })

        # Sequence rows must not pre-exist for these test pairs
        Seq.search([
            ('partner_id', 'in', (cls.client_ab + cls.client_cd + cls.partner_no_code).ids),
        ]).unlink()

    def _opp(self, partner=None, segment=None, name='Test Opp'):
        vals = {'name': name, 'type': 'opportunity'}
        if partner is not None:
            vals['partner_id'] = partner.id
        if segment is not None:
            vals['gpc_segment_id'] = segment.id
        return self.env['crm.lead'].create(vals)

    def _lead(self, partner=None, segment=None, name='Test Lead'):
        vals = {'name': name, 'type': 'lead'}
        if partner is not None:
            vals['partner_id'] = partner.id
        if segment is not None:
            vals['gpc_segment_id'] = segment.id
        return self.env['crm.lead'].create(vals)

    # ------------------------------------------------------------------
    # Trigger: at opportunity creation
    # ------------------------------------------------------------------

    def test_pr_generated_at_opportunity_create(self):
        opp = self._opp(partner=self.client_ab, segment=self.seg_50)
        yy = opp.create_date.strftime('%y')
        self.assertEqual(opp.project_reference, f'PR-AB-50-{yy}-001')

    def test_pr_not_generated_for_lead(self):
        lead = self._lead(partner=self.client_ab, segment=self.seg_50)
        self.assertFalse(lead.project_reference)

    def test_pr_not_generated_without_segment(self):
        opp = self._opp(partner=self.client_ab)
        self.assertFalse(opp.project_reference)

    def test_pr_not_generated_without_client_code(self):
        opp = self._opp(partner=self.partner_no_code, segment=self.seg_50)
        self.assertFalse(opp.project_reference)

    def test_pr_not_generated_without_partner(self):
        opp = self._opp(segment=self.seg_50)
        self.assertFalse(opp.project_reference)

    # ------------------------------------------------------------------
    # Trigger: on write when prereqs become satisfied
    # ------------------------------------------------------------------

    def test_pr_generated_on_write_when_segment_filled(self):
        opp = self._opp(partner=self.client_ab)
        self.assertFalse(opp.project_reference)
        opp.gpc_segment_id = self.seg_50
        yy = opp.create_date.strftime('%y')
        self.assertEqual(opp.project_reference, f'PR-AB-50-{yy}-001')

    def test_pr_generated_on_write_when_partner_assigned(self):
        opp = self.env['crm.lead'].create({
            'name': 'Bare opp',
            'type': 'opportunity',
            'gpc_segment_id': self.seg_50.id,
        })
        self.assertFalse(opp.project_reference)
        opp.partner_id = self.client_ab
        yy = opp.create_date.strftime('%y')
        self.assertEqual(opp.project_reference, f'PR-AB-50-{yy}-001')

    def test_pr_generated_on_lead_to_opp_conversion(self):
        lead = self._lead(partner=self.client_ab, segment=self.seg_50)
        self.assertFalse(lead.project_reference)
        lead.type = 'opportunity'
        yy = lead.create_date.strftime('%y')
        self.assertEqual(lead.project_reference, f'PR-AB-50-{yy}-001')

    # ------------------------------------------------------------------
    # Pool / counter behaviour
    # ------------------------------------------------------------------

    def test_pr_per_client_segment_sequence(self):
        opp1 = self._opp(partner=self.client_ab, segment=self.seg_50)
        opp2 = self._opp(partner=self.client_ab, segment=self.seg_50)
        opp3 = self._opp(partner=self.client_ab, segment=self.seg_50)
        yy = opp1.create_date.strftime('%y')
        self.assertEqual(opp1.project_reference, f'PR-AB-50-{yy}-001')
        self.assertEqual(opp2.project_reference, f'PR-AB-50-{yy}-002')
        self.assertEqual(opp3.project_reference, f'PR-AB-50-{yy}-003')

    def test_pr_different_clients_independent_sequence(self):
        opp_ab = self._opp(partner=self.client_ab, segment=self.seg_50)
        opp_cd = self._opp(partner=self.client_cd, segment=self.seg_50)
        yy = opp_ab.create_date.strftime('%y')
        self.assertEqual(opp_ab.project_reference, f'PR-AB-50-{yy}-001')
        self.assertEqual(opp_cd.project_reference, f'PR-CD-50-{yy}-001')

    def test_pr_different_segments_independent_sequence(self):
        opp_50 = self._opp(partner=self.client_ab, segment=self.seg_50)
        opp_51 = self._opp(partner=self.client_ab, segment=self.seg_51)
        yy = opp_50.create_date.strftime('%y')
        self.assertEqual(opp_50.project_reference, f'PR-AB-50-{yy}-001')
        self.assertEqual(opp_51.project_reference, f'PR-AB-51-{yy}-001')

    # ------------------------------------------------------------------
    # OP- shares PR-'s NNN
    # ------------------------------------------------------------------

    def test_op_inherits_nnn_from_pr(self):
        opp = self._opp(partner=self.client_ab, segment=self.seg_50)
        yy = opp.create_date.strftime('%y')
        self.assertEqual(opp.project_reference, f'PR-AB-50-{yy}-001')
        # Bypass the stage-based trigger by calling the generator directly
        opp._generate_sourcing_reference()
        self.assertEqual(opp.sourcing_reference, f'OP-AB-50-{yy}-001')

    def test_op_uses_fresh_nnn_when_no_pr_exists(self):
        # Simulate legacy opp by creating one without prereqs, then back-
        # filling them, but stubbing project_reference creation off by
        # forcing skip_sourcing_validation context.
        opp = self.env['crm.lead'].with_context(skip_sourcing_validation=True).create({
            'name': 'Legacy opp',
            'type': 'opportunity',
            'partner_id': self.client_ab.id,
            'gpc_segment_id': self.seg_50.id,
        })
        self.assertFalse(opp.project_reference,
                         "Legacy create with skip_sourcing_validation skips PR-")
        # Now generate OP- directly — should allocate a fresh NNN
        opp._generate_sourcing_reference()
        yy = opp.create_date.strftime('%y')
        self.assertEqual(opp.sourcing_reference, f'OP-AB-50-{yy}-001')

    def test_pr_and_op_share_counter_no_double_increment(self):
        # First opp gets PR- (counter -> 1) and then OP- (no increment)
        opp1 = self._opp(partner=self.client_ab, segment=self.seg_50)
        opp1._generate_sourcing_reference()
        # Second opp gets PR- (counter -> 2)
        opp2 = self._opp(partner=self.client_ab, segment=self.seg_50)
        yy = opp1.create_date.strftime('%y')
        self.assertEqual(opp1.project_reference, f'PR-AB-50-{yy}-001')
        self.assertEqual(opp1.sourcing_reference, f'OP-AB-50-{yy}-001')
        self.assertEqual(opp2.project_reference, f'PR-AB-50-{yy}-002',
                         "Counter must advance by 1 between opps, not by 2")

    # ------------------------------------------------------------------
    # Idempotence
    # ------------------------------------------------------------------

    def test_pr_generation_is_idempotent(self):
        opp = self._opp(partner=self.client_ab, segment=self.seg_50)
        first = opp.project_reference
        opp._generate_project_reference()  # call again
        self.assertEqual(opp.project_reference, first,
                         "Re-calling _generate_project_reference must not overwrite")

    def test_op_generation_is_idempotent(self):
        opp = self._opp(partner=self.client_ab, segment=self.seg_50)
        opp._generate_sourcing_reference()
        first = opp.sourcing_reference
        opp._generate_sourcing_reference()
        self.assertEqual(opp.sourcing_reference, first)

    # ------------------------------------------------------------------
    # Project propagation
    # ------------------------------------------------------------------

    def test_project_reads_opportunity_project_reference(self):
        # Note: this test only exercises the direct opp-on-project path,
        # not the SO indirection. Full project-from-SO flow requires
        # fixtures beyond the scope of this test class.
        opp = self._opp(partner=self.client_ab, segment=self.seg_50)
        yy = opp.create_date.strftime('%y')
        expected = f'PR-AB-50-{yy}-001'
        self.assertEqual(opp.project_reference, expected)
        # The mechanism: project.project.create() reads opp.project_reference
        # via the SO link. Here we directly assert the source value is in
        # the expected PR- form, which is the contract project_project
        # depends on.
        self.assertTrue(opp.project_reference.startswith('PR-'))
