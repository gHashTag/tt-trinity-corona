# gf16 rounding-mode conformance (2026-06)

Closes the last documented-open numerical item in the GoldenFloat arc: the gf16
multiply rounding convention. Characterized exhaustively by
`tools/gf16_rounding_conformance.py`.

## Finding

The gf16 spec (`t27/specs/numeric/gf16.t27`) states the intended rounding mode in
three places: "Round-to-nearest, ties to even (IEEE 754 roundTiesToEven)". But the
two implementations disagree with the spec **and with each other** on exact-halfway
cases:

| implementation | rounding actually done | matches spec intent (ties-to-even)? |
| --- | --- | --- |
| `gf16_v2_mul.v` (and frozen silicon `gf16_mul`) | **ties-to-zero** (truncate exact ties) | no -- 99.716% |
| `gf16_encode_f32` (spec's own Zig, the f32->gf16 path) | **half-up** (`discarded & 0x2000 -> +1`) | no -- 99.427% |
| intended per spec text | ties-to-even | -- |

Three different conventions; the documented IEEE standard is implemented by neither.
There is also a spec-internal inconsistency: `gf16_encode_f32`'s comment claims
"ties to even" while its code is half-up. (`gf16_round_phi` is a *separate*,
deliberate golden-ratio-biased function -- not part of this; not a defect.)

## Magnitude

Exhaustive over all 512x512 unit-exponent mantissa products (the MAC regime):
- The RTL is **ties-to-zero, exactly** (100.000% match -- no other rounding bug).
- It deviates from the intended ties-to-even on **744 / 262144 = 0.284%** of
  products, **every difference exactly 1 ULP**, and **only on exact-halfway ties**
  (1501 tie products total; the 744 are the ties whose kept-LSB is odd).

## Impact

Immaterial at the task level. The Defect-1 trained-model studies
(`gamma/test/impact_trained_gf16*.py`) already show that ULP-scale gf16 MAC
differences do not move classifier accuracy (0 accuracy delta on digits, shallow and
2-layer). A 1-ULP-on-0.28%-of-ties deviation is far smaller than the (also
task-quiet) gf16_mul halving defect. This is a **conformance/spec-hygiene** item, not
a numerical-accuracy risk.

## Resolution

- **Fabricated silicon (frozen):** rounds ties-to-zero. Cannot change; documented
  here as a known, bounded (<=1 ULP, ties-only) deviation from IEEE roundTiesToEven.
- **Spec-conformant variant staged:** `gamma/src/gf16_v3_mul.v` implements true
  ties-to-even -- a one-token change from `gf16_v2_mul`
  (`guard & (round_b | sticky | mant_out[0])`), verified 100% == a ties-to-even
  reference over all 262144 unit-exp products. This is the drop-in for a future
  regen/tapeout that wants strict IEEE conformance.
- **t27-master comment fixed (done, t27 2197e50e):** `gf16_encode_f32`'s comment no
  longer claims "ties to even" -- it now states the actual half-up behavior and
  cross-references this doc. Zero behavior change (a behavioral ties-to-even change
  to the spec is a separate, test-gated decision since it would shift the conformance
  goldens, and could not be validated here without the Zig build).
- **Still flagged for the program (needs the Zig build to verify):** `gf16_round`
  (integer round, line ~546) comments "ties to even" but its code is
  `@round(a_val)`, which in Zig rounds ties AWAY from zero -- another comment-vs-code
  mismatch worth confirming/fixing with the test suite (its own test
  `gf16_round_half_up` asserts round(2.5)->2.0, which matches neither @round nor
  half-up, so the test/comment/code triple needs reconciling).
- **Behavioral path if strict IEEE conformance is wanted:** adopt `gf16_v3_mul`
  (ties-to-even, verified) at the next regen and make `gf16_encode_f32` round
  ties-to-even (add the kept-LSB term), re-generating the conformance goldens.

## Re-check

```
python3 tools/gf16_rounding_conformance.py
  gf16_v2_mul: implements ties_zero (frozen silicon)
  gf16_v3_mul: implements ties_even (spec-conformant, 100%)
  RTL-vs-intent gap: 744/262144 = 0.28% (1 ULP, ties only)
```
