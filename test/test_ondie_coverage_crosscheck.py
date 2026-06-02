#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_ondie_coverage_crosscheck.py
#
# Loop 83: guard the chip's self-description against its actual hardware and its
# test coverage. A format is "Tier-1 / on-die" in THREE independent places:
#   1. tools/gen_rom.py   -- CATALOG records with the FLAG_ON_DIE bit (the ROM
#                            metadata the chip reports about itself)
#   2. src/rtl/tt_um_trinity_corona.v -- the decode-mux `case (fmt_id_r)` arms
#                            that set has_decoder=1 (the actual silicon decode path)
#   3. test/test_decoders.py -- the fmt_ids exercised via send_cmd (coverage)
#
# These three sets must be IDENTICAL. If they drift -- a decoder added to the mux
# without FLAG_ON_DIE, an on-die ROM flag with no decode path, or an on-die format
# with no cocotb test -- the chip would either misreport its own capabilities or
# ship an untested decode path. Nothing checked this before; the sets happen to
# agree today (22 each), so this test locks that in.
#
# It additionally checks that the shared FMT_<name> = id naming agrees between the
# top module localparams and the test's constants (a fmt_id renumber in one place
# only would be a silent hazard).
#
# Pure stdlib. Run: python3 test/test_ondie_coverage_crosscheck.py

import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gen_rom  # noqa: E402

TOP_V = os.path.join(ROOT, "src", "rtl", "tt_um_trinity_corona.v")
TEST_DECODERS = os.path.join(ROOT, "test", "test_decoders.py")


def _read(path):
    with open(path, errors="replace") as f:
        return f.read()


def rom_on_die_ids():
    return sorted(r[0] for r in gen_rom.CATALOG if r[9] & gen_rom.FLAG_ON_DIE)


def top_module(text):
    """Return (fmt_name->id localparams, set of mux fmt_ids that set a decoder)."""
    params = {n: int(v) for n, v in
              re.findall(r"localparam\s*\[6:0\]\s+(FMT_\w+)\s*=\s*7'd(\d+)", text)}
    mux_names = re.findall(r"(FMT_\w+)\s*:\s*begin\s+decode_result", text)
    mux_ids = sorted({params[n] for n in mux_names if n in params})
    return params, mux_ids, mux_names


def test_constants(text):
    """fmt_name->id defs and the set of fmt_ids exercised via send_cmd."""
    defs = {n: int(v) for n, v in
            re.findall(r"^(FMT_\w+)\s*=\s*(\d+)", text, re.M)}
    used = set(re.findall(r"send_cmd\(\s*dut\s*,\s*(FMT_\w+)", text))
    used_ids = sorted({defs[n] for n in used if n in defs})
    return defs, used_ids


def main():
    errors = []

    def check(cond, msg):
        print(("PASS: " if cond else "FAIL: ") + msg)
        if not cond:
            errors.append(msg)

    top_txt = _read(TOP_V)
    test_txt = _read(TEST_DECODERS)

    on_die = rom_on_die_ids()
    top_params, mux_ids, mux_names = top_module(top_txt)
    test_defs, tested_ids = test_constants(test_txt)

    # --- Three-way set identity
    check(set(on_die) == set(mux_ids),
          f"ROM FLAG_ON_DIE ({len(on_die)}) == decode-mux ids ({len(mux_ids)})")
    if set(on_die) != set(mux_ids):
        print(f"  on_die-only: {sorted(set(on_die)-set(mux_ids))}  "
              f"mux-only: {sorted(set(mux_ids)-set(on_die))}")

    check(set(on_die) == set(tested_ids),
          f"ROM FLAG_ON_DIE ({len(on_die)}) == tested ids ({len(tested_ids)})")
    if set(on_die) != set(tested_ids):
        print(f"  on_die-only: {sorted(set(on_die)-set(tested_ids))}  "
              f"tested-only: {sorted(set(tested_ids)-set(on_die))}")

    check(set(mux_ids) == set(tested_ids),
          f"decode-mux ids ({len(mux_ids)}) == tested ids ({len(tested_ids)})")

    # --- Shared FMT_<name>=id naming agreement (top module vs test)
    shared = set(top_params) & set(test_defs)
    mismatched = {n: (top_params[n], test_defs[n])
                  for n in shared if top_params[n] != test_defs[n]}
    check(not mismatched,
          f"FMT_ name->id agree across top module and test ({len(shared)} shared)")
    for n, (a, b) in sorted(mismatched.items()):
        print(f"  {n}: top={a} test={b}")

    # --- Every mux arm references a defined localparam (no typo'd arm)
    undefined = [n for n in mux_names if n not in top_params]
    check(not undefined, f"all {len(mux_names)} mux arms map to a FMT_ localparam")
    if undefined:
        print(f"  undefined: {undefined}")

    print("\n" + "=" * 60)
    if errors:
        print(f"on-die coverage cross-check: {len(errors)} FAILURE(S)")
        return 1
    print(f"ALL PASS: ROM<->mux<->tests agree on {len(on_die)} on-die formats")
    return 0


if __name__ == "__main__":
    sys.exit(main())
