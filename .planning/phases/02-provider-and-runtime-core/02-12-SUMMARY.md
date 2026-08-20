---
phase: 02-provider-and-runtime-core
plan: 12
subsystem: startup-entrypoints
tags: [shell, windows-batch, uv, runtime-cli, offline-tests]

requires:
  - phase: 02-11
    provides: Canonical preflight-gated runtime serve command and owned lifecycle
provides:
  - Seven thin cross-platform startup delegates with no installation or process mutation
  - Exact offline command-spy and static safety contract for every supported wrapper
  - Explicit standalone MCP entry point separated from normal Aura readiness
affects: [02-13-startup-docs, 02-18-ci, operations]

tech-stack:
  added: []
  patterns:
    - POSIX exec delegation with repository-root resolution and exact exit propagation
    - Windows batch delegation with percent-star forwarding and errorlevel propagation
    - Static mutation bans before command-spy execution

key-files:
  created:
    - tests/runtime/test_startup_entrypoints.py
  modified:
    - start_full_system.sh
    - start_full_system.bat
    - aura_backend/start.sh
    - aura_backend/start_api.sh
    - aura_backend/start_all.sh
    - aura_backend/start_frontend.sh
    - aura_backend/start_mcp.sh

key-decisions:
  - "Every normal launcher delegates to uv run --locked --no-sync python -m aura_backend.runtime serve; host selection remains in validated runtime settings."
  - "The optional MCP wrapper invokes aura_backend.aura_server explicitly and remains separate from normal Aura readiness."

patterns-established:
  - "Thin launchers: resolve the repository, verify uv exists, exec one canonical command, and forward every argument."
  - "Safe launcher tests: reject forbidden static behavior before any wrapper is allowed to run against a fake uv command."

requirements-completed: [TEST-03, OPS-01]

duration: 4min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 12: Cross-Platform Startup Delegates Summary

**Aura's seven supported launchers now delegate to one tested, loopback-first runtime path without installing dependencies, changing configuration, killing processes, opening terminals, or claiming readiness early.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-20T20:36:47Z
- **Completed:** 2026-08-20T20:41:00Z
- **Tasks:** 3/3
- **Files modified:** 8 production/test files

## Accomplishments

- Replaced the drifting Linux and Windows root launchers with exact `uv run --locked --no-sync python -m aura_backend.runtime serve` delegates.
- Replaced backend API/full/all/frontend wrappers with canonical full, backend-only, or frontend-only modes and exact argument/exit propagation.
- Corrected the MCP wrapper from the nonexistent `mcp_server.py` path to the supported `aura_backend.aura_server` module while keeping it explicitly optional.
- Removed implicit installs, environment activation, `.env` writes, permission changes, port/process kills, sleeps, health polling, detached terminals, reload, and LAN binding from supported wrappers.
- Added 21 offline tests that statically gate scripts before command-spy execution, preventing a legacy unsafe wrapper from running during tests.

## Task Commits

Each TDD gate and correction was committed atomically:

1. **Task 1 RED: root launcher safety/delegation contract** — `4b09614`
2. **Task 1 GREEN: exact Linux/Windows runtime delegates** — `d19e982`
3. **Task 1 correction: restore POSIX executable intent** — `878bc8c`
4. **Task 2 RED: backend mode and lifecycle contract** — `064161b`
5. **Task 2 GREEN: full/backend-only delegates** — `aa0897d`
6. **Task 3 RED: frontend/MCP and complete static contract** — `acffc22`
7. **Task 3 GREEN: frontend-only and standalone MCP delegates** — `8a37beb`

## Files Created/Modified

- `tests/runtime/test_startup_entrypoints.py` — Offline static bans, fake-uv command spies, exact cwd/argv checks, missing-uv behavior, and failure propagation for all wrappers.
- `start_full_system.sh` — POSIX canonical full-serve delegate.
- `start_full_system.bat` — Windows canonical full-serve delegate with `%*` and `%errorlevel%` propagation.
- `aura_backend/start.sh` and `aura_backend/start_all.sh` — Compatibility delegates for full serve.
- `aura_backend/start_api.sh` — Compatibility delegate for `serve --backend-only`.
- `aura_backend/start_frontend.sh` — Explicit `serve --frontend-only` delegate.
- `aura_backend/start_mcp.sh` — Explicit optional `aura_backend.aura_server` delegate.

## Decisions Made

- POSIX wrappers use `exec` so the canonical runtime owns signals and its exit status becomes the wrapper exit status without another lifecycle layer.
- Windows uses one foreground batch command and `exit /b %errorlevel%`; it does not open another terminal or hard-code a host.
- Wrapper checks only report missing `uv` with the official remediation URL. They never install or synchronize it.
- MCP is deliberately not folded into normal startup or readiness; consolidation of its implementation remains outside this plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - File mode] Restored root POSIX executable intent**
- **Found during:** Task 1 implementation
- **Issue:** Whole-file replacement temporarily changed `start_full_system.sh` from executable to non-executable.
- **Fix:** Restored the tracked executable bit; no wrapper contains or runs `chmod`.
- **Files modified:** `start_full_system.sh`
- **Verification:** Git reports mode `100755`; the complete launcher suite and shell syntax gate pass.
- **Committed in:** `878bc8c`

---

**Total deviations:** 1 auto-fixed (Rule 1 file-mode correctness).
**Impact on plan:** No scope expansion; the correction preserved the launcher's existing executable intent.

## Issues Encountered

- The first success-claim assertion mistook `getting-started` inside the official uv URL for a readiness claim. The test now removes URLs before checking user-facing success language.
- The installed GSD helper still cannot resolve its own package metadata, so direct atomic Git commits were used and the shared `STATE.md` was deliberately preserved for the orchestrator.

## Verification

- `uv run --locked --no-sync python -m pytest -q tests/runtime/test_startup_entrypoints.py tests/runtime/test_cli.py` — 50 passed.
- `uv run --locked --no-sync python -m pytest -q tests -m 'not live'` — 408 passed.
- `uv run --locked --no-sync ruff check tests/runtime/test_startup_entrypoints.py` — passed.
- `npx tsc --noEmit` — passed.
- `npm run build` — passed with Vite 8.0.10.
- `sh -n` across all six POSIX wrappers — passed.
- Static Windows command/exit contract and all-seven mutation bans — passed.
- `git diff --check` — passed.
- No live provider, real service, package install/sync, manifest/lock edit, data/storage operation, `.trunk/` change, or shared-state edit was performed.

## Known Stubs

None.

## Threat Controls

- **T-02-ST / T-02-SC:** Exact foreground delegates only; static bans prevent install, sync, download, permission change, process kill, reload, environment activation/write, or terminal spawning.
- **T-02-LH:** No wrapper names a host; validated runtime settings retain the loopback default and explicit LAN warning.
- **T-02-HF:** POSIX `exec` and Windows `%errorlevel%` propagate canonical failure; wrappers make no early readiness claim.

## User Setup Required

None. If `uv` is missing, the wrapper exits nonzero and points to the official uv installation documentation without changing the machine.

## Next Phase Readiness

- Plan 02-13 can document one truthful cross-platform startup path and its preflight remediation codes.
- Plan 02-18 can run the same deterministic launcher contract in CI without starting services.
- No blocker remains from Plan 02-12.

## Self-Check: PASSED

- All eight declared production/test files exist and the six POSIX launchers retain tracked mode `100755`.
- All seven listed TDD/correction commits exist in Git history.
- Launcher/CLI, complete offline Python, Ruff, TypeScript, frontend build, shell syntax, static batch, and whitespace gates pass.
- Shared `STATE.md`, dependency manifests/locks, data/storage roots, and `.trunk/` were not modified by this plan.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
