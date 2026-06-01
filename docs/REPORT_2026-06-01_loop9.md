# Corona Loop 9 Report -- 2026-06-01

## 1. What Was Implemented

### W30 Resolved: All Loop 7-8 Work Committed

```
e7cda48 feat(corona): add tf32 + fp8_e5m2 decoders, LNS8 test, code cleanup
```
11 files changed, 643 insertions. This closes the HIGH-severity uncommitted work weakness.

### New Decoder: FP6 E2M3 (Blackwell Tensor Core Format)

| Property | Value |
|----------|-------|
| File | `src/rtl/fp6_e2m3_decode.v` |
| fmt_id | 77 (new ROM record) |
| Format | 1 sign + 2 exp (bias=1) + 3 mantissa = 6 bits |
| Special values | No Inf/NaN (follows OCP MX convention) |
| Subnormal | 3-level normalization (mant=1xx/01x/001) |
| Cells | 17 |
| Test | Exhaustive 64-value sweep |

FP6 E2M3 is the wider-mantissa counterpart to FP6 E3M2 (wider-exponent). Together with FP4 E2M1 and FP8 E4M3, Corona now covers **all four NVIDIA Blackwell sub-8-bit tensor core formats**.

### ROM Expanded to 78 Records

- Added fmt_id=77 (fp6_e2m3, cluster 2 ML low-precision, FLAG_ON_DIE)
- ROM: 78 records x 80 bits = 6,240 data bits
- gen_rom.py updated: dynamic record count in comments and assertions
- format_rom.v regenerated: 836 cells (+24 from 77-record version)

### Build Files Updated

- `info.yaml`: 13 source files
- `test/Makefile`: 13 source files
- `tools/synth_stat.tcl`: 13 read_verilog entries
- ROM test strings: dynamic (no more hardcoded "77")

### Yosys Synthesis: 2,305 Cells

| Module | Cells | % of Total |
|--------|-------|-----------|
| Top (FSM + mux) | 1,081 | 46.9% |
| format_rom (78x80-bit) | 836 | 36.3% |
| nf4_decode | 99 | 4.3% |
| lns8_decode | 88 | 3.8% |
| bcd_decode | 33 | 1.4% |
| mxfp8_e4m3_decode | 32 | 1.4% |
| fp8_e5m2_decode | 32 | 1.4% |
| posit8_decode | 31 | 1.3% |
| tf32_decode | 26 | 1.1% |
| bf16_decode | 23 | 1.0% |
| fp6_e2m3_decode | 17 | 0.7% |
| fp6_e3m2_decode | 13 | 0.6% |
| fp4_decode | 4 | 0.2% |
| **TOTAL** | **2,305** | **100%** |

**Budget: 28.8%** (2,305 / 8,000). Headroom: 5,695 cells.

---

## 2. Weakness Analysis

### Fixed This Loop

| # | Weakness | How Fixed |
|---|----------|-----------|
| **W30** | Uncommitted work (HIGH) | Committed as e7cda48 |
| **W31** | No FP6 E2M3 (Blackwell gap) | fp6_e2m3_decode.v (17 cells), exhaustive test |
| **W32** | ROM test strings hardcoded to "77" | Now uses `len(CATALOG)` dynamically |
| **W33** | gen_rom.py comment said "77 records" after expansion | Now uses f-string with `len(records)` |

### Still Open

| # | Weakness | Severity | Next Action |
|---|----------|----------|-------------|
| **W10b** | GF180MCU Liberty synthesis | MEDIUM | Install volare + PDK |
| **W21** | Tests not verified in CI | MEDIUM | Push + CI trigger (needs auth) |
| **W28** | BF16 test only 7 values | LOW | Could add exhaustive 65K sweep |
| **W29** | TF32 test only 9 values | LOW | Could add parametric edge cases |
| **W34** | FP8 E4M3 FNUZ variant (fmt_id=14) has no decoder | LOW | Different NaN convention |
| **W7** | PR #1028 SSOT merge status | MEDIUM | Confirm with maintainer |
| **W9** | Gamma D2D not vendored | LOW | Phase D |

### Risk Assessment

| Risk | Status | Evidence |
|------|--------|----------|
| Area budget | **LOW** | 2,305 cells = 29% of 4x4 budget |
| Format coverage | **LOW** | 11 on-die decoders, all Blackwell sub-8-bit formats covered |
| Test coverage | **LOW** | 11/11 decoders tested, 1,207 decode values |
| Data loss | **LOW** | All work committed (5 commits on main) |
| CI validation | **MEDIUM** | Tests never run in CI, push blocked by auth |

---

## 3. Scientific Research Findings (Loop 9)

### FP6 E2M3 Technical Specification

| Property | E2M3 | E3M2 (comparison) |
|----------|------|-----|
| Exponent bits | 2 | 3 |
| Mantissa bits | 3 | 2 |
| Bias | 1 | 3 |
| Range | 0.125 to 7.5 | 0.0625 to 28.0 |
| Precision | 8 values per binade | 4 values per binade |
| Inf/NaN | No | No |
| Subnormal levels | 3 | 2 |
| Use case | High-precision narrow-range | Wide-range lower-precision |

E2M3 is the **precision-optimized** variant (more mantissa bits, narrower range). E3M2 is the **range-optimized** variant. Both are NVIDIA Blackwell tensor core native formats.

### IEEE P3109 vs OCP MX: Still Divergent

P3109 (still not ratified, Interim Report v3.0 Aug 2025) defines a parametric framework that is deliberately incompatible with OCP MX's fixed types. Key difference: P3109 changes emax definitions vs IEEE 754. Corona's approach of supporting both OCP MX decoders (E4M3, E3M2, E2M1) and the wider format catalog hedges against this standards divergence.

### Blackwell Format Coverage (Complete)

| Blackwell Format | Corona Decoder | fmt_id | Status |
|------------------|----------------|--------|--------|
| FP4 E2M1 | fp4_decode | 41 | On die |
| FP6 E3M2 | fp6_e3m2_decode | 40 | On die |
| **FP6 E2M3** | **fp6_e2m3_decode** | **77** | **On die (NEW)** |
| FP8 E4M3 | mxfp8_e4m3_decode | 39 | On die |
| FP8 E5M2 | fp8_e5m2_decode | 10 | On die |

Corona now covers **5/5 Blackwell sub-8-bit formats** (E5M2 added in Loop 7, E2M3 in this loop).

### Prior Art Update

No Tiny Tapeout project covers multiple float format decode. Closest: TT05 #292 (FP8 E5M2 adder, single format). Corona's 78-format catalog + 11 on-die decoders + 1,207-value test suite is unique in the ecosystem.

---

## 4. Project Totals

| Metric | Loop 8 | Loop 9 | Delta |
|--------|--------|--------|-------|
| RTL modules | 12 | 13 | +1 |
| On-die decoders | 10 | 11 | +1 |
| ROM records | 77 | 78 | +1 |
| Test functions | 18 | 19 | +1 |
| Decode values tested | 1,143 | 1,207 | +64 |
| Yosys cells (generic) | 2,200 | 2,305 | +105 |
| Budget utilization | 27.5% | 28.8% | +1.3% |
| Git commits | 4 | 5 | +1 |

---

## 5. Decomposed Plan (19 days to TTGF26a deadline)

### Phase A: Foundation -- COMPLETE (Loops 1-9)
- [x] 11 Tier-1 decoders, all with tests (1,207 values)
- [x] 78-record ROM, Protocol v2, anchor probe
- [x] Full Blackwell sub-8-bit format coverage
- [x] Yosys synthesis: 2,305 cells (29% budget)
- [x] All work committed (5 commits)
- [ ] **Push to GitHub (blocked on auth)**

### Phase B: CI + GF180MCU (Days 2-7)
- [ ] Push to GitHub
- [ ] CI green
- [ ] GF180MCU Liberty synthesis

### Phase C: Hardening (Days 8-14)
- [ ] DRC/LVS via OpenLane2
- [ ] Timing closure at 50 MHz
- [ ] Extended test coverage (BF16 exhaustive, TF32 edge cases)

### Phase D: Submission (Days 15-20)
- [ ] GDS generation
- [ ] TTGF26a submission (deadline: 2026-06-22)

---

## 6. Three Collaboration Options for Next Loop

### Option A: "Push + CI Green"

Push all 5 commits to GitHub. Trigger CI. Verify all 19 tests pass on Ubuntu + Python 3.12. This is the most critical remaining step before submission.

**Prerequisite:** Run `gh auth login` or configure SSH key.
**Deliverable:** Green CI, 19 tests verified in real simulation.
**Risk addressed:** W21 (CI never run). Highest-impact single action.

### Option B: "Exhaustive BF16 + Extended TF32 Tests"

BF16 currently only tests 7 key values out of 65,536 possible inputs. Add a BF16 exhaustive sweep (the decode is trivial -- zero-extension -- but the test verifies Protocol v2 handles 2-byte inputs correctly for all values). Add TF32 edge case tests (subnormals, max normal, min normal). This would push total decode values past 67,000.

**Deliverable:** ~67K decode values tested, BF16 fully validated.
**Risk addressed:** W28, W29 (incomplete test coverage for wide inputs).

### Option C: "INT8 Signed Decoder"

Add a trivial int8_decode: sign-extend 8-bit signed integer to 32-bit output. This is ~5 cells and covers the integer/fixed cluster (fmt_id=47). Completes coverage of the most commonly used ML quantization format (INT8) alongside the float decoders.

**Deliverable:** 12 on-die decoders, INT8 quantization support.
**Risk addressed:** Integer format coverage gap.

---

*Generated by Loop iteration 9, 2026-06-01.*
*Project: 13 RTL modules, 19 tests (1,207 decode values), 78 ROM records, 2,305 Yosys cells.*
*11 on-die decoders covering all Blackwell sub-8-bit formats + posit, LNS, BCD, NF4.*
*Budget: 28.8% generic / ~58% est. GF180MCU. Deadline: 2026-06-22 (19 days).*
