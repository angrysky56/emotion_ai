---
phase: 02-provider-and-runtime-core
plan: 07
subsystem: runtime
tags: [asyncio, lifecycle, providers, configuration, cancellation]

requires:
  - phase: 02-provider-and-runtime-core
    provides: ProviderRuntime cancellation, close semantics, and local-first provider settings
  - phase: 01-preservation-and-trusted-baseline
    provides: Loopback, explicit-origin, no-auth, and persistence compatibility contracts
provides:
  - Pure typed RuntimeSettings with loopback-first defaults and bounded validation
  - Dependency-injected ApplicationRuntime with exact ordered startup and reverse cleanup
  - Required selected-provider readiness and cancellation-first shutdown ownership
  - Deterministic partial-start, optional-absence, idempotence, and active-stream tests
affects: [02-08-fastapi-lifespan, 02-10-health, 02-11-runtime-cli]

tech-stack:
  added: []
  patterns: [explicit mapping configuration, AsyncExitStack ownership, provider-last startup]

key-files:
  created:
    - aura_backend/runtime/__init__.py
    - aura_backend/runtime/config.py
    - aura_backend/runtime/app.py
    - tests/runtime/test_lifecycle.py
  modified: []

key-decisions:
  - "Start the selected ProviderRuntime last so reverse shutdown cancels and closes provider work before dependent storage and tool resources."
  - "Keep runtime parsing pure by accepting an explicit mapping and constructing only typed values and unresolved Path objects."
  - "Treat an absent selected provider as a required startup failure while optional unconfigured subsystems remain visible and non-fatal."

patterns-established:
  - "Factories construct resources only during ApplicationRuntime.start and return a value with one bound async close callback."
  - "Lifecycle snapshots expose only fixed states and safe codes; source exceptions and resource values never enter status payloads."

requirements-completed: [TEST-03, AI-03, OPS-01]

duration: 17min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 07: Application Runtime Lifecycle Summary

**Pure local-first settings and one deterministic lifecycle owner now govern ordered resource startup, required provider readiness, active-stream cancellation, and idempotent reverse shutdown.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-08-20T18:57:32Z
- **Completed:** 2026-08-20T19:14:47Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added frozen `RuntimeSettings` parsing for the existing host, port, origin, storage, and selected-provider keys plus a bounded preflight timeout, without reading environment state or touching storage.
- Added `ApplicationRuntime`, which starts injected factories in dependency order, registers exactly one async cleanup for each successful resource, and unwinds partial startup in strict reverse order.
- Made the selected `ProviderRuntime` a typed required resource stored before readiness and started last so its existing `aclose()` rejects new work, cancels and awaits streams, and closes the adapter before remaining dependencies shut down.
- Represented optional absence as `not_configured`, distinct from required startup failure, without making a valid local runtime unready.

## Task Commits

Each task was committed atomically through RED and GREEN:

1. **Task 02-07-01 RED: pure settings and ordered lifecycle contract** - `988a58a`
2. **Task 02-07-01 GREEN: settings and resource ownership** - `4b0a730`
3. **Task 02-07-02 RED: provider cancellation and optional-state contract** - `2f0b9c8`
4. **Task 02-07-02 GREEN: required provider and cancellation-first shutdown** - `ca2b43e`

## Files Created/Modified

- `aura_backend/runtime/__init__.py` - Import-light public runtime API.
- `aura_backend/runtime/config.py` - Pure local-first settings parser with safe bounded failures.
- `aura_backend/runtime/app.py` - Ordered resource stack, safe snapshots, typed provider accessor, partial unwind, and idempotent shutdown.
- `tests/runtime/test_lifecycle.py` - Offline RED/GREEN proofs for settings, every partial boundary, reverse close, provider cancellation, and optional absence.

## Decisions Made

- The provider is a dedicated required stage named `selected_provider`; callers cannot claim readiness or retrieve it during partial startup or shutdown.
- Generic dependencies are declared first and the provider stage is appended last. Reverse stack cleanup therefore invokes `ProviderRuntime.aclose()` first without duplicating its internal cancellation logic.
- Configuration failures expose only recognized setting names. Runtime failures expose only fixed codes and safe resource names, never source exception text.
- `Path` construction validates the configured storage token but does not resolve, create, open, migrate, or inspect any storage root.

## Verification

- Plan-focused lifecycle suite: **18 passed**.
- Lifecycle/provider streaming/local boundary gate: **54 passed**.
- Complete deterministic suite, partitioned only to obtain reliable terminal evidence: **311 passed** (`41 preservation + 70 API/characterization + 200 provider/runtime/root`).
- Provider streaming suite: **11 passed**.
- Ruff on all four owned files: **passed**.
- Python bytecode compilation on all four owned files: **passed**.
- Frontend TypeScript check and Vite production build: **passed**.
- Repository whitespace check: **passed**.
- No live model, network service, credential, database, storage root, manifest, lockfile, or package installation was used or changed.

## TDD Gate Compliance

- Task 1 RED failed at collection because `aura_backend.runtime` did not exist; GREEN made the settings, order, partial-unwind, close, and import-purity matrix pass.
- Task 2 RED failed because `ApplicationRuntime` did not accept or expose a selected provider; GREEN made required-provider, optional-absence, cancellation, and shutdown-order cases pass.
- Git history contains each `test(02-07)` commit before its corresponding `feat(02-07)` commit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Included the synthetic provider stage in cached status initialization**
- **Found during:** Task 02-07-02 full lifecycle verification
- **Issue:** The provider stage was appended after the generic resources, but the first implementation initialized statuses from the pre-append tuple, causing partial-start snapshots to raise `KeyError`.
- **Fix:** Initialize status entries from the final ordered resource sequence and retain `selected_provider` as the explicit safe status name.
- **Files modified:** `aura_backend/runtime/app.py`, `tests/runtime/test_lifecycle.py`
- **Verification:** All 18 lifecycle tests and all 311 deterministic tests pass.
- **Committed in:** `ca2b43e`

---

**Total deviations:** 1 auto-fixed bug
**Impact on plan:** The fix is necessary for truthful fail-closed partial-start evidence and adds no scope.

## Issues Encountered

- The installed GSD JavaScript helper still cannot resolve `../../../package.json`; direct locked uv, pytest, Ruff, compile, TypeScript, build, Git, and diff commands supplied the evidence instead.
- A one-shot full-suite tool capture ended without a terminal status and was treated as no evidence. The same 311-test collection was rerun in three complete, non-overlapping partitions, each with explicit exit code zero.

## Known Stubs

None. `None` represents deliberate optional-not-configured or pre-start state, and empty collections in tests are event/status recorders rather than unfinished production behavior.

## Threat Flags

None. This plan implements the registered configuration-to-factory and shutdown-to-resource boundaries. It adds no endpoint, authentication path, schema, storage access, dependency, network call, process, or external service.

## User Setup Required

None. Aura remains loopback-first and credential-free on the default Ollama path; all verification was offline.

## Next Phase Readiness

- Plan 02-08 can construct concrete resources only inside FastAPI lifespan, call `await runtime.start()`, store the ready runtime on `app.state`, and close it once in `finally`.
- Health and CLI plans can consume cached safe lifecycle statuses and pure `RuntimeSettings` without initializing or probing resources.

## Self-Check: PASSED

- All four owned implementation/test artifacts and this summary exist on disk.
- All four RED/GREEN task commits exist in Git history in the required order.
- Frontmatter contains `status: complete` and all three requirement IDs copied from the plan.
- Focused, compatibility, complete deterministic, lint, compile, TypeScript, build, and whitespace gates passed after the final implementation.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
