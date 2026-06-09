"""Post-migration for 19.0.1.2.0 -> 19.0.1.3.0

Backfills `project_reference` on existing CRM opportunities.

Strategy (per "opportunities only — not leads"):
  1. For opps that already have an OP- sourcing_reference, copy the body
     into PR- so the two stay aligned: project_reference = 'PR-' + body.
     No sequence increment needed — the NNN was already allocated by
     the existing OP- generation.

  2. For opps that have both client_code and gpc_segment_id set but no
     OP- yet (these are eligible-but-not-yet-Quotation), walk via the
     ORM and call `_generate_project_reference()` so a fresh NNN is
     allocated through the existing sequence row.

  3. Leads (type='lead') and opportunities missing prerequisites are
     left alone — PR- will populate naturally when they qualify under
     the new create/write triggers.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # Step 1 — inherit PR- from existing OP- by prefix swap.
    cr.execute(
        """
        UPDATE crm_lead
        SET project_reference = 'PR-' || substring(sourcing_reference from 4)
        WHERE type = 'opportunity'
          AND project_reference IS NULL
          AND sourcing_reference IS NOT NULL
          AND sourcing_reference LIKE 'OP-%'
        """
    )
    op_inherited = cr.rowcount
    _logger.info(
        "sourcing_reference 19.0.1.3.0: backfilled project_reference from "
        "existing sourcing_reference on %s opportunity rows.",
        op_inherited,
    )

    # Step 2 — fresh PR- for opps with prerequisites but no OP-.
    env = api.Environment(cr, SUPERUSER_ID, {})
    Lead = env['crm.lead']
    pending = Lead.search([
        ('type', '=', 'opportunity'),
        ('project_reference', '=', False),
        ('partner_id', '!=', False),
        ('gpc_segment_id', '!=', False),
    ])
    generated = 0
    skipped = 0
    for lead in pending:
        if not lead._can_generate_project_reference():
            skipped += 1
            continue
        try:
            lead._generate_project_reference()
            generated += 1
        except Exception as e:
            skipped += 1
            _logger.warning(
                "sourcing_reference 19.0.1.3.0: PR- backfill failed for "
                "crm.lead id=%s: %s",
                lead.id, e,
            )
    _logger.info(
        "sourcing_reference 19.0.1.3.0: freshly generated PR- on %s "
        "opportunity rows; skipped %s (missing prereqs or error).",
        generated, skipped,
    )
