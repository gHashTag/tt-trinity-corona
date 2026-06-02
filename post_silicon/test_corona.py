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
