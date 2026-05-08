{
    'name': 'CW Sourcing Reference IDs',
    'version': '19.0.1.0.0',
    'summary': 'Auto-generated client/supplier reference IDs, sequence counters, '
               'CRM pipeline stages, and propagation across SO/PO/Project',
    'description': """
Phase 1 — Reference ID Architecture for the boutique sourcing firm.

Implements the spec from §2 and §12.1:
  * sourcing.client.sequence  — cumulative counter per (client, GS1 segment)
  * sourcing.supplier.sequence — cumulative counter per (province, GS1 segment)
  * crm.lead generator: OP-{ClientCode}-{Segment}-{YY}-{NNN} on Incoming Inquiry exit
  * sale.order propagation: QP-... (read from lead)
  * purchase.order generator/propagation: RQ-{Province}-{Segment}-{YY}-{NNN}, flips to PO- on confirm
  * project.project Phase 3 hook (stub field PR-... — populated in Phase 3)
  * Client Contact smart button — Orders (non-Lost opportunity count)
  * 9 CRM pipeline stages (Incoming Inquiry, Sourcing, Quotation, Proforma Invoice,
    QC, Enroute, Upsell/Reorder, Lost, On Hold)

Models sourcing.client.sequence and sourcing.supplier.sequence were originally
defined in cw_contacts_phase1; they are migrated here so the reference-ID
architecture is self-contained.
""",
    'author': 'CW Internal',
    'category': 'Sales/CRM',
    'depends': [
        'base',
        'mail',
        'crm',
        'sale_management',
        'purchase',
        'project',
        'gpc_classification',
        'cw_contacts_phase1',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/crm_stage_data.xml',
        'views/sourcing_sequence_views.xml',
        'views/crm_lead_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/res_partner_views.xml',
        'views/project_project_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
}
