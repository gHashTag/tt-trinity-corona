# src/rtl/

Verilog source. **Phase C deliverable -- not yet populated.**

## Planned modules (Phase C)

```
tt_um_trinity_corona.v             -- TinyTapeout top-level wrapper
format_rom.generated.v             -- 80-record ROM (Phase B codegen)
format_strings.generated.v         -- string table for ref_index
anchor_probe.v                     -- TG-TRIAD-X 0x47C0 emitter

# Tier-1 converters (target: 12-15 modules; see PLAN.md Section 4.2)
posit8_decode.v
posit32_decode.v
bf16_decode.v
tf32_decode.v
mxfp8_e4m3_decode.v
lns8_decode.v
decimal32_decode.v
fp4_decode.v
fp6_decode.v
nf4_decode.v
bcd_decode.v
takum16_decode.v                   -- conditional on R2 license confirmation
```

## RTL-freeze invariant

Once Phase C completes, every `.v` file in this directory becomes immutable
until Phase F tape-out. A bug fix after Phase C freeze requires:

1. updating the SSOT (PR to `gHashTag/t27`),
2. re-running Phase B codegen,
3. re-running ALL Phase C and Phase E CI before Phase F proceeds.

This contract is enforced at the `gHashTag/t27` module-library level; see
`specs/corona/d2d_routing.t27` Section 3.
