#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_rom_emitted_golden.py
#
# Loop 82: tie the THREE packed-ROM representations to the generator-of-record.
# The 80 packed 80-bit records currently exist in three forms:
#   1. tools/gen_rom.py        -- CATALOG + pack_record  (the generator)
#   2. src/rtl/format_rom.v    -- committed RTL ROM (what actually ships)
#   3. test/tb_rom_golden.v    -- hand-coded golden_lo/mid/hi (the GLS oracle)
#
# `make rom-golden` checks (2) against (3), but NOTHING checked that (2) is still
# what (1) emits, nor that (3) matches (1). So a generator/CATALOG edit that
# forgets to regenerate would leave a stale-but-self-consistent (2)+(3) pair that
# still passes -- and (2) is the silicon ROM. This test makes gen_rom.py the
# single source of record:
#   A. The committed format_rom.v is byte-identical to a fresh gen_rom emit.
#   B. Every tb_rom_golden.v golden word equals pack_record(CATALOG[i]).
#
# Pure stdlib (no cocotb / yosys / sby). Run: python3 test/test_rom_emitted_golden.py

import os
import re
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gen_rom  # noqa: E402

FORMAT_ROM_V = os.path.join(ROOT, "src", "rtl", "format_rom.v")
TB_GOLDEN_V = os.path.join(ROOT, "test", "tb_rom_golden.v")


def _read(path):
    with open(path, errors="replace") as f:
        return f.read()


def check_format_rom_fresh():
    """A. Committed format_rom.v == fresh gen_rom emit (byte-identical)."""
    with tempfile.TemporaryDirectory() as d:
        tmp = os.path.join(d, "format_rom.v")
        gen_rom.generate_verilog(gen_rom.CATALOG, tmp)
        fresh = _read(tmp)
    committed = _read(FORMAT_ROM_V)
    if fresh == committed:
        print("PASS: src/rtl/format_rom.v is up-to-date with tools/gen_rom.py")
        return []
    # Report the first differing line for a helpful message.
    fl, cl = fresh.splitlines(), committed.splitlines()
    diff_at = next((i for i in range(max(len(fl), len(cl)))
                    if (fl[i] if i < len(fl) else None)
                    != (cl[i] if i < len(cl) else None)), None)
    detail = ""
    if diff_at is not None:
        detail = (f" first diff at line {diff_at + 1}: "
                  f"committed={cl[diff_at] if diff_at < len(cl) else '<EOF>'!r} "
                  f"fresh={fl[diff_at] if diff_at < len(fl) else '<EOF>'!r}")
    print("FAIL: format_rom.v is STALE -- run `python3 tools/gen_rom.py`." + detail)
    return ["format_rom.v stale vs gen_rom.py"]


def parse_tb_golden(text):
    """Parse golden_lo/mid/hi[idx] = 32'hXXXX/16'hXXXX into {idx: 80-bit word}."""
    pat = re.compile(r"golden_(lo|mid|hi)\[\s*(\d+)\]\s*=\s*\d+'h([0-9A-Fa-f]+)")
    lo, mid, hi = {}, {}, {}
    bucket = {"lo": lo, "mid": mid, "hi": hi}
    for part, idx, val in pat.findall(text):
        bucket[part][int(idx)] = int(val, 16)
    words = {}
    for idx in lo:
        words[idx] = (hi.get(idx, 0) << 64) | (mid.get(idx, 0) << 32) | lo[idx]
    return words


def check_tb_golden_matches_generator():
    """B. Every tb_rom_golden.v word == pack_record(CATALOG[fmt_id])."""
    golden = parse_tb_golden(_read(TB_GOLDEN_V))
    errors = []
    if len(golden) != len(gen_rom.CATALOG):
        errors.append(f"tb golden has {len(golden)} records, CATALOG has "
                      f"{len(gen_rom.CATALOG)}")
        print(f"FAIL: {errors[-1]}")
    by_fmt = {rec[0]: rec for rec in gen_rom.CATALOG}
    for fmt_id, rec in sorted(by_fmt.items()):
        want = gen_rom.pack_record(*rec)
        got = golden.get(fmt_id)
        if got != want:
            errors.append(f"fmt_id={fmt_id}: tb golden=0x{(got or 0):020X} "
                          f"!= generator 0x{want:020X}")
            print(f"FAIL: {errors[-1]}")
    if not errors:
        print(f"PASS: all {len(golden)} tb_rom_golden.v words match gen_rom packer")
    return errors


def main():
    errors = []
    errors += check_format_rom_fresh()
    errors += check_tb_golden_matches_generator()
    print("\n" + "=" * 60)
    if errors:
        print(f"ROM emitted-vs-generator check: {len(errors)} FAILURE(S)")
        return 1
    print("ALL PASS: generator <-> emitted RTL <-> GLS golden are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
