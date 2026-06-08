{
    'name': "CW Debrand & Quotation Email Cleanup",
    'version': '19.0.1.0.1',
    'category': 'Tools',
    'summary': "Strips Odoo branding from website, portal, emails, and "
               "backend; replaces the portal link in quotation emails with "
               "the assigned merchandiser's contact details.",
    'description': """
Courtwell — Debrand & Quotation Email Cleanup
=============================================

This module is the single point of truth for client-facing branding
overrides on the Courtwell Odoo deployment.

Quotation email
---------------
* Overrides ``sale.email_template_edi_sale`` (the template used by the
  "Send by email" button on a quotation) to remove the customer-portal
  "View Quotation" CTA block.
* Replaces it with a block that surfaces the assigned merchandiser
  (sale.order.user_id) — name, email, direct phone — so the client
  has a real human to reply to instead of a self-service link.

Branding removed
----------------
* Website (frontend): "Powered by Odoo" footer copyright, favicon,
  login screen "Odoo" wordmark and tagline.
* Customer portal (/my/*): "Powered by Odoo" footer.
* Outbound mail layouts (``mail.mail_notification_layout`` and the
  light variant): Odoo logo, "Sent by Odoo" footer.
* Backend: login page brand strings, browser tab title default.

Notes
-----
* Favicon ships as a placeholder PNG; replace
  ``static/src/img/favicon.png`` with the real Courtwell favicon
  before installing in prod.
* No data model changes. Module is idempotent and safely uninstallable
  (reverts to stock Odoo branding on uninstall).
""",
    'author': 'Courtwell Internal',
    'website': 'https://courtwell.com.hk',
    'depends': [
        'base',
        'web',
        'mail',
        'sale',
        'sale_management',
        'portal',
        'website',
    ],
    'data': [
        'data/mail_template_sale.xml',
        'views/mail_notification_layout.xml',
        'views/website_layout.xml',
        'views/portal_layout.xml',
        'views/web_login.xml',
        'views/web_layout.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
    'pre_init_hook': '_cw_debrand_clear_template_noupdate',
}
