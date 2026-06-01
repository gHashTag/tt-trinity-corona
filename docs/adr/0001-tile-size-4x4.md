# ADR-0001: Tile Size 4x4 (16 tiles)

## Status

Accepted (2026-06-01)

## Context

Corona targets the TTGF26a shuttle on GF180MCU 180nm. The original plan considered
8x2 (MVP, 16 tiles) vs 8x4 (full Tier-1, 32 tiles). GF180MCU has ~2.1x fewer
gates per tile than SKY130A (~480-520 cells vs ~1,000), so tile budget is tight.

The project requires ~1.2 KB combinational ROM (77 records x 10 bytes) plus 12
Tier-1 decode modules (estimated 6,000-12,000 cells total) plus protocol/D2D
overhead (~300-500 cells).

## Decision

Use 4x4 (16 tiles). At ~480-520 cells/tile this gives ~7,700-8,300 cells total.
This is sufficient for ROM + 8-10 Tier-1 modules in MVP configuration. Modules
that exceed the cell budget are demoted to Tier-2 (ROM-only).

The 4x4 configuration is selected over 8x2 because the more square aspect ratio
provides better routing density for the ROM mux tree.

## Consequences

- Total cell budget: ~7,700-8,300 standard cells at 55% utilization
- posit32_decode (4,000-8,000 cells) may not fit alongside full ROM; demote to
  Tier-2 if Phase C synthesis confirms overshoot
- MVP-5 fallback (ROM + 5 converters) remains viable within this budget
- Phase A synthesis trial will validate the actual cells/tile on GF180MCU
