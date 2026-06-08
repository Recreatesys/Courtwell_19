"""
Pre-migration for 19.0.1.0.0 → 19.0.1.1.0

Field `res.partner.service_provider_type` is changing type from
`Selection` (text column) to `Many2one` (integer FK column).

This script preserves the old text values by renaming the existing column
to `service_provider_type_legacy`. The post-migration then translates each
legacy code → new cw.service.provider.type record ID and drops the legacy
column.
"""


def migrate(cr, version):
    if not version:
        return

    # Bail out if the rename already happened (re-run safety).
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'res_partner' AND column_name = 'service_provider_type_legacy'
    """)
    if cr.fetchone():
        return

    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'res_partner' AND column_name = 'service_provider_type'
    """)
    if not cr.fetchone():
        return

    cr.execute("""
        ALTER TABLE res_partner
        RENAME COLUMN service_provider_type TO service_provider_type_legacy
    """)
