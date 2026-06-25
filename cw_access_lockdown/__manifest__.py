{
    'name': 'CW Access Lockdown',
    'version': '19.0.1.0.0',
    'category': 'Hidden',
    'summary': "Restrict the Shipments + CW Sourcing top-level menus to "
               "authorised users only. Menu visibility only; model-level "
               "access is unchanged so cross-module workflows continue.",
    'description': """
Courtwell — Access Lockdown
===========================

Owns the menu-visibility policy for two operational clusters that
should not be browseable by everyone:

* **Shipments** (cw_shipment.menu_cw_shipment_root) — locked to
  cw_shipping_workflow.group_shipping_user.
  Members after install: Aris, Eva, Howard.

* **CW Sourcing** (sourcing_reference.menu_sourcing_root) — locked to
  the new cw_access_lockdown.group_sourcing_manager.
  Members after install: Eva, Howard.

What this module does NOT do
----------------------------
This is **menu visibility only**. Model-level access (ir.model.access)
on cw.shipment, cw.shipment.container, cw.port, cw.shipment.freight.quote,
sourcing.client.sequence, sourcing.supplier.sequence, sourcing.supplier.
pool.member, sourcing.inspection, etc. is **unchanged**. That keeps
the cross-module workflows working for everyone:

  * Abby's opportunity-stage move to Proforma Invoice still auto-creates
    a draft cw.shipment (via cw_shipping_workflow.crm_lead.write).
  * Hilda's deposit-received tick on the sale order still notifies
    Aris via the existing activity rule.
  * Every form on purchase.order and crm.lead still renders the
    OP-/QP-/RQ-/PO- references it reads from sourcing.client.sequence
    and sourcing.supplier.sequence.

Side channels
-------------
A smart button on crm.lead that opens cw.shipment for a specific
opportunity will still open if clicked — the menu lockdown only
removes the navigation entry, not access to specific records.
That's the intended behaviour for the Recommended option of
"menu visibility only" in the access-policy design.
""",
    'author': 'Courtwell Internal',
    'website': 'https://courtwell.com.hk',
    'depends': [
        'base',
        'cw_shipment',
        'cw_shipping_workflow',
        'sourcing_reference',
    ],
    'data': [
        'security/cw_access_lockdown_groups.xml',
        'views/menu_lockdown.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
