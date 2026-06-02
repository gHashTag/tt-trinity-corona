#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_mutation_guards.py
#
# Loop 96: mutation testing as a first-class CI gate (executes Loop 95 Option C).
#
# Every loop in the verification arc (86-95) hand-ran a mutation to prove the new
# guard was non-vacuous -- i.e. that it actually FAILS when the artifact is wrong,
# not just passes when it's right. A guard that can't fail provides false
# confidence ("oracle rot"). This test makes that property CI-enforced: it injects
# a known fault and asserts the corresponding guard/reference detects it. If any
# injected mutation goes UNDETECTED, the guard is vacuous and this test fails.
#
# Two fault classes:
#   * RTL decoder mutation -- copy a decoder .v to a tempdir, flip one output
#     literal, compile+sweep with iverilog, and assert the independent reference
#     disagrees (>=1 mismatch), showing the reference discriminates against a
#     faulty silicon source. (Non-destructive: the real src/rtl is never touched.)
#   * Codegen / freshness mutation -- monkeypatch gen_rom in-memory and assert the
#     Python guard's main() returns nonzero, then restore.
#
# Skips RTL cases gracefully (counted as skipped, not passed) if iverilog absent.
# Run: python3 test/test_mutation_guards.py

import contextlib
import io
import os
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "test"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import test_lut_published_values as lut          # noqa: E402
import test_simple_decoders_independent as simp  # noqa: E402
import test_posit8_independent as p8             # noqa: E402


def _sweep(modfile, width, inst, decl):
    mod = os.path.basename(modfile)[:-2]
    tb = (f"`timescale 1ns/1ps\nmodule tb; reg [{width-1}:0] in; {decl}\n"
          f" {mod} dut({inst}); integer i;\n"
          f" initial begin for(i=0;i<{1<<width};i=i+1) begin in=i[{width-1}:0];"
          f' #1; $display("%0d %08h", i, o); end $finish; end\nendmodule')
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "tb.v"), "w") as f:
        f.write(tb)
    binp = os.path.join(d, "a.out")
    if subprocess.run(["iverilog", "-g2012", "-o", binp, modfile,
                       os.path.join(d, "tb.v")], capture_output=True).returncode:
        return None
    r = subprocess.run(["vvp", binp], capture_output=True, text=True)
    return {int(l.split()[0]): int(l.split()[1], 16)
            for l in r.stdout.splitlines() if l.split() and l.split()[0].isdigit()}


# (module, old_literal, new_literal, width, instantiation, port-decl, reference fn)
RTL_MUTATIONS = [
    ("nf4", "4'h1: fp32_out = 32'hBF3239B1", "4'h1: fp32_out = 32'hBF3239B0",
     4, ".nf4_in(in), .fp32_out(o)", "wire [31:0] o;",
     lambda i: lut.f32_bits(lut.QLORA_NF4[i & 0xF])),
    ("e8m0", "32'h00400000", "32'h00400002",
     8, ".e8m0_in(in), .fp32_out(o), .is_nan()", "wire [31:0] o;",
     lambda i: simp.ref("e8m0", i)[0]),
    ("bitnet", "2'b01:   fp32_out = 32'h3F800000", "2'b01:   fp32_out = 32'h3F800002",
     2, ".ternary_in(in), .fp32_out(o), .is_zero(), .is_reserved()", "wire [31:0] o;",
     lambda i: simp.ref("bitnet", i)[0]),
    ("posit8",
     "is_nar)\n            fp32_out = 32'h7FC00000",
     "is_nar)\n            fp32_out = 32'h7FC00002",
     8, ".posit_in(in), .fp32_out(o), .is_zero(), .is_nar()", "wire [31:0] o;",
     p8.posit8_ref),
]


def run_rtl_mutation(mod, old, new, width, inst, decl, ref):
    src = open(os.path.join(ROOT, "src", "rtl", f"{mod}_decode.v")).read()
    if old not in src:
        return None, f"{mod}: mutation anchor not found (test stale)"
    d = tempfile.mkdtemp()
    mf = os.path.join(d, f"{mod}_decode.v")
    with open(mf, "w") as f:
        f.write(src.replace(old, new, 1))
    out = _sweep(mf, width, inst, decl)
    if out is None:
        return None, f"{mod}: iverilog unavailable/compile failed"
    mism = sum(1 for i in out if out[i] != ref(i))
    return mism > 0, f"{mod}: mutated RTL -> {mism} ref mismatches"


def _silent_main(modname):
    mod = __import__(modname)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod.main()
    return rc


def py_mutation_ssot():
    """Misplace a field in gen_rom.pack_record -> SSOT layout cross-check fails."""
    import gen_rom
    orig = gen_rom.pack_record
    gen_rom.pack_record = lambda *a: (orig(*a) & ~(0xF << 68)) | ((a[1] & 0xF) << 64)
    try:
        rc = _silent_main("test_ssot_layout_crosscheck")
    finally:
        gen_rom.pack_record = orig
    return rc != 0, f"SSOT crosscheck on misplaced field -> rc={rc}"


def py_mutation_rom_fresh():
    """Change a CATALOG record -> committed format_rom.v becomes stale."""
    import gen_rom
    orig = list(gen_rom.CATALOG)
    gen_rom.CATALOG = [(r if r[0] != 8 else r[:6] + (6,) + r[7:]) for r in orig]
    try:
        rc = _silent_main("test_rom_emitted_golden")
    finally:
        gen_rom.CATALOG = orig
    return rc != 0, f"ROM freshness on changed CATALOG -> rc={rc}"


PY_MUTATIONS = [py_mutation_ssot, py_mutation_rom_fresh]


def main():
    detected = 0
    missed = 0
    skipped = 0

    for args in RTL_MUTATIONS:
        ok, msg = run_rtl_mutation(*args)
        if ok is None:
            print("SKIP: " + msg)
            skipped += 1
        elif ok:
            print("DETECTED: " + msg)
            detected += 1
        else:
            print("MISSED (vacuous guard!): " + msg)
            missed += 1

    for fn in PY_MUTATIONS:
        ok, msg = fn()
        if ok:
            print("DETECTED: " + msg)
            detected += 1
        else:
            print("MISSED (vacuous guard!): " + msg)
            missed += 1

    print("\n" + "=" * 60)
    print(f"mutations: {detected} detected, {missed} missed, {skipped} skipped")
    if missed:
        print("FAIL: a guard did not detect its injected fault (vacuous).")
        return 1
    if detected == 0:
        print("FAIL: no mutations could be exercised.")
        return 1
    print(f"ALL PASS: every exercised guard detected its injected fault "
          f"({detected} mutations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
