---
phase: 02-provider-and-runtime-core
plan: 16
subsystem: dependency-authority
tags: [uv, ruff, docker, optional-dependencies, supply-chain]

requires:
  - phase: 02-provider-and-runtime-core
    provides: Import-safe runtime entrypoints and the exact 16 OK / 4 SUS human decision
provides:
  - Exact 14-action approved Python dependency reconciliation
  - Provider Gemini, MCP, Memvid, and Ruff dependency lanes
  - Lock-faithful Docker runtime using audited uv 0.11.21
  - Fail-closed evidence, digest, rejected-row, lock-churn, and authority tests
affects: [02-17-node-tooling, 02-18-ci, runtime-installation]

tech-stack:
  added: [ruff==0.12.7]
  patterns:
    - Exact pre-edit evidence and authority digest gate
    - Optional capability lanes with one canonical uv lock
    - Semantic rejected-record and shared-version lock comparison

key-files:
  created:
    - tests/test_python_dependency_contract.py
  modified:
    - pyproject.toml
    - uv.lock
    - aura_backend/Dockerfile

key-decisions:
  - "The four rejected SUS declarations and lock records remain byte-for-byte or semantically unchanged; rejection granted no cleanup authority."
  - "Pytest and pytest-asyncio remain in the base declarations because moving them was not one of the 14 approved Python actions."
  - "The container installs exact named runtime lanes from uv.lock and binds the unauthenticated API to loopback by default."

patterns-established:
  - "Dependency authority edits require a passing freshness, SHA-256, exact-decision, exact-action, and current-authority gate before mutation."
  - "Post-lock verification rejects shared-package version churn and preserves audited rejected records independently of textual lock formatting."

requirements-completed: [TEST-05, OPS-02]

duration: 10min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 16: Python Dependency Authority Summary

**Aura now has one uv-based Python authority with exact provider/MCP/Memvid/dev lanes, while every rejected dependency remains untouched.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-08-20T20:48:06Z
- **Completed:** 2026-08-20T20:58:11Z
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

- Independently passed the pre-edit evidence gate against the exact decision text, seven-day freshness window, 16 OK / 4 SUS partition, evidence SHA-256, and both pre-change authority SHA-256 values.
- Applied only the approved Python subset: Ruff 0.12.7, four exact capability-lane moves, and nine direct-declaration removals.
- Preserved `pyzbar`, `faiss-cpu`, `faiss-gpu-cu12`, and `asyncio-mqtt` declarations and their complete semantic lock records.
- Regenerated one 180-package `uv.lock` without changing any shared package version; only Ruff and mechanically orphaned records changed membership.
- Replaced Docker's legacy requirements/pip path with the audited official `ghcr.io/astral-sh/uv:0.11.21` source, locked explicit runtime lanes, stdlib readiness, and loopback binding.

## Task Commits

1. **Task 02-16-01 RED: Python authority and fail-closed pre-edit contract** — `96825d0`
2. **Task 02-16-02 GREEN: Exact approved manifest, lock, and Docker authority** — `cc7e922`
3. **Security RED: Loopback-only Docker runtime contract** — `7082c8a`
4. **Security GREEN: Loopback-only Docker runtime** — `58ab918`

## Files Created/Modified

- `tests/test_python_dependency_contract.py` — Exact approval envelope, pre-edit gate, desired authority, lazy-import, Docker, immutable-SUS, and lock-churn tests.
- `pyproject.toml` — Approved base removals, exact provider/MCP/Memvid extras, and exact Ruff dev group.
- `uv.lock` — Mechanically regenerated single Python lock with 180 packages.
- `aura_backend/Dockerfile` — Official exact uv source/version and lock-faithful local runtime path.

## Decisions Made

- Conditional approval is consumed only through this revised plan's narrow, independently checked action set; the evidence document itself remains non-authorizing.
- The four SUS rows remain present exactly as before. Their rejection is not reinterpreted as permission to remove, move, or repin them.
- Existing base declarations outside the 14 approved actions, including Torch, Chroma, sentence-transformers, pytest, and pytest-asyncio, remain exactly declared.
- The Docker command binds `127.0.0.1`; any broader exposure remains an explicit user decision outside this plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Security] Corrected all-interface Docker binding**

- **Found during:** Final Task 02-16-02 threat review
- **Issue:** The first repaired Docker command bound the local unauthenticated API to `0.0.0.0`, conflicting with Aura's locked loopback-first boundary.
- **Fix:** Added a failing loopback contract, then changed the container command to `127.0.0.1`.
- **Files modified:** `tests/test_python_dependency_contract.py`, `aura_backend/Dockerfile`
- **Verification:** Focused Docker tests and `docker build --check` pass with no warnings.
- **Committed in:** `7082c8a`, `58ab918`

---

**Total deviations:** 1 auto-fixed Rule 1 security issue.
**Impact on plan:** The correction restored the existing private-local boundary without changing dependency authority or package scope.

## Issues Encountered

- Ruff was initially invoked against the Dockerfile as though it were Python; that invalid diagnostic was discarded and Ruff was rerun correctly against the owned Python test file.
- No package installation, environment synchronization, live service, database, storage root, or data mutation was performed.

## Verification

- Pre-edit opt-in authorization gate — **1 passed** before either authority file changed.
- Exact dependency/audit/import/companion/persistence gate — **47 passed, 1 skipped** (the skip is the intentionally post-change-disabled pre-edit gate).
- Complete deterministic offline suite — **421 passed, 1 skipped**.
- `uv lock --check` — **passed**, 180 packages.
- Semantic lock comparison — **passed**; no shared-package version changed and added/removed names matched exact mechanical consequences.
- Rejected-record hashes and unchanged `requirements.txt` SHA-256 — **passed**.
- Ruff on the owned Python contract — **passed**.
- Docker build definition check — **passed with no warnings** using the exact official uv source/version.
- `git diff --check` — **passed**.

## TDD Gate Compliance

- Task 1 RED failed only on the old broad manifest, absent Ruff lock entry, and legacy Docker authority after the independent pre-edit test passed.
- The security review added an explicit RED commit before the loopback GREEN correction.
- Git history contains both RED commits before their corresponding implementation commits.

## Known Stubs

None. Empty containers in the contract tests are deliberate fail-closed comparison values, not unwired product behavior.

## User Setup Required

None. No install or environment synchronization was performed.

## Next Phase Readiness

- Plan 02-17 may now apply only its independently gated Node subset.
- Plan 02-18 can consume exact Ruff and optional runtime lanes from the canonical uv authority.
- The four rejected SUS rows remain explicitly unresolved and outside further Phase 2 mutation authority.

## Self-Check: PASSED

- All four owned implementation/test artifacts and this summary exist.
- All four task/deviation commits exist in Git history in RED/GREEN order.
- Frontmatter contains `status: complete` and both requirement IDs copied from the plan.
- Exact authorization, focused runtime, complete deterministic, Ruff, Docker, lock, whitespace, and immutable-rejected-row gates pass on the final committed implementation.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
