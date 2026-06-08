{
    'name': 'Courtwell CRM Access (Accounting Viewer)',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': "Stage-gated CRM opportunity read-only access for the Accounting group",
    'description': """
Courtwell CRM Access — Accounting Viewer
========================================

Defines a security group **Accounting / CRM Viewer (Post-Proforma)** whose
members can read opportunities once they reach the Proforma Invoice stage.
Visibility is restricted to four pipeline stages:

* Proforma Invoice
* QC
* Enroute
* Upsell/Reorder

Pure read-only by design
------------------------
This module is a strict CRM viewer. No create, write, or unlink on any
model. Hilda's deposit-confirmation action lives elsewhere — she flips
``sale.order.cw_deposit_received`` (owned by ``cw_shipping_workflow``)
using the write permission she already has via
``account.group_account_user`` (Bookkeeper). The flag's
``cw_deposit_confirmed_by`` and ``cw_deposit_received_date`` are auto-set
on flip; chatter tracking on the SO is the audit trail.

ACL is declared from scratch in ``security/ir.model.access.csv`` (no
inheritance of ``sales_team.group_sale_salesman``) so create and unlink
on ``crm.lead`` are hard-denied. Read is granted on:

* ``crm.lead`` (rule-gated to the four stages above)
* ``crm.stage``, ``crm.team``, ``crm.tag``, ``crm.lost.reason``,
  ``crm.recurring.plan`` — opportunity form rendering
* ``utm.source``, ``utm.medium``, ``utm.campaign`` — marketing field
  display

``sale.order`` is intentionally **not** covered here — Bookkeeper already
grants Accounting users full read+write on every SO in the company.

Record rule
-----------
``ir.rule`` on ``crm.lead`` for the group, ``domain_force`` built at
module-load time via ``eval`` so the ``sourcing_reference.crm_stage_*``
XML IDs resolve to integer stage IDs. If a stage record is recreated,
reload this module (``-u cw_crm_access``).

Why named XML IDs (not ``stage_id.sequence >= 3``)
--------------------------------------------------
The recommended pattern for named-stage rules is XML-ID anchors, which
survive stage renames and sequence re-shuffles. ``cw_shipping_workflow``
uses positional ``sequence >= 3`` which silently includes Lost (seq 7)
and On Hold (seq 8); this module excludes both — Accounting has no
workflow on Lost or On Hold opps.

Assignment
----------
Assigning users to the group is left to the administrator (UI:
Settings → Users → select user → Other → Sales → tick "Accounting / CRM
Viewer (Post-Proforma)"). The module does not pin specific users.
""",
    'author': 'Courtwell Internal',
    'website': 'https://courtwell.com.hk',
    'depends': [
        'crm',
        'sales_team',
        'utm',
        'sourcing_reference',
    ],
    'data': [
        'security/cw_crm_access_security.xml',
        'security/ir.model.access.csv',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
