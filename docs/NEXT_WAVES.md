# TRI-NET next waves -- roadmap + status (2026-06)

Forward work-stream plan, grounded in the in-repo "Wave-N" markers and the staged
post-silicon fixes. Status as of this loop.

## Wave 5 -- full-round BLAKE3 (TTIHP27a) -- DONE (staged + verified)

The RECEIPT signer's hash. Trajectory: shipped `blake3_anchor` omitted all 4 XOR
diffusion steps (Defect 3, near-linear); `blake3_anchor_v2` restored the XOR but was
a reduced 4-round / no-permutation "mini"; **`blake3_anchor_v3` (this loop)** is the
Wave-5 target -- full **7 rounds + per-round message permutation**
(PERM=[2,6,3,10,7,0,4,13,1,11,12,5,9,14,15,8]), verified == a real 7-round+permuted
BLAKE3-G reference (`test/blake3_anchor_v3_verify.py`), staged on Gamma + Euler, CI-
gated. **`blake3_anchor_v4`** then completes the real BLAKE3 **compression function**:
configurable chaining value (state[0..7]), 64-bit counter, block_len, flags
(state[12..15]), and the full 16-word output (out[i]=state[i]^state[i+8],
out[i+8]=state[i+8]^cv[i]). Verified bit-exact == the reference BLAKE3 `compress()`
over random (cv,m,counter,block_len,flags) incl. the IV-root case
(`test/blake3_anchor_v4_verify.py`); CI-gated, staged on Gamma + Euler. This is the
keyed/tree-capable primitive. **`blake3_hash_chunk`** then puts the FSM wrapper on
top: it chains the CV block-to-block and sets CHUNK_START / CHUNK_END|ROOT flags to
hash any message up to one BLAKE3 chunk (1024 bytes). Verified == a reference
single-chunk BLAKE3 validated against the OFFICIAL BLAKE3 test vectors -- 19/19
lengths (0,1,63,64,65,...,1023,1024), CI-gated, staged on Gamma + Euler. For
receipt-sized inputs this is the COMPLETE BLAKE3 hash, not just compression.
Finally **`blake3_hash`** adds the multi-chunk tree (parent nodes, counters>0, the
chunk-stack merge rule with ROOT on the final parent) for arbitrary messages up to
4 chunks (4096 B). Verified == the reference `blake3` package over all lengths
0..4096 incl 1/2/3/4 chunks, power-of-2 and partials (17/17,
`test/blake3_hash_verify.py`). The BLAKE3 line is now a complete arbitrary-length
hash (compress core -> single chunk -> tree). **`blake3_keyed_hash`** adds the keyed
MAC mode (key replaces IV as the chunk/parent CV + KEYED_HASH flag on every
compression) -- the DePIN receipt MAC; verified == `blake3.blake3(data, key=key)`
over 0..4096 incl multi-chunk (10/10, `test/blake3_keyed_hash_verify.py`). BLAKE3 is
now complete for both unkeyed hash and keyed MAC. Remaining: >4 chunks (deeper stack,
mechanical) and derive_key (a two-pass context/material variant of the same engine).

## Respin wave -- fold all staged fixes into the next tapeout

All post-silicon fixes are staged + verified (frozen dies untouched). Drop-in set for
the next shuttle: `gf16_v2_mul`/`gf16_v2_add` (Defect 1), `bitnet_encoder_v2`
(Defect 2), `blake3_anchor_v2`/**`v3`** (Defect 3 -- ship v3 for full diffusion),
`multi_tile_receipt_v2`, `alu9_decoder_v2`, `phi_d2d_lite_v2` (RX framing), gf128
split E49 M78. Go/no-go: `RESPIN_BRIEF_gf_arithmetic.md`; fix coverage:
`tools/fix_coverage_matrix.py`; full re-validation: `tools/audit_all.py` (13/13).
Optional: `gf16_v3_mul` (IEEE ties-to-even) if strict rounding conformance is wanted
(`GF16_TIES_EVEN_PROPOSAL.md`).

## Wave 7 -- Trinity SoC (host register access)

`wishbone_full` (WB-lite, 16 regs) is in and verified (`leaf_audit.py`). Next:
full Wishbone B4 compliance + a CPU-less host control path beyond the demo FSM.

## GF ladder extension -- GF512 / GF1024 (in progress, other contributor)

Specs landed (t27 `gf512.t27`/`gf1024.t27`, corona oracle GF_LADDER_EXTENDED); RTL
units not yet present. When their RTL lands: add to `gf_add_sweep`/`gf_mul_sweep`
RUNGS (the flog2 large-exponent path is ready), to `gf_ladder_consistency.py`, and
the closed-form ids to `test_rom_spec_crosscheck.py` SPEC_REFERENCE. The whole GF
ladder is now verified three ways (arithmetic <=1 ULP, structural consistency,
standalone catalog oracle); extending it to 512/1024 is mechanical.

## Power / sparsity waves (39-42) -- AUDITED (`gamma/test/power_waves_audit.py`)

All dead-code library units (none instantiated on a die top -> no silicon impact).
- `sparse_skip` (Wave-40): **CORRECT** -- skip_count == popcount(sparse_mask),
  active_lanes == ~sparse_mask (zero-skip equivalence). Minor: opcode port [3:0]
  can't hold the contract opcode 0xE1 (works only via truncation to 0x1).
- `stoch_round` (Wave-41): **DEFECT** -- not stochastic rounding; rounds up with
  prob 0.5 only when LSB=1 (measured), unrelated to the fractional part, and the
  interface has no residual to form one. `stoch_round_v2` is the corrected unit:
  round up iff random byte < frac -> P(up)=frac/256 (verified unbiased, P tracks
  frac/256 across 0..255). CI-gated.
- `spec_exit` (Wave-39, exit==conf>=thresh), `null_pe` (gate==activate), `dfs_gate`
  (skip==depth>16&&!visited), `subth_clk` (clk_freq==2^divider): all **CORRECT**.
- **Opcode-width defect fixed:** `sparse_skip`(0xE1)/`subth_clk`(0xE5)/`fbb_active_path`
  (0xF2) had `[3:0]` opcode ports truncating their 8-bit sacred opcodes to the low
  nibble (collision risk); widened to `[7:0]` + full-opcode compare on all 3 dies,
  verified. (`drowsy_ret` retention left for a reuse-time audit.)
  ALL power/sparsity units now conform (`power_waves_audit.py`, 7 units + width gate).

## Recommended next-wave order

1. **Ship Wave-5 v3 in the respin set** (done/staged; highest security value).
2. **Verify GF512/1024 RTL** when it lands (mechanical, infra ready).
3. **Functionally audit the power/sparsity waves** (stoch_round / sparse_skip /
   spec_exit) -- the last instantiated-ish logic not checked against a reference.
4. **Wave 7 SoC** -- larger, design-led (host/CPU path), beyond source-only loops.
