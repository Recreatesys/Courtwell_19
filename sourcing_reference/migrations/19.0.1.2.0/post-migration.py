"""Post-migration for 19.0.1.1.0 -> 19.0.1.2.0

Switches supplier-side RFQ IDs from YY-NNN (pool-wide sequence) to
Letter-NNN (per-supplier letter + per-supplier count).

  - Existing `sourcing_supplier_sequence.count` is left intact as the
    pool-wide RFQ tally (used for reporting).
  - New column `next_letter_index` defaults to 0 on every existing pool;
    letters are allocated lazily as new RFQs come in under the new
    scheme. Legacy suppliers do not get retroactive letter assignments.
  - Existing purchase.order rows keep their legacy `RQ-...-YY-NNN` /
    `PO-...-YY-NNN` references; only newly issued RFQs use the new
    `RQ-...-Letter-NNN` shape.
  - The new `purchase_order.opportunity_id` FK starts NULL. Linkage
    against existing POs is not backfilled — operationally there is no
    reliable way to associate legacy POs with their originating
    opportunity post hoc.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        "UPDATE sourcing_supplier_sequence "
        "SET next_letter_index = 0 "
        "WHERE next_letter_index IS NULL"
    )
    _logger.info(
        "sourcing_reference 19.0.1.2.0: initialized next_letter_index "
        "on %s pool row(s).", cr.rowcount,
    )
