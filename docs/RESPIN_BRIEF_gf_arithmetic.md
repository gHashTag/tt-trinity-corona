# Respin decision brief -- TRI-NET GoldenFloat arithmetic (2026-06)

One-page go/no-go for the next SKY26b shuttle, consolidating the loop-119..130
arithmetic audit across the four dies (Gamma, Phi, Euler taped out 2026-05-17/18;
Corona = the conformance-oracle die). All findings are source-only; the fabricated
GDS of every die is frozen. Two active on-silicon defects were found; both have
verified drop-in fixes now staged on every affected die.

> Full audit index (all four dies, every block, every script, re-run instructions):
> [`AUDIT_COMPLETE.md`](AUDIT_COMPLETE.md). Fix-coverage invariant:
> `tools/fix_coverage_matrix.py`.

## Recommendation

**The gf16_mul defect is a real, on-path numerical regression (~11x dot-product RMS
error), but its TASK-level impact is modest: on a synthetic 10-class linear classifier
it changes the predicted class on only ~0.24% of inputs vs a corrected design (the
inherent gf16 rounding floor itself flips ~0.12%).** So the ~11x MAC RMS largely
washes out at argmax -- the sparse halving error only matters near decision
boundaries. Net: it is **not a respin emergency** for the demo/research workloads the
dies were validated on, but it is a genuine defect with a verified, free fix. If a
next-shuttle slot is taken for any reason, fold in the staged `gf16_v2_*` (and
`bitnet_encoder_v2`) fixes. **The synthetic ~0.24% has now been confirmed on a
TRAINED model (`gamma/test/impact_trained_gf16.py`): a LogisticRegression on sklearn
digits (92.8% accuracy), with trained weights + test inputs quantized to gf16 and
each logit run through the ACTUAL RTL, flips only 3/2250 = 0.13% of predictions
shipped-vs-corrected, with a negligible accuracy delta (92.76% vs 92.80%) -- even
though the defect is genuinely ACTIVE (73% of logits differ at the ULP level).
Trained decision margins are wider than random ones, so the real-workload impact is
if anything SMALLER than the synthetic proxy.** This closes the prior caveat: the
gf16_mul defect is task-quiet on a trained classifier.

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
  argmax.
- **Trained-model task-level impact (`gamma/test/impact_trained_gf16.py`,
  LogisticRegression on sklearn digits, 15 PCA + bias = one dot16, 5 splits / 2250
  test samples, logits run through the ACTUAL RTL):** the defect is ACTIVE (73% of
  logits differ shipped-vs-v2 at the ULP level) but flips only **3/2250 = 0.13%** of
  predictions, with shipped accuracy 92.76% vs corrected 92.80% (a 1-sample delta).
  The trained number is at/below the synthetic proxy -- wider trained margins absorb
  the sparse halving error. Confirms: not a respin emergency for these workloads.
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

## Defect 3 -- blake3_anchor G() omits all 4 XOR diffusion steps (ACTIVE, Gamma + Euler)

- **Mechanism:** the on-die DePIN RECEIPT signer `blake3_anchor` implements BLAKE3's
  quarter-round G() WITHOUT the four XOR steps (`d = ROTR(d ^ a)`, `b = ROTR(b ^ c)`).
  The XOR is BLAKE3's core nonlinear diffusion; without it the 256-bit digest is a
  near-LINEAR function of the 512-bit input.
- **Impact:** the hash is NOT preimage/collision-resistant -- the header's "~2^96"
  security claim is false. The per-die RECEIPT signatures are cryptographically weak
  / forgeable. This is a SECURITY defect, distinct from the numerical ones, and
  (unlike gf16_mul's task-quiet error) it is qualitative -- a broken hash is broken.
- **On which dies:** Gamma, Euler (instantiated as the receipt signer u_hash); absent
  on Phi and in the t27 master.
- **Verification / fix:** `gamma/test/blake3_anchor_verify.py` confirms the shipped
  RTL == a no-XOR model and != real BLAKE3-G; the corrected `blake3_anchor_v2`
  (XORs restored) == real BLAKE3-G. Staged on Gamma + Euler. (v2 is still a 4-round /
  fixed-schedule "mini"; the XOR fix is the security-critical one.)

## Per-die exposure + fix-staged matrix

| die | gf16_mul defect | gf16_v2 staged | bitnet defect | bitnet_v2 staged |
| --- | :-: | :-: | :-: | :-: |
| Gamma | yes (MAC) | yes | yes | yes |
| Phi   | yes (MAC) | yes | no  | n/a |
| Euler | yes (MAC) | yes | yes | yes |
| Corona | n/a (no gfN compute) | -- | n/a | -- |

**Defect 3 (blake3_anchor crypto):** active on Gamma + Euler (receipt signer);
`blake3_anchor_v2` staged on both; absent on Phi/Corona.

**Recommendation update:** Defect 3 is a security defect (broken RECEIPT hash), which
is a stronger respin driver than the numerical Defect 1 -- if the DePIN receipts are
relied upon, the shipped Gamma/Euler signatures are forgeable. Fold `blake3_anchor_v2`
into any respin alongside `gf16_v2_*` / `bitnet_encoder_v2`.

## Checked and cleared (not respin drivers)

- **Shared neuromorphic / mesh blocks** (Gamma + Euler, audited 2026-06,
  `test/shared_blocks_audit.py`): all CORRECT -- `d2d_holo_mesh` (4-port D2D stub:
  TX map + layer-frozen SYNC gate + RX latch), `nca_entropy_monitor` (81-cell
  nonzero popcount, in_band [31,80] + violation pulse), `holo_lut_pe` (binary MAP-B
  VSA: bind/unbind=XOR self-inverse, bundle=OR, round-trip holds), `trinity_cortex_8col`
  (spike_count == popcount(spike_vec) over 200 random cycles). (holo_lut_pe /
  trinity_cortex_8col are Gamma-only.)
- **Corona (conformance-oracle die):** all decoder/golden sweeps re-confirmed green
  (the multi-format decoders mxfp8/fp6/nf4/lns8/posit8/bf16/tf32/bitnet/... were
  exhaustively swept loops 75-77, 14 decoders / 1892 values cross-validated); full
  Python test suite passes (the only non-runs locally are cocotb-gated, which run in
  CI). Full-design verilator lint = 0 warnings.
- **Phi (nano die) instantiated blocks** (audited 2026-06, `test/phi_audit.py`):
  `phi_anchor_post` CORRECT (Lucas-chain POST, passes clean + detects a corrupted
  value), `sacred_constants_rom` CORRECT (60-entry Q3.5 constant ROM -- all 59
  residual constants within +-1 LSB, 14 clamp entries -> 0x7F, zero region clean,
  0x47 watermark intact; no transcription error), `phi_mesh_bridge` CORRECT
  (friend/foe gate, saturating drop counter). One LATENT bug in `phi_d2d_lite` (the
  die-to-die serial link): RX requires a 2-cycle START but its own TX emits a
  1-cycle START, so the TX->RX path delivers NOTHING -- the receive side of the
  inter-die mesh is non-functional. **No impact on the current single-die TTSKY26b
  shuttle** (no second die to communicate with); it is a real bug for the intended
  multi-die mesh feature. `phi_d2d_lite_v2` fixes the RX framing (RX_IDLE ->
  RX_DATA; loopback round-trips every packet). Frozen source untouched. (Phi's
  lucas_rom / hwrng_lfsr are identical to Gamma's, already cleared.)
- **Instantiated leaf blocks** (Gamma + Euler, audited 2026-06, `test/leaf_audit.py`):
  `phi_pll_div` CORRECT (5 ticks / 8 clocks = 0.625 ~ 1/phi), `wishbone_full`
  CORRECT (scratch regs 4..15 R/W, regs 0..3 RO status mirrors, RO writes ignored),
  `wb_status_reg` CORRECT (documented bit-packing + `alive` toggle). One LATENT bug
  in `alu9_decoder`: op7 TRI_BIND uses bitwise `^` on signed lifts instead of the
  VSA bind (= ternary multiply) -- 6/9 input pairs wrong, incl. bind(x,0) != 0 and
  bind(1,1)=bind(-1,-1)=0. **Benign on the shipped dies:** u_alu is driven by random
  hwrng_word bits and its result feeds `ring27_memory` (an entropy ring whose only
  consumer is a liveness flag), so no workload depends on the ALU output.
  `alu9_decoder_v2` fixes BIND (81/81 vs reference); frozen source untouched.
- **Control / datapath mesh fabric** (instantiated on Gamma + Euler, audited
  2026-06, `test/fabric_audit.py`): `trinity_router_2x2` CORRECT (forward one-hot
  addressing to the dst tile + fair round-robin return), `trinity_mesh_2x2` CORRECT
  (end-to-end LOAD/COMPUTE/READ of [1,2,3,4].[1,2,3,4] = 0x47C0 = 30.0),
  `trinity_master_fsm` CORRECT (drives that path). One LATENT contract bug found in
  `multi_tile_receipt`: its four per-tile `agg <= agg ^ tN` are non-blocking
  assignments to the same register, so simultaneous distinct-tile receipts collapse
  to the last (t3) -- the XOR-sum is wrong for >1 tile/cycle. **Benign on the
  shipped dies:** all four tile ports are tied to ONE replicated source, so there
  are no distinct simultaneous tiles to drop and the bug gives the desired
  single-source XOR accumulate (a *correct* 4-tile XOR of four identical inputs
  would instead give 0); `attested_mask`/`all_attested` are correct regardless.
  `multi_tile_receipt_v2` folds all simultaneous contributions for future
  distinct-tile reuse (NOT a drop-in under the current replicated hookup). Frozen
  source untouched. (Also fixed a stale, non-CI testbench `tb_integration_mesh.v`
  whose wrong local packet macros made it mis-fail.)
- **Receipt / identity / nonce-path primitives** (instantiated on Gamma + Euler,
  audited 2026-06 against clean references, `test/receipt_path_audit.py`): all
  **CORRECT** -- `crc32_receipt` (CRC-32 IEEE 802.3; canonical "123456789" ->
  0xCBF43926 and 40/40 random vs zlib), `lucas_rom` (L2..L7 == Lucas sequence),
  `hwrng_lfsr` (16-bit nonce LFSR: maximal-length, period 65535, visits every
  nonzero state once; RTL == model -- so no short-period nonce reuse), and
  `cassini_post` (Cassini-Lucas POST: passes clean **and** detects a corrupted
  Lucas value -> a live checker, not a vacuous pass). This **bounds the security
  exposure**: of everything on the receipt/identity path, only `blake3_anchor`
  (Defect 3) is broken; the CRC, nonce source, identity ROM, and POST are sound.
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
