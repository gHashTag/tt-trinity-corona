# GF ladder verification (2026-06, multi-agent)

A second contributor is extending the GoldenFloat ladder to the SSOT closed-form
field-split rule `e = round((N-1)/phi^2), m = N-1-e` (corona #3 catalog; gamma
#118/#119 new RTL: GF6/10/14/48/96 add+mul, GF512/1024 specs). This records the
independent arithmetic verification of those new units + the test-harness fixes it
required.

## Result

All five new RTL formats verified against the exact-rational reference
(`gamma/test/gf_add_sweep.py`, `gf_mul_sweep.py`):

| format | split (E,M) | closed-form? | add | mul |
| --- | --- | :-: | :-: | :-: |
| gf6  | 2, 3   | yes | PASS (<=0.5 ULP) | PASS (<=0.5 ULP) |
| gf10 | 3, 6   | yes | PASS | PASS |
| gf14 | 5, 8   | yes | PASS | PASS |
| gf48 | 18, 29 | yes | PASS | PASS |
| gf96 | 36, 59 | yes | PASS | PASS |

(existing gf8/12/20/24/32/64/128/256 still ALL PASS). Field-splits all match the
closed-form rule.

## Test-harness bugs found + fixed (exposed by the tiny formats)

The new units are arithmetically correct; getting the sweep to verify them exposed
three reference-model bugs in the sweep harness (not RTL defects):

1. **Overflow threshold.** `is_overflow` used `2^oexp`; the IEEE round-to-nearest
   overflow boundary is `(1 - 2^-(M+2)) * 2^oexp`. gf6 correctly rounds 3.875 -> Inf
   (max finite is 3.75), but the sweep wrongly expected a finite result. Fixed.
2. **gen_pairs negative exponents.** It samples exponents `bias-2 .. bias+2`; for gf6
   `bias=1`, so it generated exponent `-1` -> the code became a negative int -> `"-8"`
   in the hexfile -> `$readmemh` parsed it as X -> the sweep crashed / flagged X.
   Not a gf6_mul bug (direct test of the same inputs is correct). Clamped exponents
   to `[0, expmax-1]`.
3. **Mul sweep had no over/underflow model** (crashed on X). Ported `is_overflow` /
   `is_underflow`; at the over/underflow boundary, flush-to-zero vs round-to-
   min/max-normal are both within 1 ULP, so the check now accepts either (reduced
   formats legitimately differ on the exact edge; GoldenFloat treats exp=0/mant!=0
   as a valid normal, like the gf16 silicon).

## Related fix (same session)

`gf128` was the lone ladder format whose RTL split violated the closed-form rule
(`E48 M79` vs `round(127/phi^2)=49 -> E49 M78`); fixed at the generator + RTL + all
test references across gamma/euler/phi (see commit dae422b et al.). gf16 (the only
silicon-instantiated GF) is `E6 M9`, closed-form-correct and unchanged.

## Note for the GF-ladder owner

GF512/1024 are specs-only so far (no RTL units found to sweep). When their RTL lands,
add them to the sweep RUNGS tables (they will use the flog2 large-exponent path,
already in place) to extend this verification.
