---
phase: 02-provider-and-runtime-core
plan: 04
subsystem: provider-adapters
tags: [python, openai-compatible, ollama, openrouter, streaming, cancellation, redaction]

requires:
  - phase: 02-provider-and-runtime-core
    plan: 02
    provides: Deadline-owned provider runtime, typed stream events, and deterministic fakes
  - phase: 02-provider-and-runtime-core
    plan: 03
    provides: Collision-safe neutral tool catalog and bounded executor
provides:
  - One async OpenAI-compatible transport for Ollama and OpenRouter
  - Complete local Ollama policy with bounded model-list readiness
  - Explicit OpenRouter cloud policy with pre-stream and midstream error detection
affects: [02-06, 02-07, 02-09, provider-factory, application-runtime, conversation-orchestration]

tech-stack:
  added: []
  patterns:
    - One zero-retry transport owns compatible request, tool, stream, failure, and close behavior
    - Provider policies supply endpoint, credential, header, and readiness semantics only
    - Partial streams retain safe event counts but can never emit Completed after failure

key-files:
  created:
    - aura_backend/providers/openai_compatible.py
    - tests/providers/test_openai_compatible.py
    - tests/providers/test_ollama.py
    - tests/providers/test_openrouter.py
  modified:
    - aura_backend/providers/ollama.py
    - aura_backend/providers/openrouter.py

key-decisions:
  - "Use the locked AsyncOpenAI client for both Ollama and OpenRouter with max_retries=0 and named finite HTTPX timeout fields."
  - "Treat adapters as stateless and route tools only through the neutral ToolExecutor; temporary legacy method signatures remain compatibility shims."
  - "Use Ollama model listing for readiness and report selected-model absence separately from service unavailability without generating or pulling a model."
  - "Detect OpenRouter top-level and Chat Completions embedded error envelopes; any error after text becomes stream_interrupted with count-only evidence."

patterns-established:
  - "Compatible transport: SDK objects terminate inside openai_compatible.py and only frozen provider DTOs escape."
  - "Streaming truth: upstream deltas are yielded immediately, response streams close in finally, and only a validated stop emits Completed."
  - "Cloud privacy: credentials, headers, URLs, prompts, response text, source exceptions, and tracebacks are absent from public diagnostics and default logs."

requirements-completed: [TEST-03, AI-01, AI-02, AI-03]

duration: 21min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 04: Shared OpenAI-Compatible, Ollama, and OpenRouter Providers Summary

**One zero-retry async transport now gives local Ollama and explicit OpenRouter real incremental streaming, bounded tools and readiness, typed safe failures, and deterministic cleanup without contacting a model in tests**

## Performance

- **Duration:** 21 min
- **Started:** 2026-08-20T17:56:14Z
- **Completed:** 2026-08-20T18:16:58Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Centralized compatible message/tool conversion, non-stream generation, streamed delta translation, indexed tool-fragment assembly, bounded tool execution, token usage normalization, SDK exception mapping, stream closure, and client closure.
- Constructed the locked OpenAI client with exactly zero retries and explicit connect/read/write/pool timeouts; no new package, retry loop, raw SDK result, or error-as-content path was added.
- Replaced Ollama's duplicated buffered adapter with a thin local policy over the shared transport and a bounded `/v1/models` readiness check that distinguishes ready, missing model, unavailable service, and malformed metadata.
- Replaced OpenRouter's duplicated buffered adapter and traceback logging with explicit HTTPS endpoint/auth/header policy plus documented top-level and embedded error-envelope handling.
- Proved partial streams never become completed answers, cancellation closes local streams, tool calls execute once after complete valid JSON, and process-control exceptions are not normalized.

## Task Commits

TDD gates were committed in RED/GREEN order for all three tasks, followed by one reviewed regression fix:

1. **Task 1 RED: failing shared compatible transport contract** - `bb1f57a` (test)
2. **Task 1 GREEN: shared request/tool/stream/failure transport** - `89bfa03` (feat)
3. **Task 2 RED: failing Ollama endpoint/readiness/stream contract** - `f47d9b7` (test)
4. **Task 2 GREEN: complete local Ollama policy** - `48780e8` (feat)
5. **Task 3 RED: failing OpenRouter config/envelope/privacy contract** - `3b03d23` (test)
6. **Task 3 GREEN: explicit OpenRouter error policy** - `8c0742c` (feat)
7. **Review fix: process-control exception propagation** - `cdb6629` (fix)

## Files Created/Modified

- `aura_backend/providers/openai_compatible.py` - Shared compatible client construction, translation, tools, streaming, typed errors, legacy transition shims, and close ownership.
- `aura_backend/providers/ollama.py` - Local `/v1` endpoint policy and bounded model-list readiness only.
- `aura_backend/providers/openrouter.py` - Explicit cloud configuration, safe headers, and documented envelope detection only.
- `tests/providers/test_openai_compatible.py` - Client construction, normalized generation, exception matrix, malformed/resource/tool/stream/cancellation/redaction tests.
- `tests/providers/test_ollama.py` - Offline endpoint, readiness, missing-model, timeout, malformed, resource, partial-stream, and cancellation tests.
- `tests/providers/test_openrouter.py` - Offline credential/header, pre-stream, embedded, midstream, redaction, and normal-result tests.

## Decisions Made

- `max_retries` must remain zero at the adapter boundary even though settings parsing retains a transitional numeric field; any nonzero value fails configuration instead of multiplying runtime retry/deadline policy.
- Ollama accepts only its documented service root or `/v1` path and normalizes either to the loopback-compatible `/v1` endpoint. Health lists metadata only and never sends a prompt or downloads a model.
- OpenRouter remains impossible to construct without explicit selection and credential. Its stable HTTPS `/api/v1` path and identifying headers are client-only configuration and never enter diagnostics.
- Local cancellation guarantees only Aura iterator/client cleanup. No remote compute or billing cancellation claim is made.

## Verification Evidence

- `uv run --locked --no-sync python -m pytest -q tests/providers/test_openai_compatible.py tests/providers/test_ollama.py tests/providers/test_openrouter.py tests/providers/test_streaming.py tests/characterization/test_companion_contract.py` - **44 passed in 5.31s**.
- `uv run --locked --no-sync python -m pytest -q tests -m 'not live and not ollama and not gpu'` - **254 passed in 33.54s**.
- `uv run --locked --no-sync ruff check` on all six owned implementation/test files - **passed**.
- `python -m py_compile` on the owned provider/test modules and `git diff --check` - **passed**.
- Deterministic tests used injected clients/streams; no Ollama, OpenRouter, socket, credential, or live model was required.

## TDD Gate Compliance

- Task 1 RED failed because `aura_backend.providers.openai_compatible` did not exist; GREEN made all 15 initial transport cases pass.
- Task 2 RED produced seven constructor-contract failures against the legacy Ollama adapter; GREEN replaced its duplicate loops and made the expanded eight-case lane pass.
- Task 3 RED produced six constructor-contract failures against the legacy OpenRouter adapter; GREEN replaced its duplicate loops and made all six cases pass.
- Git history contains each required `test(02-04)` commit before its corresponding `feat(02-04)` commit. No standalone refactor commit was needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restricted exception normalization to ordinary provider failures**
- **Found during:** Post-Task 3 threat and cancellation review
- **Issue:** The shared adapter explicitly re-raised `CancelledError` but its final normalization clauses still caught other process-control `BaseException` values.
- **Fix:** Narrowed both clauses to `Exception` and added an adversarial control-flow regression proving a custom `BaseException` propagates unchanged.
- **Files modified:** `aura_backend/providers/openai_compatible.py`, `tests/providers/test_openai_compatible.py`
- **Verification:** Focused 44-test lane, Ruff, compile, and 254-test deterministic suite all passed.
- **Committed in:** `cdb6629`

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug)
**Impact on plan:** The fix tightened the plan's cancellation/control-flow boundary without changing architecture, public API, dependencies, data, or scope.

## Issues Encountered

- The GSD JavaScript helper remained unavailable because its installed runtime could not resolve `../../../package.json`. Direct Git, locked uv, pytest, Ruff, compile, and diff commands were used instead.
- Current official Ollama, OpenRouter, and OpenAI Python documentation was rechecked before implementation. It confirmed `/v1` compatibility/model listing, documented OpenRouter in-band stream errors, and explicit async client close/retry behavior.

## Known Stubs

None. Optional `None` values represent explicit absence in typed configuration/SDK fields, and empty lists/dictionaries in tests are initial recorder or malformed-input fixtures rather than application placeholders.

## Threat Flags

None. The compatible HTTP and untrusted provider-chunk boundaries are the exact surfaces registered in Plan 02-04. They are covered by finite timeouts, zero retries, bounded tool turns, validated terminal ordering, typed redacted failures, and `finally` cleanup. No endpoint, authentication system, filesystem path, schema, package, data access, or new external service was added.

## User Setup Required

- None for the default local Ollama path beyond having the explicitly selected model installed; deterministic tests require neither Ollama nor a model.
- OpenRouter remains optional. Only users who explicitly select it must provide `OPENROUTER_API_KEY`; no credential is needed or requested for local Ollama use.

## Next Phase Readiness

- The factory/runtime plans can now construct one selected adapter without duplicating compatible request or stream logic.
- Conversation orchestration can consume normalized results/events and neutral tool execution without inspecting Ollama/OpenRouter SDK objects.
- Gemini remains the next provider-specific async adapter; public browser streaming and storage changes remain in their later owning phases.

## Self-Check: PASSED

- All six owned implementation/test artifacts and this summary exist on disk.
- All seven documented RED/GREEN/fix commits exist in Git history in the stated order.
- Frontmatter contains `status: complete` and all four requirement IDs copied from the plan.
- Focused provider/companion, full deterministic, Ruff, compile, and diff checks passed after the final code change.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
