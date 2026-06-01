# Open questions for the user (before any RTL is written)

These are the seven open questions from PLAN.md Section 10. Each must be
answered via a short ADR in `docs/adr/` before Phase C starts.

## Q1 -- Tile size: 8x2 (MVP) or 8x4 (full Tier-1)?

- 8x2: ROM + 5 converters (posit8, posit32, mxfp8, bf16, lns8). 6-8 weeks solo.
- 8x4: ROM + all 12 Tier-1 modules. 45-55 days solo.

Phase A synthesis trial gives a hard number. Default: 8x2 unless the
synthesis trial shows margin for 8x4.

## Q2 -- Takum16 in Tier-1 or Tier-2?

Hinges on Hunhold VHDL licensing (Hunhold 2024
[arXiv:2408.10594](https://arxiv.org/abs/2408.10594)). If the VHDL license
cannot be confirmed Apache-2.0-compatible before Phase C, takum16 is demoted
to Tier-2 ROM-only and a clean-room takum8 codec is implemented from the
mathematical definition in
[arXiv:2412.20273](https://arxiv.org/abs/2412.20273) (estimated 5
calendar-days, ~500-1,000 cells).

**Risk register entry: R2.**

## Q3 -- Should Corona ship a Posit32 module despite the 4,000-8,000 cell cost?

Posit32 alone consumes roughly the same area as the entire ROM. Phase A
synthesis trial decides; if Posit32 fits, ship it; if not, drop to Posit16
parity with Gamma (and rely on D2D).

## Q4 -- Decimal float (DPD) software oracle vs RTL?

No open-source RTL exists for IEEE 754-2008 decimal32. A hand-rolled DPD
codec costs 1,500-5,000 cells (Tier-1 high-end). Alternative: ship
decimal32 as Tier-2 ROM-only with a software oracle in `tools/`.
Cost-benefit decision is open.

## Q5 -- D2D protocol: T27 holographic mesh or simpler point-to-point?

`d2d_holo_mesh.v` is the canonical T27 mesh module owned by Gamma. A
simpler point-to-point link is faster to verify but creates a divergence
from the Gamma+Corona two-die board reference design. Default: use the
holographic mesh.

## Q6 -- License declaration for Corona itself: Apache-2.0 or MIT?

Apache-2.0 matches `gHashTag/t27` and provides patent grants. MIT is shorter
and lower-friction. Default: Apache-2.0.

## Q7 -- Preprint section 5.9: include Corona claim now or defer?

The Corona claim for preprint Sec. 5.9 ("the SSOT->silicon chain is mechanical end-to-end") is a
`[Spec]` claim at this point. Including it in the preprint may be premature
if Phase B has not started. Default: defer until Phase B `rom_readback`
passes; then add Sec. 5.9 as a `[Verified]` claim.

---

Document every answer as a one-page ADR in `docs/adr/` with the format:

```
docs/adr/0001-tile-size-8x2.md     (or 8x4)
docs/adr/0002-takum16-tier.md
...etc
```
