# Corona Loop 2 Report -- 2026-06-01

## 1. What Was Implemented

### MVP-5 Tier-1 Decoders (5 new RTL modules)

| Module | File | Lines | Est. Cells | Description |
|--------|------|-------|------------|-------------|
| bf16_decode | `src/rtl/bf16_decode.v` | 28 | 0-5 | BFloat16->FP32 (wire concat + classifier) |
| mxfp8_e4m3_decode | `src/rtl/mxfp8_e4m3_decode.v` | 62 | 80-200 | OCP MX FP8 E4M3->FP32 with subnormal normalization |
| bcd_decode | `src/rtl/bcd_decode.v` | 21 | 50-100 | 2-digit packed BCD->binary via shift-add |
| lns8_decode | `src/rtl/lns8_decode.v` | 68 | 200-500 | 8-bit LNS antilog with 16-entry fractional LUT |
| posit8_decode | `src/rtl/posit8_decode.v` | 86 | 150-400 | Posit8(es=0)->FP32 with regime detection + barrel shift |

### Top Module Integration

`tt_um_trinity_corona.v` rewritten (177 lines) with:
- Anchor probe (unchanged, combinational 0x47C0)
- State machine: CMD -> DATA_IN -> STATUS protocol
- 32-bit data accumulation buffer for multi-byte formats
- Decoder dispatch mux based on fmt_id_r
- Not-implemented response (0xFF sentinel + 'N' tag) for unknown formats
- All 5 decoders instantiated and wired

### CI Improvements

- `claim-status-lint` job added — regex check for banned words per CLAIM_STATUS.md
- Test module list expanded to include `test_decoders`
- Makefile lint target uses wildcard (`src/rtl/*.v`)

### Tests

- `test/test_decoders.py` — 10 new cocotb tests covering BF16, BCD, posit8, mxfp8, lns8, and not-implemented sentinel

### Totals

| Metric | Loop 1 | Loop 2 | Total |
|--------|--------|--------|-------|
| RTL modules | 2 | 5 | 7 |
| RTL lines | 105 | 384 | 489 |
| Test files | 1 | 1 | 2 |
| Test cases | 4 | 10 | 14 |
| CI jobs | 2 | 1 | 3 |

---

## 2. Updated Weakness Analysis

### Fixed This Loop

| # | Weakness | How Fixed |
|---|----------|-----------|
| NEW | Zero Tier-1 decoders | 5 MVP decoders implemented, lint clean |
| NEW | Top module had no decoder dispatch | Full CMD/DATA_IN/STATUS protocol + mux |
| W8 (from L1) | claim_status_lint missing | Added to CI |

### Still Open

| # | Weakness | Severity | Next Action |
|---|----------|----------|-------------|
| W6 | ROM emitter not in repo | HIGH | Phase B: implement gen_formats_catalog.py Verilog emitter |
| W7 | PR #1028 SSOT merge status unknown | HIGH | Confirm with gHashTag/t27 maintainer |
| W10 | GF180MCU density unvalidated | HIGH | Install OpenLane2 + synthesize |
| W9 | Gamma D2D not vendored | MEDIUM | Phase D (post-submission) |
| W14 | Takum16 license | LOW | Contact Hunhold |
| NEW | DATA_IN protocol only carries 6 data bits (ui_in[5:0] when mode=01) | MEDIUM | Redesign: mode in separate register, or use full 8-bit DATA_IN with preamble cycle |
| NEW | fmt_id assignments are provisional | LOW | Phase B ROM emitter finalizes; update localparams |

### Protocol Design Issue Found

During test writing, a protocol limitation was identified: in DATA_IN mode (`ui_in[7:6]=01`), only `ui_in[5:0]` = 6 bits carry data. This means an 8-bit input format requires 2 DATA_IN cycles instead of 1. This is functional but inefficient. Two fix options:

1. **Latched mode register**: CMD latches the mode; subsequent cycles use all 8 bits for data
2. **Accept the overhead**: 2 cycles per byte for 8-bit formats is still fast at 50 MHz (40 ns)

Recommendation: Option 1 for Phase B (cleaner protocol), but Option 2 is acceptable for TTGF26a MVP.

---

## 3. Scientific Research Highlights (Loop 2)

### Decoder Implementation Sources

| Format | Best Reference | License | Key Finding |
|--------|---------------|---------|-------------|
| Posit8 | PACoGen (GitHub) | BSD-3 | Parameterized Verilog generator; regime detection via LZC is the critical path |
| BF16 | Trivial (wire concat) | N/A | Zero logic gates for decode; 0-5 buffer cells max |
| MXFP8 E4M3 | MX-for-FPGA (GitHub) | MIT | Fully parameterized SV for all MX formats; subnormal handling needs 3-bit priority encoder |
| LNS8 | Alam+ (arXiv:2102.06681) | N/A | Gate-based antilog is smaller than ROM for 8-bit; 16-entry fractional LUT sufficient |
| BCD | Standard algorithm | N/A | Multiply-by-10+add is simpler than reverse double-dabble for 2-digit |

### ROM Synthesis (for Phase B)

- 77x80 combinational ROM: 2,000-6,000 cells depending on data regularity
- Key optimization: assign `80'bx` to unused addresses 77-127 (51 don't-cares)
- Split ROM into sub-ROMs per field group for better ABC optimization
- GF180MCU NAND2 site = 3.36 x 3.92 um; ~480-520 cells/tile at 55% utilization

### OpenLane2 / LibreLane

- OpenLane2 rebranded as LibreLane (July 2025), community-driven under FOSSi Foundation
- GF180MCU uses PDK variant `gf180mcuD`, cell library `gf180mcu_fd_sc_mcu7t5v0`
- No open SRAM macros — all memory must be synthesis-inferred (confirmed)
- Metal5 reserved by TinyTapeout for PDN

---

## 4. Decomposed Plan (Updated, 20 days to TTGF26a close)

### Week 1 (Jun 1-7): Phase A — DONE + PDK Trial

| Day | Task | Status |
|-----|------|--------|
| 1 | info.yaml fix + stub RTL + anchor test + CI | **DONE (Loop 1)** |
| 1 | MVP-5 decoders + top integration + decoder tests | **DONE (Loop 2)** |
| 2-3 | Install OpenLane2/LibreLane + GF180MCU PDK | TODO |
| 4 | Synthesize full design (anchor + 5 decoders); measure cells/tile | TODO |
| 5 | Write tile-budget memo; confirm 4x4 viability | TODO |

### Week 2 (Jun 8-14): Phase B — ROM + Protocol Refinement

| Day | Task |
|-----|------|
| 6-7 | Implement Verilog ROM emitter in gen_formats_catalog.py |
| 8 | Generate format_rom.v (77 records x 80 bits); replace placeholder |
| 9 | ROM readback cocotb test (sweep all 77 indices) |
| 10 | Synthesize ROM; update area budget; refine DATA_IN protocol |

### Week 3 (Jun 15-21): Phase C-F — Integration + Submission

| Day | Task |
|-----|------|
| 11-13 | Full integration test; fix timing issues if any |
| 14-16 | OpenLane2/LibreLane: synthesis -> place -> route -> DRC |
| 17-18 | LVS clean; timing closure at 50 MHz |
| 19-20 | GDS generation + TTGF26a submission (deadline: Jun 22) |

---

## 5. MVP-5 Cell Budget Estimate

| Component | Est. Cells | Tiles (at 500/tile) |
|-----------|-----------|---------------------|
| Top module (protocol + mux) | 200-400 | ~0.5 |
| bf16_decode | 0-5 | ~0 |
| mxfp8_e4m3_decode | 80-200 | ~0.3 |
| bcd_decode | 50-100 | ~0.2 |
| lns8_decode | 200-500 | ~0.7 |
| posit8_decode | 150-400 | ~0.6 |
| format_rom (77x80 optimized) | 2,000-4,000 | ~5-8 |
| **Total** | **2,680-5,605** | **~7-10** |

Budget: 16 tiles (4x4) x 500 cells/tile = 8,000 cells. **MVP-5 fits within budget** even at pessimistic ROM sizing. Room for 1-2 additional decoders if ROM optimizes well.

---

## 6. Three Collaboration Options for Next Loop

### Option A: "OpenLane2 Synthesis Sprint"

Install OpenLane2/LibreLane + GF180MCU PDK. Synthesize the current design (anchor + 5 decoders + placeholder ROM). Measure actual cells, timing, and area. This is the **earliest falsification point** — if synthesis fails or density is far worse than estimated, the entire timeline changes.

**Deliverable:** Synthesis area report, cells/tile measurement, timing report at 50 MHz.
**Risk addressed:** R1 (PDK maturity), R5 (density penalty), R10 (ROM macro absence).

### Option B: "ROM Emitter + Full Catalog"

Build the Verilog ROM emitter (17th output language of gen_formats_catalog.py). Generate the real format_rom.v with all 77 records from SSOT. Write ROM readback tests. This is the **Phase B critical path** — without the real ROM, the chip is incomplete.

**Deliverable:** format_rom.v with 77 records, ROM readback cocotb test (77 entries verified bit-exact).
**Risk addressed:** W6 (ROM emitter), Phase B unblocked.

### Option C: "Protocol Refinement + More Decoders"

Fix the DATA_IN 6-bit limitation by implementing a latched mode register. Add 2-3 more Tier-1 decoders (fp4_decode as 16-entry LUT, fp6_decode as 64-entry LUT, nf4_decode as QLoRA 16-entry LUT — all trivially small). Expand test coverage to exhaustive 8-bit sweeps.

**Deliverable:** Refined protocol, 7-8 total Tier-1 decoders, exhaustive test coverage for all 8-bit formats.
**Risk addressed:** Protocol correctness, decoder coverage, test confidence.

---

*Generated by Loop iteration 2, 2026-06-01.*
*Total project: 7 RTL modules (489 lines), 14 cocotb tests, 3 CI jobs, 3 ADRs.*
