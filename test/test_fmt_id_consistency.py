#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_fmt_id_consistency.py
#
# Loop 85: pin every FMT_<name> = id constant to ONE source of truth -- the
# decode hardware. The fmt_id name->id mapping is hand-maintained as localparams
# in src/rtl/tt_um_trinity_corona.v (the actual silicon routing) AND duplicated
# as Python constants across multiple test/tool files. Loop 83 checked only
# test_decoders.py against the RTL; test_stress.py and special_values.py (and any
# future file) were unguarded -- a fmt_id renumber in one of them would silently
# exercise a different format than the hardware routes.
#
# This test AUTO-DISCOVERS every module-level `FMT_<name> = <int>` in test/*.py
# and tools/*.py and asserts:
#   * it matches the RTL localparam of the same name (the hardware truth), and
#   * it names a fmt_id the hardware actually defines (no FMT_ constant that the
#     RTL doesn't have).
# Future test files are covered automatically -- no enumeration to keep in sync.
#
# The RTL is the source of truth on purpose: fmt_id is a hardware routing fact;
# changing one means changing the silicon, which must drive the tests, not vice
# versa. Pure stdlib. Run: python3 test/test_fmt_id_consistency.py

import glob
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TOP_V = os.path.join(ROOT, "src", "rtl", "tt_um_trinity_corona.v")
SELF = os.path.abspath(__file__)


def _read(p):
    with open(p, errors="replace") as f:
        return f.read()


def rtl_fmt_ids(text):
    """Parse `localparam [6:0] FMT_<name> = 7'd<N>` (and 7'h for the anchor)."""
    out = {}
    for name, base, val in re.findall(
            r"localparam\s*\[6:0\]\s+(FMT_\w+)\s*=\s*7'([hd])([0-9A-Fa-f]+)", text):
        out[name] = int(val, 16) if base == "h" else int(val)
    return out


def py_fmt_ids(text):
    """Module-level `FMT_<name> = <int>` definitions (decimal or 0x hex)."""
    return {n: int(v, 0) for n, v in
            re.findall(r"^(FMT_\w+)\s*=\s*(0[xX][0-9a-fA-F]+|\d+)", text, re.M)}


def discover_consumers():
    files = sorted(set(glob.glob(os.path.join(ROOT, "test", "*.py")) +
                       glob.glob(os.path.join(ROOT, "tools", "*.py"))))
    return [f for f in files if os.path.abspath(f) != SELF]


def main():
    errors = []

    def check(cond, msg):
        print(("PASS: " if cond else "FAIL: ") + msg)
        if not cond:
            errors.append(msg)

    rtl = rtl_fmt_ids(_read(TOP_V))
    check(len(rtl) >= 22, f"parsed RTL FMT_ localparams ({len(rtl)} found)")
    check(rtl.get("FMT_ID_ANCHOR") == 0x7F,
          f"RTL FMT_ID_ANCHOR == 0x7F (got {rtl.get('FMT_ID_ANCHOR')})")

    consumers = discover_consumers()
    total_checked = 0
    files_with_fmt = 0
    for path in consumers:
        defs = py_fmt_ids(_read(path))
        if not defs:
            continue
        files_with_fmt += 1
        rel = os.path.relpath(path, ROOT)
        mism = {n: (rtl.get(n), v) for n, v in defs.items() if rtl.get(n) != v}
        check(not mism, f"{rel}: {len(defs)} FMT_ consts all match RTL")
        for n, (r, d) in sorted(mism.items()):
            kind = "undefined in RTL" if r is None else f"RTL={r}"
            print(f"    {n}: file={d} but {kind}")
        total_checked += len(defs)

    check(files_with_fmt >= 3,
          f"discovered FMT_ constants in >=3 consumer files (found {files_with_fmt})")

    print("\n" + "=" * 60)
    if errors:
        print(f"fmt_id consistency: {len(errors)} FAILURE(S)")
        return 1
    print(f"ALL PASS: {total_checked} FMT_ constants across {files_with_fmt} files "
          f"match the RTL ({len(rtl)} localparams)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
