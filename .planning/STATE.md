# Project State: Aura Rehabilitation

**Updated:** 2026-08-19
**Active phase:** Phase 1 — Preservation and Trusted Baseline
**Status:** Plan 01-09 complete — ready for Plan 01-10 backup and restore

## Verified So Far

- Evidence-based codebase map committed as `7a79048`.
- Local-only runtime boundary committed as `541b5da`.
- New deterministic pytest suite: 13 passing tests.
- Active TypeScript type-check and Vite production build pass.
- `ornith:latest` is installed locally and available for marked live-model checks.
- Git tracks 39 database/vector/backup artifacts totaling approximately 33 MB.
- No database, backup, archive, or Git history has been deleted or rewritten.

## Current Gate

Execute Plans 01-01 through 01-08 autonomously. Plan 01-09 is the sole blocking
quiescence checkpoint before Plan 01-10 creates and verifies the real preservation
artifact. Structural refactoring remains blocked until that gate passes.

## Locked Decisions

- Aura is private and local; no mandatory sign-in.
- Loopback is the default boundary; LAN exposure is explicit opt-in.
- Ollama is first-class, but deterministic tests do not depend on a running model.
- Preserve behavior and data before refactoring.
- Optimize against measurements, not claims.
- Remote Git-history rewriting requires separate explicit approval.

## Working Tree Note

`.trunk/` predates this rehabilitation and remains untracked and untouched.
