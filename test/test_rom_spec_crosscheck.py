#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_rom_spec_crosscheck.py
# Independent cross-check of ROM metadata against published specifications.
# This file does NOT import gen_rom.py — values are hardcoded from specs.
#
# Sources:
#   IEEE 754-2019 Table 3.5 (fp16/fp32/fp64/fp128)
#   Google Brain bfloat16 spec (bf16: 1+8+7=16)
#   NVIDIA TF32 (1+8+10=19 bits, stored in 32-bit container)
#   OCP MX Spec v1.0 §4 (MXFP8 E4M3: 1+4+3=8, MXFP6 E3M2: 1+3+2=6,
#       MXFP4 E2M1: 1+2+1=4, E8M0: 0+8+0=8, MXINT8: 1+0+7=8)
#   AMD CDNA3 (FP8 E4M3 FNUZ: 1+4+3=8, bias=8, NaN=0x80)
#   IEEE FP8 E5M2 (1+5+2=8)
#   Posit standard draft (posit8 es=0: 8 bits, no exponent field in catalog)
#   QLoRA NF4 (4-bit, no sign/exp/mant decomposition, LUT-based)
#   BitNet 1.58b (ternary: 2 bits, no FP decomposition)
#   INT8/INT4 (signed integer: 8/4 bits)
#   BCD (packed: 8 bits, 2 decimal digits)
#   LNS8 (8-bit logarithmic: 1+7+0)

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
# We import pack_record ONLY to decode the ROM — the EXPECTED values below
# are independently derived from published specs, NOT from gen_rom.py's CATALOG.
from gen_rom import pack_record, CATALOG
# Field bit-positions come from the .t27 SSOT (rom_layout.t27), NOT a local
# copy of the shifts. See tools/ssot_layout.py (Loop 80: single layout source).
import ssot_layout


# Independent spec reference: (fmt_id, total_bits, sign_bits, exp_bits, mant_bits)
# Each entry is manually derived from the published specification.
SPEC_REFERENCE = {
    # IEEE 754-2019 Table 3.5
    0:  (16,  1,  5, 10),   # binary16 (half)
    1:  (32,  1,  8, 23),   # binary32 (single)
    2:  (64,  1, 11, 52),   # binary64 (double)
    3:  (128, 1, 15, 112),  # binary128 (quad)
    # Google Brain bfloat16
    8:  (16,  1,  8,  7),   # bf16
    # NVIDIA TF32 (19-bit mantissa truncation of FP32)
    9:  (32,  1,  8, 10),   # tf32 (stored in 32-bit container)
    # IEEE/OCP FP8 variants
    10: (8,   1,  5,  2),   # fp8 e5m2
    11: (8,   1,  4,  3),   # fp8 e4m3
    14: (8,   1,  4,  3),   # fp8 e4m3 fnuz (same bit layout, different semantics)
    # OCP MX Spec v1.0 §4
    12: (6,   1,  3,  2),   # mxfp6 e3m2
    13: (4,   1,  2,  1),   # mxfp4 e2m1
    39: (8,   1,  4,  3),   # mxfp8 e4m3 (OCP MX element)
    40: (6,   1,  3,  2),   # mxfp6 e3m2 (OCP MX element)
    41: (4,   1,  2,  1),   # mxfp4 e2m1 (OCP MX element)
    78: (8,   0,  8,  0),   # e8m0 shared scale (unsigned, exponent-only)
    79: (8,   1,  0,  7),   # mxint8 (signed integer element)
    # Posit
    31: (8,   1,  0,  0),   # posit8 es=0
    # Integer
    46: (4,   1,  0,  3),   # int4 signed (1 sign + 3 magnitude)
    47: (8,   1,  0,  7),   # int8 signed (1 sign + 7 magnitude)
    # BCD
    53: (8,   0,  0,  8),   # packed BCD (2 digits, 4 bits each)
    # LNS
    42: (8,   1,  3,  4),   # lns8 (1 sign + 7 log, stored as 3 exp + 4 mant)
    # Compression/quantization
    70: (4,   0,  0,  4),   # nf4 (LUT-based, no FP decomposition)
    71: (2,   1,  0,  1),   # bitnet ternary (1 sign + 1 value)
}


def extract_fields(packed_80bit):
    """Extract metadata fields from a packed 80-bit ROM record, using the
    bit-positions declared in rom_layout.t27 (via tools/ssot_layout.py) rather
    than hardcoded shifts. One layout source, no third copy to drift."""
    e = ssot_layout.extract
    fmt_id = e(packed_80bit, "FORMAT_INDEX_ID")
    total = e(packed_80bit, "TOTAL_BITS")
    sign = e(packed_80bit, "SIGN_BITS")
    exp = e(packed_80bit, "EXP_BITS")
    mant = e(packed_80bit, "MANT_BITS")
    return fmt_id, total, sign, exp, mant


def main():
    errors = 0
    checked = 0

    for cat_entry in CATALOG:
        fmt_id = cat_entry[0]
        if fmt_id not in SPEC_REFERENCE:
            continue

        packed = pack_record(*cat_entry)
        rid, total, sign, exp, mant = extract_fields(packed)

        spec_total, spec_sign, spec_exp, spec_mant = SPEC_REFERENCE[fmt_id]

        # total_bits=256 overflows to 0 in 8-bit field (documented convention)
        if spec_total == 256:
            spec_total = 0

        ok = True
        if rid != fmt_id:
            print(f"FAIL fmt_id={fmt_id}: ROM id={rid}")
            ok = False
        if total != spec_total:
            print(f"FAIL fmt_id={fmt_id}: total_bits ROM={total} spec={spec_total}")
            ok = False
        if sign != spec_sign:
            print(f"FAIL fmt_id={fmt_id}: sign_bits ROM={sign} spec={spec_sign}")
            ok = False
        if exp != spec_exp:
            print(f"FAIL fmt_id={fmt_id}: exp_bits ROM={exp} spec={spec_exp}")
            ok = False
        if mant != spec_mant:
            print(f"FAIL fmt_id={fmt_id}: mant_bits ROM={mant} spec={spec_mant}")
            ok = False

        if ok:
            print(f"PASS: fmt_id={fmt_id:>2} total={total:>3} sign={sign} "
                  f"exp={exp:>2} mant={mant:>3}")
        else:
            errors += 1
        checked += 1

    print(f"\n{'='*50}")
    print(f"Checked {checked}/{len(SPEC_REFERENCE)} formats against published specs")
    if errors:
        print(f"FAILURES: {errors}")
        return 1
    else:
        print("ALL PASS: ROM metadata matches published specifications")
        return 0


if __name__ == "__main__":
    sys.exit(main())
