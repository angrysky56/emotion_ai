---
phase: 02-provider-and-runtime-core
plan: 09
subsystem: api
tags: [fastapi, provider-runtime, conversation, redaction, cancellation, persistence]

requires:
  - phase: 02-provider-and-runtime-core
    provides: Typed ProviderRuntime, neutral tool catalog, and lifespan-owned ApplicationRuntime
  - phase: 01-preservation-and-trusted-baseline
    provides: Seven-field response, HTTP-200 fallback, session cleanup, persistence, and local-boundary characterization
provides:
  - Provider-neutral user emotion, Aura emotion, and cognitive-focus analysis transport
  - Runtime-owned non-streaming conversation orchestration through app.state.runtime
  - Adversarial coverage for every typed failure, invalid success, cancellation, redaction, tools, and persistence
affects: [02-10-health, 02-11-runtime-cli, phase-03-storage, phase-04-evaluation]

tech-stack:
  added: []
  patterns: [typed provider request orchestration, content-free failure logging, runtime-owned neutral tool discovery]

key-files:
  created:
    - aura_backend/conversation/__init__.py
    - aura_backend/conversation/analysis.py
    - tests/conversation/test_analysis_transport.py
    - tests/api/test_provider_compatibility.py
  modified:
    - aura_backend/main.py
    - tests/support/main_subprocess_probe.py

key-decisions:
  - "Keep the three legacy prompts, mappings, parser defaults, and DTO shapes unchanged while injecting ProviderRuntime.generate."
  - "Build and expose one neutral ToolCatalog with the lifespan resources; the live route never inspects the Gemini bridge or its private mapping."
  - "Treat asyncio cancellation separately from typed terminal failures: cancellation propagates, while every ProviderFailure code retains the Phase 1 HTTP-200 fallback and one session clear."

patterns-established:
  - "Conversation routes obtain provider and tool dependencies only from request.app.state.runtime."
  - "Default logs retain safe stage, error-code, and correlation metadata but never prompt, answer, source exception, SDK object, or hidden-reasoning content."

requirements-completed: [TEST-03, AI-01, AI-03]

duration: 20min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 09: Provider-Neutral Conversation Route Summary

**Aura's complete non-streaming conversation path now uses one selected typed provider for the answer and all three analyses while preserving its seven-field local API and persistence behavior.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-08-20T19:29:54Z
- **Completed:** 2026-08-20T19:49:57Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Extracted the existing user-emotion, Aura-emotion, and ASEKE-focus prompts and parsers into a provider-neutral conversation module with typed requests, safe defaults, content-free failure logs, and cancellation propagation.
- Rewired the live `/conversation` handler to obtain `ProviderRuntime` and `ToolCatalog` only from `request.app.state.runtime`; no provider name, SDK response, global client, Gemini bridge, or private tool map participates in the routed path.
- Preserved the exact seven response fields, nonempty HTTP-200 fallback, one provider session clear, one normalized persistence exchange with `update_profile=True` and configured timeout, and one degraded background persistence attempt.
- Added adversarial route evidence for all ten `ProviderErrorCode` values, malformed success, ASGI cancellation, neutral tools, redaction, persistence degradation, and legacy local/no-auth compatibility.
- Updated the bounded subprocess probe to inject a real typed `ProviderRuntime` around an offline fake without entering application lifespan, opening network connections, or touching repository data roots.

## Task Commits

Each task followed explicit RED and GREEN gates:

1. **Task 02-09-01 RED: provider-neutral analysis contract** - `311fc78`
2. **Task 02-09-01 GREEN: typed analysis transport and route injection** - `2b0c25e`
3. **Task 02-09-02 RED: real-route provider compatibility matrix** - `4ee862b`
4. **Task 02-09-02 GREEN: runtime-owned route, neutral tools, and safe fallback** - `f82f9cc`

## Files Created/Modified

- `aura_backend/conversation/__init__.py` - Stable exports for analysis DTOs and provider-neutral functions.
- `aura_backend/conversation/analysis.py` - Existing prompts, mappings, parsing, defaults, and typed provider transport.
- `aura_backend/main.py` - Runtime-owned tool catalog construction, live conversation orchestration, safe persistence, fallback, cancellation, and logging behavior.
- `tests/conversation/test_analysis_transport.py` - Typed request, parser/default, redaction, and cancellation tests for all analyses.
- `tests/api/test_provider_compatibility.py` - Success, all typed failures, invalid result, cancellation, persistence, tool, schema, and source-isolation route tests.
- `tests/support/main_subprocess_probe.py` - Typed runtime injection for the preserved Phase 1 subprocess contracts.

## Decisions Made

- Analysis failures remain non-fatal and return the exact legacy default/`None` behavior; prompt-quality and psychological-validity changes remain Phase 4 work.
- A successful primary provider result is the only point after which Aura records an active session or attempts persistence. Provider failure and malformed success therefore cannot create storage writes.
- Actual `asyncio.CancelledError` is never converted to the compatibility fallback and removes any local session marker before leaving the ASGI task.
- Safe diagnostic stages and normalized provider codes replace raw exceptions and response/thought previews. Provider source causes remain chained below the boundary but are neither serialized nor logged.

## Verification

- Analysis transport: **7 passed**.
- Provider route plus Phase 1 companion, persistence, and local boundary: **32 passed**.
- Complete deterministic Python suite: **344 passed**.
- Ruff on all six owned Python artifacts: **passed**.
- Python bytecode compilation on all six owned Python artifacts: **passed**.
- Frontend TypeScript check and Vite production build: **passed**.
- Repository whitespace check: **passed**.
- Tests used no live model, network, credentials, package installation, dependency manifest, lockfile, database, backup, or storage mutation.

## TDD Gate Compliance

- Task 1 RED failed with seven import errors because the provider-neutral conversation package did not exist. GREEN added the typed service and all seven behavior tests passed.
- Task 2 RED failed all fifteen cases because the routed handler still inspected the legacy global provider and bridge. GREEN moved the handler to `app.state.runtime`, after which all fifteen new route cases and all seventeen preserved compatibility cases passed.
- Git history contains each `test(02-09)` RED commit before its corresponding `feat(02-09)` GREEN commit.

## Deviations from Plan

None - the plan executed as specified. The neutral catalog startup wrapper also closes already-started legacy resources if catalog construction fails, which is required to preserve the existing partial-start unwind contract.

## Issues Encountered

- The GSD JavaScript helper remains unusable because its installed runtime cannot resolve `../../../package.json`; direct Git and verification commands were used instead.
- The bounded Phase 1 probe originally injected the deprecated mutable provider global. It was updated to inject the typed application/runtime seam while retaining its no-lifespan and no-production-service guarantees.
- The unregistered `_legacy_process_conversation` implementation remains as dead transitional code inside the broader `main.py` monolith. It has no route decorator and cannot participate in the live call path; later monolith cleanup can remove it without mixing that mechanical deletion into this contract change.

## Known Stubs

None in the routed implementation. Empty lists and `None` values in test fakes are deliberate recorder/unavailable states. The unregistered legacy function noted above is unreachable compatibility debris, not an active fallback or unwired route.

## Threat Flags

None. This plan implements the registered browser-to-runtime and provider-failure-to-public-response mitigations without adding an endpoint, authentication surface, schema, dependency, externally reachable service, or data migration.

## User Setup Required

None. Aura remains private, loopback-first, sign-in-free, and deterministically testable without Ollama or cloud access.

## Next Phase Readiness

- Health and startup plans can now measure/report the selected provider runtime without depending on legacy conversation globals.
- Phase 3 persistence work inherits a stable exchange contract; Phase 4 can improve analysis quality without reopening provider transport.
- No blocker remains for Plan 02-10.

## Self-Check: PASSED

- All six owned implementation/test artifacts and this summary exist on disk.
- All four RED/GREEN task commits exist in Git history in the required order.
- Frontmatter contains `status: complete` and all three requirement IDs copied from the plan.
- Focused, complete deterministic, lint, compile, TypeScript, build, whitespace, no-network, and data-root-preservation gates passed after the final implementation.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
