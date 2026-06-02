#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_lut_published_values.py
#
# Loop 86: verify the LUT-based decoder ROMs in the RTL against EXTERNAL
# references, not just against the project's own cocotb reference models.
#
# The cocotb sweeps prove RTL == ref_model. But for the two opaque lookup-table
# decoders that is circular if the ref model's table were itself mis-transcribed:
# both copies would agree and pass. This test pins the *silicon* LUT to sources
# outside the repo:
#   * NF4 (nf4_decode.v): the 16 entries must equal the published QLoRA /
#     bitsandbytes NormalFloat4 quantiles (float32), bit-for-bit.
#   * FP4 (fp4_decode.v): the 16 entries must equal the OCP MX E2M1 values
#     computed here directly from the format definition (1 sign, 2 exp bias 1,
#     1 mantissa, subnormals), independent of any table.
#
# Parses the RTL case tables directly (the bytes that ship). Pure stdlib.
# Run: python3 test/test_lut_published_values.py
#
# Sources:
#   NF4:  Dettmers et al., "QLoRA", arXiv:2305.14314; values from bitsandbytes
#         functional.create_normal_map / get_4bit_type("nf4").
#   FP4:  OCP Microscaling Formats (MX) v1.0, E2M1 element type.

import os
import re
import struct
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
NF4_V = os.path.join(ROOT, "src", "rtl", "nf4_decode.v")
FP4_V = os.path.join(ROOT, "src", "rtl", "fp4_decode.v")


def f32_bits(x):
    """IEEE-754 float32 bit pattern (uint32) of a Python float."""
    return struct.unpack(">I", struct.pack(">f", x))[0]


def parse_lut(path):
    """Parse `4'hX: fp32_out = 32'hXXXXXXXX;` -> {index: uint32} (skip default)."""
    out = {}
    for idx, val in re.findall(
            r"4'h([0-9A-Fa-f])\s*:\s*fp32_out\s*=\s*32'h([0-9A-Fa-f]{1,8})",
            open(path).read()):
        out[int(idx, 16)] = int(val, 16)
    return out


# --- NF4: published QLoRA / bitsandbytes NormalFloat4 values (ascending) -------
QLORA_NF4 = [
    -1.0, -0.6961928009986877, -0.5250730514526367, -0.39491748809814453,
    -0.28444138169288635, -0.18477343022823334, -0.09105003625154495, 0.0,
    0.07958029955625534, 0.16093020141124725, 0.24611230194568634,
    0.33791524171829224, 0.44070982933044434, 0.5626170039176941,
    0.7229568362236023, 1.0,
]


def fp4_e2m1_reference():
    """Compute the 16 OCP MX E2M1 values from the format definition.
    1 sign, 2 exp (bias 1), 1 mantissa; e=0 subnormal, no Inf/NaN."""
    vals = {}
    for code in range(16):
        sign = (code >> 3) & 1
        exp = (code >> 1) & 0x3
        mant = code & 1
        if exp == 0:
            mag = (mant / 2.0)              # 2^(1-1) * (m/2) = m*0.5
        else:
            mag = (2.0 ** (exp - 1)) * (1.0 + mant / 2.0)
        x = -mag if sign else mag
        # -0.0 must keep its sign bit (code 0x8)
        bits = f32_bits(x)
        if sign and x == 0.0:
            bits |= 0x80000000
        vals[code] = bits
    return vals


def main():
    errors = []

    def check(cond, msg):
        print(("PASS: " if cond else "FAIL: ") + msg)
        if not cond:
            errors.append(msg)

    # --- NF4 structural provenance: asymmetric 7 negative / 0.0 / 8 positive
    # (create_normal_map(offset=0.9677083, use_extra_value=True) -- QLoRA).
    n_neg = sum(1 for v in QLORA_NF4 if v < 0)
    n_zero = sum(1 for v in QLORA_NF4 if v == 0.0)
    n_pos = sum(1 for v in QLORA_NF4 if v > 0)
    check((n_neg, n_zero, n_pos) == (7, 1, 8),
          f"NF4 asymmetric layout 7-/0/8+ (got {n_neg}-/{n_zero}0/{n_pos}+)")

    # --- NF4 RTL LUT vs published QLoRA float32 ---------------------------
    nf4 = parse_lut(NF4_V)
    check(len(nf4) == 16, f"parsed 16 NF4 RTL entries (got {len(nf4)})")
    nf4_bad = 0
    for i in range(16):
        want = f32_bits(QLORA_NF4[i])
        got = nf4.get(i)
        if got != want:
            nf4_bad += 1
            print(f"    NF4 idx {i:X}: RTL=0x{(got or 0):08X} "
                  f"published=0x{want:08X} ({QLORA_NF4[i]})")
    check(nf4_bad == 0, "NF4 RTL LUT == published QLoRA float32 (16/16 bit-exact)")

    # --- FP4 RTL LUT vs computed OCP MX E2M1 ------------------------------
    fp4 = parse_lut(FP4_V)
    check(len(fp4) == 16, f"parsed 16 FP4 RTL entries (got {len(fp4)})")
    ref = fp4_e2m1_reference()
    fp4_bad = 0
    for i in range(16):
        if fp4.get(i) != ref[i]:
            fp4_bad += 1
            print(f"    FP4 idx {i:X}: RTL=0x{(fp4.get(i) or 0):08X} "
                  f"E2M1=0x{ref[i]:08X}")
    check(fp4_bad == 0, "FP4 RTL LUT == computed OCP MX E2M1 (16/16 bit-exact)")

    print("\n" + "=" * 60)
    if errors:
        print(f"LUT published-value check: {len(errors)} FAILURE(S)")
        return 1
    print("ALL PASS: NF4 (QLoRA) and FP4 (OCP E2M1) RTL LUTs match external refs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
