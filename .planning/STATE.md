# Project State: Aura Rehabilitation

**Updated:** 2026-08-31
**Active phase:** Phase 3 — Memory Integrity and Data Lifecycle
**Status:** Phase 2 verified 16/16; Phase 3 affective-memory architecture research active

## Verified So Far

- Evidence-based codebase map committed as `7a79048`.
- Local-only runtime boundary committed as `541b5da`.
- Deterministic Python suite: 510 passing tests, 2 expected skips, 1 live deselection.
- Active TypeScript type-check and Vite production build pass.
- Required GitHub CI is green at commit `1daf3ba` (Run `33288903971`), including
  clean-install Pyright, frontend type-check/build, backend tests, and lint.
- `npm audit --package-lock-only --audit-level=high` reports 0 vulnerabilities.
- `ornith:latest` is installed locally and available for marked live-model checks.
- Git tracks 59 grandfathered runtime/generated artifact paths totaling exactly
  153,612,467 bytes in the content-free tracked-runtime baseline.
- No database, backup, archive, or Git history has been deleted or rewritten.
- All 662 inventoried files have an outside-Git immutable backup with exact
  source-before/source-after/destination parity.
- A disposable restore passed SQLite integrity, exact FK parity, Chroma counts,
  and deterministic opaque retrieval for every non-empty collection.

## Current Position

Phase 1 is independently verified at 30/30 and Phase 2 at 16/16. Required remote
CI and clean-install Pyright are complete, and the former npm audit findings are
resolved. Phase 3 research now fixes the architectural direction: one typed
append-only local event ledger owns truth; lexical/vector indexes are rebuildable;
Memvid is optional copy-only cold archival; graph/RLM readers must earn their
complexity through evaluation. The first safety regression prevents Memvid
archival from deleting active records and enforces the requested user boundary.
No historical store has been migrated or deleted. Root ownership and the retained
eight-row FK anomalies remain Phase 3 work before any migration or cleanup.

## Locked Decisions

- Aura is private and local; no mandatory sign-in.
- Loopback is the default boundary; LAN exposure is explicit opt-in.
- Ollama is first-class, but deterministic tests do not depend on a running model.
- Preserve behavior and data before refactoring.
- Optimize against measurements, not claims.
- Treat simulated neurochemical/brainwave state as bounded computational control,
  not measured human biology; require causal tests against a fixed control.
- Keep the durable event ledger authoritative; Memvid, Chroma, temporal graphs,
  and RLM readers are replaceable projections or experiments.
- Remote Git-history rewriting requires separate explicit approval.

## Working Tree Note

`.trunk/` predates this rehabilitation and remains untracked and untouched.
