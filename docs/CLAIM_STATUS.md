# Claim-status discipline

Every numeric or quality claim in this repo MUST carry one of the eight tags
below. The CI job `claim_status_lint` enforces this on `.t27`, `.v`, `.py`,
and `.md` files. Untagged numeric/quality claims fail CI.

| Tag | `status_id` | Meaning |
| --- | --- | --- |
| `[Verified]`        | 0 | RTL tested in simulation AND confirmed on physical silicon |
| `[Empirical fit]`   | 1 | Tests pass; theoretical grounding partial |
| `[Open conjecture]` | 2 | Not yet falsified; counterexamples may exist |
| `[Risk]`            | 3 | Used in practice but known failure modes documented |
| `[Retracted]`       | 4 | Previously claimed, subsequently falsified |
| `[Experimental]`    | 5 | Prototype only; no production validation |
| `[Historical]`      | 6 | Legacy format; no active toolchain |
| `[Spec]`            | 7 | Definition only; no known open-source implementation |

## Banned vocabulary

The following words MUST NOT appear in any committed artefact (RTL comments,
README, PLAN, docs, commit messages, PR bodies):

- breakthrough, nobel, revolution, world-first, industry-leading, first-ever
- proves (and its translations)
- prize

These words assert per-rung superiority or finality and conflict with the
governing sentence:

> The goldenfloat ladder earns its place through breadth and toolchain
> coherence, NOT through per-rung superiority.

## The non-promotion invariant

**Corona being a registry chip does NOT promote FL-002.**

FL-002 (`gHashTag/trios-trainer-igla` `src/ledger.rs`) is the phi-ladder
breadth-as-moat conjecture. It stays `[Open conjecture]` regardless of:

- whether Corona tapes out successfully
- whether the conformance suite passes 100%
- whether the cross-die anchor matches across all four dice
- whether takum16_decode lands in Tier-1 or Tier-2

The standing counterexample is **takum** (Hunhold 2024
[arXiv:2412.20273](https://arxiv.org/abs/2412.20273)). It ships in the
Corona ROM and is NOT suppressed.

## Verbatim anchors

The following strings appear EXACTLY in PLAN.md and `specs/corona/anchor.t27`
and must NOT be paraphrased:

- `TG-TRIAD-X cross-die anchor: {uio_out, uo_out} == 16'h47C0 derived from dot4(1,2,3,4) over GF16 implied by phi^2 + phi^-2 = 3 = L_2.`
- `DOI 10.5281/zenodo.19227877 (hardware archive only, never results).`
- `SSOT: gHashTag/t27 specs/numeric/formats_catalog.t27, PR #1028.`
