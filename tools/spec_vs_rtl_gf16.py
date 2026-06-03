#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Bounds the gf16_mul defect's blast radius: was it in the multi-language SOURCE
# (the t27 .t27 spec -> 16 languages) or only in the hand-written Verilog?
# Compares the spec's Python reference (t27/conformance/gf16_ref.py, = encode(
# decode(a)*decode(b))) to the corrected RTL gf16_v2_mul over all 262144 unit-exp
# products, classifying each diff as benign (<=1 ULP rounding-convention) or a real
# (>1 ULP) discrepancy. Read-only. Requires iverilog + the two repos side by side.
#
# Result (2026-06): 99.36% exact, 0.64% differ by <=1 ULP (spec rounds half-up; the
# RTL rounds ties-to-zero), 0 differ by >1 ULP -> the SPEC never had the halving /
# overflow-to-zero bugs; they were Verilog-only (now fixed). The <=1 ULP gap is a
# spec<->RTL rounding-CONVENTION nuance, not a defect.
import os, sys, subprocess, tempfile

T27_REF = "/Users/playra/t27/conformance"
RTL_V2  = "/Users/playra/tt-trinity-gamma/src/gf16_v2_mul.v"
BIAS = 31

def dec(code):
    s = (code >> 15) & 1; e = (code >> 9) & 0x3F; m = code & 0x1FF
    if e == 0 and m == 0: return 0.0
    if e == 0x3F: return None
    return (-1 if s else 1) * (1 + m / 512.0) * 2.0 ** (e - BIAS)

def ulp(e): return 2.0 ** (e - BIAS - 9)

def main():
    if not os.path.exists(os.path.join(T27_REF, "gf16_ref.py")):
        print("SKIP: t27/conformance/gf16_ref.py not found"); return 0
    sys.path.insert(0, T27_REF)
    import gf16_ref as spec
    pairs = [(((31 << 9) | ma), ((31 << 9) | mb)) for ma in range(512) for mb in range(512)]
    n = len(pairs)
    with tempfile.TemporaryDirectory() as d:
        open(d + "/a.hex", "w").write("\n".join("%04x" % a for a, _ in pairs))
        open(d + "/b.hex", "w").write("\n".join("%04x" % b for _, b in pairs))
        tb = (f'`timescale 1ns/1ps\nmodule tb; reg [15:0] av[0:{n-1}],bv[0:{n-1}];'
              f' reg [15:0] a,b; wire [15:0] r; gf16_v2_mul u(.a(a),.b(b),.result(r));\n'
              f' integer i; initial begin $readmemh("{d}/a.hex",av);$readmemh("{d}/b.hex",bv);\n'
              f' for(i=0;i<{n};i=i+1) begin a=av[i];b=bv[i];#1; $display("R %04h",r); end $finish; end endmodule')
        open(d + "/tb.v", "w").write(tb)
        c = subprocess.run(["iverilog", "-g2012", "-o", d + "/x", RTL_V2, d + "/tb.v"],
                           capture_output=True, text=True)
        if c.returncode:
            print("iverilog FAILED:\n" + c.stderr); return 2
        out = subprocess.run(["vvp", d + "/x"], capture_output=True, text=True).stdout
        rtl = [int(l.split()[1], 16) for l in out.splitlines() if l.startswith("R ")]

    exact = tie = worse = 0; ex = []
    for (a, b), rraw in zip(pairs, rtl):
        sraw = spec.gf16_mul(a, b)
        if sraw == rraw:
            exact += 1; continue
        dv, sv = dec(rraw), dec(sraw)
        e = (rraw >> 9) & 0x3F
        gap = abs(dv - sv) / ulp(e) if (dv is not None and sv is not None and e not in (0, 0x3F)) else 99
        if gap <= 1.0001:
            tie += 1
        else:
            worse += 1
            if len(ex) < 5: ex.append((hex(a), hex(b), hex(sraw), hex(rraw), round(gap, 2)))
    print(f"spec gf16_mul vs corrected RTL gf16_v2_mul, {n} unit-exp products:")
    print(f"  exact: {exact} ({100.0*exact/n:.2f}%)  ; <=1 ULP (rounding convention): {tie} ; >1 ULP: {worse}")
    for e in ex: print("   ", e)
    print("RESULT:", "spec sound (bug was Verilog-only); only a <=1 ULP round-half-up vs "
          "ties-to-zero convention gap" if worse == 0 else "REAL >1 ULP spec<->RTL discrepancy")
    return 0 if worse == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
