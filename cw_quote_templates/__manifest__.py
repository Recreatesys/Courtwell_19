{
    'name': 'CW Quote Templates',
    'version': '19.0.1.2.0',
    'category': 'Sales/CRM',
    'summary': "Four sale.order.templates + three customer-facing email "
               "variants for Courtwell's standard quoting patterns "
               "(China custom merch, reorder, sample, strategic pricing).",
    'description': """
Courtwell — Quotation Templates Pack
====================================

Adds four `sale.order.template` records covering Courtwell's recurring
quoting patterns, and three matching `mail.template` variants that
preserve the cw_debrand styling (no portal CTA, reply-to-email, user
signature footer).

Templates
---------
* **CW China Custom Merch** — the default for new custom-branded
  merchandise from a China factory. 14-day validity, 50% deposit,
  artwork/qty-TBC default note.
* **CW Reorder (Existing SKU)** — repeat order on a customer-approved
  SKU. 7-day validity, 50% deposit, references prior PI.
* **CW Sample Request** — paid pre-production sample. 30-day validity,
  100% prepayment (sample fee non-refundable).
* **CW Special Pricing (Strategic)** — GM-cleared margin deals. 7-day
  validity, 50% deposit, "not a precedent" disclaimer.

Email templates
---------------
* **CW: Quote — first send** — default for new quotes. cw_debrand-
  aligned body (no portal CTA, merchandiser signature).
* **CW: Quote — gentle follow-up** — sent N days after first send if
  the customer hasn't responded. References validity expiry.
* **CW: Reorder — pricing confirmation** — for reorder template,
  references prior PI number and confirms spec unchanged.

Demo templates (`Full Mission`, `Pre project mission`,
`Energy-Efficiency Assessments`) are left untouched per the deploy
brief — they remain visible in the dropdown.
""",
    'author': 'Courtwell Internal',
    'website': 'https://courtwell.com.hk',
    'depends': [
        'sale_management',
        'sale_crm',
        'cw_debrand',
    ],
    'data': [
        'data/sale_order_template_data.xml',
        'data/mail_template_data.xml',
        'reports/report_saleorder_inherit.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
