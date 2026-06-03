# Cross-die GoldenFloat arithmetic audit (2026-06)

## What

The same `.t27` code-gen produced the GoldenFloat `gfN_add` / `gfN_mul` units for
all three TRI-NET SKY26b dies -- **Gamma**, **Phi**, **Euler** (all submitted to the
same shuttle, 2026-05-17/18). Gamma's units were found defective and fixed +
verified over loops 119-124 (see `tt-trinity-gamma/docs/GF_ARITH_FINDINGS.md`).
This audit checks whether Phi and Euler -- which ship the **same pre-fix code** --
carry the same defects. Tool: `tools/cross_die_gf_audit.py` (read-only; never
modifies any die's RTL -- all three are frozen silicon).

Two probes per rung, via iverilog: (1) `1.0 + 1.0` must give exponent `bias+1`;
(2) `max_finite + max_finite` must round to a value that **decodes as Inf**
(catches a wrong Inf constant whose mantissa field is nonzero -> decodes as NaN).

## Result

| die | buggy rungs (of 10) | detail |
| --- | :-: | --- |
| **Gamma** | **0** | all fixed (loops 119-124); full ladder verified, CI-gated |
| **Phi**   | **9** | gf4, gf8, gf12, gf20, gf24, gf32, gf64, gf128, gf256 -- only gf16 ok |
| **Euler** | **9** | identical set to Phi |

The Phi/Euler failures match Gamma's pre-fix state exactly: gf8 `1+1 -> 0.5`
(normalization), gf12 `1+1 -> 0` (too-narrow `final_exp` flushes valid exponents),
gf20/24/32/256 overflow -> NaN (wrong Inf constant), gf128/gf4 overflow -> 0,
gf64 overflow -> a bogus finite, gf256 EXP_MAX off-by-one. gf16 passes the probe on
all three dies.

## Risk assessment: shipped silicon is NOT affected

The Phi and Euler silicon top-levels (`tt_um_trinity_nano.v`,
`tt_um_ghtag_trinity_gf16.v`) instantiate **only** `gf16_dot4` and
`trinity_gf16_tile` -- the gf16 compute path. A repo-wide search finds **no
instantiation** of any of the nine buggy `gfN_add` units (gf4/8/12/20/24/32/64/128/
256); they are standalone spec-completeness module definitions, never wired into
the fabricated die. Therefore:

- **The shipped Phi/Euler chips' intended function is unaffected** -- their compute
  path is gf16, which passes the probe. (gf16 carries only the cancellation
  imprecision + mul-overflow latent bug documented for Gamma's gf16; it is shared
  by all three dies and likewise avoided by the near-1.0 workloads they run.)
- The exposure is to **future reuse**: any new design (or library consumer) that
  instantiates these gfN units would get wrong arithmetic. Gamma's fixed `src/gf*.v`
  + generators (`gen_gf_{add,mul}_fix.py`) + verification suite are the reference
  correction; `tt-trinity-gamma/src/gf16_v2_*` is the corrected gf16 for a respin.

## Compute-path primitive audit (2026-06, loop 126)

The gfN_add bugs above are in units that are NOT instantiated. The question that
matters for the shipped chips is the **instantiated** gf16 compute path. Audited:

| primitive | instantiated? | verdict |
| --- | --- | --- |
| `gf16_dot4` (4-MAC reduction tree) | yes (tiles, mesh, tops) | structurally fine, but inherits the **active `gf16_mul` defect below** |
| `gf16_mul` (via gf16_dot4) | yes (MAC path) | **ACTIVE DEFECT (loop 127):** `mant_rounded` is [8:0] not [9:0], so a product mantissa that rounds up across a binade boundary is HALVED (overflow test reads a nonexistent bit). **0.072%** of normal unit-exponent products affected. Fix = `gf16_v2_mul` |
| `tri_mant_mul` (shift-add multiplier) | yes (`fbb_active_path`) | **correct** -- standard partial-product sum, exact |
| `gf16_to_fp16` / `fp16_to_gf16` | **no** (standalone) | had an inferred **latch** (fp_out unassigned for every \|value\|<1.0) + a wrap-prone overflow add -- **fixed** (loop 126), 65536/65536 exhaustive, ported to all three dies |
| `gf16_to_posit16` / `posit16_to_gf16` | **no** (standalone) | a "simplified" stub: the posit regime is not a valid variable-length encoding. Dead code; left as-is |

**Bottom line (REVISED loop 127): there IS one active silicon arithmetic defect** --
the `gf16_mul` rounding-overflow bug, on the gf16 MAC path of all three dies, halving
~0.072% of normal products (`tt-trinity-gamma/docs/GF_ARITH_FINDINGS.md`,
`test/gf16_mul_silicon_bug.py`). It is small and data-dependent (a sparse 2x error
on individual MAC terms) but on-path and not avoided by the validated workload, so it
strengthens the respin case. The fix (`gf16_v2_mul`) exists and is verified; the
frozen `gf16_mul.v` is left as taped out. `tri_mant_mul` is correct; the converter
latch (dead code) was fixed line-wide.

## Recommendation

No action on the frozen Phi/Euler silicon. For a future Phi/Euler tapeout or any
reuse of their gfN library, port Gamma's corrected units + the `goldenfloat-arith`
verification suite (probe + sweeps + specials) into those repos -- a mechanical
port of already-verified code. This audit tool should be run on any die that
includes the gfN family before tapeout.
