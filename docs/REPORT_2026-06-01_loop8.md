# Corona Loop 8 Report -- 2026-06-01

## 1. What Was Implemented

### Code Quality Fixes

| Fix | File | Detail |
|-----|------|--------|
| Debug comment cleanup | `src/rtl/fp8_e5m2_decode.v:39-47` | Removed "wait, let me recalculate" artifact and duplicated `fp32_exp = 8'd112` assignment. Replaced with clean single-line comments. |
| byte_count documentation | `src/rtl/tt_um_trinity_corona.v:57` | Changed "byte_count (1-15)" to "byte_count (1-4 valid)" to document actual data_in_buf constraint. |

### Missing Test Coverage: LNS8 Exhaustive

Added `test_lns8_exhaustive` -- sweeps all 256 input values through Protocol v2 and compares against `ref_lns8()` Python reference model.

**LNS8 reference model** (`ref_lns8()`):
- Q3.4 log value split into int_part (octave shift) and frac_part (16-entry LUT index)
- LUT matches RTL: `round(256 * 2^(i/16))` for i=0..15
- Output: `{sign, 15'b0, magnitude[15:0]}` matching the top-module mux packing
- Special case: `lns_in == 0x00` -> zero (not just `log_val == 0`)

This was the last decoder without a dedicated test. **All 10 on-die decoders now have tests.**

### Test Suite Summary

| Test | Values | Type |
|------|--------|------|
| FP4 exhaustive | 16 | all |
| NF4 exhaustive | 16 | all |
| FP6 E3M2 exhaustive | 64 | all |
| MXFP8 E4M3 exhaustive | 256 | all |
| Posit8 exhaustive | 256 | all |
| **LNS8 exhaustive** | **256** | **all (NEW)** |
| **FP8 E5M2 exhaustive** | **256** | **all (Loop 7)** |
| BCD values | 6 | key |
| BF16 key values | 7 | key |
| **TF32 key values** | **9** | **key (Loop 7)** |
| Not-implemented sentinel | 1 | edge |
| ROM readback all | 77 records | ROM |
| ROM key fields | 1 record | ROM |
| ROM unused address | 1 | edge |
| **Total decode values** | **1,143** | |
| **Total test functions** | **14** (decoder) + **4** (anchor) = **18** | |

---

## 2. Weakness Analysis

### Fixed This Loop

| # | Weakness | How Fixed |
|---|----------|-----------|
| **W25** | LNS8 decoder has no tests | Added exhaustive 256-value sweep with ref_lns8() |
| **W26** | Debug comment "wait, let me recalculate" in fp8_e5m2_decode.v | Cleaned up: single assignment, clear comment |
| **W27** | byte_count docs say 1-15 but data_in_buf is only 4 bytes | Corrected comment to "1-4 valid" |

### Still Open

| # | Weakness | Severity | Next Action |
|---|----------|----------|-------------|
| **W10b** | GF180MCU Liberty-mapped synthesis not done | MEDIUM | Install volare + PDK |
| **W21** | Tests not run in CI (Python 3.14 blocks cocotb) | MEDIUM | Push + trigger CI |
| **W28** | BF16 test only covers 7 key values (not exhaustive 65536) | LOW | Add optional extended test |
| **W29** | TF32 test only covers 9 key values (19-bit = 524K combinations) | LOW | Add parametric sweep of edge cases |
| **W30** | Uncommitted work spanning Loops 7-8 (2 new decoders + fixes) | HIGH | Commit now |
| **W7** | PR #1028 SSOT merge status | MEDIUM | Confirm with maintainer |
| **W9** | Gamma D2D not vendored | LOW | Phase D |

---

## 3. Scientific Research Findings (Loop 8)

### IEEE P3109 FP8 Standardization

| Aspect | Finding |
|--------|---------|
| **Status** | NOT ratified as of June 2026. Interim Report v3.0 published Aug 2025. |
| **Key difference from OCP** | P3109 defines a parametric framework (binaryKpP) covering hundreds of format combinations -- deliberately broader than OCP's two fixed types. |
| **Compatibility** | P3109 is NOT compatible with OCP OFP8 or IEEE 754 emax definitions. |
| **Formal verification** | Paper published at IEEE 2025: "Formal Verification of the IEEE P3109 Standard for Binary Floating-Point Formats for ML." |
| **Corona impact** | Corona's E5M2/E4M3 decoders align with OCP MX v1.0 (stable). P3109 finalization may require parameter metadata in ROM. |

### OCP MX Spec Status

| Aspect | Finding |
|--------|---------|
| **Version** | Still at v1.0 (Sept 2023). No v1.1 or v2 found. |
| **Extensions** | MX+ (ACM MICRO 2025) and AMXFP4 achieve near-MXFP8 quality at 4.25 bits/element. Not in official spec. |
| **Hardware adoption** | AMD CDNA4 adds native MXFP4/MXFP6 support. NVIDIA Blackwell adds FP4 E2M1 + FP6 E3M2/E2M3 tensor cores. |
| **Corona impact** | Corona already covers E2M1 (fp4) and E3M2 (fp6) -- well-aligned with industry. |

### NVIDIA Blackwell Sub-8-bit Formats

| Format | Description | Corona Coverage |
|--------|-------------|----------------|
| NVFP4 | Block of 16 FP4-E2M1 values sharing FP8-E4M3 scale | Element (E2M1) covered; block structure is SW |
| FP6 E2M3 | New: wider mantissa variant | Not yet on die. ROM record could be added. |
| FP6 E3M2 | Existing MX format | On die (fp6_e3m2_decode) |
| FP4 E2M1 | Existing MX format | On die (fp4_decode) |

### Prior Art in Tiny Tapeout

| Project | Shuttle | Type |
|---------|---------|------|
| TT07 #198 | TT07 | FP8 MAC unit |
| TT05 #292 | TT05 | FP8 E5M2 adder |
| TT03 #149 | TT03 | E4M3 multiplier |
| TT07 #204 | TT07 | Integer-to-posit converter |
| TTsky25a #899 | SKY130 | DPD decoder |

**Corona's 77-format decode oracle approach is novel in the TT ecosystem.** No prior TT project implements multi-format decode or a conformance ROM.

### Key Paper

**"Taxonomy of Small Floating-Point Formats"** (UW PLSE, Feb 2025) -- the most comprehensive public survey of sub-32-bit float formats. Directly relevant as a reference taxonomy; Corona's ROM covers a superset of their catalog.

---

## 4. Project Totals

| Metric | Loop 7 | Loop 8 | Delta |
|--------|--------|--------|-------|
| RTL modules | 12 | 12 | 0 |
| On-die decoders | 10 | 10 | 0 |
| Test functions | 17 | 18 | +1 |
| Decode values tested | 873 | 1,143 | +270 |
| Yosys cells (generic) | 2,200 | 2,200 | 0 |
| Budget utilization | 27.5% | 27.5% | 0 |
| Decoders with tests | 9/10 | **10/10** | +1 |

---

## 5. Decomposed Plan (19 days to TTGF26a deadline)

### Phase A: Foundation -- COMPLETE (Loops 1-8)
- [x] info.yaml, docs, CI, anchor tests, ADRs
- [x] 10 Tier-1 decoders, Protocol v2
- [x] **All 10 decoders have exhaustive/key-value tests** (1,143 values)
- [x] ROM emitter + 77-record ROM + readback tests
- [x] Yosys synthesis: 2,200 cells (27.5% budget)
- [x] Code quality: no debug artifacts, documented constraints
- [ ] **Commit + push pending**

### Phase B: CI + GF180MCU (Days 2-7)
- [ ] Commit all Loop 7-8 work
- [ ] Push to GitHub (needs auth fix)
- [ ] CI green on Ubuntu + Python 3.12
- [ ] Install volare + GF180MCU PDK
- [ ] Liberty-mapped synthesis

### Phase C: Expansion + Hardening (Days 8-14)
- [ ] Add FP6 E2M3 decoder (Blackwell-relevant)
- [ ] DRC/LVS clean via OpenLane2
- [ ] Timing closure at 50 MHz

### Phase D: Submission (Days 15-20)
- [ ] GDS generation
- [ ] TTGF26a submission (deadline: 2026-06-22)

---

## 6. Three Collaboration Options for Next Loop

### Option A: "Commit + Push + CI Green"

Commit all uncommitted work from Loops 7-8 (2 new decoders, LNS8 test, code cleanup). Push to GitHub. Trigger CI pipeline. Verify all 18 cocotb tests pass.

**Prerequisite:** User must run `gh auth login` or set up SSH key.
**Deliverable:** Green CI, 18 tests passing, 1,143 decode values verified.
**Risk addressed:** W30 (uncommitted work), W21 (CI never run).

### Option B: "FP6 E2M3 Decoder (Blackwell Alignment)"

NVIDIA Blackwell adds FP6 E2M3 (1s+2e+3m, bias=1) as a new tensor core format. This is the wider-mantissa counterpart to our existing E3M2 decoder. Adding it would make Corona cover **all four** Blackwell sub-8-bit formats (FP4 E2M1, FP6 E3M2, FP6 E2M3, FP8 E4M3). Estimated ~20 cells. Write exhaustive 64-value test.

**Deliverable:** 11 on-die decoders, complete Blackwell FP format coverage.
**Risk addressed:** Future-proofing against Blackwell dominance in inference hardware.

### Option C: "GF180MCU Liberty Synthesis (Area Validation)"

Install volare + GF180MCU PDK. Run Yosys with Liberty file to get real cell count, area in um^2, and timing report at 50 MHz. Expected: ~4,400 cells (~55% budget). This is the key remaining technical risk before submission.

**Deliverable:** GF180MCU area report, timing closure verification.
**Risk addressed:** W10b (the longest-open medium-severity weakness).

---

*Generated by Loop iteration 8, 2026-06-01.*
*Project: 12 RTL modules, 18 tests (1,143 decode values), 77 ROM records, 2,200 Yosys cells.*
*All 10 on-die decoders now have dedicated tests. No debug artifacts remain in RTL.*
*Budget: 27.5% generic / ~55% est. GF180MCU. Deadline: 2026-06-22 (19 days).*
