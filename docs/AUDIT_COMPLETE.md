# TRI-NET post-silicon audit -- complete index (2026-06)

Single map of the post-silicon conformance audit across all four taped-out dies. The
fabricated GDS of every die is FROZEN; all corrections are source-only `*_v2` modules
staged for a respin (the frozen originals are left byte-for-byte as taped out). The
go/no-go writeup is [`RESPIN_BRIEF_gf_arithmetic.md`](RESPIN_BRIEF_gf_arithmetic.md).

## Method

Every instantiated block on every die was checked against the algorithm/contract it
claims to implement -- not just linted. Three recurring lessons:
- **Check RTL against the reference, not the comment.** Every defect was RTL that
  diverged from the spec it named (a missing XOR, a too-narrow field, a wrong bind).
- **Grade severity by how the block is WIRED.** Three real contract violations are
  benign on silicon purely because of their hookup (random-fed, replicated source,
  no second die). A truth-table bug is not automatically a silicon defect.
- **A transmitter and receiver (or spec and RTL) are two halves of one contract.**
  Test them against each other; the same op name can be right or wrong by context
  (binary XOR-bind correct in `holo_lut_pe`, ternary XOR-bind wrong in `alu9_decoder`).

## Dies

| die | role | top |
| --- | --- | --- |
| Gamma | MAX-TRUE flagship compute (32-tile) | `tt_um_trinity_max_true` |
| Euler | GF16 compute | `tt_um_ghtag_trinity_gf16` |
| Phi | nano minimal compute | `tt_um_trinity_nano` |
| Corona | 80-format conformance oracle | `tt_um_trinity_corona` |

## Defects found (all staged, frozen sources untouched)

### Active on silicon (3)
| # | defect | dies | mechanism | impact | fix |
| - | --- | --- | --- | --- | --- |
| 1 | `gf16_mul` rounding-overflow | Gamma, Euler, Phi | `mant_rounded` 1 bit too narrow -> a product rounding up across a binade is halved | ~11x MAC RMS; ~0.24% argmax flips (synthetic) | `gf16_v2_mul` |
| 2 | `bitnet_encoder` neuron aliasing | Gamma, Euler | `neuron_base` [9:0] truncates k*64 -> 16 of 32 neurons alias | latent (synthetic weights) | `bitnet_encoder_v2` |
| 3 | `blake3_anchor` missing XOR | Gamma, Euler | G() omits all 4 XOR diffusion steps -> near-linear digest | RECEIPT hash not preimage-resistant (SECURITY) | `blake3_anchor_v2` |

### Latent (benign on this shuttle) (3)
| # | defect | dies | mechanism | why benign | fix |
| - | --- | --- | --- | --- | --- |
| 4 | `multi_tile_receipt` NBA last-wins | Gamma, Euler | 4 NBA to one reg -> simultaneous tiles dropped | all 4 ports tied to one source (no distinct tiles) | `multi_tile_receipt_v2` |
| 5 | `alu9_decoder` op7 BIND | Gamma, Euler | XOR of signed lifts, not ternary multiply | fed by random LFSR bits -> entropy ring (liveness only) | `alu9_decoder_v2` |
| 6 | `phi_d2d_lite` RX framing | Phi | RX needs 2-cycle START, TX emits 1 -> receive path never delivers | single-die shuttle, no second die to talk to | `phi_d2d_lite_v2` |

Fix-coverage invariant (every affected die carries its v2): `tools/fix_coverage_matrix.py` -> COMPLETE.

**Respin-readiness of the staged fixes** (verified 2026-06): every `*_v2` module is
R-SI-1 clean (no-star checker passes; the only `*` are constant loop-index/bit-select
patterns, exempt and identical to the frozen originals), free of the harmful
width-defect class (`width_gate.py` -- WIDTHTRUNC/SELRANGE -- passes on all dies), and
has no inferred latches. The remaining verilator -Wall notes are benign WIDTHEXPAND
(safe sign/zero extension, inherited from the shipped originals). So the fixes are
drop-in-ready for a respin, not just functionally correct.

## Checked and CLEAR (no defect)

- **Arithmetic:** whole GF ladder gf4..gf256 (add+mul), gf16_dot4 MAC, VSA
  popcount, GF16<->Posit16/FP16 converters.
- **Receipt/identity/nonce path:** `crc32_receipt` (CRC-32), `hwrng_lfsr`
  (maximal-length), `lucas_rom`, `cassini_post`, `phi_anchor_post`,
  `sacred_constants_rom` (60-entry Q3.5 ROM).
- **Mesh fabric:** `trinity_router_2x2`, `trinity_mesh_2x2`, `trinity_master_fsm`.
- **Leaf:** `phi_pll_div`, `wishbone_full`, `wb_status_reg`, `phi_mesh_bridge`.
- **Shared neuromorphic/mesh:** `d2d_holo_mesh`, `nca_entropy_monitor`,
  `holo_lut_pe`, `trinity_cortex_8col`.
- **Corona oracle:** all multi-format decoders exhaustively swept (14 decoders /
  1892 values, loops 75-77); full-design verilator lint = 0 warnings.

## Audit scripts (all CI-gated)

| script | repo(s) | covers |
| --- | --- | --- |
| `test/gf16_v2_verify.py` | gamma, euler, phi | gf16_v2_mul/add vs exact-rational ref |
| `test/gf_add_sweep.py` / `gf_mul_sweep.py` etc. | gamma, euler, phi | gfN ladder vs exact-rational |
| `test/gf16_popcount_verify.py` | gamma, euler | VSA ternary matmul |
| `test/posit16_codec_verify.py` | gamma, euler, phi | Posit16 codec (dead code) |
| `test/blake3_anchor_verify.py` | gamma, euler | blake3 shipped==no-XOR; v2==real |
| `test/receipt_path_audit.py` | gamma, euler | crc32 / lucas / hwrng / cassini |
| `test/fabric_audit.py` | gamma, euler | router / mesh / multi_tile_receipt |
| `test/leaf_audit.py` | gamma, euler | phi_pll / wishbone / status / alu9 |
| `test/shared_blocks_audit.py` | gamma, euler | d2d / nca / holo_lut_pe / cortex |
| `test/phi_audit.py` | phi | phi_anchor_post / sacred ROM / bridge / d2d |
| `tools/fix_coverage_matrix.py` | corona | every affected die has its v2 |
| `tools/cross_die_gf_audit.py`, `width_defect_sweep.py`, `bitnet_neuron_base_check.py` | corona | cross-die gfN, width defects, bitnet |

CI job `instantiated-audit` (gamma/euler/phi `test.yaml`) runs the conformance
scripts as two-sided regression gates: each asserts the shipped (frozen) behaviour
AND the staged v2 fix, so a provenance break or a lost fix both fail CI.

## Re-run

```
# per die (from each repo)
python3 test/blake3_anchor_verify.py && python3 test/receipt_path_audit.py \
  && python3 test/fabric_audit.py && python3 test/leaf_audit.py \
  && python3 test/shared_blocks_audit.py            # gamma / euler
python3 test/phi_audit.py                            # phi
# cross-die (from corona)
python3 tools/fix_coverage_matrix.py
```

## Status

Audit COMPLETE across all four dies; every instantiated block checked + CI-gated.
6 defects (3 active, 3 latent), all staged with verified fixes; fix coverage
complete. No remaining autonomous engineering lever without a scheduled respin or an
external trained gf16 workload (to sharpen Defect 1's task number).
