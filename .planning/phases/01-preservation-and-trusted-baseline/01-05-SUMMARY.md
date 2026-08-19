---
phase: 01-preservation-and-trusted-baseline
plan: 05
subsystem: api-testing
tags: [fastapi, starlette, cors, localhost, subprocess, pytest]

requires: []
provides:
  - Bounded child-process probe for the real Aura FastAPI composition root
  - HTTP-level loopback, explicit-origin, strict-JSON, and no-sign-in characterization
  - Fail-closed evidence contract for timeout, crash, malformed output, partial output, and data-root writes
affects: [01-06, 01-07, phase-04-architecture, api-security, deterministic-testing]

tech-stack:
  added: []
  patterns:
    - Child-only composition-root import with preinstalled fake stateful dependencies
    - TestClient requests without lifespan entry or a listening network socket
    - JSON-only parent-child evidence with hard timeout and repository data-root snapshots

key-files:
  created:
    - tests/support/main_subprocess_probe.py
    - tests/api/test_local_boundary.py
  modified: []

key-decisions:
  - "Characterize FastAPI 0.136.1's observed 422 response for missing or non-JSON Content-Type; the security gate is that request parsing stops before provider or persistence behavior."
  - "Use TestClient without its context-manager form so the real ASGI app and middleware execute while production lifespan remains disabled."
  - "Keep normal local access credential-free; containment is loopback, explicit origins, credentials-off CORS, and strict JSON parsing rather than sign-in."

patterns-established:
  - "Quarantined ASGI probe: fake stateful imports first, import aura_backend.main only in a disposable bounded child, and emit one normalized JSON result."
  - "Fail-closed characterization: timeout, nonzero exit, malformed JSON, incomplete evidence, or a changed repository data root raises ProbeFailure."

requirements-completed: [PRES-03, LOCAL-01, LOCAL-02, LOCAL-04]

duration: 12min
completed: 2026-08-19
status: complete
---

# Phase 1 Plan 05: Localhost HTTP Boundary Characterization Summary

**A quarantined real-app ASGI probe proves loopback defaults, explicit credential-free CORS, malicious-origin non-JSON rejection, and no-sign-in local JSON access without starting production services**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-19T10:11:04Z
- **Completed:** 2026-08-19T10:23:23Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added a reusable parent/child probe that imports `aura_backend.main` only inside a temporary-cwd child with a sanitized environment and a hard timeout.
- Replaced Chroma, filesystem persistence, MCP, provider, embedding, archival, autonomic, and backup/protection collaborators before the production composition root imports; the selected requests never enter lifespan or call an external service.
- Pinned HTTP-level behavior for allowed and denied CORS preflights, wildcard-origin rejection, malicious-origin missing/`text/plain` Content-Type requests, and a normal allowed JSON conversation.
- Proved the credential-free JSON request reaches exactly one fake provider and one fake persistence call, while both non-JSON requests stop with 422 before either collaborator executes.
- Made child timeouts, crashes, malformed output, partial output, and repository data-root changes explicit non-pass results.

## Task Commits

TDD slices were committed at their RED and GREEN gates:

1. **Task 1 RED: failing quarantined probe contract** - `746fd88` (test)
2. **Task 1 GREEN: bounded production-app subprocess probe** - `cc76988` (feat)
3. **Task 2 RED: failing localhost HTTP boundary assertions** - `2a0a04a` (test)
4. **Task 2 GREEN: loopback/CORS/JSON/no-sign-in characterization** - `e2193f8` (feat)

## Files Created/Modified

- `tests/support/main_subprocess_probe.py` - Runs scenario-driven TestClient requests against the real app in a bounded child, installs deterministic collaborators, normalizes volatile values, and validates complete JSON evidence.
- `tests/api/test_local_boundary.py` - Pins loopback configuration and the real middleware/request contracts for browser origins, JSON parsing, and credential-free local use.

## Decisions Made

- Captured the actual FastAPI 0.136.1 result for missing and `text/plain` Content-Type as **422** with a `model_attributes_type` body error. Strict mode leaves those bodies unparsed; the security assertion is that provider and persistence call counts remain zero.
- Used Starlette/FastAPI `TestClient` as a plain object rather than a context manager. This executes the ASGI middleware and routes but does not trigger Aura's production lifespan.
- Sent the simple non-JSON requests with the explicitly untrusted origin. CORS alone does not prevent a browser from sending a simple request, so the parsing rejection is the behavior that prevents business execution.
- Sent no Authorization header or cookie in the valid local request and kept `allow_credentials=False`; no account, token, login, or session-auth state was introduced.

## Verification Evidence

- `uv run python -m pytest -q tests/api/test_local_boundary.py -k 'probe'` - **5 passed**.
- `uv run python -m pytest -q tests/api/test_local_boundary.py` - **12 passed in 12.22s**.
- `uv run python -m pytest -q` - **43 passed in 12.63s**; no live service, Ollama model, MCP process, or listening socket required.
- `uv run python -m py_compile tests/support/main_subprocess_probe.py tests/api/test_local_boundary.py` - passed.
- `git diff --check` - passed.
- Data-root metadata snapshots before and after every passing child matched; no database, backup, archive, or stored user data changed.

## TDD Gate Compliance

- Task 1 RED `746fd88` failed because `tests.support.main_subprocess_probe` did not yet exist; GREEN `cc76988` added the minimum bounded child contract and all five probe tests passed.
- Task 2 RED `2a0a04a` exposed plain-text preflight bodies, missing per-request lifespan evidence, and the actual 422 Content-Type behavior; GREEN `e2193f8` made the minimal harness adjustments and all twelve boundary tests passed.
- RED commits precede their corresponding GREEN commits; no refactor-only commit was necessary.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The first GREEN run identified that `FastAPI.__module__` names the framework class module rather than the module owning Aura's app instance. The probe now records the imported module's `__name__`, producing the required `aura_backend.main` evidence.
- CORS preflight responses are plain text, not JSON. The response sanitizer now parses JSON only when the response Content-Type declares JSON and otherwise records bounded synthetic text.
- Context7 was unavailable both as an MCP connector and CLI. Current official FastAPI and Starlette documentation was checked directly, then local FastAPI 0.136.1 behavior was treated as authoritative for exact status/shape assertions.
- The GSD JavaScript helper was unavailable per the execution handoff. Direct Git/status/log and pytest checks were used without changing scope.
- Wave 1 work shares the main tree. Only Plan 01-05-owned files were staged; the orchestrator's `.planning/STATE.md` edit and unrelated `.trunk/` were preserved.

## Known Stubs

None. The `None` assignments and empty synthetic call lists in the probe deliberately disable production globals and record fake call activity; they do not flow to product UI or represent unwired production data.

## User Setup Required

None - the deterministic boundary requires no account, credential, running model, Ollama process, MCP service, or new dependency.

## Next Phase Readiness

- Plans 01-06 and 01-07 can reuse the bounded child pattern for filesystem and companion behavior without importing the production app into pytest or entering lifespan.
- Later structural work can use the pinned request contract to detect regressions in loopback, origin, strict-JSON, and no-sign-in behavior.
- No storage cleanup, migration, or history rewrite occurred; the preservation gate remains intact.

## Self-Check: PASSED

- Both implementation artifacts and this summary exist on disk.
- All four RED/GREEN task commits are present in Git history in the required order.
- Required frontmatter contains `status: complete` and all four completed requirement IDs.
- The focused and complete deterministic verification commands passed after the final implementation commit.

---
*Phase: 01-preservation-and-trusted-baseline*
*Completed: 2026-08-19*
