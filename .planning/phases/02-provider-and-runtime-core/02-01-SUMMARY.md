---
phase: 02-provider-and-runtime-core
plan: 01
subsystem: provider-domain
tags: [python, dataclasses, protocol, provider-config, streaming, redaction]

requires:
  - phase: 01-preservation-and-trusted-baseline
    provides: Deterministic pytest boundary and characterized companion/local contracts
provides:
  - Immutable provider-neutral request, result, usage, health, tool, and stream values
  - Fail-closed provider failure taxonomy and allowlisted public serialization
  - Pure local-first provider settings parsing with selected-cloud-only credential validation
  - Preserved Message, ProviderResponse, and BaseProvider compatibility exports
affects: [02-02, 02-03, 02-04, 02-05, 02-06, provider-runtime, conversation-orchestration]

tech-stack:
  added: []
  patterns:
    - Frozen and slotted provider-domain values with no SDK or raw-exception fields
    - Completed as the sole successful stream terminal
    - Explicit-mapping configuration with Ollama default and redacted failures

key-files:
  created:
    - aura_backend/providers/errors.py
    - aura_backend/providers/config.py
    - tests/providers/test_contract.py
  modified:
    - aura_backend/providers/base.py

key-decisions:
  - "Keep the characterized mutable legacy provider records separate from the new immutable provider-domain types until downstream routes and adapters migrate."
  - "Represent every non-success state as ProviderFailure while allowing asyncio.CancelledError to propagate; only Completed carrying ProviderResult licenses stream success."
  - "Parse provider settings only from an explicit mapping, default to Ollama, and validate credentials only for the selected cloud provider."

patterns-established:
  - "Fail-closed terminal typing: deltas, failures, resource limits, and cancellation objects cannot construct Completed."
  - "Public failure allowlist: code, provider, model, retryable, and correlation ID are the only serialized fields."
  - "Pure configuration boundary: no environment read, SDK import, model scan, client construction, or service call occurs while parsing settings."

requirements-completed: [TEST-03, AI-01, AI-03]

duration: 10min
completed: 2026-08-19
status: complete
---

# Phase 2 Plan 01: Typed Provider Domain Boundary Summary

**Immutable provider contracts now make completed success structurally distinct from every failure, partial, resource-limited, malformed, and cancelled outcome while defaulting configuration to local Ollama**

## Performance

- **Duration:** 10 min
- **Started:** 2026-08-19T19:33:39Z
- **Completed:** 2026-08-19T19:43:10Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added frozen/slotted provider requests, messages, results, usage, health, tools, text/tool deltas, and the sole successful `Completed` terminal plus an async `Provider` protocol.
- Added all ten required failure codes as immutable `ProviderFailure` exceptions whose public dictionary is constructed from a five-field safe allowlist and contains no raw exception/source material.
- Made `Completed` accept only a validated non-empty `ProviderResult`; partial deltas, typed failures, resource exhaustion, and cancellation cannot be represented as completed success.
- Added pure `ProviderSettings.from_mapping()` parsing with a local Ollama default, explicit Gemini/OpenRouter selection, selected-key-only credential checks, finite bounded timeout/retry/tool policies, and credential-free URL validation.
- Preserved the existing `Message`, `ProviderResponse`, and `BaseProvider` imports and kept the Phase 1 route, fallback, local-only, and no-sign-in characterization green.

## Task Commits

TDD gates were committed atomically in RED/GREEN order, followed by a green refactor:

1. **Task 1 RED: failing provider outcome contract** - `6a4d510` (test)
2. **Task 1 GREEN: fail-closed provider outcomes** - `ef00ce9` (feat)
3. **Task 2 RED: failing local-first settings contract** - `e6062cb` (test)
4. **Task 2 GREEN: pure provider settings parser** - `fe8d6dc` (feat)
5. **REFACTOR: hardened failure and iterator typing** - `d7654ed` (refactor)

## Files Created/Modified

- `aura_backend/providers/base.py` - Immutable provider-domain DTOs, stream union, protocol, and retained legacy exports.
- `aura_backend/providers/errors.py` - Exact normalized error codes and content-free immutable failure serialization.
- `aura_backend/providers/config.py` - Pure local-first selected-provider settings validation.
- `tests/providers/test_contract.py` - Offline contract, false-success, mutation, redaction, credential, and configuration matrix.

## Decisions Made

- Added a separate immutable `ProviderMessage` rather than freezing the legacy `Message`; this keeps the characterized route/adapters working while ensuring new `ProviderRequest` values are deeply immutable at their message boundary.
- Kept provider failure source exceptions out of `ProviderFailure` fields entirely. Adapters may use Python exception chaining internally, while default string/public representations remain content-free.
- Kept `ProviderErrorCode.CANCELLED` for safe health/metrics records, but operation cancellation remains `asyncio.CancelledError` and is never converted into a result or fallback success.
- Preserved the current factory's recognized provider, credential, model, Ollama URL, thinking-budget, and tool-round key names; added explicit provider-policy keys without changing manifests or existing factory behavior.

## Verification Evidence

- `uv run --locked --no-sync python -m pytest -q tests/providers/test_contract.py -k 'result or failure or stream or redact'` - **6 passed, 21 deselected**.
- `uv run --locked --no-sync python -m pytest -q tests/providers/test_contract.py -k 'config or settings or credential'` - **20 passed, 7 deselected**.
- `uv run --locked --no-sync python -m pytest -q tests/characterization/test_companion_contract.py tests/api/test_local_boundary.py` - **15 passed**.
- `uv run --locked --no-sync python -m pytest -q tests -m 'not live and not ollama and not gpu'` - **exit 0; 158 tests collected**.
- `ruff check aura_backend/providers/base.py aura_backend/providers/errors.py aura_backend/providers/config.py tests/providers/test_contract.py` - **passed**.
- `python -m py_compile` for all four owned Python files and `git diff --check` - **passed**.

## TDD Gate Compliance

- Task 1 RED failed with five missing-symbol/module failures before production edits; GREEN supplied the immutable boundary and all selected contract cases passed.
- Task 2 RED failed with twenty missing-config-module cases before production edits; GREEN supplied only the pure settings implementation and all twenty selected cases passed.
- The refactor commit followed both GREEN commits and retained all 27 provider contract cases green.
- Git history contains both required `test(02-01)` commits before their corresponding `feat(02-01)` commits.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Python 3.12's generated frozen/slotted dataclass setter rejects an unknown attribute with `TypeError` rather than always using `FrozenInstanceError`; the contract accepts either rejection while still asserting the dataclass is frozen and slotted.
- The GSD JavaScript helper was unavailable per the execution handoff. Direct Git/status/log, locked uv, Ruff, and pytest commands were used without broadening scope.
- Work shared the main tree. Only Plan 02-01-owned code/tests and this summary were staged; the orchestrator's modified `.planning/STATE.md` and unrelated `.trunk/` remained untouched.

## Known Stubs

None. Optional `None` fields in the stable DTOs represent explicit absence. The legacy `ProviderResponse.raw_response` field remains only on the deliberately preserved compatibility surface and is excluded from every new stable result/event type; downstream adapter/route plans own its migration.

## Threat Flags

None. The new provider/config trust boundaries and their failure, redaction, and selection mitigations are exactly the surfaces registered in Plan 02-01's threat model; no endpoint, auth path, storage path, schema, network call, or external service was added.

## User Setup Required

None - no package, credential, running model, network service, data access, or manifest change is required.

## Next Phase Readiness

- Plan 02-02 can build its deterministic event-controlled fake and runtime directly against `Provider`, `ProviderRequest`, `ProviderResult`, `StreamEvent`, and `ProviderFailure`.
- Plan 02-03 can build collision-safe tool registration/execution against immutable `ToolDefinition` schemas.
- Adapter/factory plans can consume `ProviderSettings` without ambient environment branching or eager cloud imports.
- No storage, API behavior, authentication, dependency, package lock, model, service, or history work occurred.

## Self-Check: PASSED

- All four plan artifacts exist on disk.
- All five RED/GREEN/refactor commits exist in Git history in the required order.
- Frontmatter contains `status: complete` and all three requirement IDs from the plan.
- Exact task commands, Phase 1 compatibility commands, the full offline suite, Ruff, compile, and diff checks passed after the final refactor commit.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-19*
