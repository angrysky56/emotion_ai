---
phase: 01-preservation-and-trusted-baseline
plan: 02
subsystem: preservation
tags: [python, chromadb, sqlite, sha256, hmac, backup, restore, cli]

requires:
  - phase: 01-preservation-and-trusted-baseline
    plan: 01
    provides: Typed private/public inventory manifests and read-only SQLite/FK evidence
provides:
  - Quiescence-ticketed no-follow full-root backup copies with atomic finalization
  - Disposable-only Chroma restore verification with SQLite, FK, count, and retrieval gates
  - Digest-bound inventory, preflight, backup, restore, and validator CLI chain
  - Synthetic regressions proving path disjointness and non-pass false-success resistance
affects: [01-08, 01-09, 01-10, preservation, migration-gate, data-lifecycle]

tech-stack:
  added: []
  patterns:
    - New .partial copy claimed exclusively and renamed only after exact parity
    - Durable backup copied again before any lazy Chroma client construction
    - Required evidence state machine where fail, blocked, and not_run cannot pass

key-files:
  created:
    - aura_backend/preservation/backup.py
    - aura_backend/preservation/restore.py
    - tests/preservation/test_backup_restore.py
  modified:
    - aura_backend/preservation/cli.py

key-decisions:
  - "Store the trusted repository root only in the outside-Git private inventory artifact so later CLI commands can resolve declared sources without expanding their normative options."
  - "Compare Chroma count() against an independent ID-only get(include=[]) result so either overcounts or undercounts fail."
  - "Treat synthetic proof as implementation readiness only; the real offline PRES-02 evidence remains gated on Plans 01-09 and 01-10."

patterns-established:
  - "Immutable copy: reject links, special files, overlap, existing destinations, stale tickets, and changing sources before final rename."
  - "Disposable restore: only a TemporaryDirectory descendant is passed to PersistentClient; originals and durable backups remain unopened by Chroma."
  - "Opaque retrieval evidence: reuse a stored embedding, omit documents/metadata, and expose only HMAC fingerprints and aggregate counts."

requirements-completed: [PRES-02]

duration: 14 min
completed: 2026-08-19
status: complete
---

# Phase 1 Plan 02: Preservation Copy and Disposable Restore Summary

**Ticket-bound immutable full-root copies with disposable-only Chroma verification and fail-closed hash, SQLite, FK, count, retrieval, and artifact-binding gates**

## Performance

- **Duration:** 14 min
- **Started:** 2026-08-19T10:41:51Z
- **Completed:** 2026-08-19T10:55:19Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Claims a new `.partial` destination, copies every regular SQLite/vector sidecar without following links, retains failed partial evidence, and atomically finalizes only after source-before/source-after/destination parity.
- Copies the durable artifact into a fresh temporary directory before lazily importing Chroma; a path spy proves neither the synthetic original nor durable backup reaches `PersistentClient`.
- Verifies full SQLite integrity, exact foreign-key anomaly count/fingerprint parity, Chroma API/ID-only count parity, and opaque stored-embedding retrieval evidence.
- Exposes all seven normative CLI commands with schema-v1 artifacts, stable exit classes, ticket expiry/recheck behavior, and digest binding across the inventory-to-restore chain.
- Proves omitted sidecars, source mutation, unsafe paths, stale/partial evidence, FK drift, count drift, retrieval drift, resource errors, and cross-artifact substitution cannot produce pass.

## Task Commits

Each task was committed through explicit TDD RED and GREEN gates:

1. **Task 1 RED: Define fail-closed backup copy behavior** - `af0cba7` (test)
2. **Task 1 GREEN: Implement immutable persistence copies** - `c014100` (feat)
3. **Task 2 RED: Define disposable restore and CLI gates** - `64b7bac` (test)
4. **Task 2 GREEN: Implement digest-bound disposable verification** - `c4dd6f4` (feat)

## Files Created/Modified

- `aura_backend/preservation/backup.py` - Typed quiescence tickets, secure tree snapshots, no-follow copies, and atomic parity finalization.
- `aura_backend/preservation/restore.py` - Temporary restore lifecycle, read-only SQLite/FK comparison, and privacy-safe Chroma count/retrieval verification.
- `aura_backend/preservation/cli.py` - Preflight, ticket validation, ticketed backup, restore verification, final validation, and artifact deserialization/binding.
- `tests/preservation/test_backup_restore.py` - Synthetic full-tree, Chroma, corruption, path, status, CLI, and privacy regressions.

## Decisions Made

- The private inventory artifact records the resolved repository root because later normative commands intentionally have no `--repository-root` option. This value never enters a committable public artifact.
- Chroma count parity uses `collection.count()` versus a separate `collection.get(include=[])` result with no count-derived limit, preventing a wrong count from constraining its own comparison.
- Existing FK anomalies are compared by exact private-keyed count/fingerprint parity. They are neither repaired nor hidden, and structural integrity remains a separate required gate.
- Restore verification may occur after the copy ticket expires because the ticket licenses the copy, while the immutable backup digest licenses later restore verification. Ticket freshness is nevertheless rechecked immediately before copying.

## Deviations from Plan

None - the plan was executed within its synthetic-only boundary. No package, schema, service, migration, deletion, rotation, or history change was added.

## Issues Encountered

- The plan's `backup-from-ticket` command intentionally omits `--repository-root`. Source resolution was closed without changing the public command contract by recording the resolved root only in the already-private inventory artifact.
- A first count comparison used the reported count as the ID fetch limit, which could have hidden an undercount. It was corrected before the GREEN commit by fetching IDs independently with `include=[]`.

## Verification Evidence

- `uv run python -m pytest -q tests/preservation/test_backup_restore.py` — **20 passed**.
- `uv run python -m pytest -q` — **63 passed**.
- `uv run ruff check aura_backend/preservation/backup.py aura_backend/preservation/restore.py aura_backend/preservation/cli.py tests/preservation/test_backup_restore.py` — **all checks passed**.
- `uv run python -m compileall -q aura_backend/preservation` — exit 0.
- `git diff --check` — exit 0.
- All preservation fixtures were created beneath pytest temporary directories. No real Aura root, system backup mount, live service, deletion, migration, or Git-history operation was accessed.

## Known Stubs

None. Every command is wired to production preservation logic, and every required restore evidence class has explicit non-pass behavior.

## User Setup Required

None - no dependency, service, model, secret, or system configuration was added.

## Next Phase Readiness

- Plans 01-08 and 01-09 can create the real inventory and quiescence ticket using the now-tested CLI contract.
- Plan 01-10 can create the first durable offline artifact and run the isolated restore drill without introducing new copy or verification logic.
- The real PRES-02 operational gate remains open until the human-approved quiescence ticket and real restore-summary validator pass; this synthetic plan does not license migration or deletion.

## Self-Check: PASSED

- All four declared source/test files exist.
- All four TDD task commits (`af0cba7`, `c014100`, `64b7bac`, `c4dd6f4`) exist in Git history.
- Focused and complete deterministic verification passed after the final implementation commit.
- Stub and threat-surface scans found no blocking stub or unplanned endpoint/auth/schema surface.

---
*Phase: 01-preservation-and-trusted-baseline*
*Completed: 2026-08-19*
