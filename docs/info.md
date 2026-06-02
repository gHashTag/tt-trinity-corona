<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

TRI-1 Corona is a read-only format conformance oracle for the TRI-NET chip line,
targeting the TTGF26a shuttle on the GlobalFoundries GF180MCU 180nm process.

The chip contains a ~800-byte ROM encoding all 80 numeric-format records from
the Single Source of Truth (SSOT) catalog in gHashTag/t27 (PR #1028). Each record
is 10 bytes (80 bits) and includes fields for sign bits, exponent width, mantissa
width, encoding kind, cluster ID, claim-status ID, phi-distance (Q16), and a
reference index. The ROM is generated mechanically by `tools/gen_rom.py`.

17 Tier-1 RTL decode modules convert on-die formats to IEEE 754 FP32 (or INT32),
covering 18 format families (FP8 E4M3 reuses the MXFP8 E4M3 decoder): BF16, TF32,
FP8 E5M2, FP8 E4M3, FP8 E4M3 FNUZ, MXFP8 E4M3, FP6 E3M2, FP6 E2M3, FP4 E2M1,
Posit8, LNS8, INT4, INT8, BCD, NF4, E8M0, MXINT8, and BitNet 1.58b. Aliased
format indices (e.g. NF4_BNB, FP6_E3M2_ML) route to the same shared decoders, for
22 on-die format indices in total.

A die-to-die (D2D) adapter on `uio[3:0]` (TX) and `uio[7:4]` (RX) routes
queries for Gamma-native formats (GF4-GF256, FP8, INT4/8, NF4, Posit16, BitNet)
to the Gamma die when both chips are present on a shared bring-up board.

The TG-TRIAD-X cross-die anchor (`{uio_out, uo_out} == 16'h47C0`, derived from
`dot4(1,2,3,4)` over GF16) is produced when `format_index = 7'h7F` is asserted,
serving as a die-identity sanity check shared across all four TRI-NET chips.

## How to test

The chip uses Protocol v2, a two-byte CMD serial protocol on the TinyTapeout pins:

- **CMD1** (`ui_in[7]=0`): `ui_in[6:0]` selects a format index (0-79) or the
  anchor probe (`7'h7F`).
- **CMD2**: `ui_in[3:0]` = byte count (0 = ROM readback, 1-4 = data bytes; values >4 clamped to 4).
- **DATA**: exactly `byte_count` cycles of raw 8-bit data on `ui_in[7:0]`.
  All 256 byte values are valid (no reserved mode bits).
- **STATUS**: auto-entered after the last data byte; result bytes stream on
  `uo_out[7:0]`, one per clock cycle.

**Anchor test (quickest check):**
1. Assert `ui_in = 8'b0_1111111` (CMD1, `format_index = 7'h7F`).
2. Read `{uio_out, uo_out}` -- expect `16'h47C0` combinationally (same cycle).

**Tier-1 decode (example: 8-bit format like posit8):**
1. CMD1: `ui_in = {1'b0, fmt_id[6:0]}` (e.g., `7'd31` for posit8).
2. CMD2: `ui_in = 8'h01` (one data byte).
3. DATA: `ui_in = raw_byte` (any value 0x00-0xFF).
4. Read 4 result bytes from `uo_out` over 4 clock cycles (FP32, LSB first).

**ROM record read-back:**
1. CMD1: select format index.
2. CMD2: `ui_in = 8'h00` (zero data bytes).
3. Read 10 bytes from `uo_out` over successive clock cycles.

The cocotb testbench suite in `test/` provides automated verification including
exhaustive sweeps for all sub-8-bit and 8-bit format decoders.

## Timing

Decode latency is fixed by Protocol v2 and the input byte count (deterministic;
confirmed on silicon). From CMD1, the result streams over 4 STATUS cycles:

| Input width | Formats | First result byte | Full 32-bit result |
| --- | --- | ---: | ---: |
| 1 byte | most (fp8, posit8, int, bcd, ...) | 4 cycles | 7 cycles |
| 2 bytes | BF16 | 5 cycles | 8 cycles |
| 3 bytes | TF32 | 6 cycles | 9 cycles |

The anchor probe responds combinationally (same cycle). Nominal clock is 25 MHz;
the maximum clock frequency (Fmax) and critical-path decoder will be measured
post-silicon by sweeping the demo-board clock (`post_silicon/characterize_timing.py`):

| Metric | Value |
| --- | --- |
| Nominal clock | 25 MHz |
| Fmax (all decoders) | TBD (post-silicon) |
| Critical-path decoder | TBD (post-silicon) |

## External hardware

No external hardware is required for standalone operation. The chip is fully
functional using only the TinyTapeout demo board and a USB connection for
clock and I/O.

For **D2D operation** (routing queries to the companion Gamma die), the following
is needed:

- A second TinyTapeout module carrying the Gamma die (gHashTag/tt-trinity-gamma,
  TTSKY26b / SKY130A).
- 8 wires connecting Corona's `uio[7:0]` to Gamma's `uio[7:0]` on a shared
  breakout board (4 TX + 4 RX, directly connected or active buffered at 3.3V).
- Both modules clocked at the same frequency (25 MHz nominal).
