# Post-Silicon Test Plan -- TRI-1 Corona

## Timeline

- Chip expected: ~2026-10-01
- Delivery to participants: ~2026-11-15
- Packaging: chip-on-board (COB), bonded directly to PCB

## Hardware

- TinyTapeout RP2350 demoboard
- USB connection for clock and I/O
- No external hardware needed for standalone operation

## Test Suite (`test_corona.py`)

23 tests covering all verification paths (4 infrastructure + 17 decoder + 1 alias routing + 1 sentinel):

| Test | What it verifies | Cocotb equivalent |
|------|-----------------|-------------------|
| test_anchor | 0x47C0 anchor probe | test_anchor_basic |
| test_anchor_stability | Anchor stable over 10 reads | test_anchor_repeat |
| test_rom_self_index_sweep | All 80 ROM entries have correct self-index | test_full_rom_self_index_sweep |
| test_rom_out_of_range | Addresses 80-126 return zeros | test_rom_oob |
| test_decode_fp8_e5m2 | 8 FP8 E5M2 vectors (0, Inf, subnormal, 1.0) | test_fp8_e5m2_exhaustive |
| test_decode_bf16 | 6 BF16 vectors (0, 0.5, 1.0, 2.0, Inf) | test_bf16_key_values |
| test_decode_posit8 | 3 Posit8 vectors (0, 1, -1) | test_posit8_exhaustive |
| test_decode_int8 | 5 INT8 vectors (0, 1, 127, -1, -128) | test_int8_exhaustive |
| test_decode_tf32 | 5 TF32 vectors (0, -0, 1.0, 2.0, Inf) | test_tf32_key_values |
| test_decode_mxfp8_e4m3 | 6 MXFP8 E4M3 vectors (0, -0, 1.0, NaN) | test_mxfp8_e4m3_exhaustive |
| test_decode_lns8 | 5 LNS8 vectors (zero, key magnitudes) | test_lns8_exhaustive |
| test_decode_bcd | 5 BCD vectors (0, 1, 42, 99, 10) | test_bcd_exhaustive_valid |
| test_decode_fp4 | 5 FP4 E2M1 vectors (0, 1.0, -0, -1.0) | test_fp4_exhaustive |
| test_decode_nf4 | 5 NF4 QLoRA vectors (-1, 0, 1, key levels) | test_nf4_exhaustive |
| test_decode_fp6_e3m2 | 5 FP6 E3M2 vectors (0, -0, 0.5, max) | test_fp6_e3m2_exhaustive |
| test_decode_fp6_e2m3 | 5 FP6 E2M3 vectors (0, -0, 1.0, max) | test_fp6_e2m3_exhaustive |
| test_decode_e8m0 | 5 E8M0 vectors (2^-127, 1.0, 2^-126, NaN) | test_e8m0_exhaustive |
| test_decode_mxint8 | 6 MXINT8 vectors (0, 1/64, 1.0, NaN) | test_mxint8_exhaustive |
| test_decode_e4m3_fnuz | 5 E4M3 FNUZ vectors (0, NaN, 0.5, max) | test_fp8_e4m3_fnuz_exhaustive |
| test_decode_int4 | 5 INT4 vectors (0, 1, 7, -8, -1) | test_int4_exhaustive |
| test_decode_bitnet | 4 BitNet ternary vectors (0, +1, -1, NaN) | test_bitnet_exhaustive |
| test_alias_mux_routing | 5 alias fmt_ids route to correct decoder | (alias tests in cocotb) |
| test_not_implemented | Format 15 returns 0xFF + 'N' | test_not_implemented_sentinel |

## Decoder Coverage

All 17 unique hardware decoder paths tested:

| Decoder | fmt_id | Input bytes | Vectors |
|---------|--------|-------------|---------|
| BF16 | 8 | 2 | 6 |
| TF32 | 9 | 3 | 5 |
| FP8 E5M2 | 10 | 1 | 8 |
| E4M3 FNUZ | 14 | 1 | 5 |
| Posit8 | 31 | 1 | 3 |
| MXFP8 E4M3 | 39 | 1 | 6 |
| FP6 E3M2 | 40 | 1 | 5 |
| FP4 E2M1 | 41 | 1 | 5 |
| LNS8 | 42 | 1 | 5 |
| INT4 | 46 | 1 | 5 |
| INT8 | 47 | 1 | 5 |
| BCD | 53 | 1 | 5 |
| NF4 QLoRA | 70 | 1 | 5 |
| BitNet | 71 | 1 | 4 |
| FP6 E2M3 | 77 | 1 | 5 |
| E8M0 | 78 | 1 | 5 |
| MXINT8 | 79 | 1 | 6 |

All 5 alias decoders (FP8_E4M3=11, FP6_E3M2_ML=12, FP4_ML=13, E4M3_FNUZ_ALT=69, NF4_BNB=75) are tested via `test_alias_mux_routing` with one spot-check vector each, verifying the case statement routes to the correct shared hardware.

## Running

```python
# On RP2350 demoboard MicroPython REPL:
import test_corona
test_corona.run_all()
```

## Expected Output

```
PASS: anchor probe = 0x47C0
PASS: anchor stable over 10 reads
PASS: ROM self-index sweep (all 80 entries)
PASS: ROM out-of-range returns zeros
PASS: FP8 E5M2 decode (8 vectors)
PASS: BF16 decode (6 vectors)
PASS: Posit8 decode (3 vectors)
PASS: INT8 decode (5 vectors)
PASS: TF32 decode (5 vectors)
PASS: MXFP8 E4M3 decode (6 vectors)
PASS: LNS8 decode (5 vectors)
PASS: BCD decode (5 vectors)
PASS: FP4 E2M1 decode (5 vectors)
PASS: NF4 QLoRA decode (5 vectors)
PASS: FP6 E3M2 decode (5 vectors)
PASS: FP6 E2M3 decode (5 vectors)
PASS: E8M0 decode (5 vectors)
PASS: MXINT8 decode (6 vectors)
PASS: E4M3 FNUZ decode (5 vectors)
PASS: INT4 decode (5 vectors)
PASS: BitNet ternary decode (4 vectors)
PASS: alias mux routing (5 aliases)
PASS: not-implemented response (format 15 = GoldenFloat, no decoder)

========================================
Results: 23 passed, 0 failed, 23 total
ALL PASS
```

## Pass/Fail Criteria

- ALL 23 tests must pass for silicon validation
- Anchor test is the first check (confirms die identity + basic I/O)
- ROM sweep is the most comprehensive (validates all 80 records intact)
- Decoder tests confirm all 22 mux case entries (17 primary + 5 alias) are functional
- Any single failure indicates a silicon defect

## Exhaustive Sweeps

The test suite includes a `run_exhaustive()` function that sweeps all input values for every decoder using built-in pure-Python reference models (cross-validated against cocotb):

```python
# On RP2350 demoboard MicroPython REPL:
import test_corona
test_corona.run_exhaustive()
```

| Decoder | fmt_id | Values swept | Reference model |
|---------|--------|-------------|-----------------|
| FP8 E5M2 | 10 | 256 | IEEE 754 subnormal handling |
| MXFP8 E4M3 | 39 | 256 | OCP MX NaN encoding |
| LNS8 | 42 | 256 | Q3.4 log + 16-entry antilog LUT |
| INT8 | 47 | 256 | Two's complement sign extension |
| E8M0 | 78 | 256 | Exponent-only, 0xFF=NaN |
| MXINT8 | 79 | 256 | Fixed-point * 2^-6, 0x80=NaN |
| E4M3 FNUZ | 14 | 256 | Bias=8, 0x80=NaN |
| FP4 E2M1 | 41 | 16 | LUT-based |
| NF4 QLoRA | 70 | 16 | LUT-based (quantile levels) |
| FP6 E3M2 | 40 | 64 | OCP MX sub-byte |
| FP6 E2M3 | 77 | 64 | Blackwell sub-byte |
| INT4 | 46 | 16 | Two's complement 4-bit |
| BitNet | 71 | 4 | Ternary {-1,0,+1} |
| BCD | 53 | 100 | Valid packed BCD (00-99) |
| BF16 | 8 | 65,536 | Zero-extend to FP32 (2-byte input) |
| TF32 | 9 | ~1,280 | Boundary + 1024 random (3-byte input) |

Total: 68,708 values swept across 16 decoder sweeps.

All reference models validated bit-exact against cocotb originals.
