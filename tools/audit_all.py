#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# One-command re-validation of the full TRI-NET post-silicon audit (all four dies).
#
# Runs every instantiated-subsystem conformance audit in each die repo plus the
# cross-die fix-coverage invariant, and prints a single pass/fail summary. This is
# the reviewer/program entry point behind RESPIN_BRIEF_gf_arithmetic.md and
# AUDIT_COMPLETE.md -- it does NOT replace the per-die CI jobs (which also run the
# exhaustive gfN/VSA sweeps); it re-validates the post-silicon audit deliverable.
#
# Run from the corona repo; it invokes scripts in the sibling die repos.
# Exit code 0 iff every audit passes.
import os, subprocess, sys
HERE=os.path.dirname(os.path.abspath(__file__))
CORONA=os.path.dirname(HERE)
ROOT=os.path.dirname(CORONA)
def die(name): return os.path.join(ROOT, "tt-trinity-"+name)

# (label, cwd, argv) -- conformance audits per die + cross-die invariant
JOBS=[]
for d in ("gamma","euler"):
    for s in ("blake3_anchor_verify","receipt_path_audit","fabric_audit",
              "leaf_audit","shared_blocks_audit"):
        JOBS.append((f"{d}/{s}", die(d), ["python3", f"test/{s}.py"]))
JOBS.append(("phi/phi_audit", die("phi"), ["python3", "test/phi_audit.py"]))
JOBS.append(("corona/fix_coverage_matrix", CORONA, ["python3", "tools/fix_coverage_matrix.py"]))

def main():
    print("== TRI-NET post-silicon audit -- full re-validation (all four dies) ==\n")
    results=[]
    for label, cwd, argv in JOBS:
        script=os.path.join(cwd, argv[1])
        if not os.path.exists(script):
            print(f"  [SKIP] {label:38s} (script absent)"); results.append((label,None)); continue
        r=subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
        ok=(r.returncode==0)
        tail=(r.stdout.strip().splitlines() or [""])[-1][:60]
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:38s} {tail}")
        if not ok and r.stderr.strip():
            print(f"         stderr: {r.stderr.strip().splitlines()[-1][:80]}")
        results.append((label, ok))
    ran=[ok for _,ok in results if ok is not None]
    npass=sum(1 for ok in ran if ok); ntot=len(ran)
    nskip=sum(1 for _,ok in results if ok is None)
    print(f"\nSUMMARY: {npass}/{ntot} audits PASS" + (f" ({nskip} skipped)" if nskip else ""))
    allok = npass==ntot
    print("RESULT:", "FULL AUDIT GREEN across all four dies" if allok else "AUDIT FAILURE -- see above")
    return 0 if allok else 1

if __name__=="__main__":
    sys.exit(main())
