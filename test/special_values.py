# SPDX-License-Identifier: Apache-2.0
# test/special_values.py -- explicit, citation-backed special-value conformance
# vectors for the Tier-1 float decoders.
#
# Loop 78 motivation: every float decoder's special-value behaviour (NaN, Inf,
# signed zero, subnormal boundary, max-finite, reserved sentinels) was, until
# now, tested only IMPLICITLY as part of the 256-value exhaustive sweeps. For a
# chip whose entire purpose is to be a *format-conformance oracle*, those rules
# deserve to be asserted EXPLICITLY and traceably to the governing spec.
#
# This module is import-safe without cocotb so it can be run standalone:
#     python3 test/special_values.py
# It re-derives each expected FP32 from the same reference math used by the
# cocotb sweeps in test_decoders.py and fails loudly on any mismatch. The cocotb
# test `test_special_values_conformance` (test_decoders.py) drives every vector
# below through the DUT and checks the hardware against the same table.
#
# Spec sources (verified Loop 78 research):
#   [OFP8]  OCP 8-bit Floating Point Specification (OFP8) Rev 1.0, 2023-12.
#   [MX]    OCP Microscaling Formats (MX) v1.0, 2023; arXiv:2310.10537.
#   [FP8]   Micikevicius et al., "FP8 Formats for Deep Learning",
#           arXiv:2209.05433 (E4M3 has NO Inf, single NaN bit-pattern per sign;
#           E5M2 is IEEE-style with Inf+NaN).
#   [FNUZ]  AMD CDNA3 / Graphcore E4M3FNUZ: bias=8, 0x80 is the SOLE NaN, and
#           there is NO negative zero (that code point is NaN).
#
# Status tags per repo discipline:
#   [Verified in sim] -- asserted against RTL in cocotb; confirmed on silicon TBD.

# fmt_id assignments (must match test_decoders.py / ROM catalog ordering).
FMT_BF16       = 8
FMT_FP8_E5M2   = 10
FMT_E4M3_FNUZ  = 14
FMT_MXFP8_E4M3 = 39
FMT_E8M0       = 78
FMT_MXINT8     = 79

QNAN_POS = 0x7FC00000
QNAN_NEG = 0xFFC00000

# Each vector: (fmt_name, fmt_id, input_bytes_LSB_first, expected_fp32, klass, note)
#   klass is one of: NaN, Inf, Zero, Subnormal, MaxFinite, Boundary, Normal
SPECIAL_VALUE_VECTORS = [
    # --- E8M0 shared scale [MX] -----------------------------------------------
    # 0xFF is the SOLE NaN sentinel; a naive 2^(e-127) would wrongly yield 2^128.
    ("E8M0",  FMT_E8M0,  [0xFF], QNAN_POS,    "NaN",       "0xFF reserved NaN sentinel [MX]"),
    # 0xFE must stay FINITE (2^127) -- the boundary just below the sentinel.
    ("E8M0",  FMT_E8M0,  [0xFE], 0x7F000000,  "Boundary",  "0xFE -> 2^127 finite, NOT NaN [MX]"),
    # 0x00 is the minimum scale 2^(-127), an FP32 subnormal (not zero).
    ("E8M0",  FMT_E8M0,  [0x00], 0x00400000,  "Subnormal", "0x00 -> 2^-127 subnormal [MX]"),
    ("E8M0",  FMT_E8M0,  [0x7F], 0x3F800000,  "Normal",    "0x7F -> 2^0 = 1.0 [MX]"),

    # --- FP8 E4M3 FNUZ [FNUZ] -------------------------------------------------
    # 0x80 is the ONLY NaN; there is NO -0 in this format.
    ("E4M3FNUZ", FMT_E4M3_FNUZ, [0x80], QNAN_POS,   "NaN",  "0x80 sole NaN, no -0 [FNUZ]"),
    ("E4M3FNUZ", FMT_E4M3_FNUZ, [0x00], 0x00000000, "Zero", "0x00 +0, the only zero [FNUZ]"),

    # --- FP8 E5M2 (IEEE-style) [OFP8][FP8] ------------------------------------
    ("FP8_E5M2", FMT_FP8_E5M2, [0x7C], 0x7F800000, "Inf",       "0x7C +Inf [OFP8]"),
    ("FP8_E5M2", FMT_FP8_E5M2, [0xFC], 0xFF800000, "Inf",       "0xFC -Inf [OFP8]"),
    ("FP8_E5M2", FMT_FP8_E5M2, [0x7D], QNAN_POS,   "NaN",       "0x7D NaN (exp=0x1F, mant!=0) [OFP8]"),
    ("FP8_E5M2", FMT_FP8_E5M2, [0x80], 0x80000000, "Zero",      "0x80 -0.0 [OFP8]"),
    ("FP8_E5M2", FMT_FP8_E5M2, [0x01], 0x37800000, "Subnormal", "0x01 smallest subnormal 2^-16 [OFP8]"),

    # --- MXFP8 E4M3 (OCP, no Inf) [OFP8][FP8] ---------------------------------
    # E4M3 has NO infinities; NaN = S.1111.111 -> TWO NaN bit patterns.
    ("MXFP8_E4M3", FMT_MXFP8_E4M3, [0x7F], QNAN_POS,   "NaN",       "0x7F +NaN (no Inf in E4M3) [OFP8]"),
    ("MXFP8_E4M3", FMT_MXFP8_E4M3, [0xFF], QNAN_NEG,   "NaN",       "0xFF -NaN (second NaN pattern) [OFP8]"),
    ("MXFP8_E4M3", FMT_MXFP8_E4M3, [0x7E], 0x43E00000, "MaxFinite", "0x7E max finite = 448.0 [OFP8]"),
    ("MXFP8_E4M3", FMT_MXFP8_E4M3, [0x78], 0x43800000, "Normal",    "0x78 -> 256.0 finite, NOT Inf [OFP8]"),
    ("MXFP8_E4M3", FMT_MXFP8_E4M3, [0x80], 0x80000000, "Zero",      "0x80 -0.0 (E4M3 keeps -0) [OFP8]"),

    # --- MXINT8 (reserved code) [MX] ------------------------------------------
    ("MXINT8", FMT_MXINT8, [0x80], QNAN_POS,   "NaN",  "0x80 (-128) reserved -> NaN [MX]"),
    ("MXINT8", FMT_MXINT8, [0x00], 0x00000000, "Zero", "0x00 +0 [MX]"),

    # --- BF16 (IEEE truncation) -----------------------------------------------
    ("BF16", FMT_BF16, [0x80, 0x7F], 0x7F800000, "Inf",  "0x7F80 +Inf"),
    ("BF16", FMT_BF16, [0x80, 0xFF], 0xFF800000, "Inf",  "0xFF80 -Inf"),
    ("BF16", FMT_BF16, [0xC0, 0x7F], 0x7FC00000, "NaN",  "0x7FC0 quiet NaN"),
    ("BF16", FMT_BF16, [0x00, 0x80], 0x80000000, "Zero", "0x8000 -0.0"),
]


# ---------------------------------------------------------------------------
# Standalone reference math (copies of the golden models in test_decoders.py).
# Kept here so this module is runnable without cocotb installed.
# ---------------------------------------------------------------------------

def _ref_e8m0(val):
    if val == 0xFF:
        return 0x7FC00000
    if val == 0x00:
        return 0x00400000
    return (val << 23) & 0x7FFFFFFF


def _ref_fp8_e4m3_fnuz(val):
    val &= 0xFF
    if val == 0x00:
        return 0x00000000
    if val == 0x80:
        return 0x7FC00000
    sign = (val >> 7) & 1
    exp = (val >> 3) & 0xF
    mant = val & 0x7
    if exp == 0:
        if mant & 0x4:
            fp32_exp, fp32_mant = 119, (mant & 0x3) << 21
        elif mant & 0x2:
            fp32_exp, fp32_mant = 118, (mant & 0x1) << 22
        else:
            fp32_exp, fp32_mant = 117, 0
    else:
        fp32_exp, fp32_mant = exp + 119, mant << 20
    return (sign << 31) | (fp32_exp << 23) | fp32_mant


def _ref_fp8_e5m2(byte_val):
    sign = (byte_val >> 7) & 1
    exp = (byte_val >> 2) & 0x1F
    mant = byte_val & 0x3
    if exp == 0x1F and mant == 0:
        return (sign << 31) | 0x7F800000
    if exp == 0x1F and mant != 0:
        return (sign << 31) | 0x7FC00000
    if exp == 0 and mant == 0:
        return sign << 31
    if exp == 0:
        if mant & 2:
            fp32_exp, fp32_mant = 112, (mant & 1) << 22
        else:
            fp32_exp, fp32_mant = 111, 0
        return (sign << 31) | (fp32_exp << 23) | fp32_mant
    return (sign << 31) | ((exp + 112) << 23) | (mant << 21)


def _ref_mxfp8_e4m3(byte_val):
    sign = (byte_val >> 7) & 1
    exp = (byte_val >> 3) & 0xF
    mant = byte_val & 0x7
    if exp == 0xF and mant == 0x7:
        return 0x7FC00000 if sign == 0 else 0xFFC00000
    if exp == 0 and mant == 0:
        return 0x80000000 if sign else 0x00000000
    if exp == 0:
        if mant & 4:
            fp32_exp, fp32_mant = 120, (mant & 3) << 21
        elif mant & 2:
            fp32_exp, fp32_mant = 119, (mant & 1) << 22
        else:
            fp32_exp, fp32_mant = 118, 0
        return (sign << 31) | (fp32_exp << 23) | fp32_mant
    return (sign << 31) | ((exp + 120) << 23) | (mant << 20)


def _ref_mxint8(val):
    import struct
    if val == 0x00:
        return 0x00000000
    if val == 0x80:
        return 0x7FC00000
    signed_val = val if val < 128 else val - 256
    return struct.unpack('>I', struct.pack('>f', signed_val / 64.0))[0]


def _ref_bf16(b):  # b = LSB-first bytes
    return (b[0] | (b[1] << 8)) << 16


_DISPATCH = {
    FMT_E8M0:       lambda b: _ref_e8m0(b[0]),
    FMT_E4M3_FNUZ:  lambda b: _ref_fp8_e4m3_fnuz(b[0]),
    FMT_FP8_E5M2:   lambda b: _ref_fp8_e5m2(b[0]),
    FMT_MXFP8_E4M3: lambda b: _ref_mxfp8_e4m3(b[0]),
    FMT_MXINT8:     lambda b: _ref_mxint8(b[0]),
    FMT_BF16:       _ref_bf16,
}


def verify_against_reference():
    """Cross-check every declared expected FP32 against the golden reference
    math. Returns (n_checked, failures:list[str])."""
    failures = []
    for name, fmt_id, ins, expected, klass, note in SPECIAL_VALUE_VECTORS:
        ref = _DISPATCH[fmt_id](ins)
        if ref != expected:
            failures.append(
                f"{name} {note}: table=0x{expected:08X} but ref=0x{ref:08X}")
    return len(SPECIAL_VALUE_VECTORS), failures


if __name__ == "__main__":
    n, failures = verify_against_reference()
    by_class = {}
    for *_, klass, _note in SPECIAL_VALUE_VECTORS:
        by_class[klass] = by_class.get(klass, 0) + 1
    print(f"Special-value conformance vectors: {n}")
    print("  by class: " + ", ".join(f"{k}={v}" for k, v in sorted(by_class.items())))
    if failures:
        print(f"FAIL: {len(failures)} vectors disagree with reference math:")
        for f in failures:
            print("  - " + f)
        raise SystemExit(1)
    print("PASS: all vectors agree with golden reference math.")
