{
    'name': 'CW Sourcing Reference IDs',
    'version': '19.0.1.3.0',
    'summary': 'Auto-generated client/supplier reference IDs, sequence counters, '
               'CRM pipeline stages, and propagation across SO/PO/Project',
    'description': """
Phase 1 — Reference ID Architecture for the boutique sourcing firm.

Implements the spec from §2 and §12.1:
  * sourcing.client.sequence  — cumulative counter per (client, GS1 segment)
  * sourcing.supplier.sequence — pool counter per (province, GS1 segment)
  * sourcing.supplier.pool.member — per-supplier letter + count within a pool
  * crm.lead generator: OP-{ClientCode}-{Segment}-{YY}-{NNN} on entry to Quotation stage
  * sale.order propagation: QP-... (read from lead)
  * purchase.order generator: RQ-{Province}-{Segment}-{Letter}-{NNN},
    flips to PO- on confirm. Letter is per-(province,segment) supplier index
    (A, B, …, Z, AA, AB, …); NNN is RFQ count for that supplier in that pool.
  * crm.lead smart button — RFQs (opens linked POs with default_opportunity_id)
  * project.project Phase 3 hook (stub field PR-... — populated in Phase 3)
  * Client Contact smart button — Orders (non-Lost opportunity count)
  * 8 CRM pipeline stages (Incoming Inquiry, Quotation, Proforma Invoice,
    QC, Enroute, Upsell/Reorder, Lost, On Hold)

Models sourcing.client.sequence and sourcing.supplier.sequence were originally
defined in cw_contacts_phase1; they are migrated here so the reference-ID
architecture is self-contained.

v19.0.1.2.0 — RFQ ID scheme switched from {YY}-{NNN} (pool-wide sequence) to
{Letter}-{NNN} (per-supplier letter + per-supplier RFQ count). Existing RFQs
keep their legacy IDs; new RFQs use the new format.

v19.0.1.3.0 — Project Reference (PR-) generated at opportunity creation
rather than waiting for Quotation / SO / Project. New field
crm.lead.project_reference holds PR-{ClientCode}-{Segment}-{YY}-{NNN}.
Shares the (Client, Segment) sequence with OP-/QP- so all references for
one opportunity have the same NNN. project.project.sourcing_reference now
reads from opp.project_reference directly. Existing opportunities are
backfilled (leads not touched).
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
