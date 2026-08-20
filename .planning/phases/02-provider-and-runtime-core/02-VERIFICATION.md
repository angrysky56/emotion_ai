---
phase: 02-provider-and-runtime-core
verified: 2026-08-20T22:03:03Z
status: gaps_found
score: 13/16 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "A fresh documented base installation can start the default loopback Ollama runtime without optional cloud or MCP dependency groups."
    status: failed
    reason: "README.md and STARTUP_GUIDE.md prescribe `uv sync --locked`, whose dry run removes mcp, fastmcp, google-genai, and memvid-sdk. The required lifespan resource then unconditionally imports mcp_integration and mcp_system; mcp_system unconditionally imports the Google Gemini bridge. Missing-extra probes reproduce ModuleNotFoundError before default startup can complete."
    artifacts:
      - path: "README.md"
        issue: "The supported one-time setup installs only the base group."
      - path: "aura_backend/STARTUP_GUIDE.md"
        issue: "The same base-only setup is documented as sufficient for normal local startup."
      - path: "aura_backend/main.py"
        issue: "_start_legacy_resources unconditionally imports optional MCP modules in a required resource stage."
      - path: "aura_backend/mcp_system.py"
        issue: "Top-level import of mcp_to_gemini_bridge makes the provider-gemini group mandatory even when Ollama is selected."
    missing:
      - "Make optional MCP/Gemini integrations truly lazy and degradable so the default Ollama path starts from the documented base installation."
      - "Add a clean base-install startup/lifespan test that excludes all optional groups."
  - truth: "The current Phase 2 revision has completed green required GitHub CI, including typing-python after npm ci."
    status: failed
    reason: "HEAD 670856ed8936c260f4ca1621d8d3d90326d61ecc is 159 commits ahead of origin/main, GitHub reports no workflow run for that SHA, and the project-local Pyright executable is absent. The required clean-CI typing result remains not_run/pending."
    artifacts:
      - path: ".github/workflows/ci.yml"
        issue: "The static workflow contract is present, but there is no execution record for the current revision."
      - path: "package-lock.json"
        issue: "It locks pyright@1.1.413, but a lock entry is not execution evidence."
    missing:
      - "Publish the reviewed revision through an authorized push or PR."
      - "Obtain a completed green GitHub typing-python job that runs npm ci before npm run typecheck:python, plus green required CI lanes for the same revision."
  - truth: "Every executable Phase 2 pytest contract is import-safe and the earlier bare-pytest false-success defect cannot recur through a plan command."
    status: failed
    reason: "02-17-PLAN.md still contains three bare `uv run --locked --no-sync pytest ...` command occurrences. tests/test_ci_contract.py scans only 02-18-PLAN.md, 02-VALIDATION.md, and workflow commands, so it passes while leaving 02-17 uncovered."
    artifacts:
      - path: ".planning/phases/02-provider-and-runtime-core/02-17-PLAN.md"
        issue: "Bare pytest remains at lines 120, 150, and 177; this repository requires `python -m pytest` for import-safe execution."
      - path: "tests/test_ci_contract.py"
        issue: "PLAN_PATH is fixed to 02-18-PLAN.md and the regression test does not scan every Phase 2 plan."
    missing:
      - "Revise all three 02-17 command occurrences to `uv run --locked --no-sync python -m pytest ...`."
      - "Generalize the regression contract to reject bare pytest in every executable Phase 2 plan/validation command."
---

# Phase 2: Provider and Runtime Core Verification Report

**Phase Goal:** Deliver one reliable conversation path through Ollama and the existing cloud providers behind a typed, testable runtime boundary.

**Verified:** 2026-08-20T22:03:03Z  
**Status:** gaps_found  
**Re-verification:** No — initial verification

## Verdict

## GAPS FOUND

The provider/runtime implementation and every named locally available gate are green, but Phase 2 cannot be called complete. A fresh installation following the supported base-only setup cannot start the default Ollama runtime because required lifespan composition imports optional MCP and Gemini dependencies. Its own final-gate contract also requires a completed green clean GitHub `typing-python` job, and no GitHub run exists for the current local revision. A third independently observed gap leaves three known-bad bare-pytest commands in Plan 02-17 outside the regression test's scan.

The optional Ornith lane is truthfully `not_run`; it is not counted as a failure or as evidence. The current npm lock also reports three high-severity audit findings. Those findings are an unresolved warning, not silently treated as clean, but they do not map to a Phase 2 security requirement and repairing them would exceed the exact dependency-change authorization used by this phase.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | One immutable typed provider boundary represents messages, tools, results, stream events, health, and safe failures for Ollama, Gemini, and OpenRouter. | VERIFIED | `providers/base.py`, `errors.py`, and `config.py` are substantive; contract/factory tests pass. |
| 2 | Ollama uses the supported OpenAI-compatible path with finite timeouts, zero hidden retries, real incremental streaming, cancellation, and normalized errors. | VERIFIED | Shared transport and Ollama implementation inspected; focused provider suite passed 81/81. |
| 3 | OpenRouter is explicit-cloud only, while Gemini is lazily imported, asynchronous, stateless per request, and closes resources safely. | VERIFIED | Adapter/factory code is wired; OpenRouter/Gemini behavioral tests are included in the 81 passing focused tests. |
| 4 | Deterministic provider fakes exercise normal, streaming, malformed, timeout, unavailable-model, and bounded-work behavior without network access. | VERIFIED | Exact offline suite passed 457 tests; provider runtime tests exercise all named terminal paths. |
| 5 | Partial, cancelled, malformed, unavailable, or resource-limited work cannot be exposed or counted as `Completed`. | VERIFIED | `ProviderRuntime` withholds terminal completion until iterator exhaustion; named cancellation, mid-stream failure, timeout, post-terminal-delta, and cleanup tests passed. |
| 6 | Tool discovery/execution and emotional/cognitive analyses use provider-neutral boundaries and the one selected runtime. | VERIFIED | Neutral tool catalog/executor and analysis transport are wired; the complete offline suite passes. |
| 7 | `/conversation` uses `app.state.runtime.provider_runtime` and preserves Phase 1's seven fields, HTTP-200 fallback, one session clear, persistence, and degraded-storage behavior. | VERIFIED | Decorated route at `main.py:1950`; 38 focused compatibility/persistence/import/local-boundary tests passed. |
| 8 | Aura remains a private local app: no sign-in was added, loopback is the default, wildcard CORS is rejected, and LAN exposure is explicit. | VERIFIED | No added auth surface was found; runtime defaults to `127.0.0.1`; local-boundary tests pass, including unsigned conversation access. |
| 9 | Importing the app constructs no provider/client/database/process resources; lifespan owns exactly one runtime and unwinds partial startup in reverse order. | VERIFIED | Import-safety and lifecycle source inspected; focused lifecycle/import tests pass. |
| 10 | The documented one-command path starts the default local Ollama runtime from a fresh base install; health/preflight/serve remain bounded and non-mutating. | FAILED | Health/CLI/wrapper tests pass in the existing expanded environment, but `uv sync --locked --dry-run` removes all optional groups while required startup imports `mcp` and `google.genai`; missing-extra probes fail. |
| 11 | Phase 1 data roots and public compatibility remain invariant; Phase 2 performs no storage migration or deletion. | VERIFIED | No Phase 2 diff touches protected data roots; pre/post full-suite snapshot SHA-256 remained `45e61336fac9120f145b74be4e9b7db0b2150f1b13f6a9c1e731db3921e70e71`. |
| 12 | Only the 16 approved package rows affect the exact authorized action sets; all four SUS rows remain rejected and untouched, after Plans 02-16/02-17 were revised. | VERIFIED | Evidence has exactly 16 OK/4 SUS rows; `deceaa7` precedes manifest commits `cc7e922` and `57ca161`; 46 focused authority tests pass with two expected pre-edit-gate skips. |
| 13 | Python and Node each have one active lock authority, and every locally available deterministic/lint/frontend/build/lock gate is green. | VERIFIED | `uv lock --check`, exact 457-test gate, active-code Ruff, frontend typecheck/build, contract tests, and Docker check all pass. |
| 14 | CI is statically split into seven honest lanes, with pinned actions, `npm ci` before Pyright, module-mode pytest in CI, and adversarial rejection of swallowed failure/reordered setup. | VERIFIED | `tests/test_ci_contract.py` passes 9 tests as part of the 14-test CI/baseline run; workflow inspected directly. This verifies structure, not execution. |
| 15 | The current revision has completed green required GitHub CI, including clean-CI Python typing. | FAILED | `gh run list --commit 670856e...` returned `[]`; origin/main is 159 commits behind; local `node_modules/.bin/pyright` is absent. |
| 16 | The bare-pytest false-success defect cannot recur through any Phase 2 plan contract. | FAILED | Plan 02-17 retains bare commands at lines 120, 150, 177; the regression test scans only Plan 02-18, validation, and CI. |

**Score:** 13/16 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `aura_backend/providers/{base,errors,config,runtime}.py` | Typed domain, safe failures/settings, deadlines, cancellation, completion ownership | VERIFIED | Substantive, imported, used, and behavior-tested. |
| `aura_backend/providers/{openai_compatible,ollama,openrouter,gemini,factory}.py` | Three complete adapters behind one lazy selection boundary | VERIFIED | Real data reaches normalized results/events; no provider-specific branch exists in the active conversation route. |
| `aura_backend/providers/tools.py`, `aura_backend/mcp_system.py` | Neutral tool catalog/executor seam | VERIFIED | Wired into application composition and the conversation request. |
| `aura_backend/runtime/{app,config,health,cli}.py` | Lifecycle, local-first settings, cached health, preflight/serve | VERIFIED | Substantive and covered by passing runtime tests. |
| `aura_backend/main.py` | Import-safe composition plus one provider-neutral `/conversation` route | PARTIAL | Import and route behavior are correct, but lifespan startup makes optional MCP/Gemini modules mandatory for default Ollama. |
| Startup wrappers, `README.md`, `STARTUP_GUIDE.md`, `.env.example` | Thin non-installing delegates and accurate local-first operator contract | FAILED | Delegation and loopback claims pass, but the documented base setup does not install dependencies unconditionally required by lifespan. |
| `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`, `Dockerfile` | Exact approved dependency authority and one lock per ecosystem | VERIFIED | Static desired-state and adversarial dependency tests pass; lock check passes. |
| `.planning/evidence/phase-02/package-legitimacy.json` | Exact scoped 16 OK/4 SUS decision | VERIFIED | SHA-256 `e3efba...24bdb`; decision and candidate sets match Ty's instruction. |
| `.planning/evidence/phase-02/runtime-baseline.json` | Honest baseline-only evidence | VERIFIED | Import samples recorded; optimization and Ornith call remain explicitly `not_run`. |
| `.github/workflows/ci.yml`, `tests/test_ci_contract.py` | Seven independent fail-closed CI lanes | VERIFIED (static) | Workflow structure and adversarial mutations pass. No current-revision execution exists. |
| `.planning/phases/02-provider-and-runtime-core/02-17-PLAN.md` | Import-safe executable verification commands | FAILED | Three bare-pytest occurrences remain. |
| GitHub Actions run for `670856ed8936c260f4ca1621d8d3d90326d61ecc` | Completed green required lanes and clean Python typing | MISSING | GitHub query returned no runs for this SHA. |

### Exact Package Decision Trace

| Decision set | Exact rows | Observed result |
|---|---|---|
| 16 conditionally approved OK rows | `ruff@0.12.7`; `pyright@1.1.413`; `google-genai@1.75.0`; `mcp@1.27.0`; `fastmcp@3.2.4`; `memvid-sdk@2.0.159`; `beautifulsoup4@4.13.4`; `ebooklib@0.19`; `opencv-python@4.11.0.86`; `pandas@2.2.3`; `pillow@12.2.0`; `pypdf@6.10.2`; `qrcode@8.2`; `anthropic@0.54.0`; `websockets@15.0.1`; `@google/genai@1.51.0` | The exact 14 Python actions and two Node actions are enforced by desired-state tests. No row-level evidence was treated as direct edit authority. |
| 4 rejected SUS rows | `pyzbar@0.1.9`; `faiss-cpu@1.11.0`; `faiss-gpu-cu12@1.14.1.post1`; `asyncio-mqtt@0.16.2` | Their direct Python declarations remain unchanged and their resolved lock records pass immutable-digest checks. No rejected row appears in an action set. |
| Required chronology | Revise Plans 02-16 and 02-17 before dependency edits | Revision commit `deceaa7` precedes Python manifest/lock commit `cc7e922` and Node manifest/lock commit `57ca161`. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `main.py:/conversation` | `ApplicationRuntime.provider_runtime` | `http_request.app.state.runtime` then typed `ProviderRequest` | WIRED | Result feeds response, analysis, exchange, and persistence. |
| `ApplicationRuntime` | `ProviderRuntime` | required provider factory starts last and closes first | WIRED | Partial-start and shutdown-order tests pass. |
| `ProviderRuntime` | selected adapter | bounded `generate`/`stream` delegation | WIRED | Registry, deadline, terminal, and cancellation invariants are tested. |
| `ModelProviderFactory` | Ollama/Gemini/OpenRouter | one validated lazy branch | WIRED | Default selects only Ollama; cloud credentials are required only when explicitly selected. |
| MCP/tool discovery | adapter requests | neutral `ToolCatalog` and `ToolExecutor` | WIRED | Tool schemas/results cross no provider-specific route seam. |
| `package.json` | `package-lock.json` and CI | named local scripts after lock-faithful `npm ci` | WIRED (static) | Frontend scripts pass locally; clean Pyright execution remains absent. |
| Phase 2 plan commands | pytest import mode regression | `tests/test_ci_contract.py` | PARTIAL | CI/Plan 18/validation are covered; Plan 17 is omitted. |
| Documented `uv sync --locked` | default Ollama lifespan | base dependency group into `_start_legacy_resources` | NOT WIRED | Base sync excludes optional MCP/Gemini groups that the required startup stage imports unconditionally. |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Produces Real Data | Status |
|---|---|---|---|---|
| Active conversation route | `ProviderResult.content` and reflection summary | selected provider through `ProviderRuntime.generate` | Yes | FLOWING |
| Conversation analyses | user message + provider answer | selected runtime injected into analysis functions | Yes | FLOWING |
| Persistence exchange | normalized user/AI memories and session | completed conversation pipeline | Yes | FLOWING |
| Provider streaming | upstream text/tool deltas and terminal result | OpenAI-compatible or Gemini async iterator | Yes; terminal is gated | FLOWING |
| Health endpoints | cached runtime/provider/resource snapshot | lifespan startup capture | Yes; no health-time generation | FLOWING |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Complete required offline suite | `uv run --locked --no-sync python -m pytest tests -q -m 'not live'` | 457 passed, 2 skipped, 1 deselected in 25.70s | PASS |
| CI and baseline contracts | `... python -m pytest tests/test_ci_contract.py tests/runtime/test_baseline_evidence.py -q` | 14 passed | PASS |
| Streaming/cancellation/no-false-completion/lifecycle | focused provider + lifecycle command | 81 passed | PASS |
| Phase 1 conversation/persistence/local/import compatibility | focused compatibility command | 38 passed | PASS |
| Exact package/lock decision contracts | focused authority command | 46 passed, 2 intentional pre-edit-gate skips | PASS |
| Python lock | `uv lock --check` | resolved 180 packages; exit 0 | PASS |
| Active-code lint | Plan 02-18 Ruff command with three legacy exclusions | all checks passed | PASS |
| Frontend typing | `npm run typecheck:frontend` | exit 0 | PASS |
| Frontend build | `npm run build` | Vite 8.0.10 build succeeded | PASS |
| Docker authority | `docker build --check -f aura_backend/Dockerfile .` | check complete, no warnings | PASS |
| Data-root invariance | snapshot digest before/after full suite | same SHA-256 both times | PASS |
| Documented base dependency result | `uv sync --locked --dry-run` | would uninstall 47 packages, including `mcp`, `fastmcp`, `google-genai`, and `memvid-sdk` | FAIL |
| Default startup without optional MCP/Gemini | import-blocked `_start_legacy_resources` / `mcp_system` probes | reproducible `ModuleNotFoundError` for `mcp` and `google.genai` | FAIL |
| Current-revision GitHub CI | `gh run list --commit 670856ed...` | `[]` | FAIL |
| Python typing | required clean `typing-python` job | not run; local executable absent | FAIL |
| Optional Ornith | evidence artifact / optional live lane | `not_run` by design | OPTIONAL / NOT COUNTED |

### Probe Execution

No Phase 2 `probe-*.sh` file is declared or present. Runnable behavior is covered by the exact pytest, CLI, wrapper, lock, build, and Docker checks above; no substitute probe result is claimed.

## Requirements Coverage

| Requirement | Status | Evidence |
|---|---|---|
| TEST-03 | SATISFIED | Provider translation/failure, API, persistence, filesystem, import, and runtime behaviors are exercised by the 457-test offline suite and focused reruns. |
| TEST-05 | BLOCKED | Seven separate workflow lanes exist statically, but required CI has not run for the current revision and clean-CI Pyright is pending. |
| AI-01 | SATISFIED | One typed contract supports Ollama, Gemini, and OpenRouter without provider branches in conversation orchestration. |
| AI-02 | SATISFIED | Ollama compatible transport has explicit timeouts, real deltas, cancellation, health/error mapping, and passing behavioral tests. |
| AI-03 | SATISFIED | Deterministic fakes cover all required outcomes; optional live Ornith remains correctly marked and unclaimed. |
| OPS-01 | BLOCKED | Commands and wrappers are non-mutating and loopback-first, but the documented base setup cannot satisfy the default lifespan's imports. |
| OPS-02 | BLOCKED | Lock authority is singular and optional lanes are declared, but optional MCP/Gemini dependencies are mandatory in the default runtime composition. |

No additional Phase 2 requirement is orphaned from the plan frontmatter.

## Anti-Patterns and Risks

| File / Evidence | Pattern | Severity | Impact |
|---|---|---|---|
| `02-17-PLAN.md:120,150,177` | Bare pytest executable | BLOCKER | Reintroduces the known import/false-success defect when the plan command is replayed. |
| `tests/test_ci_contract.py:16-29,151-161` | Regression scan fixed to Plan 02-18 and validation | BLOCKER | The test is green despite the Plan 02-17 defect. |
| `README.md:163-170`, `STARTUP_GUIDE.md:15-23`, `main.py:903-915`, `mcp_system.py:16-18` | Base-only setup wired to unconditional optional imports | BLOCKER | A fresh user following the supported setup cannot start default local Ollama. Existing-environment tests conceal the missing clean-base integration case. |
| npm lock audit | Vite 8.0.10 (direct dev), PostCSS 8.5.14 and Nano ID 3.3.12 (transitive) | WARNING | `npm audit --json --package-lock-only` exits 1 with 3 high package findings and 0 critical. All are in the frontend development tool chain; the exact Phase 2 authorization did not permit a broad upgrade. |
| `_legacy_process_conversation` in `main.py` | Retained unregistered transitional implementation | INFO | It is not decorated or used by the active route; later architecture cleanup may remove it after compatibility remains pinned. |

No unreferenced `TBD`, `FIXME`, or `XXX` debt marker was found in the Phase 2 modified implementation/test files. Empty collections found by broad scans were initial state, test fixtures, or deliberate optional absence, not rendered or runtime stubs.

## Human Verification Required

None for the required Phase 2 truths: the state-transition, cancellation, cleanup, ordering, fallback, and persistence invariants have passing automated tests. The real Ornith scenario remains an optional external-service lane and is accurately recorded as `not_run`; it is not promoted to a human gate or success claim.

## Gaps Summary

1. **The supported fresh local setup does not start default Ollama.** This is locally fixable in source/tests/docs, but this verification was explicitly read-only except for this report. Decouple required lifespan composition from optional MCP/Gemini modules and prove startup in a clean base-only environment.
2. **Required clean CI/Pyright evidence is absent.** This is not locally fixable within this verification's authority: HEAD must first be published through an authorized push/PR, then the required GitHub lanes—especially `typing-python` after `npm ci`—must complete green for that same SHA. Workflow text and a lock entry cannot substitute for execution.
3. **Plan 02-17 still carries the known bare-pytest defect.** This is locally fixable, but this verification was explicitly read-only except for this report. Correct the three commands and expand the regression test to scan every Phase 2 executable plan contract before rerunning the local and CI gates.

The npm audit warning also needs an explicitly authorized, narrow follow-up dependency review; it should not be hidden, but it is not the reason this phase is marked `gaps_found`.

---

_Verified: 2026-08-20T22:03:03Z_  
_Verifier: Codex (gsd-verifier)_
