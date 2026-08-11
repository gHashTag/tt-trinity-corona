# Cross-Format Guide for P3109 Reviewers

**Status:** `[Draft, external contribution]` -- prepared for the IEEE-SA
P3109 Working Group at editor invitation.
**Author:** Dmitrii Vasilev (Trinity S3AI), ORCID 0009-0008-4294-6159,
admin@t27.ai.
**Sources:** `gHashTag/t27` (SSOT catalog),
`gHashTag/tt-trinity-corona` (frozen ROM snapshot),
`playra/numeric-format-catalog` and `playra/numeric-conformance-packs`
(Hugging Face datasets, v3).
**License:** Apache-2.0 (this guide), CC-BY-4.0 (datasets), CC0 (SSOT
catalog file). No NDA. No proprietary material.

This is a **reader's guide**, not a conformance document. It answers a
single question: if you are reviewing a P3109 binary8 record and want to
see how it lines up with adjacent 8-bit formats used in industry
(FP8 E4M3, FP8 E5M2, OCP Microscaling MXFP8, IEEE binary16 tail slices,
posit8, takum8), where do you look, what do you trust, and what is still
open? The tone is deliberately flat. Nothing here asserts that P3109
compliance can be measured against these artifacts; only that a
cross-format index exists and is public.

The P3109 repository header states that its material must not be used
for any conformance or compliance purpose. This guide honours that: it
provides pointers only, and every claim below is either a direct link
to a versioned artifact or is labelled `[open]`.

---

## 1. What the cross-format catalog is

The catalog is a plain-text SSOT file, one record per format, hand-audited
and versioned in Git:

- **SSOT canon (live, 83 records):**
  [`gHashTag/t27` `specs/numeric/formats_catalog.t27`](https://github.com/gHashTag/t27/blob/master/specs/numeric/formats_catalog.t27)
- **Frozen ROM snapshot (silicon, 80 records):**
  [`gHashTag/tt-trinity-corona` `specs/corona/rom_layout.t27`](https://github.com/gHashTag/tt-trinity-corona/blob/main/specs/corona/rom_layout.t27)
- **HF catalog (v3, Croissant 1.0, 83 records):**
  [playra/numeric-format-catalog](https://huggingface.co/datasets/playra/numeric-format-catalog)
- **HF conformance packs (v3, 83 records with test vectors and gap
  annotations):**
  [playra/numeric-conformance-packs](https://huggingface.co/datasets/playra/numeric-conformance-packs)

The 83/80/77 discrepancy across artifacts is a known and documented
provenance history, not a versioning bug. See
[`docs/FORMAT_COUNT_PROVENANCE.md`](https://github.com/gHashTag/tt-trinity-corona/blob/main/docs/FORMAT_COUNT_PROVENANCE.md)
for the exact commit trail. In short: 83 = live SSOT canon,
80 = silicon-frozen snapshot from PR #1028 (commit `18ae35a`),
77 = stale generated JSON from an earlier snapshot. When in doubt, treat
83 as canon and cite the exact commit hash of the SSOT you consulted.

Each SSOT record carries: `name`, `bits`, `sign_bits`, `exp_bits`,
`mant_bits`, `bias`, `special_values` (Inf, NaN, subnormal handling),
`endianness`, and a free-text `notes` field. Records are not RTL; RTL
lives beside the catalog in `specs/corona/` and in the Corona chip. The
catalog is a **naming and layout registry**, not a semantics
specification. Semantics for P3109 binary8 are governed by the P3109
draft text and, for the machine-checked slice, by the FLoPS Lean
formalization (see Section 6).

---

## 2. P3109 binary8 family: pointer map

The following table lists the P3109 binary8 p1..p7 records currently
present in the SSOT. **Field allocations shown are from the widely
circulated draft v3.2.1 material and must be confirmed against the
ratified P3109 text before any downstream use.** Both bias conventions
seen in P3109 WG discussion (pre- and post- "bias reversal") are noted
where they materially change the record.

| P3109 ID     | Sign | Exp | Mant | SSOT record name (t27) | Notes                             |
|--------------|:----:|:---:|:----:|------------------------|-----------------------------------|
| binary8 p1   |   1  |  6  |  0   | `p3109_binary8_p1`     | draft, WG to confirm bias sign    |
| binary8 p2   |   1  |  5  |  1   | `p3109_binary8_p2`     | draft                             |
| binary8 p3   |   1  |  4  |  2   | `p3109_binary8_p3`     | overlaps FP8 E4M3 family, see 3.1 |
| binary8 p4   |   1  |  3  |  3   | `p3109_binary8_p4`     | draft                             |
| binary8 p5   |   1  |  2  |  4   | `p3109_binary8_p5`     | draft                             |
| binary8 p6   |   1  |  1  |  5   | `p3109_binary8_p6`     | draft                             |
| binary8 p7   |   1  |  0  |  6   | `p3109_binary8_p7`     | precision-heavy, no exponent range|

`[open]` The exact bias convention adopted by the ratified P3109 text is
not encoded in this guide. When the text is finalised, the SSOT records
above will be updated in a single commit with the diff attached to the
change log.

For a side-by-side field-level view including all cross-format neighbours,
see [`docs/P3109_MAPPING.md`](https://github.com/gHashTag/tt-trinity-corona/blob/main/docs/P3109_MAPPING.md)
in this repository.

---

## 3. Cross-walks to neighbouring 8-bit formats

### 3.1 FP8 E4M3 (NVIDIA/Arm/Intel joint spec, 2022)

`p3109_binary8_p3` and FP8 E4M3 share the (1, 4, 3) sign/exp/mant split.
They are not identical: FP8 E4M3 uses a bias of 7 with no Inf and a
single NaN pattern (`S 1111 111`), while the P3109 draft assigns
different special-value semantics that must be read off the ratified
text. This overlap is the single most likely source of implementor
confusion in the 8-bit tier; the honest position is that they share
field widths but diverge on special-value handling.

Worked example, in Section 5, walks the reader through the exact FP8
E4M3 overflow representation and shows how the same bit pattern would be
interpreted under the draft P3109 binary8 p3 semantics.

### 3.2 FP8 E5M2 (NVIDIA/Arm/Intel joint spec, 2022)

FP8 E5M2 (1, 5, 2) sits between `p3109_binary8_p2` (1, 5, 1) and
`p3109_binary8_p3` (1, 4, 2) by field width. FP8 E5M2 keeps IEEE 754
binary16 conventions (Inf, quiet/signalling NaN, subnormals) truncated
to 8 bits, and is therefore closest in spirit to IEEE tail slices rather
than to the P3109 family. Cross-walk: SSOT `fp8_e5m2` versus SSOT
`p3109_binary8_p2` and `p3109_binary8_p3`.

### 3.3 OCP Microscaling (MX) family

OCP MX (arXiv:2310.10537) defines block-scaled 8-bit formats -- MXFP8
E4M3, MXFP8 E5M2, MXFP6, MXFP4, MXINT8 -- with a shared 8-bit exponent
scale per K-element block. In the SSOT, MX formats are stored as
individual per-element format records (`mxfp8_e4m3`, `mxfp8_e5m2`,
`mxfp6_e2m3`, `mxfp6_e3m2`, `mxfp4_e2m1`, `mxint8`) with the block
scale as a separate record. P3109 binary8 has no in-scope block-scale
mechanism; the comparison is per-element only.

### 3.4 Posit8 and takum8

Posit8 (Gustafson, 2017) and takum8 (Hunhold, arXiv:2412.20273, v2 2025)
are alternative tapered-precision 8-bit formats. They are present in the
SSOT (`posit8_es0`, `posit8_es1`, `posit8_es2`, `takum8`) so a P3109
reviewer can see the whole 8-bit landscape in one file. No claim of
interoperability with P3109 is made; the records are neighbours in the
catalog, not siblings in semantics.

---

## 4. Test vector packs

The [playra/numeric-conformance-packs](https://huggingface.co/datasets/playra/numeric-conformance-packs)
v3 dataset ships a JSONL pack per format containing:

- Field layout (redundant with the catalog for self-containment)
- Encode-decode round-trip vectors (bit-pattern to FP32 and back)
- Boundary vectors (min/max normal, min subnormal, zero, Inf if present,
  NaN patterns)
- Gap annotations where the reference implementation is known to
  disagree with the ratified text or with a peer implementation

For P3109 binary8, the packs currently reflect the draft v3.2.1 field
layout. When the ratified text differs, the pack for each affected
record will be regenerated in a single commit; the change will be
recorded in the dataset changelog and the SSOT commit hash bumped in
this guide.

The FP8 E4M3 pack contains a **worked overflow example** documented in
Section 5 below.

---

## 5. Worked example: FP8 E4M3 overflow, and its P3109 binary8 p3 neighbour

FP8 E4M3, bias 7, format `S EEEE MMM`. The largest finite value is
`0 1111 110 = 448.0`. The pattern `0 1111 111 = S7F` is defined as the
single NaN encoding (no Inf). Consequently, any encode that would
overflow past 448.0 must either saturate to 448.0 or produce NaN,
depending on the operator's rounding-and-saturation policy. There is no
Inf tag to fall through into.

The corresponding P3109 binary8 p3 record has field widths (1, 4, 3)
identical to FP8 E4M3, but the special-value semantics in the P3109
draft do not follow the FP8 E4M3 convention verbatim. A reviewer should
therefore not assume that a P3109 binary8 p3 implementation will handle
overflow the same way as an FP8 E4M3 implementation, even though a
generic bit-copy would appear to work.

Pack file:
[`fp8_e4m3.jsonl`](https://huggingface.co/datasets/playra/numeric-conformance-packs/blob/main/packs/fp8_e4m3.jsonl)
in the v3 packs dataset.

---

## 6. Formal semantics reference: FLoPS

The FLoPS Lean 4 formalization (Chang, Park, Lim, Nagarakatte, Rutgers;
[arXiv:2602.15965](https://arxiv.org/abs/2602.15965), February 2026)
gives machine-checked semantics for a subset of the P3109 binary8
family. Where this guide, the SSOT, and FLoPS disagree, FLoPS is the
authoritative source for the covered subset. This guide does not
duplicate the FLoPS specification; it points to it and notes the
coverage boundary in each affected pack.

---

## 7. What is `[open]`

- Ratified P3109 bias convention across all seven precisions.
- Special-value semantics (Inf presence per precision, NaN pattern per
  precision) in the ratified text.
- The exact set of P3109 binary8 records to be marked "compliant" versus
  "adjacent" in future SSOT commits, pending WG guidance.
- The set of formats a downstream conformance harness would legitimately
  test; this guide takes no position beyond "the catalog exists, the
  packs exist, and the mapping is a starting point".

---

## 8. How to cite this guide

- SSOT catalog: `gHashTag/t27` `specs/numeric/formats_catalog.t27` at
  commit hash (please cite the exact hash you consulted).
- HF catalog: `playra/numeric-format-catalog` v3, commit
  `c3e8c974dc81f25c125fb4953b4211b92b6c65c9`.
- HF packs: `playra/numeric-conformance-packs` v3, commit
  `34f18d99f4c85c8f82094a8b2f7faf1da1ec9ad7`.
- This guide: `gHashTag/tt-trinity-corona` `docs/P3109_CROSS_FORMAT_GUIDE.md`
  at commit hash from Git.
- Contact: admin@t27.ai, ORCID
  [0009-0008-4294-6159](https://orcid.org/0009-0008-4294-6159).

Feedback, corrections, and requests for additional cross-walks are
welcome via GitHub issues on either repository, or by direct reply to
[P3109/Public issue #16](https://github.com/P3109/Public/issues/16).
