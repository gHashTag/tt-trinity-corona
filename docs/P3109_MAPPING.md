# P3109 ↔ Corona 80-Format Index Mapping

**Status:** `[Draft]` — pending IEEE P3109 Working Group review.

**Purpose:** establish a one-page cross-walk between the IEEE P3109 binary8
family (v3.2.1, draft, 2025) and the Corona 80-format conformance index.
This file lets P3109 WG members and silicon implementers see at a glance
which Corona ROM record covers each P3109 width, which encodings have a
silicon path on the TTGF26b Corona shuttle (GF180MCU 180 nm, submit
2026-06-22), and which records are catalog-only (no encode/decode RTL).

This document does **not** assert P3109 compliance. It is an
implementor's cross-reference intended to be reviewed and corrected by the
P3109 WG before any conformance claim is published.

## 1. Scope

- Corona is a read-only **format conformance oracle**. The chip ships a
  ~1.2-1.4 KB ROM encoding all 80 numeric-format records plus ~12-15
  reference RTL encode/decode modules for a subset of the catalog.
- This file maps the **P3109 binary8 p1..p7** family onto the existing
  Corona records. It does not introduce new records.
- The 80-record SSOT is
  [`gHashTag/t27` `specs/numeric/formats_catalog.t27`](https://github.com/gHashTag/t27/blob/master/specs/numeric/formats_catalog.t27).
- The 80-bit-per-record bit layout is
  [`gHashTag/tt-trinity-corona` `specs/corona/rom_layout.t27`](https://github.com/gHashTag/tt-trinity-corona/blob/main/specs/corona/rom_layout.t27).

## 2. P3109 binary8 family (draft v3.2.1)

The P3109 binary8 family is a parametric family of 8-bit ML floating-point
formats. Each format has `bits = 8`, `sign_bits = 1`, and an
exponent-mantissa split parameterised by a precision integer `p` from 1
to 7. The split below is the **draft** widely circulated in P3109 WG
materials; final field allocations and the bias convention (the
"bias reversal" applied in mid-2025) must be confirmed against the
ratified text before any conformance claim is made.

| P3109 ID | Sign | Exp | Mant | Notes (draft, WG to confirm)          |
|----------|:----:|:---:|:----:|---------------------------------------|
| binary8 p1 |   1  |  6  |  0   | extreme range, no fraction bits        |
| binary8 p2 |   1  |  5  |  1   |                                        |
| binary8 p3 |   1  |  4  |  2   | overlaps FP8 E4M3 family               |
| binary8 p4 |   1  |  3  |  3   |                                        |
| binary8 p5 |   1  |  2  |  4   |                                        |
| binary8 p6 |   1  |  1  |  5   |                                        |
| binary8 p7 |   1  |  0  |  6   | precision-heavy, no exponent range     |

**Note:** the FLoPS Lean formalization (Fitzgibbon, Wintersteiger,
Sarnoff; [arXiv:2602.15965](https://arxiv.org/abs/2602.15965)) gives the
authoritative machine-checked semantics. Where the two disagree, FLoPS
wins.

## 3. Corona 80-format index — relevant rows

The full catalog has 80 records. The subset most relevant to a P3109
cross-walk is reproduced below from
[`t27/specs/numeric/formats_catalog.t27`](https://github.com/gHashTag/t27/blob/master/specs/numeric/formats_catalog.t27)
(rows abridged; field names match the on-die ROM layout).

| Corona ID    | Cluster        | Bits | S | E | M | Encoding kind | Source / standard                                  |
|--------------|----------------|:----:|:-:|:-:|:-:|---------------|----------------------------------------------------|
| `fp8_e4m3`   | MlLowPrecision |   8  | 1 | 4 | 3 | fp            | OCP / NVIDIA / Arm / Intel; Micikevicius 2022      |
| `fp8_e5m2`   | MlLowPrecision |   8  | 1 | 5 | 2 | fp            | OCP / NVIDIA; Micikevicius 2022                    |
| `mxfp8`      | Microscaling   |   8  | 1 | 4 | 3 | mx            | OCP MX v1.0; Rouhani 2023 (arXiv:2310.10537)       |
| `mxfp6`      | Microscaling   |   6  | 1 | 3 | 2 | mx            | OCP MX v1.0                                         |
| `mxfp4`      | Microscaling   |   4  | 1 | 2 | 1 | mx            | OCP MX v1.0                                         |
| `posit8`     | PositUnumIII   |   8  | 1 | 2 | - | posit         | Posit Standard 2022 (es=2)                          |
| `takum8`     | PositUnumIII   |   8  | 1 | 0 | - | takum         | Hunhold 2024 (arXiv:2412.20273)                    |
| `GF8`        | GoldenFloat    |   8  | 1 | 3 | 4 | gf            | gHashTag/t27 `gf8.t27`                              |

## 4. P3109 ↔ Corona slot map (draft)

For each P3109 binary8 variant, the closest-fit Corona ROM slot, whether
the on-die RTL covers it, and which spec record carries the bias /
subnormal / rounding semantics. **Draft** — final mapping requires P3109
WG confirmation and a public diff against the ratified text.

| P3109 ID    | Closest Corona slot | Match    | RTL on TTGF26b? | Tier | Notes                                                                    |
|-------------|---------------------|----------|:---------------:|------|--------------------------------------------------------------------------|
| binary8 p1  | (no exact slot)     | partial  | no              | T3   | Pure range-heavy; closest is `fp8_e5m2` (E=5) but allocation differs.    |
| binary8 p2  | (no exact slot)     | partial  | no              | T3   | E=5 m=1 has no current 80-format entry; candidate for catalog addition.  |
| binary8 p3  | `fp8_e4m3` / `mxfp8`| field-exact (s/e/m) | yes (via Gamma) | T1 | Field widths coincide with FP8 E4M3; bias and saturate-vs-NaN may differ |
| binary8 p4  | (no exact slot)     | partial  | no              | T3   | E=3 m=3 has no current 80-format entry; candidate for catalog addition.  |
| binary8 p5  | (no exact slot)     | partial  | no              | T3   | E=2 m=4 has no current 80-format entry.                                  |
| binary8 p6  | (no exact slot)     | partial  | no              | T3   | E=1 m=5 has no current 80-format entry.                                  |
| binary8 p7  | (no exact slot)     | partial  | no              | T3   | E=0 m=6 has no current 80-format entry; degenerate towards integer.      |

Tier legend (mirrors `specs/corona/corona_oracle.t27`):

- **T1** — on-die RTL encode/decode + ROM record (silicon path).
- **T2** — ROM record only; no on-die RTL on this shuttle.
- **T3** — not currently in the 80-format index; candidate for a v2 addition.

## 5. P3109-binding column proposal

To make the P3109 cross-walk machine-readable, the 80-format catalog gets
one new optional field, populated only when a P3109 ID applies:

```
p3109_binding : enum {
    none,         // 0 -- no P3109 correspondence
    binary8_p1,   // 1
    binary8_p2,   // 2
    binary8_p3,   // 3
    binary8_p4,   // 4
    binary8_p5,   // 5
    binary8_p6,   // 6
    binary8_p7,   // 7
    pending,      // 15 -- WG review in progress
}
```

This consumes a 4-bit field. Two viable placements:

- **(a)** repurpose the four reserved bits in `FIELD_FLAGS [7:4]` of the
  existing 80-bit ROM record (see `rom_layout.t27`). Zero ROM-width
  increase; default value is `none` so existing test vectors unchanged.
- **(b)** add a sidecar 80×4-bit table outside the main ROM (40 bytes).
  Decouples P3109 churn from the frozen catalog ROM.

We propose **(a)** for the TTGF26b submission and a public CI gate
("`P3109_binding_consistency`") that fails if any Corona record claims a
P3109 ID whose field-widths do not match the ratified P3109 spec for that
precision.

## 6. What this is NOT

- **Not a compliance claim.** Corona has not been measured against
  ratified P3109 test vectors. The chip does not yet exist.
- **Not a P3109 endorsement of GoldenFloat.** The GF cluster is listed in
  the catalog as one of 13 clusters; the catalog is descriptive of the
  numeric landscape, not prescriptive about which family is "best".
- **Not a freeze of P3109 mapping.** Any ratified change to P3109 v3.2.1
  (or v3.3.x) will cause a corresponding diff to this file and to the
  `p3109_binding` field; pre-tape-out diffs are easy, post-tape-out diffs
  affect only this MD and the sidecar table, not the silicon.

## 7. Open questions for the P3109 WG

1. Is the binary8 p1..p7 field allocation in §2 the current draft text,
   or has the bias-reversal change of mid-2025 also shifted the
   exp/mant split?
2. For `binary8 p3` (E=4, m=2 in the draft above) vs the existing FP8
   E4M3 (E=4, m=3): does the WG view E4M3 as an out-of-family
   neighbour, or as `binary8 p3` with one extra precision bit?
3. Would the WG accept the `p3109_binding` 4-bit field as an
   informational catalog annotation (no normative weight)?
4. Is there a P3109 conformance test-vector pack we should compile against
   the Corona ROM and the (future) on-die `fp8_e4m3`/`mxfp8` RTL?

## 8. References

- IEEE SA P3109 working group (pre-ballot, draft v3.2.1, 2025).
- Fitzgibbon, Wintersteiger, Sarnoff. *Novel aspects of IEEE SA P3109 arithmetic formats for ML*. 2025.
- FLoPS Lean formalization of P3109: [arXiv:2602.15965](https://arxiv.org/abs/2602.15965).
- Micikevicius et al. *FP8 formats for deep learning*. 2022. [arXiv:2209.05433](https://arxiv.org/abs/2209.05433).
- Rouhani et al. *OCP MX shared microexponents*. 2023. [arXiv:2310.10537](https://arxiv.org/abs/2310.10537).
- Hunhold. *Integer representations of real numbers*. 2024. [arXiv:2412.20273](https://arxiv.org/abs/2412.20273).
- Posit Standard 2022, [posithub.org](https://posithub.org).
- Corona 80-format SSOT: [`gHashTag/t27` `specs/numeric/formats_catalog.t27`](https://github.com/gHashTag/t27/blob/master/specs/numeric/formats_catalog.t27).
- Corona 80-bit ROM layout: [`gHashTag/tt-trinity-corona` `specs/corona/rom_layout.t27`](https://github.com/gHashTag/tt-trinity-corona/blob/main/specs/corona/rom_layout.t27).

## 9. Contact

For corrections / WG feedback:
Dmitrii Vasilev — `admin@t27.ai` — GitHub [`@gHashTag`](https://github.com/gHashTag)
ORCID [0009-0008-4294-6159](https://orcid.org/0009-0008-4294-6159)
