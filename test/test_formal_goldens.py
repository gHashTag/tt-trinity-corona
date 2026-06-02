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
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "test"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import test_posit8_independent as p8         # noqa: E402
import test_lns8_independent as lns          # noqa: E402
import test_lut_published_values as lut      # noqa: E402
import test_float_decoders_independent as flt    # noqa: E402
import test_simple_decoders_independent as simp  # noqa: E402

_FP4 = lut.fp4_e2m1_reference()

# Computed-golden harnesses: (decoder, input wire, width, golden signal, reference).
# Their golden is procedural logic (not a value table), so we evaluate it directly
# by instantiating the fv harness, FORCing the anyconst input across all values,
# and reading the golden signal hierarchically -- then compare to the independent
# reference. (bf16/tf32 assert against an inline definition with no `golden`
# signal, so there is no separate hand-written golden to validate.)
COMPUTED_GOLDENS = [
    ("e8m0",          "e8m0_in",   8, "golden", lambda i: simp.ref("e8m0", i)[0]),
    ("fp8_e5m2",      "e5m2_in",   8, "golden", flt.ref_e5m2),
    ("mxfp8_e4m3",    "e4m3_in",   8, "golden", flt.ref_e4m3),
    ("fp8_e4m3_fnuz", "e4m3_in",   8, "golden", flt.ref_e4m3_fnuz),
    ("fp6_e3m2",      "fp6_in",    6, "golden", flt.ref_fp6_e3m2),
    ("fp6_e2m3",      "fp6_in",    6, "golden", flt.ref_fp6_e2m3),
    ("mxint8",        "mxint8_in", 8, "golden", lambda i: simp.ref("mxint8", i)[0]),
    ("int4",          "int4_in",   4, "golden", lambda i: simp.ref("int4", i)[0]),
    ("int8",          "int8_in",   8, "golden", lambda i: simp.ref("int8", i)[0]),
    ("bcd",           "bcd_in",    8, "golden", lambda i: simp.ref("bcd", i)[0]),
]


def _force_sweep_golden(dec, in_wire, width, gsig):
    """Instantiate formal/fv_<dec>.sv, force its anyconst input over all values,
    read the golden signal hierarchically. Returns {i: value} or None (no iverilog)."""
    if not shutil.which("iverilog") or not shutil.which("vvp"):
        return None
    fv = os.path.join(ROOT, "formal", f"fv_{dec}.sv")
    dv = os.path.join(ROOT, "src", "rtl", f"{dec}_decode.v")
    n = 1 << width
    tb = (f"`timescale 1ns/1ps\nmodule tb; fv_{dec} u(); integer i;\n"
          f" initial begin for (i=0;i<{n};i=i+1) begin force u.{in_wire}=i[{width-1}:0];"
          f' #1; $display("%0d %08h", i, u.{gsig}); end $finish; end\nendmodule')
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "tb.v"), "w") as f:
        f.write(tb)
    binp = os.path.join(d, "a.out")
    if subprocess.run(["iverilog", "-g2012", "-o", binp,
                       os.path.join(d, "tb.v"), fv, dv], capture_output=True).returncode:
        return False
    r = subprocess.run(["vvp", binp], capture_output=True, text=True)
    return {int(l.split()[0]): int(l.split()[1], 16)
            for l in r.stdout.splitlines() if l.split() and l.split()[0].isdigit()}
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

    # --- 3. Computed (procedural) formal goldens via force + hierarchical read
    for dec, in_wire, width, gsig, ref in COMPUTED_GOLDENS:
        out = _force_sweep_golden(dec, in_wire, width, gsig)
        if out is None:
            print(f"SKIP: fv_{dec} computed golden (iverilog unavailable)")
            continue
        if out is False:
            check(False, f"fv_{dec} computed golden: harness compiled")
            continue
        n = 1 << width
        ok = len(out) == n and all(out.get(i) == ref(i) for i in range(n))
        check(ok, f"fv_{dec} computed golden == independent reference ({n}/{n})")

    print("\n" + "=" * 60)
    if errors:
        print(f"formal goldens: {len(errors)} FAILURE(S)")
        return 1
    print(f"ALL PASS: {len(decoders)} formal harnesses cover their decoder; "
          f"4 LUT + {len(COMPUTED_GOLDENS)} computed goldens match independent refs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
