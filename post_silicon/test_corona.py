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


FP8_E5M2_VECTORS = [
    (0x00, 0x00000000),  # +0
    (0x80, 0x80000000),  # -0
    (0x7E, 0x477F0000),  # max normal (57344.0)
    (0xFE, 0xC77F0000),  # -max normal
    (0x7F, 0x7F800000),  # +Inf
    (0xFF, 0xFF800000),  # -Inf
    (0x01, 0x33800000),  # min subnormal
    (0x3C, 0x3F800000),  # 1.0
]

BF16_VECTORS = [
    ([0x00, 0x3F], 0x3F000000),  # 0.5
    ([0x80, 0x3F], 0x3F800000),  # 1.0
    ([0x00, 0x40], 0x40000000),  # 2.0
    ([0x00, 0x00], 0x00000000),  # +0
    ([0x00, 0x80], 0x80000000),  # -0
    ([0x80, 0x7F], 0x7F800000),  # +Inf
]

POSIT8_VECTORS = [
    (0x00, 0x00000000),  # zero
    (0x40, 0x3F800000),  # 1.0
    (0xC0, 0xBF800000),  # -1.0
]

INT8_VECTORS = [
    (0x00, 0x00000000),  # 0
    (0x01, 0x00000001),  # 1
    (0x7F, 0x0000007F),  # 127
    (0xFF, 0xFFFFFFFF),  # -1
    (0x80, 0xFFFFFF80),  # -128
]

TF32_VECTORS = [
    ([0x00, 0x00, 0x00], 0x00000000),  # +0
    ([0x00, 0x00, 0x04], 0x80000000),  # -0
    ([0x00, 0xFC, 0x01], 0x3F800000),  # 1.0
    ([0x00, 0x00, 0x02], 0x40000000),  # 2.0
    ([0x00, 0xFC, 0x03], 0x7F800000),  # +Inf
]

MXFP8_E4M3_VECTORS = [
    (0x00, 0x00000000),  # +0
    (0x80, 0x80000000),  # -0
    (0x38, 0x3F800000),  # 1.0
    (0x01, 0x3B000000),  # min subnormal
    (0x7F, 0x7FC00000),  # NaN
    (0xFF, 0xFFC00000),  # -NaN
]

LNS8_VECTORS = [
    (0x00, 0x00000000),  # zero
    (0x10, 0x00000200),  # log=1.0, mag=512
    (0x01, 0x0000010B),  # log=0.0625, mag=267
    (0x80, 0x80000100),  # negative, mag=256
    (0x7F, 0x0000F500),  # max positive
]

BCD_VECTORS = [
    (0x00, 0x00000000),  # 0
    (0x01, 0x00000001),  # 1
    (0x42, 0x0000002A),  # 42
    (0x99, 0x00000063),  # 99
    (0x10, 0x0000000A),  # 10
]

FP4_E2M1_VECTORS = [
    (0x00, 0x00000000),  # +0
    (0x02, 0x3F800000),  # 1.0
    (0x08, 0x80000000),  # -0
    (0x0A, 0xBF800000),  # -1.0
    (0x0F, 0xC0C00000),  # -6.0
]

NF4_VECTORS = [
    (0x00, 0xBF800000),  # -1.0
    (0x07, 0x00000000),  # 0
    (0x0F, 0x3F800000),  # 1.0
    (0x08, 0x3DA2FAFF),  # ~0.0796
    (0x01, 0xBF3239B1),  # ~-0.6962
]

FP6_E3M2_VECTORS = [
    (0x00, 0x00000000),  # +0
    (0x20, 0x80000000),  # -0
    (0x08, 0x3F000000),  # 0.5
    (0x3F, 0xC1E00000),  # -28.0
    (0x01, 0x3D800000),  # min subnormal
]

FP6_E2M3_VECTORS = [
    (0x00, 0x00000000),  # +0
    (0x20, 0x80000000),  # -0
    (0x08, 0x3F800000),  # 1.0
    (0x1F, 0x40F00000),  # 7.5
    (0x01, 0x3E000000),  # min subnormal
]

E8M0_VECTORS = [
    (0x00, 0x00400000),  # 2^(-127) subnormal
    (0x7F, 0x3F800000),  # 2^0 = 1.0
    (0x01, 0x00800000),  # 2^(-126)
    (0xFE, 0x7F000000),  # 2^127
    (0xFF, 0x7FC00000),  # NaN
]

MXINT8_VECTORS = [
    (0x00, 0x00000000),  # 0
    (0x01, 0x3C800000),  # 1/64
    (0x40, 0x3F800000),  # 64/64 = 1.0
    (0x7F, 0x3FFE0000),  # 127/64
    (0x80, 0x7FC00000),  # reserved -> NaN
    (0xFF, 0xBC800000),  # -1/64
]

E4M3_FNUZ_VECTORS = [
    (0x00, 0x00000000),  # +0
    (0x80, 0x7FC00000),  # NaN
    (0x38, 0x3F000000),  # 0.5 (bias=8)
    (0x01, 0x3A800000),  # min subnormal
    (0x7F, 0x43700000),  # max normal
]

INT4_VECTORS = [
    (0x00, 0x00000000),  # 0
    (0x01, 0x00000001),  # 1
    (0x07, 0x00000007),  # 7
    (0x08, 0xFFFFFFF8),  # -8
    (0x0F, 0xFFFFFFFF),  # -1
]

BITNET_VECTORS = [
    (0x00, 0x00000000),  # 0
    (0x01, 0x3F800000),  # +1.0
    (0x02, 0xBF800000),  # -1.0
    (0x03, 0x7FC00000),  # NaN (unused)
]


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


ALIAS_VECTORS = [
    (11, [0x38], 0x3F800000, "FP8_E4M3 -> MXFP8"),
    (12, [0x08], 0x3F000000, "FP6_E3M2_ML -> FP6_E3M2"),
    (13, [0x02], 0x3F800000, "FP4_ML -> FP4"),
    (69, [0x38], 0x3F000000, "E4M3_FNUZ_ALT -> FNUZ"),
    (75, [0x07], 0x00000000, "NF4_BNB -> NF4"),
]


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


if __name__ == "__main__":
    run_all()
