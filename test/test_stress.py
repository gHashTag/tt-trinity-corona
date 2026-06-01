# SPDX-License-Identifier: Apache-2.0
# test/test_stress.py -- Back-to-back protocol stress tests.
# Verifies FSM correctness without reset between transactions.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import struct

FMT_BF16        = 8
FMT_TF32        = 9
FMT_FP8_E5M2    = 10
FMT_E4M3_FNUZ   = 14
FMT_MXFP8_E4M3 = 39
FMT_FP4         = 41
FMT_INT4        = 46
FMT_INT8        = 47
FMT_BCD         = 53
FMT_BITNET      = 71
FMT_E8M0        = 78
FMT_MXINT8      = 79


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0x80
    dut.uio_in.value = 0
    from cocotb.triggers import ClockCycles
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


async def send_cmd(dut, fmt_id, byte_count):
    dut.ui_in.value = fmt_id & 0x7F
    await RisingEdge(dut.clk)
    dut.ui_in.value = byte_count & 0x0F
    await RisingEdge(dut.clk)


async def send_data(dut, byte_list):
    for b in byte_list:
        dut.ui_in.value = b & 0xFF
        await RisingEdge(dut.clk)


async def read_result_bytes(dut, n):
    result = []
    for _ in range(n):
        await Timer(1, units="ns")
        result.append(dut.uo_out.value.integer)
        await RisingEdge(dut.clk)
    return result


def bytes_to_u32(b):
    return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)


async def transact_decode(dut, fmt_id, data_bytes):
    """Full decode transaction. Returns u32. Waits for DONE->IDLE."""
    await send_cmd(dut, fmt_id, len(data_bytes))
    await send_data(dut, data_bytes)
    result = await read_result_bytes(dut, 4)
    dut.ui_in.value = 0x80
    await RisingEdge(dut.clk)  # DONE -> IDLE
    return bytes_to_u32(result)


async def transact_rom(dut, fmt_id):
    """Full ROM readback transaction. Returns 10-byte list. Waits for DONE->IDLE."""
    await send_cmd(dut, fmt_id, 0)
    result = []
    for _ in range(10):
        await Timer(1, units="ns")
        result.append(dut.uo_out.value.integer)
        await RisingEdge(dut.clk)
    dut.ui_in.value = 0x80
    await RisingEdge(dut.clk)  # DONE -> IDLE
    return result


# Reference models (subset needed for stress tests)
def ref_fp4(val):
    LUT = {
        0x0: 0x00000000, 0x1: 0x3F000000, 0x2: 0x3F800000, 0x3: 0x3FC00000,
        0x4: 0x40000000, 0x5: 0x40400000, 0x6: 0x40800000, 0x7: 0x40C00000,
        0x8: 0x80000000, 0x9: 0xBF000000, 0xA: 0xBF800000, 0xB: 0xBFC00000,
        0xC: 0xC0000000, 0xD: 0xC0400000, 0xE: 0xC0800000, 0xF: 0xC0C00000,
    }
    return LUT[val & 0xF]


def ref_bf16(val):
    return (val & 0xFFFF) << 16


def ref_int8(val):
    signed_val = val if val < 128 else val - 256
    return struct.unpack('>I', struct.pack('>i', signed_val))[0]


def ref_e8m0(val):
    if val == 0xFF:
        return 0x7FC00000
    if val == 0x00:
        return 0x00400000
    return (val << 23) & 0x7FFFFFFF


def ref_mxint8(val):
    if val == 0x00:
        return 0x00000000
    if val == 0x80:
        return 0x7FC00000
    signed_val = val if val < 128 else val - 256
    f = signed_val / 64.0
    return struct.unpack('>I', struct.pack('>f', f))[0]


@cocotb.test()
async def test_back_to_back_same_format(dut):
    """10 consecutive FP4 decodes without reset between transactions."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    for i in range(16):
        expected = ref_fp4(i)
        got = await transact_decode(dut, FMT_FP4, [i])
        assert got == expected, \
            f"Back-to-back FP4[{i}]: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: 16 back-to-back FP4 decodes")


@cocotb.test()
async def test_back_to_back_mixed_formats(dut):
    """Alternate between different formats without reset."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    test_sequence = [
        (FMT_FP4,         [0x05],         ref_fp4(0x05)),
        (FMT_INT8,        [0x01],         ref_int8(0x01)),
        (FMT_E8M0,        [0x7F],         ref_e8m0(0x7F)),
        (FMT_MXINT8,      [0x40],         ref_mxint8(0x40)),
        (FMT_FP4,         [0x0F],         ref_fp4(0x0F)),
        (FMT_BF16,        [0x00, 0x3F],   ref_bf16(0x3F00)),
        (FMT_INT8,        [0xFF],         ref_int8(0xFF)),
        (FMT_E8M0,        [0x01],         ref_e8m0(0x01)),
        (FMT_MXINT8,      [0xFF],         ref_mxint8(0xFF)),
        (FMT_BF16,        [0x00, 0x80],   ref_bf16(0x8000)),
    ]

    for i, (fmt, data, expected) in enumerate(test_sequence):
        got = await transact_decode(dut, fmt, data)
        assert got == expected, \
            f"Mixed[{i}] fmt={fmt} data={data}: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: 10 back-to-back mixed format decodes")


@cocotb.test()
async def test_rom_then_decode(dut):
    """ROM readback followed immediately by decode, no reset."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    rom_result = await transact_rom(dut, 0)
    # ROM record 0 (IEEE FP16): byte 7 = total_bits = 16
    assert rom_result[7] == 16, f"ROM record 0 byte7 (total_bits) expected 16, got {rom_result[7]}"

    got = await transact_decode(dut, FMT_FP4, [0x05])
    expected = ref_fp4(0x05)
    assert got == expected, \
        f"Decode after ROM: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: ROM readback then decode")


@cocotb.test()
async def test_decode_then_rom(dut):
    """Decode followed immediately by ROM readback, no reset."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    got = await transact_decode(dut, FMT_INT8, [42])
    expected = ref_int8(42)
    assert got == expected, \
        f"Decode before ROM: expected 0x{expected:08X}, got 0x{got:08X}"

    rom_result = await transact_rom(dut, 0)
    assert rom_result[7] == 16, f"ROM record 0 after decode: byte7 expected 16, got {rom_result[7]}"
    dut._log.info("PASS: Decode then ROM readback")


@cocotb.test()
async def test_multi_byte_then_single_byte(dut):
    """2-byte BF16 followed by 1-byte formats to catch stale data_in_buf."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # BF16: 0x4080 = 4.0, sent as [0x80, 0x40] (LSB first)
    got = await transact_decode(dut, FMT_BF16, [0x80, 0x40])
    assert got == ref_bf16(0x4080), \
        f"BF16 0x4080: expected 0x{ref_bf16(0x4080):08X}, got 0x{got:08X}"

    # FP4 0x03 after BF16 — data_in_buf must be zeroed, not carry BF16 residue
    got = await transact_decode(dut, FMT_FP4, [0x03])
    expected = ref_fp4(0x03)
    assert got == expected, \
        f"FP4 after BF16: expected 0x{expected:08X}, got 0x{got:08X}"

    # INT8 0x80 (-128) after FP4
    got = await transact_decode(dut, FMT_INT8, [0x80])
    expected = ref_int8(0x80)
    assert got == expected, \
        f"INT8 after FP4: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: multi-byte then single-byte transitions")


@cocotb.test()
async def test_3byte_tf32_then_1byte(dut):
    """3-byte TF32 followed by 1-byte E8M0 to verify buffer cleanup."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # TF32 for +1.0: exp=127=0x7F, mantissa top 10 bits=0
    # 19-bit TF32: [18]=sign=0, [17:10]=exp=0x7F, [9:0]=mantissa=0
    # = 0b0_01111111_0000000000 = 0x1FC00 (19 bits)
    # Sent as 3 bytes LSB first: byte0=0x00, byte1=0xFC, byte2=0x01
    got = await transact_decode(dut, FMT_TF32, [0x00, 0xFC, 0x01])
    expected = 0x3F800000  # +1.0
    assert got == expected, \
        f"TF32 1.0: expected 0x{expected:08X}, got 0x{got:08X}"

    # Now E8M0 0x7F (2^0 = 1.0 as power-of-2) — must not be corrupted by TF32 residue
    got = await transact_decode(dut, FMT_E8M0, [0x7F])
    expected = ref_e8m0(0x7F)
    assert got == expected, \
        f"E8M0 after TF32: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: 3-byte TF32 then 1-byte E8M0")


@cocotb.test()
async def test_rapid_format_cycling(dut):
    """Cycle through all 14 decoder formats without reset."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    test_cases = [
        (FMT_FP4,         [0x02],         ref_fp4(0x02)),
        (FMT_MXFP8_E4M3,  [0x3F],        None),  # just verify no hang
        (FMT_INT8,        [0x01],         ref_int8(0x01)),
        (FMT_E8M0,        [0x80],         ref_e8m0(0x80)),
        (FMT_MXINT8,      [0x01],         ref_mxint8(0x01)),
        (FMT_BCD,         [0x42],         42),
        (FMT_BF16,        [0x80, 0x3F],   ref_bf16(0x3F80)),
        (FMT_FP8_E5M2,    [0x40],        None),  # just verify completes
        (FMT_E4M3_FNUZ,   [0x3F],        None),  # FNUZ: verify completes
        (FMT_BITNET,      [0x01],         0x3F800000),  # ternary +1
        (FMT_INT4,        [0x0F],         0xFFFFFFFF),  # -1 sign-extended
        (FMT_E8M0,        [0xFE],         ref_e8m0(0xFE)),
        (FMT_INT8,        [0x7E],         ref_int8(0x7E)),
    ]

    for i, (fmt, data, expected) in enumerate(test_cases):
        got = await transact_decode(dut, fmt, data)
        if expected is not None:
            assert got == expected, \
                f"Cycle[{i}] fmt={fmt}: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: rapid format cycling (13 formats, no reset)")


def not_impl_u32(fmt_id):
    return 0xFF | ((fmt_id & 0x7F) << 8) | (0x07 << 16) | (0x4E << 24)


@cocotb.test()
async def test_not_impl_response(dut):
    """Decode with fmt_id that has no decoder returns NOT_IMPL sentinel."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    no_decoder_ids = [0, 5, 6, 7, 15, 20, 50, 60]
    for fmt_id in no_decoder_ids:
        got = await transact_decode(dut, fmt_id, [0x00])
        expected = not_impl_u32(fmt_id)
        assert got == expected, \
            f"NOT_IMPL fmt_id={fmt_id}: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info(f"PASS: NOT_IMPL sentinel for {len(no_decoder_ids)} decoder-less fmt_ids")


@cocotb.test()
async def test_out_of_range_decode(dut):
    """Decode with fmt_id > 79 (beyond ROM) returns NOT_IMPL gracefully."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    for fmt_id in [80, 100, 126]:
        got = await transact_decode(dut, fmt_id, [0x42])
        expected = not_impl_u32(fmt_id)
        assert got == expected, \
            f"Out-of-range fmt_id={fmt_id}: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: out-of-range fmt_ids produce NOT_IMPL")


@cocotb.test()
async def test_rom_out_of_range(dut):
    """ROM readback for fmt_id > 79 returns all zeros (ROM default case)."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    rom_result = await transact_rom(dut, 100)
    assert all(b == 0 for b in rom_result), \
        f"ROM[100] expected all zeros, got {[hex(b) for b in rom_result]}"
    dut._log.info("PASS: ROM readback beyond entry 79 returns zeros")


@cocotb.test()
async def test_consecutive_rom_readbacks(dut):
    """Three ROM readbacks in a row without reset."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    r0 = await transact_rom(dut, 0)
    assert r0[7] == 16, f"ROM[0] byte7 expected 16 (FP16 total_bits), got {r0[7]}"

    r79 = await transact_rom(dut, 79)
    assert r79[0] != 0 or r79[1] != 0, "ROM[79] should not be all-zero (MXINT8 is valid)"

    r0_again = await transact_rom(dut, 0)
    assert r0 == r0_again, "ROM[0] second read must match first read"
    dut._log.info("PASS: 3 consecutive ROM readbacks, data consistent")


@cocotb.test()
async def test_last_valid_rom_entry(dut):
    """ROM readback for fmt_id=79 (MXINT8, last entry) returns valid data."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    rom_result = await transact_rom(dut, 79)
    assert rom_result[7] == 8, f"ROM[79] byte7 (total_bits) expected 8 (MXINT8), got {rom_result[7]}"
    assert not all(b == 0 for b in rom_result), "ROM[79] should contain valid MXINT8 metadata"

    got = await transact_decode(dut, FMT_MXINT8, [0x40])
    expected = ref_mxint8(0x40)
    assert got == expected, \
        f"MXINT8 decode after ROM[79]: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: last ROM entry (79) valid, decode still works")


@cocotb.test()
async def test_byte_count_clamping(dut):
    """Sending byte_count > 4 is clamped to 4; FSM collects 4 bytes and decodes."""
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    dut.ui_in.value = FMT_INT8
    await RisingEdge(dut.clk)
    dut.ui_in.value = 0x0F  # byte_count=15, should clamp to 4
    await RisingEdge(dut.clk)

    # Shift register: {ui_in, data_in_buf[31:8]} each cycle (right shift).
    # Last byte sent ends up at [31:24]. INT8 reads [31:24].
    for i in range(4):
        dut.ui_in.value = 0x2A if i == 3 else 0x00
        await RisingEdge(dut.clk)

    result = await read_result_bytes(dut, 4)
    got = bytes_to_u32(result)
    expected = ref_int8(0x2A)
    assert got == expected, \
        f"Clamped decode: expected 0x{expected:08X}, got 0x{got:08X}"
    dut.ui_in.value = 0x80
    await RisingEdge(dut.clk)
    dut._log.info("PASS: byte_count=15 clamped to 4, decode correct")


@cocotb.test()
async def test_mid_transaction_reset(dut):
    """Reset during CMD2, DATA, and STATUS states; verify FSM recovers."""
    from cocotb.triggers import ClockCycles
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    # Case 1: Reset during CMD2 (after CMD1, before byte_count)
    await reset_dut(dut)
    dut.ui_in.value = FMT_INT8  # CMD1
    await RisingEdge(dut.clk)
    # Now in ST_CMD2 — assert reset
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    # Verify: anchor probe works (FSM back in IDLE)
    dut.ui_in.value = 0x7F
    await Timer(1, units="ns")
    assert dut.uo_out.value.integer == 0xC0, "Reset in CMD2: anchor failed"

    # Case 2: Reset during DATA (after CMD2, during byte collection)
    await reset_dut(dut)
    dut.ui_in.value = FMT_INT8  # CMD1
    await RisingEdge(dut.clk)
    dut.ui_in.value = 0x02  # CMD2: byte_count=2
    await RisingEdge(dut.clk)
    dut.ui_in.value = 0xAA  # First data byte
    await RisingEdge(dut.clk)
    # Now in ST_DATA with 1 byte remaining — assert reset
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    dut.ui_in.value = 0x7F
    await Timer(1, units="ns")
    assert dut.uo_out.value.integer == 0xC0, "Reset in DATA: anchor failed"

    # Case 3: Reset during STATUS (during result readback)
    await reset_dut(dut)
    await send_cmd(dut, FMT_FP4, 1)
    await send_data(dut, [0x05])
    # Now in ST_STATUS — read 1 byte then reset
    await Timer(1, units="ns")
    _ = dut.uo_out.value.integer  # read first status byte
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    dut.ui_in.value = 0x7F
    await Timer(1, units="ns")
    assert dut.uo_out.value.integer == 0xC0, "Reset in STATUS: anchor failed"

    # Case 4: Verify a full transaction works after all resets
    await reset_dut(dut)
    got = await transact_decode(dut, FMT_FP4, [0x05])
    expected = ref_fp4(0x05)
    assert got == expected, f"Post-reset decode: expected 0x{expected:08X}, got 0x{got:08X}"

    dut._log.info("PASS: mid-transaction reset recovery (CMD2, DATA, STATUS, post-reset decode)")


@cocotb.test()
async def test_ena_gate_data_and_status(dut):
    """ena=0 freezes FSM in DATA and STATUS states, resumes correctly."""
    from cocotb.triggers import ClockCycles
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    # Case 1: ena=0 during ST_DATA
    await reset_dut(dut)
    dut.ui_in.value = FMT_INT8  # CMD1
    await RisingEdge(dut.clk)
    dut.ui_in.value = 0x02  # CMD2: byte_count=2
    await RisingEdge(dut.clk)
    dut.ui_in.value = 0x00  # First data byte
    await RisingEdge(dut.clk)
    # Now in ST_DATA with 1 byte remaining — freeze
    dut.ena.value = 0
    dut.ui_in.value = 0x2A  # This byte should NOT be consumed
    await ClockCycles(dut.clk, 5)
    dut.ena.value = 1
    # Now send the real last byte
    dut.ui_in.value = 0x2A
    await RisingEdge(dut.clk)
    # Should be in STATUS now
    result = await read_result_bytes(dut, 4)
    got = bytes_to_u32(result)
    expected = ref_int8(0x2A)
    assert got == expected, \
        f"ena gate DATA: expected 0x{expected:08X}, got 0x{got:08X}"

    # Case 2: ena=0 during ST_STATUS
    await reset_dut(dut)
    await send_cmd(dut, FMT_FP4, 1)
    await send_data(dut, [0x03])
    # Now in ST_STATUS — read first byte, then freeze
    await Timer(1, units="ns")
    byte0 = dut.uo_out.value.integer
    await RisingEdge(dut.clk)
    dut.ena.value = 0
    await ClockCycles(dut.clk, 5)
    dut.ena.value = 1
    # Continue reading remaining bytes
    await Timer(1, units="ns")
    byte1 = dut.uo_out.value.integer
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")
    byte2 = dut.uo_out.value.integer
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")
    byte3 = dut.uo_out.value.integer
    got = byte0 | (byte1 << 8) | (byte2 << 16) | (byte3 << 24)
    expected = ref_fp4(0x03)
    assert got == expected, \
        f"ena gate STATUS: expected 0x{expected:08X}, got 0x{got:08X}"

    dut._log.info("PASS: ena=0 freezes FSM in DATA and STATUS states")
