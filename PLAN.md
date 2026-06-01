# TRI-1 Corona -- Format Conformance Oracle (TTGF26a)

Project repo: gHashTag/tt-trinity-corona
Target shuttle: TTGF26a (GlobalFoundries GF180MCU, 180nm)
Target submission: 2026-06-22 (TTGF26a shuttle close)
Expected silicon delivery: 2026-10-01 (approximately 4 months post-submission)
Document status: SUBMISSION-READY (19 RTL modules, CI green, GDS+precheck+GL PASS, 58 formal tasks, 50 cocotb tests)
Document version: corona_plan-v1.0 (merged from corona_plan_skeleton.md and corona_research.md)

Claim-status key used throughout: [Verified], [Empirical fit], [Open conjecture], [Risk], [Retracted], [Experimental], [Historical], [Spec].
NOTE: References to "OpenLane2" below predate its rebrand to LibreLane 3.x (FOSSi Foundation, July 2025). The actual GDS flow is LibreLane.
ASCII only. No smart quotes. No em-dashes (use `--`). No Cyrillic. No banned words (see docs/CLAIM_STATUS.md for the full list).

---

## 0. TL;DR

- Corona is the fourth chip in the TRI-NET line (after Phi, Euler, Gamma), targeting the GlobalFoundries 180MCU process on the TTGF26a shuttle. Its role is format-conformance oracle, not compute accelerator. [Spec]
- The on-die ROM stores all 80 format records from the SSOT in gHashTag/t27 specs/numeric/formats_catalog.t27 (PR #1028, issue #1029). Each record encodes bit-layout fields, cluster membership, claim-status, and phi-distance in Q16 fixed point. [Spec]
- The TG-TRIAD-X cross-die anchor `{uio_out, uo_out} == 16'h47C0`, derived from `dot4(1,2,3,4)` over GF16 implied by `phi^2 + phi^-2 = 3 = L_2`, carries forward unchanged from Phi/Euler/Gamma to Corona; it is the mechanical sameness-check across all four dice. [Verified in sim; Open until all four dice measured together]
- Corona reuses the T27 module library without duplicating Gamma's 40 RTL modules. The two-die Gamma+Corona D2D assembly is the first configuration in the line at which a single board answers oracle queries for all 80 SSOT format indices. [Spec]
- The FL-002 phi-ladder breadth-as-moat conjecture in gHashTag/trios-trainer-igla src/ledger.rs stays [Open conjecture]. Corona being a registry chip does not promote it. Takum (Hunhold 2024, [arXiv:2412.20273](https://arxiv.org/abs/2412.20273)) remains the standing counterexample and ships in the Corona ROM as a Tier-2 record, not suppressed. [Open conjecture]
- Total honest build estimate is approximately 45-55 calendar-days for a solo developer across Phases A-F. The figure is [Open / aggressive] and depends on GF180MCU PDK toolchain maturity, RTL availability for 12-15 Tier-1 converters, and OpenLane2 DRC convergence on GF180MCU. A minimum-viable Corona ("ROM + 5 converters") collapses this to 6-8 weeks. [Open conjecture]
- The 180nm density penalty vs SKY130A is approximately 2.1x fewer gates per equivalent area. A standard TT tile of 160 x 100 um is estimated to yield approximately 480-520 standard cells at 55% utilization on GF180MCU versus approximately 1,000 at 130nm. This estimate is [Open conjecture] until measured on the GF0p2/GF26a returns. [Open conjecture]

---

## 1. Mission and Non-Mission

### 1.1 What Corona Is

Corona is a read-only conformance oracle: a silicon chip whose primary deliverable is a roughly 1.2-1.4 KB ROM encoding all 80 numeric-format records from the TRI-NET SSOT (gHashTag/t27 PR #1028), plus a set of approximately 12-15 reference RTL encode/decode modules for formats not already owned by Gamma. [Spec] A query arrives as a 7-bit format index on `ui_in[6:0]`; the chip returns the requested record fields across `uo_out` over N read cycles, giving any downstream consumer -- software, FPGA, or another die over D2D -- a single authoritative answer about a format's bit layout, cluster membership, and claim status. [Spec] The design ships under gHashTag/tt-trinity-corona on the TTGF26a shuttle targeting GF180MCU, and every numeric claim it exposes traces back to PR #1028 or is tagged with a claim-status enum that indicates its epistemic standing. [Spec]

The second function of Corona is to serve as the 17th output language of `tools/gen_formats_catalog.py`. The Verilog ROM emitter, produced as a PR to gHashTag/t27, is the primary toolchain artifact; the silicon chip is its validation. [Spec] This makes the SSOT -> codegen -> RTL -> silicon chain end-to-end mechanical. Any divergence between PR #1028 and the ROM output is caught at the CI level (Phase B `rom_readback` gate), not discovered during bring-up. [Spec] The result is a chip whose entire numeric content is traceable to a single versioned source file rather than to hand-transcribed constants. [Spec]

### 1.2 What Corona Is NOT

Corona is NOT a compute-performance entry. It makes no claims about TOPS, throughput, or energy per operation, and no comparison against any other ML accelerator chip should be drawn from its existence. [Spec] It is NOT evidence that the phi-ladder or goldenfloat formats are superior to any competitor numeric system; the FL-002 moat claim stays [Open conjecture] and Corona does not change that status. [Open conjecture] It is NOT a closed-IP product: all RTL, ROM generation scripts, and testbenches are open-source under the same license as the rest of the TRI-NET line; no proprietary silicon or NDA-gated PDK element is included beyond what the GF180MCU PDK already governs. [Spec]

Corona is also NOT a complete numeric co-processor. It cannot independently execute arithmetic on all 80 formats; it exposes format metadata for all 80, and performs encode/decode only on the Tier-1 module subset. [Spec] For formats owned by Gamma (GF4..GF256, FP8, INT4/8, NF4, Posit16, BitNet), the correct compute answer requires D2D routing to Gamma; a standalone Corona board without Gamma present returns the ROM record for those formats but cannot perform their arithmetic. [Spec] This is a deliberate scope boundary, not a defect. [Spec]

### 1.3 The Governing Sentence

The single sentence that governs everything Corona does: the goldenfloat ladder earns its place through breadth and toolchain coherence across many numeric formats, not through per-rung superiority over any individual competitor format. [Open conjecture] Every design decision -- which modules are Tier-1 on-die vs Tier-2 ROM-only, whether a new format is added, how the claim-status enum is set -- is evaluated against this sentence. [Spec] If a proposed addition would require asserting per-rung superiority rather than demonstrating coverage and mechanical traceability, it is deferred or dropped. [Spec]

In practice this sentence has four operational consequences: (a) formats with existing open-source RTL and an entry in PR #1028 are preferred for Tier-1 over formats that require novel research to implement; (b) the claim-status discipline is non-negotiable even under deadline pressure; (c) takum and other counterexamples are kept visible in the ROM as Experimental records rather than suppressed; and (d) the D2D architecture explicitly defers to Gamma for formats Gamma already covers, reinforcing the no-duplication variant of toolchain coherence. [Spec]

---

## 2. Position in the TRI-NET Line

### 2.1 Updated TRI-NET Lineup Table

The table below shows all four chips in the TRI-NET line. Shuttle and PDK assignments are definitive; SKY130A submission for Gamma was 2026-05-17. The Corona tile size is the Phase A decision point. The "Anchor question" column states the specific question each SKU is designed to answer for the line as a whole.

| Chip   | Repo                          | Shuttle  | PDK      | Tile size | Role                        | Anchor question this SKU answers                                       | Status          |
|--------|-------------------------------|----------|----------|-----------|-----------------------------|------------------------------------------------------------------------|-----------------|
| Phi    | gHashTag/tt-trinity-phi       | TTSKY26b | SKY130A  | 1x1       | Identity (sanity baseline)  | Does the minimal phi-kernel synthesize and pass DRC on SKY130A?        | [Verified]      |
| Euler  | gHashTag/tt-trinity-euler     | TTSKY26b | SKY130A  | 8x2       | Safety (overflow/NaN guard) | Do the safety boundaries hold across the GF16 arithmetic domain?       | [Empirical fit] |
| Gamma  | gHashTag/tt-trinity-gamma     | TTSKY26b | SKY130A  | 8x4       | Compute (ternary mesh)      | Can ~40 format-conversion modules coexist in one tile DRC-clean?       | [Empirical fit] |
| Corona | gHashTag/tt-trinity-corona    | TTGF26a  | GF180MCU | 4x4 (16 tiles) | Format-completeness oracle  | Does a silicon ROM faithfully emit all 80 SSOT records bit-exact?      | [Spec]          |

TTSKY26b precedent dates: Gamma was submitted 2026-05-17 (8x4 tile, 103 RTL modules of which ~40 are format-related). [Spec] TTGF26a dates remain to be confirmed at the calendar level. Per the [TinyTapeout chips page](https://tinytapeout.com/chips/), TTGF26a closes in 2026 Q4 with chips expected early 2027. The preceding test shuttle TTGF0p2 (52 designs, closed 2025-11-24) is described on [the TTGF0p2 page](https://tinytapeout.com/chips/ttgf0p2/) as using the gf180mcuD 180nm open-source PDK via wafer.space; TTGF26a was expected to deliver chips by 2026-11-15 per the chips page. The 5-6 month close-to-delivery interval is the basis for the early-2027 Corona delivery estimate. The exact TTGF26a close date should be verified against the TinyTapeout shuttle index near 2026 Q3. [Open conjecture]

Escalation of SKU questions through the line: Phi answers "does the substrate work?"; Euler answers "are the safety semantics correct?"; Gamma answers "can multiple formats coexist in silicon?"; Corona answers "can the full catalog be mechanically traced from SSOT to silicon?". [Spec] Each chip is necessary but not sufficient; the complete answer to "does the TRI-NET toolchain hold together across all 80 formats?" requires all four dice plus a Gamma+Corona D2D assembly. [Open conjecture]

### 2.2 Why the Cross-Die Anchor 0x47C0 Carries Over

The TG-TRIAD-X cross-die anchor `{uio_out, uo_out} == 16'h47C0` is derived from `dot4(1,2,3,4)` over GF16, where GF16 is implied by `phi^2 + phi^-2 = 3 = L_2`. It is a mechanical identity, not a format-specific result. [Verified in sim] Because the anchor depends only on the GF16 arithmetic structure shared by all four chips -- not on any particular process node, tile size, or format cluster -- it remains a valid sameness-check on every die in the line. [Empirical fit]

The anchor is produced by asserting a reserved format index (proposed: `7'h7F` = all-ones, reserved) on `ui_in[6:0]`. The chip responds with `{uio_out, uo_out} == 16'h47C0` within one or two clock cycles, before any ROM record read protocol is needed. [Spec] A new bring-up board can therefore confirm the Corona die is alive and responding with correct GF16 arithmetic in roughly 10 lines of Python, using exactly the same test helper already written for Phi, Euler, and Gamma. [Spec] Any divergence from 0x47C0 is an unambiguous failure indicator that requires die-level diagnosis before further testing. [Spec]

Mathematical grounding: `phi^2 + phi^-2 = 3` is the Lucas number `L_2` (classical, 1878, Binet-formula corollary, not original to anyone in this project). It maps to GF16 element 3 under the canonical embedding. `dot4(1,2,3,4)` over GF16 = `1*1 XOR 2*2 XOR 3*3 XOR 4*4` (GF16 arithmetic) encodes to 0x47C0 in the 16-bit output container. [Verified in sim, against the existing Phi/Euler/Gamma test suites]

### 2.3 Two-Die Packaging: Gamma + Corona on One Board (D2D)

The Gamma+Corona two-die assembly on a shared bring-up board is the first configuration in the TRI-NET line in which a single board answers format-oracle queries for all 80 SSOT records, spanning both the Gamma-native ~40-module RTL set and the Corona-native ~12-15 new converters plus the full ROM. [Spec] The board connects two TinyTapeout module slots (or equivalent breakout connectors, depending on the TTGF26a carrier format) with a direct digital interface on the shared TT bus. [Spec] From the host perspective, the assembly behaves as a single oracle: format index in, record or encode/decode result out, with internal routing to Gamma or Corona transparent to the caller. [Spec]

The D2D routing logic resides in the Corona die's adapter module (`rtl/d2d_corona_adapter.v`, Phase D deliverable). [Spec] The existing tt-trinity-gamma `d2d_holo_mesh.v` uses a 4-port holographic mesh: `uio[3:0]` = TX (North, East, South, West, one bit each, or packed nibble); `uio[7:4]` = RX (corresponding). [Spec] Reusing `d2d_holo_mesh.v` from gamma as a submodule (git submodule or vendor copy) reduces Phase D effort to wiring and a protocol state machine of approximately 100-200 cells overhead. [Open conjecture]

Latency: Corona receives a format index, asserts D2D_REQ, waits for D2D_ACK from Gamma (expected 1-4 cycles for board-level propagation), latches Gamma's result, and forwards it. At 25 MHz a 4-byte cross-die query is approximately 160 ns round-trip. [Open conjecture] The exact timing will be characterized in Phase D simulation. [Spec]

The physical two-die board is currently a design intent and not a committed deliverable. Whether it is in-scope for the Corona project or a separate post-submission bring-up project is an open question for the user (Section 10, Q3). [Open conjecture]

---

## 3. Catalog as Silicon -- The 80 Records

### 3.1 The 80 Formats by Cluster

The SSOT for all 80 format records is gHashTag/t27 `specs/numeric/formats_catalog.t27`, governed by PR #1028 and tracked in issue #1029. [Spec] The 13-cluster breakdown below is the structure carried by the SSOT at PR #1028 head (commit 18ae35a, branch `feat/formats-catalog-ssot-77-formats`); cluster counts sum to exactly 80. Any deviation is a CI failure. [Spec]

| Cluster                             | Count | Example formats                                                   | Dominant claim status |
|-------------------------------------|-------|-------------------------------------------------------------------|-----------------------|
| IEEE 754 binary                     | 5     | F16, F32, F64, F128, F256                                         | [Verified] (IEEE)     |
| IEEE 754 decimal                    | 3     | decimal32, decimal64, decimal128 (DPD/BID)                        | [Historical]          |
| MLLowPrecision                      | 8     | FP8 E4M3, FP8 E5M2, FP4, FP6 E3M2, FP6 E2M3, INT4, INT8, BF16    | [Verified] / [Empirical fit] |
| GoldenFloat (GF4..GF256)            | 16    | GF4, GF8, GF12, GF16, GF20, GF24, GF32, GF64, GF256 + variants    | [Verified] (algebra), [Open conjecture] (moat) |
| Posit/Unum III (posit + takum)      | 8     | posit8/16/32/64, takum8/16/32/64                                  | [Empirical fit] (posit), [Experimental] (takum) |
| OCP MX                              | 5     | mxfp8, mxfp6, mxfp4, E8M0, MXINT8                                  | [Spec]                |
| LNS                                 | 4     | lns8, lns16, lns32, lns64                                         | [Experimental]        |
| IntegerFixed                        | 8     | BCD, Q-format, INT8/16/32/64 variants, signed/unsigned splits     | [Verified]            |
| Historical Vendor                   | 10    | IBM HFP single/double, MBF, VAX F/D/G/H, Cray, x87 80-bit, PDP-11 | [Historical]          |
| Theoretical                         | 4     | Unum I, Unum II, minifloat, tapered FP                            | [Experimental]        |
| Compression / scaling               | 4     | block_fp, shared_exp, stochastic_rounding, per_channel_scale      | [Spec]                |
| Extended                            | 3     | double-double, quad-double, x87 80-bit extended                   | [Experimental]        |
| QuantTuned                          | 2     | NF4, AFP                                                          | [Empirical fit] (NF4), [Open conjecture] (AFP) |
| **TOTAL**                           | **80**|                                                                   |                       |

The phi-distance field (`phi_distance_q16`, 16-bit Q16 fixed point) records the distance from each format's dynamic range or precision to the nearest phi-ladder rung. [Empirical fit] This field is computed by the SSOT toolchain and stored verbatim in the ROM; it is NOT a claim that phi-ladder rungs are superior, only that a distance metric exists. [Open conjecture] The `status_id` field, not `phi_distance_q16`, is the authoritative epistemic tag for each record. [Spec]

### 3.2 ROM Layout: Per-Record Field Schema

Each of the 80 records occupies a fixed-width entry in the on-chip ROM. [Spec] The field schema below is the current Phase B design target; exact bit-widths are locked when the Verilog ROM emitter is validated against PR #1028 in Phase B CI. [Spec] The total per-record width is a multiple of 8 bits to simplify byte-addressed read-back over the TT bus. [Spec]

| Field name           | Width (bits) | Notes / encoding                                                                | Claim status    |
|----------------------|--------------|---------------------------------------------------------------------------------|-----------------|
| format_index         | 7            | Primary key 0-79; matches SSOT record order in PR #1028; `7'h7F` = anchor       | [Spec]          |
| sign_bits (s)        | 4            | Count of sign bits (0 for unsigned, 1 for most IEEE/posit, 2 for complex)       | [Spec]          |
| exponent_bits (e)    | 6            | Exponent field width; 0 for pure-integer formats                                | [Spec]          |
| mantissa_bits (m)    | 7            | Significand / mantissa field width; includes implicit-bit count where present   | [Spec]          |
| bias                 | 16           | Exponent bias, signed two's complement Q0; 0 for integer/log-number formats     | [Spec]          |
| cluster_id           | 4            | Cluster enum (0-12, matches Section 3.1 cluster order)                          | [Spec]          |
| status_id            | 4            | Claim-status enum (see Section 3.4)                                             | [Spec]          |
| phi_distance_q16     | 16           | Distance from nearest phi-ladder rung, Q16; `0xFFFF` = undefined                | [Empirical fit] |
| source_string_idx    | 8            | Index into companion string table (DOI / arXiv ref / spec name)                 | [Spec]          |
| reserved / pad       | 8            | Reserved; must read 0; pads record to a 10-byte (80-bit) boundary               | [Spec]          |
| **Total per record** | **80 bits = 10 bytes** | 80 records x 10 bytes = 800 bytes; plus string table ~500 bytes; total ROM ~1.2-1.4 KB | [Spec] |

A 1.2-1.4 KB ROM at 180nm is small but non-trivial. Per the [TinyTapeout memory spec](https://tinytapeout.com/specs/memory/), one TT tile holds approximately 320 DFFs (40 bytes); storing 1,232 bytes as DFFs would consume around 31 tiles equivalent and is rejected. [Spec] The ROM is instead synthesized as a Verilog case statement (combinational mux tree) on the 7-bit `format_index` address. Yosys synthesis of an 80-entry, 80-bit-wide ROM typically produces 2,000-6,000 standard cells (mostly multiplexers and AND gates), which maps to approximately 4-12 GF180MCU tiles of area at the 480-520 gates/tile density estimate. [Open conjecture] This is the dominant non-converter area in Corona; Phase A includes a synthesis trial to refine the estimate before committing tile size. [Spec]

### 3.3 Read-Back Protocol Over TT Pins

Corona's pin budget per the [TinyTapeout FAQ](https://tinytapeout.com/faq/): 8 `ui_in` (input only) + 8 `uo_out` (output only) + 8 `uio` (bidirectional) = 24 total GPIO. When D2D is active, `uio[3:0]` and `uio[7:4]` carry inter-die TX/RX traffic, leaving 8 `ui_in`, 8 `uo_out`, and up to 4 `uio` bits for the primary oracle interface. [Spec]

Proposed 8-bit serial CMD/DATA protocol on `ui_in` / `uo_out`:

```
Mode[1:0] = ui_in[7:6]
    00 = CMD     -- ui_in[6:0] = fmt_id (0..76; 7'h7F = anchor probe)
    01 = DATA_IN -- ui_in[7:0] = next byte of input bit pattern
    10 = STATUS  -- trigger decode/encode; result bytes streamed on uo_out
    11 = reserved

Cycle sequence for a 32-bit decode query:
  1. CMD     ui_in = {2'b00, fmt_id[6:0]}
  2..5. DATA ui_in = {2'b01, byte_k} for k = 0..3
  6. STATUS  ui_in = {2'b10, 6'b0}
  7..10. uo_out streams 4 bytes of decoded value
```

This 10-cycle protocol fits the TT 8-bit I/O model and handles up to 32-bit formats. For 64-bit formats, extend to 18 cycles at 25 MHz. For 128-bit formats, extend to 34 cycles. [Spec] The `uio` control encoding for field-select (when reading multi-byte ROM records) uses `uio_in[3:0]` = field selector and `uio_in[7:4]` = cycle-within-field. `uio_out[7]` is a valid flag; `uio_out[6:0]` carries field-specific metadata. [Spec]

Anchor protocol: `format_index = 7'h7F` with mode = 0 produces `{uio_out, uo_out} = 16'h47C0` on cycle 0 unconditionally. [Spec]

Minimum conformance proof per format: encode(canonical_value, N) produces the expected bit pattern; decode(expected_bit_pattern, N) returns the canonical value within round-trip tolerance. This is approximately 6-10 test vectors per format minimum, 50 vectors for robust conformance. [Spec]

### 3.4 Status Discipline in ROM

Every ROM record carries a 4-bit `status_id` field matching the project-wide claim-status vocabulary. The encoding is fixed and must not change between Phase B and Phase F without a corresponding update to PR #1028. [Spec]

| status_id (4-bit) | Project tag        | Meaning                                                                 |
|-------------------|--------------------|-------------------------------------------------------------------------|
| 0                 | [Verified]         | RTL tested in simulation and confirmed on physical silicon              |
| 1                 | [Empirical fit]    | Passes test suite; theoretical grounding partially established         |
| 2                 | [Open conjecture]  | Not yet falsified; may be true; standing counterexamples exist          |
| 3                 | [Risk]             | Used in practice but known failure modes documented                     |
| 4                 | [Retracted]        | Previously published or claimed, subsequently falsified                 |
| 5                 | [Experimental]     | Prototype stage only; no production validation                          |
| 6                 | [Historical]       | Legacy format; no active toolchain; included for catalog completeness   |
| 7                 | [Spec]             | Definition only; no known open-source implementation                    |
| 8-15              | Reserved           | Must read 0; reserved for future claim-status extensions                |

The `status_id` is generated directly from the SSOT status field in PR #1028 by the Verilog ROM emitter. Claim-status drift between SSOT and silicon is therefore a CI-level failure caught in Phase B, not a post-hoc review item. [Spec] Any record whose status changes between PR #1028 head and Phase F tape-out goes through a PR update first; the ROM is never edited directly. [Spec]

---

## 4. Reference RTL Converters -- What Is On-Die vs ROM-Only

### 4.1 What Gamma Already Has (~40 Modules, Reused via T27 Module Library)

Gamma (gHashTag/tt-trinity-gamma, 8x4 SKY130A) synthesizes and passes DRC with approximately 40 format-conversion modules out of its 103 total RTL modules. [Empirical fit] The T27 module library is the shared RTL source for both Gamma and Corona; no RTL is duplicated between repos -- Gamma pulls one subset, Corona pulls a different subset. [Spec]

The Gamma-native categories (approximate counts; exact list to be confirmed at repo-creation time against the tt-trinity-gamma `rtl/` directory):

| Category                  | Approx. count | Example modules                                                  | Claim status    |
|---------------------------|---------------|------------------------------------------------------------------|-----------------|
| GF ladder (GF4..GF256)    | ~10           | gf4_add, gf4_mul, gf16_add, gf16_mul, gf256_add, gf256_mul, etc. | [Verified]      |
| GF16 ecosystem            | ~6            | gf16_dot4, gf16_inv, gf16_sqrt_approx, gf16_matvec               | [Verified]      |
| FP8 (E4M3 / E5M2)         | ~4            | fp8e4m3_encode, fp8e4m3_decode, fp8e5m2_encode, fp8e5m2_decode   | [Empirical fit] |
| INT4 / INT8               | ~4            | int4_quantize, int8_quantize, int4_dequant, int8_dequant         | [Verified]      |
| NF4                       | ~2            | nf4_encode, nf4_decode                                           | [Empirical fit] |
| Posit16                   | ~2            | posit16_encode, posit16_decode                                   | [Empirical fit] |
| BitNet (INT1)             | ~2            | bitnet_pack, bitnet_unpack                                       | [Spec]          |
| Format converters (cross) | ~10           | fp32_to_fp16, fp32_to_bf16, fp16_to_fp32, fp32_to_int8, ...      | [Empirical fit] |
| **Total Gamma modules**   | **~40**       |                                                                  |                 |

Gamma also includes `d2d_holo_mesh.v` (the 4-port holographic D2D mesh, reused by Corona) and the TG-TRIAD-X anchor stimulus generator. [Spec]

These modules are owned by Gamma and available to the Gamma+Corona D2D assembly. Corona does not re-synthesize any of them. Any proposed Tier-1 Corona module that overlaps with a Gamma module (e.g., a second posit16) must be explicitly justified and de-duplicated in the T27 module library to avoid divergence. [Spec]

### 4.2 What Corona Adds On-Die (Tier-1, Target 12-15 Modules)

The Tier-1 on-die module set for Corona, with RTL availability and license status from corona_research.md. Each entry requires (a) an open-source RTL reference, (b) a compatible license, (c) complexity fitting within the tile budget, (d) no duplication with any Gamma module. Entries flagged "License TBD" are pre-demoted to Tier-2 if confirmation does not arrive before Phase C scope freeze. [Spec]

| Module name            | Format cluster      | Reference / spec                                | RTL source                                                                                                  | License        | Est. cells (GF180MCU) | Tier | Claim status     |
|------------------------|---------------------|--------------------------------------------------|-------------------------------------------------------------------------------------------------------------|----------------|-----------------------|------|------------------|
| posit8_decode          | Posit               | Posit Standard 2022 ([posithub.org](https://posithub.org/docs/posit_standard-2.pdf)) | [FloPoCo](https://flopoco.org) (LGPL); SoftPosit golden ref                                                  | LGPL           | 300-800               | 1    | [Experimental]   |
| posit32_decode         | Posit               | Posit Standard 2022                              | FloPoCo (LGPL); cross-check vs [PERCIVAL](https://github.com/artecs-group/PERCIVAL) (license TBD)            | LGPL           | 4,000-8,000           | 1    | [Experimental]   |
| bf16_decode            | IEEE 754 ext.       | [Wikipedia bfloat16](https://en.wikipedia.org/wiki/Bfloat16_floating-point_format) | Trivial truncation; FloPoCo `(wE=8, wF=7)` reference                                                          | LGPL           | 50-200                | 1    | [Verified]       |
| tf32_decode            | IEEE 754 ext.       | NVIDIA TF32 public spec                          | FloPoCo `(wE=8, wF=10)`                                                                                       | LGPL           | 50-200                | 1    | [Verified]       |
| mxfp8_e4m3_decode      | OCP MX              | OCP MX v1.0 ([Rouhani et al. arXiv:2310.10537](https://arxiv.org/abs/2310.10537)) | Hand-rolled per spec; no open RTL for full MX block                                                          | Apache-2.0 (own) | 200-400              | 1    | [Experimental]   |
| lns8_decode            | LNS                 | [Alam, Garland, Gregg arXiv:2102.06681](https://arxiv.org/abs/2102.06681) | Hand-rolled; Coleman log-add table; no open RTL standalone                                                  | Apache-2.0 (own) | 200-500              | 1    | [Experimental]   |
| decimal32_decode (DPD) | IEEE 754 decimal    | [Cowlishaw spec](https://speleotrove.com/mfc/files/cowlishaw2001-decimal-specification.pdf); IEEE 754-2008 cl. 3.5 | Hand-rolled DPD; no open RTL found; software oracle = Python `decimal`                                       | Apache-2.0 (own) | 1,500-5,000          | 1    | [Experimental]   |
| fp4_decode             | MLLowPrecision      | OCP MX E2M1; 4-bit FP                            | Trivial 16-entry case statement                                                                              | Apache-2.0 (own) | 30-50                | 1    | [Verified]       |
| fp6_decode             | MLLowPrecision      | OCP MX E3M2/E2M3                                 | Trivial 64-entry case statement                                                                              | Apache-2.0 (own) | 80-200                | 1    | [Verified]       |
| nf4_decode             | QuantTuned          | [Dettmers et al. QLoRA arXiv:2305.14314](https://arxiv.org/abs/2305.14314) Table 1 | 16-entry LUT (Q0.15 fixed-point); [bitsandbytes](https://github.com/TimDettmers/bitsandbytes) CUDA reference  | Apache-2.0 (own) | 50-100               | 1    | [Verified]       |
| bcd_decode             | IntegerFixed        | IEEE 754-2008 BCD; [OpenCores BCD adder](https://opencores.org/projects/bcd_adder) | OpenCores BCD adder reference (LGPL)                                                                          | LGPL           | 200-500               | 1    | [Verified]       |
| takum16_decode         | Posit/Unum III      | [Hunhold 2024 arXiv:2408.10594 v4](https://arxiv.org/html/2408.10594v4); [Hunhold 2024 arXiv:2412.20273](https://arxiv.org/abs/2412.20273) | Hunhold VHDL (license NOT stated in arXiv, see R2)                                                            | TBD (R2)       | 500-1,000             | 1*   | [Experimental]   |

`* takum16_decode is conditional on R2 license confirmation (Section 7).` If the Hunhold VHDL license cannot be confirmed as Apache-2.0-compatible before Phase C, takum16 is demoted to Tier-2 ROM-only and a clean-room takum8 codec is implemented from the mathematical definition in arXiv:2412.20273 (estimated 5 calendar-days, ~500-1,000 cells). [Open conjecture]

Stretch entries (added only if Tier-1 fits the tile budget after the Phase A synthesis trial):

| Module name        | Format cluster     | Reference                                                                                          | License        | Est. cells | Tier | Claim status   |
|--------------------|--------------------|----------------------------------------------------------------------------------------------------|----------------|------------|------|----------------|
| ibm_hfp32_decode   | Historical         | [Wikipedia IBM HFP](https://en.wikipedia.org/wiki/IBM_hexadecimal_floating-point); [Hercules float.c](https://github.com/SDL-Hercules-390/hyperion/blob/master/float.c) (Q Public License -- behavioral ref only); [ibm_hfp Rust crate](https://docs.rs/ibm_hfp) | Apache-2.0 (own) | 500-1,500 | 2    | [Historical]   |
| vax_f_decode       | Historical         | DEC VAX architecture manuals; [SimH VAX simulator](https://simh.trailing-edge.com) (BSD-style, behavioral) | Apache-2.0 (own) | 300-600   | 2    | [Historical]   |
| mxfp4_decode       | OCP MX             | OCP MX v1.0 E2M1                                                                                   | Apache-2.0 (own) | 30-50     | 2    | [Experimental] |
| mxfp6_decode       | OCP MX             | OCP MX v1.0 E3M2/E2M3                                                                              | Apache-2.0 (own) | 100-200   | 2    | [Experimental] |
| mbf32_decode       | Historical         | [Arduino Forum MBF analysis](https://forum.arduino.cc/t/mbf-microsoft-binary-format-to-32-bit-float/1315590); public-domain converter snippets | Apache-2.0 (own) | 100-300   | 2    | [Historical]   |

Tier-1 cell budget summary (all decode-only): ~5,000-12,000 standard cells for the core ten-module Tier-1 set. At 480-520 GF180MCU cells per tile this is approximately 10-25 tiles for converters, plus 4-12 tiles for the ROM. An 8x4 = 32 tile allocation is comfortable at the optimistic density end; an 8x2 = 16 tile allocation forces a drop to the smaller Tier-1 subset (drop posit32, decimal32, takum16). [Open conjecture] Posit32 is the highest-risk Tier-1 entry; if it cannot fit, the MVP "ROM + posit8 + bf16 + tf32 + mxfp8 + lns8" subset is the documented fallback. [Spec]

Mitigation rule: implement decode-only (not arithmetic) for all formats. Decode is typically 2-5x cheaper in area than a full FPU. Start with the ROM only (Phase B), measure actual GF180MCU synthesis cell counts, and add converters incrementally in Phase C. [Spec]

### 4.3 What Stays ROM-Only (Tier-2: Historical and Experimental)

The following format records ship in the ROM with full metadata (all fields populated from PR #1028) but have no on-die encode/decode RTL. They carry `status_id = 5` (Experimental) or `status_id = 6` (Historical), and any attempt to invoke them in compute mode returns a defined `not_implemented` error code on `uo_out`. [Spec]

| Format                       | Cluster              | Reason for ROM-only                                                                       | status_id        |
|------------------------------|----------------------|-------------------------------------------------------------------------------------------|------------------|
| Takum 8/32/64 (and 16 if R2 blocks) | Posit/Unum III | No open RTL release with confirmed license; live FL-002 counterexample                    | Experimental (5) |
| Posit64                      | Posit                | Estimated ~8,000-20,000 GF180MCU cells; exceeds reasonable single-die budget              | Experimental (5) |
| VAX F / D / G / H            | Historical           | No open RTL found; SimH provides software reference only; VAX H is 128-bit                | Historical (6)   |
| IBM HFP single / double      | Historical           | Mainframe-only context; Hercules behavioral ref under Q Public License (not synthesizable) | Historical (6)   |
| Microsoft MBF (32-bit)       | Historical           | Converter snippets exist but no synthesizable RTL with FOSS license                       | Historical (6)   |
| Cray 64-bit (1977 brochure)  | Historical           | No open RTL; format described in [Cray-1 1977 brochure](https://s3data.computerhistory.org/brochures/cray.cray1.1977.102638650.pdf) | Historical (6)   |
| PDP-11 floating-point        | Historical           | Museum format; no active toolchain                                                        | Historical (6)   |
| x87 80-bit extended          | Extended             | Well-documented (John Hauser [SoftFloat](https://www.jhauser.us/arithmetic/SoftFloat.html)), but no standalone open Verilog encode/decode | Historical (6)   |
| decimal64, decimal128        | IEEE 754 decimal     | DPD encoding scales; decimal32 already covers the protocol; d64/d128 deferred             | Experimental (5) |
| lns16 / lns32 / lns64        | LNS                  | LNS lookup tables dominate area at >8-bit; ~10,000 cells estimated for lns32              | Experimental (5) |
| Unum I (variable-length)     | Theoretical          | Variable-length encoding incompatible with fixed-width digital logic                       | Experimental (5) |
| Unum II                      | Theoretical          | [posithub.org](https://posithub.org/khub_doc) records this as an abandoned design; BSV references only | Experimental (5) |
| Minifloat (general)          | Theoretical          | Parameterized FP; no canonical size; covered by FloPoCo for any `(wE, wF)`                | Experimental (5) |
| Tapered FP (Kahan)           | Theoretical          | Pre-posit concept; no open RTL                                                            | Historical (6)   |
| MXFP2 (speculative)          | OCP MX               | Not in OCP MX v1.0; status unresolved                                                     | [Open conjecture] (2) |
| AFP (Microsoft MSFP)         | QuantTuned           | No open RTL; [Microsoft research blog (2020)](https://www.microsoft.com/en-us/research/blog/a-microsoft-custom-data-type-for-efficient-inference/) describes concept only | [Open conjecture] (2) |
| Compression-cluster entries  | Compression          | block_fp, shared_exp, stochastic_rounding, per_channel_scale are encoding strategies, not pure formats; record-only | Spec (7)         |
| double-double, quad-double   | Extended             | Software-only multi-component representations; no open silicon RTL                        | Experimental (5) |

### 4.4 What Is Fetched D2D from Gamma (the ~40 Gamma-Native Modules)

The design contract is explicit: Corona does NOT synthesize any module that Gamma already owns. [Spec] This is enforced at the T27 module library level: if a module name appears in Gamma's instance list, it cannot appear in Corona's RTL instantiation unless a supermajority PR review in gHashTag/t27 explicitly overrides this rule. [Spec]

For a Gamma+Corona two-die assembly, the D2D routing table is derived directly from the `cluster_id` field of each ROM record. [Spec] A `cluster_id` in the set `{GF ladder, GF16 ecosystem, FP8, INT4/8, NF4, Posit16, BitNet}` routes to Gamma; all other `cluster_id` values route to Corona's own Tier-1 modules or return a ROM-only (no-compute) response. [Spec] The routing table is a 7-bit lookup indexed by `format_index`, synthesized from the ROM `cluster_id` field; no separate configuration is required. [Spec]

D2D latency model: Corona receives `format_index`, asserts D2D_REQ on `uio_out[0]`, waits for D2D_ACK on `uio_in[0]` from Gamma (1-4 cycles, board-level propagation), latches Gamma's `uo_out` result, and forwards it. [Open conjecture] Exact timing characterized in Phase D simulation. [Spec]

---

## 5. TTGF26a Shuttle and GF180MCU PDK

### 5.1 Submission Window and Delivery Estimate

Per the [TinyTapeout chips page](https://tinytapeout.com/chips/), TTGF26a targets a 2026 Q4 submission close with chips expected in early 2027. [Open conjecture] The preceding test shuttle TTGF0p2 (52 designs, closed 2025-11-24, chips expected May 2026) used the `gf180mcuD` 180nm open-source PDK via wafer.space, per [the TTGF0p2 page](https://tinytapeout.com/chips/ttgf0p2/). The TTGF26a shuttle (WS-2606, closed 2026-06-22) was expected to deliver chips by 2026-11-15, giving a 5-6 month close-to-delivery interval that the Corona plan assumes for TTGF26a. [Open conjecture] The exact TTGF26a calendar date will be confirmed via the [GF GlobalShuttle MPW schedule](https://gf.com/manufacturing-services/multi-project-wafer-program/) and the TinyTapeout shuttle index near 2026 Q3. [Spec]

Key dates to confirm before Phase F:
- TTGF26a tape-out submission cutoff (exact calendar date).
- Expected silicon return date.
- PDK freeze date for GF180MCU (after which cell-library changes are locked).
- Whether a no-change resubmission (same GDS, next shuttle) is possible if Phase F misses the target window.

If the shuttle window is earlier than 2026 Q3, the Phase A-F plan requires immediate compression and the user must be notified. [Risk]

### 5.2 Tile Budget on GF180MCU

The standard TT tile size per the [TinyTapeout FAQ](https://tinytapeout.com/faq/) is 160 x 100 um and provides approximately 1,000 standard cells per tile at 55-60% utilization on SKY130A. On GF180MCU, the [vlsitechnology.org density table](https://www.vlsitechnology.org/html/lib_densities.html) gives approximately 52 kGates/mm^2 vs approximately 110 kGates/mm^2 for SKY130A -- a ratio of approximately 2.1x. Applied to the 0.016 mm^2 tile, this yields approximately **480-520 gates per tile at 55% utilization** on GF180MCU. [Open conjecture] No official TinyTapeout GF180MCU gate count per tile has been published; the estimate must be replaced with the actual measurement from TTGF0p2 / TTGF26a returns when available. [Risk]

Per the [early TinyTapeout technical paper (TechRxiv 2024)](https://d197for5662m48.cloudfront.net/documents/publicationstatus/212580/preprint_pdf/d39c8459714cce99c57003adea344a94.pdf), the maximum project size historically was 8x2 tiles (1359 x 225 um, around 20,000 logic cells on SKY130A); later shuttles supported 8x4 and an experimental 5x4 colossal tile. For TTGF26a, assume 8x4 tiles as the plausible maximum; confirm with the TinyTapeout team before submission. [Open conjecture]

GF180MCU process notes:
- 6 metal layers total (Metal1-Metal5 + MetalTop, up to 3.035 um thick).
- Metal5 is reserved by TinyTapeout for the power distribution grid; designs cannot use it. [Spec]
- Higher core voltage than SKY130A (3.3V vs 1.8V); TT carrier handles VIO/Vcore separation.
- 180nm cells are slower. At 25 MHz the critical path budget is 40 ns -- comfortable for simple format converters and adequate for multi-stage FP adders.
- GF180MCU open PDK does NOT include an open-source SRAM macro as of writing; any memory beyond DFFs must be synthesized from flip-flops or as combinational ROM. [Spec]
- COB (chip-on-board) packaging on TTGF26a: chips are die-bonded directly to the PCB and cannot be removed from the board, per the [TinyTapeout FAQ](https://tinytapeout.com/faq/). This affects prototyping workflow. [Spec]

### 5.3 PDK Status: Open-Source Level and Tooling

The GF180MCU PDK is genuinely open-source under Apache 2.0, released by Google/GlobalFoundries. Key resources:

- PDK GitHub: [google/globalfoundries-pdk-libs-gf180mcu_fd_sc_mcu7t5v0](https://github.com/google/globalfoundries-pdk-libs-gf180mcu_fd_sc_mcu7t5v0) -- 7-track standard cells, 100% Verilog, Apache-2.0. [Verified]
- PDK documentation: [gf180mcu-pdk.readthedocs.io](https://gf180mcu-pdk.readthedocs.io/) -- DRC rules, antenna rules, interconnect specs.
- Cell libraries: 7-track (`gf180mcu_fd_sc_mcu7t5v0`) and 9-track (`gf180mcu_fd_sc_mcu9t5v0`), both 5V nominal with 3.3V core compatibility in TT configuration.
- EDA tools: OpenLane2 (OpenROAD, Yosys, KLayout, Magic, TritonRoute) per [openroad.readthedocs.io](https://openroad.readthedocs.io/); GF180MCU support is confirmed in [LibreLane Changelog](https://github.com/librelane/librelane/blob/main/Changelog.md).
- PDK history: the [Zero to ASIC Course blog](https://www.zerotoasiccourse.com/post/excited_by_silicon/) recounts that the Google/GF180MCU PDK was released end of 2022, temporarily lost when Google sponsorship ended, then revived via the Swiss Chips / wafer.space partnership in 2024.

GF180MCU-specific gotchas:
1. **DRC density rules.** Metal-fill density requirements. OpenLane2 inserts fill automatically, but complex RTL may require manual density-check iteration.
2. **Antenna rules.** Per the [GF180MCU antenna document](https://mithro-gf180mcu-pdk.readthedocs.io/en/latest/physical_verification/design_manual/drm_08.html): poly2 ratio limit 200; metal1-MetalTop perimeter ratios 400; via area ratios 20. Similar in character to SKY130A but with specific numeric thresholds; use OpenLane2 diode insertion.
3. **Metal5 reserved.** PDN; designs cannot use it.
4. **Cell timing.** 180nm cells are slower; budget single-cycle critical paths conservatively.
5. **SKY130A port delta.** The t27 toolchain and CI scripts assume SKY130A. A GF180MCU port requires at minimum a new `config.json` (`PDK=gf180mcu`, `STD_CELL_LIBRARY=gf180mcu_fd_sc_mcu7t5v0`), new cell library references, and re-timing.

Toolchain risk summary: OpenLane2 GF180MCU flow is less battle-tested than SKY130A; known PDK errata may require workarounds not yet documented in the TinyTapeout infrastructure. [Risk] Phase A is explicitly the PDK exploration phase and produces a go/no-go memo before Phase B begins. [Spec]

### 5.4 First Corona Tile Budget Guess

Two primary candidate tile sizes are under evaluation for Phase A. The decision is made at the end of Phase A after PDK density data is in hand. [Spec]

| Candidate | Tile count | Rationale                                                                                                                | ROM fit (~1.4 KB) | Tier-1 RTL fit (12-15 modules) | Recommendation                                          |
|-----------|------------|--------------------------------------------------------------------------------------------------------------------------|-------------------|--------------------------------|---------------------------------------------------------|
| 8x2       | 16         | Conservative; same as Euler on SKY130A; at ~50% density penalty equivalent to ~4x2 SKY130A; tight RTL budget             | Very likely       | Tight; may force drop to 8-10 modules | Start here; upgrade if Phase A confirms better density   |
| 8x4       | 32         | Same as Gamma on SKY130A; comfortable for ROM + 12-15 modules; higher shuttle cost if priced per tile                    | Yes               | Comfortable; allows posit32 + lns8 + decimal32 | Upgrade to this if Phase A density permits               |
| 8x8       | 64         | Speculative; would allow research modules or spare capacity; requires explicit shuttle pricing confirmation              | Yes               | Very comfortable                | Do not assume; requires user sign-off (Section 10, Q1)   |

The minimum viable Corona ("ROM + anchor + 5 confirmed RTL modules") should fit in 8x2 even at the pessimistic 50% density estimate. [Open conjecture] The 8x4 tile allows the full 12-15 module Tier-1 list. [Open conjecture] The decision gate is the Phase A tile-budget memo, which must include: (a) synthesis area estimate for ROM only, (b) area estimate per proposed Tier-1 module, (c) total projected utilization at 50% and 70% density targets, (d) recommendation for tile size. [Spec]

---

## 6. Decomposed Milestone Plan (Phases A-F)

Total honest estimate across all six phases: approximately 45-55 calendar-days for a solo developer. [Open conjecture] The figure is [Open / aggressive] and depends on PDK toolchain maturity (Phase A), RTL availability for 12-15 Tier-1 modules (Phase C), D2D protocol complexity (Phase D), and OpenLane2 DRC convergence on GF180MCU (Phase F). [Risk] Each phase has a falsification path (Fpath) defining the evidence that would require declaring the phase failed and escalating to the user.

### Phase A: Repo Bootstrap (~3 calendar-days) [Spec]

| Field            | Detail                                                                                                                                                                                                                  |
|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Deliverable      | gHashTag/tt-trinity-corona repo initialized; OpenLane2 + GF180MCU PDK installed and DRC-clean on a hello-world stub tile; tile-budget memo produced comparing 8x2 vs 8x4 on confirmed PDK density.                      |
| RTL files added  | `tt_um_trinity_corona.v` (stub: TG-TRIAD-X anchor output only; 24 GPIO connected; compiles clean), `info.yaml` (TTGF26a metadata, tile size TBD), `config.json` (`PDK=gf180mcu`, `STD_CELL_LIBRARY=gf180mcu_fd_sc_mcu7t5v0`). |
| Test files added | `test/test_stub.py` (cocotb; checks basic IO connectivity), `test/test_anchor.py` (asserts `{uio_out, uo_out} == 16'h47C0` on `format_index = 7'h7F`).                                                                  |
| CI gate          | OpenLane2 synthesis + DRC passes on the stub tile; anchor test green; tile-budget memo filed as a Phase A artifact.                                                                                                     |
| Claim status     | [Spec] for all Phase A outputs; nothing is [Verified] until silicon.                                                                                                                                                    |
| Effort estimate  | 3 calendar-days.                                                                                                                                                                                                        |
| Fpath            | PDK fails to install cleanly OR DRC produces unresolvable violations on the hello-world tile after 5 days; escalate to user with a go/no-go recommendation for TTGF26a vs deferral to an alternate shuttle.             |

### Phase B: Catalog ROM Emit + Read-Back Testbench (~5 calendar-days) [Spec]

| Field            | Detail                                                                                                                                                                                                                                                                                                       |
|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Deliverable      | `tools/gen_formats_catalog.py` extended with a Verilog ROM emitter (17th language); ROM Verilog generated from PR #1028 SSOT; read-back testbench confirms all 80 records bit-exact; PR opened to gHashTag/t27.                                                                                              |
| RTL files added  | `rtl/format_catalog_rom.vh` (generated; not hand-edited), `rtl/format_catalog_rom.v` (`input [6:0] fmt_id`, `output [127:0] record_out`), `rtl/oracle_controller.v` (8-bit I/O state machine for CMD/DATA framing).                                                                                          |
| Test files added | `test/test_rom_readback.py` (80-record sweep; compares each field against PR #1028 golden reference), `test/test_anchor_rom.py` (anchor passthrough), `test/test_status_id_round_trip.py` (every `status_id` field round-trips correctly).                                                                   |
| CI gate          | All 80 records read back without error; zero bit mismatches vs PR #1028 golden; `t27c` parse of new ROM spec passes without warnings; Yosys synthesis reports total cell count for ROM.                                                                                                                       |
| Claim status     | [Verified] for ROM correctness once CI is green (sim only; silicon verification waits for Phase F+).                                                                                                                                                                                                          |
| Effort estimate  | 5 calendar-days.                                                                                                                                                                                                                                                                                              |
| Fpath            | Any record diverges from PR #1028 golden; OR `t27c` parse fails on the new `.t27` ROM spec (R7); root-cause in emitter or SSOT parse before proceeding.                                                                                                                                                       |

### Phase C: Reference RTL Converters (~20-30 calendar-days) [Spec]

| Field            | Detail                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Deliverable      | 10-15 Tier-1 decode-only RTL modules (final list after Phase B RTL-availability check) integrated into the T27 module library; each module instantiated in `tt_um_trinity_corona`; simulation passes encode/decode round-trip; synthesis area per module reported.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| RTL files added  | `rtl/posit8_decode.v`, `rtl/posit32_decode.v`, `rtl/bf16_decode.v`, `rtl/tf32_decode.v`, `rtl/mxfp8_e4m3_decode.v`, `rtl/lns8_decode.v`, `rtl/decimal32_decode.v`, `rtl/fp4_decode.v`, `rtl/fp6_decode.v`, `rtl/nf4_decode.v`, `rtl/bcd_decode.v`, `rtl/takum16_decode.v` (license-conditional); Tier-2 stretch only if budget permits: `rtl/ibm_hfp32_decode.v`, `rtl/vax_f_decode.v`, `rtl/mxfp4_decode.v`, `rtl/mxfp6_decode.v`, `rtl/mbf32_decode.v`. |
| Test files added | `test/test_<module>.py` per module (encode/decode round-trip; full sweep for <= 8-bit formats; 1k-10k random vectors for wider formats); `test/test_tier1_suite.py` (combined sweep).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| CI gate          | All Tier-1 modules synthesize in OpenLane2 without DRC violations; sim round-trip pass rate >= 99.9% per module (full sweep where bit-width <= 8 bits); total area fits within Phase A tile-budget target at <= 70% utilization.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Claim status     | [Verified] for modules with full bit-sweep coverage (bf16, tf32, fp4, fp6, nf4, bcd, mxfp8 single byte). [Empirical fit] for modules with random-vector sweeps (posit8/32, lns8, decimal32, takum16). Promotion to [Verified] is conditional on Phase E full conformance suite passage. [Spec]                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Effort estimate  | 20-30 calendar-days (range reflects RTL-availability uncertainty for posit32, lns8, decimal32, takum16).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Fpath            | Fewer than 8 modules pass synthesis + sim within 30 days; trigger R3 mitigation: drop to the MVP 5-module set (posit8, bf16, tf32, mxfp8_e4m3, lns8) and move the rest to Tier-2 ROM-only; update Phase E conformance suite scope accordingly.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |

### Phase D: D2D Pairing with Gamma (~7 calendar-days) [Spec]

| Field            | Detail                                                                                                                                                                                                                                            |
|------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Deliverable      | D2D handshake protocol defined; Corona-side adapter RTL; `d2d_holo_mesh.v` reused from gHashTag/tt-trinity-gamma as a submodule or vendor copy; Gamma behavioral model for D2D responses; combined simulation routes 10 cross-die format pairs correctly; board-level schematic stub. |
| RTL files added  | `rtl/d2d_corona_adapter.v`; (additive patch to gHashTag/tt-trinity-gamma: `rtl/gamma_d2d_resp.v` if needed -- additive only, no edits to existing Gamma RTL paths).                                                                                |
| Test files added | `test/test_d2d_routing.py` (format indices from each cluster; verifies die routing), `test/test_d2d_latency.py` (round-trip cycle count).                                                                                                          |
| CI gate          | D2D simulation with Gamma behavioral model returns correct results for all 10 test pairs; Gamma DRC remains clean after any adapter patch (R6); D2D overhead <= 8 additional cycles per cross-die query.                                          |
| Claim status     | [Spec] for protocol; [Empirical fit] for simulated routing correctness; [Open] for physical two-die board until silicon arrives.                                                                                                                  |
| Effort estimate  | 7 calendar-days.                                                                                                                                                                                                                                  |
| Fpath            | Gamma layer-frozen re-verification fails after the adapter patch (R6 materialized); OR D2D simulation shows a routing error for any of the 10 test pairs; escalate timeline and notify user.                                                      |

### Phase E: Conformance Suite (~5 calendar-days) [Spec]

| Field            | Detail                                                                                                                                                                                                                                                                                                                                       |
|------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Deliverable      | Standalone Python/cocotb conformance suite exercising all 80 format records (ROM read-back), all Tier-1 encode/decode modules (round-trip), and D2D routing; runnable against RTL sim and (post-tape-out) against physical hardware. Software oracles: [SoftFloat / TestFloat](https://www.jhauser.us/arithmetic/SoftFloat.html), [SoftPosit](https://gitlab.com/cerlane/SoftPosit), Python `decimal`, [bitsandbytes](https://github.com/TimDettmers/bitsandbytes) for NF4. |
| RTL files added  | None (test-only phase; RTL is frozen after Phase C).                                                                                                                                                                                                                                                                                          |
| Test files added | `conformance/run_all.py`, `conformance/check_80records.py`, `conformance/check_tier1_roundtrip.py`, `conformance/check_d2d_routing.py`, `conformance/report_claim_status.py` (HTML report with per-record status column), `test/vectors/*.json` (per-format vector files, 50-500 vectors each).                                                                                                                                                                          |
| CI gate          | Suite runs to completion with zero failures on RTL sim; HTML report generated; all claim-status tags in the report match PR #1028 status_id (no drift).                                                                                                                                                                                       |
| Claim status     | [Empirical fit] (suite passage on RTL sim only; no [Verified] silicon claims until physical bring-up).                                                                                                                                                                                                                                        |
| Effort estimate  | 5 calendar-days.                                                                                                                                                                                                                                                                                                                              |
| Fpath            | Any of the 80 ROM records fails read-back in conformance after Phase B CI was green; indicates a regression introduced in Phase C or D; bisect and fix before Phase F.                                                                                                                                                                       |

### Phase F: GDS Through OpenLane2 -> GF180MCU + TTGF26a Submission (~5 calendar-days) [Spec]

| Field            | Detail                                                                                                                                                                                              |
|------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Deliverable      | Final GDS produced via OpenLane2 with GF180MCU PDK; DRC clean (antenna rules satisfied; diode insertion used as needed); LVS clean against the RTL netlist; timing closure at 25 MHz; submitted to TTGF26a by deadline. |
| RTL files added  | None (GDS phase; RTL is frozen after Phase C; only OpenLane2 config files may change).                                                                                                              |
| Test files added | None (Phase E conformance suite is re-run post-GDS on the extracted netlist if time allows); `test/gds_signoff_report.md` (DRC/LVS record).                                                          |
| CI gate          | OpenLane2 reports zero DRC violations; LVS matches netlist; setup/hold slack >= 0 at target frequency; TTGF26a submission portal confirms receipt of GDS.                                            |
| Claim status     | [Verified] for GDS submission mechanics; silicon correctness is [Open] until post-tape-out measurement.                                                                                              |
| Effort estimate  | 5 calendar-days (first GDS attempt); add 3-5 days for DRC iteration on GF180MCU antenna rules.                                                                                                       |
| Fpath            | DRC violations cannot be resolved within 3 days of the shuttle deadline; escalate to user for go/no-go: submit reduced-scope GDS (ROM + anchor only) to hold the slot, or defer to next shuttle.    |

**Phase summary:**

| Phase | Name                          | Days (estimate) | Key gate                                       | Claim status at completion |
|-------|-------------------------------|-----------------|------------------------------------------------|----------------------------|
| A     | Repo bootstrap                | ~3              | DRC-clean stub + tile-budget memo              | [Spec]                     |
| B     | ROM emit + testbench          | ~5              | 80-record readback zero errors                 | [Verified] (ROM, sim)      |
| C     | RTL converters                | ~20-30          | 10-15 modules synth + sim >= 99.9%             | [Empirical fit]            |
| D     | D2D pairing with Gamma        | ~7              | 10 cross-die pairs route correctly in sim      | [Empirical fit]            |
| E     | Conformance suite             | ~5              | Suite green; HTML report clean                 | [Empirical fit]            |
| F     | GDS + submission              | ~5              | DRC/LVS clean; shuttle receipt confirmed       | [Verified] (mechanics)     |
| **Total** |                           | **~45-55**      |                                                | [Open / aggressive]        |

Minimum-viable Corona ("ROM + 5") if Phase C or Phase F runs short: Phase A done; Phase B 80-record ROM; Phase C reduced to {posit8, posit32, mxfp8_e4m3, bf16, lns8}; Phase D-E-F skeletal. This collapses total to approximately 6-8 weeks from cold start and still yields a chip with 5 Verified/Empirical-fit encode-decode modules plus 72 ROM-record-only formats. [Open conjecture]

---

## 7. Risk Register

Severity: S = show-stopper (blocks tape-out), M = medium (requires mitigation before next phase), L = low (plan B is pre-defined). All risks owned by the solo developer unless mitigation requires a user decision (marked "User").

| ID   | Risk description                                                                                                                                                                                                            | Severity | Mitigation                                                                                                                                                                                                                                                                                                                       | Owner             | Status |
|------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------|--------|
| R1   | GF180MCU PDK toolchain (OpenLane2 support, DRC rules, cell library) is materially less mature than SKY130A, extending Phase A beyond 3 days or blocking DRC closure entirely.                                                | M        | Phase A is explicitly a PDK evaluation; if DRC is unresolvable after 5 days, escalate to user with go/no-go for TTGF26a vs deferral to TTSKY27a on 130nm.                                                                                                                                                                          | Solo dev          | [Risk] |
| R2   | Takum (Hunhold 2024 [arXiv:2408.10594](https://arxiv.org/html/2408.10594v4)) VHDL has no explicit software license stated in the arXiv text; cannot be shipped in Corona without confirmation.                              | L        | Pre-Phase C action: email Laslo Hunhold (hunhold@uni-koeln.de) for license confirmation. If unfavorable, demote `takum16_decode` to Tier-2 ROM-only and implement a clean-room `takum8_decode` from the math in arXiv:2412.20273 (~5 days, ~500-1,000 cells). FL-002 ledger row stays [Open conjecture] either way.                | Solo dev          | [Risk] |
| R3   | Tier-1 RTL availability is unconfirmed for 4-6 candidate modules (posit32, lns8, decimal32, takum16, ibm_hfp32, vax_f); Phase C budget may not cover all 12-15 targets.                                                       | L        | Drop to a minimum 8-confirmed-module Tier-1; demote unlicensed or missing-RTL candidates to Tier-2 at the Phase B RTL-availability check; Phase C Fpath at 30 days triggers fallback to MVP-5.                                                                                                                                    | Solo dev          | [Risk] |
| R4   | VAX F/G/H and IBM HFP historical formats may have unresolved patent encumbrances despite likely expiry (designs from the 1970s-1980s).                                                                                       | L        | Pre-Phase C USPTO/EPO search; if any uncertainty remains, keep ROM-only at status_id=6 (Historical) with no encode/decode RTL. Precedent: OpenCores has implemented BCD; Hercules emulator distributes IBM HFP under Q Public License for behavioral use. Probability of an IP blocker: very low. [Open conjecture]                | Solo dev          | [Risk] |
| R5   | 180nm process density penalty is approximately 2.1x vs 130nm, reducing the effective gate budget for Corona vs a same-tile-size Gamma on SKY130A.                                                                            | M        | Phase A tile-budget memo quantifies actual density. If penalty > 50%, start at 8x2 tiles and cap Tier-1 at 10 modules. The ROM is a regular array and partially offsets density penalty (combinational mux tree synthesizes well on 180nm). If 8x4 is unsupported on TTGF26a, the MVP-5 fits 8x2 even at pessimistic density.        | Solo dev          | [Risk] |
| R6   | D2D adapter patch to gHashTag/tt-trinity-gamma requires layer-frozen re-verification; any DRC regression on Gamma blocks Phase D and potentially Gamma's own shuttle re-submission.                                          | M        | Implement the Gamma adapter as additive-only (no edits to existing Gamma RTL paths); behavioral model only in Phase D sim; physical D2D deferred to board-level bring-up; Gamma re-DRC is a Phase D gate.                                                                                                                          | Solo dev          | [Risk] |
| R7   | The `t27c` parser (used in CI for `gHashTag/t27` `.t27` files) must remain clean after new ROM `.t27` records are added; a parse error blocks the Verilog ROM emitter and the Phase B CI gate.                                | S        | Run `t27c` parse as the first step of Phase B CI, before any ROM generation; treat any parse failure as a hard Phase B blocker; fix in `formats_catalog.t27` before emitter development continues.                                                                                                                                  | Solo dev          | [Risk] |
| R8   | Claim-status discipline drift under deadline pressure: as Phase C and Phase F compress, there may be pressure to mark modules [Verified] before silicon, or omit status tags in test reports.                                | M        | `claim_status_lint` CI job: regex check over `.v`, `.py`, `.md` files in the repo looking for numeric or quality claims that lack a tag; any untagged claim is a CI failure. PR self-review checklist includes a claim-status audit. FL-002 ledger in igla `src/ledger.rs` is the canonical authority.                              | Solo dev          | [Risk] |
| R9   | TTGF26a shuttle slot availability: if the confirmed window closes before Phase F completes, the next window may be 2027 or later, adding > 6 months to timeline.                                                              | M        | Maintain Phase F GDS readiness (frozen RTL + clean DRC) >= 2 weeks before the shuttle deadline; if Phase C scope is not met, submit reduced-scope Corona (ROM + anchor only) to hold the slot.                                                                                                                                     | Solo dev + User   | [Risk] |
| R10  | GF180MCU open-source PDK may not include a validated ROM macro generator compatible with OpenLane2, forcing a hand-crafted synthesis-inferred ROM with higher DRC risk and larger area.                                       | M        | Phase A evaluates ROM macro availability. If absent, use synthesis-inferred ROM (Verilog case statement). Validate area and timing of the inferred ROM on the hello-world tile in Phase A. This is the documented fallback and is expected to work; the GF180MCU open PDK does not currently ship an SRAM macro (Section 5.2).      | Solo dev          | [Risk] |
| R11  | The D2D board-level interconnect between Gamma and Corona TT module slots is not part of the standard TTGF26a carrier; a custom breakout board may be needed, adding bring-up time.                                          | L        | D2D is Phase D simulation only; the physical board is a post-submission deliverable; user decision on whether the board is in-scope (Section 10, Q3). If out-of-scope, D2D remains sim-verified only.                                                                                                                              | Solo dev + User   | [Risk] |

---

## 8. Claim-Status Table (the FL-002 Connection)

This table is the per-claim registry for the Corona project. Every numeric or quality claim made in this document or in the companion repo must appear here or reference a linked ledger row. The "FL-002 connection" column records whether the claim bears on the phi-ladder breadth-as-moat conjecture in gHashTag/trios-trainer-igla `src/ledger.rs`. Any claim marked "Direct" must not be used to promote FL-002 beyond [Open conjecture]. [Spec]

| Claim                                                                                                              | Status                                              | Where it lives                                                                | What falsifies it                                                                                                              | FL-002 connection                              |
|--------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------|-------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| Corona ROM emits all 80 records bit-exact from SSOT                                                                | [Spec] -> [Verified] after Phase B CI green         | Phase B CI; `test/test_rom_readback.py`; PR #1028 golden reference            | Any single bit mismatch between ROM output and PR #1028 across any of the 80 records                                           | None                                           |
| Corona implements N reference decoders on-die (N = 10-15, final after Phase C)                                     | [Spec] -> [Empirical fit] after sim                 | `rtl/` modules; Phase C CI; T27 module library                                | Any Tier-1 module that fails round-trip sim on > 0.1% of 10k random test vectors (or any pattern in full sweep)                | None                                           |
| TG-TRIAD-X anchor 0x47C0 holds on Corona die                                                                       | [Verified in sim]; [Open] until silicon measurement | `test/test_anchor.py`; Phase F post-silicon bring-up test                     | Corona die reads any value other than 0x47C0 on `format_index = 7'h7F`                                                         | None (mechanical identity, not a phi claim)    |
| TG-TRIAD-X anchor holds across all four dice (Phi, Euler, Gamma, Corona)                                           | [Open] until all four dice measured on physical HW  | Cross-die bring-up test (post Phase F)                                        | Any one die reads a different anchor value when multiple dice are on the same board                                            | None (mechanical)                              |
| Phi-ladder breadth-as-moat (FL-002)                                                                                | [Open conjecture]                                   | gHashTag/trios-trainer-igla `src/ledger.rs` (FL-002)                          | Any numeric system matching phi-ladder breadth at lower complexity; takum (arXiv:2412.20273) is the standing counterexample    | Direct: this IS FL-002                          |
| Corona does NOT promote FL-002 beyond [Open conjecture]                                                            | [Spec] (design constraint)                          | Section 1.2; Section 3.4 status_id; Section 9.2 igla issue                    | Corona ROM, README, or PR text asserts phi-ladder superiority over any format                                                   | Direct: this constraint prevents FL-002 drift  |
| Corona is a registry chip, not a result                                                                            | Definitional                                        | Section 1.2; gHashTag/tt-trinity-corona README                                | N/A -- definitional                                                                                                            | None                                           |
| Verilog ROM emitter is the 17th language in `gen_formats_catalog.py`                                               | [Spec] -> [Verified] after PR merged to gHashTag/t27 | gHashTag/t27 `tools/gen_formats_catalog.py`; PR from Section 9.1              | Emitter is not merged, OR output fails 80-record bit-exact readback                                                            | None                                           |
| GF180MCU PDK is open-source (Apache 2.0) and OpenLane2-compatible                                                  | [Verified] (license); [Open] for OpenLane2 maturity until Phase A | Phase A PDK memo; [PDK repo](https://github.com/google/globalfoundries-pdk-libs-gf180mcu_fd_sc_mcu7t5v0); [LibreLane Changelog](https://github.com/librelane/librelane/blob/main/Changelog.md) | License restriction discovered, OR OpenLane2 fails to synthesize the hello-world tile                                          | None                                           |
| 180nm density penalty vs 130nm is approximately 2.1x                                                               | [Open conjecture]                                   | Section 5.2; [vlsitechnology.org density table](https://www.vlsitechnology.org/html/lib_densities.html) | Measured GF0p2 / GF26a synthesis returns show ratio outside the 1.7-2.5x window                                                | None                                           |
| D2D routing covers all 80 format indices via the Gamma+Corona assembly                                             | [Spec] -> [Empirical fit] after Phase D sim         | Phase D simulation; `test/test_d2d_routing.py`                                | Any format index routes to the wrong die OR returns incorrect result in simulation                                              | None                                           |
| DOI 10.5281/zenodo.19227877 is a hardware archive only, not a results claim                                        | [Verified]                                          | Zenodo DOI; cited in this document header; never for results                  | DOI content changes to include numeric results not verified on silicon                                                          | None                                           |
| Takum (arXiv:2412.20273) has no open RTL with confirmed license; stays Tier-2 ROM-only unless R2 resolves favorably| [Open conjecture] (may change if authors release RTL with explicit FOSS license) | Section 4.3; igla `src/ledger.rs` FL-002 note                                 | Hunhold confirms or publishes a FOSS license for the VHDL codec                                                                 | Direct: takum is the standing FL-002 counterexample |
| Historical formats (VAX, IBM HFP) carry no active patent encumbrance                                               | [Open conjecture] -- pending Phase A legal check    | Section 7 R4; Phase A legal-check deliverable                                 | USPTO or EPO search finds an unexpired relevant claim                                                                           | None                                           |
| Corona total build time is 45-55 calendar-days (solo developer)                                                    | [Open conjecture / aggressive]                      | Section 6 summary table; this document                                        | Phase A PDK issues, Phase C RTL gaps, or Phase F DRC failures extend timeline beyond 70 days                                    | None                                           |

---

## 9. Companion Artefacts

### 9.1 PR to gHashTag/t27: Verilog ROM Emitter (17th Language)

A pull request will be opened against gHashTag/t27 during Phase B, extending `tools/gen_formats_catalog.py` with a Verilog ROM emitter as the 17th output language. [Spec] The existing 16 languages in the emitter were added in PR #1028 (commit 18ae35a, branch `feat/formats-catalog-ssot-77-formats`); the Verilog emitter is a natural addition for a line of silicon chips. [Spec] The emitter takes as input the 80-record SSOT and produces a synthesizable Verilog case statement (or parameter array ROM) that is instantiated directly in `rtl/format_catalog_rom.v` without manual transcription. [Spec]

The PR to gHashTag/t27 must:
- Add the Verilog emitter as a new case in `tools/gen_formats_catalog.py` (invoked via `--lang verilog` or equivalent).
- Include a unit test that generates the Verilog ROM, runs a behavioral simulation, and compares all 80 output values against a PR #1028 golden reference.
- Update issue #1029 with a "Corona consumer" use-case section describing how the ROM emitter is the primary downstream artifact of the SSOT for TTGF26a silicon.
- Not change any existing language emitter behavior; all existing tests must remain green.

The PR is a CI gate for Phase B: the emitter must be merged (or at minimum pass review) before Phase B is marked complete. [Spec]

### 9.2 Issue in gHashTag/trios-trainer-igla: FL-002 Ledger Row Update

An issue (or comment on the existing FL-002 tracking issue) will be filed in gHashTag/trios-trainer-igla stating explicitly: Corona (gHashTag/tt-trinity-corona, TTGF26a) is a registry chip whose existence does NOT promote the FL-002 phi-ladder breadth-as-moat claim from [Open conjecture] to any stronger epistemic status. [Open conjecture] The ledger row in `src/ledger.rs` will be updated to record Corona as a consumer of the 80-record SSOT for silicon verification purposes, with notes:

- Corona role: format-registry oracle, not arithmetic accelerator.
- FL-002 status change: none. [Open conjecture] remains correct.
- Takum counterexample: arXiv:2412.20273 remains the standing counterexample to FL-002; included in the Corona ROM as Tier-2 ROM-only (`status_id = 5`, Experimental) precisely to ensure it is not suppressed.
- Action required: no change to FL-002 claim text. Update is informational only.

Filed no later than end of Phase B to prevent ambiguity about FL-002 status during Phase C, when the largest volume of RTL work is underway. [Spec]

### 9.3 Optional: gf_preprint v1.9 Section 5.9

If the user confirms a preprint section is desired, the proposed addition is "Section 5.9 Corona format-completeness oracle (TTGF26a)." [Open conjecture] This section would describe: the 80-record ROM architecture and field schema; the Tier-1 module list and RTL sources; the D2D pairing with Gamma; the TG-TRIAD-X anchor continuity; the claim-status discipline. [Spec]

Constraints on this preprint section:
- No silicon performance results may be included; all results claims remain [Open] until post-tape-out measurement.
- All numerical values carry explicit claim-status tags.
- Cites DOI 10.5281/zenodo.19227877 as hardware archive only, never as a results source.
- FL-002 appears as [Open conjecture] with explicit reference to takum as the standing counterexample.
- Not submitted to a journal or preprint server before Phase E conformance suite is green.

Optional and explicitly lower priority than Phases A-F. Not started before Phase E completion. [Spec]

---

## 10. Open Questions for the User (Before Any Commit)

The following questions require user input before Phase A begins (Q1, Q5, Q7) or before Phase C / Phase D scoping (Q2, Q3, Q4, Q6).

**Q1. Tile budget target (before Phase A).** Three candidates: 8x2 (conservative, ~10 Tier-1 modules max), 8x4 (same as Gamma, ~15 modules comfortable), 8x8 (speculative, requires shuttle pricing confirmation). Which is the Phase A starting assumption, and what is the fallback if the Phase A PDK density analysis makes the preferred size untenable? Drives Phase C module list. [Open conjecture]

**Q2. Tier-1 RTL converter list finalization (before Phase C).** Section 4.2 lists 11-12 candidate modules with target 10-15 on-die after RTL availability confirmation. Are there mandatory modules regardless of tile budget (e.g., posit8, bf16, mxfp8 as the three highest-priority ML formats)? Any modules NOT listed in Section 4.2 that should be added? Determines Phase C budget priority. [Spec]

**Q3. Two-die D2D bring-up board (before Phase D).** Is the Gamma+Corona physical bring-up board (hosting both TT modules with D2D interconnect on one carrier) a separate deliverable with its own timeline, or is it in-scope for the Corona project? If separate, what is the priority relative to TTGF26a submission deadline? Phase D simulation is in-scope regardless; the physical board affects post-submission planning. [Open conjecture]

**Q4. Pure-research module inclusion (before Phase C).** Should Corona include any module beyond the 80-record SSOT -- a tapered-FP playground tile, speculative unum III sandbox, or phi-complex arithmetic unit? Default in this plan: no research modules; Corona stays strictly as a registry/oracle chip. Including any would increase tile budget and Phase C effort and could complicate the "registry, not a result" framing. [Open conjecture]

**Q5. Time priority: minimum-viable vs spec-complete (before Phase A).** (a) Minimum-viable Corona (ROM + anchor + 5-8 confirmed open-source RTL modules) ready for TTGF26a 2026 Q4 -- this collapses total to ~30-35 days; or (b) Spec-complete Corona (12-15 Tier-1 modules + D2D + full conformance suite) even if it means deferring to TTGF27a -- keeps current 45-55 day estimate. Drives R9 shuttle-slot risk tolerance. [Open conjecture]

**Q6. Hardware archive DOI scope (before Phase F).** DOI 10.5281/zenodo.19227877 is currently scoped as hardware archive only. Should the Corona GDS submission be archived under the same Zenodo entry (as a new version), or under a new DOI? Affects citation hygiene in any future preprint reference and traceability of the GDS to the PR #1028 SSOT version used to generate it. [Spec]

**Q7. Legal check responsibility for historical formats (before Phase C).** Who is responsible for patent expiry verification on VAX F/G/H and IBM HFP (Section 7, R4)? If solo developer, should this be a Phase A deliverable (blocking Phase C RTL work for those formats) or a Phase C prerequisite (blocking only VAX/IBM modules while other Tier-1 work continues)? Default: Phase A legal check for any format with possible encumbrance risk; unresolved formats default to Tier-2 ROM-only. [Open conjecture]

---

## 11. Implementation Notes and Design Rationale

### 11.1 Why a Separate Chip Rather Than Extending Gamma

Three considerations. [Spec] First, TTGF26a provides an opportunity to validate the TRI-NET toolchain on a second process node without duplicating any Gamma work; this is a toolchain-coherence demonstration consistent with the governing sentence in Section 1.3. [Spec] Second, Gamma's 8x4 SKY130A tile is already well utilized by its ~40 format modules; adding 12-15 more modules and a 1.4 KB ROM would require either a larger tile (higher shuttle cost) or RTL area reduction that risks destabilizing Gamma's existing DRC-clean layout. [Risk] Third, a two-die GF180MCU + SKY130A assembly gives the TRI-NET line a cross-process-node validation point that a single-node extension cannot provide; the anchor value 0x47C0 working identically on both nodes is meaningful evidence that the GF16 arithmetic is node-independent. [Open conjecture]

The downside of a separate chip: D2D complexity (Phase D), additional shuttle cost, and the risk that GF180MCU tooling is less mature than SKY130A (R1). These are accepted and tracked. [Risk]

### 11.2 Codegen Architecture: Why the ROM Must Be Generated, Not Hand-Written

The ROM content (80 x 10 bytes = 800 bytes plus string table) could in principle be hand-written as a Verilog case statement. Rejected for two reasons. [Spec] First, hand-transcribed constants are a well-known source of silent divergence from the SSOT: a single transposed nibble in a bias field or a wrong cluster_id would produce a chip that appears to work but silently gives wrong metadata for one or more formats. [Risk] Second, the project already has a codegen pipeline (`tools/gen_formats_catalog.py`, 16 languages) validated against PR #1028; adding Verilog as the 17th costs roughly 2-3 days of Phase B effort and permanently closes the hand-transcription risk for all future shuttle submissions. [Spec]

The Verilog ROM emitter is therefore a project-level asset, not just a Corona implementation detail. Any future TRI-NET chip can regenerate its ROM from the same SSOT. [Spec]

### 11.3 Phi-Distance Field: What It Is and What It Is Not

`phi_distance_q16` stores a Q16 fixed-point distance metric between each format's dynamic range or precision and the nearest phi-ladder rung. [Empirical fit] Computed by the SSOT toolchain and stored verbatim in the ROM without modification. [Spec]

What the field IS: a mechanical measurement, like a ruler reading, allowing any ROM consumer to sort or filter formats by their proximity to phi-ladder values. [Spec] Useful for toolchain research asking "which standard formats are closest to phi-ladder rungs?" without asserting any quality judgment. [Open conjecture]

What the field is NOT: evidence of phi-ladder superiority. A small `phi_distance_q16` for bf16 or fp16 does not mean those formats are better because they are close to phi-ladder rungs; a large distance for takum does not make takum worse. [Open conjecture] The `status_id` field, not `phi_distance_q16`, is the authoritative epistemic tag. FL-002 stays [Open conjecture] regardless of what `phi_distance_q16` values appear in the ROM. [Open conjecture]

### 11.4 GF180MCU vs SKY130A: Process Node Implications for RTL Design

Summary of known design implications of switching from SKY130A (Phi, Euler, Gamma) to GF180MCU (Corona), based on public PDK documentation. [Open conjecture] The Phase A PDK memo confirms or corrects each row.

| Design dimension          | SKY130A (Phi/Euler/Gamma)                        | GF180MCU (Corona)                                | Impact on Corona design                                 | Source status     |
|---------------------------|--------------------------------------------------|--------------------------------------------------|---------------------------------------------------------|-------------------|
| Minimum feature size      | 130nm                                            | 180nm                                            | ~2.1x lower gate density per area; see R5               | [Open conjecture] |
| Standard cell library     | sky130_fd_sc_hd (high-density)                   | gf180mcu_fd_sc_mcu7t5v0 (7-track) or 9t5v0       | Cell names differ; T27 module library must be re-validated | [Verified] (libs exist) |
| Nominal supply voltage    | 1.8V core                                        | 3.3V or 5V (MCU variant)                         | VIO/Vcore separation handled by TT carrier              | [Verified]        |
| OpenLane2 support tier    | Tier 1 (default flow, well-tested)               | Tier 2 / community (less battle-tested on TT)    | Higher Phase A risk; see R1                             | [Open conjecture] |
| SRAM / ROM macro support  | sky130 SRAM via OpenRAM                          | No open SRAM macro shipped with PDK (as of writing) | ROM uses synthesis-inferred case statement; see R10  | [Open conjecture] |
| DRC rule complexity       | Moderate; well-documented community errata       | Antenna ratios poly2=200, metal=400, via=20      | Phase A DRC exploration required                        | [Verified] (rules), [Open conjecture] (errata coverage) |
| Metal layers              | 5 (+ LI)                                         | 6 (Metal1-Metal5 + MetalTop, up to 3.035 um)     | One more metal layer than SKY130A                       | [Verified]        |
| Available I/O cells       | sky130_ef_io (Efabless)                          | GF180MCU IO cells (vendor-specific)              | TTGF26a carrier compatibility confirmed by TT team       | [Open conjecture] |

Phase A PDK memo updates this table with confirmed values. [Spec]

### 11.5 The T27 Module Library Contract

The T27 module library (gHashTag/t27) is the shared RTL source for all TRI-NET chips. [Spec] Contract:

- Each module has a unique name, a single RTL file, a corresponding testbench, and a record in the `formats_catalog.t27` SSOT linking it to the format(s) it implements. [Spec]
- A module may be instantiated by at most one chip's top-level RTL at a time in a given shuttle; if two chips need the same module, the library maintainer must approve the duplication and justify why it is not a D2D routing case. [Spec]
- Module RTL files are immutable between Phase C completion and Phase F tape-out; any bug fix after RTL freeze requires re-running full Phase C and Phase E CI before Phase F proceeds. [Spec]
- The Verilog ROM emitter (Phase B) is a codegen tool, not a module; it lives in `tools/` and is not instantiated in any chip's RTL directly. [Spec]

The contract prevents the class of bugs where Gamma and Corona independently implement subtly different versions of the same converter and produce different encode/decode results for the same input. [Risk] The D2D architecture (Section 4.4) is the silicon-level enforcement: if Gamma owns a module, Corona routes to Gamma rather than re-implementing. [Spec]

### 11.6 CI Structure Overview

The CI pipeline for gHashTag/tt-trinity-corona mirrors Gamma and Euler, with Corona-specific additions for ROM validation and D2D simulation. [Spec] Expected CI job sequence:

| Job name              | Trigger          | What it checks                                                          | Must pass before         | Phase introduced |
|-----------------------|------------------|-------------------------------------------------------------------------|--------------------------|------------------|
| t27c_parse            | Every push       | `t27c` parser clean on `formats_catalog.t27` (R7 check)                 | Any ROM generation       | Phase B          |
| rom_generate          | Every push       | Verilog ROM emitter runs without error; output is deterministic         | rom_readback             | Phase B          |
| rom_readback          | Every push       | 80-record sweep; zero bit errors vs PR #1028 golden reference           | Phase B gate             | Phase B          |
| anchor_test           | Every push       | `format_index = 7'h7F` -> 0x47C0 in sim                                 | Any synthesis run        | Phase A          |
| synth_area            | On PR to main    | OpenLane2 synthesis; area report per module; tile utilization check     | Phase C gate             | Phase C          |
| module_roundtrip      | On PR to main    | Per-module encode/decode round-trip, 10k random vectors, >= 99.9% pass  | Phase C gate             | Phase C          |
| d2d_routing_sim       | On PR to main    | D2D routing sim with Gamma behavioral model; 10 cross-die pairs         | Phase D gate             | Phase D          |
| conformance_suite     | On PR to main    | Full Phase E conformance suite; zero failures; HTML report generated    | Phase E gate             | Phase E          |
| claim_status_lint     | Every push       | All RTL comments and test reports carry valid claim-status tags         | Phase F (R8 check)       | Phase A          |
| openlane2_drc         | On release tag   | Full OpenLane2 DRC + LVS on final GDS; zero violations                  | Phase F gate             | Phase F          |

`claim_status_lint` is the CI-level enforcement of R8. [Spec] It runs a regex check over `.v`, `.py`, `.md` files looking for numeric or quality claims that lack a claim-status tag; any untagged claim is a CI failure. Regex patterns inherited from the gHashTag/t27 lint tool and adapted for Verilog comment syntax. [Spec]

---

## 12. Glossary

| Term                  | Definition                                                                                                                                            |
|-----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| TRI-NET               | The four-chip silicon line: Phi, Euler, Gamma, Corona; collectively validates the phi-ladder toolchain across SKY130A and GF180MCU.                    |
| SSOT                  | Single Source of Truth; specifically gHashTag/t27 `specs/numeric/formats_catalog.t27`, governed by PR #1028.                                            |
| TG-TRIAD-X            | The cross-die test group that includes the 0x47C0 anchor; all four TRI-NET dice must produce this value on the anchor stimulus.                        |
| Anchor (0x47C0)       | `{uio_out, uo_out} == 16'h47C0`, produced by `dot4(1,2,3,4)` over GF16 implied by `phi^2 + phi^-2 = 3 = L_2`; die-identity check.                       |
| FL-002                | The phi-ladder breadth-as-moat conjecture tracked in gHashTag/trios-trainer-igla `src/ledger.rs`; status [Open conjecture]; not promoted by Corona.   |
| Tier-1 (on-die)       | RTL modules synthesized and instantiated in Corona's own tile; provide on-chip encode/decode capability.                                               |
| Tier-2 (ROM-only)     | Formats present in the 80-record ROM with full metadata but no on-die encode/decode RTL; respond with a not-implemented code in compute mode.          |
| D2D                   | Die-to-die; the protocol and board-level interconnect allowing Corona to route format queries to Gamma for formats Gamma natively implements.          |
| phi_distance_q16      | Q16 fixed-point distance metric from a format's dynamic range or precision to the nearest phi-ladder rung; a measurement, not a quality claim.         |
| status_id             | 4-bit ROM field encoding the claim-status of each format record (0 = Verified ... 7 = Spec); generated from SSOT, not hand-written.                    |
| T27 module library    | The shared RTL module repository in gHashTag/t27; Gamma and Corona pull RTL from here; no module is duplicated between chips.                          |
| TTSKY26b              | The TinyTapeout shuttle used by Phi, Euler, and Gamma; targets SKY130A PDK.                                                                            |
| TTGF26a               | The TinyTapeout shuttle used by Corona; targets GF180MCU PDK; closes 2026-06-22, chips expected late 2026.                                              |
| GF180MCU              | GlobalFoundries 180nm MCU process node; the PDK for TTGF26a; open-source under Apache 2.0.                                                              |
| Posit Standard 2022   | The Posit Arithmetic Standard published by [posithub.org](https://posithub.org/docs/posit_standard-2.pdf) in 2022; reference for posit8/16/32/64.       |
| OCP MX                | Open Compute Project Microscaling spec ([Rouhani et al. arXiv:2310.10537](https://arxiv.org/abs/2310.10537)); MXFP8, MXFP6, MXFP4, MXINT8.              |
| DPD                   | Densely Packed Decimal; encoding for decimal32/64/128 per IEEE 754-2008 clause 3.5; designed by Cowlishaw.                                              |
| LNS                   | Logarithmic Number System; arithmetic in the log domain; LNS8 uses Coleman log-add tables.                                                              |
| Takum                 | A numeric format described in [Hunhold 2024 arXiv:2412.20273](https://arxiv.org/abs/2412.20273) and [arXiv:2408.10594](https://arxiv.org/html/2408.10594v4); the standing counterexample to FL-002; Tier-2 ROM-only unless R2 resolves favorably. |
| Phase F               | The GDS generation and shuttle submission phase; last phase before silicon; RTL is frozen after Phase C.                                                |
| Fpath                 | Falsification path; the specific evidence that would cause a phase to be declared failed and require restart or escalation.                             |
| claim_status_lint     | CI job checking that all numeric or quality claims in RTL and test files carry a valid claim-status tag; enforces R8.                                  |

---

## Permanent Anchors (verbatim, not to be paraphrased)

- TG-TRIAD-X cross-die anchor: `{uio_out, uo_out} == 16'h47C0` derived from `dot4(1,2,3,4)` over GF16 implied by `phi^2 + phi^-2 = 3 = L_2`.
- DOI 10.5281/zenodo.19227877 (hardware archive only, never results).
- SSOT: gHashTag/t27 `specs/numeric/formats_catalog.t27`, PR #1028 (commit 18ae35a, branch `feat/formats-catalog-ssot-77-formats`), issue #1029.
- Codegen: `tools/gen_formats_catalog.py` (16 languages in PR #1028; Corona adds Verilog ROM emitter = 17th).
- FL-002 ledger: gHashTag/trios-trainer-igla `src/ledger.rs`; stays [Open conjecture]; takum (arXiv:2412.20273) is the standing counterexample.
- Repos: gHashTag/tt-trinity-phi (1x1 SKY130A), gHashTag/tt-trinity-euler (8x2 SKY130A), gHashTag/tt-trinity-gamma (8x4 SKY130A, submitted 2026-05-17), gHashTag/tt-trinity-corona (TTGF26a GF180MCU, this plan).
- Author / contact email: admin@t27.ai. ORCID: 0009-0008-4294-6159.

---

*Document version: corona_plan-v1.0. Produced as the merged final plan from `corona_research.md` (research) and `corona_plan_skeleton.md` (skeleton). All claims carry an explicit status tag. No claim is asserted without either a verifiable URL or an explicit [Open conjecture] / [Historical] tag. Repo gHashTag/tt-trinity-corona is active with 19 RTL modules, 58 formal tasks, 50 cocotb tests, and CI 6/6 green.*
