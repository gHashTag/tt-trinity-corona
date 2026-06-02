#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_postsilicon_vectors_fresh.py
#
# Loop 101: post_silicon/corona_vectors.py is generated from the independent
# reference models by tools/gen_postsilicon_vectors.py (so bring-up vectors can't
# be wrong-by-transcription -- the Loop 92 bug class). This gate asserts the
# committed file is byte-identical to a fresh generation. If a reference or input
# set changes, regenerate and commit.
#
# Run: python3 test/test_postsilicon_vectors_fresh.py

import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "test"))

import gen_postsilicon_vectors as gen  # noqa: E402

DEST = os.path.join(ROOT, "post_silicon", "corona_vectors.py")


def main():
    fresh = gen.main()
    if not os.path.exists(DEST):
        print("FAIL: post_silicon/corona_vectors.py missing -- run "
              "python3 tools/gen_postsilicon_vectors.py")
        return 1
    with open(DEST, errors="replace") as f:
        committed = f.read()
    if fresh == committed:
        print(f"PASS: post_silicon/corona_vectors.py is up-to-date "
              f"({len(committed)} bytes)")
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
    print("FAIL: post_silicon/corona_vectors.py is STALE -- run "
          "`python3 tools/gen_postsilicon_vectors.py`." + detail)
    return 1


if __name__ == "__main__":
    sys.exit(main())
