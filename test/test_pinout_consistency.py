#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_pinout_consistency.py
#
# Loop 112: guard the pin documentation against the RTL, so the drift fixed in
# Loop 111 (uio labelled "D2D TX/RX" while the silicon has no D2D and instead
# drives the anchor high byte) cannot recur. Checks that:
#   * info.yaml declares 8 ui + 8 uo + 8 uio pins;
#   * the top module's port directions are ui_in (in), uo_out (out), uio_in (in),
#     uio_out (out), uio_oe (out), each [7:0];
#   * uio is driven only during the anchor probe (uio_oe = is_anchor_cmd ? FF : 00);
#   * the RTL contains NO D2D logic (deferred, ADR-0006); and therefore
#   * every doc that mentions D2D (info.yaml, info.md) also carries a deferral
#     marker ("deferred" / "adr/0006"), and info.md describes the as-built uio
#     anchor behaviour.
#
# Pure stdlib (regex; no PyYAML). Run: python3 test/test_pinout_consistency.py

import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TOP = os.path.join(ROOT, "src", "rtl", "tt_um_trinity_corona.v")
INFO_YAML = os.path.join(ROOT, "info.yaml")
INFO_MD = os.path.join(ROOT, "docs", "info.md")


def _read(p):
    with open(p, errors="replace") as f:
        return f.read()


def main():
    errors = []

    def check(cond, msg):
        print(("PASS: " if cond else "FAIL: ") + msg)
        if not cond:
            errors.append(msg)

    top = _read(TOP)
    yml = _read(INFO_YAML)
    md = _read(INFO_MD)

    # A. info.yaml pin counts (regex, no PyYAML dependency).
    for prefix, n_exp in (("ui", 8), ("uo", 8), ("uio", 8)):
        n = len(re.findall(rf"^\s*{prefix}\[\d+\]\s*:", yml, re.M))
        check(n == n_exp, f"info.yaml has {n_exp} {prefix}[] pins (got {n})")

    # B. RTL port directions.
    for pat, label in [
        (r"input\s+wire\s*\[7:0\]\s*ui_in", "ui_in input[8]"),
        (r"output\s+wire\s*\[7:0\]\s*uo_out", "uo_out output[8]"),
        (r"input\s+wire\s*\[7:0\]\s*uio_in", "uio_in input[8]"),
        (r"output\s+wire\s*\[7:0\]\s*uio_out", "uio_out output[8]"),
        (r"output\s+wire\s*\[7:0\]\s*uio_oe", "uio_oe output[8]"),
    ]:
        check(bool(re.search(pat, top)), f"RTL declares {label}")

    # C. uio driven only on the anchor probe.
    check(bool(re.search(r"uio_oe\s*=\s*is_anchor_cmd\s*\?\s*8'hFF\s*:\s*8'h00", top)),
          "RTL: uio_oe = is_anchor_cmd ? 0xFF : 0x00 (uio output only on anchor)")
    check(bool(re.search(r"uio_out_r\s*=\s*ANCHOR_UIO", top)),
          "RTL: uio drives ANCHOR_UIO during the anchor probe")

    # D. No D2D logic in the RTL (deferred, ADR-0006). Ignore comments.
    code_lines = [ln.split("//", 1)[0] for ln in top.splitlines()]
    d2d_code = [ln.strip() for ln in code_lines if re.search(r"d2d", ln, re.I)]
    check(not d2d_code, f"RTL has no D2D logic (deferred) (found: {d2d_code})")

    # E. Since D2D is not implemented, any doc that mentions it must mark it
    #    deferred (document-level, so an adjacent-line marker is fine).
    DEFER = re.compile(r"deferr|adr[-/]?0006|0006", re.I)
    for path, text, name in ((INFO_YAML, yml, "info.yaml"), (INFO_MD, md, "info.md")):
        mentions = bool(re.search(r"d2d", text, re.I))
        check((not mentions) or bool(DEFER.search(text)),
              f"{name}: D2D mention carries a deferral marker (ADR-0006)")

    # F. info.md documents the as-built uio anchor behaviour.
    check(bool(re.search(r"anchor[^\n]*0x47|0x47[^\n]*anchor|anchor high byte", md, re.I)),
          "info.md describes uio carrying the anchor high byte")

    print("\n" + "=" * 60)
    if errors:
        print(f"pinout consistency: {len(errors)} FAILURE(S)")
        return 1
    print("ALL PASS: pin docs (info.yaml + info.md) agree with the RTL; D2D deferred")
    return 0


if __name__ == "__main__":
    sys.exit(main())
