# ADR-0003: Takum demoted to Tier-2 (ROM-only)

## Status

Accepted (2026-06-02). Resolves OPEN_QUESTIONS Q2.

## Context

Q2 asked whether takum16 should be a Tier-1 on-die codec or a Tier-2 ROM-only
record. This hinged on whether the Hunhold takum VHDL (Hunhold 2024,
[arXiv:2408.10594](https://arxiv.org/abs/2408.10594)) could be confirmed
Apache-2.0-compatible before Phase C, or whether a clean-room takum8 codec
(estimated 5 calendar-days, ~500-1,000 cells) would be implemented from the
mathematical definition ([arXiv:2412.20273](https://arxiv.org/abs/2412.20273)).

## Decision

Takum ships **Tier-2 (ROM-only)**. The catalog records takum8/16/32/64
(fmt_id 35-38, `encoding_kind = ENC_TAKUM`) as ROM metadata with **no on-die
codec** (no `FLAG_ON_DIE`). The Hunhold VHDL license was not confirmed
Apache-2.0-compatible before Phase C, and a clean-room takum8 codec was not
prioritised within the 4x4 cell budget (ADR-0001).

Takum remains **visible** in the ROM as the standing counterexample to FL-002 --
it is recorded, not suppressed (per the project's claim-status discipline).

## Consequences

- fmt_id 35-38 are ROM-only; takum decode requires off-die / software.
- The FL-002 counterexample is preserved and queryable on-chip.
- A clean-room takum8 codec remains a future Tier-1 candidate if Hunhold VHDL
  licensing resolves favourably, or if a from-definition implementation is funded.
