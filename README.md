# tt-trinity-corona

![verification](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/gHashTag/tt-trinity-corona/main/docs/verification-badge.json)

TRI-1 Corona -- Format Conformance Oracle (TTGF26a / GF180MCU).

The fourth chip in the TRI-NET line, after Phi, Euler, and Gamma. Corona is a
**read-only conformance oracle**, not a compute accelerator.

| Field | Value |
| --- | --- |
| Shuttle | TTGF26a (TinyTapeout, GF180MCU 180nm) |
| Submission target | 2026-06-22 (TTGF26a close) |
| Expected silicon | 2026-10 to 2026-11 |
| Tile size | 4x4 (16 tiles) |
| Document status | Submission-ready (17 decoders, 51 tests PASS, GDS+precheck PASS) |
| SSOT | `gHashTag/t27 specs/numeric/formats_catalog.t27` (PR #1028, issue #1029) |
| License | Apache-2.0 |
| Contact | admin@t27.ai, ORCID 0009-0008-4294-6159 |

## What Corona is

A silicon chip whose primary deliverable is a **~800-byte ROM encoding all
80 numeric-format records** from the TRI-NET SSOT, plus **17 Tier-1 RTL
decode modules** (covering 18 format families; FP8 E4M3 reuses the MXFP8 E4M3
decoder) converting on-die formats to IEEE 754 FP32 (or INT32).
A query arrives as a 7-bit format index on `ui_in[6:0]`; the chip
returns the requested record fields or decoded value across `uo_out`
over N read cycles. Synthesizes to 2,308 cells (~1% of 4x4 site budget).

The second function of Corona is to serve as the **17th output language** of
`tools/gen_formats_catalog.py` in `gHashTag/t27`. The Verilog ROM emitter
(produced as a PR to `t27`) is the primary toolchain artifact; the silicon
chip is its validation. This makes the chain SSOT -> codegen -> RTL ->
silicon end-to-end mechanical.

## What Corona is NOT (honest disclaimers)

- **NOT a compute-performance entry.** It makes no claims about TOPS,
  throughput, or energy per operation, and no comparison against any other
  ML accelerator chip should be drawn from its existence.
- **NOT evidence that the phi-ladder or goldenfloat formats are superior to
  any competitor numeric system.** The FL-002 moat claim
  (`gHashTag/trios-trainer-igla src/ledger.rs`) stays
  **[Open conjecture]** and Corona does not change that status.
- **NOT a closed-IP product.** All RTL, ROM generation scripts, and
  testbenches are open-source under Apache 2.0.
- **NOT a complete numeric co-processor.** It exposes format metadata
  for all 80 formats and performs encode/decode only on the Tier-1 module
  subset. For formats owned by Gamma (GF4..GF256, FP8, INT4/8, NF4, Posit16,
  BitNet), the correct compute answer requires D2D routing to Gamma.
- **Takum** (Hunhold 2024 [arXiv:2412.20273](https://arxiv.org/abs/2412.20273))
  remains the **standing counterexample** to FL-002 and SHIPS in the Corona
  ROM as a Tier-2 record (or Tier-1 if Hunhold VHDL licensing resolves
  favorably). It is **not suppressed**.

## The governing sentence

> The goldenfloat ladder earns its place through **breadth and toolchain
> coherence** across many numeric formats, NOT through per-rung superiority
> over any individual competitor format.

Claim status of the sentence itself: **[Open conjecture]**.

## TRI-NET line

| Chip | Repo | Shuttle / PDK | Tile | Role | Status |
| --- | --- | --- | --- | --- | --- |
| Phi | `gHashTag/tt-trinity-phi` | TTSKY26b / SKY130A | 1x1 | Identity baseline | [Verified] |
| Euler | `gHashTag/tt-trinity-euler` | TTSKY26b / SKY130A | 8x2 | Safety boundary | [Empirical fit] |
| Gamma | `gHashTag/tt-trinity-gamma` | TTSKY26b / SKY130A | 8x4 | Ternary mesh compute (submitted 2026-05-17) | [Empirical fit] |
| **Corona** | `gHashTag/tt-trinity-corona` | **TTGF26a / GF180MCU** | 4x4 | Format-completeness oracle | **[Empirical fit]** |

## The TG-TRIAD-X cross-die anchor

```
{uio_out, uo_out} == 16'h47C0
```

Derived from `dot4(1, 2, 3, 4)` over GF16 implied by `phi^2 + phi^-2 = 3 = L_2`.
A mechanical identity, not a format-specific result. Carries forward unchanged
from Phi / Euler / Gamma to Corona. Status: **[Verified in sim]**, **[Open
conjecture]** until all four dice are measured together post-silicon.

## Repository layout

```
specs/corona/             # SSOT: chip spec in .t27 (Zig-like spec DSL)
  corona_oracle.t27       # top-level chip identity + cluster counts
  rom_layout.t27          # 80-bit-per-record ROM bit layout
  protocol.t27            # 8-bit serial CMD/DATA on TinyTapeout pins
  anchor.t27              # TG-TRIAD-X 0x47C0 anchor
  d2d_routing.t27         # die-to-die routing to Gamma
src/rtl/                  # 19 Verilog modules (top + ROM + 17 decoders)
test/                     # cocotb (51) + SSOT/ROM/anchor/fmt_id + 17/17 decoders + post-silicon vectors + GLS
formal/                   # SymbiYosys formal verification (19 configs, 57 tasks)
tools/                    # ROM emitter (gen_rom.py) + cross-checks
docs/                     # design notes, loop reports, VERIFICATION.md; see docs/README.md (index)
PLAN.md                   # full plan (also corona_plan.pdf, 23 pages)
info.yaml                 # TinyTapeout chip metadata
```

## Claim-status discipline

Every numeric or quality claim in this repo carries an explicit tag:

| Tag | Meaning |
| --- | --- |
| `[Verified]` | RTL tested in simulation and confirmed on physical silicon |
| `[Empirical fit]` | Passes test suite; theoretical grounding partial |
| `[Open conjecture]` | Not yet falsified; counterexamples may exist |
| `[Risk]` | Used in practice but known failure modes documented |
| `[Retracted]` | Previously claimed, subsequently falsified |
| `[Experimental]` | Prototype stage only; no production validation |
| `[Historical]` | Legacy format; no active toolchain; included for completeness |
| `[Spec]` | Definition only; no known open-source implementation |

The CI job `claim_status_lint` enforces that every claim in `.t27`, `.v`,
`.py`, and `.md` files carries a valid tag.

## Phase plan (decomposed in PLAN.md)

| Phase | What | Status |
| --- | --- | --- |
| A | GF180MCU PDK exploration + tile-size decision (4x4) | **Done** |
| B | Verilog ROM emitter (80 records, 10 bytes each) | **Done** |
| C | Tier-1 RTL decoders (17 modules) + formal verification | **Done** |
| D | D2D wiring + Gamma routing simulation | Deferred |
| E | Conformance suite (51 cocotb + 57 formal tasks + 76 GL tests) | **Done** |
| F | LibreLane GDS + shuttle submission | **GDS+precheck PASS** |

## Verification

Every Tier-1 decoder is validated by **five independent evidence layers**, so a
bug shared between the RTL and any single reference model cannot hide:

1. **Exhaustive sweep** — all `2^width` input codes decoded and checked (cocotb +
   iverilog); **592,308** codes total across the 17 decoders.
2. **Independent reference** — a spec-derived decoder written separately from the
   RTL (QLoRA, OCP MX/OFP8, Posit Standard, IEEE, two's complement, BitNet b1.58…),
   so the RTL is checked against external truth, not just its own model.
3. **Formal harness** — `formal/fv_*.sv` checks decoder == golden over *all* inputs
   (`anyconst` + SMT); each golden is cross-checked to the independent reference.
4. **Post-silicon vector** — the RP2350 bring-up oracle's expected values are
   **generated** from the independent references (`tools/gen_postsilicon_vectors.py`),
   so they cannot be wrong-by-transcription.
5. **Mutation kill** — a fault injected into each decoder is confirmed to be
   detected, so no check is vacuous.

These layers, the per-decoder evidence matrix, and the **21 CI cross-check gates**
that enforce them are documented in [`docs/VERIFICATION.md`](docs/VERIFICATION.md)
(with a machine-readable [`docs/verification.json`](docs/verification.json) for
tooling) — both generated from the test suite and freshness-gated, so they cannot
drift.

## How to read this repo

0. For a map of all documentation (specs, ADRs, verification dossier), start at
   [`docs/README.md`](docs/README.md).
1. Read `PLAN.md` (or `corona_plan.pdf`, 23 pages landscape A4) end-to-end.
2. Read the `.t27` SSOT files in `specs/corona/` in this order:
   `corona_oracle.t27` -> `rom_layout.t27` -> `protocol.t27` -> `anchor.t27`
   -> `d2d_routing.t27`.
3. The seven Phase-A open questions (PLAN.md Section 10) are all decided and
   recorded as ADRs in `docs/adr/` (see `docs/OPEN_QUESTIONS.md` for the Q->ADR map).

## Permanent anchors (verbatim, not to be paraphrased)

- TG-TRIAD-X anchor: `{uio_out, uo_out} == 16'h47C0` derived from
  `dot4(1,2,3,4)` over GF16 implied by `phi^2 + phi^-2 = 3 = L_2`.
- DOI [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)
  (hardware archive only, never results).
- SSOT: `gHashTag/t27` `specs/numeric/formats_catalog.t27`
  (PR #1028, commit `18ae35a`, branch `feat/formats-catalog-ssot-77-formats`),
  issue #1029.
- Codegen: `tools/gen_formats_catalog.py` (16 languages in PR #1028;
  Corona adds Verilog ROM emitter = 17th).
- FL-002 ledger: `gHashTag/trios-trainer-igla` `src/ledger.rs`; stays
  **[Open conjecture]**; takum
  ([arXiv:2412.20273](https://arxiv.org/abs/2412.20273)) is the standing
  counterexample.
- Author / contact email: admin@t27.ai. ORCID: 0009-0008-4294-6159.

## External archival reference

The GoldenFloat (GF) static-split floating-point family that defines the
`GF ladder` cluster in the SSOT is archived on arXiv as
[arXiv:2606.05017](https://arxiv.org/abs/2606.05017) (cs.AR, 2026-06-03).
Corona is the registry chip for the catalog the paper describes; the
arithmetic for the GF ladder lives on `gHashTag/tt-trinity-gamma` and is
routed via D2D (see `specs/corona/d2d_routing.t27`).

For the structural mapping between the 17 Corona Tier-1 decoders, the GF
ladder rule from arXiv:2606.05017, and the OCP MX FP8 parameter dictionaries
in `tenstorrent/tt-metal` (`tt_metal/api/tt-metalium/mxfp8.hpp`,
`tt_metal/impl/data_format/mxfp8.cpp`), see
[`docs/goldenfloat_ladder_crossreference.md`](docs/goldenfloat_ladder_crossreference.md).

This cross-reference does NOT change the status of the FL-002 phi-ladder
breadth-as-moat conjecture, which remains **[Open conjecture]**. Takum
([arXiv:2412.20273](https://arxiv.org/abs/2412.20273)) remains the standing
counterexample and is shipped in the Corona ROM, not suppressed (PLAN.md
Section 7 R2).

## Document version

`corona_plan-v1.0`, produced from `corona_research.md` (research) and
`corona_plan_skeleton.md` (skeleton). All claims carry an explicit status
tag. No claim is asserted without either a verifiable URL or an explicit
`[Open conjecture]` / `[Historical]` tag.
