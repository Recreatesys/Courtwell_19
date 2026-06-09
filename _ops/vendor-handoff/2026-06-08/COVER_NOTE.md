# Courtwell_19 custom-addons — 2026-06-08 Vendor Handoff

**From:** Howard Cheng <howardcheng@courtwell.com.hk>
**Repo:** `Recreatesys/Courtwell_19` · `custom-addons/`
**Base commit (required ref):** `91df39e` — *Add cw_project_mail_route_fix to guard upstream list.remove crash*
**Tip after applying:** `71fc3f4`
**Total:** 14 commits, +8.5K lines, 0 deletions outside the affected modules

## What's in the bundle

Three categories of work, all already deployed and running on our `CW19_Test` database:

### A. Feature work on existing modules (commits 1–3)

| # | SHA | Module | Version | What |
|---|---|---|---|---|
| 1 | `e422a7e` | `sourcing_reference` | → 19.0.1.1.0 | Pipeline simplified from 9 → 8 stages; Sourcing stage removed; ID generator rerouted to Quotation entry |
| 2 | `aeb69b8` | `sourcing_reference` | → 19.0.1.2.0 | New RFQ ID format `RQ-{Prov}-{Seg}-{Letter}-{NNN}`; new `sourcing.supplier.pool.member` model; `opportunity_id` FK on `purchase.order`; CRM smart button. 15-test suite. |
| 3 | `9a9e7c0` | `cw_contacts_phase1` | → 19.0.1.1.0 | `service_provider_type` Selection → Many2one to new `cw.service.provider.type` lookup model. Migration backfills existing partners. |

### B. New CW modules — first time in git (commits 4–13)

| # | SHA | Module | Version | What |
|---|---|---|---|---|
| 4 | `7eb901b` | `cw_debrand` | 19.0.1.0.0 | Strip Odoo branding from frontend, portal, email. Replaces portal-link CTA in quote emails with merchandiser contact. |
| 5 | `aa7836b` | `cw_contacts_restrict` | 19.0.1.0.0 | Form-only Contacts UI for non-directory staff; autocomplete-only lookup wizard. |
| 6 | `7bcef66` | `cw_shipment` | 19.0.1.0.0 | Inbound shipment header/lines model (`cw.shipment`, `cw.shipment.container`, `cw.port`). Foundational for shipping cluster. |
| 7 | `24d0eb5` | `cw_sourcing_inspection` | 19.0.1.3.0 | Structured pre-shipment / DUPRO QC reports replacing the Chinese paper form. Per-SKU detail grid, 4-state outcome, PDF report. |
| 8 | `9ae77d9` | `cw_quote_revision` | 19.0.1.1.0 | `sale.order` revision tracking with Revise button, `is_superseded` flag, revision chain visible from CRM opportunity. |
| 9 | `d4c00a7` | `cw_crm_access` | 19.0.1.0.0 | Defines *Accounting / CRM Viewer (Post-Proforma)* security group with read-only access to opportunities at stages Proforma Invoice / QC / Enroute / Upsell-Reorder. |
| 10 | `6e3d2a7` | `cw_client_code_approval` | 19.0.1.0.0 | GM-only workflow for assigning the 2-letter `client_code` on Clients — closes the loop left open by `cw_contacts_phase1` + `sourcing_reference`. |
| 11 | `26c591b` | `cw_shipment_inspection_gate` | 19.0.1.0.0 | Bridge module: blocks `cw.shipment` from progressing past Booked unless every linked inspection is cleared for loading. |
| 12 | `451c2f7` | `cw_shipping_workflow` | 19.0.1.1.0 | Pipeline-gated shipping coordination for the Shipping Dept (Aris). Auto-creates draft `cw.shipment` on Proforma Invoice; deposit gate; QC-anchored booking deadline. |
| 13 | `895fe7e` | `cw_freight_expense` | 19.0.1.1.0 | 8 decomposed freight cost fields on `cw.shipment` auto-posted to `hr.expense` records, all tagged with the linked project's analytic account. |

### C. Follow-up bug fix (commit 14)

| # | SHA | Module | Version | What |
|---|---|---|---|---|
| 14 | `71fc3f4` | `cw_debrand` | → 19.0.1.0.1 | Clears the `noupdate=1` flag on `email_template_edi_sale` and friends before `cw_debrand` data files load, so the body_html override actually takes effect on upgrade. Adds `pre_init_hook` + migration. Verified on `CW19_Test`: `S00053` now renders without merchandiser block, falling through to user signature as intended. |

## Module dependency order (read top-down for clean apply)

`cw_debrand`, `cw_contacts_restrict`, `cw_shipment` have no internal-module dependencies — these can land first. Then `sourcing_reference` and `cw_contacts_phase1` work (commits 1, 2, 3) provide foundations used by the rest. The remaining modules layer on top.

If your repo already has the base commit `91df39e`, applying the bundle preserves this exact dependency order — no manual reshuffling needed.

## How to ingest

```bash
# Single bundle, recommended
git fetch /path/to/courtwell_19_2026-06-08.bundle main:cw-2026-06-08
git log cw-2026-06-08 --oneline ^91df39e   # inspect the 14 commits
git merge cw-2026-06-08                     # or rebase onto your branch

# Alternative — text-based apply (14 patches, in order)
for p in 0001-*.patch 0002-*.patch 0003-*.patch 0004-*.patch 0005-*.patch \
         0006-*.patch 0007-*.patch 0008-*.patch 0009-*.patch 0010-*.patch \
         0011-*.patch 0012-*.patch 0013-*.patch 0014-*.patch; do
  git am "$p"
done
```

## DB impact — summary across all modules

- **New tables:** `sourcing_supplier_pool_member`, `cw_service_provider_type`, `cw_shipment`, `cw_shipment_container`, `cw_port`, `sourcing_inspection`, `sourcing_inspection_sku_line`, `cw_freight_quote`.
- **New columns** on existing tables: `purchase_order.opportunity_id`, `sourcing_supplier_sequence.next_letter_index`, `res_partner.service_provider_type_id`, plus several on `crm_lead` and `sale_order` for the shipping/revision flows.
- **Schema migrations** under each module's `migrations/<version>/` run automatically on module upgrade. All have already run cleanly on CW19_Test.
- **Existing IDs preserved** — `sourcing_reference` retains legacy `RQ-…-YY-NNN` style IDs; only new RFQs use the new format.

## Testing

Only `sourcing_reference` ships an automated test suite (15 tests under `tests/test_supplier_pool_allocation.py`):

```bash
odoo-bin -d <db> --test-enable --stop-after-init \
         -u sourcing_reference --test-tags cw_sourcing
```

Other modules: no automated tests; behavior verified by deployment + manual walkthrough on CW19_Test.

## Merchandiser handoff doc

`sourcing_reference/docs/RFQ_ID_GUIDE.md` (in commit #2) is a one-pager explaining the new RFQ ID format and CRM smart button for non-developer audiences.

## Contact

Howard Cheng — howardcheng@courtwell.com.hk
