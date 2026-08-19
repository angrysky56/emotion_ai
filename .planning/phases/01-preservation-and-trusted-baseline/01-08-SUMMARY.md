---
phase: 01-preservation-and-trusted-baseline
plan: 08
subsystem: preservation
tags: [python, sqlite, sha256, privacy, inventory, restore-parity]

requires:
  - phase: 01-preservation-and-trusted-baseline
    plan: 01
    provides: Read-only inventory and public/private evidence lanes
  - phase: 01-preservation-and-trusted-baseline
    plan: 02
    provides: Digest-bound backup and disposable restore contract
  - phase: 01-preservation-and-trusted-baseline
    plan: 03
    provides: Content-free Git-index runtime baseline
provides:
  - Current content-safe inventory of all 14 declared Aura roots and 662 regular files
  - Immutable private per-file evidence outside Git plus a validated aggregate summary
  - Role-bound not-applicable evidence for preserved non-database archive artifacts
  - Reconciliation proving all 59 tracked runtime-baseline paths are inventoried
affects: [01-09, 01-10, phase-03-storage, preservation, restore-parity]

tech-stack:
  added: []
  patterns:
    - SQLITE_NOTADB is not-applicable only beneath an explicitly declared archive root
    - Disposable restore compares role-bound SQLite facts before licensing parity
    - Persistent Chroma clients close before disposable-directory cleanup

key-files:
  created:
    - .planning/evidence/phase-01/inventory-summary.json
    - .planning/phases/01-preservation-and-trusted-baseline/01-08-SUMMARY.md
  modified:
    - aura_backend/preservation/manifest.py
    - aura_backend/preservation/inventory.py
    - aura_backend/preservation/restore.py
    - aura_backend/preservation/cli.py
    - tests/preservation/test_inventory.py
    - tests/preservation/test_manifest_privacy.py
    - tests/preservation/test_backup_restore.py
    - .planning/phases/01-preservation-and-trusted-baseline/01-08-PLAN.md
    - .planning/phases/01-preservation-and-trusted-baseline/01-RESEARCH.md

key-decisions:
  - "Preserve a SQLITE_NOTADB suffix-matched file as not_applicable only when its declared root role is archive; identical active, backup, or test evidence fails."
  - "Count preserved archive N/A evidence as an anomaly and expose only its fixed non-content reason in the public aggregate."
  - "Bind role, status, result, and reason across disposable restore so N/A cannot replace active integrity or unrun checks."

patterns-established:
  - "Preservation success is distinct from database integrity success: a hashed archive artifact may be preserved while both inapplicable database checks remain explicit."
  - "Public evidence uses fixed reason-count buckets; raw SQLite errors and file-level evidence remain outside Git."

requirements-completed: [PRES-01, PRES-04]

duration: 18 min
completed: 2026-08-19
status: complete
---

# Phase 1 Plan 08: Real-Root Inventory Summary

**A validated 992,522,715-byte inventory of 14 active, backup, test, and archive roots, with 59/59 tracked artifacts reconciled and one known non-database archive artifact preserved as an explicit anomaly**

## Performance

- **Duration:** 18 min
- **Started:** 2026-08-19T12:06:09Z
- **Completed:** 2026-08-19T12:24:30Z
- **Tasks:** 2
- **Files modified:** 11 repository files plus one private artifact outside Git

## Accomplishments

- Inventoried 662 regular files totaling 992,522,715 bytes across all 14 declared roots; every file reached a stable hash pass and every required root passed.
- Preserved both likely-active Chroma candidates independently without selecting a canonical root. Each reports structural integrity `pass` and eight separately retained foreign-key anomaly rows.
- Reconciled all 59 content-free tracked-runtime baseline paths against private per-file evidence with zero missing paths.
- Kept detailed evidence at `/backup/aura-preservation/phase-01-20260819T121845Z/inventory.private.json` with mode `0600`; the committable aggregate passed its exact allowlist validator.
- Recorded 605 total anomalies truthfully: 604 known foreign-key rows plus one role-bound `preserved_non_sqlite_archive` classification.

## Task Commits

TDD RED/GREEN gates and the restore lifecycle fix were committed atomically:

1. **Inventory policy RED:** `27f014b` (test) - archive N/A, operational failure, and public-privacy contract.
2. **Inventory policy GREEN:** `328c568` (feat) - normative `not_applicable` status and archive-only SQLITE_NOTADB classification.
3. **Restore parity RED:** `fe65599` (test) - archive parity acceptance and forged active N/A rejection.
4. **Restore parity GREEN:** `654ed79` (feat) - role-bound SQLite facts and valid-Chroma-root selection.
5. **Disposable lifecycle:** `42eca62` (fix) - close every restored PersistentClient before temporary cleanup.

## Files Created/Modified

- `.planning/evidence/phase-01/inventory-summary.json` - allowlisted real-root totals, roles, checks, hashes, and anomaly counts.
- `aura_backend/preservation/manifest.py` - normative N/A status and fixed public-safe reason aggregation.
- `aura_backend/preservation/inventory.py` - archive-only SQLITE_NOTADB classification while retaining file hashes and counts.
- `aura_backend/preservation/cli.py` - public schema validation and private evidence deserialization for the added status/reason.
- `aura_backend/preservation/restore.py` - role-bound SQLite/FK parity, scoped Chroma opening, and explicit client closure.
- `tests/preservation/` - synthetic regression coverage for inventory, privacy, fail-closed operational roles, and disposable restore.
- `01-08-PLAN.md` and `01-RESEARCH.md` - resolved policy documented at the execution contract and research decision seam.

## Decisions Made

- `not_applicable` means a check has no valid subject; it is never a synonym for `pass`, `not_run`, or a tolerated operational failure.
- Only SQLite's explicit `SQLITE_NOTADB` result under an archive declaration receives the fixed classification. Other SQLite errors and every non-archive role remain fail-closed.
- Restore parity must reproduce the role, path, status, result, reason, FK status, count, and fingerprint. This prevents a forged active N/A from passing later verification.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Completed the missing normative not-applicable evidence state**
- **Found during:** Task 1 real inventory
- **Issue:** The first exact run hashed every file but failed because an intentionally retained archive artifact has a SQLite suffix while SQLite reports it is not a database. Plan 01-02 specified `not_applicable`, but `CheckStatus` did not implement it.
- **Fix:** Added the missing state, fixed public-safe reason counts, and an archive-role plus `SQLITE_NOTADB` guard. Active, backup, and test roles still fail on the same bytes.
- **Files modified:** manifest, inventory, CLI, inventory/privacy tests, plan, and research files.
- **Verification:** RED failed 5 tests; GREEN passed 16/16 focused tests and the fresh exact real inventory exited 0.
- **Committed in:** `27f014b`, `328c568`

**2. [Rule 2 - Missing Critical] Bound archive N/A through disposable restore**
- **Found during:** Task 1 policy decision review
- **Issue:** Existing restore verification required every SQLite integrity status to be `pass` and had no way to distinguish licensed archive N/A from forged active N/A.
- **Fix:** Compare exact role-bound SQLite facts, license only the fixed archive reason, retain exact FK parity, and open Chroma only for restored roots with passing `chroma.sqlite3` evidence.
- **Files modified:** restore implementation and backup/restore tests.
- **Verification:** RED failed the archive parity test; GREEN passed both new parity tests and 22/22 backup/restore tests.
- **Committed in:** `fe65599`, `654ed79`

**3. [Rule 2 - Missing Critical] Closed disposable Chroma clients before cleanup**
- **Found during:** Overall preservation verification
- **Issue:** Restore clients were left to garbage collection while their temporary persistence directory was removed.
- **Fix:** Use Chroma 1.5.9's current `Client.close()` contract for every disposable client, including fault-injection wrappers.
- **Files modified:** restore implementation and backup/restore tests.
- **Verification:** 22/22 backup/restore tests and 128/128 full deterministic tests passed.
- **Committed in:** `42eca62`

---

**Total deviations:** 3 auto-fixed (1 bug, 2 missing critical correctness safeguards)
**Impact on plan:** The fixes implement the already-specified N/A semantics without excluding, mutating, repairing, opening, or copying any original data. No storage migration or canonical-root decision was introduced.

## Issues Encountered

- The first immutable run remains preserved under `/backup/aura-preservation/phase-01-20260819T120618Z/`, including its failed public aggregate at mode `0600`. It was not overwritten or discarded.
- Declared backup roots grew between the failed and passing runs (516 to 662 regular files). The final artifact passed per-file stability checks, but Plan 01-09 must still quiesce writers before any real copy.
- The GSD helper remains unavailable because its local package metadata is broken. Direct Git/status/log operations preserved the orchestrator-owned `.planning/STATE.md` edit and untouched `.trunk/` directory.

## Verification Evidence

- Exact real inventory command - exit `0`, run `phase-01-20260819T121845Z`.
- Exact public validator with all four required roles - exit `0`.
- Tracked baseline reconciliation - **59 tracked, 59 accounted, 0 missing**.
- Active candidate reconciliation - two separate roots; each integrity `pass`, FK check `pass`, eight rows retained.
- Aggregate reconciliation - **604 FK rows + 1 preserved archive N/A = 605 anomalies**.
- Public SHA-256 - `debf25853a2301d4372ec8df210128cf31b8d0adb62d3509d1d3ccaabfbd43cc`.
- Private SHA-256 - `f935283ba00df928be09ba9485c6b2702774c4b6a12183d6e44d989ca5b73c52`.
- `uv run python -m pytest -q tests/preservation/test_inventory.py tests/preservation/test_manifest_privacy.py tests/test_repository_hygiene.py` - **19 passed**.
- `uv run python -m pytest -q tests/preservation/test_backup_restore.py` - **22 passed**.
- `uv run python -m pytest -q` - **128 passed**.
- Ruff, bytecode compilation, and `git diff --check` - passed.
- No original was opened through Chroma, copied, repaired, migrated, deleted, renamed, or declared canonical.

## TDD Gate Compliance

- RED commits: `27f014b`, `fe65599`.
- GREEN commits: `328c568`, `654ed79`.
- Both RED runs failed on the intended missing behavior before implementation; all focused and full tests are green afterward.

## Known Stubs

None. The empty accumulators and optional/default fields found by the stub scan are populated runtime structures, not unwired data sources or placeholder behavior.

## User Setup Required

None - no dependency, service, model, credential, or system configuration was added.

## Next Phase Readiness

- Plan 01-09 can bind its quiescence ticket to the validated public/private inventory pair.
- The observed backup-root growth reinforces that quiescence is mandatory before Plan 01-10 copies anything.
- The eight-row finding on each active candidate and the preserved archive N/A remain open parity facts; neither licenses cleanup or migration.

## Self-Check: PASSED

- The public and private evidence files exist and match the recorded SHA-256 values.
- All five Plan 01-08 task/TDD commits exist in Git history.
- All 59 tracked baseline paths are accounted for, all 14 required roots pass, and the committable summary validator exits 0.
- Stub and threat-surface scans found no blocking stub or unplanned network, authentication, file-access, or schema trust boundary.

---
*Phase: 01-preservation-and-trusted-baseline*
*Completed: 2026-08-19*
