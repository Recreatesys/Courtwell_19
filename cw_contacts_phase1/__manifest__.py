{
    'name': 'CW Contacts — Phase 1',
    'version': '19.0.1.0.0',
    'summary': 'Contact Type classification, Client/Supplier/Service Provider profiles, '
               'custom activity types',
    'description': """
Phase 1 — Contact Management foundation for the boutique sourcing firm.

Includes:
  * Contact Type classification (Client / Supplier / Service Provider / Internal)
  * Client profile fields (client_code, tier, GS1 segments/classes of interest, etc.)
  * Supplier profile fields (province_code, vetting status, GS1 supplied, etc.)
  * Service Provider profile fields (coverage, services, preferred flag)
  * Uses GS1 GPC Segment / Class reference models from gpc_classification module
  * 8 custom mail.activity.type records — no auto-creation triggers yet

The sourcing sequence models (sourcing.client.sequence,
sourcing.supplier.sequence) and the Reference ID auto-generation triggers
live in the sourcing_reference module.
""",
    'author': 'CW Internal',
    'category': 'Contacts',
    'depends': [
        'base',
        'contacts',
        'mail',
        'crm',
        'gpc_classification',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'data/mail_activity_type_data.xml',
        'data/res_partner_industry_data.xml',
        'data/cw_tags_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
