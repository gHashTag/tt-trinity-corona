# SPDX-License-Identifier: Apache-2.0
# post_silicon/test_corona.py -- RP2350 demoboard test suite for TRI-1 Corona
#
# Run on the TinyTapeout RP2350 demoboard via MicroPython or CPython.
# Requires the tt_um_controller library (bundled with TT demoboard firmware).
#
# Usage:
#   import test_corona
#   test_corona.run_all()

import time

try:
    from machine import Pin
    MICROPYTHON = True
except ImportError:
    MICROPYTHON = False

ANCHOR_UO = 0xC0
ANCHOR_UIO = 0x47
FMT_ID_ANCHOR = 0x7F
NUM_FORMATS = 80


class CoronaDriver:
    """Low-level driver for Corona's Protocol v2 over TT demoboard pins."""

    def __init__(self, tt):
        self.tt = tt

    def reset(self):
        self.tt.reset_project(True)
        time.sleep(0.001)
        self.tt.reset_project(False)
        time.sleep(0.001)

    def clock_pulse(self):
        self.tt.clock_project_once()

    def set_ui_in(self, val):
        self.tt.input_byte = val & 0xFF

    def read_uo_out(self):
        return self.tt.output_byte

    def read_uio_out(self):
        return self.tt.bidir_byte

    def anchor_probe(self):
        self.set_ui_in(FMT_ID_ANCHOR)
        self.clock_pulse()
        uo = self.read_uo_out()
        uio = self.read_uio_out()
        return (uio << 8) | uo

    def rom_readback(self, fmt_id):
        self.set_ui_in(fmt_id & 0x7F)
        self.clock_pulse()
        self.set_ui_in(0x00)
        self.clock_pulse()
        result = []
        for _ in range(10):
            self.clock_pulse()
            result.append(self.read_uo_out())
        self.clock_pulse()
        return result

    def decode(self, fmt_id, data_bytes):
        self.set_ui_in(fmt_id & 0x7F)
        self.clock_pulse()
        self.set_ui_in(len(data_bytes) & 0x0F)
        self.clock_pulse()
        for b in data_bytes:
            self.set_ui_in(b)
            self.clock_pulse()
        result = []
        for _ in range(4):
            self.clock_pulse()
            result.append(self.read_uo_out())
        self.clock_pulse()
        return result


def bytes_to_u32(b):
    return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)


def test_anchor(drv):
    drv.reset()
    val = drv.anchor_probe()
    assert val == 0x47C0, f"FAIL: anchor expected 0x47C0, got 0x{val:04X}"
    print("PASS: anchor probe = 0x47C0")


def test_anchor_stability(drv):
    drv.reset()
    for i in range(10):
        val = drv.anchor_probe()
        assert val == 0x47C0, f"FAIL: anchor unstable at cycle {i}: 0x{val:04X}"
    print("PASS: anchor stable over 10 reads")


def test_rom_self_index_sweep(drv):
    drv.reset()
    errors = 0
    for fmt_id in range(NUM_FORMATS):
        rom = drv.rom_readback(fmt_id)
        got_index = rom[9]
        if got_index != fmt_id:
            print(f"  FAIL: ROM[{fmt_id}] self-index = {got_index}")
            errors += 1
        if all(b == 0 for b in rom):
            print(f"  FAIL: ROM[{fmt_id}] all zeros")
            errors += 1
    assert errors == 0, f"ROM sweep: {errors} error(s)"
    print(f"PASS: ROM self-index sweep (all {NUM_FORMATS} entries)")


def test_rom_out_of_range(drv):
    drv.reset()
    for fmt_id in [80, 100, 126]:
        rom = drv.rom_readback(fmt_id)
        assert all(b == 0 for b in rom), f"FAIL: ROM[{fmt_id}] should be zeros"
    print("PASS: ROM out-of-range returns zeros")


from corona_vectors import (
    FP8_E5M2_VECTORS, BF16_VECTORS, POSIT8_VECTORS, INT8_VECTORS, TF32_VECTORS,
    MXFP8_E4M3_VECTORS, LNS8_VECTORS, BCD_VECTORS, FP4_E2M1_VECTORS, NF4_VECTORS,
    FP6_E3M2_VECTORS, FP6_E2M3_VECTORS, E8M0_VECTORS, MXINT8_VECTORS,
    E4M3_FNUZ_VECTORS, INT4_VECTORS, BITNET_VECTORS, ALIAS_VECTORS,
)


def test_decode_fp8_e5m2(drv):
    drv.reset()
    for inp, expected in FP8_E5M2_VECTORS:
        result = drv.decode(10, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: FP8_E5M2 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: FP8 E5M2 decode ({len(FP8_E5M2_VECTORS)} vectors)")


def test_decode_bf16(drv):
    drv.reset()
    for data, expected in BF16_VECTORS:
        result = drv.decode(8, data)
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: BF16 {data}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: BF16 decode ({len(BF16_VECTORS)} vectors)")


def test_decode_posit8(drv):
    drv.reset()
    for inp, expected in POSIT8_VECTORS:
        result = drv.decode(31, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: Posit8 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: Posit8 decode ({len(POSIT8_VECTORS)} vectors)")


def test_decode_int8(drv):
    drv.reset()
    for inp, expected in INT8_VECTORS:
        result = drv.decode(47, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: INT8 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: INT8 decode ({len(INT8_VECTORS)} vectors)")


def test_decode_tf32(drv):
    drv.reset()
    for data, expected in TF32_VECTORS:
        result = drv.decode(9, data)
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: TF32 {data}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: TF32 decode ({len(TF32_VECTORS)} vectors)")


def test_decode_mxfp8_e4m3(drv):
    drv.reset()
    for inp, expected in MXFP8_E4M3_VECTORS:
        result = drv.decode(39, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: MXFP8_E4M3 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: MXFP8 E4M3 decode ({len(MXFP8_E4M3_VECTORS)} vectors)")


def test_decode_lns8(drv):
    drv.reset()
    for inp, expected in LNS8_VECTORS:
        result = drv.decode(42, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: LNS8 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: LNS8 decode ({len(LNS8_VECTORS)} vectors)")


def test_decode_bcd(drv):
    drv.reset()
    for inp, expected in BCD_VECTORS:
        result = drv.decode(53, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: BCD 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: BCD decode ({len(BCD_VECTORS)} vectors)")


def test_decode_fp4(drv):
    drv.reset()
    for inp, expected in FP4_E2M1_VECTORS:
        result = drv.decode(41, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: FP4 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: FP4 E2M1 decode ({len(FP4_E2M1_VECTORS)} vectors)")


def test_decode_nf4(drv):
    drv.reset()
    for inp, expected in NF4_VECTORS:
        result = drv.decode(70, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: NF4 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: NF4 QLoRA decode ({len(NF4_VECTORS)} vectors)")


def test_decode_fp6_e3m2(drv):
    drv.reset()
    for inp, expected in FP6_E3M2_VECTORS:
        result = drv.decode(40, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: FP6_E3M2 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: FP6 E3M2 decode ({len(FP6_E3M2_VECTORS)} vectors)")


def test_decode_fp6_e2m3(drv):
    drv.reset()
    for inp, expected in FP6_E2M3_VECTORS:
        result = drv.decode(77, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: FP6_E2M3 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: FP6 E2M3 decode ({len(FP6_E2M3_VECTORS)} vectors)")


def test_decode_e8m0(drv):
    drv.reset()
    for inp, expected in E8M0_VECTORS:
        result = drv.decode(78, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: E8M0 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: E8M0 decode ({len(E8M0_VECTORS)} vectors)")


def test_decode_mxint8(drv):
    drv.reset()
    for inp, expected in MXINT8_VECTORS:
        result = drv.decode(79, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: MXINT8 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: MXINT8 decode ({len(MXINT8_VECTORS)} vectors)")


def test_decode_e4m3_fnuz(drv):
    drv.reset()
    for inp, expected in E4M3_FNUZ_VECTORS:
        result = drv.decode(14, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: E4M3_FNUZ 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: E4M3 FNUZ decode ({len(E4M3_FNUZ_VECTORS)} vectors)")


def test_decode_int4(drv):
    drv.reset()
    for inp, expected in INT4_VECTORS:
        result = drv.decode(46, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: INT4 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: INT4 decode ({len(INT4_VECTORS)} vectors)")


def test_decode_bitnet(drv):
    drv.reset()
    for inp, expected in BITNET_VECTORS:
        result = drv.decode(71, [inp])
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: BitNet 0x{inp:02X}: expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: BitNet ternary decode ({len(BITNET_VECTORS)} vectors)")


def test_alias_mux_routing(drv):
    drv.reset()
    for fmt_id, data, expected, label in ALIAS_VECTORS:
        result = drv.decode(fmt_id, data)
        got = bytes_to_u32(result)
        assert got == expected, (
            f"FAIL: alias {label} (fmt_id={fmt_id}): "
            f"expected 0x{expected:08X}, got 0x{got:08X}"
        )
    print(f"PASS: alias mux routing ({len(ALIAS_VECTORS)} aliases)")


def test_not_implemented(drv):
    drv.reset()
    result = drv.decode(15, [0x42])
    assert result[0] == 0xFF, f"FAIL: not-implemented byte 0 = 0x{result[0]:02X}"
    assert result[3] == 0x4E, f"FAIL: not-implemented byte 3 = 0x{result[3]:02X} (expected 'N')"
    print("PASS: not-implemented response (format 15 = GoldenFloat, no decoder)")


ALL_TESTS = [
    test_anchor,
    test_anchor_stability,
    test_rom_self_index_sweep,
    test_rom_out_of_range,
    test_decode_fp8_e5m2,
    test_decode_bf16,
    test_decode_posit8,
    test_decode_int8,
    test_decode_tf32,
    test_decode_mxfp8_e4m3,
    test_decode_lns8,
    test_decode_bcd,
    test_decode_fp4,
    test_decode_nf4,
    test_decode_fp6_e3m2,
    test_decode_fp6_e2m3,
    test_decode_e8m0,
    test_decode_mxint8,
    test_decode_e4m3_fnuz,
    test_decode_int4,
    test_decode_bitnet,
    test_alias_mux_routing,
    test_not_implemented,
]


def run_all(tt=None):
    if tt is None:
        try:
            from ttboard.demoboard import DemoBoard
            tt = DemoBoard.get()
            tt.shuttle.tt_um_trinity_corona.enable()
        except ImportError:
            print("ERROR: ttboard not available. Run on the TT RP2350 demoboard.")
            return

    drv = CoronaDriver(tt)
    passed = 0
    failed = 0

    for test_fn in ALL_TESTS:
        try:
            test_fn(drv)
            passed += 1
        except AssertionError as e:
            print(f"  {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR in {test_fn.__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("ALL PASS")
    return failed == 0


def _ref_fp8_e5m2(v):
    s, e, m = (v >> 7) & 1, (v >> 2) & 0x1F, v & 0x3
    if e == 0x1F and m == 0:
        return (s << 31) | 0x7F800000
    if e == 0x1F:
        return (s << 31) | 0x7FC00000
    if e == 0 and m == 0:
        return s << 31
    if e == 0:
        if m & 2:
            return (s << 31) | (112 << 23) | ((m & 1) << 22)
        return (s << 31) | (111 << 23)
    return (s << 31) | ((e + 112) << 23) | (m << 21)


def _ref_mxfp8_e4m3(v):
    s, e, m = (v >> 7) & 1, (v >> 3) & 0xF, v & 0x7
    if e == 0xF and m == 0x7:
        return 0x7FC00000 if s == 0 else 0xFFC00000
    if e == 0 and m == 0:
        return 0x80000000 if s else 0x00000000
    if e == 0:
        if m & 4:
            return (s << 31) | (120 << 23) | ((m & 3) << 21)
        if m & 2:
            return (s << 31) | (119 << 23) | ((m & 1) << 22)
        return (s << 31) | (118 << 23)
    return (s << 31) | ((e + 120) << 23) | (m << 20)


def _ref_lns8(v):
    LUT = [256, 267, 279, 292, 304, 318, 332, 347,
           362, 378, 395, 412, 431, 450, 470, 490]
    if v == 0x00:
        return 0
    s = (v >> 7) & 1
    log = v & 0x7F
    mag = (LUT[log & 0xF] << ((log >> 4) & 0x7)) & 0xFFFF
    return (s << 31) | mag


def _ref_int8(v):
    if v & 0x80:
        return 0xFFFFFF00 | v
    return v


def _ref_e8m0(v):
    if v == 0xFF:
        return 0x7FC00000
    if v == 0x00:
        return 0x00400000
    return (v << 23) & 0x7FFFFFFF


def _ref_mxint8(v):
    if v == 0x00:
        return 0x00000000
    if v == 0x80:
        return 0x7FC00000
    signed = v if v < 128 else v - 256
    import struct
    f = signed / 64.0
    return struct.unpack('>I', struct.pack('>f', f))[0]


def _ref_e4m3_fnuz(v):
    v = v & 0xFF
    if v == 0x00:
        return 0x00000000
    if v == 0x80:
        return 0x7FC00000
    s, e, m = (v >> 7) & 1, (v >> 3) & 0xF, v & 0x7
    if e == 0:
        if m & 4:
            return (s << 31) | (119 << 23) | ((m & 3) << 21)
        if m & 2:
            return (s << 31) | (118 << 23) | ((m & 1) << 22)
        return (s << 31) | (117 << 23)
    return (s << 31) | ((e + 119) << 23) | (m << 20)


def _ref_bcd(v):
    return ((v >> 4) & 0xF) * 10 + (v & 0xF)


def _ref_fp6_e3m2(v):
    s, e, m = (v >> 5) & 1, (v >> 2) & 0x7, v & 0x3
    if e == 0 and m == 0:
        return s << 31
    if e == 0:
        if m & 2:
            return (s << 31) | (124 << 23) | ((m & 1) << 22)
        return (s << 31) | (123 << 23)
    return (s << 31) | ((e + 124) << 23) | (m << 21)


def _ref_fp6_e2m3(v):
    s, e, m = (v >> 5) & 1, (v >> 3) & 0x3, v & 0x7
    if e == 0 and m == 0:
        return s << 31
    if e == 0:
        if m & 4:
            return (s << 31) | (126 << 23) | ((m & 3) << 21)
        if m & 2:
            return (s << 31) | (125 << 23) | ((m & 1) << 22)
        return (s << 31) | (124 << 23)
    return (s << 31) | ((e + 126) << 23) | (m << 20)


def _ref_fp4(v):
    LUT = [0x00000000, 0x3F000000, 0x3F800000, 0x3FC00000,
           0x40000000, 0x40400000, 0x40800000, 0x40C00000,
           0x80000000, 0xBF000000, 0xBF800000, 0xBFC00000,
           0xC0000000, 0xC0400000, 0xC0800000, 0xC0C00000]
    return LUT[v & 0xF]


def _ref_nf4(v):
    LUT = [0xBF800000, 0xBF3239B1, 0xBF066B30, 0xBECA32A0,
           0xBE91A24D, 0xBE3D353F, 0xBDBA7871, 0x00000000,
           0x3DA2FAFF, 0x3E24CAE3, 0x3E7C04DD, 0x3EAD033A,
           0x3EE1A4B8, 0x3F1007AB, 0x3F3913B3, 0x3F800000]
    return LUT[v & 0xF]


def _ref_posit8(v):
    if v == 0x00:
        return 0x00000000
    if v == 0x80:
        return 0x7FC00000
    sign = (v >> 7) & 1
    abs_val = ((~v + 1) & 0x7F) if sign else (v & 0x7F)
    regime_sign = (abs_val >> 6) & 1
    inverted = (~abs_val & 0x7F) if regime_sign else (abs_val & 0x7F)
    lzc = 1
    for i in range(6, -1, -1):
        if (inverted >> i) & 1:
            lzc = 6 - i
            break
    else:
        lzc = 7
    if lzc == 0:
        lzc = 1
    k = (lzc - 1) if regime_sign else -lzc
    regime_total = lzc + 1 if lzc < 7 else lzc
    shifted = (abs_val << regime_total) & 0x7F
    fraction = (shifted >> 1) & 0x3F
    return (sign << 31) | ((k + 127) << 23) | (fraction << 17)


def _ref_int4(v):
    v = v & 0xF
    if v >= 8:
        return 0xFFFFFFF0 | v
    return v


def _ref_bitnet(v):
    return [0x00000000, 0x3F800000, 0xBF800000, 0x7FC00000][v & 0x3]


def _ref_bf16(val_16bit):
    return val_16bit << 16


def _ref_tf32(val_19bit):
    s = (val_19bit >> 18) & 1
    e = (val_19bit >> 10) & 0xFF
    m = val_19bit & 0x3FF
    return (s << 31) | (e << 23) | (m << 13)


EXHAUSTIVE_SWEEPS = [
    ("FP8_E5M2",    10, 256, _ref_fp8_e5m2),
    ("MXFP8_E4M3", 39, 256, _ref_mxfp8_e4m3),
    ("LNS8",        42, 256, _ref_lns8),
    ("INT8",        47, 256, _ref_int8),
    ("E8M0",        78, 256, _ref_e8m0),
    ("MXINT8",      79, 256, _ref_mxint8),
    ("E4M3_FNUZ",   14, 256, _ref_e4m3_fnuz),
    ("Posit8",      31, 256, _ref_posit8),
    ("FP4",         41,  16, _ref_fp4),
    ("NF4",         70,  16, _ref_nf4),
    ("FP6_E3M2",    40,  64, _ref_fp6_e3m2),
    ("FP6_E2M3",    77,  64, _ref_fp6_e2m3),
    ("INT4",        46,  16, _ref_int4),
    ("BitNet",      71,   4, _ref_bitnet),
    ("BCD_valid",   53, 100, None),
    ("BF16_full",    8,  0, None),
    ("TF32_sample",  9,  0, None),
]


def _sweep_bf16(drv):
    fails = 0
    for inp in range(65536):
        b0 = inp & 0xFF
        b1 = (inp >> 8) & 0xFF
        result = drv.decode(8, [b0, b1])
        got = bytes_to_u32(result)
        expected = _ref_bf16(inp)
        if got != expected:
            if fails < 3:
                print(f"  BF16 0x{inp:04X}: 0x{got:08X} != 0x{expected:08X}")
            fails += 1
    return fails, 65536


def _sweep_tf32(drv):
    fails = 0
    count = 0
    boundaries = list(range(16)) + list(range(0x7FF00, 0x80000))
    boundaries += [0x00000, 0x1FC00, 0x20000, 0x3FC00, 0x3FC01,
                   0x40000, 0x5FC00, 0x60000, 0x7FC00, 0x7FFFF]
    try:
        import random
        rng = random.Random(42)
        boundaries += [rng.randint(0, (1 << 19) - 1) for _ in range(1024)]
    except ImportError:
        for i in range(1024):
            boundaries.append((i * 511 + 137) & 0x7FFFF)
    seen = set()
    for val in boundaries:
        if val in seen:
            continue
        seen.add(val)
        b0 = val & 0xFF
        b1 = (val >> 8) & 0xFF
        b2 = (val >> 16) & 0xFF
        result = drv.decode(9, [b0, b1, b2])
        got = bytes_to_u32(result)
        expected = _ref_tf32(val)
        if got != expected:
            if fails < 3:
                print(f"  TF32 0x{val:05X}: 0x{got:08X} != 0x{expected:08X}")
            fails += 1
        count += 1
    return fails, count


def run_exhaustive(tt=None):
    if tt is None:
        try:
            from ttboard.demoboard import DemoBoard
            tt = DemoBoard.get()
            tt.shuttle.tt_um_trinity_corona.enable()
        except ImportError:
            print("ERROR: ttboard not available.")
            return

    drv = CoronaDriver(tt)
    total_pass = 0
    total_fail = 0

    for name, fmt_id, count, ref_fn in EXHAUSTIVE_SWEEPS:
        drv.reset()
        if name == "BCD_valid":
            fails = 0
            for tens in range(10):
                for ones in range(10):
                    bcd_in = (tens << 4) | ones
                    result = drv.decode(fmt_id, [bcd_in])
                    got = bytes_to_u32(result)
                    expected = _ref_bcd(bcd_in)
                    if got != expected:
                        print(f"  BCD 0x{bcd_in:02X}: 0x{got:08X} != 0x{expected:08X}")
                        fails += 1
        elif name == "BF16_full":
            fails, count = _sweep_bf16(drv)
        elif name == "TF32_sample":
            fails, count = _sweep_tf32(drv)
        else:
            fails = 0
            for inp in range(count):
                result = drv.decode(fmt_id, [inp])
                got = bytes_to_u32(result)
                expected = ref_fn(inp)
                if got != expected:
                    print(f"  {name} 0x{inp:02X}: 0x{got:08X} != 0x{expected:08X}")
                    fails += 1
        if fails == 0:
            print(f"PASS: {name} exhaustive ({count}/{count})")
            total_pass += 1
        else:
            print(f"FAIL: {name} exhaustive ({fails}/{count} failed)")
            total_fail += 1

    print(f"\n{'='*40}")
    print(f"Exhaustive: {total_pass} passed, {total_fail} failed, "
          f"{total_pass + total_fail} total")
    if total_fail == 0:
        print("ALL EXHAUSTIVE PASS")
    return total_fail == 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--exhaustive":
        run_exhaustive()
    else:
        run_all()
