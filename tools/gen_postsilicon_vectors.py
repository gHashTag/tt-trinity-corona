#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# tools/gen_postsilicon_vectors.py
#
# Loop 101: GENERATE the post-silicon bring-up vectors from the independent
# reference models, so they cannot be wrong-by-transcription. Loop 92 found 5
# hand-written FP8_E5M2 vectors that were wrong and would have failed a correct
# chip; generating them from the (RTL-validated, Loops 86-90) references removes
# that bug class structurally. Emits post_silicon/corona_vectors.py; a freshness
# gate (test/test_postsilicon_vectors_fresh.py) keeps the committed file in sync.
#
# Self-contained: imports only the reference modules (no test_corona), so there is
# no import cycle (test_corona imports the generated corona_vectors).
# Run: python3 tools/gen_postsilicon_vectors.py

import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "test"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import test_float_decoders_independent as flt    # noqa: E402
import test_posit8_independent as p8             # noqa: E402
import test_lns8_independent as lns              # noqa: E402
import test_simple_decoders_independent as simp  # noqa: E402
import test_lut_published_values as lut          # noqa: E402

_FP4 = lut.fp4_e2m1_reference()


def chip_output(fmt, data):
    """Expected full-chip 32-bit output (independent reference + top-module
    assembly). A second, independent copy of this mapping lives in
    test_post_silicon_vectors.py; the two cross-check via the generated tables."""
    if fmt == "e5m2":
        return flt.ref_e5m2(data[0])
    if fmt == "bf16":
        return flt.ref_bf16((data[1] << 8) | data[0])
    if fmt == "posit8":
        return p8.posit8_ref(data[0])
    if fmt == "int8":
        return simp.ref("int8", data[0])[0]
    if fmt == "tf32":
        return flt.ref_tf32(data[0] | (data[1] << 8) | (data[2] << 16))
    if fmt == "mxfp8":
        return flt.ref_e4m3(data[0])
    if fmt == "lns8":
        s, mag, _z = lns.lns8_ref(data[0])
        return (s << 31) | mag
    if fmt == "bcd":
        return simp.ref("bcd", data[0])[0]
    if fmt == "fp4":
        return _FP4[data[0] & 0xF]
    if fmt == "nf4":
        return lut.f32_bits(lut.QLORA_NF4[data[0] & 0xF])
    if fmt == "fp6_e3m2":
        return flt.ref_fp6_e3m2(data[0])
    if fmt == "fp6_e2m3":
        return flt.ref_fp6_e2m3(data[0])
    if fmt == "e8m0":
        return simp.ref("e8m0", data[0])[0]
    if fmt == "mxint8":
        return simp.ref("mxint8", data[0])[0]
    if fmt == "fnuz":
        return flt.ref_e4m3_fnuz(data[0])
    if fmt == "int4":
        return simp.ref("int4", data[0])[0]
    if fmt == "bitnet":
        return simp.ref("bitnet", data[0])[0]
    raise KeyError(fmt)


# Curated representative input codes per format (specials, 1.0, max, min-subnormal,
# reserved, etc.), and the emitted variable name. Single-byte unless noted.
VARNAME = {
    "e5m2": "FP8_E5M2_VECTORS", "bf16": "BF16_VECTORS", "posit8": "POSIT8_VECTORS",
    "int8": "INT8_VECTORS", "tf32": "TF32_VECTORS", "mxfp8": "MXFP8_E4M3_VECTORS",
    "lns8": "LNS8_VECTORS", "bcd": "BCD_VECTORS", "fp4": "FP4_E2M1_VECTORS",
    "nf4": "NF4_VECTORS", "fp6_e3m2": "FP6_E3M2_VECTORS", "fp6_e2m3": "FP6_E2M3_VECTORS",
    "e8m0": "E8M0_VECTORS", "mxint8": "MXINT8_VECTORS", "fnuz": "E4M3_FNUZ_VECTORS",
    "int4": "INT4_VECTORS", "bitnet": "BITNET_VECTORS",
}
ORDER = ["e5m2", "bf16", "posit8", "int8", "tf32", "mxfp8", "lns8", "bcd", "fp4",
         "nf4", "fp6_e3m2", "fp6_e2m3", "e8m0", "mxint8", "fnuz", "int4", "bitnet"]
MULTIBYTE = {"bf16", "tf32"}
INPUTS = {
    "e5m2": [0x00, 0x80, 0x7B, 0xFB, 0x7C, 0xFC, 0x7D, 0x01, 0x3C],
    "bf16": [[0x00, 0x3F], [0x80, 0x3F], [0x00, 0x40], [0x00, 0x00], [0x00, 0x80], [0x80, 0x7F]],
    "posit8": [0x00, 0x40, 0xC0],
    "int8": [0x00, 0x01, 0x7F, 0xFF, 0x80],
    "tf32": [[0, 0, 0], [0, 0, 4], [0, 0xFC, 1], [0, 0, 2], [0, 0xFC, 3]],
    "mxfp8": [0x00, 0x80, 0x38, 0x01, 0x7F, 0xFF],
    "lns8": [0x00, 0x10, 0x01, 0x80, 0x7F],
    "bcd": [0x00, 0x01, 0x42, 0x99, 0x10],
    "fp4": [0x00, 0x02, 0x08, 0x0A, 0x0F],
    "nf4": [0x00, 0x07, 0x0F, 0x08, 0x01],
    "fp6_e3m2": [0x00, 0x20, 0x08, 0x3F, 0x01],
    "fp6_e2m3": [0x00, 0x20, 0x08, 0x1F, 0x01],
    "e8m0": [0x00, 0x7F, 0x01, 0xFE, 0xFF],
    "mxint8": [0x00, 0x01, 0x40, 0x7F, 0x80, 0xFF],
    "fnuz": [0x00, 0x80, 0x38, 0x01, 0x7F],
    "int4": [0x00, 0x01, 0x07, 0x08, 0x0F],
    "bitnet": [0x00, 0x01, 0x02, 0x03],
}
# alias fmt_id -> (canonical reference label, input bytes, human label)
ALIASES = [
    (11, "mxfp8", [0x38], "FP8_E4M3 -> MXFP8"),
    (12, "fp6_e3m2", [0x08], "FP6_E3M2_ML -> FP6_E3M2"),
    (13, "fp4", [0x02], "FP4_ML -> FP4"),
    (69, "fnuz", [0x38], "E4M3_FNUZ_ALT -> FNUZ"),
    (75, "nf4", [0x07], "NF4_BNB -> NF4"),
]


def _fmt_in(fmt, inp):
    if fmt in MULTIBYTE:
        return "[" + ", ".join(f"0x{b:02X}" for b in inp) + "]"
    return f"0x{inp:02X}"


def main():
    L = ["# SPDX-License-Identifier: Apache-2.0",
         "# post_silicon/corona_vectors.py",
         "# AUTO-GENERATED by tools/gen_postsilicon_vectors.py -- DO NOT EDIT BY HAND",
         "# Bring-up (input -> expected fp32) vectors, computed from the independent",
         "# reference models so they cannot be wrong-by-transcription (Loop 92/101).",
         ""]
    for fmt in ORDER:
        L.append(f"{VARNAME[fmt]} = [")
        for inp in INPUTS[fmt]:
            data = inp if fmt in MULTIBYTE else [inp]
            exp = chip_output(fmt, data)
            L.append(f"    ({_fmt_in(fmt, inp)}, 0x{exp:08X}),")
        L.append("]")
        L.append("")
    L.append("ALIAS_VECTORS = [")
    for fmt_id, label, data, human in ALIASES:
        exp = chip_output(label, data)
        ins = "[" + ", ".join(f"0x{b:02X}" for b in data) + "]"
        L.append(f"    ({fmt_id}, {ins}, 0x{exp:08X}, {human!r}),")
    L.append("]")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    out = main()
    dest = os.path.join(ROOT, "post_silicon", "corona_vectors.py")
    with open(dest, "w") as f:
        f.write(out)
    print(f"Generated {dest} ({len(out)} bytes)")
