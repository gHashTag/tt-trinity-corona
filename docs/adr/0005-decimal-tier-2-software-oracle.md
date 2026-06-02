# ADR-0005: Decimal float Tier-2 (ROM-only + software oracle)

## Status

Accepted (2026-06-02). Resolves OPEN_QUESTIONS Q4.

## Context

Q4 asked whether IEEE 754-2008 decimal float (DPD) should ship as on-die RTL or
as a Tier-2 ROM-only record with a software oracle. No open-source DPD RTL exists;
a hand-rolled densely-packed-decimal codec is estimated at 1,500-5,000 cells
(Tier-1 high-end), pressuring the 4x4 budget (ADR-0001).

## Decision

Decimal float ships **Tier-2 (ROM-only) plus a software oracle**. decimal32/64/128
(fmt_id 5-7, `encoding_kind = ENC_BCD`, IEEE-decimal cluster) are ROM metadata
with **no on-die DPD codec**.

Note: the on-die `bcd_decode` module handles only the **2-digit packed-BCD
primitive** (`{tens[7:4], ones[3:0]} -> tens*10 + ones`), which is a building
block, not IEEE 754-2008 decimal32. Full DPD decode is provided off-die (software
oracle in `tools/` / host).

## Consequences

- fmt_id 5-7 are ROM-only; no DPD arithmetic on silicon.
- `bcd_decode` covers the packed-BCD primitive only (verified exhaustively).
- A from-definition DPD codec remains a future Tier-1 option if a later, larger
  shuttle provides the cell budget.
