# SPDX-License-Identifier: Apache-2.0
# test/test_decoders.py -- cocotb tests for Tier-1 decoders.
# Protocol v2: CMD1 (fmt_id) + CMD2 (byte_count) + raw 8-bit DATA + auto STATUS.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer
import struct

# fmt_id assignments (aligned with ROM catalog / SSOT ordering)
FMT_BF16        = 8
FMT_POSIT8      = 31
FMT_MXFP8_E4M3 = 39
FMT_FP6_E3M2    = 40
FMT_FP4         = 41
FMT_LNS8        = 42
FMT_BCD         = 53
FMT_TF32        = 9
FMT_FP8_E5M2    = 10
FMT_NF4         = 70


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


async def send_cmd(dut, fmt_id, byte_count):
    """Protocol v2 CMD: two cycles. CMD1 = fmt_id (ui_in[7]=0), CMD2 = byte_count."""
    dut.ui_in.value = fmt_id & 0x7F  # CMD1: bit7=0, bits[6:0]=fmt_id
    await RisingEdge(dut.clk)
    dut.ui_in.value = byte_count & 0x0F  # CMD2: bits[3:0]=byte_count
    await RisingEdge(dut.clk)


async def send_data(dut, byte_list):
    """Send raw 8-bit data bytes. All 256 values accepted in Protocol v2."""
    for b in byte_list:
        dut.ui_in.value = b & 0xFF
        await RisingEdge(dut.clk)


async def read_result_bytes(dut, n):
    """Read n result bytes during STATUS state (auto-entered after data)."""
    result = []
    for _ in range(n):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        result.append(dut.uo_out.value.integer)
    return result


def bytes_to_u32(b):
    """Convert 4 LSB-first bytes to uint32."""
    return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)


# =========================================================================
# Python reference models
# =========================================================================

def ref_fp4(val):
    LUT = {
        0x0: 0x00000000, 0x1: 0x3F000000, 0x2: 0x3F800000, 0x3: 0x3FC00000,
        0x4: 0x40000000, 0x5: 0x40400000, 0x6: 0x40800000, 0x7: 0x40C00000,
        0x8: 0x80000000, 0x9: 0xBF000000, 0xA: 0xBF800000, 0xB: 0xBFC00000,
        0xC: 0xC0000000, 0xD: 0xC0400000, 0xE: 0xC0800000, 0xF: 0xC0C00000,
    }
    return LUT[val & 0xF]


def ref_nf4(val):
    LUT = {
        0x0: 0xBF800000, 0x1: 0xBF3239B1, 0x2: 0xBF066B30, 0x3: 0xBECA32A0,
        0x4: 0xBE91A24D, 0x5: 0xBE3D353F, 0x6: 0xBDBA7871, 0x7: 0x00000000,
        0x8: 0x3DA2FAFF, 0x9: 0x3E24CAE3, 0xA: 0x3E7C04DD, 0xB: 0x3EAD033A,
        0xC: 0x3EE1A4B8, 0xD: 0x3F1007AB, 0xE: 0x3F3913B3, 0xF: 0x3F800000,
    }
    return LUT[val & 0xF]


def ref_fp6_e3m2(val):
    sign = (val >> 5) & 1
    exp = (val >> 2) & 0x7
    mant = val & 0x3
    if exp == 0 and mant == 0:
        return sign << 31
    elif exp == 0:
        if mant & 2:
            fp32_exp = 124
            fp32_mant = (mant & 1) << 22
        else:
            fp32_exp = 123
            fp32_mant = 0
        return (sign << 31) | (fp32_exp << 23) | fp32_mant
    else:
        fp32_exp = exp + 124
        fp32_mant = mant << 21
        return (sign << 31) | (fp32_exp << 23) | fp32_mant


def ref_mxfp8_e4m3(byte_val):
    sign = (byte_val >> 7) & 1
    exp = (byte_val >> 3) & 0xF
    mant = byte_val & 0x7
    if exp == 0xF and mant == 0x7:
        return 0x7FC00000 if sign == 0 else 0xFFC00000
    elif exp == 0 and mant == 0:
        return 0x80000000 if sign else 0x00000000
    elif exp == 0:
        if mant & 4:
            fp32_exp = 121
            fp32_mant = (mant & 3) << 21
        elif mant & 2:
            fp32_exp = 120
            fp32_mant = (mant & 1) << 22
        else:
            fp32_exp = 119
            fp32_mant = 0
        return (sign << 31) | (fp32_exp << 23) | fp32_mant
    else:
        fp32_exp = exp + 120
        fp32_mant = mant << 20
        return (sign << 31) | (fp32_exp << 23) | fp32_mant


def ref_posit8(byte_val):
    if byte_val == 0x00:
        return 0x00000000
    if byte_val == 0x80:
        return 0x7FC00000
    sign = (byte_val >> 7) & 1
    if sign:
        abs_val = ((~byte_val) + 1) & 0x7F
    else:
        abs_val = byte_val & 0x7F
    regime_sign = (abs_val >> 6) & 1
    if regime_sign:
        inverted = (~abs_val) & 0x7F
    else:
        inverted = abs_val & 0x7F
    lzc = 1
    for i in range(6, -1, -1):
        if (inverted >> i) & 1:
            lzc = 6 - i
            break
    else:
        lzc = 7
    if lzc == 0:
        lzc = 1
    if regime_sign:
        k = lzc - 1
    else:
        k = -lzc
    regime_total = lzc + 1 if lzc < 7 else lzc
    shifted = (abs_val << regime_total) & 0x7F
    fraction = (shifted >> 1) & 0x3F
    fp32_exp = k + 127
    return (sign << 31) | (fp32_exp << 23) | (fraction << 17)


def ref_lns8(byte_val):
    """LNS8: 1 sign + 7-bit Q3.4 log -> {sign, 15'b0, magnitude[15:0]}."""
    LUT = [256, 267, 279, 291, 304, 317, 331, 345,
           362, 378, 395, 412, 431, 450, 470, 490]
    sign = (byte_val >> 7) & 1
    log_val = byte_val & 0x7F
    is_zero = (byte_val == 0x00)
    if is_zero:
        magnitude = 0
    else:
        int_part = (log_val >> 4) & 0x7
        frac_part = log_val & 0xF
        magnitude = (LUT[frac_part] << int_part) & 0xFFFF
    return (sign << 31) | magnitude


# =========================================================================
# FP4 Exhaustive (16 values)
# =========================================================================

@cocotb.test()
async def test_fp4_exhaustive(dut):
    """FP4 E2M1: exhaustive test of all 16 values."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    for inp in range(16):
        await reset_dut(dut)
        expected = ref_fp4(inp)
        await send_cmd(dut, FMT_FP4, 1)
        await send_data(dut, [inp])
        result = await read_result_bytes(dut, 4)
        got = bytes_to_u32(result)
        assert got == expected, \
            f"FP4 0x{inp:X}: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: FP4 exhaustive (16/16)")


# =========================================================================
# NF4 Exhaustive (16 values)
# =========================================================================

@cocotb.test()
async def test_nf4_exhaustive(dut):
    """NF4 QLoRA: exhaustive test of all 16 values."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    for inp in range(16):
        await reset_dut(dut)
        expected = ref_nf4(inp)
        await send_cmd(dut, FMT_NF4, 1)
        await send_data(dut, [inp])
        result = await read_result_bytes(dut, 4)
        got = bytes_to_u32(result)
        assert got == expected, \
            f"NF4 0x{inp:X}: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: NF4 exhaustive (16/16)")


# =========================================================================
# FP6 E3M2 Exhaustive (64 values)
# =========================================================================

@cocotb.test()
async def test_fp6_e3m2_exhaustive(dut):
    """FP6 E3M2: exhaustive test of all 64 values."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    for inp in range(64):
        await reset_dut(dut)
        expected = ref_fp6_e3m2(inp)
        await send_cmd(dut, FMT_FP6_E3M2, 1)
        await send_data(dut, [inp])
        result = await read_result_bytes(dut, 4)
        got = bytes_to_u32(result)
        assert got == expected, \
            f"FP6 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: FP6 E3M2 exhaustive (64/64)")


# =========================================================================
# MXFP8 E4M3 Exhaustive (256 values)
# =========================================================================

@cocotb.test()
async def test_mxfp8_e4m3_exhaustive(dut):
    """MXFP8 E4M3: exhaustive test of all 256 values."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    fail_count = 0
    for inp in range(256):
        await reset_dut(dut)
        expected = ref_mxfp8_e4m3(inp)
        await send_cmd(dut, FMT_MXFP8_E4M3, 1)
        await send_data(dut, [inp])
        result = await read_result_bytes(dut, 4)
        got = bytes_to_u32(result)
        if got != expected:
            dut._log.error(
                f"MXFP8 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}")
            fail_count += 1
    assert fail_count == 0, f"MXFP8 E4M3: {fail_count}/256 values failed"
    dut._log.info("PASS: MXFP8 E4M3 exhaustive (256/256)")


# =========================================================================
# Posit8 Exhaustive (256 values)
# =========================================================================

@cocotb.test()
async def test_posit8_exhaustive(dut):
    """Posit8(es=0): exhaustive test of all 256 values."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    fail_count = 0
    for inp in range(256):
        await reset_dut(dut)
        expected = ref_posit8(inp)
        await send_cmd(dut, FMT_POSIT8, 1)
        await send_data(dut, [inp])
        result = await read_result_bytes(dut, 4)
        got = bytes_to_u32(result)
        if got != expected:
            dut._log.error(
                f"Posit8 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}")
            fail_count += 1
    assert fail_count == 0, f"Posit8: {fail_count}/256 values failed"
    dut._log.info("PASS: Posit8 exhaustive (256/256)")


# =========================================================================
# BCD Test
# =========================================================================

@cocotb.test()
async def test_bcd_values(dut):
    """BCD decode: packed BCD bytes -> binary."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    test_cases = [
        (0x00, 0),   # 00
        (0x42, 42),  # 42
        (0x99, 99),  # 99
        (0x10, 10),  # 10
        (0x01, 1),   # 01
        (0x50, 50),  # 50
    ]

    for bcd_in, expected_bin in test_cases:
        await reset_dut(dut)
        await send_cmd(dut, FMT_BCD, 1)
        await send_data(dut, [bcd_in])
        result = await read_result_bytes(dut, 4)
        got = bytes_to_u32(result)
        assert got == expected_bin, \
            f"BCD 0x{bcd_in:02X}: expected {expected_bin}, got {got}"
        dut._log.info(f"BCD 0x{bcd_in:02X} -> {got} OK")
    dut._log.info("PASS: BCD values correct")


# =========================================================================
# LNS8 Exhaustive (256 values)
# =========================================================================

@cocotb.test()
async def test_lns8_exhaustive(dut):
    """LNS8: exhaustive test of all 256 values."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    fail_count = 0
    for inp in range(256):
        await reset_dut(dut)
        expected = ref_lns8(inp)
        await send_cmd(dut, FMT_LNS8, 1)
        await send_data(dut, [inp])
        result = await read_result_bytes(dut, 4)
        got = bytes_to_u32(result)
        if got != expected:
            dut._log.error(
                f"LNS8 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}")
            fail_count += 1
    assert fail_count == 0, f"LNS8: {fail_count}/256 values failed"
    dut._log.info("PASS: LNS8 exhaustive (256/256)")


# =========================================================================
# Not-Implemented Format Test
# =========================================================================

@cocotb.test()
async def test_not_implemented_sentinel(dut):
    """Unknown fmt_id returns NOT_IMPL sentinel (0xFF, fmt_id, 0x07, 'N')."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    await send_cmd(dut, 0x01, 1)  # fmt_id=1 has no decoder
    await send_data(dut, [0x00])
    result = await read_result_bytes(dut, 4)

    assert result[0] == 0xFF, f"byte 0: expected 0xFF, got 0x{result[0]:02X}"
    assert result[1] == 0x01, f"byte 1: expected 0x01 (fmt_id), got 0x{result[1]:02X}"
    assert result[2] == 0x07, f"byte 2: expected 0x07 (SPEC), got 0x{result[2]:02X}"
    assert result[3] == 0x4E, f"byte 3: expected 0x4E ('N'), got 0x{result[3]:02X}"
    dut._log.info(f"PASS: not-impl -> {[hex(b) for b in result]}")


# =========================================================================
# BF16 Key Values (2-byte input)
# =========================================================================

@cocotb.test()
async def test_bf16_key_values(dut):
    """BF16: key values -> FP32 (zero-extends lower 16 bits)."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    test_cases = [
        ([0x00, 0x00], 0x00000000),  # +0.0
        ([0x00, 0x80], 0x80000000),  # -0.0
        ([0x00, 0x3F], 0x3F000000),  # 0.5 (BF16 = 0x3F00)
        ([0x80, 0x3F], 0x3F800000),  # 1.0 (BF16 = 0x3F80)
        ([0x00, 0x40], 0x40000000),  # 2.0 (BF16 = 0x4000)
        ([0x80, 0x7F], 0x7F800000),  # +Inf
        ([0xC0, 0x7F], 0x7FC00000),  # NaN (quiet)
    ]

    for data_bytes, expected in test_cases:
        await reset_dut(dut)
        await send_cmd(dut, FMT_BF16, 2)
        await send_data(dut, data_bytes)
        result = await read_result_bytes(dut, 4)
        got = bytes_to_u32(result)
        assert got == expected, \
            f"BF16 {[hex(b) for b in data_bytes]}: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: BF16 key values correct")


# =========================================================================
# ROM Readback (byte_count=0 triggers ROM mode, streams 10 bytes)
# =========================================================================

# Import the ROM catalog from gen_rom.py for verification
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from gen_rom import CATALOG, pack_record


async def read_rom_record(dut, fmt_id):
    """Send ROM readback CMD (byte_count=0) and read 10 bytes."""
    await send_cmd(dut, fmt_id, 0)
    result = []
    for _ in range(10):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        result.append(dut.uo_out.value.integer)
    return result


def rom_bytes_to_u80(b):
    """Convert 10 LSB-first bytes to 80-bit integer."""
    val = 0
    for i, byte in enumerate(b):
        val |= byte << (i * 8)
    return val


@cocotb.test()
async def test_rom_readback_all(dut):
    """ROM readback: verify all 77 records match expected packed values."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    fail_count = 0
    for rec in CATALOG:
        fmt_id = rec[0]
        expected = pack_record(*rec)
        await reset_dut(dut)
        result = await read_rom_record(dut, fmt_id)
        got = rom_bytes_to_u80(result)
        if got != expected:
            dut._log.error(
                f"ROM[{fmt_id}]: expected 0x{expected:020X}, got 0x{got:020X}")
            fail_count += 1
    assert fail_count == 0, f"ROM readback: {fail_count}/77 records failed"
    dut._log.info("PASS: ROM readback all 77 records correct")


@cocotb.test()
async def test_rom_readback_key_fields(dut):
    """ROM readback: verify key fields can be extracted from a few records."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    # Check fp32 (fmt_id=1): total_bits=32, exp=8, mant=23, encoding=FP(0)
    await reset_dut(dut)
    result = await read_rom_record(dut, 1)
    got = rom_bytes_to_u80(result)

    # Extract fields per rom_layout
    fmt_idx = (got >> 72) & 0xFF
    total_bits = (got >> 56) & 0xFF
    exp_bits = (got >> 44) & 0xFF
    mant_bits = (got >> 36) & 0xFF
    enc_kind = (got >> 32) & 0xF

    assert fmt_idx == 1, f"fmt_idx: expected 1, got {fmt_idx}"
    assert total_bits == 32, f"total_bits: expected 32, got {total_bits}"
    assert exp_bits == 8, f"exp_bits: expected 8, got {exp_bits}"
    assert mant_bits == 23, f"mant_bits: expected 23, got {mant_bits}"
    assert enc_kind == 0, f"enc_kind: expected 0 (FP), got {enc_kind}"
    dut._log.info("PASS: ROM key fields for fp32 correct")


@cocotb.test()
async def test_rom_unused_address(dut):
    """ROM address >= 77 returns zero."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    result = await read_rom_record(dut, 100)  # unused address
    got = rom_bytes_to_u80(result)
    assert got == 0, f"ROM[100]: expected 0, got 0x{got:020X}"
    dut._log.info("PASS: ROM unused address returns zero")


# =========================================================================
# TF32 reference model
# =========================================================================

def ref_tf32(val_19bit):
    """TF32 (19-bit) -> FP32: sign + exp(8) + mant(10) zero-extended to 23."""
    sign = (val_19bit >> 18) & 1
    exp = (val_19bit >> 10) & 0xFF
    mant = val_19bit & 0x3FF
    return (sign << 31) | (exp << 23) | (mant << 13)


# =========================================================================
# FP8 E5M2 reference model
# =========================================================================

def ref_fp8_e5m2(byte_val):
    """FP8 E5M2 (bias=15) -> FP32 with Inf, NaN, subnormal."""
    sign = (byte_val >> 7) & 1
    exp = (byte_val >> 2) & 0x1F
    mant = byte_val & 0x3

    if exp == 0x1F and mant == 0:
        return (sign << 31) | 0x7F800000  # Inf
    elif exp == 0x1F and mant != 0:
        return (sign << 31) | 0x7FC00000  # quiet NaN
    elif exp == 0 and mant == 0:
        return sign << 31  # zero
    elif exp == 0:
        # Subnormal: 2^(1-15) * 0.mant = 2^(-14) * 0.mant
        if mant & 2:  # mant = 10 or 11
            fp32_exp = 112  # 2^(-15) normalized
            fp32_mant = (mant & 1) << 22
        else:  # mant = 01
            fp32_exp = 111  # 2^(-16) normalized
            fp32_mant = 0
        return (sign << 31) | (fp32_exp << 23) | fp32_mant
    else:
        fp32_exp = exp + 112
        fp32_mant = mant << 21
        return (sign << 31) | (fp32_exp << 23) | fp32_mant


# =========================================================================
# TF32 Key Values Test
# =========================================================================

@cocotb.test()
async def test_tf32_key_values(dut):
    """TF32: key values -> FP32 (wire-concat decode)."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    test_cases = [
        # (19-bit TF32 input as 3 bytes LSB-first, expected FP32)
        (0x00000, 0x00000000),  # +0.0
        (0x40000, 0x80000000),  # -0.0  (sign=1, exp=0, mant=0)
        (0x1FC00, 0x3F800000),  # 1.0   (sign=0, exp=0x7F=127, mant=0)
        (0x20000, 0x40000000),  # 2.0   (sign=0, exp=0x80=128, mant=0)
        (0x1F800, 0x3F000000),  # 0.5   (sign=0, exp=0x7E=126, mant=0)
        (0x3FC00, 0x7F800000),  # +Inf  (sign=0, exp=0xFF, mant=0)
        (0x7FC00, 0xFF800000),  # -Inf  (sign=1, exp=0xFF, mant=0)
        (0x3FC01, 0x7F802000),  # NaN   (sign=0, exp=0xFF, mant=1)
        (0x20200, 0x40400000),  # 3.0   (sign=0, exp=128, mant=0x200=512 -> 512<<13)
    ]

    for tf32_in, expected in test_cases:
        await reset_dut(dut)
        b0 = tf32_in & 0xFF
        b1 = (tf32_in >> 8) & 0xFF
        b2 = (tf32_in >> 16) & 0xFF
        ref = ref_tf32(tf32_in)
        assert ref == expected, \
            f"ref_tf32 self-check: 0x{tf32_in:05X} -> 0x{ref:08X}, expected 0x{expected:08X}"
        await send_cmd(dut, FMT_TF32, 3)
        await send_data(dut, [b0, b1, b2])
        result = await read_result_bytes(dut, 4)
        got = bytes_to_u32(result)
        assert got == expected, \
            f"TF32 0x{tf32_in:05X}: expected 0x{expected:08X}, got 0x{got:08X}"
    dut._log.info("PASS: TF32 key values correct")


# =========================================================================
# FP8 E5M2 Exhaustive (256 values)
# =========================================================================

@cocotb.test()
async def test_fp8_e5m2_exhaustive(dut):
    """FP8 E5M2: exhaustive test of all 256 values."""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    fail_count = 0
    for inp in range(256):
        await reset_dut(dut)
        expected = ref_fp8_e5m2(inp)
        await send_cmd(dut, FMT_FP8_E5M2, 1)
        await send_data(dut, [inp])
        result = await read_result_bytes(dut, 4)
        got = bytes_to_u32(result)
        if got != expected:
            dut._log.error(
                f"FP8_E5M2 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}")
            fail_count += 1
    assert fail_count == 0, f"FP8 E5M2: {fail_count}/256 values failed"
    dut._log.info("PASS: FP8 E5M2 exhaustive (256/256)")
