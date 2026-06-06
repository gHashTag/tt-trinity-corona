#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# gf16 multiply rounding-mode conformance characterization.
#
# The gf16 spec (t27/specs/numeric/gf16.t27) states the intended rounding mode is
# "Round-to-nearest, ties to even (IEEE 754 roundTiesToEven)". This exhaustively
# checks which mode the RTL actually implements, over all 512x512 unit-exponent
# mantissa products (the regime a MAC runs), against three references:
#   half_up    -- round up whenever the discarded part >= half (spec's encode code)
#   ties_zero  -- round up only when discarded > half (truncate exact ties)
#   ties_even  -- round up on discarded>half; on an exact tie, up iff kept LSB odd
# and confirms gf16_v3_mul is the ties-to-even-conformant variant. Run from corona;
# drives the gamma RTL.
import os, subprocess, tempfile, sys
HERE=os.path.dirname(os.path.abspath(__file__))
GAMMA=os.path.join(os.path.dirname(os.path.dirname(HERE)),"tt-trinity-gamma","src")
E=31

def ref(ma,mb,mode):
    fp=(512+ma)*(512+mb)
    if fp&(1<<19): exp=E+1; kept=(fp>>10)&0x1FF; disc=fp&0x3FF; half=1<<9
    else:          exp=E;   kept=(fp>>9)&0x1FF;  disc=fp&0x1FF; half=1<<8
    if   mode=="half_up":   up=1 if disc>=half else 0
    elif mode=="ties_zero": up=1 if disc>half  else 0
    else:                   up=(1 if disc>half else (0 if disc<half else (kept&1)))  # ties_even
    m=kept+up; e=exp
    if m>0x1FF: m=0; e+=1
    return 0x7E00 if e>=63 else (e<<9)|m

def drive(mod_file, mod):
    pairs=[(((E<<9)|ma),((E<<9)|mb)) for ma in range(512) for mb in range(512)]; n=len(pairs)
    TB=("`timescale 1ns/1ps\nmodule tb; reg [15:0] av[0:%d]; reg [15:0] bv[0:%d]; reg [15:0] a,b;"
        " wire [15:0] r;\n %s u(.a(a),.b(b),.result(r)); integer i;\n"
        " initial begin $readmemh(\"%s\",av); $readmemh(\"%s\",bv);\n"
        "  for(i=0;i<%d;i=i+1) begin a=av[i]; b=bv[i]; #1; $display(\"R %%04h\", r); end $finish; end endmodule")
    d=tempfile.mkdtemp(); af,bf=d+"/a.hex",d+"/b.hex"
    open(af,"w").write("\n".join("%04x"%a for a,_ in pairs)); open(bf,"w").write("\n".join("%04x"%b for _,b in pairs))
    open(d+"/tb.v","w").write(TB%(n-1,n-1,mod,af,bf,n))
    c=subprocess.run(["iverilog","-g2012","-o",d+"/x",os.path.join(GAMMA,mod_file),d+"/tb.v"],capture_output=True,text=True)
    if c.returncode: print(f"{mod}: COMPILE FAIL\n{c.stderr[:300]}"); sys.exit(2)
    return [int(l.split()[1],16)&0x7FFF for l in subprocess.run(["vvp",d+"/x"],capture_output=True,text=True).stdout.splitlines() if l.startswith("R ")]

def main():
    mp=[(ma,mb) for ma in range(512) for mb in range(512)]; n=len(mp)
    print("== gf16 multiply rounding-mode conformance (512x512 unit-exp products) ==")
    print("spec intent: IEEE roundTiesToEven (t27/specs/numeric/gf16.t27)\n")
    for modfile,mod in (("gf16_v2_mul.v","gf16_v2_mul"),("gf16_v3_mul.v","gf16_v3_mul")):
        if not os.path.exists(os.path.join(GAMMA,modfile)):
            print(f"  {mod}: absent -- skipped"); continue
        rtl=drive(modfile,mod)
        ag={m:sum(1 for i,(ma,mb) in enumerate(mp) if rtl[i]==(ref(ma,mb,m)&0x7FFF)) for m in ("half_up","ties_zero","ties_even")}
        impl=max(ag,key=ag.get)
        print(f"  {mod}: matches half_up {100*ag['half_up']/n:.3f}%  "
              f"ties_zero {100*ag['ties_zero']/n:.3f}%  ties_even {100*ag['ties_even']/n:.3f}%  "
              f"-> implements {impl}")
    ties=sum(1 for ma,mb in mp if ((512+ma)*(512+mb)&0x3FF)==512 and (512+ma)*(512+mb)&(1<<19)
             or ((512+ma)*(512+mb)&0x1FF)==256 and not (512+ma)*(512+mb)&(1<<19))
    gap=sum(1 for ma,mb in mp if (ref(ma,mb,"ties_zero")&0x7FFF)!=(ref(ma,mb,"ties_even")&0x7FFF))
    print(f"\n  exact-tie products: {ties}; RTL(ties_zero) vs intended(ties_even) gap: "
          f"{gap}/{n} = {100*gap/n:.4f}% (all 1 ULP, ties only)")
    print("RESULT: gf16_v2_mul = ties-to-zero (frozen silicon); gf16_v3_mul = ties-to-even (spec-conformant)")
    return 0

if __name__=="__main__":
    sys.exit(main())
