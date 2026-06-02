#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_post_silicon_vectors.py
#
# Loop 92: validate the POST-SILICON bring-up oracle against the verified model.
#
# post_silicon/test_corona.py carries hardcoded (input -> expected fp32) vectors
# for every on-die decoder. That table is THE oracle that will declare the
# physical chip good or bad on the RP2350 demoboard (~Nov 2026). It was
# hand-written separately from the RTL, so it can drift -- and it had: 5 of the 8
# FP8_E5M2 vectors were wrong (exp=31 codes labelled max-normal/Inf instead of
# NaN, and a mis-scaled subnormal), which would have FAILED a perfectly correct
# chip during bring-up. This test pins every post-silicon vector to the
# independent references built in Loops 86-90 (which were checked against the
# actual RTL via iverilog), applying the top-module output assembly:
#   lns8  -> {sign, 15'b0, magnitude}
#   bcd   -> {25'b0, bin7}
#   int4/int8 -> sign-extended int32
#   others -> the decoder's fp32 directly.
#
# Pure stdlib (imports the reference modules; no iverilog). Run:
#   python3 test/test_post_silicon_vectors.py

import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "test"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "post_silicon"))

import test_corona as ps                       # noqa: E402  (bring-up suite)
import test_float_decoders_independent as flt  # noqa: E402
import test_posit8_independent as p8           # noqa: E402
import test_lns8_independent as lns            # noqa: E402
import test_simple_decoders_independent as simp  # noqa: E402
import test_lut_published_values as lut        # noqa: E402

_FP4 = lut.fp4_e2m1_reference()


def _read(path):
    with open(path, errors="replace") as f:
        return f.read()


def independent_chip_output(fmt, data):
    """Expected full-chip 32-bit output, from the independent references."""
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
        return (s << 31) | mag               # top-module: {sign, 15'b0, mag}
    if fmt == "bcd":
        return simp.ref("bcd", data[0])[0]   # {25'b0, bin7}
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


# (label, vector table, single-byte input?, fmt_id)
TABLES = [
    ("e5m2",     ps.FP8_E5M2_VECTORS,   True,  10),
    ("bf16",     ps.BF16_VECTORS,       False, 8),
    ("posit8",   ps.POSIT8_VECTORS,     True,  31),
    ("int8",     ps.INT8_VECTORS,       True,  47),
    ("tf32",     ps.TF32_VECTORS,       False, 9),
    ("mxfp8",    ps.MXFP8_E4M3_VECTORS, True,  39),
    ("lns8",     ps.LNS8_VECTORS,       True,  42),
    ("bcd",      ps.BCD_VECTORS,        True,  53),
    ("fp4",      ps.FP4_E2M1_VECTORS,   True,  41),
    ("nf4",      ps.NF4_VECTORS,        True,  70),
    ("fp6_e3m2", ps.FP6_E3M2_VECTORS,   True,  40),
    ("fp6_e2m3", ps.FP6_E2M3_VECTORS,   True,  77),
    ("e8m0",     ps.E8M0_VECTORS,       True,  78),
    ("mxint8",   ps.MXINT8_VECTORS,     True,  79),
    ("fnuz",     ps.E4M3_FNUZ_VECTORS,  True,  14),
    ("int4",     ps.INT4_VECTORS,       True,  46),
    ("bitnet",   ps.BITNET_VECTORS,     True,  71),
]

# Alias fmt_ids route to a canonical decoder; map each to the reference label.
ALIAS_REF = {11: "mxfp8", 12: "fp6_e3m2", 13: "fp4", 69: "fnuz", 75: "nf4"}


def main():
    errors = []
    total = 0

    def check(cond, msg):
        print(("PASS: " if cond else "FAIL: ") + msg)
        if not cond:
            errors.append(msg)

    for name, table, single, _fmt in TABLES:
        bad = 0
        for inp, expected in table:
            data = [inp] if single else inp
            ref = independent_chip_output(name, data)
            total += 1
            if ref != expected:
                bad += 1
                ins = f"0x{inp:02X}" if single else str(inp)
                print(f"  {name} {ins}: post-silicon=0x{expected:08X} "
                      f"reference=0x{ref:08X}")
        print(("PASS: " if bad == 0 else "FAIL: ") +
              f"{name} {len(table)} vectors match independent reference")
        if bad:
            errors.append(name)

    # --- Alias mux routing vectors vs the canonical decoder's reference -------
    abad = 0
    for fmt_id, data, expected, label in ps.ALIAS_VECTORS:
        ref = independent_chip_output(ALIAS_REF[fmt_id], data)
        total += 1
        if ref != expected:
            abad += 1
            print(f"  alias {label}: post-silicon=0x{expected:08X} reference=0x{ref:08X}")
    print(("PASS: " if abad == 0 else "FAIL: ") +
          f"alias routing {len(ps.ALIAS_VECTORS)} vectors match reference")
    if abad:
        errors.append("alias")

    # --- Bring-up decode coverage == on-die decoder set -----------------------
    import gen_rom
    on_die = {r[0] for r in gen_rom.CATALOG if r[9] & gen_rom.FLAG_ON_DIE}
    covered = {fmt for *_, fmt in TABLES} | set(ALIAS_REF)
    missing = sorted(on_die - covered)
    extra = sorted(covered - on_die)
    ok_cov = not missing and not extra
    print(("PASS: " if ok_cov else "FAIL: ") +
          f"bring-up decode tests cover the {len(on_die)} on-die formats "
          f"(missing={missing}, extra={extra})")
    if not ok_cov:
        errors.append("coverage")

    # --- NUM_FORMATS consistency ---------------------------------------------
    ok_nf = ps.NUM_FORMATS == len(gen_rom.CATALOG) == 80
    print(("PASS: " if ok_nf else "FAIL: ") +
          f"NUM_FORMATS ({ps.NUM_FORMATS}) == CATALOG ({len(gen_rom.CATALOG)}) == 80")
    if not ok_nf:
        errors.append("NUM_FORMATS")

    # --- ROM self-index sweep oracle: byte[9] == fmt_id, record != 0 (gen_rom)
    # The bring-up test reads 10 bytes and asserts rom[9] == fmt_id; pin that to
    # gen_rom's packing (bits[79:72] = format_index_id; readback byte[9]).
    rom_bad = 0
    cat = {r[0]: gen_rom.pack_record(*r) for r in gen_rom.CATALOG}
    for fmt_id, word in cat.items():
        if ((word >> 72) & 0xFF) != fmt_id or word == 0:
            rom_bad += 1
    check(rom_bad == 0,
          "ROM self-index: byte[9]==fmt_id and record!=0 for all 80 (gen_rom)")
    # Out-of-range: catalog only defines 0..79, format_rom default is 0 -> reads 0.
    check(max(cat) == 79 and min(cat) == 0 and len(cat) == 80,
          "ROM catalog is exactly fmt_id 0..79 (out-of-range reads default 0)")

    # --- not-implemented response oracle: [NOT_IMPL, fmt_id, SPEC, 'N'] -------
    top = _read(os.path.join(ROOT, "src", "rtl", "tt_um_trinity_corona.v"))
    m = re.search(r"localparam\s*\[7:0\]\s*NOT_IMPL\s*=\s*8'h([0-9A-Fa-f]+)", top)
    not_impl = int(m.group(1), 16) if m else None
    pst = _read(os.path.join(ROOT, "post_silicon", "test_corona.py"))
    check(not_impl == 0xFF, f"RTL NOT_IMPL == 0xFF (got {not_impl})")
    # RTL not-impl status bytes 2/3 are SPEC (0x07) and 'N' (0x4E); tie to gen_rom.
    check("8'h4E" in top and gen_rom.ST_SPEC == 0x07,
          "RTL not-impl response uses 'N'(0x4E) + status_id SPEC(0x07==ST_SPEC)")
    check("0xFF" in pst and "0x4E" in pst,
          "post_silicon test_not_implemented asserts 0xFF (byte0) and 0x4E (byte3)")

    print("\n" + "=" * 60)
    if errors:
        print(f"post-silicon oracle: FAIL ({', '.join(errors)})")
        return 1
    print(f"ALL PASS: {total} bring-up vectors + alias/coverage/NUM_FORMATS "
          f"match the verified model")
    return 0


if __name__ == "__main__":
    sys.exit(main())
