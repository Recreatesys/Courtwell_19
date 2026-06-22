# cw_quote_templates

Adds four `sale.order.template` records covering Courtwell's recurring quoting patterns,
and three matching `mail.template` variants that preserve the `cw_debrand` styling
(no portal CTA, reply-to-email, user signature footer).

## Sale-order templates

| Name | Validity | Prepay | Use case |
|---|---|---|---|
| `CW China Custom Merch` | 14 d | 50 % | New custom-branded merchandise from a China factory (the DCME pattern). |
| `CW Reorder (Existing SKU)` | 7 d | 50 % | Repeat order on a SKU the customer has approved before. References prior PI. |
| `CW Sample Request` | 30 d | 100 % | Paid pre-production sample. Sample fee non-refundable unless followed by production within 60 d. |
| `CW Special Pricing (Strategic)` | 7 d | 50 % | GM-cleared margin deals. Signature required. "Not a precedent" disclaimer. |

Each template seeds a default `note` (terms text on the quotation) that the merchandiser
can leave as-is or edit per deal.

## Mail templates

| Name | Use case |
|---|---|
| `CW: Quote — first send` | Default outbound when the merchandiser issues a quote for the first time. |
| `CW: Quote — gentle follow-up` | Sent N days after first send when no response. Mentions validity expiry. |
| `CW: Reorder — pricing confirmation` | Paired with the Reorder template. References prior PI No.; confirms spec unchanged. |

All three mail templates:

- Use `object.user_id.signature` for the merchandiser contact block (set on each user's profile in Settings → Users → Preferences).
- Reference `object.sourcing_reference` for the coded ref (QP-/PI-) and fall back to `object.name` (S00057-style) only if missing.
- Include the standard `sale.action_report_saleorder` PDF as attachment.
- Carry no portal CTA — `cw_debrand` already disables that infrastructure-wide via `mail.mail_notification_layout`.

## Dependencies

* `sale_management` — provides `sale.order.template`.
* `sale_crm` — links templates to opportunities (the smart-button flow).
* `cw_debrand` — guarantees the portal CTA is suppressed for the new mail templates as well.

## Demo templates left in place

Per deploy brief, the existing demo templates (`Full Mission`, `Pre project mission`,
`Energy-Efficiency Assessments`) are **not archived**. They remain visible in the
Quotation Template dropdown alongside the four CW templates. Archive them later with:

```python
self.env['sale.order.template'].browse([1, 2, 3]).write({'active': False})
```

## Editing terms after install

The `note` field on each template carries the default terms text. Because the data is
loaded with `noupdate="0"` (default), upgrades will **re-assert** any change you make
in the UI on the next `cw-deploy` run. If you want UI edits to stick:

1. Edit the template in the UI (Settings → Sales → Quotation Templates).
2. Either bump `noupdate="0"` to `noupdate="1"` in `data/sale_order_template_data.xml`
   and re-deploy, or remove the relevant `<field name="note" .../>` line from the XML.

The standard pattern is to keep `noupdate="0"` until terms are stable, then flip to
`noupdate="1"` so UI edits persist.
