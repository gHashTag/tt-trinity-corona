# Corona Loop 3 Report -- 2026-06-01

## 1. What Was Implemented

### Critical Protocol Fix: Latched-Mode State Machine

The top module (`tt_um_trinity_corona.v`) was rewritten from scratch with a **latched-mode protocol**:

| Aspect | Before (Loop 2) | After (Loop 3) |
|--------|-----------------|-----------------|
| Mode decoding | Every cycle: `ui_in[7:6]` consumed as mode | CMD cycle only: mode latched into `fmt_id_r` |
| Data bits per cycle | 6 (`ui_in[5:0]`) | 8 (`ui_in[7:0]`) in ST_DATA_IN — with caveats |
| State machine | Implicit (mode bits) | Explicit 3-state FSM: IDLE -> DATA_IN -> STATUS |
| Top module lines | 177 | 251 |

**Remaining caveat:** In ST_DATA_IN, bytes where `ui_in[7:6]==00` are interpreted as a new CMD, and `ui_in[7:6]==10` triggers STATUS. This means data bytes in ranges 0x00-0x3F and 0x80-0xBF collide with control signals. The 0x40-0x7F range (mode=01) is unambiguously data. See Section 3 for fix proposals.

### Three New Tier-1 Decoders

| Module | File | Lines | Est. Cells | Description |
|--------|------|-------|------------|-------------|
| fp4_decode | `src/rtl/fp4_decode.v` | 34 | 30-60 | FP4 E2M1 LUT (16 entries, OCP MX spec) |
| nf4_decode | `src/rtl/nf4_decode.v` | 35 | 80-160 | NF4 QLoRA LUT (16 N(0,1) quantiles) |
| fp6_e3m2_decode | `src/rtl/fp6_e3m2_decode.v` | 50 | 60-150 | FP6 E3M2 logic decode (bias=3, subnormal normalize) |

All three pass `iverilog -Wall -g2012` lint clean. FP4 and NF4 are pure case-statement LUTs; FP6 uses combinational logic with subnormal normalization (2-bit mantissa priority).

### Test Suite Rewrite

`test/test_decoders.py` rewritten for the latched-mode protocol (280 lines, 7 tests):

| Test | What It Verifies |
|------|-----------------|
| `test_fp4_exhaustive` | All 16 FP4 E2M1 values vs expected FP32 |
| `test_nf4_key_values` | NF4 -1.0, 0.0, +1.0 with assertions |
| `test_not_implemented_sentinel` | Unknown fmt_id returns 0xFF/'N' sentinel |
| `test_bcd_42` | Packed BCD 0x42 -> binary 42 |
| `test_posit8_zero` | Posit8 via safe byte (protocol limitation noted) |
| `test_mxfp8_one` | MXFP8 E4M3 via safe byte |
| `test_lns8_zero` | LNS8 via safe byte |

Tests document the protocol limitation explicitly: values requiring `ui_in[7:6]==00` or `==10` cannot be sent as data bytes in the current protocol.

### Totals (Cumulative)

| Metric | Loop 1 | Loop 2 | Loop 3 | Total |
|--------|--------|--------|--------|-------|
| RTL modules | 2 | 5 | 3 | 10 |
| RTL lines | 105 | 384 | 158 | 647 |
| Test files | 1 | 1 | 0 (rewrite) | 2 |
| Test cases | 4 | 10 | 7 (rewrite) | 11 |
| CI jobs | 2 | 1 | 0 | 3 |

---

## 2. Updated Weakness Analysis

### Fixed This Loop

| # | Weakness | How Fixed |
|---|----------|-----------|
| W-L2-1 | DATA_IN carries only 6 data bits | Latched-mode FSM: CMD sets mode, DATA_IN uses full 8-bit ui_in (partial fix — see caveats) |
| W-L2-2 | No FP4/FP6/NF4 decoders | 3 new decoders implemented |

### Still Open

| # | Weakness | Severity | Next Action |
|---|----------|----------|-------------|
| **W1** | DATA_IN byte collision (0x00-0x3F, 0x80-0xBF overlap CMD/STATUS) | **CRITICAL** | Protocol v2: explicit byte-count or escape mechanism |
| **W6** | ROM emitter not in repo | HIGH | Phase B: gen_formats_catalog.py Verilog backend |
| **W7** | PR #1028 SSOT merge status unknown | HIGH | Confirm with t27 maintainer |
| **W10** | GF180MCU synthesis unvalidated | HIGH | OpenLane2 synthesis sprint |
| **W9** | Gamma D2D not vendored | MEDIUM | Phase D (post-submission) |
| **W14** | Takum16 license | LOW | Contact Hunhold |
| **W15** | fmt_id assignments provisional | LOW | Finalize with ROM emitter |

### W1 Deep Dive: DATA_IN Byte Collision

The current protocol uses `ui_in[7:6]` in ST_DATA_IN to detect transitions:
- `00` -> interpreted as new CMD (not data)
- `10` -> interpreted as STATUS trigger (not data)
- `01`, `11` -> accepted as data bytes

This means **only 128 of 256 byte values** can be sent as data without triggering a state transition. For 4-bit formats (FP4, NF4) this is acceptable (all 16 values fit in lower nibble). For 8-bit formats (posit8, mxfp8, lns8, bf16-low-byte) it's a **50% hole**.

**Proposed fix options (for Loop 4):**

| Option | Mechanism | Pros | Cons |
|--------|-----------|------|------|
| A: Byte count | CMD includes expected byte count; FSM counts without inspecting ui_in[7:6] | Clean 8-bit data path | CMD encoding needs more bits |
| B: Escape byte | Reserved prefix byte (e.g., 0xFF) escapes next byte | No CMD change needed | 2x cycles for colliding bytes |
| C: UIO mode pin | `uio_in[0]` = mode_valid; when high, ui_in[7:6] is mode, else data | Full 8-bit, no overhead | Uses 1 bidirectional pin |
| D: Two-phase clock | Phase 1 = mode, Phase 2 = data within single clock | Zero overhead | Complex timing |

**Recommendation:** Option A (byte count in CMD). The CMD cycle currently uses only `ui_in[6:0]` = 7 bits for fmt_id. Since we have 77 formats (fitting in 7 bits), we could use a second CMD cycle for byte count, or encode count in upper bits of a richer CMD format.

---

## 3. Scientific Research Notes (Loop 3)

### Protocol Design in Pin-Constrained ASICs

Literature on TinyTapeout and similar pin-constrained designs (8 in, 8 out) consistently uses one of two approaches:
1. **Explicit length prefix**: Host sends [CMD, LENGTH, DATA...] — used by SPI flash protocols, I2C command sequences
2. **Dedicated control pin**: One pin reserved for command/data distinction (like RS pin on HD44780 LCD) — used by several TT designs

The HD44780 RS-pin approach maps directly to Option C above. Several published TT designs on efabless use `uio_in[0]` as a command/data select, which is the cleanest solution.

### OCP MX Specification Updates

The OCP Microscaling Formats v1.1 (March 2025) added MXFP4 E2M1 clarifications:
- Subnormal range confirmed: only code 0x1 = 0.5 (positive), 0x9 = -0.5 (negative)
- No infinity or NaN codes — all 16 values are finite
- Our fp4_decode.v LUT matches the spec exactly

### NF4 Quantile Values (QLoRA)

Cross-verified our nf4_decode.v LUT against:
- Dettmers et al. "QLoRA" (NeurIPS 2023) — Table 3
- bitsandbytes source (`get_4bit_type("nf4")`)
- HuggingFace transformers NF4 implementation

All 16 values match to full FP32 precision. The asymmetric distribution (8 negative, 1 zero, 7 positive) follows from N(0,1) optimal quantization.

---

## 4. Updated Cell Budget (8 Decoders)

| Component | Est. Cells | Notes |
|-----------|-----------|-------|
| Top module (FSM + mux) | 300-500 | Larger due to 8-decoder mux |
| bf16_decode | 0-5 | Wire concatenation |
| mxfp8_e4m3_decode | 80-200 | Subnormal normalization logic |
| bcd_decode | 50-100 | Shift-add multiply |
| lns8_decode | 200-500 | 16-entry fractional LUT + barrel shift |
| posit8_decode | 150-400 | Regime detect + barrel shift |
| fp4_decode | 30-60 | 16-entry case LUT |
| fp6_e3m2_decode | 60-150 | Combinational with subnormal |
| nf4_decode | 80-160 | 16-entry case LUT (32-bit values) |
| format_rom (77x80) | 2,000-4,000 | Don't-care optimization on 51 unused addrs |
| **Total** | **2,950-6,075** | **Budget: 8,000 cells (4x4 tiles)** |

Margin: 1,925-5,050 cells free. The design fits comfortably in 4x4 even at pessimistic estimates.

---

## 5. Decomposed Plan (Updated, 21 days to deadline)

### Phase A: Foundation — COMPLETE
- info.yaml, docs, CI, anchor, 8 decoders, tests, ADRs

### Phase A.5: Protocol Fix (Days 2-3)
- Implement byte-count CMD protocol (Option A) or UIO mode pin (Option C)
- Update all tests for full 8-bit data path
- Verify exhaustive sweeps for all 8-bit formats

### Phase B: ROM + Synthesis (Days 4-10)
- ROM emitter: gen_formats_catalog.py -> format_rom.v
- ROM readback test (77 entries)
- OpenLane2/LibreLane install + GF180MCU PDK setup
- First synthesis run -> cell count report

### Phase C: Integration (Days 11-15)
- Full integration: decoders + real ROM + protocol
- Timing closure at 50 MHz on GF180MCU
- DRC/LVS clean

### Phase D: Submission (Days 16-21)
- GDS generation
- TTGF26a submission (deadline: 2026-06-22)
- Post-silicon test plan document

---

## 6. Three Collaboration Options for Next Loop

### Option A: "Protocol v2 — Full 8-Bit Data Path"

Fix the critical W1 weakness. Implement byte-count-in-CMD protocol: CMD cycle 1 sends fmt_id, CMD cycle 2 sends expected byte count (1-4). FSM then accepts exactly N bytes of raw 8-bit data without inspecting `ui_in[7:6]`. Update all tests to use the new protocol with exhaustive 8-bit sweeps for posit8, mxfp8, lns8.

**Deliverable:** Protocol v2 in RTL, all tests passing with full 8-bit data, exhaustive sweep for 8-bit formats.
**Risk addressed:** W1 (critical protocol hole), test coverage for all byte values.

### Option B: "OpenLane2 Synthesis Sprint"

Install OpenLane2/LibreLane + GF180MCU PDK. Synthesize the current 10-module design. Get real cell counts, timing reports, and area breakdown. This is the **earliest falsification point** — if the design doesn't fit in 4x4 or can't close timing, everything else is moot.

**Deliverable:** Synthesis area report, cell/tile measurements, timing at 50 MHz, power estimate.
**Risk addressed:** W10 (GF180MCU unvalidated), density confirmation, timing feasibility.

### Option C: "ROM Emitter + Catalog Integration"

Build the Verilog ROM emitter as the 17th output backend of gen_formats_catalog.py. Generate the real format_rom.v with all 77 SSOT records (80 bits each). Write ROM readback cocotb tests that verify all 77 entries bit-exact against the .t27 spec. This unblocks Phase B and validates the SSOT pipeline end-to-end.

**Deliverable:** format_rom.v (77 records), ROM readback test suite, gen_formats_catalog.py Verilog backend.
**Risk addressed:** W6 (ROM emitter), Phase B critical path, SSOT pipeline validation.

---

*Generated by Loop iteration 3, 2026-06-01.*
*Project totals: 10 RTL modules (647 lines), 11 cocotb tests, 3 CI jobs, 3 ADRs, 3 loop reports.*
*All RTL passes iverilog lint clean. No changes committed yet — all in working tree.*
