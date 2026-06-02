#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_posit8_independent.py
#
# Loop 87: verify the Posit8(es=0) decoder against a from-scratch reference, and
# against the *actual RTL* simulated with iverilog -- not the project's own cocotb
# reference model. Posit regime decoding is the most error-prone decode in the
# chip (variable-length regime + terminator + fraction), so "RTL == our refmodel"
# is the weakest link: a regime-extraction bug shared by both would pass.
#
# This test:
#   * implements posit8(es=0) -> FP32 independently, by STRING-parsing the regime
#     run / terminator / fraction from the bit layout (a different method than the
#     RTL's casez priority encoder + barrel shift, and not copied from ref_posit8);
#   * compiles src/rtl/posit8_decode.v with iverilog and sweeps all 256 inputs;
#   * asserts the silicon output equals the independent reference for 256/256.
#
# Posit8(es=0): useed = 2^(2^0) = 2; value = (-1)^S * 2^k * (1 + fraction).
# Specials: 0x00 -> +0.0; 0x80 -> NaR, which this RTL maps to FP32 qNaN 0x7FC00000.
# Ref: Posit Standard (2022); Gustafson & Yonemoto, "Beating Floating Point...",
#      Supercomputing Frontiers 2017.
#
# Skips gracefully (rc=0) if iverilog/vvp are absent; CI installs them.
# Run: python3 test/test_posit8_independent.py

import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
POSIT_V = os.path.join(ROOT, "src", "rtl", "posit8_decode.v")
TB_V = os.path.join(ROOT, "test", "tb_posit8_sweep.v")

QNAN = 0x7FC00000

# Decoder this test pins (read by test_independent_oracle_coverage.py).
COVERED = frozenset({"posit8"})


def posit8_ref(p):
    """Independent posit8(es=0) -> FP32 bit pattern, matching the RTL's truncated
    construction {sign, k+127, frac6, 17'b0}. Derived from the posit bit layout by
    string parsing -- intentionally not the RTL's algorithm and not ref_posit8."""
    p &= 0xFF
    if p == 0x00:
        return 0x00000000
    if p == 0x80:
        return QNAN  # NaR
    sign = p >> 7
    # Negative posits: two's-complement the whole 8-bit word, decode, reapply sign.
    mag = p if not sign else ((~p + 1) & 0xFF)
    bits = format(mag & 0x7F, "07b")          # 7-bit magnitude, MSB (bit6) first
    r0 = bits[0]
    run = 1
    while run < 7 and bits[run] == r0:
        run += 1
    k = run - 1 if r0 == "1" else -run        # regime value
    consumed = run + (1 if run < 7 else 0)     # regime run + terminator bit
    frac6 = (bits[consumed:] + "000000")[:6]   # fraction MSB-aligned, 6 bits kept
    fraction = int(frac6, 2)
    exp = (k + 127) & 0xFF
    return (sign << 31) | (exp << 23) | (fraction << 17)


def run_rtl_sweep():
    """Compile + run the RTL sweep; return {index: fp32_uint32} or None if no tools."""
    iverilog = shutil.which("iverilog")
    vvp = shutil.which("vvp")
    if not iverilog or not vvp:
        return None
    with tempfile.TemporaryDirectory() as d:
        binp = os.path.join(d, "p8")
        c = subprocess.run([iverilog, "-g2012", "-o", binp, POSIT_V, TB_V],
                           capture_output=True, text=True)
        if c.returncode != 0:
            print("FAIL: iverilog compile error:\n" + c.stderr)
            return False
        r = subprocess.run([vvp, binp], capture_output=True, text=True)
        out = {}
        for line in r.stdout.splitlines():
            m = re.match(r"^\s*(\d+)\s+([0-9A-Fa-f]{8})\s*$", line)
            if m:
                out[int(m.group(1))] = int(m.group(2), 16)
        return out


def main():
    rtl = run_rtl_sweep()
    if rtl is None:
        print("SKIP: iverilog/vvp not found (CI installs them); reference still "
              "self-checks below.")
        # Still sanity-check the reference on the well-known specials.
        assert posit8_ref(0x00) == 0x00000000
        assert posit8_ref(0x80) == QNAN
        assert posit8_ref(0x40) == 0x3F800000  # +1.0 (regime 0, k=0)
        print("PASS: reference specials (0x00->+0, 0x80->NaR, 0x40->1.0)")
        return 0
    if rtl is False:
        return 1

    if len(rtl) != 256:
        print(f"FAIL: RTL sweep produced {len(rtl)} values, expected 256")
        return 1

    mism = 0
    for i in range(256):
        want = posit8_ref(i)
        got = rtl[i]
        if want != got:
            mism += 1
            if mism <= 10:
                print(f"  posit 0x{i:02X}: RTL=0x{got:08X} independent=0x{want:08X}")
    if mism:
        print(f"\nFAIL: posit8 RTL vs independent reference: {mism}/256 mismatch")
        return 1
    print("PASS: posit8_decode RTL == independent Posit-Standard reference (256/256)")
    print("\n" + "=" * 60)
    print("ALL PASS: Posit8(es=0) silicon matches a from-scratch reference")
    return 0


if __name__ == "__main__":
    sys.exit(main())
