"""
Post-migration for 19.0.1.0.0 → 19.0.1.1.0

Translate legacy text values of `service_provider_type` to FK references on
`service_provider_type_id`, then drop the legacy column.
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'res_partner' AND column_name = 'service_provider_type_legacy'
    """)
    if not cr.fetchone():
        return

    cr.execute("""
        UPDATE res_partner p
        SET service_provider_type_id = spt.id
        FROM cw_service_provider_type spt
        WHERE p.service_provider_type_legacy IS NOT NULL
          AND spt.code = p.service_provider_type_legacy
          AND p.service_provider_type_id IS NULL
    """)

    cr.execute("""
        SELECT DISTINCT service_provider_type_legacy
        FROM res_partner
        WHERE service_provider_type_legacy IS NOT NULL
          AND service_provider_type_id IS NULL
    """)
    unmapped = [row[0] for row in cr.fetchall()]
    if unmapped:
        # Surface in the upgrade log so the admin can decide; do not block.
        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning(
            "cw_contacts_phase1 upgrade: %d distinct service_provider_type "
            "values could not be mapped to a cw.service.provider.type record: %s. "
            "The legacy column will be dropped — these values are lost. "
            "Roll back via the legacy column backup if needed.",
            len(unmapped), unmapped,
        )

    cr.execute("ALTER TABLE res_partner DROP COLUMN service_provider_type_legacy")
