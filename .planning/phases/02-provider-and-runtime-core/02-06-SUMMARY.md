---
phase: 02-provider-and-runtime-core
plan: 06
subsystem: provider-runtime
tags: [python, provider-factory, ollama, autonomic, privacy, tdd]

requires:
  - phase: 02-provider-and-runtime-core
    plan: 04
    provides: Shared typed Ollama and OpenRouter adapters
  - phase: 02-provider-and-runtime-core
    plan: 05
    provides: Lazy asynchronous Gemini adapter
provides:
  - Strict local-first factory that imports and constructs only the selected adapter
  - Provider-neutral autonomic generation through an injected ProviderRuntime
  - Truthful disabled autonomic state when no compatible runtime is configured
  - Content-free autonomic failure, cancellation, and status diagnostics
affects: [02-07, application-runtime, conversation-orchestration, health]

tech-stack:
  added: []
  patterns:
    - Validate selection and credentials before importing a concrete adapter
    - Optional background processing receives the selected typed runtime by injection
    - Disabled optional subsystems start no worker and report a stable reason

key-files:
  created:
    - tests/providers/test_factory.py
    - tests/runtime/test_autonomic_provider.py
  modified:
    - aura_backend/providers/factory.py
    - aura_backend/aura_autonomic_system.py

key-decisions:
  - "The compatibility factory defaults to Ollama and delegates to one strict ProviderSettings constructor; unknown names never fall back to cloud."
  - "Autonomic model work uses the selected ProviderRuntime or remains disabled with reason not_configured; it never creates its own Gemini client."
  - "Autonomic task failures retain only typed terminal codes in task state and count-only system status/logs."

patterns-established:
  - "Lazy selection: each concrete provider import lives only inside its exact validated ProviderKind branch."
  - "Optional runtime truth: no injected runtime means disabled, no worker, and no model-client side effect."

requirements-completed: [TEST-03, AI-01, AI-03]

duration: 16min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 06: Local-First Factory and Autonomic Provider Boundary Summary

**Aura now selects exactly one validated provider with Ollama as the default, while optional autonomic work uses an injected typed runtime or stays honestly disabled without importing or constructing Google clients**

## Performance

- **Duration:** 16 min
- **Started:** 2026-08-20T18:39:02Z
- **Completed:** 2026-08-20T18:55:18Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Removed eager concrete-adapter imports and the unknown-provider Gemini fallback from the factory.
- Added explicit `ProviderSettings` construction that validates selection and cloud credentials before importing or constructing any adapter.
- Preserved the legacy factory call surface while changing its credential-free default from Gemini to local Ollama.
- Removed all Google imports and client construction from the autonomic module.
- Routed autonomic generation through `ProviderRuntime.generate(ProviderRequest)` and normalized success/failure handling.
- Made missing autonomic runtime configuration a stable disabled state that starts no worker.
- Replaced raw exception/task-content logging with safe task type, duration, terminal code, and count diagnostics.

## Task Commits

Each task was committed through a RED/GREEN TDD pair:

1. **Task 1 RED: strict lazy factory contract** - `ad907e6` (test)
2. **Task 1 GREEN: local-first selected-adapter factory** - `b90bef9` (feat)
3. **Task 2 RED: autonomic provider injection contract** - `f22aad5` (test)
4. **Task 2 GREEN: injected/disabled autonomic runtime** - `9501e26` (feat)

## Files Created/Modified

- `aura_backend/providers/factory.py` - Validated exact-branch provider construction and local-first compatibility wrapper.
- `aura_backend/aura_autonomic_system.py` - ProviderRuntime injection, disabled state, neutral model requests, and safe terminal diagnostics.
- `tests/providers/test_factory.py` - Import, construction, credential, fallback, and redaction tripwires.
- `tests/runtime/test_autonomic_provider.py` - Disabled startup, injected success/failures, cancellation, import-safety, and diagnostic privacy tests.

## Decisions Made

- `ProviderSettings.from_mapping` remains the sole environment-validation boundary; the factory does not probe providers or read `.env` files.
- The compatibility wrapper retains its old positional tool arguments so existing startup code remains callable, but only the neutral `ToolExecutor` crosses into adapters.
- The legacy autonomic model-name argument remains callable but is not trusted as provider ownership or diagnostic metadata. Status reports `selected_provider` or `not_configured` instead.
- Cancellation is re-raised after marking the autonomic task failed with the safe `cancelled` code; it is never converted to completion.

## Verification Evidence

- Factory contract: **9 passed**.
- Autonomic provider contract: **8 passed**.
- Combined provider, companion, local-boundary, and runtime-security lane: **167 passed**.
- Full deterministic backend lane: **293 passed in 33.52s**.
- Ruff on all four owned files: **passed**.
- Python bytecode compilation on all four owned files: **passed**.
- Frontend TypeScript check and Vite production build: **passed**.
- Repository whitespace check: **passed**.
- All tests used fakes or subprocess import probes; no Ollama, Gemini, OpenRouter, socket, credential, or live model was used.

## TDD Gate Compliance

- Task 1 RED failed on eager adapter imports, the missing strict constructor, Gemini default, and unknown-provider fallback; GREEN made all nine cases pass.
- Task 2 RED failed at collection because the disabled/runtime-injection state did not exist; GREEN made all eight success, failure, timeout, cancellation, redaction, and import-safety cases pass.
- Git history contains each `test(02-06)` commit before its matching `feat(02-06)` commit.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The installed GSD JavaScript helper remains unusable because it cannot resolve `../../../package.json`. Direct locked uv, pytest, Ruff, compile, TypeScript, build, Git, and diff commands supplied the execution evidence instead.
- One initially referenced local-boundary test path was stale; the repository's actual test is `tests/api/test_local_boundary.py`, which passed in the 167-test compatibility lane.

## Known Stubs

None. Optional `None` values represent explicit absence in configuration/task state, and empty test recorders are assertion fixtures rather than unfinished application behavior.

## Threat Flags

None. The selected-provider import/client boundary and autonomic payload/model boundary are the exact registered Plan 02-06 surfaces. No endpoint, authentication path, filesystem access, schema, dependency, manifest, lock, data store, or external service was added.

## User Setup Required

None. Local Ollama remains credential-free, deterministic tests remain offline, and autonomic processing is safely disabled until the application runtime explicitly injects a compatible selected provider.

## Next Phase Readiness

- Application lifecycle work can now construct one selected provider without importing alternatives.
- Conversation and analysis orchestration can inject the same selected runtime into optional autonomic work without a Gemini side channel.
- Existing Phase 1 response, fallback, session-clear, persistence, loopback, CORS, and no-sign-in checks remain green.

## Self-Check: PASSED

- All four owned implementation/test artifacts and this summary exist on disk.
- All four RED/GREEN commits exist in Git history in the required order.
- Frontmatter contains `status: complete` and all three requirement IDs copied from the plan.
- Focused, compatibility, full deterministic, Ruff, compile, TypeScript, build, and whitespace gates passed after the final implementation.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
