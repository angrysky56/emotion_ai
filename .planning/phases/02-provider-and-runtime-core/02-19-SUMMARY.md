---
phase: 02-provider-and-runtime-core
plan: 19
subsystem: runtime
tags: [fastapi, lifespan, ollama, mcp, gemini, memvid, autonomic, tdd]

requires:
  - phase: 02-provider-and-runtime-core
    provides: typed providers, lifecycle ownership, optional dependency lanes, and verification gap report
provides:
  - base-only loopback Ollama import, preflight, serve, lifespan, and shutdown proof
  - four explicit optional lifecycle stages with safe failure and reverse cleanup
  - bounded installed-lane smoke for MCP, Gemini bridge, Memvid, and autonomic behavior
affects: [02-20, phase-02-verification, local-runtime, dependency-contract]

tech-stack:
  added: []
  patterns: [strict false-default feature flags, local optional imports, AsyncExitStack partial-start cleanup, deferred provider-neutral runtime]

key-files:
  created:
    - tests/runtime/test_base_install_startup.py
    - tests/runtime/test_optional_integrations.py
  modified:
    - aura_backend/main.py
    - aura_backend/mcp_system.py
    - aura_backend/runtime/config.py
    - tests/support/main_subprocess_probe.py
    - tests/test_python_dependency_contract.py

key-decisions:
  - "Keep the supported main and runtime entry points base-only; optional packages load only inside explicitly enabled owning stages."
  - "Preserve the legacy_services resource name for route compatibility while separating MCP, Gemini bridge, Memvid, and autonomic ownership."
  - "Treat missing enabled extras as fixed optional_resource_failed status without exposing source details or making base Ollama unready."

patterns-established:
  - "Optional lifecycle pattern: strict configuration gate, local import, cleanup registration before fallible initialization, safe optional status."
  - "Conditional smoke pattern: exact installed module check, no-I/O collaborator injection, pass or declared_extra_not_installed only."

requirements-completed: [TEST-03, AI-01, OPS-01, OPS-02]

duration: 18min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 19: Base-Only Optional Runtime Closure Summary

**Default loopback Ollama now completes import, preflight, serve delegation, FastAPI lifespan, readiness, and reverse shutdown while MCP, Gemini, Memvid, and autonomic behavior remain four explicit optional stages.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-08-20T22:50:25Z
- **Completed:** 2026-08-20T23:08:51Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Removed optional MCP, Google Gemini, and Memvid imports from the required base startup path; a bounded child proves the public app/runtime start with all four optional distribution roots blocked.
- Added strict false-default `AURA_MCP_ENABLED`, `AURA_MEMVID_ENABLED`, and `AUTONOMIC_ENABLED` settings and independent optional resource stages for MCP, Gemini bridge, Memvid, and autonomic behavior.
- Separated provider-neutral MCP discovery from Gemini conversion, preserved installed explicit integrations, and made partial initialization cleanup idempotent and reverse ordered.
- Exercised all installed real lanes without network, MCP subprocesses, model requests, repositories, databases, or user data. MCP/FastMCP, `google.genai.types`, `memvid_sdk`, and the autonomic application seam each passed; no lane was summarized from `not_run`.

## Task Commits

1. **Task 02-19-01: Specify base-only startup and four optional-stage contracts** — `56f33c1` (RED tests)
2. **Task 02-19-02: Implement lazy four-stage optional lifecycle composition** — `2473ecf` (GREEN implementation)

## Files Created/Modified

- `tests/runtime/test_base_install_startup.py` — Strict settings, blocked-extra import, and complete subprocess startup evidence.
- `tests/runtime/test_optional_integrations.py` — Four-stage enablement/failure/cleanup plus conditional real-lane no-I/O smoke.
- `tests/support/main_subprocess_probe.py` — Bounded base-only preflight, serve, lifespan, cleanup, and side-effect probe.
- `tests/test_python_dependency_contract.py` — Base-only main/runtime entrypoint lane contract.
- `aura_backend/runtime/config.py` — Exact lower-case boolean parsing with false defaults.
- `aura_backend/mcp_system.py` — Provider-neutral MCP startup and separately lazy Gemini bridge lifecycle.
- `aura_backend/main.py` — Required base composition plus four optional `ResourceFactory` stages.

## Verification

- Focused RED before implementation: **26 failed, 21 passed, 1 skipped**, for missing strict flags, missing base child, and absent optional stages.
- Plan Task 1 command after implementation: **54 passed, 1 intentional pre-change authorization skip**.
- Plan Task 2 compatibility command: **148 passed**.
- Complete offline suite: **498 passed, 2 skipped, 1 deselected**.
- Active backend/test Ruff: **passed**.
- `uv lock --check`: **passed**, 180 packages resolved with no lock mutation.
- Frontend TypeScript and Vite production build: **passed**.
- Manifest, lock, package evidence, rejected dependency rows, protected data roots, authentication boundary, and remote state: **unchanged**.
- GitHub CI/Pyright: **not run and not claimed**; the separate remote execution blocker remains pending.

## Decisions Made

- Gemini bridge activation requires both explicit MCP enablement and explicit Gemini provider selection; MCP with Ollama never imports Google.
- Memvid verifies its declared SDK only after explicit enablement, then starts the existing facade inside an owned cleanup boundary.
- Autonomic behavior receives a provider-neutral deferred runtime so the selected provider remains the final required lifecycle stage and closes first.

## Deviations from Plan

None - plan executed within its declared files and scope fence.

## Issues Encountered

- The GSD helper remains unavailable because its installed runtime cannot resolve `../../../package.json`; execution and verification used the plan's direct commands. The shared `.planning/STATE.md` was intentionally left for the parent orchestrator, as assigned.

## Known Stubs

None. Test fakes are deliberate no-I/O evidence collaborators and do not flow into application behavior.

## User Setup Required

None. Optional integrations remain disabled unless explicitly selected and enabled.

## Next Phase Readiness

- Plan 02-20 can consume the complete base-startup contract and four safe optional statuses.
- Required remote GitHub CI/Pyright remains pending and must not be inferred from these local results.

## Self-Check: PASSED

- Both created test files and all five modified implementation/contract files exist.
- RED commit `56f33c1` precedes GREEN commit `2473ecf`.
- Both exact plan commands, the complete offline suite, Ruff, frontend typing/build, lock check, and diff check passed.
- No manifest, lock, evidence, data-root, auth, `.trunk/`, or remote-state change is present.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
