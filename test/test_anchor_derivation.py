#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_anchor_derivation.py
#
# Loop 84: verify what is genuinely verifiable about the TG-TRIAD-X cross-die
# anchor (0x47C0) and HONESTLY record what is not.
#
# test_anchor.py already checks the hardware *outputs* 0x47C0. Nothing checked
# (a) the arithmetic basis the spec claims for it, or (b) that the constant
# agrees across the spec, the RTL, and the test. anchor.t27 states a 3-step
# derivation:
#   Step 1: Lucas L_2 = phi^2 + phi^-2 = 3            [exact integer identity]
#   Step 2: L_2 = 3  ->  GF(2^4) = GF16               [a labelling/choice]
#   Step 3: dot4(1,2,3,4) over GF16  ->  0x47C0       [bit pattern]
#
# This test:
#   * VERIFIES Step 1 exactly (Lucas recurrence + float phi), the spec's own
#     "canary in the mine" (anchor.t27 tags it [Verified]).
#   * LOCKS the 0x47C0 / 0x47 / 0xC0 / 0x7F constants across anchor.t27,
#     tt_um_trinity_corona.v, and test_anchor.py (no cross-file drift).
#   * DOES NOT fabricate a derivation for Step 3. Under the standard GF(2^4)
#     field (x^4+x+1), dot4(1,2,3,4)*self XOR-reduces to 0x3, a single nibble;
#     the mapping from that GF16 result to the 16-bit 0x47C0 is unspecified in
#     anchor.t27. That step stays [Open conjecture] per the spec, and is
#     reported here for the record -- it is NOT a test failure (conjecture,
#     not a falsified claim).
#
# Pure stdlib. Run: python3 test/test_anchor_derivation.py

import math
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ANCHOR_T27 = os.path.join(ROOT, "specs", "corona", "anchor.t27")
TOP_V = os.path.join(ROOT, "src", "rtl", "tt_um_trinity_corona.v")
TEST_ANCHOR = os.path.join(ROOT, "test", "test_anchor.py")

ANCHOR_VALUE = 0x47C0
ANCHOR_UIO = 0x47   # high byte
ANCHOR_UO = 0xC0    # low byte
FMT_ID_ANCHOR = 0x7F


def _read(p):
    with open(p, errors="replace") as f:
        return f.read()


def lucas(n):
    """Integer Lucas sequence: L_0=2, L_1=1, L_n = L_{n-1}+L_{n-2}."""
    a, b = 2, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def gfmul(a, b, poly=0x13):
    """Multiply in GF(2^4) with irreducible x^4 + x + 1 (0x13)."""
    r = 0
    for _ in range(4):
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
        if a & 0x10:
            a ^= poly
    return r & 0xF


def main():
    errors = []

    def check(cond, msg):
        print(("PASS: " if cond else "FAIL: ") + msg)
        if not cond:
            errors.append(msg)

    # --- Step 1: Lucas L_2 = phi^2 + phi^-2 = 3 (exact) ----------------------
    check(lucas(2) == 3, f"Lucas L_2 == 3 (got {lucas(2)})")
    phi = (1 + math.sqrt(5)) / 2
    identity = phi ** 2 + phi ** -2
    check(abs(identity - 3.0) < 1e-12,
          f"phi^2 + phi^-2 == 3 (got {identity!r})")
    check(abs(identity - lucas(2)) < 1e-12,
          "phi^2 + phi^-2 equals the integer Lucas L_2")

    # --- Constant self-consistency ------------------------------------------
    check((ANCHOR_UIO << 8) | ANCHOR_UO == ANCHOR_VALUE,
          f"byte split: (0x{ANCHOR_UIO:02X}<<8)|0x{ANCHOR_UO:02X} == 0x{ANCHOR_VALUE:04X}")

    # anchor.t27
    a = _read(ANCHOR_T27)

    def t27const(name):
        m = re.search(rf"{name}\s*:\s*u\d+\s*=\s*(0[xX][0-9A-Fa-f]+|\d+)", a)
        return int(m.group(1), 0) if m else None
    check(t27const("ANCHOR_VALUE_U16") == ANCHOR_VALUE,
          "anchor.t27 ANCHOR_VALUE_U16 == 0x47C0")
    check(t27const("ANCHOR_UIO_OUT") == ANCHOR_UIO,
          "anchor.t27 ANCHOR_UIO_OUT == 0x47")
    check(t27const("ANCHOR_UO_OUT") == ANCHOR_UO,
          "anchor.t27 ANCHOR_UO_OUT == 0xC0")
    check(t27const("FMT_ID_ANCHOR") == FMT_ID_ANCHOR,
          "anchor.t27 FMT_ID_ANCHOR == 0x7F")

    # tt_um_trinity_corona.v
    v = _read(TOP_V)

    def vconst(name):
        m = re.search(rf"localparam\s*\[[^\]]*\]\s*{name}\s*=\s*\d+'[hd]([0-9A-Fa-f]+)", v)
        return int(m.group(1), 16) if m else None
    check(vconst("ANCHOR_UIO") == ANCHOR_UIO, "RTL ANCHOR_UIO == 0x47")
    check(vconst("ANCHOR_UO") == ANCHOR_UO, "RTL ANCHOR_UO == 0xC0")
    check(vconst("FMT_ID_ANCHOR") == FMT_ID_ANCHOR, "RTL FMT_ID_ANCHOR == 0x7F")

    # test_anchor.py asserts the same value/bytes
    ta = _read(TEST_ANCHOR)
    check("0x47C0" in ta and "0x47" in ta and "0xC0" in ta,
          "test_anchor.py asserts 0x47C0 / 0x47 / 0xC0")

    # --- Step 3 honesty: report, do not fabricate ---------------------------
    v4 = [1, 2, 3, 4]
    dot = 0
    for x in v4:
        dot ^= gfmul(x, x)
    print()
    print("[Open conjecture] Step 3 (anchor.t27 sec.2): dot4(1,2,3,4) over GF16")
    print(f"  under standard GF(2^4) x^4+x+1: dot4*self XOR-reduces to 0x{dot:X} "
          f"(a 4-bit element), which does not by itself yield the 16-bit 0x47C0.")
    print("  The GF16-result -> 16-bit-pattern mapping is unspecified in anchor.t27;")
    print("  this step remains [Open conjecture] (NOT a test failure). Step 1 and the")
    print("  cross-file constant are what this test verifies.")

    print("\n" + "=" * 60)
    if errors:
        print(f"anchor derivation check: {len(errors)} FAILURE(S)")
        return 1
    print("ALL PASS: Lucas L_2 identity holds; anchor constant consistent across "
          "spec/RTL/test")
    return 0


if __name__ == "__main__":
    sys.exit(main())
