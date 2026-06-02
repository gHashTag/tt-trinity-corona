# Corona docs — index

A single entry point to the project's documentation. (The repo root `README.md`
is the project overview; `PLAN.md` / `corona_plan.pdf` are the full plan.)

## Start here

1. [`../README.md`](../README.md) — what Corona is, the TRI-NET line, repo layout,
   the verification summary, and the claim-status discipline.
2. [`../PLAN.md`](../PLAN.md) — the full plan (also `../corona_plan.pdf`, 23 pages):
   architecture, ROM layout, tile budget, risk register, and the as-built
   resolution of the Section 10 planning questions.

## Specification (SSOT, read in this order)

The chip spec lives in `../specs/corona/*.t27` (Zig-like spec DSL):

1. [`corona_oracle.t27`](../specs/corona/corona_oracle.t27) — chip identity,
   cluster counts, status/cluster enums, `TOTAL_FORMATS = 80`.
2. [`rom_layout.t27`](../specs/corona/rom_layout.t27) — the 80-bit-per-record ROM
   bit layout (field offsets, encoding-kind enum, flags).
3. [`protocol.t27`](../specs/corona/protocol.t27) — 8-bit serial CMD/DATA protocol.
4. [`anchor.t27`](../specs/corona/anchor.t27) — the TG-TRIAD-X `0x47C0` cross-die anchor.
5. [`d2d_routing.t27`](../specs/corona/d2d_routing.t27) — die-to-die routing to Gamma (deferred; see ADR-0006).

The ROM is **generated** from the SSOT layout by `../tools/gen_rom.py`.

## Decisions (ADRs)

Architecture Decision Records in [`adr/`](adr/):

| ADR | Decision |
| --- | --- |
| [0001](adr/0001-tile-size-4x4.md) | Tile size 4x4 (16 tiles) |
| [0002](adr/0002-shuttle-ttgf26a.md) | Shuttle TTGF26a / GF180MCU |
| [0003](adr/0003-takum-tier-2.md) | Takum Tier-2 (ROM-only) |
| [0004](adr/0004-no-posit32-module.md) | No on-die Posit32 module |
| [0005](adr/0005-decimal-tier-2-software-oracle.md) | Decimal Tier-2 + software oracle |
| [0006](adr/0006-d2d-holographic-mesh-deferred.md) | D2D holographic mesh, deferred |
| [0007](adr/0007-license-apache-2.0.md) | License Apache-2.0 |
| [0008](adr/0008-preprint-sec-5-9-status.md) | Preprint Sec. 5.9 claim status |

[`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) maps the Phase-C scoping questions to
these ADRs (and notes how it relates to PLAN.md Section 10).

## Verification

- [`VERIFICATION.md`](VERIFICATION.md) — the evidence dossier: every decoder x
  five evidence layers (exhaustive sweep, independent reference, formal harness,
  post-silicon vector, mutation kill), the 18 CI gates, and total codes decoded.
- [`verification.json`](verification.json) — the same matrix as machine-readable
  data (for tooling / the preprint evidence table).

Both are **generated** from the test suite (`../tools/gen_verification_matrix.py`)
and freshness-gated, so they cannot drift.

## Status & claims

- [`CLAIM_STATUS.md`](CLAIM_STATUS.md) — the eight claim-status tags and the CI
  lint that enforces them.
- [`info.md`](info.md) — the TinyTapeout project datasheet.

## Loop reports

`REPORT_*.md` (100+ files) are the chronological development log — one per
recurring-loop iteration. They are historical context; the authoritative current
state is in the specs, ADRs, and `VERIFICATION.md` above.
