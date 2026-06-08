{
    'name': "CW Sourcing Inspection (QC)",
    'version': '19.0.1.3.0',
    'category': 'Inventory/Purchase',
    'summary': "Pre-shipment / DUPRO / factory inspection records — "
               "English-language equivalent of Courtwell's existing "
               "Chinese paper QC form, with project/PO/SO linkage.",
    'description': """
Courtwell — Sourcing Inspection (QC)
====================================

Captures pre-shipment inspections in structured form, replacing the
existing Chinese paper inspection report. Designed to match the actual
checklist structure used in the field (6 inspection categories with
sub-item booleans + per-section pass/fail), plus:

* Per-SKU detail grid (Item No., Ordered Qty, Sampled Qty, outcome)
* Free-text inspection comments + improvement notes
* Final 4-state outcome (Pass / Rework / Fail / Pending)
* Linkage to project, sale order, purchase order, supplier
* Re-inspection chain via parent_inspection_id
* Inspection cost field (flows to project analytic via same pattern
  as cw_freight_expense, when an inspection_cost is entered)
* Chatter for photos + report attachments + back-and-forth comments

Deliberately omitted (future iterations)
----------------------------------------
* AQL sampling fields + defect-count tracking (the paper form doesn't
  use them; add when statistical QC discipline is introduced)
* PDF report template matching the form layout (separate iteration)
* Email templates for inspection request / result notification
* Project-stage gate enforcement (e.g. Failed blocks Goods Ready)
""",
    'author': 'Courtwell Internal',
    'website': 'https://courtwell.com.hk',
    'depends': [
        'base',
        'mail',
        'contacts',
        'crm',
        'sale_management',
        'purchase',
        'project',
        'project_account',
        'hr_expense',
        'analytic',
        'cw_contacts_phase1',
        'sourcing_reference',
    ],
    'data': [
        'security/cw_sourcing_inspection_groups.xml',
        'security/ir.model.access.csv',
        'security/cw_sourcing_inspection_rules.xml',
        'data/sourcing_inspection_sequence_data.xml',
        'data/sourcing_inspection_expense_product_data.xml',
        'reports/sourcing_inspection_report.xml',
        'reports/sourcing_inspection_report_templates.xml',
        'views/sourcing_inspection_views.xml',
        'views/sourcing_inspection_dashboard_views.xml',
        'views/sourcing_inspection_menus.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
