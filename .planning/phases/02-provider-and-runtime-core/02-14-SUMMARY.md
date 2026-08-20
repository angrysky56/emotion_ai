---
phase: 02-provider-and-runtime-core
plan: 14
subsystem: testing
tags: [dependency-audit, supply-chain, pypi, npm, entrypoints, fail-closed]

requires:
  - phase: 01-preservation-and-trusted-baseline
    provides: trusted offline test lane and preservation boundaries
provides:
  - current legitimacy evidence for 20 exact package-change candidates
  - consumer and lane inventory for all 37 direct manifest dependencies
  - fail-closed validation across eight supported API, MCP, Memvid, Docker, frontend, and test entrypoints
affects: [02-15-package-approval, 02-16-python-dependencies, 02-17-node-dependencies]

tech-stack:
  added: []
  patterns: [offline evidence snapshot, adversarial mutation tests, human-gated manifest authorization]

key-files:
  created:
    - .planning/evidence/phase-02/package-legitimacy.json
    - tests/test_dependency_audit.py
  modified: []

key-decisions:
  - "Registry presence never authorizes a manifest change; all Plan 02-14 records remain pending explicit Plan 02-15 review."
  - "Current eager API/MCP/Memvid consumers keep their executable lanes until later lazy-runtime work proves a safe group move."
  - "Torch, ChromaDB, and sentence-transformers remain base dependencies because characterized persistence and embedding paths consume them."

patterns-established:
  - "Package evidence gate: exact candidate identity, fresh authoritative metadata, source owner, release age, scripts, entrypoints, and verdict are mandatory."
  - "Consumer gate: every direct dependency and supported entrypoint has one explicit lane; uncovered moves/removals fail closed."

requirements-completed: [TEST-05, OPS-02]

duration: 1h active across resumed execution
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 14: Package Legitimacy and Dependency Consumer Evidence Summary

**Fail-closed package evidence for 20 exact candidates, 37 direct dependencies, and eight executable entrypoints, with four suspicious identities and zero authorized manifest changes**

## Scorecard

| Measure | Result |
|---|---:|
| Exact package-change candidates | 20 |
| Identity verdict `OK` | 16 |
| Identity verdict `SUS` | 4 |
| Identity verdict `UNASSESSED` | 0 |
| Direct manifest dependencies inventoried | 37 / 37 |
| Supported entrypoints inventoried | 8 / 8 |
| Manifest changes authorized | 0 |
| Full validator | 18 passed |

The four `SUS` records are `pyzbar` (old release and unresolved maintenance status), `faiss-cpu` (registry source redirects to an archived repository), `faiss-gpu-cu12` (third-party wheels rather than Meta's official FAISS source), and `asyncio-mqtt` (renamed project/source redirect). Suspicion blocks authorization; it is not treated as approval or silently converted to `OK`.

## Performance

- **Duration:** About 1 hour active, across the original and resumed executor turns
- **Evidence retrieved:** 2026-08-20T07:48:15Z
- **Completed:** 2026-08-20T08:02:28Z
- **Tasks:** 2 / 2
- **Files created:** 2

## Accomplishments

- Captured exact PyPI/npm registry, official source/owner, maintainer/publisher, license, release-age, yanked/deprecated, install-script, and declared-entrypoint evidence for every proposed addition, move, or removal.
- Proved Ruff exposes `ruff`; Pyright exposes `pyright` and `pyright-langserver`; Pyright declares no install lifecycle hooks; frontend `@google/genai` declares a no-op `preinstall` hook and has no active TypeScript consumer.
- Inventoried all direct Python and Node dependencies and bound active consumers to API, FastMCP, companion MCP, Memvid, Docker, frontend build/type-check, and deterministic-test lanes.
- Kept the Docker entrypoint visibly blocked: it installs the contradictory `requirements.txt` path and its current `CMD ["python", "main.py"]` does not address `aura_backend/main.py`.
- Added adversarial tests for stale, omitted, duplicate, unexpected, malformed, identity-mismatched, suspicious-as-approved, unassessed-as-approved, omitted-consumer, missing-lane, and self-authorized variants.

## Task Commits

1. **Task 02-14-01: Record current legitimacy for every addition/removal candidate** — `527f9aa` (`test`)
2. **Task 02-14-02: Bind dependency moves/removals to actual imports and supported entry points** — `4fdb8e6` (`test`)
3. **Evidence provenance correction** — `f1e14b5` (`fix`)

## Files Created

- `.planning/evidence/phase-02/package-legitimacy.json` — Current content-safe package provenance, approval state, direct-dependency consumer inventory, and supported-entrypoint lanes.
- `tests/test_dependency_audit.py` — Deterministic schema, freshness, candidate completeness, authorization, consumer, and entrypoint validator with adversarial mutation coverage.

## Decisions Made

- `OK` means the recorded identity signals agree; it does not approve adding, moving, or removing the package.
- Every record has `manifest_change_authorized: false`, and the document-level approval remains `PENDING_HUMAN_REVIEW` with an empty authorization list.
- Python null lifecycle-script fields mean the exact audited wheel metadata declares no npm-style lifecycle hooks; they do not claim arbitrary source builds are harmless.
- Current eager consumers are recorded honestly. Named extras are target lanes, not proof that the current API can run without those packages today.
- Archives, scratch code, and the obsolete mutating `integrate_memvid.py` generator are not supported entrypoints and cannot license direct dependencies.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Evidence bug] Corrected the Ruff artifact URL to the exact inspected wheel**

- **Found during:** Overall provenance self-check
- **Issue:** The first evidence record cited a different platform wheel from the exact wheel whose contents were inspected in memory.
- **Fix:** Replaced the link with the exact immutable PyPI artifact URL for `ruff-0.12.7-py3-none-musllinux_1_2_armv7l.whl`.
- **Files modified:** `.planning/evidence/phase-02/package-legitimacy.json`
- **Verification:** Full 18-test validator passed after the correction.
- **Committed in:** `f1e14b5`

**Total deviations:** 1 auto-fixed Rule 1 evidence bug.

## Issues Encountered

- The execution resumed after a usage-limit interruption. Safe-resume checks found no prior 02-14 commits or summary and preserved the existing untracked RED validator.
- The checked-in Docker lane is not currently executable as declared. This is recorded as blocking evidence rather than repaired because Plan 02-14 forbids manifest/runtime changes and later plans own Docker reconciliation.
- `.planning/STATE.md` was already modified by the wave orchestrator and `.trunk/` already existed untracked; both were preserved untouched.

## Verification

- `uv run --locked --no-sync python -m pytest -q tests/test_dependency_audit.py -k 'package or legitimacy or freshness or candidate'` — **10 passed, 8 deselected**
- `uv run --locked --no-sync python -m pytest -q tests/test_dependency_audit.py` — **18 passed**
- `./node_modules/.bin/tsc --noEmit` — **passed**
- `npm run build` — **passed**, Vite 8.0.10 production build
- `python -m json.tool .planning/evidence/phase-02/package-legitimacy.json` — **passed**
- Scope diff from the first task base contains only the evidence JSON and validator; forbidden manifest, lock, installed-environment, and runtime-data paths have no changes.

## Known Stubs

None. Null lifecycle fields are explicit package metadata facts governed by the schema, not unwired implementation placeholders.

## User Setup Required

None. No package was installed, removed, moved, imported for execution, or otherwise changed.

## Next Phase Readiness

- Plan 02-15 has a concrete review artifact and must explicitly approve or reject exact identities/dispositions before any manifest change.
- Four suspicious identities and the blocked Docker lane remain visible stop conditions.
- Plans 02-16 and 02-17 may consume this evidence only while it is fresh and only after the required human gate; the validator expires registry evidence after seven days.

## Self-Check: PASSED

- Both created files exist.
- Commits `527f9aa`, `4fdb8e6`, and `f1e14b5` exist in Git history.
- All task acceptance criteria and plan verification commands passed.
- No manifest, lock, installed artifact, runtime data, provider service, production database, or personal data was changed or opened.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
