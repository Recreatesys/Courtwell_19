# RFQ & PO IDs — What Changed and Why

**For merchandisers issuing RFQs to suppliers.**

---

## 1. The new ID format

```
RQ-{Province}-{Segment}-{Letter}-{NNN}
```

Example: **`RQ-GD-50-A-001`**

| Piece | Meaning |
|---|---|
| `RQ-` | Draft RFQ (flips to `PO-` when you confirm) |
| `GD` | Supplier's province (Guangdong) |
| `50` | GS1 segment for this purchase |
| `A` | This supplier's permanent letter in the Guangdong–segment-50 pool |
| `001` | How many RFQs you've sent **to this supplier** in this pool |

When you confirm: `RQ-GD-50-A-001` → `PO-GD-50-A-001`. Body unchanged; only the prefix flips.

---

## 2. The problem this fixes

**Old format:** `RQ-GD-50-26-007`, `RQ-GD-50-26-008`
Two manufacturers in Guangdong both quoting segment 50 → you couldn't tell which RFQ came from which supplier without opening the record.

**New format:** `RQ-GD-50-A-001`, `RQ-GD-50-B-001`
The letter tells you which supplier — immediately, from the ID alone.

---

## 3. How letters are assigned

Each **(Province + Segment)** is its own pool. Letters are assigned in order of first appearance:

| Event | Resulting ID |
|---|---|
| XYZ Mfg's first RFQ in Guangdong segment 50 | `RQ-GD-50-A-001` |
| PQR Mfg's first RFQ in same pool | `RQ-GD-50-B-001` |
| XYZ again, same pool | `RQ-GD-50-A-002` |
| PQR again, same pool | `RQ-GD-50-B-002` |
| XYZ in **Zhejiang** segment 50 (different pool) | `RQ-ZJ-50-A-001` |
| XYZ in Guangdong segment **51** (different pool) | `RQ-GD-51-A-001` |

**Key rule:** A supplier's letter is permanent within a pool. If XYZ is "A" in `GD-50`, they will *always* be "A" there. The number after the letter grows each time you send them another RFQ in that pool.

---

## 4. New smart button in CRM

Every CRM Opportunity now has an **RFQs** button at the top of the form, with a live count badge.

```
   ┌─────────────────────┐
   │   📦 RFQs           │
   │        2            │
   └─────────────────────┘
```

**To issue an RFQ from an Opportunity:**

1. Open the Opportunity in CRM.
2. Click the **RFQs** smart button.
3. Click **New** in the list that opens.
4. The Opportunity link and GS1 Segment **auto-fill** — no typing.
5. Pick the supplier.
6. Save → the RFQ ID generates automatically.

You no longer need to remember or copy-paste the Opportunity reference.

---

## 5. Pre-requisites checklist

Before the system can generate an RFQ ID, both of these must be true:

- ☐ The supplier has a **Province Code** (2 letters) on their contact record
- ☐ The RFQ has a **GS1 Segment** (auto-fills if you used the smart button)

If either is missing you'll get a clear error pointing at what's missing. Fix it on the supplier or the RFQ form, then save again.

---

## 6. What happens to existing RFQs and POs?

**Nothing.** Existing IDs (`RQ-GD-50-26-007` and similar) stay exactly as they are. Don't rename them.

Only RFQs created from this point onward use the new format. Both formats can coexist — they're distinct enough that you'll always know which is which.

---

## 7. Quick reference card

| Symbol in ID | Means |
|---|---|
| `RQ-…` | Draft RFQ awaiting supplier quote or your confirmation |
| `PO-…` | Confirmed PO — supplier is committed |
| Letter (A, B, C…) | Which supplier within this (Province + Segment) pool |
| NNN | How many RFQs we've sent this supplier in this pool |

When in doubt: open the record. The supplier name, opportunity link, and segment are all on the form. The ID is shorthand — the database holds the full picture.

---

*Questions? Talk to the General Manager or the IT support contact.*
