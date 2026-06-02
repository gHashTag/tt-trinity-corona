#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# tools/run_verification_gates.py
#
# Loop 113: run ALL standalone verification gates with one command, replacing the
# 20 hand-added `python3 test/...` steps in CI. Auto-discovers every standalone
# gate (test/test_*.py that does NOT import cocotb) and runs it as a subprocess,
# aggregating pass/fail. New gates are picked up automatically -- no CI edit per
# gate. The cocotb tests (test_anchor/test_decoders/test_stress) are run by the
# separate `make` flow and are skipped here.
#
# A floor on the discovered-gate count guards against silent under-discovery (a
# glob/skip bug that would quietly run fewer gates). Pure stdlib.
# Run: python3 tools/run_verification_gates.py

import glob
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TESTDIR = os.path.join(ROOT, "test")
MIN_GATES = 18  # current standalone-gate count is 20; floor catches gross under-run


def discover():
    gates, cocotb = [], []
    for path in sorted(glob.glob(os.path.join(TESTDIR, "test_*.py"))):
        with open(path, errors="replace") as f:
            src = f.read()
        (cocotb if "import cocotb" in src else gates).append(path)
    return gates, cocotb


def main():
    gates, cocotb = discover()
    print(f"Discovered {len(gates)} standalone verification gates "
          f"({len(cocotb)} cocotb tests skipped -- run via `make`).\n")

    if len(gates) < MIN_GATES:
        print(f"FAIL: only {len(gates)} gates discovered (< floor {MIN_GATES}); "
              f"gate discovery looks broken.")
        return 1

    failed = []
    results = []  # (name, status, summary line)
    for path in gates:
        name = os.path.basename(path)
        r = subprocess.run([sys.executable, path], capture_output=True, text=True)
        last = ""
        for line in reversed(r.stdout.splitlines()):
            if line.strip():
                last = line.strip()
                break
        status = "PASS" if r.returncode == 0 else "FAIL"
        results.append((name, status, last))
        print(f"  [{status}] {name:42s} {last[:60]}")
        if r.returncode != 0:
            failed.append(name)
            if r.stderr.strip():
                print("         stderr: " + r.stderr.strip().splitlines()[-1][:80])

    _write_step_summary(results, failed)

    print("\n" + "=" * 60)
    if failed:
        print(f"verification gates: {len(failed)}/{len(gates)} FAILED "
              f"({', '.join(failed)})")
        return 1
    print(f"ALL PASS: {len(gates)}/{len(gates)} standalone verification gates green")
    return 0


def _write_step_summary(results, failed):
    """If running under GitHub Actions, append a markdown results table to the
    job step summary (visible in the CI UI). No-op locally."""
    dest = os.environ.get("GITHUB_STEP_SUMMARY")
    if not dest:
        return
    total = len(results)
    lines = [
        "## Verification gates",
        "",
        f"**{total - len(failed)}/{total} standalone gates passed**"
        + (f" -- FAILED: {', '.join(failed)}" if failed else " ✅"),
        "",
        "| Gate | Status | Result |",
        "| --- | :-: | --- |",
    ]
    for name, status, summary in results:
        mark = "✅" if status == "PASS" else "❌"
        # escape pipes in the free-text summary so the table stays well-formed
        safe = summary.replace("|", "\\|")[:80]
        lines.append(f"| `{name}` | {mark} | {safe} |")
    lines.append("")
    try:
        with open(dest, "a") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass  # summary is best-effort; never fail the run over it


if __name__ == "__main__":
    sys.exit(main())
