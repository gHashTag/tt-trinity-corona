# src/tb/

cocotb testbenches. **Phase E deliverable -- not yet populated.**

## Planned CI gates (per PLAN.md Section 11.6)

| Gate | What it checks | Phase introduced |
| --- | --- | --- |
| `t27c_parse`           | t27c parser clean on `specs/corona/*.t27` | A |
| `rom_generate`         | Verilog ROM emitter runs without error; output deterministic | B |
| `rom_readback`         | 80-record sweep; zero bit errors vs PR #1028 golden reference | B (gate) |
| `anchor_test`          | `format_index = 7'h7F -> 0x47C0` in sim | A |
| `synth_area`           | OpenLane2 synthesis area report per module; tile utilization | C (gate) |
| `module_roundtrip`     | Per-module encode/decode round-trip, 10k random vectors, >=99.9% pass | C (gate) |
| `d2d_routing_sim`      | D2D routing sim with Gamma behavioral model; 10 cross-die pairs | D (gate) |
| `conformance_suite`    | Full Phase E conformance suite; zero failures; HTML report | E (gate) |
| `claim_status_lint`    | All claims in RTL/test/md carry a valid claim-status tag | A (perma-check) |
| `openlane2_drc`        | Full OpenLane2 DRC + LVS on final GDS; zero violations | F (gate) |
