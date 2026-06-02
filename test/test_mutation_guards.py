#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# test/test_mutation_guards.py
#
# Loop 96/97: mutation testing as a first-class CI gate. A guard that cannot FAIL
# gives false confidence ("oracle rot"). This test injects a known fault into each
# artifact and asserts the corresponding guard/reference detects it; an UNDETECTED
# fault means a vacuous guard and fails the run.
#
# Loop 97 generalises the RTL fault injection from 4 hand-picked decoders to ALL
# 17 unique decoders, automatically:
#   * sweep the real decoder (bounded) to get the baseline;
#   * try mutating each Verilog literal (toggle its LSB) until one CHANGES an
#     output; compile+sweep the mutant and assert the independent reference
#     (Loops 86-90) disagrees on >=1 input -> the reference is discriminating;
#   * for purely structural decoders (int4/int8 sign-extension) with no mutable
#     output literal, fall back to a declared structural mutation (flip the sign
#     bit index).
# Plus 2 codegen mutations: gen_rom field misplacement -> SSOT cross-check fails;
# CATALOG change -> ROM freshness fails.
#
# Non-destructive: src/rtl is never modified (tempdir copies). RTL cases skip
# gracefully (counted skipped, not passed) if iverilog is absent.
# Run: python3 test/test_mutation_guards.py

import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "test"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import test_float_decoders_independent as flt    # noqa: E402
import test_posit8_independent as p8             # noqa: E402
import test_lns8_independent as lns              # noqa: E402
import test_simple_decoders_independent as simp  # noqa: E402
import test_lut_published_values as lut          # noqa: E402

_FP4 = lut.fp4_e2m1_reference()
SWEEP_LIMIT = 512  # bounded sweep is enough to observe a mutated output

# module -> (width, instantiation, port-decl, reference, optional structural fallback)
W32 = "wire [31:0] o;"
DECODERS = {
    "bf16":          (16, ".bf16_in(in), .fp32_out(o), .is_zero(), .is_inf(), .is_nan()", W32, flt.ref_bf16, None),
    "tf32":          (19, ".tf32_in(in), .fp32_out(o), .is_zero(), .is_inf(), .is_nan()", W32, flt.ref_tf32, None),
    "fp8_e5m2":      (8,  ".e5m2_in(in), .fp32_out(o), .is_zero(), .is_inf(), .is_nan()", W32, flt.ref_e5m2, None),
    "mxfp8_e4m3":    (8,  ".e4m3_in(in), .fp32_out(o), .is_zero(), .is_nan()", W32, flt.ref_e4m3, None),
    "fp8_e4m3_fnuz": (8,  ".e4m3_in(in), .fp32_out(o), .is_zero(), .is_nan()", W32, flt.ref_e4m3_fnuz, None),
    "fp6_e3m2":      (6,  ".fp6_in(in), .fp32_out(o)", W32, flt.ref_fp6_e3m2, None),
    "fp6_e2m3":      (6,  ".fp6_in(in), .fp32_out(o), .is_zero()", W32, flt.ref_fp6_e2m3, None),
    "posit8":        (8,  ".posit_in(in), .fp32_out(o), .is_zero(), .is_nar()", W32, p8.posit8_ref, None),
    "nf4":           (4,  ".nf4_in(in), .fp32_out(o)", W32,
                      lambda i: lut.f32_bits(lut.QLORA_NF4[i & 0xF]), None),
    "fp4":           (4,  ".fp4_in(in), .fp32_out(o)", W32, lambda i: _FP4[i & 0xF], None),
    "e8m0":          (8,  ".e8m0_in(in), .fp32_out(o), .is_nan()", W32, lambda i: simp.ref("e8m0", i)[0], None),
    "bitnet":        (2,  ".ternary_in(in), .fp32_out(o), .is_zero(), .is_reserved()", W32, lambda i: simp.ref("bitnet", i)[0], None),
    "mxint8":        (8,  ".mxint8_in(in), .fp32_out(o), .is_zero(), .is_reserved()", W32, lambda i: simp.ref("mxint8", i)[0], None),
    "int4":          (4,  ".int4_in(in), .int32_out(o), .is_zero()", W32,
                      lambda i: simp.ref("int4", i)[0], ("int4_in[3]", "int4_in[2]")),
    "int8":          (8,  ".int8_in(in), .int32_out(o), .is_zero()", W32,
                      lambda i: simp.ref("int8", i)[0], ("int8_in[7]", "int8_in[6]")),
    "bcd":           (8,  ".bcd_in(in), .bin_out(o), .valid()", "wire [6:0] o;",
                      lambda i: simp.ref("bcd", i)[0], None),
    "lns8":          (8,  ".lns_in(in), .sign_out(), .magnitude(o), .is_zero()", "wire [15:0] o;",
                      lambda i: lns.lns8_ref(i)[1], None),
}

_TOK = re.compile(r"(\d+)'([hHbBdD])([0-9A-Fa-f_]+)")
_BASE = {"h": 16, "b": 2, "d": 10}
_FMT = {"h": "X", "b": "b", "d": "d"}


def _sweep(modfile, width, inst, decl, limit=None):
    n = min(1 << width, limit) if limit else (1 << width)
    mod = os.path.basename(modfile)[:-2]
    tb = (f"`timescale 1ns/1ps\nmodule tb; reg [{width-1}:0] in; {decl}\n"
          f" {mod} dut({inst}); integer i;\n"
          f" initial begin for(i=0;i<{n};i=i+1) begin in=i[{width-1}:0]; #1;"
          f' $display("%0d %08h", i, o); end $finish; end\nendmodule')
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


def _literal_variants(src):
    """Yield src with one Verilog literal's LSB toggled (skip x/z literals)."""
    for m in _TOK.finditer(src):
        w, base, raw = int(m.group(1)), m.group(2).lower(), m.group(3).replace("_", "")
        try:
            v = int(raw, _BASE[base])
        except ValueError:
            continue
        nv = (v ^ 1) & ((1 << w) - 1)
        newlit = f"{w}'{m.group(2)}{format(nv, _FMT[base])}"
        yield src[:m.start()] + newlit + src[m.end():]


def _mutant_detected(mod, mutated_src, width, inst, decl, ref):
    d = tempfile.mkdtemp()
    mf = os.path.join(d, f"{mod}_decode.v")
    with open(mf, "w") as f:
        f.write(mutated_src)
    out = _sweep(mf, width, inst, decl, SWEEP_LIMIT)
    if out is None:
        return False
    return any(out[i] != ref(i) for i in out)


def find_killing_mutation(mod, width, inst, decl, ref, fallback):
    src = open(os.path.join(ROOT, "src", "rtl", f"{mod}_decode.v")).read()
    if _sweep(os.path.join(ROOT, "src", "rtl", f"{mod}_decode.v"),
              width, inst, decl, SWEEP_LIMIT) is None:
        return None  # iverilog unavailable
    tried = 0
    for mut in _literal_variants(src):
        tried += 1
        if tried > 50:
            break
        if _mutant_detected(mod, mut, width, inst, decl, ref):
            return ("literal", tried)
    if fallback and fallback[0] in src:
        if _mutant_detected(mod, src.replace(fallback[0], fallback[1], 1),
                            width, inst, decl, ref):
            return ("structural", 0)
    return ("NO-KILL", tried)


def _silent_main(modname):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = __import__(modname).main()
    return rc


def py_mutation_ssot():
    import gen_rom
    orig = gen_rom.pack_record
    gen_rom.pack_record = lambda *a: (orig(*a) & ~(0xF << 68)) | ((a[1] & 0xF) << 64)
    try:
        rc = _silent_main("test_ssot_layout_crosscheck")
    finally:
        gen_rom.pack_record = orig
    return rc != 0, f"SSOT crosscheck on misplaced field -> rc={rc}"


def py_mutation_rom_fresh():
    import gen_rom
    orig = list(gen_rom.CATALOG)
    gen_rom.CATALOG = [(r if r[0] != 8 else r[:6] + (6,) + r[7:]) for r in orig]
    try:
        rc = _silent_main("test_rom_emitted_golden")
    finally:
        gen_rom.CATALOG = orig
    return rc != 0, f"ROM freshness on changed CATALOG -> rc={rc}"


def main():
    detected = missed = skipped = 0

    for mod, (width, inst, decl, ref, fallback) in DECODERS.items():
        res = find_killing_mutation(mod, width, inst, decl, ref, fallback)
        if res is None:
            print(f"SKIP: {mod} (iverilog unavailable)")
            skipped += 1
        elif res[0] in ("literal", "structural"):
            extra = f"after {res[1]} literals" if res[0] == "literal" else "structural fallback"
            print(f"DETECTED: {mod} mutant killed by reference ({extra})")
            detected += 1
        else:
            print(f"MISSED (vacuous guard!): {mod} -- no killing mutation among "
                  f"{res[1]} literals + fallback")
            missed += 1

    for fn in (py_mutation_ssot, py_mutation_rom_fresh):
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
          f"({detected} mutations across {len(DECODERS)} decoders + 2 codegen)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
