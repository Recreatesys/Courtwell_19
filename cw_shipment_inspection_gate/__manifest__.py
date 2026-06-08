{
    'name': "CW Shipment Inspection Gate",
    'version': '19.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': "Block cw.shipment from progressing past Booked unless "
               "every linked inspection has been cleared for loading "
               "by the merchandiser.",
    'description': """
Courtwell — Shipment / Inspection Gate
======================================

Bridge module connecting cw_sourcing_inspection to cw_shipment.

Behaviour
---------
* Resolves the set of inspections linked to a shipment by walking
  cw.shipment.sale_order_id and cw.shipment.container_ids.sale_order_id
  back to sourcing.inspection.sale_order_id.
* Adds an inspection_ids computed field + inspection-status banner +
  smart-button count on the shipment form.
* On status transition past 'booked' (shipped / arrived / delivered),
  raises UserError if any linked inspection is not in
  merchandiser_decision == 'load_for_shipping'.

The check only fires when there ARE linked inspections. Shipments
without any inspections (e.g. legacy data or simple deliveries) pass
through unchanged.

GM bypass: members of base.group_system can force a transition by
setting context key 'bypass_inspection_gate=True' on the write call.
""",
    'author': 'Courtwell Internal',
    'website': 'https://courtwell.com.hk',
    'depends': [
        'base',
        'mail',
        'cw_shipment',
        'cw_sourcing_inspection',
    ],
    'data': [
        'views/cw_shipment_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
