# Proposal: align GoldenFloat gf16 software rounding to IEEE ties-to-even

Ready-to-apply change set for the gf16 **software** stack to round-ties-to-even
(the mode the spec text claims), with the measured blast radius. **Not applied to
the live baseline** -- it shifts the conformance goldens, so it is a program-owner
decision gated on a full conformance + 16-language regen run. Companion to
`GF16_ROUNDING_CONFORMANCE.md`.

## Current state (consistent, half-up)

The whole software stack rounds **half-up** (verified):
- `t27/specs/numeric/gf16.t27` `gf16_encode_f32`: `if (discarded & 0x2000) mant += 1`
- `t27/conformance/gf16_ref.py` `encode`: `int(frac * 512 + 0.5)`
- `t27/conformance/gf16_vectors.json`: derived from the above.

(The fabricated silicon `gf16_mul` rounds ties-to-**zero**; that is frozen and NOT
changed by this proposal. `gamma/src/gf16_v3_mul.v` is the verified ties-to-even RTL
variant for a future regen.)

## Blast radius (measured)

- Committed `gf16_vectors.json`: **1 of 36** vectors changes -- `planck_reduced`
  (1.054571817e-34), mant 1 (half-up) -> 0 (ties-even). 1 ULP, exact tie.
- Random sweep of 200000 f32 in [-8,8]: **0** differ -- exact ties are measure-zero
  on random reals; only deliberately-halfway values differ, always by 1 ULP.
- Task impact: none (the Defect-1 trained-model studies show ULP-scale gf16
  differences do not move accuracy).

## Change set

### 1. `t27/specs/numeric/gf16.t27` -- `gf16_encode_f32`
Replace the half-up round with ties-to-even (add the kept-LSB to the tie case):
```
    // Round-to-nearest, ties to even
    const discarded = f32_mant & 0x3FFF;
    const half = 0x2000;
    const round_up = (discarded > half) or (discarded == half and (mant & 1) == 1);
    if (round_up) {
        mant += 1;
        if (mant > MANT_MASK) { mant = 0; if (gf16_exp < EXP_MAX) gf16_exp += 1; }
    }
```
(and restore the comment to "ties to even", which then matches the code).

### 2. `t27/conformance/gf16_ref.py` -- `encode`
Replace `shifted = int(frac * (1 << MANT_BITS) + 0.5)` with a ties-to-even step:
```
    scaled = frac * (1 << MANT_BITS)
    fl = int(scaled); rem = scaled - fl
    shifted = fl + (1 if rem > 0.5 else (0 if rem < 0.5 else (fl & 1)))
```

### 3. `t27/conformance/gf16_round` (integer round)
If integer rounding should also be ties-to-even, replace Zig `@round` (ties-away)
with a ties-to-even step and revert the test assertion (`gf16_round_half_up`,
currently corrected to 3.0, would become 2.0 for 2.5). Otherwise leave as ties-away
(documented).

## Validation checklist (owner, with the toolchain)

1. Apply 1+2; regenerate `gf16_vectors.json` from the updated `gf16_ref.py`.
2. `python3 conformance/gf16_ref.py` round-trip + `run_conformance` -> green.
3. Re-run Corona's gf16 cross-checks against the regenerated vectors
   (`tt-trinity-corona`: `test_rom_spec_crosscheck.py`, `test_formal_goldens.py`, ...).
4. Regenerate the 16-language gf16 libraries from `gf16.t27`; fix the Zig codegen
   first -- `gen/zig/specs/numeric/gf16.zig` does not compile under zig 0.16.0
   (`for (0..5) {` needs a loop payload) -- then run the generated test suites.
5. Confirm the only golden delta is `planck_reduced` (1 ULP).

## Recommendation

Low urgency: the stack is self-consistent at half-up and the silicon is ties-to-zero
regardless, so software ties-to-even matches the *stated intent* but neither the
current software nor the chip. Adopt it only if IEEE conformance of the generated
software libraries is a goal; the change is verified-small (1 vector, 1 ULP) and the
RTL variant (`gf16_v3_mul`) is already staged. Otherwise the documentation is now
truthful as-is (half-up software, ties-zero silicon, ties-even available).
