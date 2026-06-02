#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_bringup_oracle_complete.py
#
# Loop 95: make "every post-silicon bring-up test is cross-checked against the
# verified model" an ENFORCED invariant (executes Loop 94 Option C).
#
# Loops 92-94 pinned every assertion in post_silicon/test_corona.py to the RTL /
# gen_rom / independent references. But that coverage was a snapshot: a new entry
# added to ALL_TESTS later -- a new decoder's bring-up test, or a new ROM check --
# could ship to the demoboard with NO model cross-check, and CI would stay green.
#
# This gate walks ps.ALL_TESTS and requires each entry to be cross-checked:
#   * vector-driven tests (reference a *_VECTORS global) -> that exact table must
#     appear in test_post_silicon_vectors.TABLES (decode) or be ALIAS_VECTORS;
#   * non-vector tests (anchor / ROM-meta / not-implemented) -> must be listed in
#     NON_VECTOR_CROSSCHECKED with the guard that covers them.
# A new bring-up test that is neither -> this gate fails. Pure stdlib (imports).
# Run: python3 test/test_bringup_oracle_complete.py

import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "test"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "post_silicon"))

import test_corona as ps                    # noqa: E402
import test_post_silicon_vectors as tpsv    # noqa: E402

# Non-vector bring-up tests and the guard that cross-checks each against the model.
NON_VECTOR_CROSSCHECKED = {
    "test_anchor":               "test_anchor_derivation.py (0x47C0 across 4 copies)",
    "test_anchor_stability":     "test_anchor_derivation.py (anchor constant)",
    "test_rom_self_index_sweep": "test_post_silicon_vectors.py (byte[9]==fmt_id vs gen_rom)",
    "test_rom_out_of_range":     "test_post_silicon_vectors.py (catalog 0..79, default 0)",
    "test_not_implemented":      "test_post_silicon_vectors.py (NOT_IMPL/SPEC/'N')",
}


def main():
    errors = []

    def check(cond, msg):
        print(("PASS: " if cond else "FAIL: ") + msg)
        if not cond:
            errors.append(msg)

    covered_tables = {id(t) for _n, t, _s, _f in tpsv.TABLES} | {id(ps.ALIAS_VECTORS)}

    seen_nonvector = set()
    for fn in ps.ALL_TESTS:
        name = fn.__name__
        vec_names = [n for n in fn.__code__.co_names
                     if n.endswith("_VECTORS") and hasattr(ps, n)]
        if vec_names:
            uncovered = [n for n in vec_names
                         if id(getattr(ps, n)) not in covered_tables]
            check(not uncovered,
                  f"{name}: vector table cross-checked (uncovered: {uncovered})")
        else:
            check(name in NON_VECTOR_CROSSCHECKED,
                  f"{name}: non-vector test has a declared cross-check")
            seen_nonvector.add(name)

    # No stale entries in the allowlist (a removed test must be removed here too).
    stale = sorted(set(NON_VECTOR_CROSSCHECKED) - seen_nonvector)
    check(not stale, f"no stale NON_VECTOR_CROSSCHECKED entries (stale: {stale})")

    # Sanity: the gate actually saw the whole suite.
    check(len(ps.ALL_TESTS) >= 23,
          f"walked ps.ALL_TESTS ({len(ps.ALL_TESTS)} entries)")

    print("\n" + "=" * 60)
    if errors:
        print(f"bring-up oracle completeness: {len(errors)} FAILURE(S)")
        return 1
    print(f"ALL PASS: all {len(ps.ALL_TESTS)} bring-up tests are cross-checked "
          f"against the verified model (invariant enforced)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
