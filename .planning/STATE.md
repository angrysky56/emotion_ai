# Project State: Aura Rehabilitation

**Updated:** 2026-08-20
**Active phase:** Phase 2 — Provider and Runtime Core
**Status:** Phase 2 locally verified 15/16 — authorized remote CI/Pyright pending

## Verified So Far

- Evidence-based codebase map committed as `7a79048`.
- Local-only runtime boundary committed as `541b5da`.
- Deterministic Python suite: 508 passing tests, 2 expected skips, 1 live deselection.
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

Phase 1 is independently verified at 30/30. All 14 Phase 2 waves, including two
gap-closure waves, are locally complete. Independent verification scores Phase 2
15/16: every local behavior and gate passes, while required GitHub CI and clean
Pyright remain `not_run` because current HEAD has not been pushed. The package
checkpoint authorized exactly 16 OK-row actions; all four SUS rows remain
rejected and unchanged. Three high-severity npm development-toolchain audit
findings remain recorded as warnings. The preservation gate does not authorize
storage cleanup: root ownership and the retained eight-row FK anomalies remain
Phase 3 work before migration or deletion.

## Locked Decisions

- Aura is private and local; no mandatory sign-in.
- Loopback is the default boundary; LAN exposure is explicit opt-in.
- Ollama is first-class, but deterministic tests do not depend on a running model.
- Preserve behavior and data before refactoring.
- Optimize against measurements, not claims.
- Remote Git-history rewriting requires separate explicit approval.

## Working Tree Note

`.trunk/` predates this rehabilitation and remains untracked and untouched.
