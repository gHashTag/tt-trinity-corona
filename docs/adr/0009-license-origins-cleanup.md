# ADR-0009: License-Origins Cleanup in `corona_oracle.t27`

## Status

Accepted (2026-06-03). Resolves a documentation-vs-reality mismatch flagged by a
license audit on 2026-06-03.

## Context

The Tier-1 module table in `specs/corona/corona_oracle.t27` (the canonical t27
spec for the on-die oracle) listed third-party RTL origins for several decoders
that, in reality, do not exist in the repository:

- `posit8_decode`, `posit32_decode`, `bf16_decode`, `tf32_decode` — labelled
  "FloPoCo LGPL" in the spec.
- `lns8_decode` — labelled "Coleman log-add".
- `bcd_decode` — labelled "OpenCores LGPL".
- `takum16_decode` — listed as a Tier-1 slot pending an "R2 GATE" on Hunhold's
  VHDL license.

A direct audit of `src/rtl/*.v` shows the opposite:

- All 14 RTL files start with `// SPDX-License-Identifier: Apache-2.0` and are
  independent behavioural models authored in this repository.
- None of them link to or derive from FloPoCo, OpenCores, or Coleman log-add
  RTL. The LNS8 decoder is hand-rolled with a 16-entry antilog LUT; the BCD
  decoder is the trivial `tens*10 + ones` recombination.
- `takum16_decode.v` does not exist as RTL. The format ships Tier-2 ROM-only
  per ADR-0003. The slot in the Tier-1 list was a stale placeholder.

The single case where third-party numeric content is reused is `nf4_decode.v`,
which encodes 16 fp32 LUT constants — the quantiles of N(0,1) — published in
bitsandbytes (Tim Dettmers, MIT). The values are constants, not code; we treat
this as a de minimis reuse and credit bitsandbytes in the file header. No
copyleft contagion.

## Decision

1. Rewrite the comment block above `TIER1_MODULES` in `corona_oracle.t27` to
   state, accurately, that all on-die decoders are Apache-2.0 hand-rolled, and
   to credit bitsandbytes for the 16 NF4 LUT constants only.
2. Drop `takum16_decode` from `TIER1_MODULES` and shrink the array from 12 to
   11 entries; leave a one-line comment pointing to ADR-0003.
3. Update the inline comments on `posit64` and `lns` to remove "FloPoCo" and
   "Coleman" wording. (See file diff for the exact edits.)

## Consequences

- The spec now matches the RTL on disk; readers, packagers, and downstream
  reviewers (Hunhold included) see Apache-2.0 hand-rolled provenance.
- No code change to RTL; this is documentation-only.
- The R2 license gate is closed: Hunhold's VHDL is not imported and not needed.
  Future on-die takum work, if any, requires either an explicit licence grant
  from Hunhold or independent re-implementation. Today neither is on the
  critical path — takum is Tier-2 ROM-only per ADR-0003.

## Files touched

- `specs/corona/corona_oracle.t27` — see commit message of this ADR's commit
  for the exact diff.
- `docs/adr/0009-license-origins-cleanup.md` — this file.
