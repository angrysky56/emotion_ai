---
phase: 01-preservation-and-trusted-baseline
plan: 01
subsystem: preservation
tags: [python, sqlite, sha256, hmac, privacy, cli]

requires: []
provides:
  - No-follow metadata and streaming SHA-256 inventory for declared Aura data roots
  - Read-only SQLite integrity and separately fingerprinted foreign-key evidence
  - Private per-file manifests and allowlisted committable aggregate summaries
  - Fail-closed inventory and summary-validation CLI commands
affects: [01-02, 01-08, preservation, backup, restore, repository-hygiene]

tech-stack:
  added: []
  patterns:
    - Explicit pass, fail, blocked, and not_run evidence states
    - Public summaries constructed from aggregate allowlists rather than redacted private data
    - Exclusive owner-only private artifact creation outside Git

key-files:
  created:
    - aura_backend/preservation/__init__.py
    - aura_backend/preservation/manifest.py
    - aura_backend/preservation/inventory.py
    - aura_backend/preservation/cli.py
    - tests/preservation/test_inventory.py
    - tests/preservation/test_manifest_privacy.py
  modified: []

key-decisions:
  - "Construct public summaries directly from an aggregate allowlist; never delete sensitive keys from a private dictionary."
  - "Treat a completed foreign-key check as run evidence while reporting anomaly counts and HMAC fingerprints separately from structural integrity."
  - "Create private evidence with mode 0600 and refuse to overwrite either evidence lane."

patterns-established:
  - "No-follow inventory: lstat/scandir metadata checks plus O_NOFOLLOW and before/after descriptor identity checks."
  - "Truthful status: required blocked or failed checks always produce a nonzero CLI exit."
  - "Privacy split: detailed paths/errors remain private; public JSON contains only root and aggregate evidence."

requirements-completed: [PRES-01, PRES-04]

duration: 11 min
completed: 2026-08-19
status: complete
---

# Phase 1 Plan 01: Preservation Inventory and Privacy Summary

**Read-only Aura data inventory with no-follow traversal, streaming SHA-256, separate SQLite/FK evidence, and privacy-safe public summaries**

## Performance

- **Duration:** 11 min
- **Started:** 2026-08-19T09:32:46Z
- **Completed:** 2026-08-19T09:43:56Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Inventories regular files exactly once with stable size, timestamp, type, and SHA-256 aggregates while blocking symlinks and special files.
- Opens SQLite databases through read-only URIs and reports full integrity independently from foreign-key anomaly counts and private-keyed fingerprints.
- Produces private per-file evidence outside Git and a separately constructed committable summary that excludes file-level content, IDs, errors, and the HMAC key.
- Exposes only `inventory` and `validate-summary` commands with exclusive-output and fail-closed process semantics.

## Task Commits

Each TDD task was committed through its RED and GREEN gates:

1. **Task 1 RED: Define no-follow inventory behavior** - `fd75ef5` (test)
2. **Task 1 GREEN: Implement typed filesystem and SQLite inventory** - `df3ceb1` (feat)
3. **Task 2 RED: Define evidence-lane privacy and CLI behavior** - `52ea0d8` (test)
4. **Task 2 GREEN: Implement serializers and CLI** - `c552cdc` (feat)

## Files Created/Modified

- `aura_backend/preservation/__init__.py` - Import-light public preservation API.
- `aura_backend/preservation/manifest.py` - Typed evidence records plus explicit private/public serializers.
- `aura_backend/preservation/inventory.py` - No-follow traversal, stable streaming hashes, and read-only SQLite checks.
- `aura_backend/preservation/cli.py` - Inventory generation and non-mutating public-summary validation.
- `tests/preservation/test_inventory.py` - Synthetic traversal, SQLite, special-file, and status regression coverage.
- `tests/preservation/test_manifest_privacy.py` - Recursive sentinel privacy, exclusive-output, validation, and exit-code coverage.

## Decisions Made

- Public JSON is constructed field-by-field from aggregate evidence rather than derived from the private manifest, closing the risk that a future private field is accidentally left behind.
- Foreign-key violations remain visible as counts and HMAC fingerprints but do not masquerade as structural-integrity failures; inability to run either check remains non-pass evidence.
- CLI root mappings use deterministic safe aliases, repository-relative paths, an explicit outside-Git backup root, and owner-only private artifact permissions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Blocked symlinks in intermediate root-path components**
- **Found during:** Task 2 privacy/threat-boundary review
- **Issue:** The first implementation blocked a declared root that was itself a symlink, but an earlier path component could still point outside the repository.
- **Fix:** Check every existing declared-root component with `lstat()` before traversal and add a regression test proving the outside tree is never inventoried.
- **Files modified:** `aura_backend/preservation/inventory.py`, `tests/preservation/test_inventory.py`
- **Verification:** `test_symlink_in_declared_root_path_is_never_traversed` passes.
- **Committed in:** `52ea0d8` (test), `c552cdc` (implementation)

**2. [Rule 2 - Missing Critical] Prevented a regular-file race from blocking on a FIFO**
- **Found during:** Task 2 privacy/threat-boundary review
- **Issue:** A path changed from a regular file to a FIFO between `lstat()` and `open()` could block despite static special-file detection.
- **Fix:** Add `O_NONBLOCK` beside `O_NOFOLLOW`; descriptor type/identity checks then reject the changed entry without reading it as ordinary data.
- **Files modified:** `aura_backend/preservation/inventory.py`
- **Verification:** Focused special-file and unstable-file tests pass; full preservation suite passes 11/11.
- **Committed in:** `c552cdc`

---

**Total deviations:** 2 auto-fixed (2 missing critical security/correctness safeguards)
**Impact on plan:** Both changes tighten the declared no-follow trust boundary without expanding into backup, migration, deletion, or Chroma access.

## Issues Encountered

- The optional `pyright` executable is not installed in this environment, so no Pyright result is claimed. Required pytest checks, Ruff, bytecode compilation, and `git diff --check` passed.

## Verification Evidence

- `uv run python -m pytest -q tests/preservation/test_inventory.py tests/preservation/test_manifest_privacy.py` — **11 passed**.
- `uv run python -m pytest -q` — **24 passed**.
- `uv run ruff check aura_backend/preservation tests/preservation` — **all checks passed**.
- `uv run python -m compileall -q aura_backend/preservation` — exit 0.
- `git diff --check` — exit 0.
- No live Aura process, Chroma client, Ollama model, backup copy, deletion, or migration was invoked.

## Known Stubs

None. All public commands and serializers in this plan are wired to the inventory implementation and covered by deterministic tests.

## User Setup Required

None - no dependency, service, model, or secret configuration was added.

## Next Phase Readiness

- The import-light manifest and CLI contracts are ready for Plan 01-02 to extend with backup/restore ticket binding.
- The real repository inventory remains intentionally deferred to Plan 01-08; this plan used synthetic temporary roots only.
- No data cleanup or structural refactor is licensed until the later quiescence and isolated-restore gates pass.

## Self-Check: PASSED

- All six declared source/test files exist.
- All four TDD task commits (`fd75ef5`, `df3ceb1`, `52ea0d8`, `c552cdc`) exist in Git history.
- Focused and full deterministic verification passed after the final implementation change.

---
*Phase: 01-preservation-and-trusted-baseline*
*Completed: 2026-08-19*
