# Full-design lint triage -- TRI-NET dies (2026-06)

A `verilator --lint-only -Wall` from each die's silicon top (so only INSTANTIATED
logic is elaborated) was run as a broad weakness scan beyond the GoldenFloat units.
It found the `gf16_mul` rounding-overflow defect (loop 127; see
`tt-trinity-gamma/docs/GF_ARITH_FINDINGS.md`) and a set of `WIDTHTRUNC` warnings.
This doc triages every `WIDTHTRUNC` site: 10 are benign mask-extraction idioms; 1 is
a real bug.

## Benign (intentional, lossless) -- 10 sites

All are the Verilog-2005 "shift then mask to a narrow wire" idiom, where the mask
guarantees the truncated high bits are zero, so assigning to the narrow target loses
nothing:

| site | code | why safe |
| --- | --- | --- |
| `gf16_popcount.v:51-52` | `wire [1:0] ae = (a_row >> k*2) & 2'b11;` | mask 2'b11 -> only bits[1:0] can be set |
| `gf16_popcount16.v:43-44` | same | same |
| `vsa_matmul_8x8.v:49-50` | `wire [15:0] x = (reg >> gi*16) & 16'hFFFF;` | mask 16'hFFFF -> only bits[15:0] |
| `vsa_matmul_16x16.v:43-44` | `& 32'hFFFFFFFF` -> `[31:0]` | mask 32 bits |
| `blake3_anchor.v:80` | `m[i] <= (m_in >> i*32) & 32'hFFFFFFFF;` | 32-bit word extraction |
| `bitnet_encoder.v:57` | `temp = x >> (i*2); xe = temp[1:0];` | only `temp[1:0]` is ever read |

These can be silenced (size the mask, or slice explicitly) but are not defects.

## Real bug -- `bitnet_encoder.v:92` (neuron_base too narrow)

`bitnet_encoder` is a 64->32->8 ternary-MLP demo encoder, **instantiated on the
silicon top of Gamma (`tt_um_trinity_max_true`) and Euler
(`tt_um_ghtag_trinity_gf16`)** (not Phi). Layer 1 computes 32 hidden neurons:

```
function signed [15:0] ternary_dot; input [127:0] x; input [9:0] neuron_base; ...
    we = w_gen(neuron_base + i[5:0]);   // i = 0..63
...
for (k = 0; k < 32; k = k + 1) dot = ternary_dot(x_reg, k * 64);   // k*64 = 0..1984
```

`neuron_base` is **10-bit** but `k*64` reaches **1984** (11-bit) for k>=16, so it
truncates mod 1024. The collision map is exact:

```
k=16 -> 1024 -> 0   (== k=0)
k=17 -> 1088 -> 64  (== k=1)
...
k=31 -> 1984 -> 960 (== k=15)
=> all 16 upper neurons alias a lower one: h1[k] == h1[k-16]
```

Because `w_gen(addr)` is a pure function of `neuron_base + i`, identical
`neuron_base` yields an identical weight sequence and hence an identical dot product.
So the hidden layer realizes **16 distinct neurons, not 32** -- the nominal
architecture is not met.

**Severity: moderate / latent.** The weights are synthetic ("canned demo",
hash-derived `w_gen`), so there is no trained model whose accuracy this corrupts; and
any golden-vector test passes because it was captured from this same RTL. But the
demo does not compute the 64->32->8 projection it documents (effectively
64->16(dup)->8), and any future use with real weights would be wrong. It is on the
fabricated Gamma/Euler silicon (frozen).

**Fix (for a respin / next lineup):** widen the address path by one bit --
`input [10:0] neuron_base;` in `ternary_dot`, `input [10:0] addr;` in `w_gen`, and
pass `k * 11'd64`. That gives the full 0..2047 weight-address range and 32 distinct
neurons. The frozen module is left as taped out (source must match the die).

## Summary

The full-design lint surfaced **two real on-silicon bugs** -- `gf16_mul`
rounding-overflow (loop 127) and `bitnet_encoder` neuron-base aliasing (this loop) --
both the same root class: **a width one bit too short causing a wraparound**. Both
are on the instantiated hierarchy of shipped dies; both have a one-line fix staged
for a respin; both frozen sources are left untouched. The remaining 10 WIDTHTRUNC
flags are benign mask idioms. No other serious lint class (LATCH / UNDRIVEN /
MULTIDRIVEN / CASEINCOMPLETE) appears in any die's elaborated top.
