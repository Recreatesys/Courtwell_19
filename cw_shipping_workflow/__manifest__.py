{
    'name': "Courtwell Shipping Workflow",
    'version': '19.0.1.1.0',
    'summary': "Pipeline-gated shipping coordination for Aris (Shipping Dept): "
               "auto-create draft shipments on Proforma Invoice, deposit gate, QC-anchored booking deadline.",
    'description': """
Courtwell Shipping Workflow
===========================

Sits on top of ``cw_shipment`` + ``sourcing_reference`` to drive the
Shipping Department user's (Aris) workflow off CRM pipeline stage
transitions.

Phases mapped to existing pipeline stages
-----------------------------------------
* Stage 3 (Proforma Invoice) — auto-creates a draft ``cw.shipment``
  linked to the opportunity; assigns the Shipping responsible user
  and schedules an activity "Request freight forwarder spot rates".
* Hilda (Accounting) ticks ``cw_deposit_received`` on the related
  ``sale.order`` — this schedules an activity on the shipment for
  Aris: "Coordinate packing list / CBM / crate sizes".
* QC inspection date set on a ``project.task`` (with
  ``cw_is_qc_inspection`` flagged) computes a shipping booking
  deadline of QC date − 7 days and schedules a deadline activity on
  the shipment. A daily cron warns when the deadline is within 2 days
  and the shipment is not yet booked.

Security
--------
Adds group ``Shipping / User`` with restrictive record rules:
* ``crm.lead``: read only opportunities at stage sequence >= 3.
* ``sale.order``: read only SOs whose opportunity passes the same
  gate (or that have no opportunity).

Post-install setup (manual)
---------------------------
After install, the admin must:
1. Add Aris (shipping@courtwell.com.hk, uid 11) to
   ``cw_shipping_workflow.group_shipping_user``.
2. Remove Aris from ``sales_team.group_sale_salesman_all_leads``
   (the "User: All Documents" group) — otherwise its broad read
   access OR-overrides this module's stage-gated rules.
""",
    'author': "Courtwell",
    'category': 'Inventory/Purchase',
    'license': 'LGPL-3',
    'depends': [
        'cw_shipment',
        'sourcing_reference',
        'crm_project_assign',
        'sale_crm',
        'sale_management',
        'project',
        'mail',
    ],
    'data': [
        'security/cw_shipping_workflow_groups.xml',
        'security/ir.model.access.csv',
        'security/cw_shipping_workflow_rules.xml',
        'data/mail_activity_type_data.xml',
        'data/ir_cron.xml',
        'views/cw_shipment_views.xml',
        'views/crm_lead_views.xml',
        'views/sale_order_views.xml',
        'views/project_task_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
