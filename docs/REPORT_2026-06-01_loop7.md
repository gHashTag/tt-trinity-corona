# Corona Loop 7 Report -- 2026-06-01

## 1. What Was Implemented

### Two New Tier-1 Decoders

| Decoder | File | fmt_id | Input | Output | Cells |
|---------|------|--------|-------|--------|-------|
| **tf32_decode** | `src/rtl/tf32_decode.v` | 9 | 19-bit TF32 (1s+8e+10m) | FP32 (wire-concat) | 26 |
| **fp8_e5m2_decode** | `src/rtl/fp8_e5m2_decode.v` | 10 | 8-bit FP8 E5M2 (1s+5e+2m, bias=15) | FP32 | 32 |

**TF32** is a pure wire-concatenation decoder (zero-extends 10-bit mantissa to 23 bits). Identical structure to bf16_decode but with 19-bit input.

**FP8 E5M2** handles all IEEE-like cases: normal, subnormal (2-bit mantissa normalization), zero, Inf, and NaN. Subnormal logic normalizes the 2 possible leading-one positions (mant=1x -> exp=112, mant=01 -> exp=111).

### Integration into Top Module

- Added `FMT_TF32 = 7'd9` and `FMT_FP8_E5M2 = 7'd10` localparams
- Instantiated both decoders with proper port connections
- Added mux cases in decoder output selector
- Added status wires to `_unused` tie-off

### ROM Catalog Updated

- Set `FLAG_ON_DIE` for fmt_id 9 (tf32) and fmt_id 10 (fp8_e5m2) in `tools/gen_rom.py`
- Regenerated `src/rtl/format_rom.v` (77 records, 6,160 bits)

### Tests Added

- `test_tf32_key_values`: 9 key values (+0, -0, 0.5, 1.0, 2.0, 3.0, +Inf, -Inf, NaN)
- `test_fp8_e5m2_exhaustive`: all 256 values with Python reference model
- Python reference models: `ref_tf32()` and `ref_fp8_e5m2()` with full subnormal/special handling

### Build Files Updated

- `info.yaml`: added tf32_decode.v and fp8_e5m2_decode.v to source_files (12 entries)
- `test/Makefile`: added both new source files
- `tools/synth_stat.tcl`: added both new read_verilog lines

### Yosys Synthesis: 2,200 Cells

| Module | Cells | % of Total |
|--------|-------|-----------|
| Top (FSM + decoder mux + ROM readback) | 1,007 | 45.8% |
| format_rom (77x80-bit) | 812 | 36.9% |
| nf4_decode | 99 | 4.5% |
| lns8_decode | 88 | 4.0% |
| bcd_decode | 33 | 1.5% |
| mxfp8_e4m3_decode | 32 | 1.5% |
| fp8_e5m2_decode | 32 | 1.5% |
| posit8_decode | 31 | 1.4% |
| tf32_decode | 26 | 1.2% |
| bf16_decode | 23 | 1.0% |
| fp6_e3m2_decode | 13 | 0.6% |
| fp4_decode | 4 | 0.2% |
| **TOTAL** | **2,200** | **100%** |

**Budget utilization: 27.5%** (2,200 / 8,000 cells for 4x4 tiles).
Delta from Loop 6: +168 cells (+8.3%), from new decoders (58 cells) + slightly larger mux/top (110 cells).

---

## 2. Weakness Analysis

### Fixed This Loop

| # | Weakness | How Fixed |
|---|----------|-----------|
| **W22** | Room for more decoders (6K cells free) | Added tf32 + fp8_e5m2; now 10 on-die decoders |
| **W23** | tf32 not on die despite trivial decode | tf32_decode.v: 26 cells, wire-concat |
| **W24** | fp8_e5m2 not on die despite being OCP-adjacent | fp8_e5m2_decode.v: 32 cells with full IEEE handling |

### Still Open

| # | Weakness | Severity | Next Action |
|---|----------|----------|-------------|
| **W10b** | GF180MCU Liberty-mapped synthesis not done | MEDIUM | Install volare + GF180MCU PDK |
| **W21** | Tests not run in CI (Python 3.14 blocks cocotb) | MEDIUM | Push to GitHub, trigger CI |
| **W25** | New tests (tf32, fp8_e5m2) not verified in simulation | MEDIUM | Run cocotb locally or in CI |
| **W7** | PR #1028 SSOT merge status | MEDIUM | Confirm with t27 maintainer |
| **W17** | ROM data not cross-verified against upstream SSOT | MEDIUM | Compare when PR merges |
| **W9** | Gamma D2D not vendored | LOW | Phase D |
| **W14** | Takum16 license | LOW | Contact Hunhold |

---

## 3. Scientific Research Findings (Loop 7)

### FP8 E5M2 Format Analysis

| Aspect | Finding |
|--------|---------|
| **Origin** | OCP Microscaling (MX) spec + IEEE WG P3109 draft. Also adopted by NVIDIA H100 (native hardware). |
| **Key difference from E4M3** | Has Inf and NaN (like IEEE). E4M3 uses max-exponent+max-mantissa as NaN instead. |
| **Dynamic range** | 2^(-16) to 57,344 (vs E4M3: 2^(-9) to 448). Much wider range, lower precision. |
| **Use case** | Gradient computation in training (where range matters more than precision). E4M3 for forward pass. |
| **Subnormal count** | Only 3 subnormal values (mant=01,10,11) due to 2-bit mantissa — simplest subnormal logic possible. |

### TF32 Format Analysis

| Aspect | Finding |
|--------|---------|
| **Origin** | NVIDIA Ampere (A100), 2020. Not a storage format — only used in tensor cores. |
| **Key insight** | Same exponent range as FP32 (8-bit exp) but truncated mantissa (10 bits vs 23). |
| **Decode complexity** | Zero — pure bit concatenation with zero-fill. No normalization, no special cases. |
| **Why include it** | Demonstrates that Corona handles variable-width inputs (19-bit) cleanly. |

---

## 4. Project Totals

| Metric | Loop 6 | Loop 7 | Delta |
|--------|--------|--------|-------|
| RTL modules | 10 | 12 | +2 |
| RTL lines | 745 | ~860 | +115 |
| On-die decoders | 8 | 10 | +2 |
| Test cases | 15 | 17 | +2 |
| Decode values tested | 608 | 873 | +265 |
| ROM records | 77 | 77 | 0 |
| Yosys cells (generic) | 2,032 | 2,200 | +168 |
| Budget utilization | 25% | 27.5% | +2.5% |
| Formats with FLAG_ON_DIE | 8 | 10 | +2 |

---

## 5. Decomposed Plan (19 days to TTGF26a deadline)

### Phase A: Foundation -- COMPLETE (Loops 1-7)
- [x] info.yaml, docs, CI, anchor tests, ADRs
- [x] 10 Tier-1 decoders, Protocol v2, exhaustive tests
- [x] ROM emitter + 77-record ROM + readback tests
- [x] Yosys synthesis: 2,200 cells (27.5% budget)
- [x] Git committed (pending push)

### Phase B: GF180MCU Validation (Days 2-7)
- [ ] Install volare + GF180MCU PDK
- [ ] Liberty-mapped synthesis (real cell count + area in um^2)
- [ ] Push to GitHub, trigger CI
- [ ] Verify all 17 tests pass in CI (Ubuntu + Python 3.12)

### Phase C: Expansion + Hardening (Days 8-14)
- [ ] Add decimal32_decode, int8_decode if area permits
- [ ] String table ROM (if area permits)
- [ ] DRC/LVS clean via OpenLane2
- [ ] Timing closure at 50 MHz

### Phase D: Submission (Days 15-20)
- [ ] GDS generation
- [ ] TTGF26a submission (deadline: 2026-06-22)
- [ ] Post-silicon test plan

---

## 6. Three Collaboration Options for Next Loop

### Option A: "Push to GitHub + CI Green"

Push all commits (including the 2 new decoders) to GitHub. Trigger CI pipeline. Verify all 17 cocotb tests pass on Ubuntu with Python 3.12. This validates tf32 and fp8_e5m2 end-to-end in simulation.

**Deliverable:** Green CI pipeline, 17 tests passing, 873 decode values verified.
**Risk addressed:** W21 (tests not run), W25 (new decoders unverified in sim).
**Prerequisite:** User must run `gh auth login` or configure SSH key for push access.

### Option B: "GF180MCU Liberty-Mapped Synthesis"

Install volare + GF180MCU PDK (`gf180mcuD`). Run Yosys with the real Liberty file to get actual cell count, area in um^2, and timing report at 50 MHz. With 2,200 generic cells, we expect ~4,400 GF180MCU cells (55% budget) -- still safe.

**Deliverable:** GF180MCU area report, timing closure at 50 MHz, tile utilization.
**Risk addressed:** W10b (Liberty-mapped synthesis).

### Option C: "Add 2 More Decoders + Commit All"

With 5,800 cells of headroom, add `int8_decode` (trivial sign-extension, ~5 cells) and `decimal32_decode` (DPD->BCD unpacking, ~200 cells). This brings on-die decoders to 12, covering all 3 major encoding families (IEEE FP, posit, BCD/integer). Commit everything and write final Phase A summary.

**Deliverable:** 12 on-die decoders, updated ROM, exhaustive tests, clean commit.
**Risk addressed:** Format coverage breadth, Phase A completeness.

---

*Generated by Loop iteration 7, 2026-06-01.*
*Project: 12 RTL modules (~860 lines), 17 tests (873 values), 77 ROM records, 2,200 Yosys cells.*
*10 on-die decoders covering IEEE FP, OCP MX, posit, LNS, BCD, and compression formats.*
*Budget: 27.5% (generic) / ~55% (est. GF180MCU). Deadline: 2026-06-22 (19 days).*
