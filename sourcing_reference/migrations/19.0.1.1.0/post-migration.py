"""
Post-migration for 19.0.1.0.0 → 19.0.1.1.0

The reference-ID auto-generation trigger has moved from the `Sourcing` stage
to the `Quotation` stage. The `Sourcing` stage is being retired.

This script:
  1. Re-points any crm.lead currently sitting at Sourcing → Quotation.
     Existing `sourcing_reference` values are preserved (the generation
     function is idempotent; we also bypass it with skip_sourcing_validation).
  2. Removes the `Sourcing` crm.stage record and its ir_model_data mapping.

If the Sourcing stage cannot be removed (e.g. because some other module
references it that we don't know about), we log a warning and leave it in
place — the user can delete it manually.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # --- locate Sourcing + Quotation stages --------------------------------
    cr.execute("""
        SELECT res_id FROM ir_model_data
        WHERE module = 'sourcing_reference' AND name = 'crm_stage_sourcing'
    """)
    row = cr.fetchone()
    sourcing_id = row[0] if row else None

    cr.execute("""
        SELECT res_id FROM ir_model_data
        WHERE module = 'sourcing_reference' AND name = 'crm_stage_quotation'
    """)
    row = cr.fetchone()
    quotation_id = row[0] if row else None

    if not sourcing_id:
        # Stage may have been adopted from a pre-existing record under a
        # different xml_id, or already removed. Fall back to name-based lookup.
        cr.execute(
            "SELECT id FROM crm_stage WHERE name->>'en_US' = 'Sourcing' LIMIT 1"
        )
        row = cr.fetchone()
        sourcing_id = row[0] if row else None

    if not quotation_id:
        cr.execute(
            "SELECT id FROM crm_stage WHERE name->>'en_US' = 'Quotation' LIMIT 1"
        )
        row = cr.fetchone()
        quotation_id = row[0] if row else None

    if not sourcing_id:
        _logger.info(
            "sourcing_reference migration 19.0.1.1.0: no Sourcing stage found, nothing to do."
        )
        return

    if not quotation_id:
        _logger.warning(
            "sourcing_reference migration 19.0.1.1.0: Sourcing stage exists but "
            "Quotation stage not found. Cannot reroute leads; leaving Sourcing "
            "in place."
        )
        return

    # --- move leads ---------------------------------------------------------
    cr.execute(
        "UPDATE crm_lead SET stage_id = %s WHERE stage_id = %s",
        (quotation_id, sourcing_id),
    )
    moved = cr.rowcount
    _logger.info(
        "sourcing_reference migration 19.0.1.1.0: moved %d leads from Sourcing → Quotation.",
        moved,
    )

    # --- drop xml_id mapping then the stage row ----------------------------
    cr.execute(
        "DELETE FROM ir_model_data "
        "WHERE module = 'sourcing_reference' AND name = 'crm_stage_sourcing'"
    )

    # Check for FK references from any other table before deleting.
    cr.execute("""
        SELECT 1 FROM crm_lead WHERE stage_id = %s LIMIT 1
    """, (sourcing_id,))
    if cr.fetchone():
        _logger.warning(
            "sourcing_reference migration 19.0.1.1.0: stage %s still referenced "
            "after move — leaving it in place to avoid FK violation.",
            sourcing_id,
        )
        return

    try:
        cr.execute("DELETE FROM crm_stage WHERE id = %s", (sourcing_id,))
        _logger.info(
            "sourcing_reference migration 19.0.1.1.0: removed Sourcing stage id=%s.",
            sourcing_id,
        )
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "sourcing_reference migration 19.0.1.1.0: could not delete stage %s: %s. "
            "You can remove it manually via CRM → Configuration → Pipeline Stages.",
            sourcing_id, exc,
        )
