"""Pre-migration for 19.0.1.0.1.

Runs BEFORE cw_debrand's data files re-load during a module upgrade
that crosses this version boundary. Clears the noupdate flag on the
stock sale email template ir_model_data rows so our body_html override
actually writes when the data file is processed afterwards.

Same logic as the pre_init_hook in __init__.py; duplicated here because
hooks only fire on fresh install, not on upgrades.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE ir_model_data
        SET noupdate = false
        WHERE module = 'sale'
          AND name IN (
              'email_template_edi_sale',
              'email_template_proforma',
              'mail_template_sale_confirmation'
          )
    """)
