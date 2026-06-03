#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Project-wide hunt for the recurring "a field one bit too narrow" defect class that
# this codebase keeps producing: sized literals that overflow their width (N'dM with
# M >= 2^N) and out-of-range bit-selects. Every active arithmetic defect found in the
# GoldenFloat audit (gf16_mul mantissa, bitnet neuron_base, gf_formats IDs,
# int4_quantizer dequant) was an instance. Runs `verilator --lint-only -Wall` on each
# RTL file (catches files NOT reachable from any top, which a from-top lint misses)
# and reports the two telltale warnings. Read-only.
import os, re, subprocess, sys
LOC = re.compile(r"\.v:\d+:\d+:")   # only real "file.v:line:col:" warning lines

# RTL directories to sweep (edit as repos move)
DIRS = [
    "/Users/playra/tt-trinity-gamma/src",
    "/Users/playra/tt-trinity-phi/src",
    "/Users/playra/tt-trinity-euler/src",
    "/Users/playra/t27/rtl_gen",
    "/Users/playra/tt-trinity-corona/src/rtl",
]
SIG = ("Value too large for", "SELRANGE", "Selection index out of range",
       "Extracting")  # the width/range defect signatures

def main():
    total_files = hit_files = 0
    for d in DIRS:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".v"):
                continue
            total_files += 1
            path = os.path.join(d, fn)
            out = subprocess.run(["verilator", "--lint-only", "-Wall", path],
                                 capture_output=True, text=True).stderr
            hits = sorted(set(
                l.strip() for l in out.splitlines()
                if any(s in l for s in SIG) and "MULTITOP" not in l and LOC.search(l)))
            if hits:
                hit_files += 1
                print(f"### {path}")
                for h in hits[:8]:
                    print("   ", h.replace("%Warning-", "").split(" ... ")[0])
    print(f"\nswept {total_files} RTL files; {hit_files} with width/range defects")
    return 1 if hit_files else 0

if __name__ == "__main__":
    sys.exit(main())
