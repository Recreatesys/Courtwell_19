{
    'name': "CW Quotation Version Control",
    'version': '19.0.1.1.0',
    'category': 'Sales',
    'summary': "Quotation revision tracking on sale.order: Revise button, "
               "supersedes flag, revision chain visible from the CRM opportunity.",
    'description': """
Courtwell — Quotation Version Control
=====================================

Adds revision tracking to sale.order so that quote negotiation cycles
are auditable end-to-end.

Behaviour
---------
* Every sale.order starts at revision_number = 1, no parent.
* On a draft or sent quote, the "Revise Quotation" button:
    - copies the order (preserves lines, partner, etc.)
    - increments revision_number on the new copy
    - sets parent_order_id on the new copy
    - propagates revision_root_id (always points to Rev.1 — used
      for grouping all revisions of one quote together)
    - marks the old order as is_superseded = True (does NOT cancel
      it — original stays visible for comparison)
* Confirming a superseded quote is blocked with an error pointing
  the user at the latest revision.
* The CRM Opportunity's Quotations smart-button list view is
  enhanced with Revision and Latest columns plus a Quote Family
  group-by, so a merchandiser can see all revision chains at once.

Out of scope (deferred)
-----------------------
PDF templates rendering "Rev.N" in the document header. Spec'd
separately.
""",
    'author': 'Courtwell Internal',
    'website': 'https://courtwell.com.hk',
    'depends': [
        'base',
        'sale',
        'sale_management',
        'sale_crm',
        'purchase',
        'sale_purchase',
        # PI fields derive from sourcing_reference's QP- prefix; the
        # dependency is mandatory now that we store the PI ref.
        'sourcing_reference',
    ],
    'data': [
        'views/sale_order_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
