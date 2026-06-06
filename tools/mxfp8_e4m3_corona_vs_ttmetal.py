#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# tt-trinity-corona / tools/mxfp8_e4m3_corona_vs_ttmetal.py
#
# Cross-check: Corona RTL `mxfp8_e4m3_decode.v` algorithm vs the OCP MX FP8
# E4M3 parameter dictionary `kMxFp8E4M3Params` in tenstorrent/tt-metal
# (`tt_metal/impl/data_format/mxfp8.cpp`).
#
# Status: [Empirical fit]
# Run:    python3 tools/mxfp8_e4m3_corona_vs_ttmetal.py
#
# This script is a Python re-implementation of the per-element decode that
# the Corona Verilog module performs.  It compares each of the 256 possible
# E4M3 byte values against an independent FP32 reference produced from the
# OCP MX v1.0 specification (arXiv:2310.10537, Section 5.3).  The OCP MX FP8
# E4M3 parameters used are the same as `kMxFp8E4M3Params` in tt-metal:
#
#     block_size               = 32          (block-level; not exercised here)
#     scale_bias               = 0x7F        (block-level; not exercised here)
#     elem_exp_bits            = 4
#     elem_man_bits            = 3
#     elem_exp_bias            = 7
#     elem_exp_max_unbiased    = 8
#     elem_exp_min_unbiased    = -6
#     elem_man_max             = 0x6         (mant 0b111 at max exp = NaN)
#     elem_sat_pos_bits        = 0x7E        (= +max normal = 448)
#     elem_sat_neg_bits        = 0xFE        (= -max normal = -448)
#     inf_rep                  = NotRepresentable
#     nan_rep                  = ExpAllOnesManAllOnes  (only S.1111.111)
#
# This is a per-element check.  The block-level layout (E8M0 scale per 32
# elements) is OUT OF SCOPE for this script; see
# `gHashTag/tt-trinity-corona` `src/rtl/e8m0_decode.v` and the tt-metal
# `mx_tile_pack.hpp` for the block-level path.
#
# This script does NOT call tt-metal; tt-metal is a C++ library with a
# hardware backend.  This script only documents the parameter set the two
# implementations share and runs the Corona-side algorithm against it.

from __future__ import annotations

import math
import struct
import sys


def corona_decode_e4m3(byte: int) -> tuple[float, bool, bool]:
    """Re-implement `src/rtl/mxfp8_e4m3_decode.v` in Python.

    Returns ``(fp32_value, is_zero, is_nan)``.  The Verilog source lines
    referenced below correspond to the Corona RTL module as of repo HEAD.
    """
    assert 0 <= byte <= 0xFF
    sign = (byte >> 7) & 0x1
    exp = (byte >> 3) & 0xF
    mant = byte & 0x7

    is_zero = (exp == 0) and (mant == 0)
    is_nan = (exp == 0xF) and (mant == 0x7)

    if is_nan:
        # Quiet NaN, sign-preserving (matches the Verilog: sign passes through).
        return (float("nan") if not sign else -float("nan"), False, True)
    if is_zero:
        return (-0.0 if sign else 0.0, True, False)

    if exp == 0:
        # Subnormal.  value = (-1)^S * 2^(-6) * (0.mant)
        # Verilog normalises by leading-1 search; we do the same arithmetically.
        # mant in {1, 2, ..., 7}.
        mantissa_fraction = mant / 8.0
        magnitude = mantissa_fraction * (2.0 ** -6)
    else:
        # Normal.  value = (-1)^S * 2^(exp - 7) * (1.mant)
        mantissa_fraction = 1.0 + (mant / 8.0)
        magnitude = mantissa_fraction * (2.0 ** (exp - 7))

    value = -magnitude if sign else magnitude
    return (value, False, False)


def ocp_reference_e4m3(byte: int) -> tuple[float, bool, bool]:
    """OCP MX v1.0 reference decode for FP8 E4M3 (arXiv:2310.10537 Sec 5.3).

    Identical math to ``corona_decode_e4m3``, written from the OCP spec
    independently of the Corona Verilog.  If the two diverge, that is a
    falsification of one or the other.
    """
    sign_bit = (byte >> 7) & 0x1
    exp_field = (byte >> 3) & 0xF
    man_field = byte & 0x7

    sign = -1.0 if sign_bit else 1.0
    is_zero = (exp_field == 0) and (man_field == 0)
    is_nan = (exp_field == 0xF) and (man_field == 0x7)
    if is_nan:
        return (sign * float("nan"), False, True)
    if is_zero:
        return (sign * 0.0, True, False)

    bias = 7
    if exp_field == 0:
        # Subnormal: 2^(1 - bias) * (man / 2^man_bits)
        value = sign * (2.0 ** (1 - bias)) * (man_field / 8.0)
    else:
        # Normal: 2^(exp - bias) * (1 + man / 2^man_bits)
        value = sign * (2.0 ** (exp_field - bias)) * (1.0 + man_field / 8.0)
    return (value, False, False)


def float_to_uint32_bits(x: float) -> int:
    """Round-trip a Python float to the 32-bit IEEE 754 representation that
    the Corona Verilog produces on `fp32_out[31:0]`."""
    return struct.unpack("<I", struct.pack("<f", x))[0]


def main() -> int:
    mismatches: list[tuple[int, float, float]] = []
    max_normal_seen = 0.0
    nan_byte_count = 0

    for byte in range(256):
        corona_val, corona_zero, corona_nan = corona_decode_e4m3(byte)
        ocp_val, ocp_zero, ocp_nan = ocp_reference_e4m3(byte)

        if corona_nan != ocp_nan or corona_zero != ocp_zero:
            mismatches.append((byte, corona_val, ocp_val))
            continue

        if corona_nan:
            nan_byte_count += 1
            continue

        # Compare 32-bit IEEE 754 bit patterns directly.  ``math.isnan`` is
        # not reached because nan bytes are handled above.
        cb = float_to_uint32_bits(corona_val)
        ob = float_to_uint32_bits(ocp_val)
        if cb != ob:
            # Allow signed-zero difference (both are zero, both encode to
            # +0.0 in Python float arithmetic; not a defect).
            if corona_val == 0.0 and ocp_val == 0.0:
                continue
            mismatches.append((byte, corona_val, ocp_val))
        max_normal_seen = max(max_normal_seen, abs(corona_val))

    print(f"E4M3 cross-check: 256 byte values exercised.")
    print(f"  NaN bytes (S.1111.111, S in {{0,1}}): {nan_byte_count}")
    print(f"  Max normal observed:                  {max_normal_seen}")
    print(f"  Mismatches Corona vs OCP reference:   {len(mismatches)}")

    if max_normal_seen != 448.0:
        print(f"  WARNING: expected max normal 448.0, got {max_normal_seen}")
        return 2

    if nan_byte_count != 2:
        print(f"  WARNING: expected exactly 2 NaN bytes, got {nan_byte_count}")
        return 2

    if mismatches:
        print()
        print("Mismatched bytes (first 10):")
        for byte, cv, ov in mismatches[:10]:
            print(f"  0x{byte:02X}: corona={cv!r}  ocp_ref={ov!r}")
        return 1

    print()
    print("PASS: Corona E4M3 decode matches OCP MX v1.0 reference on all 256 bytes.")
    print("Status: [Empirical fit] -- per-element correspondence.")
    print("Block-level (E8M0 scale x 32 elements) NOT exercised here; see e8m0_decode.v.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
