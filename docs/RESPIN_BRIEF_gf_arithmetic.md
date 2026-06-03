# Respin decision brief -- TRI-NET GoldenFloat arithmetic (2026-06)

One-page go/no-go for the next SKY26b shuttle, consolidating the loop-119..130
arithmetic audit across the four dies (Gamma, Phi, Euler taped out 2026-05-17/18;
Corona = the conformance-oracle die). All findings are source-only; the fabricated
GDS of every die is frozen. Two active on-silicon defects were found; both have
verified drop-in fixes now staged on every affected die.

## Recommendation

**The gf16_mul defect is a real, on-path numerical regression (~11x dot-product RMS
error), but its TASK-level impact is modest: on a synthetic 10-class linear classifier
it changes the predicted class on only ~0.24% of inputs vs a corrected design (the
inherent gf16 rounding floor itself flips ~0.12%).** So the ~11x MAC RMS largely
washes out at argmax -- the sparse halving error only matters near decision
boundaries. Net: it is **not a respin emergency** for the demo/research workloads the
dies were validated on, but it is a genuine defect with a verified, free fix. If a
next-shuttle slot is taken for any reason, fold in the staged `gf16_v2_*` (and
`bitnet_encoder_v2`) fixes. (Caveat: the 0.24% is a synthetic-classifier proxy; a
trained net's margins could differ -- a real-workload run, Option B in the loop
reports, would sharpen it.)

## Root cause fixed upstream (2026-06)

The defective `gf16_mul` was copied into all three dies from the canonical
`t27/rtl_gen/gf16_mul.v`. That master is now fixed at the source (t27 commit
19b41635) -- both defects corrected, cross-checked EXACT-equal to the verified
`gf16_v2_mul` over 1.8M pairs -- so any future tapeout or regeneration starts
correct. The fabricated dies' frozen `src/gf16_mul.v` are deliberately NOT touched
(source must match the taped-out silicon).

## Defect 1 -- gf16_mul rounding-overflow (ACTIVE, all three compute dies)

- **Mechanism:** `mant_rounded` is `[8:0]` (M=9, not M+1); `mant_out + 1` wraps when
  the mantissa is all-ones and the overflow test `mant_rounded[9]` reads a
  nonexistent bit -> a product that rounds up across a binade boundary is **halved**.
- **Scope:** 0.072% of normal unit-exponent products (exhaustive over 262144 mantissa
  pairs, `gamma/test/gf16_mul_silicon_bug.py`).
- **Impact (measured on the gf16_dot4 MAC, `gamma/test/impact_gf16_mul.py`, 20000
  near-1.0 dot products vs exact):** shipped NMSE 1.49e-4 (~1.22% RMS); fixing the
  mul alone -> 1.29e-6 (~0.11% RMS) = **~115x NMSE / ~11x RMS** improvement. The mul
  defect dominates the MAC error despite the 0.27% dot footprint (halving a term is a
  large per-term error).
- **Task-level impact (`gamma/test/impact_task_gf16.py`, 5000 trials, 10-class linear
  classifier):** changes the predicted class on **~0.24%** of inputs vs corrected
  (the gf16 rounding floor alone flips ~0.12%). The ~11x MAC RMS mostly washes out at
  argmax. (Synthetic-classifier proxy; a trained workload could differ.)
- **On which dies:** Gamma, Phi, Euler -- `gf16_mul` is reached via `gf16_dot4` on
  every die's silicon top (the core MAC). This is on the validated MNIST/IGLA path.
- **Fix:** `gf16_v2_mul.v` (correct M+1-bit `mant_rounded`), verified faithful
  (`gamma/test/gf16_v2_verify.py`); CI-gated on all three dies. Staged everywhere.

## Defect 2 -- bitnet_encoder neuron-base aliasing (ACTIVE, Gamma + Euler)

- **Mechanism:** `ternary_dot`'s `neuron_base` is `[9:0]` but the 32 hidden neurons
  span `k*64 = 0..1984`, so it truncates mod 1024 and neurons 16..31 alias 0..15.
- **Scope:** 16 of 32 hidden neurons are duplicates -> the 64->32->8 encoder realizes
  only 16 distinct neurons (`corona/tools/bitnet_neuron_base_check.py`).
- **Severity:** moderate/latent -- the weights are a synthetic "canned demo", so no
  trained model is corrupted and golden vectors still match; but the nominal
  architecture is not met, and any future use with real weights would be wrong.
- **On which dies:** Gamma, Euler (not Phi). Fix: `bitnet_encoder_v2.v` (11-bit
  address path + hash), behavioral diff confirmed (`gamma/test/tb_bitnet_v2.v`,
  2/6 inputs differ). Staged on Gamma, Euler.

## Per-die exposure + fix-staged matrix

| die | gf16_mul defect | gf16_v2 staged | bitnet defect | bitnet_v2 staged |
| --- | :-: | :-: | :-: | :-: |
| Gamma | yes (MAC) | yes | yes | yes |
| Phi   | yes (MAC) | yes | no  | n/a |
| Euler | yes (MAC) | yes | yes | yes |
| Corona | n/a (no gfN compute) | -- | n/a | -- |

## Checked and cleared (not respin drivers)

- **gfN add/mul rungs gf4..gf256** (the wider GoldenFloat ladder): had many bugs,
  all fixed + verified in Gamma and audited cross-die -- but these units are **not
  instantiated** on any die's silicon top (standalone spec RTL), so no silicon impact.
- **gf16_to_fp16 / gf16_to_posit16 converters:** had a real inferred latch
  (gf16_to_fp16, fixed line-wide) and a posit stub -- both **not instantiated** (dead
  code, not in any GDS).
- **tri_mant_mul, gf16_dot4 structure:** correct.
- **Corona** (submission-complete oracle): full-design verilator lint = **0 warnings**.

## Evidence index

- Mechanism + rates: `tt-trinity-gamma/docs/GF_ARITH_FINDINGS.md`
- Cross-die + compute-path audit: `tt-trinity-corona/docs/CROSS_DIE_GF_AUDIT.md`
- Lint triage: `tt-trinity-corona/docs/FULL_DESIGN_LINT_TRIAGE.md`
- Scripts: `gf16_mul_silicon_bug.py`, `impact_gf16_mul.py`, `gf16_v2_verify.py`,
  `tb_bitnet_v2.v` (gamma/test); `cross_die_gf_audit.py`,
  `bitnet_neuron_base_check.py` (corona/tools)
- Loop reports 119-130: `tt-trinity-corona/docs/REPORT_2026-06-03_loop1{19..30}.md`
