# tools/

## Verilog ROM emitter (Phase B, not yet implemented)

The primary toolchain artefact for Corona is a Verilog ROM emitter added to
`tools/gen_formats_catalog.py` in `gHashTag/t27` as the **17th output
language**. The emitter reads the 77-record SSOT from
`gHashTag/t27 specs/numeric/formats_catalog.t27` (PR #1028) and produces:

1. `src/rtl/format_rom.generated.v` -- a Verilog `case` statement
   over the 7-bit `format_index` address, returning the 80-bit record per
   `specs/corona/rom_layout.t27`.
2. `src/rtl/format_strings.generated.v` -- the ~500-byte ASCII string
   table referenced by `ref_index` in each record.
3. `tests/golden_rom_vectors.json` -- a 77-record reference dump for the
   `rom_readback` CI gate (Phase B).

## Why upstream in t27 and not here

The emitter belongs in `gHashTag/t27` `tools/` next to the other 16
language emitters because:

- the SSOT lives there
- the existing CI verifies every emitter produces deterministic, parseable
  output for the same SSOT
- this prevents emitter drift between repos

Corona will pin to a specific `t27` commit hash and verify the generated
RTL against `tests/golden_rom_vectors.json` on every push.

## Status

`[Spec]` -- emitter design is documented in PLAN.md Section 6 (Phase B).
No code has been written yet.
