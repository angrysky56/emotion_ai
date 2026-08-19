---
phase: 01-preservation-and-trusted-baseline
plan: 10
subsystem: preservation
tags: [python, chromadb, sqlite, sha256, hmac, backup, restore]

requires:
  - phase: 01-preservation-and-trusted-baseline
    plan: 09
    provides: Ty-approved fresh quiescence ticket bound to all 14 inventoried roots
provides:
  - Immutable outside-Git copy of all 662 inventoried files
  - Disposable-restore proof for hashes, SQLite integrity, FK parity, Chroma counts, and opaque retrieval
  - Preserved failed-attempt evidence and a passing canonical public summary
affects: [phase-02-runtime, phase-03-storage, preservation, migration-gate]

tech-stack:
  added: []
  patterns:
    - Repeated identical nearest-neighbor queries must produce stable ordered opaque evidence
    - Tied embeddings are validated by known-ID membership and metric-correct distance, not arbitrary ID tie-breaking
    - Every restore retry receives a new immutable private artifact

key-files:
  created:
    - .planning/evidence/phase-01/restore-drill-summary.json
    - .planning/phases/01-preservation-and-trusted-baseline/01-10-SUMMARY.md
  modified:
    - aura_backend/preservation/restore.py
    - aura_backend/preservation/cli.py
    - tests/preservation/test_backup_restore.py

key-decisions:
  - "A stored embedding may retrieve a different known record first when multiple records share the exact nearest distance; stable known-ID membership, ordered finite distances, and a metric-correct nearest result are the licensed oracle."
  - "Run every retrieval fixture twice and require identical normalized ID/distance order before HMACing it."
  - "Retain failed restore evidence immutably and issue a new private filename for every retry."

patterns-established:
  - "No Chroma retrieval fixture passes unless every non-empty collection contributes one stable, privacy-safe result."
  - "A successful preservation gate proves parity, not repair or canonical ownership of anomalous databases."

requirements-completed: [PRES-01, PRES-02, PRES-04]

duration: 21min
completed: 2026-08-19
status: complete
---

# Phase 1 Plan 10: Immutable Backup and Isolated Restore Summary

**A complete 662-file outside-Git backup with byte-identical sources and a disposable restore proving SQLite, exact FK, Chroma count, and deterministic opaque retrieval parity**

## Performance

- **Duration:** 21 min
- **Started:** 2026-08-19T16:19:38Z
- **Completed:** 2026-08-19T16:40:38Z
- **Tasks:** 2
- **Files modified:** 7 repository files plus private backup/restore evidence outside Git

## Accomplishments

- Finalized `/backup/aura-preservation/phase-01-20260819T121845Z/backup` only after 662-file source-before, source-after, and destination manifests matched exactly.
- Proved backup hash parity, disposable copy parity, SQLite integrity, exact foreign-key evidence, 10 Chroma collection counts, 1,204 record counts, and opaque retrieval for both non-empty collections.
- Preserved the eight-row FK anomaly independently in each likely-active root with the exact same fingerprint; it remains unresolved rather than being normalized or repaired.
- Preserved the archive-only `not_applicable` SQLite classification exactly across restore.
- Retained the failed first retrieval attempt at mode `0600`, then wrote the passing retry to a distinct immutable private artifact.

## Task Commits

Each outcome was committed atomically:

1. **Retrieval oracle RED gates** - `3418532` (test)
2. **Tied-neighbor and immutable retry implementation** - `bf25b3f` (fix)
3. **Task 1: Immutable backup and disposable restore evidence** - `1f91657` (feat)
4. **Task 2: Phase evidence gate** - verified by the final metadata commit with no additional production change

## Files Created/Modified

- `.planning/evidence/phase-01/restore-drill-summary.json` - Canonical allowlisted passing restore evidence.
- `aura_backend/preservation/restore.py` - Stable known-ID, finite-distance, metric-aware, repeated-query retrieval oracle.
- `aura_backend/preservation/cli.py` - New immutable private evidence path for every verification retry.
- `tests/preservation/test_backup_restore.py` - Tied-neighbor, nondeterminism, unknown-result, resource-failure, and retry-retention coverage.
- `/backup/aura-preservation/phase-01-20260819T121845Z/backup/` - Complete durable copy, never opened through Chroma.
- `/backup/aura-preservation/phase-01-20260819T121845Z/backup.private.json` - Private exact source/destination manifests.
- `/backup/aura-preservation/phase-01-20260819T121845Z/restore.attempt-02.private.json` - Passing private restore evidence.

## Decisions Made

- Duplicate exact embeddings make a particular ID an invalid tie-break oracle. A fixture now requires returned IDs to be unique members of the known collection, distances to be finite and ascending, and the best result to be at least as close as the stored query embedding under the configured `l2`, `cosine`, or `ip` metric.
- Each identical query is executed twice. Any result-order or distance difference fails the fixture rather than producing a nondeterministic HMAC.
- Fixture count must equal the number of non-empty collections. Partial retrieval evidence cannot pass.
- Preservation parity does not authorize deletion, migration, normalization, canonical-root selection, or FK repair.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created the plan-named private restore parent**
- **Found during:** Task 1 verifier startup
- **Issue:** `/backup/aura-preservation/.restore-work` did not exist, so the first verifier invocation stopped with exit `5` before copying or opening Chroma.
- **Fix:** Created the empty directory with mode `0700` and reran the unchanged verifier command.
- **Files modified:** Private directory outside Git only.
- **Verification:** The path passed no-symlink, disjointness, and disposable-child checks.
- **Committed in:** Not applicable; private environment preparation only.

**2. [Rule 1 - Bug] Corrected false failure on exact tied embeddings**
- **Found during:** Task 1 real disposable restore
- **Issue:** One collection has 23 zero-distance tied records. Chroma returned five valid tied neighbors, but the verifier required the lexicographically chosen record ID to appear first.
- **Fix:** Validate stable ordered results by known-ID membership, uniqueness, finite ascending distances, metric-correct nearest distance, and identical repeated-query output. The arbitrary self-ID tie-break was removed.
- **Files modified:** `restore.py` and focused tests.
- **Verification:** RED failed the tied-neighbor and nondeterminism tests; GREEN passed 24/24 backup/restore tests, 40/40 preservation tests, and the real retry.
- **Committed in:** `3418532`, `bf25b3f`

**3. [Rule 2 - Missing Critical] Preserved retry evidence immutably**
- **Found during:** Task 1 failed restore retry
- **Issue:** The fixed verifier could not rerun because `restore.private.json` is intentionally exclusive, and overwriting it would destroy audit evidence.
- **Fix:** Select `restore.attempt-NN.private.json` for later attempts while retaining the original private result. The first failed public summary was copied privately before canonical replacement.
- **Files modified:** `cli.py` and focused tests; private evidence outside Git.
- **Verification:** The synthetic CLI chain passes twice with two extant private artifacts; the real canonical summary points to `restore.attempt-02.private.json`.
- **Committed in:** `3418532`, `bf25b3f`

---

**Total deviations:** 3 auto-fixed (1 bug, 1 missing critical audit safeguard, 1 blocking environment setup)
**Impact on plan:** All changes tighten the planned privacy and truthfulness gates. No persistence source, durable backup, schema, or product behavior was altered.

## Issues Encountered

- The first real restore attempt truthfully failed only `retrieval_parity`; all six earlier gates passed. Its public-safe copy is retained privately at `restore.attempt-01.public.json` with SHA-256 `5bc0794ae58aec72b92f4a94480896a1b473b4dc3b7b374cd20eb6d623b4280c`; its private artifact remains `restore.private.json` with SHA-256 `15584f763ae7f6930b8055df0f8716b7907e870bf36468c19241135bf771fd46`.
- A retained diagnostic disposable copy remains under `/backup/aura-preservation/.restore-work/diagnostic-20260819T1624`. It was opened only after copying from the durable backup and was not deleted under the no-cleanup rule.
- The GSD helper remains unavailable because its local package metadata is broken. Direct, file-specific Git operations preserved the orchestrator-owned state edit and untouched `.trunk/` directory.

## Verification Evidence

- Durable backup manifest: **662 files**, source-before/source-after/destination SHA-256 `f5259d70f525515f366eca3e626571697842338875963b0c9475e413dc3e5cef`.
- Inventory/source-set binding: `350091c106ffb5443d0b9d3dfee3c514789021838322c8440a45f6eaade54c78`.
- Final public evidence binds inventory SHA-256 `debf25853a2301d4372ec8df210128cf31b8d0adb62d3509d1d3ccaabfbd43cc`, quiescence SHA-256 `8ed35d1678275d565d36dc6b645e7219c090132816a2133710dfb10dab9595ab`, and backup-result SHA-256 `153d5b55dfb3d1eeb50f7583446385080ec83074d7e213e928702eddd5de098a`.
- Passing private restore evidence: SHA-256 `e6b1c64face60c4257aeb17716b5998dbf38da0130201d5112af28bb53f3bb7b`, mode `0600`.
- Both active roots: integrity `pass`, **8 FK rows each**, identical FK fingerprint `f39db0ac9239b95af5b15d1da2774241dd96d4b5a0338e3db89142d7c7d7d834`.
- Archive parity: the retained non-database archive remains exactly one role-bound `not_applicable` item.
- Chroma restore: **10 collections**, **1,204 records**, **2/2 non-empty collection fixtures**, retrieval HMAC `7c10f11712192a7e57c7e46262231725152beb803040cc9282d006ca578b8889`.
- Exact required restore validator - exit `0` with every `--require-*` gate.
- `uv run python -m pytest -q tests/preservation/test_backup_restore.py` - **24 passed**.
- `uv run python -m pytest -q tests/preservation` - **40 passed**.
- `uv run python -m pytest -q` - **130 passed**.
- `npx tsc --noEmit`, `npm run build`, Ruff, bytecode compilation, and `git diff --check` - passed independently.

## TDD Gate Compliance

- RED commit `3418532` produced the three intended failures: tied-neighbor false rejection, undetected nondeterministic ordering, and private retry collision.
- GREEN commit `bf25b3f` passed all three focused gates and the complete preservation suite.

## Authentication Gates

None.

## Known Stubs

None. The optional/default fields and local accumulators found by the stub scan are populated runtime structures, not unwired behavior.

## User Setup Required

None - no dependency, external service, credential, model, or system configuration was added.

## Next Phase Readiness

- Phase 1's preservation gate is complete. Later storage work may use this backup as a recovery baseline, but must retain its immutable evidence.
- Phase 3 must determine root ownership and analyze the eight-row FK anomalies before any repair, consolidation, migration, tracked-data removal, or deletion.
- The passing restore does not imply the databases are anomaly-free; it proves the anomalous source state was preserved exactly and remains queryable.

## Self-Check: PASSED

- The durable backup, backup manifest, failed-attempt artifacts, passing private artifact, and canonical public summary exist with the recorded digests and permissions.
- TDD commits `3418532` and `bf25b3f` and evidence commit `1f91657` exist in Git history.
- All seven required restore checks are `pass`; both non-empty collections produced stable opaque fixtures.
- No original or durable backup path was passed to Chroma, and no source was deleted, migrated, normalized, renamed, repaired, or declared canonical.
- Stub and threat-surface scans found no blocking stub or unplanned network, authentication, schema, or trust-boundary expansion.

---
*Phase: 01-preservation-and-trusted-baseline*
*Completed: 2026-08-19*
