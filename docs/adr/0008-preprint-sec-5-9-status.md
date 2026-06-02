# ADR-0008: Preprint Sec. 5.9 -- mechanical-chain claim status

## Status

Accepted (2026-06-02). Resolves OPEN_QUESTIONS Q7.

## Context

Q7 asked whether the Corona claim for preprint Sec. 5.9 ("the SSOT -> codegen ->
RTL -> silicon chain is mechanical end-to-end") should be included now or deferred.
The original default was to defer until Phase B `rom_readback` passes, then add it
as `[Verified]`.

## Decision

Phase B (Verilog ROM emitter) and Phases C-F (Tier-1 decoders, formal verification,
LibreLane GDS, precheck) are complete. The SSOT -> codegen -> RTL -> silicon chain
is demonstrated **end-to-end in simulation and GDS** and is enforced by 18 CI
cross-check gates across 5 independent evidence layers (`docs/VERIFICATION.md`).

This ADR records the **repository-side status** of the claim (the preprint text
itself is external):

- The mechanical-chain claim is stated as **`[Empirical fit]`** -- demonstrated in
  sim/GDS and CI; an upgrade to `[Verified]` awaits **measured silicon** (~Nov 2026).
- The FL-002 governing sentence ("the goldenfloat ladder earns its place through
  breadth and toolchain coherence, not per-rung superiority") remains
  **`[Open conjecture]`**, independent of the chain claim.

## Consequences

- Sec. 5.9 may cite the chain as `[Empirical fit]`, with the silicon caveat.
- The status upgrades to `[Verified]` only after post-silicon bring-up confirms
  the ROM and decoders on physical hardware.
- FL-002's status is unchanged by this decision.
