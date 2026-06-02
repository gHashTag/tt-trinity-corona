#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_formal_goldens.py
#
# Loop 98: validate the FORMAL verification layer locally and tie it to the same
# independent references as the rest of the suite.
#
# Each formal harness formal/fv_<name>.sv checks, over ALL inputs (`anyconst` +
# SMT), that the decoder equals an independent "golden" -- a 5th hand-written copy
# of decode truth (after RTL, cocotb ref models, post-silicon vectors, and the
# Loop 86-90 references). That golden is only checked when SymbiYosys runs (the
# slow CI formal job). A typo'd formal golden for a LUT decoder would otherwise go
# unnoticed until then.
#
# This test, in pure Python (no sby):
#   1. Coverage -- every src/rtl/*_decode.v has a formal/fv_<name>.sv that
#      instantiates it and contains an output-equivalence assertion.
#   2. LUT golden consistency -- the hardcoded value tables in fv_nf4 / fv_fp4 /
#      fv_posit8 / fv_lns8 match the independent references built in Loops 86-90
#      (QLoRA, OCP E2M1, posit-standard, antilog). Catches a drifted formal golden
#      before the formal run.
#
# Run: python3 test/test_formal_goldens.py

import glob
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "test"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import test_posit8_independent as p8         # noqa: E402
import test_lns8_independent as lns          # noqa: E402
import test_lut_published_values as lut      # noqa: E402

_FP4 = lut.fp4_e2m1_reference()
# Output port asserted for equivalence in each formal harness.
_OUT_PORTS = ("fp32_out", "int32_out", "bin_out", "magnitude")


def _read(p):
    with open(p, errors="replace") as f:
        return f.read()


def parse_case32(text):
    """`N'hI: <var> = 32'hVVVVVVVV;` -> {index: uint32}."""
    return {int(i, 16): int(v, 16) for i, v in
            re.findall(r"\b\d+'h([0-9A-Fa-f]+)\s*:\s*\w+\s*=\s*32'h([0-9A-Fa-f]+)", text)}


def main():
    errors = []

    def check(cond, msg):
        print(("PASS: " if cond else "FAIL: ") + msg)
        if not cond:
            errors.append(msg)

    # --- 1. Formal coverage: every decoder has a harness asserting equivalence
    decoders = sorted(os.path.basename(p)[:-len("_decode.v")]
                      for p in glob.glob(os.path.join(ROOT, "src", "rtl", "*_decode.v")))
    eq_re = re.compile(r"assert\s*\(\s*(?:" + "|".join(_OUT_PORTS) + r")\s*==")
    for dec in decoders:
        fv = os.path.join(ROOT, "formal", f"fv_{dec}.sv")
        if not os.path.exists(fv):
            check(False, f"{dec}: formal/fv_{dec}.sv exists")
            continue
        txt = _read(fv)
        check(f"{dec}_decode" in txt, f"{dec}: fv harness instantiates {dec}_decode")
        check(bool(eq_re.search(txt)),
              f"{dec}: fv harness asserts output-equivalence")

    # --- 2. LUT golden consistency vs independent references -----------------
    nf4 = parse_case32(_read(os.path.join(ROOT, "formal", "fv_nf4.sv")))
    check(len(nf4) == 16 and all(
        nf4.get(i) == lut.f32_bits(lut.QLORA_NF4[i]) for i in range(16)),
        "fv_nf4 golden LUT == published QLoRA (16/16)")

    fp4 = parse_case32(_read(os.path.join(ROOT, "formal", "fv_fp4.sv")))
    check(len(fp4) == 16 and all(fp4.get(i) == _FP4[i] for i in range(16)),
          "fv_fp4 golden LUT == computed OCP E2M1 (16/16)")

    pos = parse_case32(_read(os.path.join(ROOT, "formal", "fv_posit8.sv")))
    check(len(pos) == 256 and all(
        pos.get(i) == p8.posit8_ref(i) for i in range(256)),
        "fv_posit8 256-entry golden == independent posit reference (256/256)")

    lns_txt = _read(os.path.join(ROOT, "formal", "fv_lns8.sv"))
    lns_lut = {int(i): int(v) for i, v in
               re.findall(r"4'd(\d+)\s*:\s*golden_lut\s*=\s*9'd(\d+)", lns_txt)}
    check(len(lns_lut) == 16 and all(
        lns_lut.get(i) == lns.antilog_lut(i) for i in range(16)),
        "fv_lns8 antilog LUT == round(256*2^(i/16)) (16/16)")

    print("\n" + "=" * 60)
    if errors:
        print(f"formal goldens: {len(errors)} FAILURE(S)")
        return 1
    print(f"ALL PASS: {len(decoders)} formal harnesses cover their decoder; "
          f"4 LUT goldens match independent references")
    return 0


if __name__ == "__main__":
    sys.exit(main())
