#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Cross-die audit of the GoldenFloat gfN_add units across the TRI-NET dies.
#
# The same .t27 code-gen produced the gfN arithmetic for Gamma, Phi and Euler.
# Gamma's units were found buggy and fixed/verified (loops 119-124,
# tt-trinity-gamma/docs/GF_ARITH_FINDINGS.md). Phi and Euler were submitted to the
# SAME SKY26b shuttle (2026-05-17/18) and ship the SAME pre-fix code -- so they
# likely carry the same defects. This script confirms it by probing each die's
# gfN_add units directly (read-only; it never modifies any die's RTL -- all three
# are frozen silicon).
#
# Two checks per rung, via iverilog:
#   1) add probe:  1.0 + 1.0 must give exponent bias+1 (a normalization check)
#   2) overflow:   max_finite + max_finite must round to a value that DECODES as
#                  Inf (catches the wrong Inf constant: mantissa-field nonzero ->
#                  decodes as NaN, i.e. a produced "Inf" that does not round-trip)
# Result decoding uses the CORRECT convention (Inf = exp-all-ones & mant==0),
# independent of each unit's (possibly wrong) EXP_MAX.
import os, subprocess, sys, tempfile

DIES = {
    "gamma": "/Users/playra/tt-trinity-gamma/src",
    "phi":   "/Users/playra/tt-trinity-phi/src",
    "euler": "/Users/playra/tt-trinity-euler/src",
}
# rung -> (total, E, M)
RUNGS = {
    "gf4": (4, 1, 2), "gf8": (8, 3, 4), "gf12": (12, 4, 7), "gf16": (16, 6, 9),
    "gf20": (20, 7, 12), "gf24": (24, 9, 14), "gf32": (32, 12, 19),
    "gf64": (64, 24, 39), "gf128": (128, 48, 79), "gf256": (256, 97, 158),
}

def bias(E): return (1 << (E - 1)) - 1

def decode_kind(code, E, M):
    e = (code >> M) & ((1 << E) - 1)
    m = code & ((1 << M) - 1)
    emax = (1 << E) - 1
    if e == emax and m == 0: return "Inf"
    if e == emax:            return "NaN"
    if e == 0 and m == 0:    return "zero"
    return e                                   # finite -> stored exponent

def probe_rung(src, rung, E, M):
    total = 1 + E + M
    b = bias(E)
    one  = b << M                              # 1.0 (invalid for bias 0)
    emax = (1 << E) - 1
    maxf = ((emax - 1) << M) | ((1 << M) - 1)  # largest finite magnitude
    add = os.path.join(src, rung + "_add.v")
    if not os.path.exists(add):
        return None
    tb = (
        "`timescale 1ns/1ps\n"
        f"module tb; reg [{total-1}:0] a,b; wire [{total-1}:0] s;\n"
        f" {rung}_add u(.a(a),.b(b),.result(s));\n"
        " initial begin\n"
        f"  a={total}'d{one}; b={total}'d{one}; #1; $display(\"P %h\", s);\n"
        f"  a={total}'d{maxf}; b={total}'d{maxf}; #1; $display(\"O %h\", s);\n"
        "  $finish; end endmodule\n"
    )
    d = tempfile.mkdtemp()
    open(os.path.join(d, "tb.v"), "w").write(tb)
    c = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "x"),
                        add, os.path.join(d, "tb.v")], capture_output=True, text=True)
    if c.returncode != 0:
        return ("ERR", None, None)
    out = subprocess.run(["vvp", os.path.join(d, "x")], capture_output=True, text=True).stdout
    res = {}
    for ln in out.splitlines():
        q = ln.split()
        if len(q) == 2 and q[0] in ("P", "O"):
            res[q[0]] = int(q[1], 16)
    probe_exp = decode_kind(res.get("P", 0), E, M) if b > 0 else "(skip bias0)"
    ovf_kind  = decode_kind(res.get("O", 0), E, M)
    return (probe_exp, ovf_kind, b + 1)

def main():
    print("Cross-die gfN_add audit (1+1 exponent + overflow->Inf round-trip):\n")
    summary = {}
    for die, src in DIES.items():
        if not os.path.isdir(src):
            print(f"[{die}] src not found: {src}"); continue
        print(f"=== {die} ({src}) ===")
        nbad = 0
        for rung, (total, E, M) in RUNGS.items():
            r = probe_rung(src, rung, E, M)
            if r is None:
                continue
            probe_exp, ovf_kind, want = r
            probe_ok = (probe_exp == want) or probe_exp == "(skip bias0)"
            ovf_ok = (ovf_kind == "Inf")
            bad = (not probe_ok) or (not ovf_ok)
            nbad += bad
            tag = "ok" if not bad else "BUG"
            print(f"  {rung:6s} probe_exp={str(probe_exp):>14} (want {want:>14})  "
                  f"overflow->{str(ovf_kind):>5}  [{tag}]")
        summary[die] = nbad
        print(f"  -> {nbad} rung(s) with a detected bug\n")
    print("=" * 60)
    for die, nbad in summary.items():
        print(f"{die:6s}: {nbad} buggy rung(s)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
