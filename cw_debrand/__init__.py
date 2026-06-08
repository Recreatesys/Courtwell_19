def _cw_debrand_clear_template_noupdate(env):
    """Clear noupdate=True on the stock sale email template ir_model_data
    rows so cw_debrand's data file (and any future override) can write
    body_html on install AND on upgrade.

    Stock seeds these inside <data noupdate="1"> blocks. That flag
    persists on ir_model_data and silently blocks ALL future writes
    via the XML data loader, no matter which module is doing the
    writing. Clearing it once unblocks every subsequent module-data
    refresh of these templates.

    Wired as pre_init_hook (fresh install) + migration script
    (upgrade) so the unblock happens BEFORE cw_debrand's own data
    files load.
    """
    env.cr.execute("""
        UPDATE ir_model_data
        SET noupdate = false
        WHERE module = 'sale'
          AND name IN (
              'email_template_edi_sale',
              'email_template_proforma',
              'mail_template_sale_confirmation'
          )
    """)
