#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_doc_counts_consistency.py
#
# Loop 117: guard the hand-typed counts in the prose docs against the actual
# artifacts, so the staleness found repeatedly by manual audit (18-vs-17 decode
# modules, 58-vs-57 formal tasks, 49-vs-76 GL tests) cannot recur. Computes each
# count from the source of truth, scans README.md / PLAN.md / docs/info.md /
# post_silicon/POST_SILICON_PLAN.md for the canonical count phrasings, and asserts
# every stated number equals the actual.
#
# Auto-discovered by tools/run_verification_gates.py (no CI edit). Historical
# docs/REPORT_*.md are intentionally NOT scanned (snapshots). Pure stdlib.
# Run: python3 test/test_doc_counts_consistency.py

import glob
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "post_silicon"))

PROSE_DOCS = ["README.md", "PLAN.md", "docs/info.md",
              "post_silicon/POST_SILICON_PLAN.md"]


def _read(rel):
    with open(os.path.join(ROOT, rel), errors="replace") as f:
        return f.read()


def actuals():
    decoders = len(glob.glob(os.path.join(ROOT, "src", "rtl", "*_decode.v")))
    formal = sum(3 for _ in glob.glob(os.path.join(ROOT, "formal", "*.sby")))  # 3 tasks/sby
    # Count @cocotb.test() only in real cocotb test files -- detected by a
    # module-level cocotb import (a line starting with import/from cocotb), so this
    # guard never counts its own string literals.
    cocotb = 0
    imp = re.compile(r"^\s*(?:import cocotb|from cocotb)", re.M)
    for f in glob.glob(os.path.join(ROOT, "test", "*.py")):
        src = _read_test(f)
        if imp.search(src):
            cocotb += src.count("@cocotb.test()")
    import test_corona
    postsi = len(test_corona.ALL_TESTS)
    gl = int(re.search(r"(\d+) tests",
                       _read("test/tb_gls_smoke.v")).group(1))
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import run_verification_gates
    gates = len(run_verification_gates.discover()[0])
    return {"decoders": decoders, "formal": formal, "cocotb": cocotb,
            "postsi": postsi, "gl": gl, "gates": gates}


def _read_test(path):
    with open(path, errors="replace") as f:
        return f.read()


def main():
    a = actuals()
    print(f"actuals: decoders={a['decoders']} formal={a['formal']} "
          f"cocotb={a['cocotb']} postsi={a['postsi']} gl={a['gl']}")

    # (regex with one int group, expected actual). Phrasings are specific enough
    # to be unambiguous count claims.
    checks = [
        (r"(\d+) formal tasks", a["formal"]),
        (r"(\d+) cocotb", a["cocotb"]),
        (r"(\d+) GL tests", a["gl"]),
        (r"(\d+) Tier-1 RTL decode modules", a["decoders"]),
        (r"ALL (\d+) tests must pass", a["postsi"]),
        (r"(\d+) tests covering all verification", a["postsi"]),
        (r"(\d+) CI cross-check gates", a["gates"]),
    ]

    errors = []
    checked = 0
    for rel in PROSE_DOCS:
        txt = _read(rel)
        for pat, expected in checks:
            for m in re.finditer(pat, txt):
                checked += 1
                got = int(m.group(1))
                if got != expected:
                    errors.append(f"{rel}: '{m.group(0)}' but actual is {expected}")
                    print(f"FAIL: {errors[-1]}")

    # Non-vacuity: the canonical phrasings must actually be present somewhere.
    if checked < 6:
        print(f"FAIL: only {checked} count-claims found (< 6); phrasings may have "
              f"changed -- update this guard.")
        return 1

    print(f"\nchecked {checked} count-claims across {len(PROSE_DOCS)} prose docs")
    print("=" * 60)
    if errors:
        print(f"doc-count consistency: {len(errors)} FAILURE(S)")
        return 1
    print("ALL PASS: prose doc counts match the artifacts "
          "(decoders/formal/cocotb/post-silicon/GL)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
