#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Cross-die respin fix-coverage invariant.
#
# Every active/latent silicon defect found in the 2026-06 post-silicon audit has a
# staged drop-in *_v2 fix. This checks the deliverable itself: that EVERY die which
# instantiates a buggy module also carries that module's staged v2 fix. A gap here
# would mean a respin silently re-ships a known-broken block. Run from the corona
# repo; it inspects the sibling die repos.
#
# Invariant: for each (buggy, v2) pair, every die with <buggy>.v also has <v2>.v.
import os, sys
HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.dirname(os.path.dirname(HERE))   # parent of tt-trinity-corona
DIES={"gamma":"tt-trinity-gamma","euler":"tt-trinity-euler","phi":"tt-trinity-phi"}
PAIRS=[("gf16_mul","gf16_v2_mul"),("gf16_add","gf16_v2_add"),
       ("bitnet_encoder","bitnet_encoder_v2"),("blake3_anchor","blake3_anchor_v2"),
       ("multi_tile_receipt","multi_tile_receipt_v2"),("alu9_decoder","alu9_decoder_v2"),
       ("phi_d2d_lite","phi_d2d_lite_v2")]
def has(die,mod): return os.path.exists(os.path.join(ROOT,DIES[die],"src",mod+".v"))

def main():
    print("== respin fix-coverage matrix (every affected die must carry its v2) ==")
    print(f"{'buggy module':20s} {'staged fix':22s} " + " ".join(f"{d:>11s}" for d in DIES))
    gaps=[]
    for bug,fix in PAIRS:
        row=f"{bug:20s} {fix:22s} "
        for d in DIES:
            if has(d,bug):
                ok=has(d,fix); row+=f"{'BUG+FIX' if ok else 'NO-FIX!':>11s} "
                if not ok: gaps.append((d,bug,fix))
            else:
                row+=f"{'-':>11s} "
        print(row)
    print()
    if gaps:
        print("FIX-COVERAGE GAP(S):")
        for d,b,f in gaps: print(f"  {d}: instantiates {b} but is missing {f}.v")
        return 1
    print("FIX COVERAGE COMPLETE: every affected die carries its staged v2 fix.")
    return 0

if __name__=="__main__":
    sys.exit(main())
