---
phase: 02
slug: provider-and-runtime-core
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-19
revised: 2026-08-20
plan_count: 18
task_count: 38
---

# Phase 2 — Validation Strategy

Every implementation task has an exact sub-60-second automated check except the final consolidated regression, whose broader duration is intentional and isolated to 02-18-03. Behavior-changing tasks create their RED test first, then make the same command GREEN. Deterministic proof never requires Ollama, cloud credentials, personal data, or network access.

## Test Infrastructure

| Layer | Authority | Phase 2 use |
|---|---|---|
| Python unit/integration | Locked pytest + pytest-asyncio through `uv run --locked --no-sync` | Provider contracts, runtime lifecycle, import safety, API preservation, manifests, workflow contract |
| Type checking | Exact checkpoint-approved Pyright through `npm run typecheck:python` | Static manifest/lock/script proof in 02-17; first execution after Plan 02-18's isolated clean npm install |
| Python lint | Exact checkpoint-approved Ruff through locked uv dev group | Required source/test lint lane |
| Frontend typing/build | Locked TypeScript/Vite through npm scripts | Separate `tsc --noEmit` and build evidence |
| Optional live | Pytest markers `live` and `ollama`, explicit environment opt-in, `asyncio.timeout` | Synthetic `ornith:latest` first-delta/cancellation probe, never deterministic proof |
| CI contract | `tests/test_ci_contract.py` | Parses workflow structure, pins, commands, and anti-false-success rules |

## Sampling and Truth Rules

- Each task runs the exact row below before completion; TDD tasks capture an intentional RED result before production edits and the listed GREEN result afterward.
- Each plan reruns all task commands in that plan. Plans touching public behavior also run the cited Phase 1 characterization/preservation tests.
- Wave completion requires every plan in that wave to be GREEN; same-wave plans have disjoint file ownership.
- Phase completion requires 02-18-03's locally available offline gate plus a completed green clean-CI `typing-python` status; absent CI status leaves Python typing `not_run`/pending. Optional live and environment-blocked results remain separately labeled and cannot satisfy required gates.
- `skipped`, `blocked`, `timeout`, `resource_limit`, malformed streams, or missing terminal success are not provider successes. Once live prerequisites are confirmed, these outcomes fail the live lane.
- Public and logged provider errors contain only safe category/provider/retryable/correlation metadata; raw exception text, credentials, endpoints, prompts, tool payloads, and response bodies are prohibited.

## Exact Task Verification Matrix

| Task ID | Wave | Requirements | Exact automated command | Evidence boundary |
|---|---:|---|---|---|
| 02-01-01 | 1 | TEST-03, AI-01, AI-03 | `uv run --locked --no-sync python -m pytest -q tests/providers/test_contract.py -k 'result or failure or stream or redact'` | Typed terminal/result and error-redaction contract |
| 02-01-02 | 1 | TEST-03, AI-01, AI-03 | `uv run --locked --no-sync python -m pytest -q tests/providers/test_contract.py -k 'config or settings or credential'` | Local-first parsing and secret-safe representation |
| 02-14-01 | 1 | TEST-05, OPS-02 | `uv run --locked --no-sync python -m pytest -q tests/test_dependency_audit.py -k 'package or legitimacy or freshness or candidate'` | Current registry/source/maintainer/entrypoint evidence; no install |
| 02-14-02 | 1 | TEST-05, OPS-02 | `uv run --locked --no-sync python -m pytest -q tests/test_dependency_audit.py` | Every dependency move/removal tied to imports and supported entry points |
| 02-02-01 | 2 | TEST-03, AI-02, AI-03 | `uv run --locked --no-sync python -m pytest -q tests/providers/test_fake.py` | Event-controlled fake; no sleeps or network |
| 02-02-02 | 2 | TEST-03, AI-02, AI-03 | `uv run --locked --no-sync python -m pytest -q tests/providers/test_streaming.py` | First-delta, deadline, cancellation, terminal uniqueness, in-flight cleanup |
| 02-03-01 | 2 | TEST-03, AI-01 | `uv run --locked --no-sync python -m pytest -q tests/providers/test_tools.py tests/characterization/test_mcp_parameters.py tests/characterization/test_mcp_result_formatting.py` | Neutral schemas plus preserved MCP parameter/result formatting |
| 02-03-02 | 2 | TEST-03, AI-01 | `uv run --locked --no-sync python -m pytest -q tests/providers/test_tools.py` | Provider-neutral catalog/executor wiring |
| 02-15-01 | 2 | TEST-05, OPS-02 | `uv run --locked --no-sync python -m pytest -q tests/test_dependency_audit.py` | Exact row-scoped decision: 16 OK conditionally approved, four SUS rejected, no direct manifest authority |
| 02-04-01 | 3 | TEST-03, AI-01, AI-02, AI-03 | `uv run --locked --no-sync python -m pytest -q tests/providers/test_openai_compatible.py` | Shared async transport, real incremental events, mapped failures |
| 02-04-02 | 3 | TEST-03, AI-01, AI-02, AI-03 | `uv run --locked --no-sync python -m pytest -q tests/providers/test_ollama.py` | Complete injected Ollama adapter without live service |
| 02-04-03 | 3 | TEST-03, AI-01, AI-02, AI-03 | `uv run --locked --no-sync python -m pytest -q tests/providers/test_openrouter.py` | Pre-stream/midstream failures produce no false completion |
| 02-05-01 | 3 | TEST-03, AI-01, AI-03 | `uv run --locked --no-sync python -m pytest -q tests/providers/test_gemini.py -k 'adapter or stream or failure or close'` | Lazy async Gemini adapter and cleanup |
| 02-05-02 | 3 | TEST-03, AI-01, AI-03 | `uv run --locked --no-sync python -m pytest -q tests/providers/test_gemini.py -k 'thinking or async or cancel'` | Thinking path contains no synchronous send or loop blocking |
| 02-06-01 | 4 | TEST-03, AI-01, AI-03 | `uv run --locked --no-sync python -m pytest -q tests/providers/test_factory.py` | One explicit lazy provider; unknown config fails closed |
| 02-06-02 | 4 | TEST-03, AI-01, AI-03 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_autonomic_provider.py` | Autonomic path cannot instantiate implicit Gemini |
| 02-07-01 | 5 | TEST-03, AI-03, OPS-01 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_lifecycle.py -k 'settings or order or partial or close'` | Pure settings, ordered ownership, reverse partial-start unwind |
| 02-07-02 | 5 | TEST-03, AI-03, OPS-01 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_lifecycle.py -k 'provider or cancel or shutdown or optional'` | Shutdown cancels/awaits local provider work and closes once |
| 02-08-01 | 6 | TEST-03, OPS-01 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_import_safety.py tests/api/test_local_boundary.py -k 'import or probe or wildcard or host'` | Import performs no client/db/process/filesystem/network work; boundary remains local |
| 02-08-02 | 6 | TEST-03, OPS-01 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_app_lifespan.py tests/api/test_local_boundary.py tests/api/test_filesystem_contract.py` | One lifespan-owned runtime and preserved filesystem/local contracts |
| 02-09-01 | 7 | TEST-03, AI-01, AI-03 | `uv run --locked --no-sync python -m pytest -q tests/conversation/test_analysis_transport.py` | Existing analyses use selected provider without prompt/schema redesign |
| 02-09-02 | 7 | TEST-03, AI-01, AI-03 | `uv run --locked --no-sync python -m pytest -q tests/api/test_provider_compatibility.py tests/characterization/test_companion_contract.py tests/characterization/test_persistence_contract.py tests/api/test_local_boundary.py` | Exact seven fields, HTTP-200 fallback, one session clear, persistence parity, no auth/loopback |
| 02-10-01 | 8 | TEST-03, OPS-01 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_health.py -k 'model or snapshot or redact or aggregate'` | Typed health truth and source/public error redaction |
| 02-10-02 | 8 | TEST-03, OPS-01 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_health.py` | Side-effect-free liveness/readiness/provider semantics |
| 02-11-01 | 9 | TEST-03, OPS-01 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_cli.py -k 'preflight or check or redaction or mutation'` | Non-mutating checks with exact ready/blocked/fail statuses |
| 02-11-02 | 9 | TEST-03, OPS-01 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_cli.py -k 'serve or signal or child or loopback'` | Canonical loopback serve, signal propagation, child cleanup |
| 02-12-01 | 10 | TEST-03, OPS-01 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_startup_entrypoints.py -k 'root or windows or linux'` | Root launchers delegate exactly and do not install/kill/broad-bind |
| 02-12-02 | 10 | TEST-03, OPS-01 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_startup_entrypoints.py -k 'backend or api or all'` | Backend wrappers delegate without environment activation/mutation |
| 02-12-03 | 10 | TEST-03, OPS-01 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_startup_entrypoints.py` | Frontend/MCP wrappers are explicit non-installing delegates |
| 02-16-01 | 10 | TEST-05, OPS-02 | `uv run --locked --no-sync python -m pytest -q tests/test_python_dependency_contract.py` | Digest-bound pre-edit gate plus exact 14-action Python authority/group/removal/Docker RED contract; four SUS rows immutable |
| 02-16-02 | 10 | TEST-05, OPS-02 | `uv lock --check && uv run --locked --no-sync python -m pytest -q tests/test_python_dependency_contract.py tests/test_dependency_audit.py tests/runtime/test_import_safety.py tests/characterization/test_companion_contract.py tests/characterization/test_persistence_contract.py` | Exact approved Python subset, mechanical lock-only consequences, one authority, supported paths retained, four SUS rows untouched |
| 02-13-01 | 11 | TEST-03, OPS-01 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_startup_docs.py tests/runtime/test_startup_entrypoints.py` | Docs match executable preflight/serve and truth boundaries |
| 02-13-02 | 11 | TEST-03, OPS-01 | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_startup_docs.py -k 'env or provider or loopback or secret'` | Non-secret local-first example config and explicit cloud selection |
| 02-17-01 | 11 | TEST-03, TEST-05, OPS-01, OPS-02 | `uv run --locked --no-sync python -m pytest tests/test_node_dependency_contract.py -q` | Digest-bound pre-edit gate plus exact two-action Node authority/import/script RED contract |
| 02-17-02 | 11 | TEST-03, TEST-05, OPS-01, OPS-02 | `uv run --locked --no-sync python -m pytest tests/test_node_dependency_contract.py -q && npm run typecheck:frontend && npm run build` | Exact Pyright addition and frontend SDK removal, static lock/script agreement plus existing frontend checks; actual Pyright runs only in 02-18 isolated clean CI |
| 02-18-01 | 12 | TEST-03, TEST-05, AI-01, AI-02, AI-03, OPS-01, OPS-02 | `uv run --locked --no-sync python -m pytest tests/live/test_ollama_ornith.py tests/runtime/test_baseline_evidence.py -q -m "live or not live" -rs` | Truthful default skip plus schema-checked baseline; explicit live is separately opt-in |
| 02-18-02 | 12 | TEST-03, TEST-05, AI-01, AI-02, AI-03, OPS-01, OPS-02 | `uv run --locked --no-sync python -m pytest tests/test_ci_contract.py -q` | CI pins/lanes/locks and adversarial false-success rejection |
| 02-18-03 | 12 | TEST-03, TEST-05, AI-01, AI-02, AI-03, OPS-01, OPS-02 | `uv run --locked --no-sync python -m pytest tests/test_ci_contract.py -q && uv run --locked --no-sync python -m pytest tests -q -m "not live" && uv run --locked --no-sync ruff check aura_backend tests --exclude aura_backend/archive_unused --exclude aura_backend/scratch --exclude aura_backend/tests && npm run typecheck:frontend && npm run build` | Complete locally available gate; CI contract enforces `npm ci` before Pyright, and only completed green clean-CI `typing-python` status proves that lane |

## Wave 0 Status

`wave_0_complete: true` means every missing Phase 2 test artifact has an owning TDD task that writes its RED contract before implementation, and the repository already has the locked pytest/pytest-asyncio harness and marker configuration needed to collect those tests. No task uses a `MISSING` verification reference, and no separate scaffold-only Wave 0 is necessary. This does not claim that future tests already pass; GREEN status remains owned by the exact task rows above.

The package-legitimacy seam has completed its human checkpoint: 02-14 created current machine-readable evidence and 02-15 recorded Ty's exact decision to conditionally approve the 16 OK rows and reject the four SUS rows. Revised Plans 02-16 and 02-17 independently require fresh evidence, exact decision/action sets, and matching pre-change manifest/lock digests before any edit. A stale, missing, widened, changed, or mismatched gate remains blocked and is never auto-approved or reported as success.

## Multi-Source Coverage Audit

| Source | Item | Disposition | Plan coverage |
|---|---|---|---|
| GOAL | A reliable provider/runtime path that keeps Aura locally runnable and preserves Phase 1 behavior | COVERED | 02-01 through 02-13, closed by 02-18 |
| REQ | TEST-03 — automated unit/integration coverage for provider/runtime behavior | COVERED | 02-01 through 02-13, 02-17, 02-18 |
| REQ | TEST-05 — CI build/lint/type checks | COVERED | 02-14 through 02-18 |
| REQ | AI-01 — pluggable LLM providers behind one interface | COVERED | 02-01, 02-03 through 02-06, 02-09, 02-18 |
| REQ | AI-02 — streaming where supported | COVERED | 02-02, 02-04, 02-18 |
| REQ | AI-03 — normalized provider failures and graceful fallback | COVERED | 02-01, 02-02, 02-04 through 02-07, 02-09, 02-18 |
| REQ | OPS-01 — supported documented one-command runtime entrypoint | COVERED | 02-07, 02-08, 02-10 through 02-13, 02-17, 02-18 |
| REQ | OPS-02 — single dependency declaration/lock model | COVERED | 02-14 through 02-18 |
| CONTEXT D-01 | Ollama is complete local provider; cloud only when explicitly selected | COVERED | 02-01, 02-04, 02-06, 02-11, 02-13, 02-18 |
| CONTEXT D-02 | One typed adapter-neutral contract for messages/tools/results/failures | COVERED | 02-01 through 02-06 |
| CONTEXT D-03 | True incremental streaming/cancellation with no unsupported upstream-stop claim | COVERED | 02-01, 02-02, 02-04, 02-05, 02-07, 02-18 |
| CONTEXT D-04 | Import-safe app and lifespan-owned runtime | COVERED | 02-07 through 02-11, 02-18 |
| CONTEXT D-05 | Dependency/startup repair is authoritative, evidence-gated, and not a broad upgrade | COVERED | 02-11 through 02-18 |
| CONTEXT D-06 | Verification is offline-first; Ornith and baseline are optional, bounded, and honest | COVERED | 02-02, 02-04, 02-13 through 02-18 |
| RESEARCH | Typed outcomes/config, source-safe errors, deterministic fake, runtime cancellation | COVERED | 02-01, 02-02 |
| RESEARCH | Neutral tools/MCP bridge and shared OpenAI-compatible Ollama/OpenRouter transport | COVERED | 02-03, 02-04 |
| RESEARCH | Async Gemini, lazy factory, no implicit autonomic Gemini | COVERED | 02-05, 02-06 |
| RESEARCH | Runtime ownership, import safety, create_app/lifespan, route/analysis preservation | COVERED | 02-07 through 02-09 |
| RESEARCH | Honest health, non-mutating preflight, canonical serve and thin wrappers/docs/env | COVERED | 02-10 through 02-13 |
| RESEARCH | Current legitimacy/import/entrypoint audit, blocking approval, Python/Node lock authority, Docker lane | COVERED | 02-14 through 02-17 |
| RESEARCH | Optional Ornith live check, baseline-only evidence, pinned CI truth lanes | COVERED | 02-18 |

Excluded without a gap: Phase 3 storage migration/cleanup, Phase 4 prompt-quality redesign, Phase 5 frontend refactor, broad dependency upgrades, authentication, real user data, deployment work, and Git-history changes. These are deferred or explicitly outside Phase 2 and appear in no implementation task.

## Manual and Environment-Dependent Verification

| Item | Why it cannot be ordinary deterministic proof | Success rule |
|---|---|---|
| 02-15 package legitimacy/disposition checkpoint | Package evidence contained 16 OK and four SUS rows; policy required an explicit row-scoped human decision | Completed: only the 16 OK rows were conditionally approved, all four SUS rows rejected, and revised downstream plans must still pass independent digest/freshness/scope gates |
| Optional `ornith:latest` live lane | Requires a running local Ollama service and installed 5.6 GB model | Separately reported; precise preflight block/skip is honest, but any post-preflight non-success fails |

## Validation Sign-Off

- [x] All 38 tasks have one exact automated command and an owning test/evidence artifact.
- [x] All seven Phase 2 requirement IDs appear in plan frontmatter and this matrix.
- [x] D-01 through D-06 have cited implementation coverage; no deferred idea is planned.
- [x] No three consecutive tasks lack automated verification.
- [x] Deterministic and live/environment-blocked evidence are separated.
- [x] Adversarial false-success and public/logged error-redaction checks are explicit.
- [x] Wave 0 has no missing scaffold or unowned reference.
- [x] Final phase proof preserves Phase 1 response, fallback, persistence/session, and local-boundary contracts.

**Approval:** ready for execution. Plan 02-15's human checkpoint is complete; Plans 02-16 and 02-17 remain fail-closed until their independent pre-edit digest, freshness, decision, and exact-action gates pass.
