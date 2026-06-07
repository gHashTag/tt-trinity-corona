# GoldenFloat ladder cross-reference (arXiv:2606.05017)

This document records the structural correspondence between three independent
artefacts:

1. The 80 numeric format records in the TRI-NET SSOT
   (`gHashTag/t27` `specs/numeric/formats_catalog.t27`) and the 17 Tier-1
   RTL decoders shipped in this repo (`src/rtl/*_decode.v`).
2. The GoldenFloat (GF) static-split floating-point family described in
   [arXiv:2606.05017](https://arxiv.org/abs/2606.05017)
   ("GoldenFloat: A Phi-Derived Static-Split Floating-Point Family from
   GF4 to GF256 with a Lucas-Exact Integer Identity", Vasiliev 2026,
   cs.AR).
3. The OCP MX format-parameter dictionaries in tenstorrent/tt-metal
   (`tt_metal/api/tt-metalium/mxfp8.hpp` and
   `tt_metal/impl/data_format/mxfp8.cpp`), specifically `kMxFp8E5M2Params`
   and `kMxFp8E4M3Params`.

The intent of this document is *narrow*: it records a mechanical mapping
that already exists in the artefacts. It does NOT promote the FL-002
phi-ladder breadth-as-moat conjecture in
`gHashTag/trios-trainer-igla` `src/ledger.rs`, which remains
**[Open conjecture]**. Corona being a registry chip and the GF ladder
being archived on arXiv do not change the FL-002 status.

## 1. Scope of correspondence

### 1.1 Formats covered by both Corona and arXiv:2606.05017

The arXiv paper covers the GF ladder from GF4 to GF256 by a single rule
`e = round((N-1)/phi^2), f = N-1-e` for total width `N >= 4`, where
`phi = (1+sqrt(5))/2`. The realised exponent widths reproduce nine
shipped formats (9 of 9) and extend consistently to GF128, GF512,
GF1024. The GF family is **owned by Gamma**
(`gHashTag/tt-trinity-gamma`); Corona stores ROM records for the GF
ladder but does NOT carry standalone arithmetic for it (the D2D path
routes arithmetic queries for `cluster_id == GF ladder` to Gamma; see
PLAN.md Section 2 and `specs/corona/d2d_routing.t27`). **[Spec]**

### 1.2 Formats Corona decodes Tier-1 and which appear in arXiv:2606.05017 only as comparison anchors

The arXiv paper compares the GF ladder to posit, takum, OCP-MX, and
IEEE P3109 multi-width float draft, "making no per-rung accuracy or
superiority claim against any of them" (paper abstract, verbatim).
Several of those comparison anchors are Tier-1 in Corona because
existing open-source RTL exists for them and they appear in the SSOT
catalog:

| Corona Tier-1 RTL                | Format family    | arXiv:2606.05017 role          | Tier in Corona ROM |
| -------------------------------- | ---------------- | ------------------------------ | ------------------ |
| `mxfp8_e4m3_decode.v`            | OCP MX FP8 E4M3  | Comparison anchor              | Tier-1             |
| `fp8_e5m2_decode.v`              | FP8 E5M2 (IEEE)  | Comparison anchor (FP8 family) | Tier-1             |
| `fp8_e4m3_fnuz_decode.v`         | FP8 E4M3 FNUZ    | Adjacent (FP8 family)          | Tier-1             |
| `bf16_decode.v`                  | bfloat16         | Adjacent (16-bit float family) | Tier-1             |
| `tf32_decode.v`                  | TF32             | Adjacent                       | Tier-1             |
| `mxint8_decode.v`                | OCP MX INT8      | Comparison anchor (MX family)  | Tier-1             |
| `posit8_decode.v`                | Posit-8          | Comparison anchor (posit)      | Tier-1             |
| `lns8_decode.v`                  | LNS-8            | Adjacent                       | Tier-1             |
| `nf4_decode.v`                   | NF4 (QLoRA)      | Adjacent (sub-byte)            | Tier-1             |
| `fp4_decode.v`                   | FP4              | Adjacent (sub-byte)            | Tier-1             |
| `fp6_e2m3_decode.v`              | FP6 E2M3         | Adjacent                       | Tier-1             |
| `fp6_e3m2_decode.v`              | FP6 E3M2         | Adjacent                       | Tier-1             |
| `int4_decode.v` / `int8_decode.v`| INT4 / INT8      | Adjacent                       | Tier-1             |
| `bitnet_decode.v`                | BitNet           | Adjacent (ternary)             | Tier-1             |
| `e8m0_decode.v`                  | E8M0 (MX scale)  | Comparison anchor (MX family)  | Tier-1             |
| `bcd_decode.v`                   | BCD              | Adjacent (legacy)              | Tier-1             |

Takum (Hunhold 2024
[arXiv:2412.20273](https://arxiv.org/abs/2412.20273)) is the standing
counterexample to FL-002. It ships in the Corona ROM as a Tier-2 record
and is not suppressed; see PLAN.md Section 7 (R2). **[Open conjecture]**

## 2. OCP MX FP8 cross-reference (Corona vs tt-metal)

This is the one cross-reference where two independent open-source
implementations of the same OCP MX FP8 sub-format exist in the same
ecosystem:

| Property                | Corona `mxfp8_e4m3_decode.v`           | tt-metal `kMxFp8E4M3Params` in `mxfp8.cpp` |
| ----------------------- | -------------------------------------- | ------------------------------------------ |
| Bit layout              | S1 E4 M3, one byte per element         | `elem_exp_bits = 4`, `elem_man_bits = 3`   |
| Exponent bias           | 7                                      | `elem_exp_bias = 7`                        |
| Infinity                | Not representable                      | `inf_rep = NotRepresentable`               |
| NaN                     | Only at `S.1111.111`                   | `nan_rep = ExpAllOnesManAllOnes`           |
| Max normal              | `(1 + 6/8) * 2^8 = 448`                | `elem_man_max = 0x6` (mant 0b111 reserved for NaN); `elem_sat_pos_bits = 0x7E` |
| Subnormal               | Decoded by leading-1 search (mant=001/01x/1xx, see `src/rtl/mxfp8_e4m3_decode.v` line 25-50) | OCP-standard subnormals; `elem_exp_subnorm_encoding = 0` |
| Block size (OCP MX)     | N/A (Corona decodes a single element)  | `block_size = 32`                          |
| Block scale             | N/A (Corona does not consume E8M0; that is `e8m0_decode.v`'s job) | `scale_bias = 0x7F`, E8M0           |

The two implementations are **byte-compatible at the element level**.
Corona is a per-element decoder; tt-metal's `mxfp8.cpp` is a host-side
block packer that uses the same per-element bit layout and then groups
32 elements with one E8M0 scale per block (the OCP MX v1.0 layout from
[Rouhani et al. arXiv:2310.10537](https://arxiv.org/abs/2310.10537)).
**[Empirical fit]**

A small cross-check tool that exercises this correspondence is provided
at `tools/mxfp8_e4m3_corona_vs_ttmetal.py`. It re-implements the Corona
RTL decode algorithm in Python and compares each of the 256 possible
E4M3 byte values to a FP32 reference. It does NOT call tt-metal directly
(tt-metal is a C++ library with a hardware backend); it documents the
parameter set that Corona and tt-metal share, and runs the Corona
algorithm against it. **[Spec]** Running tt-metal's actual pack/unpack
against Corona requires a tt-metal build environment and is out of scope
for this repo.

## 3. The GF ladder and the on-die ROM

The Corona ROM stores all 80 SSOT format records; the GF ladder
(GF4..GF256 + variants, 16 records per PLAN.md Section 3 cluster
inventory) is the largest single cluster. Each record carries:

- `format_index` (7 bits): index used on `ui_in[6:0]`.
- bit-layout fields (sign, exponent, mantissa widths, total width).
- `cluster_id`: maps to the GF ladder for GF4..GF256.
- `status_id`: claim-status enum.
- `phi_distance_q16` (16 bits, Q16 fixed point): distance from the
  format's dynamic range or precision to the nearest phi-ladder rung.

The `phi_distance_q16` field is **a distance metric, not a claim of
superiority**. PLAN.md Section 4.3 explicitly states this:

> The `phi_distance_q16` field [...] is NOT a claim that phi-ladder
> rungs are superior, only that a distance metric exists. The
> `status_id` field, not `phi_distance_q16`, is the authoritative
> epistemic tag for each record. **[Open conjecture]**

The arXiv paper makes the matching disclaimer (verbatim from the
abstract):

> The rule is positioned alongside posit, takum, OCP-MX, and the IEEE
> P3109 multi-width float draft. We make no per-rung accuracy or
> superiority claim against any of them. The breadth/toolchain-coherence
> framing is recorded as an open conjecture with a pre-registered
> falsification path.

Both texts are aligned. Neither artefact promotes FL-002 beyond
**[Open conjecture]**.

## 4. The TG-TRIAD-X anchor and `phi^2 + phi^-2 = 3`

The TG-TRIAD-X cross-die anchor `{uio_out, uo_out} == 16'h47C0`,
documented in PLAN.md Section 2.3 and `specs/corona/anchor.t27`, derives
from `dot4(1, 2, 3, 4)` over GF16, where GF16 is implied by the Lucas
identity `phi^2 + phi^-2 = 3 = L_2`. The Lucas identity itself is
classical (Binet-formula corollary, 1878) and not original to this
project. The arXiv paper uses the same Lucas-exact integer accumulator
path (paper abstract item (ii)): "an integer-backed Lucas-exact
accumulator path verified at 500-digit precision for n = 1, ..., 256".

The anchor is independent of any specific format and serves as a
sameness-check across all four chips in the TRI-NET line; it carries
forward unchanged from Phi, Euler, Gamma to Corona. **[Verified in sim]**
The status remains **[Open conjecture]** until all four dice are
measured together post-silicon.

## 5. Erratum carried from arXiv:2606.05017

The arXiv paper records an RTL-correctness erratum dated 2026-05-31:

> An RTL-correctness erratum dated 2026-05-31 is reported; the
> fabricated TTSKY26b dies carry the defective multiplier portfolio,
> and the corrected generator is the regeneration baseline.

This erratum concerns the GF ladder multipliers shipped in the
TTSKY26b silicon (Phi, Euler, Gamma). Corona on TTGF26a does NOT carry
the GF multipliers (the GF arithmetic cluster is owned by Gamma; Corona
routes via D2D, see `specs/corona/d2d_routing.t27`). The erratum is
recorded here for traceability between the arXiv paper and the silicon
delivery chain; it does not affect the Corona RTL deliverables.
**[Spec]**

For the matching corona-line fix on the Gamma side, see
`gHashTag/tt-trinity-corona` Loop 121 (ADR-0009, commit `80c0acd` on
the companion `gHashTag/tt-trinity-corona` upstream and on the
`gHashTag/tt-trinity-gamma` line; the corrected multiplier portfolio is
the regeneration baseline). **[Empirical fit]**

## 6. What this cross-reference does and does not authorize

This document authorizes:

1. Citing arXiv:2606.05017 in this repo, PLAN.md, and downstream
   documentation as the archival reference for the GF static-split rule
   and the Lucas-exact integer accumulator path.
2. Documenting that 16 of the 17 Corona Tier-1 RTL decoders fall into
   one of three roles relative to the arXiv paper: comparison anchor,
   adjacent format, or sub-byte family member.
3. Recording that the `phi_distance_q16` ROM field is a metric, not a
   claim.

This document does NOT authorize:

1. Any claim that the GF ladder is superior to MX, posit, takum, or
   P3109 on any per-rung axis.
2. Any change to FL-002's status. FL-002 remains
   **[Open conjecture]**; this document records additional artefacts
   but does not provide a falsification or a promotion.
3. Any change to the takum line. Takum remains the standing
   counterexample; its Tier-2 ROM record is preserved and is not
   suppressed (PLAN.md Section 7 R2).
4. Any silent edit of the arXiv paper's stated comparison framing.

## 7. References

- Vasiliev, D. (2026). *GoldenFloat: A Phi-Derived Static-Split Floating-Point Family from GF4 to GF256 with a Lucas-Exact Integer Identity*. [arXiv:2606.05017](https://arxiv.org/abs/2606.05017) (cs.AR).
- Rouhani, B. et al. (2023). *OCP Microscaling Formats (MX) v1.0*. [arXiv:2310.10537](https://arxiv.org/abs/2310.10537).
- Hunhold, L. (2024). *Takum Arithmetic*. [arXiv:2412.20273](https://arxiv.org/abs/2412.20273).
- IEEE P3109 working group draft, multi-width float format (in progress, no public archive ID at the time of writing). **[Spec]**
- `tt_metal/api/tt-metalium/mxfp8.hpp` and `tt_metal/impl/data_format/mxfp8.cpp` in `tenstorrent/tt-metal`.
- Corona PLAN.md Sections 1.3, 2.3, 3, 4.3, 7 R2.
