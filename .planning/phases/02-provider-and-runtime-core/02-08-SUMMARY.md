---
phase: 02-provider-and-runtime-core
plan: 08
subsystem: runtime
tags: [fastapi, lifespan, import-safety, local-first, subprocess-testing]

requires:
  - phase: 02-provider-and-runtime-core
    provides: ApplicationRuntime ordered startup, partial unwind, and provider-first shutdown
  - phase: 01-preservation-and-trusted-baseline
    provides: Loopback, explicit-origin, no-auth, filesystem, and companion compatibility contracts
provides:
  - Resource-free create_app factory and compatibility module-level app
  - Lifespan ownership of exactly one ApplicationRuntime with fail-closed startup state
  - Bounded import probes for runtime, provider, network, process, database, model, client, and write effects
  - Lifespan-only construction of legacy storage, MCP, embedding, autonomic, and provider resources
affects: [02-09-conversation-runtime, 02-10-health, 02-11-runtime-cli]

tech-stack:
  added: []
  patterns: [pure application factory, lifespan-owned runtime, fail-closed subprocess import evidence]

key-files:
  created:
    - tests/runtime/test_import_safety.py
    - tests/runtime/test_app_lifespan.py
  modified:
    - aura_backend/main.py
    - tests/support/main_subprocess_probe.py

key-decisions:
  - "Keep app = create_app() for existing Uvicorn and test imports while deferring every resource constructor to lifespan."
  - "Publish app.state.runtime only after successful startup and clear it before shutdown so partial state cannot appear ready."
  - "Retain legacy route globals only as lifespan-populated aliases until Plan 02-09 migrates conversation orchestration to the typed runtime."

patterns-established:
  - "Plain TestClient proves route and middleware behavior without lifespan; context-managed TestClient is mandatory for lifecycle evidence."
  - "Import probes reject timeout, crash, malformed, partial, or side-effect evidence instead of treating missing observations as success."

requirements-completed: [TEST-03, OPS-01]

duration: 8min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 08: FastAPI Composition and Import Safety Summary

**Aura now exposes a pure FastAPI factory while one lifespan-owned runtime constructs and closes all model, storage, MCP, embedding, and autonomic resources.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-08-20T19:20:37Z
- **Completed:** 2026-08-20T19:28:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Removed import-time environment loading, provider-factory construction, shared-embedding construction, optional Google SDK import, and resource-owning Aura integration imports from `aura_backend.main`.
- Added `create_app(runtime_builder=...)`, retained `app = create_app()`, and moved route registration to one shared router so independently created apps preserve the complete local API surface.
- Made FastAPI lifespan build, start, publish, and close exactly one runtime; startup failure is never published as ready and still receives one cleanup call.
- Preserved the existing dependency order behind `ApplicationRuntime`, including database protection before storage, provider last on startup, and provider first on reverse shutdown.
- Strengthened the bounded subprocess probe with explicit traps for network, subprocess, SQLite, client/factory/model construction, repository writes, and optional-provider absence.

## Task Commits

Each task was committed through explicit RED and GREEN gates:

1. **Task 02-08-01 RED: import purity and fail-closed child evidence** - `b7c29ad`
2. **Task 02-08-01 GREEN: resource-free application imports** - `c97348e`
3. **Task 02-08-02 RED: application factory and lifespan ownership** - `2c3deb2`
4. **Task 02-08-02 GREEN: ordered lifespan composition** - `6335ba1`

## Files Created/Modified

- `aura_backend/main.py` - Pure application factory, lifespan composition, deferred concrete imports, compatibility aliases, and module-level app.
- `tests/runtime/test_import_safety.py` - Offline import purity, optional SDK absence, and invalid-evidence tests.
- `tests/runtime/test_app_lifespan.py` - Exact builder/start/close, partial-start, CORS, route, and compatibility tests.
- `tests/support/main_subprocess_probe.py` - Side-effect traps, import scenarios, construction counters, and fail-closed diagnostics.

## Decisions Made

- The compatibility app is created only after all router declarations exist. This keeps `aura_backend.main:app` stable without duplicating route definitions across factory instances.
- Legacy MCP routes are imported and attached once after their owning runtime resource starts. Their module-level client can therefore no longer be constructed merely by importing Aura.
- Compatibility globals remain inert `None` aliases outside lifespan and are cleared after shutdown. Plan 02-09 can now replace the remaining route reads with `app.state.runtime` without combining lifecycle and conversation behavior changes.
- The existing `ApplicationRuntime` from Plan 02-07 already supplied correct partial unwind and idempotent close semantics, so it required no speculative changes.

## Verification

- Import/local boundary focus: **13 passed**.
- Lifespan/local/filesystem integration: **44 passed**.
- Runtime lifecycle plus app lifespan: **23 passed**.
- Complete deterministic suite: **322 passed**.
- Ruff on all owned Python files: **passed**.
- Python bytecode compilation on all owned Python files: **passed**.
- Frontend TypeScript check and Vite production build: **passed**.
- Repository whitespace check: **passed**.
- Data-root metadata hash before and after the full suite remained `1b2e5ee264a0c211b11b591d5ce24931ca74ce52dc653fc64b1678e7d97b942f`.
- No live model, network service, credential, package install, manifest, lockfile, database, backup, or storage root was used or changed.

## TDD Gate Compliance

- Task 1 RED failed because the old composition root imported Google's optional SDK and constructed the provider factory and shared embedding singleton. GREEN removed those import effects and all import/local boundary tests passed.
- Task 2 RED failed at collection because `create_app` did not exist. GREEN added the pure factory and lifespan owner, after which all five new lifecycle tests and the complete compatibility set passed.
- Git history contains each `test(02-08)` RED commit before its corresponding `feat(02-08)` GREEN commit.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The deliberate RED import trap exposed an additional practical failure: eager Google SDK import reached MCP annotations that expected the real `subprocess.Popen` class. Removing the unselected SDK import resolved the underlying import impurity rather than weakening the trap.
- The shared main worktree contains the orchestrator-owned `.planning/STATE.md` edit and pre-existing untracked `.trunk/`; both were preserved and excluded from every task commit.

## Known Stubs

None. Lifecycle `None` aliases are deliberate unavailable/pre-start state, and empty lists in tests are event/call recorders rather than unwired product behavior.

## Threat Flags

None. The plan implements the registered import-to-host and lifespan-to-resource boundaries. It adds no new endpoint, authentication path, schema, dependency, or externally reachable service.

## User Setup Required

None. Deterministic verification remains offline and the default product remains local, loopback-first, and sign-in-free.

## Next Phase Readiness

- Plan 02-09 can consume `request.app.state.runtime.provider_runtime` and remove the remaining provider/client compatibility aliases from the conversation path.
- Health and CLI plans can safely create app instances and inspect cached lifecycle state without triggering model, service, or storage initialization.
- No blockers remain for the next plan.

## Self-Check: PASSED

- All four owned implementation/test artifacts and this summary exist on disk.
- All four RED/GREEN commits exist in Git history in the required order.
- Frontmatter contains `status: complete` and both requirement IDs copied from the plan.
- Focused, complete deterministic, lint, compile, TypeScript, build, whitespace, and data-root invariance gates passed after the final implementation.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
