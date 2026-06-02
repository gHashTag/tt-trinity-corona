# ADR-0004: No on-die Posit32 module

## Status

Accepted (2026-06-02). Resolves OPEN_QUESTIONS Q3.

## Context

Q3 asked whether Corona should ship a Posit32 decode module despite its
4,000-8,000 cell cost -- roughly the same area as the entire ~1.2 KB ROM. The 4x4
tile budget (ADR-0001) is ~7,700-8,300 cells total for ROM + all Tier-1 decoders.

## Decision

**No Posit32 on-die module.** The posit ladder is split by tier:

- posit8 (fmt_id 31) -- **on-die** (`FLAG_ON_DIE`), the only on-die posit codec.
- posit16 (fmt_id 32) -- **Gamma-owned, D2D-routable** (`FLAG_GAMMA | FLAG_D2D`);
  decode is delegated to the Gamma die over D2D (see ADR-0006).
- posit32 (fmt_id 33), posit64 (fmt_id 34) -- **ROM-only** metadata.

Posit32 alone would consume the ROM's entire area; shipping it would force
dropping breadth elsewhere, contradicting the governing "breadth over per-rung
superiority" sentence.

## Consequences

- posit8 decodes on-chip; posit16 via D2D to Gamma; posit32/64 are ROM-only.
- Corona reaches posit16 parity with Gamma without duplicating Gamma's RTL.
- A standalone Corona board returns ROM records for posit16/32/64 but cannot
  perform their arithmetic without Gamma present.
