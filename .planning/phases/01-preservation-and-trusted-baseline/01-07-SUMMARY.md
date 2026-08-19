---
phase: 01-preservation-and-trusted-baseline
plan: 07
subsystem: api-testing
tags: [fastapi, pytest, subprocess, persistence, provider-fakes, characterization]

requires:
  - phase: 01-preservation-and-trusted-baseline
    plan: 05
    provides: Bounded child-process probe for the real Aura FastAPI app
provides:
  - Normalized route-to-persistence exchange and call-shape characterization
  - Stable user-visible companion response schema characterization
  - Deterministic provider error, empty-content, and persistence-failure evidence
affects: [phase-02-provider-consolidation, phase-04-architecture, persistence, companion-api]

tech-stack:
  added: []
  patterns:
    - Recording fake collaborators behind a real request to the production ASGI route
    - Boolean, count, type, and normalized-token evidence instead of volatile snapshots
    - Child-process socket rejection for deterministic offline characterization

key-files:
  created:
    - tests/characterization/test_persistence_contract.py
    - tests/characterization/test_companion_contract.py
  modified:
    - tests/support/main_subprocess_probe.py

key-decisions:
  - "Record persistence exchange shape and structured results through a fake service without constructing production storage clients."
  - "Pin the observed HTTP 200 fallback for provider error and empty content; changing it to non-2xx is deferred because this plan forbids production behavior changes."
  - "Reject socket connections inside the child so accidental Ollama, MCP, Chroma, or other service access fails closed."

patterns-established:
  - "Sanitized call evidence: retain field linkage, flags, method names, counts, and stable types while excluding raw prompts, provider prose, hidden reasoning, UUIDs, and timestamps."
  - "Observed-contract priority: characterization records current legacy behavior even when it contradicts an aspirational acceptance statement."

requirements-completed: [PRES-03]

duration: 8min
completed: 2026-08-19
status: complete
---

# Phase 1 Plan 07: Companion and Persistence Characterization Summary

**Deterministic real-route probes now preserve Aura's persistence exchange, visible companion schema, and degraded failure behavior without model, network, or storage dependencies**

## Performance

- **Duration:** 8 min task execution window
- **Started:** 2026-08-19T11:45:11Z
- **Completed:** 2026-08-19T11:53:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Pinned the exact route-to-persistence call shape: one user/Aura exchange, matching normalized session linkage, expected senders/user IDs, `update_profile=True`, and the configured `4.25` second timeout.
- Distinguished structured immediate persistence success from structured failure. The failure path preserves the visible provider answer, performs one fake background retry, and makes no filesystem or production-data write.
- Captured the stable seven-field `ConversationResponse` schema and JSON-facing types while excluding exact provider prose, raw prompts, timestamps, UUID values, and hidden reasoning.
- Proved the provider receives one user message and a nonempty system instruction using booleans and counts only.
- Made any socket connection in the child an explicit failure, in addition to replacing all stateful production collaborators before importing `aura_backend.main`.

## Task Commits

TDD slices were committed at their RED, GREEN, and final refactor gates:

1. **Task 1 RED: failing persistence contract** - `ce2bf2f` (test)
2. **Task 1 GREEN: recording persistence fake and normalized evidence** - `d244b98` (feat)
3. **Task 2 RED: failing companion response and provider-failure contract** - `414c60f` (test)
4. **Task 2 GREEN: deterministic companion/provider scenarios** - `ff5fa8f` (feat)
5. **Task 2 REFACTOR: fail-closed network boundary** - `9040509` (refactor)

## Files Created/Modified

- `tests/characterization/test_persistence_contract.py` - Asserts exchange linkage, immediate-persistence options/results, bounded degraded behavior, and unchanged production data roots.
- `tests/characterization/test_companion_contract.py` - Asserts stable response keys/types, normalized emotion/cognition/session evidence, sanitized provider input evidence, and current fallback behavior.
- `tests/support/main_subprocess_probe.py` - Adds scenario-aware recording fakes, sanitized evidence builders, zero emergency retries, deterministic timeout configuration, and a child-only network prohibition.

## Decisions Made

- Used the existing quarantined real-app subprocess instead of importing `aura_backend.main` in pytest or reimplementing route logic.
- Returned only stable call shape, booleans, counts, normalized tokens, and type names for the new scenarios. Raw provider/system content and full response bodies stay inside the disposable child.
- Treated current production behavior as authoritative for characterization: the route's broad exception handler converts provider error and empty content into a nonempty HTTP 200 fallback response and clears the provider session.

## Verification Evidence

- `uv run python -m pytest -q tests/characterization/test_persistence_contract.py` - **2 passed in 4.45s**.
- `uv run python -m pytest -q tests/characterization/test_companion_contract.py` - **3 passed in 5.13s**.
- `uv run python -m pytest -q tests/api/test_local_boundary.py` - **12 passed in 12.26s**.
- `uv run python -m pytest -q` - **121 passed in 31.08s** after the final implementation commit.
- `uv run python -m py_compile tests/support/main_subprocess_probe.py tests/characterization/test_persistence_contract.py tests/characterization/test_companion_contract.py` - passed.
- `git diff --check` - passed.
- Every passing probe independently verifies that known repository data-root size/mtime metadata is unchanged.

## TDD Gate Compliance

- Task 1 RED failed only because `persistence_success` and `persistence_failure` were absent; GREEN added the minimum recording service and both focused tests passed.
- Task 2 RED failed only because `companion_success`, `provider_error`, and `provider_empty` were absent; GREEN added deterministic fake-provider scenarios and all focused tests passed.
- The final refactor retained GREEN while adding a fail-closed socket boundary. RED commits precede their corresponding GREEN commits.

## Deviations from Plan

### Observed Legacy Behavior Replaced an Aspirational Assertion

- **Found during:** Task 2 source inspection and focused characterization.
- **Plan statement:** Provider error and empty-content cases should assert non-2xx statuses.
- **Observed behavior:** `process_conversation` catches both conditions in its broad exception handler and returns a structured, nonempty fallback with HTTP 200; the provider's error text is not exposed.
- **Resolution:** The tests pin the observed 200 fallback and distinguish it from probe/infrastructure failure. No production route behavior was changed because D-05 explicitly restricts this plan to characterization.
- **Impact:** PRES-03 is satisfied truthfully, but changing these cases to non-2xx remains a future API behavior decision and cannot be claimed complete here.

No other deviations occurred.

## Issues Encountered

- The plan's non-2xx acceptance statement contradicted the current route implementation. Preserving actual behavior took precedence over inventing a passing response or modifying production orchestration.
- The GSD JavaScript helper was unavailable per the execution handoff. Direct Git, status, log, and pytest commands were used.
- Work shared the main tree. Only Plan 01-07-owned files and this summary were staged; the orchestrator's `.planning/STATE.md` edit and unrelated `.trunk/` remained untouched.

## Known Stubs

None. Empty provider content, synthetic failure lists, disabled globals, and empty call-recording lists are deliberate test states. They do not flow to production UI or represent unwired production data.

## User Setup Required

None - these tests require no credentials, Ollama model, network, MCP process, GPU, Chroma instance, production data, or new dependency.

## Next Phase Readiness

- Later provider and route work can detect changes to the seven-field response schema, message/system-instruction wiring, hidden-reasoning exclusion, and failure fallback semantics.
- Later persistence refactoring can detect changes to sender/user/session linkage, immediate method selection, update-profile behavior, timeout propagation, and degraded background retry behavior.
- The HTTP 200 fallback for provider failures is explicitly documented as legacy behavior requiring a future product/API decision rather than a successful error-status contract.

## Self-Check: PASSED

- All three implementation artifacts and this summary exist on disk.
- All five RED/GREEN/refactor commits are present in Git history in the required order.
- Required frontmatter contains `status: complete` and requirement `PRES-03`.
- Focused, boundary, compile, diff, and complete deterministic verification passed after the final implementation commit.

---
*Phase: 01-preservation-and-trusted-baseline*
*Completed: 2026-08-19*
