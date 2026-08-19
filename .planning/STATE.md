# Project State: Aura Rehabilitation

**Updated:** 2026-08-19
**Active phase:** Phase 1 — Preservation and Trusted Baseline
**Status:** Phase 1 complete — preservation and trusted-baseline gates passed

## Verified So Far

- Evidence-based codebase map committed as `7a79048`.
- Local-only runtime boundary committed as `541b5da`.
- Deterministic Python suite: 131 passing tests.
- Active TypeScript type-check and Vite production build pass.
- `ornith:latest` is installed locally and available for marked live-model checks.
- Git tracks 59 grandfathered runtime/generated artifact paths totaling exactly
  153,612,467 bytes in the content-free tracked-runtime baseline.
- No database, backup, archive, or Git history has been deleted or rewritten.
- All 662 inventoried files have an outside-Git immutable backup with exact
  source-before/source-after/destination parity.
- A disposable restore passed SQLite integrity, exact FK parity, Chroma counts,
  and deterministic opaque retrieval for every non-empty collection.

## Current Position

Phase 1 is complete. Phase 2 may begin provider/runtime consolidation. The
preservation gate does not itself authorize storage cleanup: root ownership and
the retained eight-row FK anomalies remain Phase 3 work before migration or deletion.

## Locked Decisions

- Aura is private and local; no mandatory sign-in.
- Loopback is the default boundary; LAN exposure is explicit opt-in.
- Ollama is first-class, but deterministic tests do not depend on a running model.
- Preserve behavior and data before refactoring.
- Optimize against measurements, not claims.
- Remote Git-history rewriting requires separate explicit approval.

## Working Tree Note

`.trunk/` predates this rehabilitation and remains untracked and untouched.
