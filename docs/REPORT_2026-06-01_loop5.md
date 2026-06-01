# Corona Loop 5 Report -- 2026-06-01

## 1. What Was Implemented

### ROM Emitter + 77-Record ROM (W6 Eliminated)

Created `tools/gen_rom.py` (263 lines) — the Verilog ROM emitter for the SSOT catalog.

| Metric | Value |
|--------|-------|
| Records | 77 (all SSOT formats) |
| Bits per record | 80 |
| Total ROM bits | 6,160 |
| ROM file | `src/rtl/format_rom.v` (97 lines, auto-generated) |
| Fields per record | 11 (format_index_id, cluster_id, status_id, total_bits, sign_bits, exp_bits, mant_bits, encoding_kind, phi_distance_q16, ref_index, flags) |

The emitter:
- Defines all 77 records across 13 clusters matching `corona_oracle.t27`
- Computes `phi_distance_q16` automatically from exp/mant ratio vs 1/phi
- Packs each record to 80 bits per `rom_layout.t27`
- Generates synthesizable Verilog `case` statement with `default: data <= 80'h0`
- Verifies `format_index_id` round-trip on every record

### ROM Readback in Top Module

Updated `tt_um_trinity_corona.v` (274 lines) with:
- **ROM mode**: `byte_count=0` in CMD2 triggers ROM readback (10 bytes streamed from `rom_data[79:0]`)
- **Decode mode**: `byte_count>0` works as before (raw data -> decoder -> 4-byte result)
- `status_cnt` widened to 4 bits (0-9 for ROM, 0-3 for decode)
- `rom_mode` register tracks which readback path is active

### fmt_id Alignment with SSOT

All fmt_id assignments in RTL and tests updated to match the ROM catalog ordering:

| Decoder | Old fmt_id | New fmt_id | Cluster |
|---------|-----------|-----------|---------|
| bf16_decode | 12 | **8** | ML low-precision |
| posit8_decode | 24 | **31** | Posit/Unum III |
| mxfp8_e4m3_decode | 33 | **39** | OCP MX |
| fp6_e3m2_decode | 41 | **40** | OCP MX |
| fp4_decode | 40 | **41** | OCP MX |
| lns8_decode | 36 | **42** | LNS |
| bcd_decode | 53 | 53 | Integer/fixed |
| nf4_decode | 42 | **70** | Compression |

### ROM Readback Test Suite

Added 3 new tests to `test_decoders.py`:

| Test | What It Verifies |
|------|-----------------|
| `test_rom_readback_all` | All 77 ROM records match expected packed values (bit-exact) |
| `test_rom_readback_key_fields` | Field extraction for fp32 (fmt_id=1): total_bits=32, exp=8, mant=23, enc=FP |
| `test_rom_unused_address` | Address >= 77 returns zero |

---

## 2. Updated Weakness Analysis

### Fixed This Loop

| # | Weakness | How Fixed |
|---|----------|-----------|
| **W6** | ROM emitter not in repo | `tools/gen_rom.py` + auto-generated `format_rom.v` with 77 records |
| **W15** | fmt_id assignments provisional | Aligned with SSOT catalog ordering |
| **W-L4** | No ROM readback in top module | Added ROM mode (byte_count=0), 10-byte streaming |
| **W-L4** | No ROM tests | 77-record readback test + field extraction + unused address |

### Still Open

| # | Weakness | Severity | Next Action |
|---|----------|----------|-------------|
| **W10** | GF180MCU synthesis unvalidated | **HIGH** | OpenLane2/LibreLane synthesis sprint |
| **W7** | PR #1028 SSOT merge status | MEDIUM | Confirm with t27 maintainer |
| **W9** | Gamma D2D not vendored | MEDIUM | Phase D |
| **W17** | ROM data not cross-verified against upstream SSOT | MEDIUM | Compare with gHashTag/t27 when PR merges |
| **W14** | Takum16 license | LOW | Contact Hunhold |
| **W18** | All changes still uncommitted | **HIGH** | Git commit needed |

---

## 3. Scientific Research Findings (Loop 5)

### ROM Synthesis on GF180MCU (from research agent)

| Aspect | Finding |
|--------|---------|
| **Yosys ROM optimization** | `proc_rom` -> `memory_map` -> `abc -liberty`. Case-statement ROM becomes combinational mux tree. ABC finds data-address pattern correlations to minimize cells |
| **GF180MCU cell library** | `gf180mcu_fd_sc_mcu7t5v0`, 7-track, site pitch 0.56x3.92 um. AOI/OAI complex gates available for efficient decoder logic. MUX2/MUX4 cells usable as mux-tree building blocks |
| **No SRAM macros** | Confirmed: only DFFRAM compiler (for R/W RAM). Pure combinational ROM is correct approach |
| **Area rule of thumb** | ~0.3-1.0 standard cells per ROM bit after ABC optimization. Our 6,160-bit ROM: **1,850-6,160 cells** estimated |
| **TT precedent** | a1k0n's TT08 demo: 3,374 cells for font/music data tables on Sky130 — ABC found address-data pattern correlation. GF180MCU is ~2.1x less dense |
| **Density ceiling** | ~62% target utilization; routing/tap/antenna cells consume significant area beyond logic cells |
| **Key insight** | Don't-care optimization: if `proc_rom` detects X bits in any case, it falls back to mux-tree. Our `default: data <= 80'h0` provides 51 don't-care addresses (77-127) for optimization |

### Updated Cell Budget

| Component | Est. Cells | Notes |
|-----------|-----------|-------|
| Top module (FSM + mux + ROM readback) | 400-600 | Larger with ROM mode |
| bf16_decode | 0-5 | Wire concat |
| mxfp8_e4m3_decode | 80-200 | Subnormal normalization |
| bcd_decode | 50-100 | Shift-add multiply |
| lns8_decode | 200-500 | 16-entry fractional LUT |
| posit8_decode | 150-400 | Regime detect + barrel shift |
| fp4_decode | 30-60 | 16-entry LUT |
| fp6_e3m2_decode | 60-150 | Combinational + subnormal |
| nf4_decode | 80-160 | 16-entry LUT (32-bit values) |
| **format_rom (77x80)** | **1,850-6,160** | Key variable: ABC optimization |
| **Total** | **2,900-8,335** | **Budget: 8,000 cells (4x4)** |

**Assessment:** At the optimistic end (ABC finds good patterns in our regular data), we fit comfortably. At the pessimistic end (1 cell/bit), we're over budget by ~300 cells. The synthesis sprint will resolve this uncertainty.

---

## 4. Project Totals (Cumulative)

| Metric | L1 | L2 | L3 | L4 | L5 | Total |
|--------|----|----|----|----|----|----|
| RTL modules | 2 | 5 | 3 | 0 | 0 (regenerated) | 10 |
| RTL lines | 105 | 384 | 158 | -2 | +100 | 745 |
| Test cases | 4 | 10 | 7 | 9 | 12 | 15 (4+11) |
| ROM records | 0 | 0 | 0 | 0 | 77 | 77 |
| Tools/scripts | 0 | 0 | 0 | 0 | 1 | 1 |
| Total source lines | — | — | — | — | — | 1,553 |

---

## 5. Decomposed Plan (20 days to TTGF26a deadline)

### Phase A: Foundation — COMPLETE (Loops 1-5)
- [x] info.yaml, docs, CI, anchor tests, ADRs
- [x] 8 Tier-1 decoders, Protocol v2, exhaustive tests
- [x] ROM emitter + 77-record ROM + readback tests
- [x] fmt_id alignment with SSOT
- [ ] **Git commit (W18 — urgent)**

### Phase B: Synthesis Validation (Days 2-7)
- [ ] Install OpenLane2/LibreLane + GF180MCU PDK
- [ ] First synthesis: get real cell counts
- [ ] If over budget: ROM field splitting or decoder trimming
- [ ] Timing closure at 50 MHz
- [ ] Area/power report

### Phase C: Integration + DRC (Days 8-15)
- [ ] Full integration test in CI (Ubuntu + Python 3.12 + cocotb)
- [ ] DRC/LVS clean
- [ ] Post-layout timing analysis
- [ ] String table ROM (if area permits)

### Phase D: Submission (Days 16-20)
- [ ] GDS generation
- [ ] TTGF26a submission (deadline: 2026-06-22)
- [ ] Post-silicon test plan

---

## 6. Three Collaboration Options for Next Loop

### Option A: "Git Commit + OpenLane2 Synthesis Sprint"

Commit all 5 loops of work to git (currently nothing is committed). Then install OpenLane2/LibreLane + GF180MCU PDK and run first synthesis. This is the **single most important next step**: W18 (uncommitted work) and W10 (synthesis unvalidated) are both HIGH severity. The synthesis result determines whether we can ship the full design or need to trim.

**Deliverable:** Git history with clean commits, synthesis area/timing/power report.
**Risk addressed:** W18 (data loss), W10 (area validation), timeline de-risking.

### Option B: "CI Pipeline + Cocotb Test Execution"

Set up a working CI pipeline that actually runs the cocotb tests (currently blocked by Python 3.14 locally — need Ubuntu + Python 3.12). Push to GitHub and trigger CI. Verify all 15 tests pass: 4 anchor + 11 decoder/ROM tests (608 decode values + 77 ROM records). Fix any simulation issues discovered.

**Deliverable:** Green CI pipeline, all 15 tests passing, simulation waveforms.
**Risk addressed:** Test confidence, simulation correctness, CI readiness for submission.

### Option C: "ROM Optimization + Area Reduction"

The ROM is the largest area consumer (~1,850-6,160 cells). Implement optimization strategies: (1) split ROM into sub-ROMs per field group (cluster_id and flags rarely change within a cluster — factor them out), (2) assign `80'bx` (don't-care) to unused addresses for better ABC optimization, (3) encode repetitive phi_distance values as delta from cluster baseline. Target: reduce ROM to <3,000 cells, guaranteeing 4x4 fit.

**Deliverable:** Optimized format_rom.v, ROM cell count estimate via Yosys `stat` command.
**Risk addressed:** Area budget, synthesis feasibility.

---

*Generated by Loop iteration 5, 2026-06-01.*
*Project totals: 10 RTL modules (745 lines), 15 cocotb tests, 77 ROM records, 1 tool script, 1,553 total source lines.*
*All RTL passes iverilog lint clean. ROM emitter verified: all 77 records round-trip correctly.*
*WARNING: All changes still uncommitted (W18). Git commit is the top priority for next loop.*
