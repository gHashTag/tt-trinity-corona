#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_independent_oracle_coverage.py
#
# Loop 91: turn the 17/17 "every decoder verified against a reference outside its
# own cocotb model" result (built across Loops 86-90) into an ENFORCED invariant.
#
# Across five tests, each decoder is pinned to an independent oracle:
#   test_lut_published_values.py     -> nf4, fp4
#   test_posit8_independent.py       -> posit8
#   test_lns8_independent.py         -> lns8
#   test_simple_decoders_independent -> int4, int8, bcd, bitnet, e8m0, mxint8
#   test_float_decoders_independent  -> bf16, tf32, fp8_e5m2, fp8_e4m3_fnuz,
#                                       mxfp8_e4m3, fp6_e3m2, fp6_e2m3
# Each of those declares a module-level COVERED frozenset. This gate imports them,
# unions COVERED, and asserts it equals the set of src/rtl/*_decode.v modules.
#
# Effect: if someone adds a new decoder later WITHOUT an independent-reference
# test (or removes one), CI fails here -- 17/17 becomes a maintained invariant,
# not a one-time snapshot. Pure stdlib, no iverilog needed (imports only).
# Run: python3 test/test_independent_oracle_coverage.py

import glob
import importlib
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TESTDIR = os.path.join(ROOT, "test")
sys.path.insert(0, TESTDIR)

ORACLE_TESTS = [
    "test_lut_published_values",
    "test_posit8_independent",
    "test_lns8_independent",
    "test_simple_decoders_independent",
    "test_float_decoders_independent",
]


def decoder_modules():
    """Set of `<name>` for every src/rtl/<name>_decode.v."""
    out = set()
    for path in glob.glob(os.path.join(ROOT, "src", "rtl", "*_decode.v")):
        out.add(os.path.basename(path)[:-len("_decode.v")])
    return out


def main():
    errors = []

    def check(cond, msg):
        print(("PASS: " if cond else "FAIL: ") + msg)
        if not cond:
            errors.append(msg)

    decoders = decoder_modules()
    check(len(decoders) >= 17, f"found {len(decoders)} *_decode.v modules")

    covered = set()
    overlaps = []
    for name in ORACLE_TESTS:
        mod = importlib.import_module(name)
        cov = getattr(mod, "COVERED", None)
        check(cov is not None, f"{name} declares COVERED")
        if cov:
            dup = covered & set(cov)
            if dup:
                overlaps.append((name, sorted(dup)))
            covered |= set(cov)

    # Every covered name must be a real decoder module (no typos in COVERED).
    bogus = sorted(covered - decoders)
    check(not bogus, f"all COVERED names are real decoders (bogus: {bogus})")

    # Every decoder module must have an independent-reference test.
    missing = sorted(decoders - covered)
    check(not missing,
          f"every decoder has an independent-reference oracle "
          f"(missing: {missing})")

    # Each decoder pinned by exactly one oracle test (no accidental double-claim).
    check(not overlaps, f"no decoder claimed by two oracle tests ({overlaps})")

    print("\n" + "=" * 60)
    if errors:
        print(f"independent-oracle coverage: {len(errors)} FAILURE(S)")
        return 1
    print(f"ALL PASS: {len(covered)}/{len(decoders)} decoders pinned to an "
          f"independent oracle (invariant enforced)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
