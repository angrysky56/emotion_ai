---
phase: 02-provider-and-runtime-core
plan: 11
subsystem: runtime-cli
tags: [argparse, preflight, uvicorn, lifecycle, redaction, tdd]

requires:
  - phase: 02-10
    provides: Cached fail-closed readiness and selected-provider health semantics
provides:
  - Complete non-mutating startup preflight with exact statuses and exits
  - Canonical loopback-first Uvicorn factory and optional frontend process owner
  - Deterministic command, readiness, signal, cleanup, and redaction evidence
affects: [02-12-launchers, 02-13-startup-docs, 02-18-ci]

tech-stack:
  added: []
  patterns:
    - Fixed required-check registry with aggregate status derived from complete evidence
    - Injected OS, provider, readiness, and process probes for offline verification
    - Signal-driven reverse cleanup limited to child handles started by Aura

key-files:
  created:
    - aura_backend/runtime/cli.py
    - aura_backend/runtime/__main__.py
    - tests/runtime/test_cli.py
  modified: []

key-decisions:
  - "Preflight has twelve required named checks; omitted, duplicate, contradictory, blocked, missing, failed, and not-run evidence cannot pass."
  - "Provider readiness uses bounded metadata only, while application readiness inspects the resource-free factory and derives startup permission from every prerequisite."
  - "Serve launches Uvicorn with factory and lifespan enabled, waits for truthful /ready, and stops only owned children in reverse order."

patterns-established:
  - "Report-only startup: inspection may read manifests, bind-test a port, inspect permissions, and query provider metadata, but never mutates dependencies, configuration, models, permissions, processes, or storage."
  - "Safe diagnostics: public CLI JSON contains only fixed fields, safe codes, validated versions/model identifiers, and numeric ports."

requirements-completed: [TEST-03, OPS-01]

duration: 18min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 11: Canonical Runtime Preflight and Serve Summary

**Aura now has one cross-platform Python entry point that truthfully checks startup prerequisites without mutation, then owns loopback API/UI processes through readiness and reverse shutdown.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-08-20T20:10:16Z
- **Completed:** 2026-08-20T20:28:43Z
- **Tasks:** 2/2
- **Files modified:** 3

## Accomplishments

- Added twelve exact preflight checks for Python, uv, Node, npm, both lock authorities, provider configuration, port, storage, provider service/model metadata, and application readiness.
- Made every non-pass state explicit and nonzero; incomplete, duplicate, contradictory, or vacuous evidence is rejected before startup.
- Kept preflight report-only: no sync/install/download/model pull, configuration write, chmod, process termination, database open, or Aura startup occurs.
- Added `python -m aura_backend.runtime preflight` and `serve` with loopback defaults, explicit LAN/no-sign-in warning, Uvicorn factory/lifespan mode, `/ready` gating, backend-only/frontend-only modes, child-failure propagation, and reverse owned cleanup.
- Proved diagnostics omit raw paths, credentials, content, URLs, tracebacks, and source exceptions.

## Task Commits

Each TDD gate and correction was committed atomically:

1. **Task 1 RED: complete fail-closed preflight contract** — `c0ee770`
2. **Task 1 GREEN: non-mutating preflight implementation** — `9dd3bb0`
3. **Task 2 RED: owned serve/readiness/cleanup contract** — `c59c3cc`
4. **Task 2 GREEN: preflight-gated local service ownership** — `13509e6`
5. **Threat review RED: prompt signal-interruption contract** — `e78e10d`
6. **Threat review GREEN: immediate SIGINT/SIGTERM interruption** — `1038b79`

## Files Created/Modified

- `aura_backend/runtime/cli.py` — Typed preflight evidence, bounded inspection probes, JSON command boundary, Uvicorn/frontend process ownership, readiness polling, signals, and exact exits.
- `aura_backend/runtime/__main__.py` — Cross-platform `python -m aura_backend.runtime` entry point.
- `tests/runtime/test_cli.py` — Offline preflight truth tables, mutation/redaction tripwires, module subprocess help, exact command arrays, readiness, child failure, LAN, signal, and reverse-cleanup tests.

## Decisions Made

- All twelve canonical checks remain required for the canonical serve gate, including compatibility modes; a partial environment cannot be reported ready.
- `uv lock --check --offline` validates Python lock freshness without synchronizing, while Node lock freshness is verified by read-only comparison of manifest and lock root declarations.
- Storage checks inspect existence and writability without creating/opening data; a missing path is reported with remediation rather than silently created.
- A provider/model `unknown` observation remains blocked, not successful; model absence is distinct from service unavailability and never triggers a pull.
- The API child uses `aura_backend.main:create_app --factory --lifespan on` and is not called ready until its cached `/ready` contract returns explicit ready truth.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Signal cleanup] Interrupted readiness waits immediately on SIGINT/SIGTERM**
- **Found during:** Final Task 2 threat/control review
- **Issue:** The first signal handler set a stop event but could leave a bounded readiness request running until timeout before cleanup began.
- **Fix:** The handler now records the stop request and raises the controlled interruption consumed by `run_serve`, whose `finally` block closes owned children in reverse order.
- **Files modified:** `aura_backend/runtime/cli.py`, `tests/runtime/test_cli.py`
- **Verification:** The signal test failed before the fix, passes afterward, and the full offline suite remains green.
- **Committed in:** `e78e10d`, `1038b79`

---

**Total deviations:** 1 auto-fixed (Rule 1 correctness/signal cleanup).
**Impact on plan:** Strengthened the required prompt shutdown behavior without expanding scope or changing the local/no-auth model.

## Issues Encountered

- The installed GSD helper still fails while resolving its own missing `../../../package.json`. Direct plan commands and atomic Git commits were used; shared `STATE.md` remains untouched for the orchestrator.

## Verification

- `uv run --locked --no-sync python -m pytest -q tests/runtime/test_cli.py -k 'preflight or check or redaction or mutation'` — passed.
- `uv run --locked --no-sync python -m pytest -q tests/runtime/test_cli.py -k 'serve or signal or child or loopback'` — 4 passed.
- CLI, health, lifecycle, import-safety, and local-boundary regression — 84 passed.
- `uv run --locked --no-sync python -m pytest -q tests -m 'not live'` — 387 passed.
- `npx tsc --noEmit` — passed.
- `npm run build` — passed with Vite 8.0.10.
- Ruff on all Plan 02-11 source/test files — passed.
- `git diff --check` — passed.
- No live provider, real server, dependency sync/install, manifest/lock edit, or storage/data operation was used.

## Known Stubs

None.

## User Setup Required

None - no account, authentication, or external configuration is required for this implementation.

## Next Phase Readiness

- Plan 02-12 can replace legacy shell/batch behavior with thin delegates to this canonical command.
- Plan 02-13 can document exact preflight statuses, remediations, and safe local/LAN operation.
- No blocker remains for the next wave.

## Self-Check: PASSED

- All three declared implementation/test files exist.
- All six listed task/deviation commits exist in Git history.
- Task-specific, focused runtime, complete offline Python, Ruff, TypeScript, production build, and whitespace gates pass.
- Shared `STATE.md`, dependency manifests/locks, data/storage roots, and `.trunk/` were not modified by this plan.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
