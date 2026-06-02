#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_ssot_layout_crosscheck.py
#
# Loop 79: guard the chip's HEADLINE claim -- "SSOT -> codegen -> RTL -> silicon
# is mechanical end-to-end". Until now nothing verified that the ROM bit-layout,
# encoding-kind enum, flag bits, status IDs, and record cardinality used by the
# codegen (tools/gen_rom.py) actually match the FROZEN [Spec] in the .t27 SSOT
# (specs/corona/rom_layout.t27 + corona_oracle.t27). The layout was duplicated
# by hand in THREE places (rom_layout.t27, gen_rom.py pack_record, and
# test_rom_spec_crosscheck.py extract_fields) with no cross-check -- exactly the
# drift the rom_layout.t27 "FROZEN at Phase B" warning anticipates.
#
# This test PARSES the SSOT and asserts gen_rom.py agrees with it:
#   1. Every FIELD_*.{lo,width} in rom_layout.t27 matches where pack_record()
#      actually places that field (functional bit-extraction check).
#   2. Field widths sum to RECORD_BITS (== 80).
#   3. ENCODING_* enum values match gen_rom ENC_*.
#   4. FLAG_* bit values match gen_rom FLAG_*.
#   5. STATUS_* enum values match gen_rom ST_*.
#   6. RECORD_COUNT / TOTAL_FORMATS == len(CATALOG) == 80, and CLUSTER_COUNTS
#      sum to TOTAL_FORMATS.
#
# Pure Python, no cocotb / no sby. Run: python3 test/test_ssot_layout_crosscheck.py
#
# Status: [Verified in sim] for the codegen<->SSOT structural agreement.

import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gen_rom  # noqa: E402
# The .t27 SSOT is parsed by exactly ONE module (Loop 80). This cross-check
# pins gen_rom.py's hand-coded packer to whatever that single parser reads.
import ssot_layout  # noqa: E402

ROM_LAYOUT = ssot_layout.ROM_LAYOUT
ORACLE = ssot_layout.ORACLE

# Thin aliases onto the shared parser so the check logic below reads unchanged.
parse_fields = ssot_layout.field_offsets
parse_const_enum = ssot_layout.const_enum
parse_cluster_counts = ssot_layout.cluster_counts


def parse_scalar(text, name):
    return ssot_layout.scalar(name, text=text)


def main():
    layout = ssot_layout.read(ROM_LAYOUT)
    oracle = ssot_layout.read(ORACLE)
    errors = []

    def check(cond, msg):
        if not cond:
            errors.append(msg)
            print(f"FAIL: {msg}")
        else:
            print(f"PASS: {msg}")

    # --- 1+2. Field layout: SSOT (lo,width) vs where pack_record actually puts it
    fields = parse_fields(layout)
    check(len(fields) == 11, f"parsed 11 SSOT fields (got {len(fields)})")

    # Map SSOT field name -> the pack_record() argument we feed it.
    # phi_distance_q16 is computed inside pack_record (from exp/mant), so we
    # probe it indirectly via the known phi_distance() output for our inputs.
    record_bits = parse_scalar(layout, "RECORD_BITS")
    check(record_bits == 80, f"RECORD_BITS == 80 (got {record_bits})")
    width_sum = sum(w for _, _, w in fields.values())
    check(width_sum == record_bits,
          f"field widths sum to RECORD_BITS ({width_sum} == {record_bits})")

    # Distinct probe values that fit each field's width, chosen so a swapped
    # shift/width would change the extracted value.
    probe = dict(fmt_id=0xA5, cluster=0x9, status=0x6, total_bits=0xC3,
                 sign_bits=0x1, exp_bits=0x4B, mant_bits=0x37, enc_kind=0x5,
                 ref_idx=0xD2, flags=0x8)
    word = gen_rom.pack_record(
        probe["fmt_id"], probe["cluster"], probe["status"], probe["total_bits"],
        probe["sign_bits"], probe["exp_bits"], probe["mant_bits"],
        probe["enc_kind"], probe["ref_idx"], probe["flags"])
    expected_phi = gen_rom.phi_distance(probe["exp_bits"], probe["mant_bits"])

    SSOT_TO_PROBE = {
        "FORMAT_INDEX_ID": probe["fmt_id"],
        "CLUSTER_ID": probe["cluster"],
        "STATUS_ID": probe["status"],
        "TOTAL_BITS": probe["total_bits"],
        "SIGN_BITS": probe["sign_bits"],
        "EXP_BITS": probe["exp_bits"],
        "MANT_BITS": probe["mant_bits"],
        "ENCODING_KIND": probe["enc_kind"],
        "PHI_DISTANCE_Q16": expected_phi,
        "REF_INDEX": probe["ref_idx"],
        "FLAGS": probe["flags"],
    }
    for name, expected in SSOT_TO_PROBE.items():
        hi, lo, w = fields[name]
        extracted = (word >> lo) & ((1 << w) - 1)
        check(extracted == expected,
              f"field {name} @ [{hi}:{lo}] w{w}: pack_record placed "
              f"0x{extracted:X}, SSOT-positioned expected 0x{expected:X}")

    # --- 3. ENCODING enum
    enc_ssot = parse_const_enum(layout, "ENCODING")
    enc_gen = {k[len("ENC_"):]: v for k, v in vars(gen_rom).items()
               if k.startswith("ENC_") and isinstance(v, int)}
    for name, val in enc_ssot.items():
        check(enc_gen.get(name) == val,
              f"ENCODING_{name}={val} matches gen_rom ENC_{name}={enc_gen.get(name)}")

    # --- 4. FLAG bits (map two renamed flags by value)
    flag_ssot = parse_const_enum(layout, "FLAG")
    flag_gen = {k: v for k, v in vars(gen_rom).items()
                if k.startswith("FLAG_") and isinstance(v, int)}
    check(set(flag_ssot.values()) == set(flag_gen.values()),
          f"FLAG bit-values match (SSOT {sorted(flag_ssot.values())} == "
          f"gen_rom {sorted(flag_gen.values())})")
    check(flag_ssot.get("ON_DIE") == flag_gen.get("FLAG_ON_DIE") == 0x01,
          "FLAG_ON_DIE == 0x01 in both")

    # --- 5. STATUS enum (normalize names: STATUS_EMPIRICAL_FIT vs ST_EMPIRICAL)
    status_ssot = parse_const_enum(oracle, "STATUS")
    st_gen = {k[len("ST_"):]: v for k, v in vars(gen_rom).items()
              if k.startswith("ST_") and isinstance(v, int)}
    check(set(status_ssot.values()) == set(st_gen.values()) == set(range(8)),
          f"STATUS values form 0..7 in both (SSOT {sorted(status_ssot.values())}, "
          f"gen_rom {sorted(st_gen.values())})")
    check(status_ssot.get("VERIFIED") == st_gen.get("VERIFIED") == 0,
          "STATUS_VERIFIED == 0 in both")
    check(status_ssot.get("SPEC") == st_gen.get("SPEC") == 7,
          "STATUS_SPEC == 7 in both")

    # --- 6. Cardinality
    total_formats = parse_scalar(oracle, "TOTAL_FORMATS")
    record_count = parse_scalar(layout, "RECORD_COUNT")
    check(total_formats == 80, f"TOTAL_FORMATS == 80 (got {total_formats})")
    check(record_count == total_formats,
          f"RECORD_COUNT ({record_count}) == TOTAL_FORMATS ({total_formats})")
    check(len(gen_rom.CATALOG) == total_formats,
          f"len(CATALOG) ({len(gen_rom.CATALOG)}) == TOTAL_FORMATS ({total_formats})")
    cluster_counts = parse_cluster_counts(oracle)
    check(sum(cluster_counts.values()) == total_formats,
          f"CLUSTER_COUNTS sum ({sum(cluster_counts.values())}) == "
          f"TOTAL_FORMATS ({total_formats})")

    print("\n" + "=" * 60)
    if errors:
        print(f"SSOT<->codegen cross-check: {len(errors)} FAILURE(S)")
        return 1
    print("ALL PASS: gen_rom.py layout/enums/cardinality match the .t27 SSOT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
