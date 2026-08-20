---
phase: 02-provider-and-runtime-core
plan: 03
subsystem: provider-tools
tags: [python, json-schema, mcp, immutable-catalog, redaction, tdd]

requires:
  - phase: 02-provider-and-runtime-core
    plan: 01
    provides: Immutable ToolDefinition and typed ProviderFailure taxonomy
provides:
  - Collision-safe immutable provider-neutral tool catalog and registrations
  - Bounded schema-validating tool executor with typed content-free failures
  - Neutral MCP/internal enumeration and metadata-routed dispatch beside compatibility APIs
affects: [02-04, 02-05, 02-06, 02-09, provider-adapters, conversation-orchestration]

tech-stack:
  added: []
  patterns:
    - Draft-selected JSON Schema validation with local-only references
    - Frozen registrations plus immutable provider-name lookup
    - Typed timeout resource malformed and unavailable execution failures

key-files:
  created:
    - aura_backend/providers/tools.py
    - tests/providers/test_tools.py
  modified:
    - aura_backend/mcp_system.py

key-decisions:
  - "Normalize every provider tool name once at catalog construction and reject duplicate original names or post-normalization collisions."
  - "Treat malformed arguments/results, timeouts, output/argument bounds, and tool-turn exhaustion as typed ProviderFailure outcomes rather than successful strings."
  - "Keep legacy Gemini bridge/status entry points callable while new orchestration enumerates and dispatches only through neutral immutable registration metadata."

patterns-established:
  - "Provider-safe routing: adapters consume ToolCatalog.definitions and execution resolves back to immutable original name, source, and server metadata."
  - "Content-free diagnostics: ToolExecutionResult hides value from repr/str and executor failures never retain arguments, results, or source exception strings."
  - "Optional-tool truth: unavailable discovery yields an empty catalog; execution without an available registration raises typed unavailable."

requirements-completed: [TEST-03, AI-01]

duration: 16min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 03: Provider-Neutral Tool Boundary Summary

**Immutable collision-safe tool definitions now validate names, schemas, calls, deadlines, turns, and output bounds before neutral metadata routes internal or MCP execution without Gemini SDK types or bridge-private mappings**

## Performance

- **Duration:** 16 min
- **Started:** 2026-08-20T08:34:28Z
- **Completed:** 2026-08-20T08:50:09Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added frozen `ToolRegistration`, `ToolCatalog`, `ToolExecutionLimits`, and `ToolExecutionResult` values plus one `ToolExecutor` that owns provider-safe naming, schema/argument/result validation, deadlines, and resource bounds.
- Centralized OpenAI-compatible name normalization and fail-closed rejection for duplicate original names and collisions caused by sanitization or truncation.
- Validated schemas with the locked `jsonschema` runtime, requiring object inputs, valid meta-schemas, bounded schema size, and document-local references only.
- Parsed string or mapping arguments as complete JSON objects, enforced required/additional-property rules, and dispatched only immutable validated arguments.
- Returned bounded recursively immutable JSON results while representing malformed results, timeouts, unavailable sources, excess arguments/output, and excess tool turns only as typed `ProviderFailure` exceptions.
- Added `get_provider_tool_catalog()` and `get_provider_tool_executor()` to enumerate and route injected/current internal and MCP sources without using Google types or `_tool_mapping`.
- Preserved `initialize_mcp_system()`, `get_mcp_bridge()`, status/client accessors, existing tool listing, and shutdown behavior while retaining internal-only availability when optional MCP initialization fails.

## Task Commits

TDD gates were committed in RED/GREEN order for both tasks:

1. **Task 1 RED: failing neutral catalog/executor contract** - `27c2dbf` (test)
2. **Task 1 GREEN: collision-safe bounded tool boundary** - `e7f3018` (feat)
3. **Task 2 RED: failing neutral MCP/internal seam contract** - `0cb0c0c` (test)
4. **Task 2 GREEN: metadata-routed MCP/internal wiring** - `c18f742` (feat)

## Files Created/Modified

- `aura_backend/providers/tools.py` - Immutable catalog/registration/result contracts, shared name normalization, JSON Schema validation, and bounded executor.
- `aura_backend/mcp_system.py` - Neutral internal/MCP catalog enumeration and executor adapter alongside existing compatibility APIs.
- `tests/providers/test_tools.py` - Offline schema, collision, mutation, argument, result, bound, redaction, source-matrix, dispatch, and SDK-neutrality coverage.

## Decisions Made

- Used the common provider-safe name grammar (`A-Z`, `a-z`, digits, underscore, dash; maximum 64 characters), with deterministic replacement and truncation followed by mandatory collision rejection.
- Required each tool schema to describe an object. Legacy missing/empty MCP parameter definitions are converted to an explicit empty-object schema before the same strict validation path.
- Rejected non-local `$ref` values so catalog construction cannot turn untrusted tool schemas into network retrieval.
- Raised the Plan 02-01 `ProviderFailure` taxonomy for every execution non-success and allowed `asyncio.CancelledError` to propagate unchanged.
- Kept result content available only through the typed `.value` field needed by adapters; default `repr`/`str` expose only safe tool name and byte count.
- Used injected structural protocols for deterministic tests while defaulting production calls to the current MCP/internal instances owned by `mcp_system`.

## Verification Evidence

- `uv run --locked --no-sync python -m pytest -q tests/providers/test_tools.py tests/characterization/test_mcp_parameters.py tests/characterization/test_mcp_result_formatting.py` - **37 passed in 2.24s**.
- `uv run --locked --no-sync python -m pytest -q tests -m 'not live and not ollama and not gpu'` - **219 passed in 37.44s**.
- `uv run --locked --no-sync ruff check aura_backend/providers/tools.py aura_backend/mcp_system.py tests/providers/test_tools.py` - **passed**.
- `python -m py_compile` for all three owned Python files and `git diff --check` - **passed**.

## TDD Gate Compliance

- Task 1 RED failed at collection because `aura_backend.providers.tools` did not exist; its GREEN implementation made all 15 initial neutral catalog/executor tests pass.
- Task 2 RED retained those 15 passes while five new cases failed on the missing neutral `mcp_system` functions; its GREEN implementation made all 20 tool tests pass.
- Git history contains both required `test(02-03)` commits before their corresponding `feat(02-03)` commits.
- No refactor commit was needed after the GREEN gates; fresh Ruff, compile, exact, and full offline checks stayed green on the final implementation.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Context7 MCP and its CLI fallback were unavailable. The official `jsonschema` 4.24 documentation was consulted instead before using `validator_for()` and `check_schema()` against the locked installed version.
- The GSD JavaScript helper was unavailable per the execution handoff. Direct Git/status/log, locked uv, Ruff, pytest, compile, and diff checks were used without broadening scope.
- Work shared `main`. Only Plan 02-03-owned code/tests and this summary were staged; the orchestrator's modified `.planning/STATE.md` and unrelated `.trunk/` remained untouched.

## Known Stubs

None. Empty catalogs and optional `None` clients represent the explicit unavailable-MCP contract, not unfinished behavior. Empty internal lists in tests are recording-fake state before execution.

## Threat Flags

None. Tool-name/schema/argument tampering, result/error disclosure, and execution denial-of-service are the exact registered Plan 02-03 surfaces and are covered by collision rejection, immutable routing, local-only schema references, bounded execution, typed failures, and redacted diagnostics. No endpoint, auth path, storage path, data schema, subprocess, network call, external service, package, manifest, or configuration was added.

## User Setup Required

None - no package, credential, model, network service, data access, MCP process, configuration, or manifest change is required.

## Next Phase Readiness

- Provider adapter plans can convert `ToolCatalog.definitions` to SDK-local shapes while sharing the same original-name routing and execution policy.
- Conversation orchestration can enumerate and execute tools without importing Gemini types or reading bridge-private mappings.
- The compatibility Gemini bridge remains available until its existing consumers migrate in their owning plans.

## Self-Check: PASSED

- All three owned implementation/test artifacts and this summary exist on disk.
- All four RED/GREEN commits exist in Git history in the required order.
- Frontmatter contains `status: complete` and both requirement IDs from the plan.
- Exact task checks, Phase 1 MCP characterization, the full offline suite, Ruff, compile, and diff checks passed after the final code change.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
