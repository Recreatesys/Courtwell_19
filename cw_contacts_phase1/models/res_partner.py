import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


# China province codes (2-letter standard administrative abbreviations)
CN_PROVINCES = [
    ('GD', 'Guangdong'),
    ('ZJ', 'Zhejiang'),
    ('JS', 'Jiangsu'),
    ('FJ', 'Fujian'),
    ('SD', 'Shandong'),
    ('SH', 'Shanghai'),
    ('AH', 'Anhui'),
    ('JX', 'Jiangxi'),
    ('HB', 'Hubei'),
    ('SC', 'Sichuan'),
    ('LN', 'Liaoning'),
    ('HE', 'Hebei'),
    ('GX', 'Guangxi'),
    ('YN', 'Yunnan'),
    ('GZ', 'Guizhou'),
    ('HA', 'Henan'),
    ('HN', 'Hunan'),
    ('SX', 'Shanxi'),
    ('SN', 'Shaanxi'),
    ('NM', 'Inner Mongolia'),
    ('XJ', 'Xinjiang'),
    ('QH', 'Qinghai'),
    ('GS', 'Gansu'),
    ('HI', 'Hainan'),
    ('CQ', 'Chongqing'),
    ('TJ', 'Tianjin'),
    ('BJ', 'Beijing'),
    ('JL', 'Jilin'),
    ('HL', 'Heilongjiang'),
    ('NX', 'Ningxia'),
    ('XZ', 'Tibet'),
    ('HK', 'Hong Kong SAR'),
    ('MO', 'Macao SAR'),
    ('TW', 'Taiwan'),
]

# Common non-China supplier countries (ISO 3166-1 alpha-2). Extend as needed.
NON_CN_COUNTRIES = [
    ('VN', 'Vietnam'),
    ('IN', 'India'),
    ('TR', 'Turkey'),
    ('BD', 'Bangladesh'),
    ('TH', 'Thailand'),
    ('MY', 'Malaysia'),
    ('ID', 'Indonesia'),
    ('PH', 'Philippines'),
    ('KH', 'Cambodia'),
    ('PK', 'Pakistan'),
    ('LK', 'Sri Lanka'),
    ('KR', 'South Korea'),
    ('JP', 'Japan'),
    ('IT', 'Italy'),
    ('DE', 'Germany'),
    ('US', 'United States'),
    ('OTHER', 'Other (specify in notes)'),
]

PROVINCE_CODE_SELECTION = CN_PROVINCES + NON_CN_COUNTRIES


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ------------------------------------------------------------------
    # §4.1 — Contact Type Classification
    # ------------------------------------------------------------------
    contact_type = fields.Selection(
        [
            ('client', 'Client'),
            ('supplier', 'Supplier'),
            ('service_provider', 'Service Provider'),
            ('internal', 'Internal'),
        ],
        string='Contact Type',
        index=True,
        tracking=True,
        help='Primary classifier for this contact. Drives field visibility, '
             'role-based access, and downstream sourcing workflows.',
    )

    service_provider_type = fields.Selection(
        [
            ('freight', 'Freight Forwarder'),
            ('inspection', 'Inspection Company'),
            ('customs', 'Customs Broker'),
            ('testing', 'Testing Lab / Certification Body'),
        ],
        string='Service Provider Type',
        help='Visible only when Contact Type = Service Provider.',
    )

    # ------------------------------------------------------------------
    # §4.2 / §5 — Client fields
    # ------------------------------------------------------------------
    client_code = fields.Char(
        string='Client Code',
        size=2,
        index=True,
        copy=False,
        tracking=True,
        help='2 uppercase letters. Assigned by General Manager. Used as a '
             'component of the client-side Reference ID. Must be unique '
             'across all clients.',
    )

    client_tier = fields.Selection(
        [
            ('strategic', 'Strategic'),
            ('active', 'Active'),
            ('occasional', 'Occasional'),
            ('prospect', 'Prospect'),
            ('inactive', 'Inactive'),
        ],
        string='Client Tier',
        tracking=True,
    )

    relationship_since = fields.Date(string='Relationship Since')

    # Primary Market: Odoo's native country_id is reused for ISO alpha-2 country.
    # The "country code for clients" requested in scope = country_id.code (derived).
    primary_market_country_id = fields.Many2one(
        'res.country',
        string='Primary Market',
        help="Client's operating market — where they sell or develop. "
             'Distinct from the HQ registration address country.',
    )
    primary_market_code = fields.Char(
        related='primary_market_country_id.code',
        string='Primary Market Code',
        store=True,
        readonly=True,
    )

    industries_served_ids = fields.Many2many(
        'res.partner.industry',
        'res_partner_client_industry_rel',
        'partner_id', 'industry_id',
        string='Industries Served',
        help="Client's own business sectors — enables category anticipation.",
    )

    gs1_segments_of_interest_ids = fields.Many2many(
        'gpc.segment',
        'res_partner_gpc_segment_interest_rel',
        'partner_id', 'segment_id',
        string='GS1 Segments of Interest',
    )

    gs1_classes_of_interest_ids = fields.Many2many(
        'gpc.class',
        'res_partner_gpc_class_interest_rel',
        'partner_id', 'class_id',
        string='GS1 Classes of Interest',
    )

    typical_order_value = fields.Selection(
        [
            ('lt_10k', 'Under USD 10K'),
            ('10_50k', 'USD 10K – 50K'),
            ('50_100k', 'USD 50K – 100K'),
            ('100_250k', 'USD 100K – 250K'),
            ('250_500k', 'USD 250K – 500K'),
            ('500_1m', 'USD 500K – 1M'),
            ('gt_1m', 'Over USD 1M'),
        ],
        string='Typical Order Value',
    )

    preferred_trade_terms_client = fields.Selection(
        [
            ('exw', 'EXW'),
            ('fob', 'FOB'),
            ('cif', 'CIF'),
            ('dap', 'DAP'),
            ('ddp', 'DDP'),
            ('flex', 'Flexible'),
        ],
        string='Preferred Trade Terms (Client)',
    )

    preferred_currency = fields.Selection(
        [
            ('USD', 'USD'),
            ('HKD', 'HKD'),
            ('EUR', 'EUR'),
            ('RMB', 'RMB'),
            ('OTHER', 'Other'),
        ],
        string='Preferred Currency',
    )

    preferred_communication = fields.Selection(
        [
            ('email', 'Email'),
            ('whatsapp', 'WhatsApp'),
            ('wechat', 'WeChat'),
            ('phone', 'Phone'),
            ('inperson', 'In-Person'),
        ],
        string='Preferred Communication',
    )

    language_preference = fields.Selection(
        [
            ('en', 'English'),
            ('yue', 'Cantonese'),
            ('zh', 'Mandarin'),
            ('ar', 'Arabic'),
            ('fr', 'French'),
            ('other', 'Other'),
        ],
        string='Language Preference',
    )

    decision_making_notes = fields.Text(
        string='Decision-Making Notes',
        help='Who are the real decision-makers, how approval works, '
             'who influences the final call.',
    )
    key_sensitivities = fields.Text(
        string='Key Sensitivities',
        help='Historical sensitivities: price, lead time, QC, documentation, '
             'communication style.',
    )

    # ------------------------------------------------------------------
    # §4.3 / §6 — Supplier fields
    # ------------------------------------------------------------------
    province_code = fields.Selection(
        PROVINCE_CODE_SELECTION,
        string='Province Code',
        index=True,
        tracking=True,
        help='Chinese provincial 2-letter abbreviation, OR ISO 3166-1 alpha-2 '
             'country code for non-China suppliers. Used as a component of '
             'the supplier-side Reference ID.',
    )

    gs1_segments_supplied_ids = fields.Many2many(
        'gpc.segment',
        'res_partner_gpc_segment_supplied_rel',
        'partner_id', 'segment_id',
        string='GS1 Segments Supplied',
    )

    gs1_classes_supplied_ids = fields.Many2many(
        'gpc.class',
        'res_partner_gpc_class_supplied_rel',
        'partner_id', 'class_id',
        string='GS1 Classes Supplied',
    )

    factory_location = fields.Char(
        string='Factory Location',
        help='City and district. Province captured separately in Province Code.',
    )

    vetting_status = fields.Selection(
        [
            ('unvetted', 'Unvetted'),
            ('under_review', 'Under Review'),
            ('approved_t1', 'Approved — Tier 1'),
            ('approved_t2', 'Approved — Tier 2'),
            ('suspended', 'Suspended'),
            ('blacklisted', 'Blacklisted'),
        ],
        string='Vetting Status',
        default='unvetted',
        tracking=True,
        help='CRITICAL: only Tier 1 and Tier 2 should appear in active sourcing '
             'workflows. Domain filters on RFQ supplier lookups will be applied '
             'at the sourcing stage.',
    )

    factory_audit_completed = fields.Boolean(string='Factory Audit Completed')
    factory_audit_date = fields.Date(string='Audit Date')

    moq_range = fields.Selection(
        [
            ('flexible', 'Flexible'),
            ('small', 'Small Batch (under 500 units)'),
            ('medium', 'Medium Batch (500 – 5,000)'),
            ('large', 'Large Batch (5,000+)'),
            ('project', 'Project-Based'),
        ],
        string='MOQ Range',
    )

    typical_lead_time = fields.Selection(
        [
            ('lt_2w', 'Under 2 weeks'),
            ('2_4w', '2 – 4 weeks'),
            ('4_6w', '4 – 6 weeks'),
            ('6_8w', '6 – 8 weeks'),
            ('gt_8w', '8+ weeks'),
        ],
        string='Typical Lead Time',
    )

    preferred_trade_terms_supplier = fields.Selection(
        [
            ('exw', 'EXW'),
            ('fob', 'FOB'),
            ('cif', 'CIF'),
            ('other', 'Other'),
        ],
        string='Preferred Trade Terms (Supplier)',
    )

    payment_terms_accepted_ids = fields.Many2many(
        'cw.payment.term.tag',
        string='Payment Terms Accepted',
    )

    export_license_held = fields.Boolean(
        string='Export License Held',
        help='Particularly relevant for equipment and controlled product categories.',
    )

    certification_ids = fields.Many2many(
        'cw.supplier.certification',
        string='Certifications',
    )

    inspection_access = fields.Selection(
        [
            ('open', 'Open access'),
            ('appt', 'Appointment required'),
            ('restricted', 'Restricted'),
        ],
        string='Inspection Access',
    )

    wechat_id = fields.Char(string='WeChat ID')

    performance_rating = fields.Selection(
        [
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('acceptable', 'Acceptable'),
            ('problematic', 'Problematic'),
            ('do_not_use', 'Do Not Use'),
        ],
        string='Performance Rating',
        tracking=True,
    )

    supplier_notes = fields.Text(string='Supplier Notes')

    # ------------------------------------------------------------------
    # §7 — Service Provider fields
    # ------------------------------------------------------------------
    coverage_market_ids = fields.Many2many(
        'cw.coverage.market',
        string='Coverage Markets',
    )

    services_offered_ids = fields.Many2many(
        'cw.service.offered',
        string='Services Offered',
    )

    preferred_provider = fields.Boolean(
        string='Preferred Provider',
        help="Flag the firm's go-to choice in each service category. "
             'Surfaced first in lookups.',
    )

    rate_notes = fields.Text(string='Rate Notes')
    sp_performance_notes = fields.Text(string='Performance Notes')

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        # Partial unique index implemented via Python constraint below
        # (Odoo SQL constraints don't support WHERE clauses portably)
    ]

    # ------------------------------------------------------------------
    # Python constraints
    # ------------------------------------------------------------------
    @api.constrains('client_code', 'contact_type')
    def _check_client_code(self):
        for rec in self:
            if rec.contact_type == 'client':
                if not rec.client_code:
                    # Empty allowed at create-time; GM populates after import.
                    # Block save only when explicitly empty AND record is being
                    # promoted to active. Per spec: warn but don't hard-block on
                    # initial import. Treated as soft-required at form level
                    # via view attrs.
                    continue
                if not re.fullmatch(r'[A-Z]{2}', rec.client_code):
                    raise ValidationError(
                        'Client Code must be exactly 2 uppercase letters (A–Z).'
                    )
            elif rec.client_code:
                # Non-client contacts must not carry a client code
                raise ValidationError(
                    'Client Code may only be set on contacts of type Client.'
                )

    @api.constrains('client_code', 'contact_type')
    def _check_client_code_unique(self):
        for rec in self:
            if rec.contact_type == 'client' and rec.client_code:
                dup = self.search([
                    ('id', '!=', rec.id),
                    ('contact_type', '=', 'client'),
                    ('client_code', '=', rec.client_code),
                ], limit=1)
                if dup:
                    raise ValidationError(
                        f"Client Code '{rec.client_code}' is already used by "
                        f"'{dup.display_name}'. Codes must be unique across "
                        f'all clients.'
                    )

    @api.constrains('contact_type', 'service_provider_type')
    def _check_service_provider_type(self):
        for rec in self:
            if rec.service_provider_type and rec.contact_type != 'service_provider':
                raise ValidationError(
                    'Service Provider Type may only be set when Contact Type '
                    '= Service Provider.'
                )

    # ------------------------------------------------------------------
    # Onchange / write hooks
    # ------------------------------------------------------------------
    @api.onchange('contact_type')
    def _onchange_contact_type_flags(self):
        """Sync native customer_rank / supplier_rank with contact_type."""
        for rec in self:
            if rec.contact_type == 'client':
                rec.customer_rank = max(rec.customer_rank or 0, 1)
                rec.supplier_rank = 0
            elif rec.contact_type in ('supplier', 'service_provider'):
                rec.customer_rank = 0
                rec.supplier_rank = max(rec.supplier_rank or 0, 1)
            elif rec.contact_type == 'internal':
                rec.customer_rank = 0
                rec.supplier_rank = 0
            if rec.contact_type != 'service_provider':
                rec.service_provider_type = False

    @api.onchange('client_code')
    def _onchange_client_code_uppercase(self):
        for rec in self:
            if rec.client_code:
                rec.client_code = rec.client_code.upper().strip()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('client_code'):
                vals['client_code'] = vals['client_code'].upper().strip()
        records = super().create(vals_list)
        for rec in records:
            rec._sync_native_flags_from_contact_type()
        return records

    def write(self, vals):
        if 'client_code' in vals and vals.get('client_code'):
            vals['client_code'] = vals['client_code'].upper().strip()
        res = super().write(vals)
        if 'contact_type' in vals:
            for rec in self:
                rec._sync_native_flags_from_contact_type()
        return res

    def _sync_native_flags_from_contact_type(self):
        for rec in self:
            if rec.contact_type == 'client':
                if not rec.customer_rank:
                    rec.customer_rank = 1
                rec.supplier_rank = 0
            elif rec.contact_type in ('supplier', 'service_provider'):
                rec.customer_rank = 0
                if not rec.supplier_rank:
                    rec.supplier_rank = 1
            elif rec.contact_type == 'internal':
                rec.customer_rank = 0
                rec.supplier_rank = 0
