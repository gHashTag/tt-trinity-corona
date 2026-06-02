#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_lns8_independent.py
#
# Loop 88: verify the LNS8 (8-bit logarithmic) decoder against a from-scratch
# reference and against the actual RTL simulated with iverilog -- not the
# project's own cocotb reference model. LNS8 is the second non-obvious decode
# (after posit8): a base-2 logarithm, so the magnitude is an antilog (2^x), and
# the 16-entry fractional LUT of 2^(i/16) is exactly the kind of constant table
# that can be mis-rounded in both the RTL and a hand-written ref model.
#
# Encoding (per lns8_decode.v): 1 sign bit + 7-bit Q3.4 logarithm.
#   int_part = log[6:4] (octave), frac = log[3:0] (LUT index).
#   magnitude (Q8.8) = round(256 * 2^(frac/16)) << int_part.
#   lns_in == 0x00 -> zero. sign = bit7 (pass-through).
#
# This test:
#   * recomputes the 16 antilog LUT entries as round(256 * 2^(i/16)) and asserts
#     the RTL's case table matches them exactly (external math vs the constants);
#   * compiles lns8_decode.v with iverilog, sweeps all 256 inputs, and asserts
#     (sign, magnitude, is_zero) equals the independent reference for 256/256.
#
# Skips gracefully (rc=0) if iverilog/vvp are absent; CI installs them.
# Run: python3 test/test_lns8_independent.py
#
# Ref: logarithmic number systems; antilog table = 2^(frac/16) in Q0.8.

import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LNS_V = os.path.join(ROOT, "src", "rtl", "lns8_decode.v")
TB_V = os.path.join(ROOT, "test", "tb_lns8_sweep.v")

# Decoder this test pins (read by test_independent_oracle_coverage.py).
COVERED = frozenset({"lns8"})


def antilog_lut(i):
    """Independent: 2^(i/16) in Q0.8 (256 = 1.0), round-half-up."""
    return int(math.floor(256.0 * (2.0 ** (i / 16.0)) + 0.5))


def lns8_ref(b):
    """Independent (sign, magnitude_Q8.8, is_zero) for an LNS8 byte."""
    sign = b >> 7
    is_zero = 1 if b == 0 else 0
    log_val = b & 0x7F
    int_part = (log_val >> 4) & 0x7
    frac = log_val & 0xF
    mag = 0 if is_zero else (antilog_lut(frac) << int_part) & 0xFFFF
    return sign, mag, is_zero


def parse_rtl_lut(path):
    """Parse `4'dN: frac_lut = 9'dV;` (and 4'hN) -> {i: V}."""
    out = {}
    for idx, val in re.findall(
            r"4'[dh]([0-9A-Fa-f]+)\s*:\s*frac_lut\s*=\s*9'd(\d+)", open(path).read()):
        out[int(idx, 16) if not idx.isdigit() else int(idx)] = int(val)
    return out


def run_rtl_sweep():
    iverilog, vvp = shutil.which("iverilog"), shutil.which("vvp")
    if not iverilog or not vvp:
        return None
    with tempfile.TemporaryDirectory() as d:
        binp = os.path.join(d, "lns8")
        c = subprocess.run([iverilog, "-g2012", "-o", binp, LNS_V, TB_V],
                           capture_output=True, text=True)
        if c.returncode != 0:
            print("FAIL: iverilog compile error:\n" + c.stderr)
            return False
        r = subprocess.run([vvp, binp], capture_output=True, text=True)
        out = {}
        for line in r.stdout.splitlines():
            m = re.match(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", line)
            if m:
                idx, s, mag, iz = (int(x) for x in m.groups())
                out[idx] = (s, mag, iz)
        return out


def main():
    errors = []

    def check(cond, msg):
        print(("PASS: " if cond else "FAIL: ") + msg)
        if not cond:
            errors.append(msg)

    # --- LUT constants vs independent antilog math ---------------------------
    rtl_lut = parse_rtl_lut(LNS_V)
    check(len(rtl_lut) == 16, f"parsed 16 RTL antilog LUT entries (got {len(rtl_lut)})")
    lut_bad = 0
    for i in range(16):
        want = antilog_lut(i)
        if rtl_lut.get(i) != want:
            lut_bad += 1
            print(f"    LUT[{i}]: RTL={rtl_lut.get(i)} round(256*2^({i}/16))={want}")
    check(lut_bad == 0, "RTL antilog LUT == round(256*2^(i/16)) for all 16 entries")

    # --- Full RTL sweep vs independent reference -----------------------------
    rtl = run_rtl_sweep()
    if rtl is None:
        print("SKIP: iverilog/vvp not found (CI installs them); LUT math verified above.")
        return 1 if errors else 0
    if rtl is False:
        return 1
    if len(rtl) != 256:
        print(f"FAIL: RTL sweep produced {len(rtl)} values, expected 256")
        return 1
    mism = 0
    for i in range(256):
        if lns8_ref(i) != rtl[i]:
            mism += 1
            if mism <= 10:
                print(f"  lns 0x{i:02X}: RTL={rtl[i]} independent={lns8_ref(i)}")
    check(mism == 0, "lns8_decode RTL == independent reference (256/256)")

    print("\n" + "=" * 60)
    if errors:
        print(f"LNS8 independent check: {len(errors)} FAILURE(S)")
        return 1
    print("ALL PASS: LNS8 silicon matches a from-scratch antilog reference")
    return 0


if __name__ == "__main__":
    sys.exit(main())
