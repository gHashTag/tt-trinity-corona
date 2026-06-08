#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Three-way GF ladder consistency: SSOT closed-form rule <-> Corona ROM catalog
# <-> gamma RTL field-splits. A format's (E, M) split is a definition that must
# agree everywhere; this is the cross-artifact check that the gf128 finding showed
# matters (the catalog, the RTL generator, and every decoder must use one split).
#
# Rule (t27 SSOT FORMAT-SPEC-001): e = round((N-1)/phi^2), m = N-1-e.
# Run from the corona repo; reads tools/gen_rom.py CATALOG + the sibling gamma RTL.
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
CORONA = os.path.dirname(HERE)
GAMMA = os.path.join(os.path.dirname(CORONA), "tt-trinity-gamma", "src")
PHI2 = ((1 + 5 ** 0.5) / 2) ** 2

def closed_form(N):
    e = round((N - 1) / PHI2)
    return e, (N - 1) - e

def catalog_gf():
    """parse GF rungs from gen_rom.py: (..., total, S, E, M, ENC_GF, ...)  # GFxxx"""
    t = open(os.path.join(CORONA, "tools", "gen_rom.py")).read()
    out = {}
    for m in re.finditer(r"\(\s*\d+,\s*CL_GOLDENFLOAT,\s*ST_\w+,\s*(\d+),\s*1,\s*(\d+),\s*(\d+),\s*ENC_GF.*?#\s*(GF\w+)", t):
        total, E, M, name = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
        out[name] = (total, E, M)
    return out

def rtl_split(N):
    """read (E, M) from gamma gfN_add.v header [S(1) | E(x) | M(y)]"""
    for cand in (f"gf{N}_add.v", f"gf{N}_v2_add.v"):
        f = os.path.join(GAMMA, cand)
        if not os.path.exists(f): continue
        h = re.search(r"E\((\d+)\)\s*\|\s*M\((\d+)\)", open(f).read())
        if h: return (int(h.group(1)), int(h.group(2)))
    return None

def main():
    cat = catalog_gf()
    print("== GF ladder three-way consistency (closed-form / catalog / RTL) ==")
    print(f"{'fmt':7} {'N':>4} {'closed-form':>12} {'catalog':>10} {'RTL':>10}  verdict")
    bad = 0
    for name in sorted(cat, key=lambda s: int(re.sub(r"\D", "", s) or 0)):
        total, cE, cM = cat[name]
        N = total
        if name in ("GF4", "GFTernary") or N < 4:
            # GF4 closed-form round(3/phi^2)=1 -> (1,2); GFTernary is special
            pass
        e, m = closed_form(N)
        rtl = rtl_split(N)
        cf_ok = (cE == e and cM == m)
        rtl_str = f"E{rtl[0]} M{rtl[1]}" if rtl else "(no RTL)"
        rtl_ok = (rtl is None) or (rtl == (cE, cM))
        ok = cf_ok and rtl_ok
        if not ok: bad += 1
        print(f"{name:7} {N:>4} {'E%d M%d'%(e,m):>12} {'E%d M%d'%(cE,cM):>10} {rtl_str:>10}  "
              f"{'OK' if ok else ('CF-MISMATCH' if not cf_ok else 'RTL-MISMATCH')}")
    print()
    if bad:
        print(f"RESULT: {bad} format(s) inconsistent across closed-form/catalog/RTL")
        return 1
    print("RESULT: GF ladder CONSISTENT (closed-form == catalog == RTL for every rung)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
