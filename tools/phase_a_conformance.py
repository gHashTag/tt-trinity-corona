#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pinned, executable Phase A proof chain (issue #12).

This is verification plumbing. The acceptance function is compiled from .t27;
the oracle enumerates independent area classes and receipt truth tables.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC = Path("specs/corona/phase_a.t27")
VECTORS = Path("conformance/corona_phase_a.json")
SEAL = Path(".trinity/seals/corona_corona_phase_a.json")
PIN = "db870cdf292272f373037fb40b607c4134f59474"
U32_MAX = (1 << 32) - 1
U64_MAX = (1 << 64) - 1


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def vectors():
    # Expected verdict is attached to each independent area class. It is not
    # evaluated by a second copy of the acceptance function or by generated code.
    areas = [(0, 0, False), (0, 1, False), (1, 0, False), (1, 1, False),
             (1, 2, True), (2, 1, False), (279800192, 10452664320, True),
             (U64_MAX - 1, U64_MAX, True), (U64_MAX, U64_MAX, False),
             (U64_MAX, 1, False)]
    rows = []
    for cells, area_case, drc, precheck, anchor, lint in itertools.product(
            (0, 1, 1356, U32_MAX), areas, (0, 1, U32_MAX),
            (False, True), (0, 0x47BF, 0x47C0, U32_MAX), (False, True)):
        area, core, area_ok = area_case
        expected = all((cells != 0, area_ok, drc == 0, precheck,
                        anchor == 0x47C0, lint))
        rows.append({"id": f"phase_a_{len(rows):04d}",
                     "input": {"cells": cells, "area": str(area), "core": str(core),
                               "drc_items": drc, "precheck_ok": precheck,
                               "anchor": anchor, "claim_lint_ok": lint},
                     "expected": expected})
    return {"schema_version": 1, "module": "corona_phase_a",
            "spec_path": SPEC.as_posix(), "spec_hash": digest((ROOT / SPEC).read_bytes()),
            "compiler_revision": PIN,
            "scope": "Phase A digital acceptance only; no timing signoff or silicon proof",
            "integer_encoding": "u64 inputs are decimal strings to preserve exact values",
            "generator": "tools/phase_a_conformance.py --write-vectors",
            "vectors": rows}


def encoded(document):
    # One vector per line keeps the committed boundary matrix reviewable.
    head = dict(document)
    rows = head.pop("vectors")
    return (json.dumps(head, indent=2)[:-2] + ',\n  "vectors": [\n' +
            ',\n'.join('    ' + json.dumps(row, separators=(',', ':')) for row in rows) +
            '\n  ]\n}\n')


def run(args, *, output=None, expect_ok=True):
    result = subprocess.run([str(x) for x in args], cwd=ROOT, text=True,
                            capture_output=True, timeout=1800)
    if output:
        Path(output).write_text(result.stdout)
    if expect_ok and result.returncode:
        raise RuntimeError(f"{args[0]} failed ({result.returncode})\n{result.stdout}\n{result.stderr}")
    return result


def replay(compiler, spec, data, out, label, *, should_pass=True):
    generated = out / f"{label}.rs"
    run([compiler, "gen-rust", spec], output=generated)
    rows = []
    for row in data["vectors"]:
        v = row["input"]
        rows.append(f'({v["cells"]}u32,{v["area"]}u64,{v["core"]}u64,'
                    f'{v["drc_items"]}u32,{str(v["precheck_ok"]).lower()},'
                    f'{v["anchor"]}u32,{str(v["claim_lint_ok"]).lower()},'
                    f'{str(row["expected"]).lower()})')
    harness = out / f"{label}_replay.rs"
    harness.write_text(
        f'#[allow(dead_code,unused_parens)] mod policy {{ include!("{generated.name}"); }}\n'
        'fn main() {\nlet cases: &[(u32,u64,u64,u32,bool,u32,bool,bool)] = &[\n' +
        ',\n'.join(rows) + '\n];\n'
        'for (i, &(cells,area,core,drc,precheck,anchor,lint,expected)) in cases.iter().enumerate() {\n'
        'assert_eq!(policy::accepts(cells,area,core,drc,precheck,anchor,lint), expected, "vector {}", i);\n'
        '}\nprintln!("replayed {} vectors", cases.len());\n}\n')
    binary = out / f"{label}_replay"
    run(["rustc", "--edition=2021", "-Dwarnings", harness, "-o", binary])
    result = run([binary], expect_ok=False)
    (out / f"{label}.log").write_text(result.stdout + result.stderr)
    if should_pass:
        if result.returncode or f'replayed {len(rows)} vectors' not in result.stdout:
            raise RuntimeError(f"{label}: vector replay failed\n{result.stderr}")
    elif not result.returncode or "assertion `left == right` failed" not in result.stderr:
        raise RuntimeError(f"{label}: valid source mutant was not rejected by runtime assertions")


def check(compiler_root, save_seal):
    compiler_root = compiler_root.resolve()
    revision = run(["git", "-C", compiler_root, "rev-parse", "HEAD"]).stdout.strip()
    if revision != PIN:
        raise RuntimeError(f"compiler pin mismatch: {revision} != {PIN}")
    run(["git", "-C", compiler_root, "diff", "--exit-code", "HEAD", "--"])
    if run(["zig", "version"]).stdout.strip() != "0.16.0":
        raise RuntimeError("Zig 0.16.0 is required on PATH (also used by the native seal)")
    target = ROOT / "work/phase-a-toolchain"
    run(["cargo", "build", "--locked", "--release", "--manifest-path",
         compiler_root / "Cargo.toml", "-p", "t27c", "--bin", "t27c", "--target-dir", target])
    compiler = target / "release/t27c"
    out = ROOT / "work/phase-a-proof"
    out.mkdir(parents=True, exist_ok=True)
    data = vectors()
    if (ROOT / VECTORS).read_text() != encoded(data):
        raise RuntimeError("conformance vectors or spec hash drift; review before --write-vectors")
    result = run([compiler, "parse-complete", "--show", SPEC])
    if "nothing discarded" not in result.stdout:
        raise RuntimeError("spec was not fully parsed")
    run([compiler, "typecheck", SPEC])
    zig = out / "phase_a.zig"
    run([compiler, "gen", SPEC], output=zig)
    source_tests = len(re.findall(r"^test \w+\s*\{", (ROOT / SPEC).read_text(), re.M))
    emitted_tests = len(re.findall(r'^test "', zig.read_text(), re.M))
    if source_tests != 6 or emitted_tests != source_tests:
        raise RuntimeError(f"test inventory drift: source={source_tests}, generated={emitted_tests}")
    result = run(["zig", "test", zig])
    (out / "zig-tests.log").write_text(result.stdout + result.stderr)
    if f"All {source_tests} tests passed." not in result.stdout + result.stderr:
        raise RuntimeError("Zig did not report every expected test passing")
    replay(compiler, SPEC, data, out, "phase_a")
    source = (ROOT / SPEC).read_text()
    mutants = [("area_equality", "area < core", "area <= core"),
               ("nonzero_drc", "drc_items == 0", "drc_items <= 1"),
               ("missing_precheck", "&& precheck_ok", "&& (precheck_ok || true)"),
               ("wrong_anchor", "anchor == ANCHOR_VALUE", "anchor != ANCHOR_VALUE")]
    for label, old, new in mutants:
        if source.count(old) != 1:
            raise RuntimeError(f"mutant {label}: source boundary is ambiguous")
        path = out / f"{label}.t27"
        path.write_text(source.replace(old, new))
        run([compiler, "typecheck", path])
        replay(compiler, path, data, out, label, should_pass=False)
    # A flipped expectation must fail the same consumer, independently of the
    # byte-for-byte generation check above.
    bad = json.loads(json.dumps(data))
    bad["vectors"][0]["expected"] = not bad["vectors"][0]["expected"]
    replay(compiler, SPEC, bad, out, "altered_vector", should_pass=False)
    run([sys.executable, "test/test_phase_a_evidence.py"])
    result = run([compiler, "validate-conformance", "--repo-root", ROOT])
    if "WARN" in result.stdout or "ALL CONFORMANCE VALID" not in result.stdout:
        raise RuntimeError("native conformance validation incomplete")
    if save_seal:
        result = run([compiler, "seal", "--save", SPEC])
        if "BLOCKED" in result.stdout + result.stderr:
            raise RuntimeError("native seal tests blocked; do not publish this seal")
    run([compiler, "seal", "--verify", SPEC])
    seal = json.loads((ROOT / SEAL).read_text())
    if seal["spec_hash"] != data["spec_hash"]:
        raise RuntimeError("seal does not bind the current spec")
    if "blocked" in seal.get("tests", {}):
        raise RuntimeError("saved native seal has blocked tests")
    # Copy only to an isolated root; mutation must not touch the tracked spec.
    isolated = out / "stale-seal"
    (isolated / SPEC).parent.mkdir(parents=True, exist_ok=True)
    (isolated / SEAL).parent.mkdir(parents=True, exist_ok=True)
    (isolated / SPEC).write_text(source + "\n; stale-seal negative control\n")
    (isolated / SEAL).write_bytes((ROOT / SEAL).read_bytes())
    stale = subprocess.run([str(compiler), "seal", "--verify", str(SPEC)],
                           cwd=isolated, text=True, capture_output=True, timeout=120)
    if stale.returncode == 0:
        raise RuntimeError("native verifier accepted a stale source seal")
    report = {"spec_path": SPEC.as_posix(), "spec_hash": data["spec_hash"],
              "compiler_revision": PIN, "compiler_sha256": digest(compiler.read_bytes()),
              "zig_tests": source_tests, "rust_vectors": len(data["vectors"]),
              "source_mutants_rejected": len(mutants), "altered_vector_rejected": True,
              "stale_seal_rejected": True, "receipt_gate": "passed", "seal": SEAL.as_posix()}
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-vectors", action="store_true")
    parser.add_argument("--save-seal", action="store_true")
    parser.add_argument("--compiler-root", type=Path, default=Path(".phase-a-toolchain"))
    args = parser.parse_args()
    if args.write_vectors:
        (ROOT / VECTORS).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / VECTORS).write_text(encoded(vectors()))
        print(f"wrote {len(vectors()['vectors'])} vectors to {VECTORS}")
    else:
        check(args.compiler_root, args.save_seal)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        sys.exit(str(error))
