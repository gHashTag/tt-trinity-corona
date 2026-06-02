# tt-trinity-corona

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
80 numeric-format records** from the TRI-NET SSOT, plus **18 Tier-1 RTL
decode modules** converting on-die formats to IEEE 754 FP32 (or INT32).
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
test/                     # cocotb tests (51) + SSOT/codegen/ROM-freshness cross-checks + GLS
formal/                   # SymbiYosys formal verification (19 configs, 58 tasks)
tools/                    # ROM emitter (gen_rom.py)
docs/                     # design notes, loop reports
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
| E | Conformance suite (51 cocotb + 57 formal tasks + 49 GL tests) | **Done** |
| F | LibreLane GDS + shuttle submission | **GDS+precheck PASS** |

## How to read this repo

1. Read `PLAN.md` (or `corona_plan.pdf`, 23 pages landscape A4) end-to-end.
2. Read the `.t27` SSOT files in `specs/corona/` in this order:
   `corona_oracle.t27` -> `rom_layout.t27` -> `protocol.t27` -> `anchor.t27`
   -> `d2d_routing.t27`.
3. Inspect the seven open questions in Section 10 of `PLAN.md` and answer them
   in `docs/adr/` before any RTL is written.

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

## Document version

`corona_plan-v1.0`, produced from `corona_research.md` (research) and
`corona_plan_skeleton.md` (skeleton). All claims carry an explicit status
tag. No claim is asserted without either a verifiable URL or an explicit
`[Open conjecture]` / `[Historical]` tag.
