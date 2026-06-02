#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_verification_matrix_fresh.py
#
# Loop 100: the verification dossier docs/VERIFICATION.md is generated from the
# test suite by tools/gen_verification_matrix.py. This gate asserts the committed
# file is byte-identical to a fresh generation, so the dossier cannot drift from
# the actual evidence (the same regenerate-and-diff pattern as the ROM freshness
# gate). If a decoder or evidence layer changes, regenerate and commit.
#
# Run: python3 test/test_verification_matrix_fresh.py

import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "test"))

import gen_verification_matrix as gen  # noqa: E402

DOSSIER = os.path.join(ROOT, "docs", "VERIFICATION.md")


def main():
    fresh = gen.main()
    if not os.path.exists(DOSSIER):
        print("FAIL: docs/VERIFICATION.md missing -- run "
              "python3 tools/gen_verification_matrix.py")
        return 1
    with open(DOSSIER, errors="replace") as f:
        committed = f.read()
    if fresh == committed:
        print(f"PASS: docs/VERIFICATION.md is up-to-date ({len(committed)} bytes)")
        return 0
    fl, cl = fresh.splitlines(), committed.splitlines()
    diff_at = next((i for i in range(max(len(fl), len(cl)))
                    if (fl[i] if i < len(fl) else None)
                    != (cl[i] if i < len(cl) else None)), None)
    detail = ""
    if diff_at is not None:
        detail = (f" first diff at line {diff_at + 1}: "
                  f"committed={cl[diff_at] if diff_at < len(cl) else '<EOF>'!r} "
                  f"fresh={fl[diff_at] if diff_at < len(fl) else '<EOF>'!r}")
    print("FAIL: docs/VERIFICATION.md is STALE -- run "
          "`python3 tools/gen_verification_matrix.py`." + detail)
    return 1


if __name__ == "__main__":
    sys.exit(main())
