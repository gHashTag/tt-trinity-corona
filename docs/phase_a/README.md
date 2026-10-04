# Phase A: measured GF180MCU design fit

The historical GDS workflow is retained byte-for-byte in
`gds-workflow-source.yml`, under its original provenance hash. The current
workflow differs only by the guard that publishes Pages from canonical `main`.
Fork PRs still execute hardening, precheck and gate-level simulation; they cannot
publish Pages because GitHub withholds the OIDC write token. The receipt gate
rejects any workflow change outside this exact publication guard.

Issue: [#1](https://github.com/gHashTag/tt-trinity-corona/issues/1).
Acceptance policy: [phase_a.t27](../../specs/corona/phase_a.t27).
Evidence retrieved and checked on 2026-10-03 by dmitrii-f-t27.

## Scope and provenance

[Empirical fit] The existing **full Corona design**, including its ROM and
decoders, passed GF180MCU hardening and Tiny Tapeout precheck at source commit
`2a5eefc43ab28e74a07831cb56a77489a99c59d3`. This supersedes the preliminary
anchor/placeholder stub proposed in issue #1; no new stub run is asserted.
The flow was LibreLane 3.0.3, PDK `gf180mcuD`, open_pdks revision
`54435919abffb937387ec956209f9cf5fd2dfbee`.

- [GDS run 35509472314](https://github.com/gHashTag/tt-trinity-corona/actions/runs/35509472314)
  contains synthesis, floorplan, hardening, precheck and gate-level tests.
- [CI run 35509472285](https://github.com/gHashTag/tt-trinity-corona/actions/runs/35509472285)
  contains the anchor and claim-status-lint receipts at the same source commit.
- [provenance.json](provenance.json) pins all 19 RTL files, `info.yaml`, the GDS
  workflow, and receipt hashes. The numbered log excerpts retain the original
  lines as JSON strings; their full-download SHA-256 is recorded separately.
- The unmodified `synthesis-stat.json`, `floorplan-metrics.json`,
  `final-metrics.json`, `pdk.json` and `commit-id.json` come from `gds-files`
  artifact `10603829942`; the commit receipt binds that archive to this run.
- `receipts/*.xml` are unmodified upstream precheck reports from artifact
  `precheck_reports`, ID `10605055371`, in the GDS run. Third-party receipt text
  is preserved, including its original units and character set.

## Measurement and calculation

[Empirical fit] Values below come from Yosys technology-mapped synthesis and
OpenROAD floorplan output, not a generic-cell estimate.

| Quantity | Value | Source or calculation |
| --- | ---: | --- |
| Allocated tile | 4x4 = 16 tiles | `info.yaml`, floorplan/precheck template |
| Mapped cells | 1,356 | GDS log line 18270 |
| Mapped cell area | 27,980.0192 um^2 | GDS log line 18305 |
| Core area | 1,045,266.432 um^2 | GDS log line 18444 |
| Synthesis area / core area | 2.6768313% | 100 x 27,980.0192 / 1,045,266.432 |
| Allocated cells per tile | 84.75 | 1,356 / 16 |
| Allocated cell area per tile | 1,748.7512 um^2 | 27,980.0192 / 16 |
| GF180MCU DRC / antenna / zero-area / label overlap items | 0 each | Four KLayout XML `items` collections |
| Precheck cases | 12 pass, 0 fail/error/skip | `receipts/results.xml` |

The cells-per-tile row is **this design's allocation**, not a maximum capacity
measurement. It replaces use of the old 480-520 cells/tile estimate as a fit
criterion. No SKY130 comparison was run; a 2.1x density ratio cannot be inferred
from this design. Area fractions use the synthesis stage, excluding later
fillers, taps, buffers and routing changes. They are not final utilization.

## Exit-criteria reconciliation

| Original issue requirement | Verified disposition |
| --- | --- |
| GF180MCU PDK and DRC-clean stub | Full-design GF180MCU run supersedes stub; independent precheck XML has zero DRC items |
| Synthesis report in `docs/phase_a/` | This report and hashed synthesis excerpt |
| Cells-per-tile measurement | 84.75 allocated mapped cells/tile; capacity/density extrapolation explicitly excluded |
| Tile-size ADR | [ADR-0001](../adr/0001-tile-size-4x4.md); [original requested path](../adr/0001-tile-size.md) redirects there |
| Anchor CI gate | Same-head CI log: `0x47C0`, output enable `0xFF`, stable across ten cycles |
| Claim-status-lint | Same-head CI log: PASS; remains a CI job |

## Boundaries and remaining risks

[Risk] The GDS job warns about setup, maximum slew and maximum capacitance
violations. Its internal KLayout DRC metric is missing; the separate precheck
**did** run the GF180MCU KLayout deck and reported zero items. Both facts are
retained in the receipts. This report establishes digital Phase A area/DRC
viability, **not timing signoff**. Further timing work is required before any
future submission; do not infer 25 MHz operation at all corners from green CI.

Corona was not submitted or fabricated, as recorded in the current README.
This closes a digital exploration milestone only. FL-002 remains
[Open conjecture]. No new RTL, D2D implementation or hardware measurement is
introduced by this evidence reconciliation.

## Reproduce

```
make verify
make lint verilator-lint
make test
t27c parse specs/corona/phase_a.t27
t27c typecheck specs/corona/phase_a.t27
t27c gen specs/corona/phase_a.t27 > /tmp/corona-phase-a.zig
zig test /tmp/corona-phase-a.zig
t27c gen-rust specs/corona/phase_a.t27 > /tmp/corona-phase-a.rs
rustc --crate-type lib /tmp/corona-phase-a.rs
```

Compiler pin: `gHashTag/t27@db870cdf292272f373037fb40b607c4134f59474`,
Zig 0.16.0. The Rust backend emits declarations and policy; the Zig backend
executes all six spec test blocks. A successful parse or Rust compilation
alone does not establish that the tests ran. The receipt gate rejects changed
RTL/inventory, area drift, precheck failures and nonempty DRC results.

Retrieve originals with `gh run view RUN_ID --log` and
`gh run download 35509472314 -n precheck_reports -R gHashTag/tt-trinity-corona`.
CI also runs the GDS workflow against the proposed PR head.

## Executable proof chain (issue #12)

The measured design accepted in [PR #11](https://github.com/gHashTag/tt-trinity-corona/pull/11)
is unchanged. [Issue #12](https://github.com/gHashTag/tt-trinity-corona/issues/12)
adds a repeatable source/seal/vector check for `specs/corona/phase_a.t27`:

```sh
# T27_ROOT is a clean checkout at the compiler pin above; Zig 0.16.0 is on PATH.
make t27-test T27_ROOT=/path/to/pinned/t27
```

This builds the compiler from the pinned source, checks complete parsing and
types, executes six generated Zig tests, verifies the native seal under
`.trinity/seals/`, and compiles a Rust consumer that replays every committed
vector in `conformance/corona_phase_a.json`. The boundary matrix contains
4 cell counts x 10 independently classified area pairs x 3 DRC counts x
2 precheck states x 4 anchors x 2 lint states = **1,920 vectors**. Decimal
strings preserve exact u64 extremes in JSON. Rust compilation by itself is
not counted as replay.

Four typechecked, compiled source mutants (area equality, nonzero DRC,
missing precheck and inverted anchor) must fail the same runtime consumer.
A flipped vector expectation must fail it too; a copied seal over changed
source must fail the native verifier. The original receipt gate still runs.
CI invokes this same target and uploads `phase-a-proof` with the result and logs.

After an intentional source or vector-boundary change, regenerate vectors with
`python3 tools/phase_a_conformance.py --write-vectors`, then run the complete
gate with `--compiler-root /path/to/pinned/t27 --save-seal`. The gate invokes
the native `t27c seal --save` only after executable checks pass; normal
`make t27-test` verifies without changing committed vectors or seals.

This proof covers Phase A only. It does not claim executable coverage of the
other five descriptive Corona specs, timing signoff, fabricated silicon, or
game reward payment. The game must ingest the accepted evidence separately.

phi^2 + phi^-2 = 3 | TRINITY
