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

9 tests covering the critical verification paths:

| Test | What it verifies | Cocotb equivalent |
|------|-----------------|-------------------|
| test_anchor | 0x47C0 anchor probe | test_anchor_basic |
| test_anchor_stability | Anchor stable over 10 reads | test_anchor_repeat |
| test_rom_self_index_sweep | All 80 ROM entries have correct self-index | test_full_rom_self_index_sweep |
| test_rom_out_of_range | Addresses 80-126 return zeros | test_rom_oob |
| test_decode_fp8_e5m2 | 8 FP8 E5M2 vectors (0, Inf, subnormal, 1.0) | test_fp8_e5m2_exhaustive |
| test_decode_bf16 | 6 BF16 vectors (0, 0.5, 1.0, 2.0, Inf) | test_bf16_sweep |
| test_decode_posit8 | 3 Posit8 vectors (0, 1, -1) | test_posit8_exhaustive |
| test_decode_int8 | 5 INT8 vectors (0, 1, 127, -1, -128) | test_int8_sweep |
| test_not_implemented | Format 15 returns 0xFF + 'N' | test_no_decoder_response |

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
PASS: not-implemented response (format 15 = GoldenFloat, no decoder)

========================================
Results: 9 passed, 0 failed, 9 total
ALL PASS
```

## Pass/Fail Criteria

- ALL 9 tests must pass for silicon validation
- Anchor test is the first check (proves die identity + basic I/O)
- ROM sweep is the most comprehensive (proves all 80 records intact)
- Decoder tests prove the combinational logic is functional
- Any single failure indicates a silicon defect

## Extending

To add exhaustive decoder sweeps (matching cocotb's 256-value sweeps for 8-bit formats), increase the vector tables in `test_corona.py`. The RP2350 has enough speed to sweep all 256 values for each 8-bit decoder in under 1 second.
