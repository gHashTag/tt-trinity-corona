#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_simple_decoders_independent.py
#
# Loop 89: pin the remaining ALGORITHMIC decoders to closed-form references and
# the actual RTL (iverilog), so NO decoder is verified only against its own
# cocotb reference model. After posit8 (Loop 87) and lns8 (Loop 88), these six
# are simple enough that their definitions ARE the reference:
#
#   int4   : two's-complement 4-bit -> sign-extended int32
#   int8   : two's-complement 8-bit -> sign-extended int32
#   bcd    : packed 2-digit BCD -> tens*10 + ones (7-bit); valid if both nibbles <=9
#   bitnet : ternary 2-bit -> {0, +1.0, -1.0, NaN(reserved 0b11)}
#   e8m0   : 2^(e-127); 0x00 -> 2^-127 subnormal; 0xFF -> NaN
#   mxint8 : signed int8 * 2^-6 as float32; 0x80 (-128) reserved -> NaN
#
# For each, a tiny TB is generated, compiled with the module via iverilog, swept
# exhaustively, and every output compared to the closed-form reference computed
# here. 1044 input values total. Skips gracefully (rc=0) if iverilog/vvp absent.
# Run: python3 test/test_simple_decoders_independent.py

import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
QNAN = 0x7FC00000


def f32(x):
    return struct.unpack(">I", struct.pack(">f", x))[0]


def i32(x):
    return struct.unpack(">I", struct.pack(">i", x))[0]


# (verilog_width, port-decl, instantiation, $display args, n_extra_flag_cols)
DECODERS = {
    "int4":   (4, "wire [31:0] o; wire z;",
               ".int4_in(in), .int32_out(o), .is_zero(z)",
               '"%0d %08h %0d", i, o, z', "hex"),
    "int8":   (8, "wire [31:0] o; wire z;",
               ".int8_in(in), .int32_out(o), .is_zero(z)",
               '"%0d %08h %0d", i, o, z', "hex"),
    "bcd":    (8, "wire [6:0] o; wire v;",
               ".bcd_in(in), .bin_out(o), .valid(v)",
               '"%0d %0d %0d", i, o, v', "dec"),
    "bitnet": (2, "wire [31:0] o; wire z, r;",
               ".ternary_in(in), .fp32_out(o), .is_zero(z), .is_reserved(r)",
               '"%0d %08h %0d %0d", i, o, z, r', "hex2"),
    "e8m0":   (8, "wire [31:0] o; wire nan;",
               ".e8m0_in(in), .fp32_out(o), .is_nan(nan)",
               '"%0d %08h %0d", i, o, nan', "hex"),
    "mxint8": (8, "wire [31:0] o; wire z, r;",
               ".mxint8_in(in), .fp32_out(o), .is_zero(z), .is_reserved(r)",
               '"%0d %08h %0d %0d", i, o, z, r', "hex2"),
}


# Decoders this test pins (read by test_independent_oracle_coverage.py).
COVERED = frozenset(DECODERS)


def ref(mod, i):
    if mod == "int4":
        v = i - 16 if i >= 8 else i
        return (i32(v), 1 if i == 0 else 0)
    if mod == "int8":
        v = i - 256 if i >= 128 else i
        return (i32(v), 1 if i == 0 else 0)
    if mod == "bcd":
        t, o = i >> 4, i & 0xF
        return ((t * 10 + o) & 0x7F, 1 if (t <= 9 and o <= 9) else 0)
    if mod == "bitnet":
        val = {0: 0x0, 1: 0x3F800000, 2: 0xBF800000, 3: QNAN}[i]
        return (val, 1 if i == 0 else 0, 1 if i == 3 else 0)
    if mod == "e8m0":
        if i == 0xFF:
            return (QNAN, 1)
        if i == 0x00:
            return (0x00400000, 0)        # 2^-127 subnormal
        return ((i << 23) & 0x7FFFFFFF, 0)
    if mod == "mxint8":
        if i == 0x00:
            return (0x0, 1, 0)
        if i == 0x80:
            return (QNAN, 0, 1)
        v = i - 256 if i >= 128 else i
        return (f32(v / 64.0), 0, 0)
    raise KeyError(mod)


def build_tb(mod, cfg):
    width, decl, inst, disp, _ = cfg
    n = 1 << width
    return (f"`timescale 1ns/1ps\n"
            f"module tb; reg [{width - 1}:0] in; {decl}\n"
            f" {mod}_decode dut({inst}); integer i;\n"
            f" initial begin for (i=0;i<{n};i=i+1) begin in=i[{width - 1}:0]; #1; "
            f"$display({disp}); end $finish; end\nendmodule\n")


def parse_line(kind, parts):
    i = int(parts[0])
    if kind == "hex":
        return i, (int(parts[1], 16), int(parts[2]))
    if kind == "dec":
        return i, (int(parts[1]), int(parts[2]))
    if kind == "hex2":
        return i, (int(parts[1], 16), int(parts[2]), int(parts[3]))


def main():
    iverilog, vvp = shutil.which("iverilog"), shutil.which("vvp")
    if not iverilog or not vvp:
        # Pure-Python sanity of a few references so the test isn't a no-op.
        assert ref("int8", 0xFF) == (i32(-1), 0)
        assert ref("e8m0", 0xFF) == (QNAN, 1)
        assert ref("mxint8", 0x01) == (0x3C800000, 0, 0)  # 1/64 = 2^-6
        print("SKIP: iverilog/vvp not found (CI installs them); reference spot-checks OK.")
        return 0

    errors = []
    total = 0
    for mod, cfg in DECODERS.items():
        width, _decl, _inst, _disp, kind = cfg
        with tempfile.TemporaryDirectory() as d:
            tbf = os.path.join(d, "tb.v")
            with open(tbf, "w") as f:
                f.write(build_tb(mod, cfg))
            binp = os.path.join(d, "a.out")
            c = subprocess.run(
                [iverilog, "-g2012", "-o", binp,
                 os.path.join(ROOT, "src", "rtl", f"{mod}_decode.v"), tbf],
                capture_output=True, text=True)
            if c.returncode != 0:
                print(f"FAIL: {mod} iverilog compile:\n{c.stderr}")
                errors.append(mod)
                continue
            r = subprocess.run([vvp, binp], capture_output=True, text=True)
            mism = 0
            cnt = 0
            for line in r.stdout.splitlines():
                parts = line.split()
                if not parts or not parts[0].isdigit():
                    continue
                idx, got = parse_line(kind, parts)
                cnt += 1
                if got != ref(mod, idx):
                    mism += 1
                    if mism <= 5:
                        print(f"  {mod} 0x{idx:X}: RTL={got} ref={ref(mod, idx)}")
            total += cnt
            ok = (mism == 0 and cnt == (1 << width))
            print(("PASS: " if ok else "FAIL: ") +
                  f"{mod}_decode {cnt}/{1 << width} match closed-form ref")
            if not ok:
                errors.append(mod)

    print("\n" + "=" * 60)
    if errors:
        print(f"simple decoders independent check: FAIL ({', '.join(errors)})")
        return 1
    print(f"ALL PASS: {len(DECODERS)} decoders, {total} values, all match closed-form refs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
