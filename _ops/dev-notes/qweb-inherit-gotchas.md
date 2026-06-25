# QWeb Inherit — Gotchas Learned the Hard Way

Topic: writing template inherits that target stock Odoo report XML.
First captured 2026-06-25, during the `cw_quote_templates 19.0.1.0.0 → 19.0.1.2.0` work.
Add to this file when new gotchas surface; don't split per-date.

---

## 1. Don't insert XML between sibling `t-if` and `t-else`

The stock `sale.report_saleorder_document` signature block looks like this:

```xml
<div t-if="not doc.signature" class="oe_structure"/>
<div t-else="" class="mt-4 ml64 mr4" name="signature">
    ...
    <img t-att-src="image_data_uri(doc.signature)"/>
    ...
</div>
```

Putting *anything* between the two divs via `<xpath ... position="before">` on the
second div **detaches the `t-else` from its `t-if` anchor**. QWeb then renders the
t-else branch unconditionally. If the t-else branch contains a `t-att` expression
that explodes on the falsy value the original t-if was guarding against, you get a
runtime crash.

In our case `image_data_uri(False)` raised
`TypeError: 'bool' object is not subscriptable`.

**Rule:** when you need to inject content adjacent to a `t-else`, anchor the
xpath on a stable parent or wrapper, **not on the t-else sibling itself**.

---

## 2. Put defensive guards on the leaf, not the branch

When you want to harden against a falsy-value crash, guard the expression that
actually explodes — not the surrounding container.

**Bad** (gets bypassed when the surrounding conditional breaks):

```xml
<div t-if="doc.signature">
    <img t-att-src="image_data_uri(doc.signature)"/>
</div>
```

**Good** (survives any restructuring of the surroundings):

```xml
<xpath expr="//img[@t-att-src='image_data_uri(doc.signature)']"
       position="attributes">
    <attribute name="t-if">doc.signature</attribute>
</xpath>
```

The guard is now intrinsic to the dangerous element. Other modules' inherits
can't accidentally re-expose the bug. Live example in
`cw_quote_templates/reports/report_saleorder_inherit.xml` under the
`report_saleorder_signature_safety` template id.

---

## 3. Package fixes near their source — promote when they recur

If a stock-Odoo bug surfaces during work on module X, fix it *in X first*.
Keeping the link between the lesson and the code that revealed it makes the
git history readable.

If the same pattern shows up in another stock template (e.g.
`account.report_invoice_document` has the same `t-if`/`t-else` signature
structure), then **promote the fix** to a dedicated module like
`cw_signature_safety`.

Don't pre-emptively factor things out. Wait for the second instance.

---

## Variables in stock QWeb report templates

Sale report uses `doc` (singular), iterated from `docs`. **Not `o`.** Verified
for Odoo 19 in `sale/report/ir_actions_report_templates.xml`. Different stock
modules have different conventions:

| Stock template | Iteration variable |
|---|---|
| `sale.report_saleorder_document` | `doc` |
| `account.report_invoice_document` | `o` (older convention, may differ in 19) |
| `stock.report_picking` | `o` |
| `purchase.report_purchaseorder_document` | `o` |

When in doubt, grep the stock template for `doc.` vs `o.` references before
writing your inherit.

---

## `ref()` is not available in QWeb report context

You can use `ref('module.xml_id')` in form/list/kanban views but **not** in
QWeb report rendering. Trying it raises `KeyError: 'ref'`. Use either:

* `env.ref('module.xml_id')` when `env` is in scope (uncommon in report
  context — depends on the report engine)
* **Name-based matching against a stable field** (what we did):
  `doc.sale_order_template_id.name == 'CW Sample Request'`

The name approach survives DB transplants where record IDs differ, as long
as you control the record's `name` field (which you do for any record you
created via XML data).

---

## Both report actions share `sale.report_saleorder_document`

In `sale/report/ir_actions_report_templates.xml`:

```
sale.report_saleorder_document   ← the rendering brain
    ↓ called by
sale.report_saleorder_raw         ← wraps in HTML container
    ↓ called by
sale.report_saleorder             ← "PDF Quote" action      (id 374)
sale.report_saleorder_pro_forma   ← "PRO-FORMA Invoice" action (id 375)
```

`sale.report_saleorder_pro_forma` also calls `sale.report_saleorder_document`
directly. **A single inherit on `_document` extends both PDF outputs.**
No need to write parallel inherits on the two action templates.

