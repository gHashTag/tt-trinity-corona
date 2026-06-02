# Open questions (RESOLVED -- recorded as ADRs)

These are the seven **Phase-C scoping decisions** (a distilled set related to,
but not identical to, PLAN.md Section 10's planning questions -- see that section
for the planning-stage Q1-Q7 and their as-built resolution). Phases C-F are
complete, so all seven here are decided; each is now recorded as an ADR in
`docs/adr/`. The original question text is kept below for historical context.

| Q | Topic | Decision | ADR |
| --- | --- | --- | --- |
| Q1 | Tile size | 4x4 (16 tiles) | [`0001`](adr/0001-tile-size-4x4.md) |
| Q2 | Takum16 tier | Tier-2 (ROM-only) | [`0003`](adr/0003-takum-tier-2.md) |
| Q3 | Posit32 module | Not on-die (posit8 on-die, posit16 D2D, posit32 ROM-only) | [`0004`](adr/0004-no-posit32-module.md) |
| Q4 | Decimal (DPD) | Tier-2 ROM-only + software oracle | [`0005`](adr/0005-decimal-tier-2-software-oracle.md) |
| Q5 | D2D protocol | Holographic mesh (spec'd), implementation deferred | [`0006`](adr/0006-d2d-holographic-mesh-deferred.md) |
| Q6 | License | Apache-2.0 | [`0007`](adr/0007-license-apache-2.0.md) |
| Q7 | Preprint Sec. 5.9 | Chain claim `[Empirical fit]`; FL-002 stays `[Open conjecture]` | [`0008`](adr/0008-preprint-sec-5-9-status.md) |

(The shuttle choice TTGF26a is recorded separately in [`0002`](adr/0002-shuttle-ttgf26a.md).)

---

## Historical: the seven questions as originally posed

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
