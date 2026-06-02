# ADR-0007: License = Apache-2.0

## Status

Accepted (2026-06-02). Resolves OPEN_QUESTIONS Q6.

## Context

Q6 asked whether Corona should be licensed Apache-2.0 or MIT. MIT is shorter and
lower-friction; Apache-2.0 is longer but provides an explicit patent grant and
matches the upstream SSOT repository.

## Decision

**Apache-2.0.** It matches `gHashTag/t27` (the SSOT that Corona is downstream of)
and provides patent grants, which matter for a hardware design. Every RTL, tool,
test, and spec file carries an `SPDX-License-Identifier: Apache-2.0` header, and
the CI `claim-status-lint` job scans the tree.

## Consequences

- Repository `LICENSE` is Apache-2.0; SPDX headers are present repo-wide.
- License-consistent with the t27 SSOT toolchain.
- Explicit patent grant covers the RTL and ROM-generation tooling.
