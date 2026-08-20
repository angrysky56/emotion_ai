---
phase: 02-provider-and-runtime-core
plan: 20
subsystem: testing
tags: [pytest, shlex, yaml, ci-contract, startup-docs, optional-runtime]

requires:
  - phase: 02-provider-and-runtime-core
    provides: base-only runtime repair, final 20-plan inventory, and optional-stage status contract
provides:
  - parsed fail-closed pytest command validation across every Phase 2 plan, validation row, and CI run block
  - exactly three import-safe Plan 02-17 command corrections
  - tested base and optional-stage startup instructions with inactive defaults
affects: [phase-02-verification, ci-contract, startup-operations]

tech-stack:
  added: []
  patterns: [schema-scoped command extraction, quote-aware shell segmentation, token-resolved executable validation, executable documentation contracts]

key-files:
  created: []
  modified:
    - .planning/phases/02-provider-and-runtime-core/02-17-PLAN.md
    - .env.example
    - aura_backend/STARTUP_GUIDE.md
    - tests/runtime/test_startup_docs.py
    - tests/test_ci_contract.py

key-decisions:
  - "Validate resolved executable tokens across complete required surfaces rather than matching one uv prefix or scanning ordinary prose."
  - "Keep optional integration preparation explicit while preserving base-only Ollama startup and false-default feature flags."

patterns-established:
  - "Command truth surface: exact inventory, non-empty extraction, safe YAML load, HTML decoding, quote-aware segmentation, shlex tokenization, and fail-closed errors."
  - "Optional startup contract: locked extra plus explicit selection key, redacted resource status, and no startup-time environment mutation."

requirements-completed: [TEST-03, TEST-05, OPS-01, OPS-02]

duration: 4min
completed: 2026-08-20
status: complete
---

# Phase 2 Plan 20: Verification Command and Startup Documentation Closure Summary

**All Phase 2 executable pytest surfaces are now parsed and import-safe, while the supported startup guide keeps base Ollama sufficient and makes each optional stage an explicit, tested choice.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-20T23:20:50Z
- **Completed:** 2026-08-20T23:24:14Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Replaced the narrow Plan 02-18 string check with an exact Plan 01-through-20 inventory, validation-matrix task parity, and every-job CI run-block contract.
- Added HTML decoding, escaped-continuation normalization, quote-aware shell segmentation, standard-library shell tokenization, environment/`uv run` resolution, adversarial prefix/boundary coverage, prose immunity, and non-vacuous failure checks.
- Corrected exactly three Plan 02-17 executable commands by inserting `python -m`; targets, flags, frontend chains, dependency approvals, and outcome claims are unchanged.
- Documented inactive MCP, Memvid, and autonomic defaults; exact MCP, Gemini, and Memvid locked extras; explicit Gemini/provider credentials; provider-preserving autonomic activation; and redacted `optional_resource_failed` remediation.

## Task Commits

Each task was committed atomically using RED then GREEN:

1. **Task 02-20-01 RED: Add failing phase command contract** — `bc54041` (test)
2. **Task 02-20-01 GREEN: Make Plan 02-17 pytest import-safe** — `6460f33` (fix)
3. **Task 02-20-02 RED: Add failing optional startup docs contract** — `f536217` (test)
4. **Task 02-20-02 GREEN: Document explicit optional runtime stages** — `57f26c5` (docs)

## Files Created/Modified

- `.planning/phases/02-provider-and-runtime-core/02-17-PLAN.md` — Three reviewed commands now invoke pytest through `python -m`.
- `tests/test_ci_contract.py` — Complete parsed plan, validation, and CI executable-token contract with adversarial and fail-closed fixtures.
- `.env.example` — Exact inactive MCP and Memvid defaults alongside the existing inactive autonomic default.
- `aura_backend/STARTUP_GUIDE.md` — Base-only setup plus explicit optional activation and safe remediation.
- `tests/runtime/test_startup_docs.py` — Executable defaults, extras, activation, non-mutation, and redaction documentation contract.

## Verification

- Task 02-20-01 RED: **2 expected failures, 5 passes**; failures identified exactly the three bare Plan 02-17 surfaces.
- Task 02-20-01 GREEN: **15 passed**.
- Task 02-20-02 RED: **4 expected failures, 9 passes**; failures identified exactly the missing defaults and optional-stage guidance.
- Task 02-20-02 GREEN: **13 passed**.
- Complete offline suite: **508 passed, 2 skipped, 1 deselected**.
- Active backend/test Ruff: **passed**.
- `uv lock --check`: **passed**, resolving the existing 180-package lock without mutation.
- Frontend TypeScript and Vite production build: **passed**.
- `git diff --check`: **passed**.
- Scoped diff: only the five declared task files changed; no source, manifest, lock, evidence, workflow, data, authentication, `.trunk/`, or remote state changed.
- GitHub CI and project-local Pyright execution: **not run and still pending**; no local success is claimed.

## Decisions Made

- Resolve the command at each shell segment rather than rejecting a harmless argument or filename containing the word `pytest`.
- Treat missing plans, task rows, workflow jobs, run collections, executable bodies, and parseable shell surfaces as failures, never clean evidence.
- Keep optional setup separate from preflight and serve; the runtime never installs or synchronizes packages.

## Deviations from Plan

None - plan executed exactly within its declared files and scope fence.

## Issues Encountered

None.

## Known Stubs

None.

## User Setup Required

None. The default remains local Ollama with optional stages disabled. Operators who deliberately enable an optional stage can now follow the tested locked command and setting in the startup guide.

## Next Phase Readiness

- The two locally repairable Phase 2 verification gaps are closed and ready for independent phase re-verification.
- Remote GitHub CI/Pyright evidence remains pending and must stay separate from local completion.

## Self-Check: PASSED

- All five declared task files exist and are the only Plan 02-20 task changes.
- RED commits `bc54041` and `f536217` precede GREEN commits `6460f33` and `57f26c5`.
- Both focused suites, the complete offline suite, Ruff, lock check, frontend typing/build, and diff checks passed.
- No manifest, lock, evidence, workflow, runtime source, data-root, authentication, `.trunk/`, or remote-state change is present.

---
*Phase: 02-provider-and-runtime-core*
*Completed: 2026-08-20*
