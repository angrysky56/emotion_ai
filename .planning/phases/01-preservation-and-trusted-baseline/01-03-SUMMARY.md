---
phase: 01-preservation-and-trusted-baseline
plan: 03
subsystem: testing
tags: [pytest, git-hygiene, evidence, legacy-classification]

requires: []
provides:
  - Strict tests-only deterministic pytest discovery with registered external lanes
  - Exact Git-index baseline and regression gate for tracked runtime artifacts
  - Complete audited classification of all legacy test-shaped scripts
affects: [01-04, phase-03-storage, ci, repository-hygiene]

tech-stack:
  added: []
  patterns:
    - Content-free Git-index evidence using path, byte size, and blob OID
    - Default deterministic tests separated from live, model, GPU, destructive, and archive lanes

key-files:
  created:
    - .planning/evidence/phase-01/tracked-runtime-baseline.json
    - .planning/evidence/phase-01/legacy-test-classification.json
    - tests/test_repository_hygiene.py
    - tests/test_legacy_classification.py
  modified:
    - pyproject.toml
    - .gitignore

key-decisions:
  - "Grandfather existing tracked runtime anomalies by exact Git-index path, byte size, and blob OID without reading or reporting file contents."
  - "Keep legacy scripts in place but give each one an explicit non-default disposition; only three production-backed groups migrate in Plan 01-04."

patterns-established:
  - "No-new-runtime-artifact gate: current tracked candidates must exactly equal the content-free baseline."
  - "Legacy truthfulness gate: printed booleans, import success, environment blocks, and diagnostics never count as deterministic passes."

requirements-completed: [PRES-04, TEST-01, TEST-02]

duration: 13min
completed: 2026-08-19
status: complete
---

# Phase 1 Plan 03: Deterministic Test and Git-Hygiene Boundaries Summary

**Strict tests-only pytest discovery, a 59-artifact content-free Git baseline, and exact audited ownership for all 38 legacy test-shaped scripts**

## Performance

- **Duration:** 13 min
- **Started:** 2026-08-19T09:50:52Z
- **Completed:** 2026-08-19T10:03:52Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Made `uv run python -m pytest -q` the strict deterministic boundary with `tests/`-only discovery, strict async behavior, and registered `live`, `ollama`, and `gpu` markers.
- Added a no-new-runtime-data regression gate while preserving all existing tracked databases, backups, vector artifacts, and personal-data anomalies unchanged.
- Classified every one of the 38 current legacy test-shaped scripts exactly once, including dependencies, write risk, production ownership, lane command/markers, and truthful result semantics.
- Reserved only smart parameter handling, MCP/large-result serialization, and pure NumPy conversion for deterministic migration in Plan 01-04.

## Task Commits

TDD slices were committed at their RED and GREEN gates:

1. **Task 1 RED: failing repository hygiene contract** - `106e3c7` (test)
2. **Task 1 GREEN: deterministic discovery and hygiene boundary** - `bdee858` (feat)
3. **Task 2 RED: failing legacy classification contract** - `2ee75d9` (test)
4. **Task 2 GREEN: complete legacy classification manifest** - `ecdaf52` (feat)

## Files Created/Modified

- `pyproject.toml` - Keeps discovery under `tests/`, makes async handling strict, and registers external lanes.
- `.gitignore` - Covers generated databases, backup roots, exports, sessions, profiles/users, logs, traces, sidecars, vector files, and secret variants while retaining `.gitkeep` exceptions.
- `.planning/evidence/phase-01/tracked-runtime-baseline.json` - Stores only path, indexed byte size, and Git blob OID for 59 grandfathered candidates.
- `.planning/evidence/phase-01/legacy-test-classification.json` - Assigns one audited category and disposition to all 38 legacy scripts.
- `tests/test_repository_hygiene.py` - Enforces exact baseline parity, synthetic new-candidate rejection, and ignore coverage.
- `tests/test_legacy_classification.py` - Enforces exact discovery parity, schema/result truthfulness, migration ownership, and synthetic missing-classification detection.

## Decisions Made

- Used Git-index metadata (`git ls-files -s` plus `git cat-file -s`) so the baseline measures committed bytes and never serializes database or personal content.
- Excluded `.gitkeep` sentinels and documented example configuration files from runtime-candidate detection.
- Kept all legacy files physically unchanged. Classification changes their ownership and result meaning, not their stored location or discovery scope.
- Live/model lane commands remain explicit marked pytest targets and never broaden default collection into `aura_backend/tests`, archives, or scratch.

## Verification Evidence

- `uv run python -m pytest --collect-only -q` - **31 tests collected**, all under root `tests/`; no legacy path collected.
- `uv run python -m pytest -q` - **31 passed in 0.22s** with no live service or model required.
- `uv run python -m pytest -q tests/test_repository_hygiene.py` - **3 passed**.
- `uv run python -m pytest -q tests/test_legacy_classification.py` - **4 passed**.
- Manifest checks - **59** exact tracked runtime candidates and **38** unique legacy classifications.
- `git diff --check` - passed.
- Commit deletion scan - no tracked database, backup, export, profile, log, secret, generated-data, or legacy-script deletion.

## TDD Gate Compliance

- RED commits: `106e3c7`, `2ee75d9`
- GREEN commits: `bdee858`, `ecdaf52`
- Both focused contracts failed because their required manifests/ignore coverage were absent before implementation, then passed after the minimum implementation was added.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The GSD JavaScript helper was unavailable because its local package metadata is broken. Per the execution handoff, direct Git/status/log and pytest checks were used; this did not change plan scope or verification.
- Other Wave 1 work was landing concurrently on the shared main tree. Only Plan 01-03-owned files were staged, and the orchestrator's existing `.planning/STATE.md` edit plus unrelated `.trunk/` were preserved.

## Known Stubs

None. The empty `records` list in the repository-hygiene collector is an ordinary accumulator populated from the Git index, not a UI or data-source stub.

## User Setup Required

None - the deterministic command requires no external service, model, credential, or new dependency.

## Next Phase Readiness

- Plan 01-04 can migrate the three named production-backed legacy groups into assertion-based deterministic tests.
- CI and later storage cleanup plans can rely on exact default-collection and no-new-runtime-artifact gates.
- Existing tracked runtime anomalies remain intentionally preserved for the Phase 3 removal gate.

## Self-Check: PASSED

- All six implementation artifacts and this summary exist.
- All four RED/GREEN task commits are present in Git history.
- Required frontmatter contains `status: complete` and all three completed requirement IDs.

---
*Phase: 01-preservation-and-trusted-baseline*
*Completed: 2026-08-19*
