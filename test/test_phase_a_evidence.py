# SPDX-License-Identifier: Apache-2.0
"""Verify pinned Phase A receipts against the spec and current design inputs.

Verification tooling only: the acceptance policy lives in phase_a.t27.
The phase-a-spec CI job executes its test blocks through t27c -> Zig and
checks the Rust declarations. This gate independently checks source receipts.
"""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/phase_a"


def validate(root, provenance, receipts):
    for rel, digest in provenance["sha256"].items():
        path = provenance["source_workflow_snapshot"] if rel == ".github/workflows/gds.yml" else rel
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, rel
    original_workflow = (root / provenance["source_workflow_snapshot"]).read_text()
    # Preserve the historical workflow hash. The ONLY accepted current delta is
    # withholding a Pages deployment token from unaccepted/fork source.
    viewer_guard = (
        "    # Fork PRs have no Pages/OIDC write token. Validate their GDS above and\n"
        "    # publish the viewer only from the canonical accepted default branch.\n"
        "    if: github.event_name != 'pull_request' && github.repository == 'gHashTag/tt-trinity-corona' && github.ref == 'refs/heads/main'\n"
    )
    expected_workflow = original_workflow.replace("  viewer:\n    needs: gds\n", "  viewer:\n    needs: gds\n" + viewer_guard)
    assert expected_workflow != original_workflow, "viewer guard was not applied"
    assert (root / ".github/workflows/gds.yml").read_text() == expected_workflow, "GDS workflow drift outside publication guard"
    actual_rtl = {str(p.relative_to(root)) for p in (root / "src/rtl").glob("*.v")}
    pinned_rtl = {p for p in provenance["sha256"] if p.startswith("src/rtl/")}
    assert actual_rtl == pinned_rtl, "RTL inventory drift"
    assert set(receipts) == set(provenance["receipts_sha256"]), "receipt inventory"
    for name, digest in provenance["receipts_sha256"].items():
        assert hashlib.sha256(receipts[name]).hexdigest() == digest, name

    spec = (root / "specs/corona/phase_a.t27").read_text()
    constants = dict(re.findall(r"pub const (\w+)\s*:\s*\w+\s*=\s*(\w+)\s*;", spec))
    values = {k: int(v, 0) for k, v in constants.items() if v not in ("true", "false")}
    assert values["TILE_COLUMNS"] * values["TILE_ROWS"] == values["TILE_COUNT"]
    tiles = re.search(r'tiles:\s*"(\d+)x(\d+)"', (root / "info.yaml").read_text())
    assert tiles and tuple(map(int, tiles.groups())) == (values["TILE_COLUMNS"], values["TILE_ROWS"])
    for k in ("FL002_PROMOTED", "SILICON_EXPECTED", "TIMING_SIGNOFF"):
        assert constants[k] == "false", k

    for kind in ("gds", "ci"):
        excerpt = json.loads(receipts[kind + "-log-excerpt.json"])
        assert excerpt["head_sha"] == provenance["source_commit"]
        assert excerpt["run_url"].endswith("/" + str(provenance[kind + "_run"]))
        assert excerpt["lines"] and len(excerpt["full_log_sha256"]) == 64
    gds = "\n".join(l["text"] for l in json.loads(receipts["gds-log-excerpt.json"])["lines"])
    ci = "\n".join(l["text"] for l in json.loads(receipts["ci-log-excerpt.json"])["lines"])
    cells = re.findall(r"\b(\d+)\s+2\.8E\+04 cells", gds)
    area = re.findall(r"Chip area for module.*?:\s*(\d+\.\d+)", gds)
    core = re.findall(r"Core area:\s*(\d+\.\d+) um\^2", gds)
    assert len(cells) == len(area) == len(core) == 1, "missing/ambiguous area receipt"
    assert int(cells[0]) == values["MAPPED_CELLS"]
    assert Decimal(area[0]) * 10000 == values["CELL_AREA_1E4"]
    assert Decimal(core[0]) * 10000 == values["CORE_AREA_1E4"]
    stat = json.loads(receipts["synthesis-stat.json"], parse_float=Decimal)["design"]
    assert stat["num_cells"] == values["MAPPED_CELLS"]
    assert stat["area"] * 10000 == values["CELL_AREA_1E4"]
    floor = json.loads(receipts["floorplan-metrics.json"], parse_float=Decimal)
    assert floor["design__instance__count"] == values["MAPPED_CELLS"]
    bbox = list(map(Decimal, floor["design__core__bbox"].split()))
    assert (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) * 10000 == values["CORE_AREA_1E4"]
    pdk = json.loads(receipts["pdk.json"])
    assert pdk["PDK"] == provenance["pdk"] == "gf180mcuD"
    assert pdk["PDK_VERSION"] == provenance["pdk_revision"]
    assert pdk["FLOW_NAME"] + " " + pdk["FLOW_VERSION"] == provenance["flow"]
    commit = json.loads(receipts["commit-id.json"])
    assert commit["commit"] == provenance["source_commit"]
    assert commit["workflow_url"].endswith("/" + str(provenance["gds_run"]))
    final = json.loads(receipts["final-metrics.json"])
    assert final["timing__setup_vio__count__corner:nom_ss_125C_3v00"] > 0
    assert "Precheck passed" in gds
    assert "Check for Magic DRC errors clear" in gds
    assert "Checker.SetupViolations" in gds, "timing caveat must remain visible"
    assert "Checker.MaxSlewViolations" in gds and "Checker.MaxCapViolations" in gds
    assert "PASS: anchor = 0x47C0" in ci and values["ANCHOR_VALUE"] == 0x47C0
    assert "claim-status-lint: PASS" in ci

    junit = ET.fromstring(receipts["results.xml"])
    cases = junit.findall(".//testcase")
    assert len(cases) == values["PRECHECK_CASES"], "precheck count"
    assert not junit.findall(".//failure") and not junit.findall(".//error")
    assert not junit.findall(".//skipped")
    assert {"KLayout GF180MCU DRC", "Antenna check"} <= {c.get("name") for c in cases}
    for name in ("drc_gf180mcuD.xml", "drc_antenna.xml", "drc_zero_area.xml",
                 "drc_pin_label_purposes_overlapping_drawing.xml"):
        report = ET.fromstring(receipts[name])
        assert report.tag == "report-database" and report.find("items") is not None
        assert len(report.find("items")) == 0, name


def main():
    provenance = json.loads((EVIDENCE / "provenance.json").read_text())
    receipts = {p.name: p.read_bytes() for p in (EVIDENCE / "receipts").iterdir()}
    validate(ROOT, provenance, receipts)
    # Rehash adversarial receipts so rejection depends on report contents too.
    controls = []
    bad = dict(receipts)
    bad["results.xml"] = bad["results.xml"].replace(b' time="192.43" />', b'><failure /></testcase>')
    controls.append(bad)
    bad = dict(receipts)
    bad["drc_gf180mcuD.xml"] = bad["drc_gf180mcuD.xml"].replace(b"<items>", b"<items><item />").replace(b"<items/>", b"<items><item /></items>")
    controls.append(bad)
    bad = dict(receipts)
    bad["gds-log-excerpt.json"] = bad["gds-log-excerpt.json"].replace(b"27980.019200", b"27981.019200")
    controls.append(bad)
    for changed in controls:
        assert changed != receipts, "negative control did not mutate a receipt"
        p = deepcopy(provenance)
        p["receipts_sha256"] = {k: hashlib.sha256(v).hexdigest() for k, v in changed.items()}
        try:
            validate(ROOT, p, changed)
        except AssertionError:
            continue
        raise AssertionError("corrupt Phase A receipt accepted")
    print("ALL PASS: Phase A source hashes, measured area, 12 prechecks, zero DRC items; 3 corrupt receipts rejected")


if __name__ == "__main__":
    main()
