# ADR-0006: D2D = holographic mesh (spec'd), implementation deferred

## Status

Accepted (2026-06-02). Resolves OPEN_QUESTIONS Q5.

## Context

Q5 asked whether die-to-die routing should use the T27 holographic mesh
(`d2d_holo_mesh.v`, the canonical T27 module owned by Gamma) or a simpler
point-to-point link. Point-to-point is faster to verify but diverges from the
Gamma+Corona two-die board reference design.

## Decision

The **holographic mesh** is the specified D2D protocol (`specs/corona/d2d_routing.t27`),
chosen over point-to-point to avoid divergence from the Gamma reference. However,
**D2D implementation is deferred** (Phase D) for the TTGF26a shuttle: Corona ships
**standalone** (ROM + Tier-1 decoders + anchor), with no D2D RTL this round.

The Gamma+Corona two-die D2D assembly -- the first configuration that answers
oracle queries for all 80 SSOT indices including Gamma-owned formats -- is a
future milestone.

## Consequences

- Phase D is deferred; no D2D RTL on this shuttle.
- `specs/corona/d2d_routing.t27` remains a `[Spec]` artifact.
- Gamma-owned formats (GF*, FP8 subset, INT4/8, NF4, posit16, BitNet) return ROM
  metadata on a standalone Corona board but require Gamma over D2D for arithmetic.
- D2D bring-up happens when the two-die board is assembled (post-shuttle).
