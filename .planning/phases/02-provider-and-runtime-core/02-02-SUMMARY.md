---
phase: 02-provider-and-runtime-core
plan: 02
subsystem: provider-runtime
tags: [python, asyncio, streaming, cancellation, deterministic-fakes, redaction]

requires:
  - phase: 02-provider-and-runtime-core
    plan: 01
    provides: Immutable provider request/result/event contracts and normalized failures
provides:
  - Event-controlled offline provider fake with independently gated first delta and completion
  - Deadline-owned ProviderRuntime with bounded in-flight operation ownership
  - Fail-closed stream terminal validation, cancellation, session clearing, and shutdown
affects: [02-04, 02-05, 02-06, 02-07, provider-adapters, application-runtime]

tech-stack:
  added: []
  patterns:
    - Internal producer tasks make active streams cancellable while consumers are between reads
    - Adapter completion is withheld until iterator exhaustion proves it is the final event
    - Runtime and fake diagnostics retain only safe codes and counts

key-files:
  created:
    - aura_backend/providers/runtime.py
    - tests/providers/fakes.py
    - tests/providers/test_fake.py
    - tests/providers/test_streaming.py
  modified: []

key-decisions:
  - "Use one registered producer task per stream so clear-session and shutdown can cancel active provider work independently of consumer scheduling."
  - "Withhold Completed until adapter exhaustion proves there are no late events; malformed terminal ordering can never escape as success."
  - "Guarantee local task, iterator, provider-client, and registry cleanup only; upstream compute or billing cancellation remains explicitly unknown."

patterns-established:
  - "Event-gated incrementality: the first delta and completion require distinct externally controlled events."
  - "Cancellation truth: cleanup runs, the registry empties, and CancelledError is re-raised without Completed or fallback."
  - "Safe evidence: partial event counts and normalized terminal codes are retained without prompt or response content."

requirements-completed: [TEST-03, AI-02, AI-03]

duration: 11min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 02: Deterministic Provider Runtime and Fakes Summary

**Event-controlled offline providers and a fail-closed async runtime now prove first-delta delivery, absolute deadlines, local cancellation, truthful terminal states, and idempotent shutdown without a model or network service**

## Performance

- **Duration:** 11 min
- **Started:** 2026-08-20T08:16:51Z
- **Completed:** 2026-08-20T08:27:44Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added a reusable `ScriptedProvider` whose first delta and completion are released by separate `asyncio.Event` gates, proving the response is not replayed from a pre-buffered result.
- Covered normal, incremental, malformed, timeout, missing-model, unavailable, authentication, resource-limit, midstream-failure, and cancellation outcomes offline with distinct typed evidence and no false `Completed`.
- Added `ProviderRuntime` with one absolute `asyncio.timeout()` per operation, a bounded in-flight task registry, safe health/session delegation, fail-closed stream ordering, and idempotent close.
- Made caller cancellation, session clear, and shutdown cancel and await local provider work, close async iterators, empty the registry, and propagate `CancelledError` without fallback or completed success.
- Recorded only counts and normalized codes; prompts, deltas, results, raw exceptions, session keys, and correlation keys are absent from public snapshots and fake recorders.

## Task Commits

TDD gates were committed atomically in RED/GREEN order, followed by a regression RED/fix pair:

1. **Task 1 RED: failing event-controlled fake contract** - `90f24eb` (test)
2. **Task 1 GREEN: deterministic scripted provider** - `cc68ea6` (feat)
3. **Task 2 RED: failing runtime ownership contract** - `380ff35` (test)
4. **Task 2 GREEN: deadline/cancellation/terminal runtime** - `1354cf3` (feat)
5. **Regression RED: synchronous stream-start cleanup** - `a206c3a` (test)
6. **Regression GREEN: iterator construction inside owned cleanup** - `b7370c9` (fix)

## Files Created/Modified

- `aura_backend/providers/runtime.py` - Provider operation ownership, deadlines, safe metrics, stream state validation, cancellation, session clearing, health delegation, and shutdown.
- `tests/providers/fakes.py` - Event-controlled scripted provider and content-free call recorder implementing the production protocol.
- `tests/providers/test_fake.py` - Required offline fake outcome matrix, true-incrementality proof, cancellation cleanup, invalid-script, and redaction cases.
- `tests/providers/test_streaming.py` - Runtime deadline, partial failure, malformed ordering, cancellation, clear-session, shutdown, registry-bound, health, and close-idempotence cases.

## Decisions Made

- A stream is drained by an internal registered producer task. This gives Aura a stable local cancellation handle even when the outer consumer is paused between `anext()` calls.
- `Completed` is retained internally until the adapter iterator ends. Any later delta, second terminal, missing terminal, typed failure, timeout, raw exception, or cancellation closes without yielding completed success.
- Session and correlation keys are internal registry selectors only. Public runtime snapshots expose registry size, counts, terminal code, partial event count, and the literal upstream-cancellation status `unknown`.
- Runtime policy contains no retry or fallback loop. Provider failures remain failures, while direct cancellation is recorded safely and re-raised as `asyncio.CancelledError`.

## Verification Evidence

- `uv run --locked --no-sync python -m pytest -q tests/providers/test_fake.py` - **12 passed**.
- `uv run --locked --no-sync python -m pytest -q tests/providers/test_streaming.py` - **11 passed**.
- `uv run --locked --no-sync python -m pytest -q tests/providers/test_contract.py` - **27 passed**.
- `uv run --locked --no-sync python -m pytest -q tests/providers` - **50 passed**.
- `ruff check aura_backend/providers/runtime.py tests/providers/fakes.py tests/providers/test_fake.py tests/providers/test_streaming.py` - **passed**.
- `python -m py_compile` for all four owned Python files and `git diff --check` - **passed**.

## TDD Gate Compliance

- Task 1 RED failed at collection because `tests.providers.fakes` did not exist; GREEN added only the scripted fake and made all 12 cases pass.
- Task 2 RED failed at collection because `aura_backend.providers.runtime` did not exist; GREEN added the runtime and made all 10 original cases pass.
- Review then produced a focused RED failure for synchronous iterator-construction errors, followed by the fix; the runtime lane now has 11 passing cases.
- Git history contains each required `test(02-02)` commit before its corresponding `feat(02-02)` or `fix(02-02)` commit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Closed synchronous stream-start registry leak**
- **Found during:** Task 2 post-GREEN review
- **Issue:** A provider that raised while constructing its async iterator could bypass the producer cleanup boundary, leaving the operation registered and the consumer waiting without a typed terminal failure.
- **Fix:** Added a failing adversarial regression, moved iterator creation inside the runtime-owned `try/finally`, normalized the raw startup error as `malformed_response`, and retained no source text.
- **Files modified:** `tests/providers/test_streaming.py`, `aura_backend/providers/runtime.py`
- **Verification:** Focused regression passed, followed by all 11 runtime cases and all 50 provider cases.
- **Committed in:** `a206c3a` (RED), `b7370c9` (GREEN)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug)
**Impact on plan:** The fix is directly required by the plan's failure cleanup and bounded-registry guarantees; no scope, dependency, service, data, or public API expansion occurred.

## Issues Encountered

- The broad repository offline command was attempted, but the execution harness ended after partial progress without returning a final exit status. It is therefore not claimed as passing evidence. The exact task lanes, inherited provider contract, and complete relevant provider directory all passed independently.
- The GSD JavaScript helper remained unavailable per the execution handoff. Direct Git/status/log and locked uv commands were used, while the orchestrator's existing `.planning/STATE.md` edit and unrelated `.trunk/` remained untouched.

## Known Stubs

None. Optional `None` values represent explicit absence in safe runtime state; empty test lists and the empty initial in-flight registry are assertions/setup rather than application placeholders.

## Threat Flags

None. The only new security-relevant surfaces are the provider-iterator and caller/shutdown boundaries already registered in Plan 02-02's threat model. No endpoint, authentication path, filesystem path, schema, package, network transport, model, service, or data access was added.

## User Setup Required

None - no package, credential, running model, network service, data access, manifest, or lock change is required.

## Next Phase Readiness

- Ollama/OpenRouter and Gemini adapters can reuse the runtime and scripted fake to prove their translation and cancellation behavior without changing orchestration.
- Application lifecycle work can close one `ProviderRuntime` and rely on it to cancel/await local work and close the selected provider exactly once.
- Upstream cancellation remains honestly unproven and must not be upgraded to a remote compute or billing guarantee by later adapter/live-test plans.

## Self-Check: PASSED

- All four owned implementation/test artifacts and this summary exist on disk.
- All six RED/GREEN/regression commits exist in Git history in the documented order.
- Frontmatter contains `status: complete` and all three requirement IDs from the plan.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
