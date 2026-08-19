---
phase: 01-preservation-and-trusted-baseline
plan: 06
subsystem: filesystem-security
tags: [pathlib, containment, symlink, fastapi, export, pytest]

requires:
  - 01-05 local HTTP boundary characterization
provides:
  - Canonical resolved-root profile and export path constructors
  - Stable client-error mapping for invalid export identifiers and formats
  - Evidence that export success names an existing parseable JSON file
affects: [phase-03-storage, export-lifecycle, local-api-security]

tech-stack:
  added: []
  patterns:
    - Positive component and format validation followed by resolved-path containment
    - Fixed trusted storage categories with final-candidate symlink checks
    - Disposable child-process production filesystem and endpoint probes

key-files:
  created:
    - tests/api/test_filesystem_contract.py
  modified:
    - aura_backend/runtime_security.py
    - aura_backend/main.py

key-decisions:
  - "Preserve all ordinary non-path identifiers byte-for-byte while rejecting separators, traversal components, and Unicode control characters."
  - "Resolve the configured base, fixed category, and final candidate before I/O; reject either a category symlink or final-file symlink that resolves outside the base."
  - "Map storage validation failures to a generic HTTP 400 and verify export success only after the named path exists and parses as JSON."
  - "Treat empty conversation and pattern arrays as the honest Phase 1 baseline, not evidence of complete export history."

patterns-established:
  - "Contained path construction: validate the caller component, combine it with a fixed category, resolve without creating, and prove the result remains relative to both category and base."
  - "Export evidence gate: an API success response requires an existing, parseable JSON artifact."

requirements-completed: [PRES-03, LOCAL-03]

duration: 6min
completed: 2026-08-19
status: complete
---

# Phase 1 Plan 06: Filesystem Containment Summary

**Resolved-root containment now blocks traversal and symlink escapes while preserving ordinary Aura identifiers and tying export success to a real JSON file**

## Performance

- **Duration:** 6 min
- **Started:** 2026-08-19T11:26:11Z
- **Completed:** 2026-08-19T11:31:39Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added stable storage validation exceptions and canonical profile/export constructors using `Path.resolve(strict=False)` plus `Path.is_relative_to` containment.
- Preserved current safe identifier filename behavior, including `ty-local_01`, spaces, punctuation, and Unicode identifiers.
- Rejected empty/dot/traversal values, both separators, absolute paths, decoded separator payloads, Unicode control characters, and non-JSON export formats before I/O.
- Blocked both fixed-category symlinks and final-file symlinks that redirect a profile or export outside the configured data root.
- Routed `save_user_profile`, `load_user_profile`, and `export_conversation_history` through the canonical constructors.
- Mapped invalid export requests to a generic 400 without exposing filesystem details; unrelated failures remain server errors.
- Required the export endpoint to verify that its returned path exists and parses as JSON before reporting success.

## Task Commits

TDD slices were committed at RED and GREEN gates:

1. **Task 1 RED: failing resolved-containment contract** - `e751cbb` (test)
2. **Task 1 GREEN: canonical contained path constructors** - `5f8f739` (feat)
3. **Task 2 RED: failing production filesystem and endpoint contract** - `41ad59d` (test)
4. **Task 2 GREEN: contained AuraFileSystem and HTTP wiring** - `a96b8c4` (feat)
5. **GREEN refactor: explicit baseline and unwritten-path evidence** - `fcb7e8d` (refactor)

## Files Created/Modified

- `aura_backend/runtime_security.py` - Defines stable storage errors and resolved-root profile/export constructors.
- `aura_backend/main.py` - Uses canonical paths for profile/export I/O, maps validation to HTTP 400, and verifies written JSON before success.
- `tests/api/test_filesystem_contract.py` - Covers pure containment plus direct production and real endpoint behavior in disposable child processes.

## Decisions Made

- Retained the existing permissive component compatibility boundary instead of introducing a narrower username alphabet. Only path-significant and control values are rejected.
- Kept JSON as the sole implemented format and derived the recorded format from the validated filename suffix.
- Used a generic `Invalid export request` response for all caller validation errors so local filesystem structure is not disclosed.
- Kept the current empty conversation/emotional/cognitive arrays unchanged and labeled them as a Phase 1 baseline; populating export history remains later lifecycle work.

## Verification Evidence

- `uv run python -m pytest -q tests/api/test_filesystem_contract.py` - **27 passed**.
- `uv run python -m pytest -q tests/api/test_filesystem_contract.py tests/api/test_local_boundary.py` - **39 passed in 15.61s**.
- `uv run python -m pytest -q` - **116 passed in 21.33s**; deterministic suite required no live model or service.
- `uv run ruff check aura_backend/runtime_security.py aura_backend/main.py tests/api/test_filesystem_contract.py` - passed.
- `uv run python -m py_compile aura_backend/runtime_security.py aura_backend/main.py tests/api/test_filesystem_contract.py` - passed.
- `git diff --check` - passed.
- Final `git status --short` contained only the orchestrator-owned `.planning/STATE.md` edit and pre-existing untracked `.trunk/`; no runtime data was written.

## TDD Gate Compliance

- Task 1 RED failed at import because the storage error and canonical path constructors did not exist; GREEN added them and 22 focused component/containment/symlink/format cases passed.
- Task 2 RED produced two expected failures: invalid profile loading swallowed its validation error, and invalid export requests returned 500 with raw validation details. GREEN made all 26 then-current filesystem contract cases pass.
- The GREEN refactor added explicit regression proof for final-file symlinks and unwritten export collaborators; all 27 final contract cases pass.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The GSD JavaScript helper was unavailable per the execution handoff, so direct Git/status/log commands were used without broadening scope.
- Work ran in a shared main tree. Only Plan 01-06-owned files and this summary were staged; the orchestrator's `.planning/STATE.md` change and `.trunk/` remained untouched.

## Known Stubs

- `aura_backend/main.py` intentionally writes empty `conversations`, `emotional_patterns`, and `cognitive_patterns` arrays. These are the captured Phase 1 baseline and do not claim complete history; later storage/export lifecycle work must wire actual data sources.

## User Setup Required

None - this work uses the Python standard library and already-installed framework/test dependencies.

## Next Phase Readiness

- Later export lifecycle work can populate the existing JSON structure without reopening caller-controlled path construction.
- Storage migration, retention/deletion, authentication, and complete-history export remain deliberately outside Phase 1.
- No real data, backup, archive, schema, or Git history was moved, deleted, or rewritten.

## Self-Check: PASSED

- All three implementation/test artifacts and this summary exist on disk.
- All five Plan 01-06 RED/GREEN/refactor commits exist in Git history in the required order.
- Required frontmatter contains `status: complete` and both completed requirement IDs.
- Focused, combined-boundary, full deterministic, lint, compile, and whitespace checks passed after the final implementation commit.

---
*Phase: 01-preservation-and-trusted-baseline*
*Completed: 2026-08-19*
