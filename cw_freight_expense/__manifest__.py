{
    'name': "CW Freight Expense Capture",
    'version': '19.0.1.1.0',
    'category': 'Inventory/Purchase',
    'summary': "Aris-facing freight cost decomposition on cw.shipment + "
               "auto-posting to Expense app with project analytic linkage.",
    'description': """
Courtwell — Freight Cost Capture & Expense Posting
==================================================

Extends cw.shipment with 8 decomposed freight cost fields (Inland
Transport, Export Clearance, Customs Filing, BL Fee, Certificate of
Origin, Documentation Other, Port Fees, Actual Freight). When Aris
finalises a freight booking, the breakdown is posted as one
hr.expense record per non-zero category, all tagged with the linked
project's analytic account.

Cost flow
---------
cw.shipment.action_finalize_freight()
   --> creates 1..8 hr.expense records (one per non-zero category)
   --> each carries analytic_distribution pointing at the linked
       project.project.account_id
   --> Expense app shows them under Freight expense products
   --> Project cost dashboard rolls them up via the analytic account
   --> sale.order Profitability tab picks up the same costs via the
       same analytic account (sale_project linkage)

Import duties are explicitly NOT captured here — clients' customs
brokers handle import-side duties on their own.

Quote-version control is delivered separately in cw_quote_revision.
""",
    'author': 'Courtwell Internal',
    'website': 'https://courtwell.com.hk',
    'depends': [
        'base',
        'mail',
        'hr_expense',
        'analytic',
        'project',
        'project_account',
        'cw_shipment',
        'cw_shipping_workflow',
    ],
    'data': [
        'data/freight_expense_products.xml',
        'views/cw_shipment_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
