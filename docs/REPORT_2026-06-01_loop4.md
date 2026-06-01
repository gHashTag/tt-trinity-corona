# Corona Loop 4 Report -- 2026-06-01

## 1. What Was Implemented

### Protocol v2: Two-Byte CMD + Raw 8-Bit Data

**Critical weakness W1 eliminated.** The top module (`tt_um_trinity_corona.v`, 249 lines) was rewritten with a 5-state FSM:

```
IDLE -> CMD2 -> DATA -> STATUS -> DONE -> IDLE
```

| Aspect | Protocol v1 (Loop 3) | Protocol v2 (Loop 4) |
|--------|---------------------|---------------------|
| CMD encoding | `ui_in[7:6]=00` + 6-bit fmt_id | `ui_in[7]=0` + 7-bit fmt_id |
| Data path | 128 of 256 values (50% hole) | **All 256 values** (0% hole) |
| Status trigger | Manual (`ui_in[7:6]=10`) | Auto after last data byte |
| State machine | 3 states, mode inspected every cycle | 5 states, mode inspected only on CMD1 |
| Byte count | Implicit | Explicit in CMD2 (`ui_in[3:0]`) |

The key insight (confirmed by research): **counter-based FSM makes the mode field authoritative only on CMD cycles**. After CMD2 provides the byte count, the FSM accepts exactly N raw 8-bit bytes without inspecting any bits for control. This is the same approach used by SPI flash protocols and HD44780 LCD controllers.

### Exhaustive Test Suite

`test/test_decoders.py` rewritten (381 lines, 9 tests) with Python reference models for every decoder:

| Test | Format | Coverage | Assertions |
|------|--------|----------|------------|
| `test_fp4_exhaustive` | FP4 E2M1 | 16/16 (100%) | Bit-exact FP32 |
| `test_nf4_exhaustive` | NF4 QLoRA | 16/16 (100%) | Bit-exact FP32 |
| `test_fp6_e3m2_exhaustive` | FP6 E3M2 | 64/64 (100%) | Bit-exact FP32 |
| `test_mxfp8_e4m3_exhaustive` | MXFP8 E4M3 | 256/256 (100%) | Bit-exact FP32 |
| `test_posit8_exhaustive` | Posit8(es=0) | 256/256 (100%) | Bit-exact FP32 |
| `test_bcd_values` | Packed BCD | 6 key values | Decimal equality |
| `test_bf16_key_values` | BFloat16 | 7 key values (2-byte) | Bit-exact FP32 |
| `test_not_implemented_sentinel` | Unknown fmt | 1 value | Sentinel match |
| `test_zero_byte_cmd` | Zero-data CMD | 1 value | Immediate STATUS |

Total decode-value coverage: **608 unique values tested** (up from ~30 in Loop 3).

### Protocol Spec Updated

`specs/corona/protocol.t27` updated to document Protocol v2:
- Section 2 rewritten: two-byte CMD, raw data, auto-STATUS
- Section 4 cycle sequences updated for 8-bit, 16-bit, and sub-byte formats
- Anchor probe behavior unchanged (combinational, no CMD2 needed)

### docs/info.md Updated

"How to test" section rewritten for Protocol v2 with new examples.

---

## 2. Weakness Analysis

### Fixed This Loop

| # | Weakness | Severity | How Fixed |
|---|----------|----------|-----------|
| **W1** | DATA_IN byte collision (50% hole) | CRITICAL | Protocol v2: counter-based FSM, all 256 values valid |
| **W-L3** | No exhaustive 8-bit sweep tests | HIGH | 256-value sweeps for MXFP8 and Posit8 |
| **W-L3** | Protocol spec outdated | MEDIUM | protocol.t27 updated to v2 |

### Still Open

| # | Weakness | Severity | Next Action |
|---|----------|----------|-------------|
| **W6** | ROM emitter not in repo | HIGH | Phase B: gen_formats_catalog.py Verilog backend |
| **W10** | GF180MCU synthesis unvalidated | HIGH | OpenLane2/LibreLane synthesis sprint |
| **W7** | PR #1028 SSOT merge status | MEDIUM | Confirm with t27 maintainer |
| **W9** | Gamma D2D not vendored | MEDIUM | Phase D |
| **W16** | BF16 test is key-values only, not exhaustive 65536 | LOW | Can add if needed, but 2-byte format is just wire concat |
| **W14** | Takum16 license | LOW | Contact Hunhold |
| **W15** | fmt_id assignments provisional | LOW | Finalize with ROM emitter |

### Risk Assessment Update

| Risk | Status | Evidence |
|------|--------|----------|
| Protocol correctness | **RESOLVED** | All 608 test values pass through full 8-bit data path |
| Decoder correctness | **HIGH CONFIDENCE** | Exhaustive sweeps for all sub-256-value formats; reference models cross-verified against specs |
| Area budget | **UNVALIDATED** | Still estimated (2,950-6,075 cells); need OpenLane2 synthesis |
| Timing (50 MHz) | **UNVALIDATED** | GF180MCU is slow (~100-200 MHz for simple logic); should close easily |
| Submission readiness | **ON TRACK** | 20 days to deadline; foundation solid, ROM + synthesis remain |

---

## 3. Scientific Research Findings (Loop 4)

### Protocol Design (from research agent)

| Approach | Used in | Verdict for Corona |
|----------|---------|-------------------|
| SPI framing (CS pin) | tt05-spi-peripheral, SPI flash | Overkill — uses 4 uio pins |
| UART (start/stop bits) | tt_um_ccattuto_charmatrix | Too slow for parallel access |
| Dedicated RS pin (HD44780) | LCD controllers, some TT designs | Clean, but uses 1 uio pin |
| **Byte-count in CMD** | SPI flash CMD sequences | **Adopted — zero extra pins, full 8-bit** |
| Escape byte (HDLC/COBS) | Serial comms | Overkill, variable latency |

### Numeric Format Decode Hardware (from research agent)

| Topic | Key Finding | Impact on Corona |
|-------|-------------|-----------------|
| **Posit8 decode** | SPADE (arXiv:2601.17279, 2026): regime-aware SIMD with unified LOD/shifter — 45% LUT reduction. b-Posit (arXiv:2603.01615): constrained regime = 79% less power | Our LZC-based posit8_decode.v is correct and area-efficient; b-Posit approach could optimize further if needed |
| **OCP MX formats** | MX-for-FPGA (ebby-s/MX-for-FPGA) confirmed: parameterized SV for all MX formats. OCP spec still at v1.0 (no v1.1 errata found) | Our mxfp8_e4m3_decode.v matches spec; fp4/fp6 LUTs are correct |
| **NF4 (QLoRA)** | Fast NF4 Dequant (arXiv:2604.02556, 2026): GPU kernel optimization. QRazor (arXiv:2501.13331): decompression-free 4-bit ALU. No silicon NF4 decoder exists — **we may be first** | Our 16-entry LUT is trivially correct and minimal-area |
| **LNS8** | QAA-LNS (arXiv:2510.17058, 2025): piecewise-linear with power-of-two slopes, no multipliers — 32.5% area reduction. Johnson (Meta): ROM-free LNS via restoring shift-and-add | Our 16-entry fractional LUT approach is valid; QAA-LNS technique could replace it if area is tight |
| **BF16** | ARM BFDOT analysis: BF16 multiply is ~half the area of FP16 | Our wire-concat decode is zero logic; confirmed optimal |

### Key Papers

- SPADE: arXiv:2601.17279 (posit SIMD, 2026)
- b-Posit: arXiv:2603.01615 (constrained regime, 2025)
- MX-for-FPGA: arXiv:2407.01475 (FPL 2024)
- QAA-LNS: arXiv:2510.17058 (bitwidth-specific LNS, 2025)
- QRazor: arXiv:2501.13331 (decompression-free 4-bit, 2025)
- "Navigating Posit Arithmetic": ACM Computing Surveys, 2025

---

## 4. Updated Project Totals

| Metric | Loop 1 | Loop 2 | Loop 3 | Loop 4 | Total |
|--------|--------|--------|--------|--------|-------|
| RTL modules | 2 | 5 | 3 | 0 (rewrite) | 10 |
| RTL lines | 105 | 384 | 158 | -2 (net) | 645 |
| Test files | 1 | 1 | 0 | 0 (rewrite) | 2 |
| Test cases | 4 | 10 | 7 | 9 (rewrite) | 13 |
| Decode values tested | 0 | ~30 | ~30 | 608 | 608 |
| CI jobs | 2 | 1 | 0 | 0 | 3 |
| Specs updated | 0 | 0 | 0 | 1 | 1 |

---

## 5. Decomposed Plan (20 days to TTGF26a deadline, Jun 22)

### Phase A: Foundation — COMPLETE (Loops 1-4)
- info.yaml, docs, CI, anchor, 8 decoders, Protocol v2, exhaustive tests

### Phase B: ROM + Synthesis (Days 2-10)
- [ ] ROM emitter: gen_formats_catalog.py -> format_rom.v (77 records x 80 bits)
- [ ] ROM readback test (77 entries, bit-exact vs SSOT)
- [ ] OpenLane2/LibreLane install + GF180MCU PDK
- [ ] First synthesis run -> cell count / area report
- [ ] Timing closure at 50 MHz

### Phase C: Integration + Polish (Days 11-16)
- [ ] Full integration test: all decoders + ROM
- [ ] DRC/LVS clean
- [ ] Power analysis
- [ ] ADR: ROM optimization decisions

### Phase D: Submission (Days 17-20)
- [ ] GDS generation
- [ ] TTGF26a submission (deadline: 2026-06-22)
- [ ] Post-silicon test plan

---

## 6. Three Collaboration Options for Next Loop

### Option A: "OpenLane2 Synthesis Sprint"

Install OpenLane2/LibreLane + GF180MCU PDK. Synthesize the current 10-module design (645 RTL lines). Produce real cell counts, timing reports, and area breakdown. This is the **highest-priority falsification point** — if the design doesn't fit in 4x4 or can't close timing at 50 MHz, the entire timeline must adapt. The research confirms GF180MCU has a 2.1x density penalty vs SKY130A and no open SRAM macros, so real numbers are essential.

**Deliverable:** Synthesis report (cells, area, timing, power), tile utilization map.
**Risk addressed:** W10 (synthesis unvalidated), area budget confirmation.

### Option B: "ROM Emitter Pipeline"

Build the Verilog ROM emitter as a backend of gen_formats_catalog.py. Parse the 77 SSOT records from the .t27 specs, generate format_rom.v with optimized case statements (don't-care on unused addresses 77-127), and write a ROM readback cocotb test that verifies all 77 entries bit-exact. This unblocks Phase B and validates the full SSOT-to-silicon pipeline.

**Deliverable:** format_rom.v (77 records), ROM readback test, gen_formats_catalog.py Verilog backend.
**Risk addressed:** W6 (ROM emitter missing), Phase B critical path.

### Option C: "LNS8 Optimization + Remaining Decoder Hardening"

Apply the QAA-LNS piecewise-linear technique (arXiv:2510.17058) to replace the current 16-entry fractional LUT in lns8_decode.v with a multiplier-free approximation using power-of-two slopes (bit-shifts only). Also harden the posit8 decoder based on SPADE/b-Posit findings. Add BCD exhaustive test (100 valid + 156 invalid BCD codes). Run gate-count estimation.

**Deliverable:** Optimized lns8_decode.v, hardened posit8_decode.v, BCD exhaustive test, gate-count estimates.
**Risk addressed:** Area optimization, decoder robustness, test completeness.

---

*Generated by Loop iteration 4, 2026-06-01.*
*Project totals: 10 RTL modules (645 lines), 13 cocotb tests (608 decode values), 3 CI jobs, 1118 total source lines.*
*All RTL passes iverilog lint clean. Protocol v2 eliminates the critical data-path collision.*
*No changes committed yet — all in working tree.*
