#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_float_decoders_independent.py
#
# Loop 90: pin the last 7 decoders -- the IEEE/OCP-style float formats -- to
# independent references and the actual RTL (iverilog), completing 17/17 unique
# decoders verified against an oracle OUTSIDE their own cocotb reference model.
#
# Two independent derivation styles, neither copied from the cocotb ref models:
#   * Definitional (the format IS a view of fp32): bf16 = bits << 16;
#     tf32 = repack sign|exp|mant into fp32 fields. NaN/Inf payloads pass through.
#   * Value-based: compute the exact REAL number the code represents, then let
#     struct emit its IEEE-754 float32 bits -- a different method than the RTL's
#     exponent-bias + mantissa-shift. Specials handled per each spec.
#       fp8_e5m2   : 1s 5e 2m, bias 15, IEEE-style (Inf at e=31,m=0; NaN m!=0).
#       mxfp8_e4m3 : 1s 4e 3m, bias 7, OCP (no Inf; NaN only at e=15,m=7).
#       fp6_e3m2   : 1s 3e 2m, bias 3, no Inf/NaN.
#       fp6_e2m3   : 1s 2e 3m, bias 1, no Inf/NaN.
#
# Each module is compiled with iverilog and swept exhaustively (590,464 values
# total, incl. full 2^19 tf32 -- broader than the cocotb 1024-sample tf32 test).
# Skips gracefully (rc=0) if iverilog/vvp absent. Run: python3 test/test_float_decoders_independent.py

import os
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
QNAN = 0x7FC00000


def f32(x):
    return struct.unpack(">I", struct.pack(">f", x))[0]


def ref_bf16(b):
    return (b << 16) & 0xFFFFFFFF


def ref_tf32(b):
    s = (b >> 18) & 1
    e = (b >> 10) & 0xFF
    m = b & 0x3FF
    return (s << 31) | (e << 23) | (m << 13)


def ref_e5m2(b):
    s, e, m = b >> 7, (b >> 2) & 0x1F, b & 3
    if e == 0x1F:
        return (s << 31) | (0x7F800000 if m == 0 else QNAN)
    if e == 0 and m == 0:
        return s << 31
    val = (2.0 ** -14) * (m / 4) if e == 0 else (2.0 ** (e - 15)) * (1 + m / 4)
    return f32(-val if s else val)


def ref_e4m3(b):
    s, e, m = b >> 7, (b >> 3) & 0xF, b & 7
    if e == 0xF and m == 7:
        return (s << 31) | QNAN
    if e == 0 and m == 0:
        return s << 31
    val = (2.0 ** -6) * (m / 8) if e == 0 else (2.0 ** (e - 7)) * (1 + m / 8)
    return f32(-val if s else val)


def ref_fp6_e3m2(b):
    s, e, m = (b >> 5) & 1, (b >> 2) & 7, b & 3
    if e == 0 and m == 0:
        return s << 31
    val = (2.0 ** -2) * (m / 4) if e == 0 else (2.0 ** (e - 3)) * (1 + m / 4)
    return f32(-val if s else val)


def ref_fp6_e2m3(b):
    s, e, m = (b >> 5) & 1, (b >> 3) & 3, b & 7
    if e == 0 and m == 0:
        return s << 31
    val = (m / 8) if e == 0 else (2.0 ** (e - 1)) * (1 + m / 8)
    return f32(-val if s else val)


def ref_e4m3_fnuz(b):
    # AMD/Graphcore E4M3FNUZ: bias 8, no Inf, 0x80 is the sole NaN, no -0.
    if b == 0x00:
        return 0x00000000
    if b == 0x80:
        return QNAN
    s, e, m = b >> 7, (b >> 3) & 0xF, b & 7
    val = (2.0 ** (1 - 8)) * (m / 8) if e == 0 else (2.0 ** (e - 8)) * (1 + m / 8)
    return f32(-val if s else val)


# mod -> (width, instantiation, port decl, reference)
DECODERS = {
    "bf16":       (16, ".bf16_in(in), .fp32_out(o), .is_zero(z), .is_inf(inf), .is_nan(nan)",
                   "wire [31:0] o; wire z, inf, nan;", ref_bf16),
    "tf32":       (19, ".tf32_in(in), .fp32_out(o), .is_zero(z), .is_inf(inf), .is_nan(nan)",
                   "wire [31:0] o; wire z, inf, nan;", ref_tf32),
    "fp8_e5m2":   (8,  ".e5m2_in(in), .fp32_out(o), .is_zero(z), .is_inf(inf), .is_nan(nan)",
                   "wire [31:0] o; wire z, inf, nan;", ref_e5m2),
    "mxfp8_e4m3": (8,  ".e4m3_in(in), .fp32_out(o), .is_zero(z), .is_nan(nan)",
                   "wire [31:0] o; wire z, nan;", ref_e4m3),
    "fp8_e4m3_fnuz": (8, ".e4m3_in(in), .fp32_out(o), .is_zero(z), .is_nan(nan)",
                      "wire [31:0] o; wire z, nan;", ref_e4m3_fnuz),
    "fp6_e3m2":   (6,  ".fp6_in(in), .fp32_out(o)",
                   "wire [31:0] o;", ref_fp6_e3m2),
    "fp6_e2m3":   (6,  ".fp6_in(in), .fp32_out(o), .is_zero(z)",
                   "wire [31:0] o; wire z;", ref_fp6_e2m3),
}


def build_tb(mod, width, inst, decl):
    n = 1 << width
    return (f"`timescale 1ns/1ps\n"
            f"module tb; reg [{width - 1}:0] in; {decl}\n"
            f" {mod}_decode dut({inst}); integer i;\n"
            f" initial begin for (i=0;i<{n};i=i+1) begin in=i[{width - 1}:0]; #1; "
            f'$display("%0d %08h", i, o); end $finish; end\nendmodule\n')


def main():
    iverilog, vvp = shutil.which("iverilog"), shutil.which("vvp")
    if not iverilog or not vvp:
        assert ref_bf16(0x7F80) == 0x7F800000          # +Inf
        assert ref_e5m2(0x7C) == 0x7F800000            # +Inf
        assert ref_e4m3(0x7F) == QNAN                  # NaN, no Inf in e4m3
        assert ref_fp6_e2m3(0b001000) == 0x3F800000    # 1.0
        print("SKIP: iverilog/vvp not found (CI installs them); reference spot-checks OK.")
        return 0

    errors = []
    total = 0
    for mod, (width, inst, decl, fn) in DECODERS.items():
        with tempfile.TemporaryDirectory() as d:
            tbf = os.path.join(d, "tb.v")
            with open(tbf, "w") as f:
                f.write(build_tb(mod, width, inst, decl))
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
                if len(parts) < 2 or not parts[0].isdigit():
                    continue
                i, got = int(parts[0]), int(parts[1], 16)
                cnt += 1
                if got != fn(i):
                    mism += 1
                    if mism <= 5:
                        print(f"  {mod} 0x{i:X}: RTL=0x{got:08X} ref=0x{fn(i):08X}")
            total += cnt
            ok = (mism == 0 and cnt == (1 << width))
            print(("PASS: " if ok else "FAIL: ") +
                  f"{mod}_decode {cnt}/{1 << width} match independent ref")
            if not ok:
                errors.append(mod)

    print("\n" + "=" * 60)
    if errors:
        print(f"float decoders independent check: FAIL ({', '.join(errors)})")
        return 1
    print(f"ALL PASS: {len(DECODERS)} float decoders, {total} values, all match "
          f"independent refs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
