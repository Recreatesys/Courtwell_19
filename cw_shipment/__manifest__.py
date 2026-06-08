{
    'name': "Courtwell Shipment Tracking",
    'version': '19.0.1.0.0',
    'summary': "Track inbound shipments: PI, containers, vessel, ETD/ETA, carrier, BL",
    'description': """
Courtwell Shipment Tracking
===========================

Header/lines model for inbound shipments:

* ``cw.shipment`` — one record per PI No. (customer, supplier, freight, dates,
  invoice).
* ``cw.shipment.container`` — one line per physical container (size, CNTR No.,
  BL No., vessel, ETD/ETA).
* ``cw.port`` — master list of ports of loading and destination ports.

Partners (client/supplier/forwarder/carrier) are linked to existing
``res.partner`` records. Forwarders and carriers are tagged with the
"Service Provider" partner category (auto-seeded if missing).
""",
    'category': 'Inventory/Purchase',
    'license': 'LGPL-3',
    'depends': [
        'mail',
        'contacts',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/res_partner_category_data.xml',
        'data/cw_port_data.xml',
        'views/cw_port_views.xml',
        'views/cw_shipment_views.xml',
        'views/cw_shipment_menus.xml',
    ],
    'installable': True,
    'application': True,
}
