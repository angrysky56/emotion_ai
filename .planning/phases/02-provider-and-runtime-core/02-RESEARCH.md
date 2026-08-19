# Phase 2: Provider and Runtime Core - Research

**Researched:** 2026-08-19
**Domain:** Async model-provider adapters, application lifecycle, local startup, dependency authority, and verification lanes
**Confidence:** HIGH for current code/runtime evidence; MEDIUM-HIGH for the recommended refactor because cancellation beyond the client connection is not guaranteed by every upstream provider

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

## Implementation Decisions

### D-01 — Local-first provider behavior

- Ollama is a complete first-class provider, not a fallback demo.
- `ornith:latest` is the preferred bounded live-test model when installed, but no deterministic test may require Ollama or any network service.
- Cloud providers remain supported when explicitly configured; Aura must have no silent cloud dependency.

### D-02 — Provider contract and failures

- Conversation orchestration consumes one small typed provider interface and must not branch on provider names or SDK response types.
- Normal, streamed, malformed, timeout, cancellation, missing-model, unavailable-service, and provider-auth failures require distinct typed outcomes.
- Resource limits, unavailable services, malformed output, and partial streams may not be reported as successful completed answers.
- Raw provider exceptions, credentials, prompts, and conversation content must not leak through public health/error responses or default logs.

### D-03 — Streaming and cancellation

- Streaming is a real incremental contract with deterministic fake coverage; it must not be implemented by buffering a full response and replaying chunks.
- Client cancellation and shutdown must stop provider work promptly and clean up sessions/resources without converting cancellation into a fallback success.
- The existing non-streaming conversation path remains functional throughout the refactor.

### D-04 — Runtime lifecycle

- Importing `aura_backend.main` or provider modules must not construct model clients, connect to services, scan/download models, start subprocesses, or open databases.
- One explicit application/runtime factory owns initialization and shutdown.
- Health distinguishes process liveness, application readiness, and optional provider availability; an unavailable optional cloud provider must not make a valid local-only runtime dishonest.
- Aura remains loopback-first with no mandatory sign-in.

### D-05 — Startup and dependencies

- Provide one documented cross-platform startup/preflight entry point; it reports missing dependencies, occupied port, unwritable storage, and unavailable selected model with actionable redacted messages and never installs software implicitly.
- `pyproject.toml` plus `uv.lock` are the authoritative Python dependency path; `package.json` plus its lockfile are authoritative for Node.
- GPU-heavy and optional provider/tool capabilities belong in explicit optional groups and may not burden the base local runtime without evidence they are needed.
- Reconcile manifests against actual imports before removing or moving dependencies; do not perform broad speculative upgrades in this phase.

### D-06 — Verification lanes

- The root deterministic suite uses provider fakes and stays offline.
- Live Ollama/Ornith checks are explicitly marked, bounded by timeouts, skip with a truthful environment reason when unavailable, and report failures separately.
- CI/reporting must keep deterministic tests, live-model checks, lint, typing, frontend build, and environment-blocked lanes distinct.
- Performance claims require captured startup and provider-latency measurements; this phase may record baselines but must not claim optimization from anecdotes.

### Codex's Discretion

- Exact module names and class decomposition inside the provider/runtime boundary.
- Whether the Ollama adapter uses the native API or supported OpenAI-compatible API, based on current official behavior and the cleanest streaming/cancellation contract.
- Exact CLI framework and health payload field names, provided the contracts above are typed, tested, and documented.

### Deferred Ideas (OUT OF SCOPE)

- Chroma root ownership, FK repair, storage consolidation, export, deletion, and tracked-data removal are Phase 3.
- Emotion/reflection quality evaluation and prompt redesign are Phase 4.
- Frontend modularization and browser experience are Phase 5.
- Broad performance optimization and final packaging are Phase 6.
- Remote Git-history rewriting remains separately approved and out of scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TEST-03 | Backend API contracts, filesystem containment, persistence, provider translation, and failure behavior require automated tests. | Typed failure taxonomy, adapter contract tests, Phase 1 compatibility gates, import-safety probes, and route-level fallback tests below. [VERIFIED: `.planning/REQUIREMENTS.md`; local tests] |
| TEST-05 | CI must separately report deterministic tests, optional live Ollama checks, builds, linting, typing, and environment-blocked checks. | Separate job/lane design and exact commands below; the repository currently has no workflow files. [VERIFIED: `.planning/REQUIREMENTS.md`; `.github` inventory] |
| AI-01 | A small typed provider contract supports Ollama, Gemini, and OpenRouter without provider-specific logic in conversation orchestration. | `Provider` protocol, typed request/result/event types, neutral tool catalog, and provider-runtime ownership below. [VERIFIED: local provider call-path audit] |
| AI-02 | Ollama works locally through its supported OpenAI-compatible or native API with explicit timeouts, cancellation, streaming, and error mapping. | Use the official OpenAI-compatible chat/model APIs with explicit HTTP timeouts, zero hidden SDK retries, true stream consumption, and typed mapping. [CITED: https://docs.ollama.com/api/openai-compatibility] |
| AI-03 | Deterministic provider fakes cover normal, streaming, malformed, timeout, and unavailable-model behavior; live Ornith tests are optional and marked. | Fake scripts, stream state-machine cases, `asyncio.timeout()` live bound, truthful skip rules, and installed-model evidence below. [VERIFIED: local pytest configuration and `ollama list`] |
| OPS-01 | One cross-platform documented startup path performs dependency, model, port, storage, and health preflight checks without installing software via an opaque startup side effect. | Standard-library CLI, `--no-sync` startup, preflight result model, and replacement of mutating shell/batch behavior below. [VERIFIED: local launcher audit] |
| OPS-02 | Python and Node dependency manifests have one authoritative lock path each; GPU-only and optional capabilities do not burden the base install. | Manifest drift inventory, dependency-group recommendations, lock checks, and Docker/launcher reconciliation below. [VERIFIED: `pyproject.toml`, `uv.lock`, `requirements.txt`, `package.json`, `package-lock.json`, import scan] |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Explain outcomes in concise, plain language for a technically literate non-coder; report failures as directly as successes. [VERIFIED: prompt-provided AGENTS instructions]
- Research current solutions before selecting packages or creating manifests; do not reinvent solved infrastructure. [VERIFIED: prompt-provided AGENTS instructions]
- Prefer TypeScript and `uv`, write changes to files/scripts, and use docstrings, type hints, comments, and a virtual environment. [VERIFIED: prompt-provided AGENTS instructions]
- Keep this project self-contained; never wire another project into it by filesystem path. [VERIFIED: prompt-provided AGENTS instructions]
- Ask before sudo or large-package installation. [VERIFIED: prompt-provided AGENTS instructions]
- The target is Pop!_OS with an RTX 3060 12 GB and 64 GB RAM, but cross-platform startup remains a locked phase requirement. [VERIFIED: prompt-provided AGENTS instructions; `02-CONTEXT.md`]
- No repository `AGENTS.md` file and no project-local `rules/*.md` or project skill were found; these prompt-provided constraints are therefore the applicable project instructions. [VERIFIED: local file inventory]

## Summary

Aura already has the outline of a provider abstraction, but the current boundary is not reliable. All three `stream_response()` implementations first await the complete response and then yield it once; provider exceptions become nominal `ProviderResponse` values containing raw exception text; Ollama and OpenRouter clients use the OpenAI SDK's long default timeout and hidden retry policy; and Gemini performs synchronous `chat.send_message()` calls inside async functions. [VERIFIED: `aura_backend/providers/{base,ollama,openrouter,gemini}.py`; `aura_backend/thinking_processor.py`] The conversation route also calls three Gemini-client-specific analysis functions after the main provider call, so an Ollama-selected request is not actually provider-neutral. [VERIFIED: `aura_backend/main.py:905-1215,1534-1773`]

The safest implementation is an incremental extraction, not a rewrite: strengthen the existing provider types; share one OpenAI-compatible async transport between Ollama and OpenRouter; convert Gemini to the official `client.aio` API; add a small `ProviderRuntime` that owns provider startup, in-flight cancellation, and shutdown; and make the existing FastAPI lifespan own all resource construction in one place. [CITED: https://github.com/openai/openai-python; https://googleapis.github.io/python-genai/; https://fastapi.tiangolo.com/advanced/events/] Keep the seven-field `/conversation` response, HTTP-200 fallback, session clear on provider failure, immediate persistence arguments, loopback/CORS defaults, and no-auth model exactly as Phase 1 characterized them. [VERIFIED: `.planning/phases/01-preservation-and-trusted-baseline/01-VERIFICATION.md`; `01-05-SUMMARY.md`; `01-07-SUMMARY.md`]

Use Ollama's official OpenAI-compatible API, not a new Ollama client package. It supports chat completions, streaming, tools, JSON responses, and model listing; Aura already locks the official OpenAI Python client used for OpenRouter, so this choice removes duplicate translation and dependency risk. [CITED: https://docs.ollama.com/api/openai-compatibility] The reviewed Ollama API pages do not promise that disconnecting a client always halts model computation, and OpenRouter explicitly says cancellation support depends on the underlying provider. Aura can guarantee prompt local task cancellation, stream closure, and no false success; it must not claim guaranteed upstream compute/billing cancellation. [CITED: https://docs.ollama.com/api/streaming; https://openrouter.ai/docs/guides/features/streaming]

**Primary recommendation:** Build a typed, lifecycle-owned `ProviderRuntime` around the existing adapters, use one OpenAI-compatible transport for Ollama/OpenRouter, use Gemini's async client, preserve Phase 1's public contract, and prove the change in offline fake/import/lifespan lanes before running a bounded optional `ornith:latest` check.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Provider configuration and selection | API / Backend | — | Credentials, model selection, timeout policy, and provider construction must not enter browser code. [VERIFIED: current env-based factory; D-02/D-04] |
| Conversation orchestration | API / Backend | Database / Storage | The route/service builds the provider-neutral request; persisted memory supplies context without the adapter knowing storage details. [VERIFIED: current `process_conversation()` call path; Phase 3 boundary] |
| Model transport and stream translation | API / Backend | External provider boundary | Adapters normalize SDK chunks/errors and never leak SDK types upward. [CITED: official Ollama/OpenAI/Google/OpenRouter APIs] |
| Session cancellation and cleanup | API / Backend | External provider boundary | Aura owns tasks and client closure; upstream work cancellation is best-effort where providers do not guarantee it. [CITED: https://openrouter.ai/docs/guides/features/streaming] |
| Liveness/readiness/provider health | API / Backend | External provider boundary | Liveness is process-local; readiness checks required initialized resources; provider availability is independently reported. [VERIFIED: D-04; current health implementation] |
| Startup/preflight | API / Backend | OS / external service | A Python entry point can check executables, port, storage, selected model, and app readiness consistently on Linux and Windows. [VERIFIED: current shell/batch divergence; D-05] |
| Browser stream rendering | Browser / Client | API / Backend | A public streaming endpoint and UI consumption are Phase 5; Phase 2 establishes the backend iterator contract only. [VERIFIED: ROADMAP phase boundaries] |
| Persistence/storage ownership | Database / Storage | API / Backend | Existing persistence remains untouched except for lifecycle construction; consolidation and migration are Phase 3. [VERIFIED: ROADMAP and STATE] |
| Authentication | — | — | Aura retains its no-sign-in local trust model; loopback and explicit LAN opt-in remain the security boundary. [VERIFIED: D-04; Phase 1 verification] |

## Current System Evidence

### Exact provider, session, and error paths

1. `process_conversation()` creates only one `Message(role="user", ...)`, then invokes the global `provider.generate_response(...)` with `session_key = "{user_id}_{session_id}"`. [VERIFIED: `aura_backend/main.py:1671-1691`]
2. `GeminiProvider` keeps hidden SDK chat objects in `_chat_sessions`; Ollama and OpenRouter are stateless and their `clear_session()` methods do nothing. Provider behavior therefore changes with the selected adapter even though orchestration uses the same method. [VERIFIED: `aura_backend/providers/gemini.py:58-75,128-145`; `ollama.py:217-221`; `openrouter.py:244-248`]
3. The route unwraps `provider_response.content`, `thoughts`, and `raw_response`, then performs user-emotion, Aura-emotion, and cognitive-focus calls through a global `client.models.generate_content()`. Under Ollama/OpenRouter, `client` is an `AsyncOpenAI`, not a Gemini client, and those functions catch the resulting error and silently return defaults/`None`. [VERIFIED: `aura_backend/main.py:972-1018,1083-1129,1194-1215,1686-1773`]
4. Ollama/OpenRouter manually execute tools, but return max-turn exhaustion and exceptions as normal `ProviderResponse` objects whose content/error fields contain provider text. Tool errors likewise return `"Error: {exception}"` strings. [VERIFIED: `aura_backend/providers/ollama.py:119-200`; `openrouter.py:129-226`]
5. All adapters implement fake streaming by awaiting `generate_response()` and yielding once. No HTTP route currently consumes the streaming method. [VERIFIED: `aura_backend/providers/{ollama,openrouter,gemini}.py`; route inventory]
6. The route converts provider error/empty output into the Phase 1 fallback `ConversationResponse`, clears the provider session, and returns HTTP 200. Phase 1 tests require exactly one clear call and prove the raw provider error is absent from the response. [VERIFIED: `aura_backend/main.py:1986-2028`; `tests/characterization/test_companion_contract.py`]
7. In the installed Python 3.12 runtime, `asyncio.CancelledError` derives from `BaseException`, not `Exception`, so current broad `except Exception` blocks do not catch direct task cancellation. They still lack explicit stream closure and provider-resource cleanup. [VERIFIED: local Python introspection; current exception handlers]

### Exact import and lifecycle path

- `aura_backend.main` calls `load_dotenv()`, reads/logs thinking configuration, creates the shared embedding singleton, imports provider factory plus Chroma/MCP/Memvid/autonomic modules, and creates the FastAPI app at import time. The embedding weights are lazy, but importing `sentence_transformers`/Torch is not. [VERIFIED: `aura_backend/main.py:14-115`; `aura_backend/shared_embedding_service.py:11-60`]
- An isolated import probe on this machine took **6.70 s** and **1,110,152 KiB maximum RSS**, while `providers.base` took **0.03 s / 18,544 KiB** and `providers.factory` took **1.60 s / 118,708 KiB**. These are single baseline samples, not optimization claims. [VERIFIED: `/usr/bin/time` probes on 2026-08-19]
- The current lifespan starts database protection first, then opens the robust Chroma wrapper, filesystem/state/tools, MCP subprocess clients, provider, persistence, Memvid, and autonomic workers. Shutdown stops autonomic, MCP, vector DB, and database protection, but does not close OpenAI/Google provider clients or explicitly clear provider sessions. [VERIFIED: `aura_backend/main.py:1218-1347`]
- `ThinkingProcessor` calls synchronous `chat.send_message()` at three points from async methods, which can block the event loop for the entire model request. [VERIFIED: `aura_backend/thinking_processor.py:95,244,376`; official async client surface at https://googleapis.github.io/python-genai/]
- `/health` reports `status: operational`, calls the filesystem operational, and treats the existence of a `vector_db.client` attribute as connectivity; its catch path returns raw `str(e)`. It does not represent liveness, readiness, or selected-provider availability. [VERIFIED: `aura_backend/main.py:1433-1531`]

### Exact startup and manifest drift

- `start_full_system.sh` may install `uv` with `curl`, create an environment, run `uv sync`, run `npm install`, create an `.env`, `chmod` scripts, and kill any process occupying ports 8000/5173. `start_full_system.bat` has different behavior and starts Uvicorn on `0.0.0.0` with reload. Both violate the locked non-mutating, loopback-first preflight contract. [VERIFIED: local launcher scripts]
- `pyproject.toml`/`uv.lock` currently resolve and `uv lock --check` passes, while `requirements.txt` is a contradictory second Python resolution path. Examples include locked `openai==1.86.0` versus `requirements.txt` 2.34, and locked `anthropic==0.54.0` versus 0.99. [VERIFIED: local manifests/lock and registry inspection]
- The checked-in Dockerfile installs `requirements.txt` with pip and starts `python main.py`, so it is coupled to the contradictory path rather than the locked project. [VERIFIED: `aura_backend/Dockerfile`]
- `package.json`/`package-lock.json` are consistent (`npm ls --depth=0` exited 0), but `@google/genai` has no active TypeScript import and can be removed after a clean build. `marked` is actively imported by `index.tsx`. [VERIFIED: source import scan and npm tree]
- No GitHub Actions workflow exists. `package.json` has only `dev`, `build`, and `preview`; Python has Pyright and Ruff configuration but neither tool is declared in an authoritative dependency group. [VERIFIED: `.github` inventory; local manifests]

## Architecture Patterns

### System Architecture Diagram

```mermaid
flowchart TD
    CLI[python -m aura_backend.runtime preflight/serve]
    Factory[create_app + FastAPI lifespan]
    Runtime[ApplicationRuntime]
    Health[/live, /ready, /health/providers]
    Route[/conversation existing JSON contract]
    Service[Conversation orchestration]
    PR[ProviderRuntime]
    Sessions[In-flight session/cancellation registry]
    Tools[Neutral MCP tool catalog/executor]
    P[Typed Provider protocol]
    OA[OpenAICompatibleProvider]
    G[GeminiProvider using client.aio]
    O[Ollama /v1]
    OR[OpenRouter /api/v1]
    GA[Gemini API]
    Store[Existing persistence and memory]

    CLI -->|validated settings| Factory
    Factory -->|start/close| Runtime
    Runtime --> Health
    Runtime --> PR
    Runtime --> Store
    Route --> Service
    Service -->|ProviderRequest only| PR
    Service --> Store
    PR --> Sessions
    PR --> P
    P --> OA
    P --> G
    OA --> O
    OA --> OR
    G --> GA
    P --> Tools
    O -. timeout/error/stream .-> P
    OR -. timeout/error/stream .-> P
    GA -. timeout/error/stream .-> P
    P -->|TextDelta* then Completed OR one typed failure| Service
```

The application factory is the only composition root. Provider adapters do not import storage or FastAPI, routes do not inspect provider names or SDK objects, and provider-neutral tools enter through one catalog/executor interface. [VERIFIED: D-02/D-04; current coupling audit]

### Recommended Project Structure

```text
aura_backend/
├── main.py                         # existing routes/models; thin create_app composition
├── providers/
│   ├── base.py                     # Provider Protocol and immutable domain types
│   ├── errors.py                   # ProviderErrorCode and safe ProviderFailure
│   ├── config.py                   # selected-provider settings validation
│   ├── runtime.py                  # lifecycle, cancellation, health, session cleanup
│   ├── openai_compatible.py        # shared Ollama/OpenRouter transport and stream assembly
│   ├── ollama.py                   # endpoint/model policy only
│   ├── openrouter.py               # headers plus in-stream error policy only
│   ├── gemini.py                   # google-genai aio translation only
│   └── fake.py                     # scripted deterministic fake, test-only or reusable support
├── runtime/
│   ├── app.py                      # ApplicationRuntime and ordered start/close
│   ├── config.py                   # application settings; pure parsing/validation
│   ├── health.py                   # liveness/readiness/provider DTOs
│   ├── cli.py                      # argparse preflight/serve entry point
│   └── __main__.py                 # python -m aura_backend.runtime
└── conversation/
    └── analysis.py                 # minimal provider-neutral versions of current 3 analyses

tests/
├── providers/                      # protocol, adapters, stream/error/cancellation
├── runtime/                        # import effects, lifespan, health, CLI preflight
├── api/                            # Phase 1 plus non-streaming compatibility
└── live/test_ollama_ornith.py      # marked, bounded, optional
```

This is an incremental seam map, not permission to split every route or redesign prompts. Keep `main.py` route bodies and Phase 1 test seams working while moving construction and model transport first. [VERIFIED: Phase boundaries and Phase 1 tests]

### Component and symbol targets

| Target | Required change | Boundary guard |
|--------|-----------------|----------------|
| `providers/base.py::{BaseProvider,ProviderResponse,Message}` | Replace/augment with a small `Provider` `Protocol`, frozen request/result DTOs, and stream-event union; retain temporary compatibility aliases if Phase 1 fakes need them. | No SDK imports or raw response field in the stable result. [VERIFIED: current types expose `Any raw_response`] |
| `providers/errors.py` (new) | Define safe codes: `configuration`, `authentication`, `unavailable`, `model_not_found`, `rate_limited`, `timeout`, `malformed_response`, `resource_limit`, `stream_interrupted`, and `cancelled`. | Safe public message and provider/status metadata only; original exception remains chained for internal debugging, never serialized/logged by default. [VERIFIED: D-02] |
| `providers/openai_compatible.py` (new) | Own `AsyncOpenAI`, message/tool conversion, explicit timeout/retry settings, normal/stream calls, tool-delta assembly, OpenRouter in-stream errors, and `aclose()`. | Ollama/OpenRouter subclasses contain no duplicate loop and no public raw SDK object. [CITED: https://github.com/openai/openai-python] |
| `providers/ollama.py` | Supply local base URL/model and model-list readiness check using `/v1/models`; map 404 to `model_not_found`. | Never pull/download a model; no API key is needed by Ollama even though the OpenAI SDK parameter is syntactically required. [CITED: https://docs.ollama.com/api/openai-compatibility] |
| `providers/openrouter.py` | Supply URL/headers and detect documented post-start stream error payloads. | A partial stream followed by an error never emits `Completed`. [CITED: https://openrouter.ai/docs/api/reference/errors-and-debugging] |
| `providers/gemini.py` and `thinking_processor.py` | Use `client.aio`, async chats/stream methods, typed Google errors, and `await client.aio.aclose()`; remove sync sends from event-loop paths. | No hidden `_chat_sessions`; no raw thought/SDK response in stable result. [CITED: https://googleapis.github.io/python-genai/] |
| `providers/factory.py::ModelProviderFactory` | Parse a validated selected provider, import only that adapter inside the branch, and fail unknown values instead of silently constructing Gemini. | Default local config is Ollama; cloud requires explicit provider plus credential. [VERIFIED: D-01; current silent fallback] |
| `providers/runtime.py::ProviderRuntime` | Own selected adapter, neutral tool preparation, in-flight task handles, `generate`, `stream`, `clear_session`, `health`, and reverse-order `aclose`. | Re-raise `CancelledError` after cleanup; never transform it into a conversation success. [VERIFIED: D-03] |
| `mcp_system.py` / `mcp_to_gemini_bridge.py` | Expose neutral MCP schemas and execution independently of Gemini; retain Gemini conversion only inside `GeminiProvider`. | Conversation orchestration must not use `MCPGeminiBridge` or its private mapping. [VERIFIED: current main path at `1637-1663`] |
| `main.py::{lifespan,process_conversation,health_check}` | Delegate construction/close to `ApplicationRuntime`, take provider runtime from `app.state`, preserve response/persistence/fallback behavior, and expose honest health endpoints. | Transitional globals may alias runtime resources for untouched routes, but nothing constructs them at import. [VERIFIED: safe incremental seam analysis] |
| `main.py::{detect_user_emotion,detect_aura_emotion,detect_aura_cognitive_focus}` | Call the selected provider through the same typed request or a thin provider-neutral analysis service; preserve current prompts/parsers/defaults. | Prompt redesign and emotion-quality claims stay Phase 4. [VERIFIED: current Gemini-only calls; ROADMAP] |
| `aura_autonomic_system.py` | Do not construct Gemini implicitly. Default local runtime leaves this optional subsystem disabled until explicitly configured with a compatible provider path, or inject the selected provider if the existing behavior can be preserved. | An Ollama-selected runtime may never create a cloud client as a side effect. [VERIFIED: `aura_autonomic_system.py:608-614`; D-01] |
| `runtime/cli.py` (new), launch scripts | One `argparse` preflight/serve implementation; shell/batch wrappers only delegate. | No install, sync, download, `.env` creation, chmod, port killing, or `--reload`. [VERIFIED: D-05; launcher audit] |
| `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`, Dockerfile | Create explicit dependency groups, remove contradictory install paths/import-unused direct deps, add scripts, and regenerate both locks once. | Keep current resolved runtime versions; no broad upgrade. [VERIFIED: D-05 and manifest drift] |

### Pattern 1: Typed provider outcomes, not error-bearing successes

**What:** A successful call returns a `ProviderResult`; every unsuccessful terminal state raises a safe typed `ProviderFailure`; cancellation propagates as `asyncio.CancelledError` while the runtime records code `cancelled` for health/metrics. [VERIFIED: D-02/D-03]

**Recommended shape:**

```python
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True, slots=True)
class ProviderRequest:
    messages: tuple[Message, ...]
    system_instruction: str | None = None
    tools: tuple[ToolDefinition, ...] = ()
    temperature: float = 0.7
    max_tokens: int | None = None
    session_id: str | None = None

@dataclass(frozen=True, slots=True)
class ProviderResult:
    content: str
    usage: ProviderUsage | None = None
    reflection_summary: str | None = None  # never raw hidden reasoning

type StreamEvent = TextDelta | ToolCallDelta | Completed

class Provider(Protocol):
    async def generate(self, request: ProviderRequest) -> ProviderResult: ...
    def stream(self, request: ProviderRequest) -> AsyncIterator[StreamEvent]: ...
    async def clear_session(self, session_id: str) -> None: ...
    async def health(self) -> ProviderHealth: ...
    async def aclose(self) -> None: ...
```

This is a project-domain recommendation derived from the locked contract; it intentionally excludes `raw_response: Any`. [VERIFIED: D-02 and current raw-response leak surface]

### Pattern 2: One explicit stream state machine

**What:** The stream begins in `OPEN`, may emit zero or more `TextDelta`/tool-delta events, and ends exactly once with `Completed`; error, timeout, malformed chunk, resource limit, or cancellation closes it without a completed event. [VERIFIED: D-02/D-03]

```text
OPEN ──text/tool delta──> OPEN
OPEN ──valid finish─────> COMPLETED
OPEN ──provider error───> FAILED
OPEN ──deadline─────────> TIMED_OUT
OPEN ──caller cancel────> CANCELLED

Only COMPLETED is a successful answer.
```

For OpenAI-compatible tool streams, accumulate tool-call IDs/names/JSON argument fragments by index, validate the finished argument object, execute the tool once, append its result, and begin the next bounded provider turn. Do not expose incomplete JSON as a tool call. [CITED: https://github.com/openai/openai-python; https://docs.ollama.com/api/openai-compatibility]

### Pattern 3: Explicit timeout/retry ownership

The installed OpenAI client defaults to two retries and a ten-minute timeout. Set `max_retries=0` and an explicit `httpx.Timeout(connect=..., read=..., write=..., pool=...)`; then put the single retry/deadline policy in `ProviderRuntime`. [CITED: https://github.com/openai/openai-python#retries; https://github.com/openai/openai-python#timeouts] This avoids multiplying SDK retries by Aura's tool/session retry loops. Use the current non-streaming path's chosen finite deadline as configuration, and use shorter independent readiness/model-list timeouts. [VERIFIED: current retry/tool-loop audit]

The Google client accepts timeout configuration through `HttpOptions` and exposes async close through `client.aio`; use the same Aura-level deadline categories even though the SDK exception classes differ. [CITED: https://googleapis.github.io/python-genai/]

### Pattern 4: Adapter-stateless model history

Provider adapters should not retain hidden SDK chat sessions. The current route's persisted-memory context remains the continuity input during Phase 2, and `session_id` becomes a correlation/cancellation/cleanup key rather than a provider-specific history implementation. [VERIFIED: current one-message request plus memory-context behavior; Phase 3 storage boundary] This resolves the parity question without inventing a second persistence owner; richer ordered-history semantics belong with Phase 3/4 and must be characterized before addition. [VERIFIED: ROADMAP]

### Pattern 5: Lifespan-owned resources and app factory

FastAPI recommends lifespan for resources that are shared across requests and must be cleaned up; its `TestClient` must be used as a context manager when tests need lifespan events. [CITED: https://fastapi.tiangolo.com/advanced/events/; https://fastapi.tiangolo.com/advanced/testing-events/]

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = app.state.runtime_builder()
    app.state.runtime = runtime
    try:
        await runtime.start()
        yield
    finally:
        await runtime.aclose()

def create_app(runtime_builder: RuntimeBuilder = build_runtime) -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.state.runtime_builder = runtime_builder
    install_routes_and_local_middleware(app)
    return app

# Compatibility for existing imports; construction is pure and resource-free.
app = create_app()
```

Start in dependency order and close in strict reverse order. If any startup stage fails, close only resources already started before returning a typed readiness/startup failure. [VERIFIED: current partial-start leak risk; D-04]

### Pattern 6: Honest three-level health

| Endpoint | Meaning | Network work | Failure status |
|----------|---------|--------------|----------------|
| `/live` | Python process/event loop can serve a tiny request. | None. | 200 unless process cannot serve. [VERIFIED: D-04] |
| `/ready` | Application runtime started and required local resources plus the selected provider/model passed bounded checks. | Cached status by default; explicit refresh may be bounded. | 503 when required runtime/selected model is unavailable. [VERIFIED: D-04/D-05] |
| `/health/providers` | Selected and configured optional provider state, with safe code and last-check time. | Bounded checks only; never sends a prompt. | 200 diagnostic payload; unselected cloud is `not_configured`, not a runtime failure. [VERIFIED: D-04] |

Retain `/health` as a compatibility composite during this phase, but make its status derive from runtime readiness and remove raw error strings. [VERIFIED: current consumers and D-02] Provider/model checks must use listing/metadata endpoints, never a generation request, so health cannot spend cloud money or expose content. [CITED: https://docs.ollama.com/api/tags; https://docs.ollama.com/api/openai-compatibility]

### Pattern 7: Cross-platform non-mutating preflight

Use the Python standard library `argparse`, `shutil.which`, `socket`, `pathlib`, and the locked HTTP client. This needs no new runtime package. [VERIFIED: Python standard library and locked `httpx`]

The canonical commands should be:

```bash
uv run --locked --no-sync python -m aura_backend.runtime preflight
uv run --locked --no-sync python -m aura_backend.runtime serve
```

`--no-sync` is essential: `uv run` otherwise checks/synchronizes the environment before running; `--locked` alone only prevents lock changes. [CITED: https://docs.astral.sh/uv/concepts/projects/sync/]

Preflight returns one structured result per check: Python/uv/Node/npm presence and version, lock freshness, configured provider credential requirement, port free, storage roots present/writable, selected Ollama endpoint reachable, selected model listed, and application readiness. It prints remediation commands but never executes them. [VERIFIED: D-05] A busy port is a failure naming the port; it is never authorization to kill an unrelated process. [VERIFIED: current launcher risk and D-05]

### Anti-Patterns to Avoid

- **Error-as-content:** A string beginning with `Error:` is not a successful assistant answer. Raise a typed failure and let the existing route map it to its pinned fallback. [VERIFIED: D-02; current adapters]
- **Catch-all around cancellation:** Do cleanup in `finally`; explicitly re-raise `CancelledError`. Never return the fallback from a cancelled streaming task. [VERIFIED: D-03]
- **Buffered fake streaming:** Do not split an already completed response into chunks. Tests must prove the consumer receives the first delta before the fake/provider is allowed to complete. [VERIFIED: D-03]
- **Raw SDK objects above adapters:** `raw_response` couples the route to Gemini-specific attributes and makes accidental serialization/logging possible. Normalize usage and safe reflection fields inside each adapter. [VERIFIED: current route at `1700-1723,1964-1975`]
- **Provider-name branching in routes:** Selection happens once in the factory/runtime; orchestration only sees the protocol. [VERIFIED: D-02]
- **Eager adapter imports:** A factory that imports Gemini, Ollama, and OpenRouter at module load preserves the current import penalty and makes optional dependency groups impossible. [VERIFIED: `providers/factory.py:10-13`]
- **Silent Gemini fallback:** Unknown provider configuration must fail preflight/startup with `configuration`, never spend cloud resources. [VERIFIED: current `factory.py:66-74`; D-01]
- **Unbounded hidden SDK retries:** SDK retry/timeouts plus Aura loops can make cancellation and latency unknowable. [CITED: https://github.com/openai/openai-python#retries]
- **Raw content logging:** Remove answer previews (currently up to 100,000 characters), raw tracebacks, prompts, tool arguments/results, and provider exception strings from default logs. Log correlation ID, safe code, provider kind, duration, and counts. [VERIFIED: `main.py:1705-1723`; current adapters; D-02]
- **Health as initialization-by-probe:** Health must not initialize a model, open Chroma, start MCP, or send a generation request. [VERIFIED: D-04]
- **Startup as installer/process manager:** No curl installer, implicit `uv sync`/`npm install`, `.env` writing, port killing, terminal emulator discovery, or reload mode. [VERIFIED: D-05 and launcher audit]

## Standard Stack

### Core (retain the lock; do not upgrade in this phase)

| Library/runtime | Verified version | Publish/observation date | Purpose | Why standard here |
|-----------------|------------------|--------------------------|---------|-------------------|
| Python | 3.12.9 | observed 2026-08-19 | Backend runtime and CLI | Project requires Python >=3.12 and the existing venv uses 3.12.9. [VERIFIED: local runtime; `pyproject.toml`] |
| FastAPI | 0.136.1 | published 2026-04-23 | ASGI API and lifespan | Existing API contract and official lifespan/test support. [VERIFIED: PyPI registry and local environment; CITED: https://fastapi.tiangolo.com/advanced/events/] |
| Starlette | 1.0.0 | published 2026-03-22 | ASGI/test foundation | Locked transitive runtime used by FastAPI/TestClient; retain exact lock. [VERIFIED: PyPI registry and local environment] |
| Uvicorn | 0.46.0 | published 2026-04-23 | Local ASGI server | Supports app factories, lifespan, loopback host settings, and graceful-shutdown timeout. [VERIFIED: PyPI registry/local environment; CITED: https://www.uvicorn.org/settings/] |
| OpenAI Python | 1.86.0 | published 2025-06-10 | Shared async OpenAI-compatible transport for Ollama/OpenRouter | Existing locked client supports `AsyncOpenAI`, streaming, typed errors, close/context management. [VERIFIED: local API introspection/registry; CITED: https://github.com/openai/openai-python] |
| google-genai | 1.75.0 | published 2026-05-04 | Explicit Gemini adapter only | Existing official Google SDK exposes async APIs and close. Keep optional/lazy. [VERIFIED: registry/local environment; CITED: https://googleapis.github.io/python-genai/] |
| HTTPX | 0.28.1 | published 2024-12-06 | Explicit timeout objects and preflight HTTP | Already locked and used beneath the OpenAI client. [VERIFIED: registry/local environment; CITED: https://github.com/encode/httpx] |
| Pydantic | 2.13.3 | published 2026-04-20 | Settings/health validation at boundaries | Existing FastAPI stack; retain exact lock. [VERIFIED: registry/local environment] |
| pytest | 9.0.3 | published 2026-04-07 | Deterministic tests | Existing root suite and strict marker configuration. [VERIFIED: registry/local environment; `pyproject.toml`] |
| pytest-asyncio | 1.3.0 | published 2025-11-10 | Async provider/runtime tests | Existing lock and strict asyncio mode. [VERIFIED: registry/local environment; `pyproject.toml`] |
| uv | 0.11.21 | observed 2026-08-19 | Python lock/sync/run authority | Locked-project and dependency-group workflow required by D-05. [VERIFIED: local CLI; CITED: https://docs.astral.sh/uv/concepts/projects/sync/] |
| Node/npm | 24.19.0 / 11.17.0 | observed 2026-08-19 | Frontend build and TypeScript tool lane | Current installed environment; CI should state its chosen supported Node version rather than silently follow local. [VERIFIED: local CLIs] |
| TypeScript/Vite | 5.7.3 / 8.0.10 | lock observation 2026-08-19 | Existing frontend type/build lane | Installed lock is coherent and `npx tsc --noEmit` plus build are the correct current surfaces; do not adopt newly published majors here. [VERIFIED: npm tree and local commands] |

Registry checks found newer majors/minors for several packages (for example OpenAI 3.3.1, google-genai 2.18.1, FastAPI 0.141.1, Uvicorn 0.52.4, TypeScript 7.0.2, and Vite 8.2.1). That is evidence **against** broad upgrades during a contract refactor, not an invitation to update. [VERIFIED: PyPI/npm registry queries on 2026-08-19; D-05]

### Supporting/development

| Tool | Recommended version | Purpose | Disposition |
|------|---------------------|---------|-------------|
| Ruff | 0.12.7 initially | Python lint lane | Declare the already-used local version in the `dev` dependency group, then let `uv.lock` remain authoritative. [VERIFIED: local `ruff --version`; existing `[tool.ruff]`] |
| Pyright npm CLI | 1.1.413 | Python type lane | Official Microsoft installation documents the npm package; add as an exact devDependency only after the package-legitimacy checkpoint below. [CITED: https://github.com/microsoft/pyright/blob/main/docs/installation.md] |
| `asyncio.timeout()` | Python 3.12 stdlib | Deterministic/live deadlines | Use inside tests instead of adding another timeout dependency solely for this phase. [VERIFIED: local Python version] |
| `argparse` | Python 3.12 stdlib | Startup/preflight CLI | No third-party CLI package is needed. [VERIFIED: local Python runtime] |

### Alternatives Considered

| Instead of | Could use | Decision and tradeoff |
|------------|-----------|-----------------------|
| OpenAI-compatible Ollama transport | Ollama native `/api/chat` NDJSON | Do not add the second main transport now: the compatible API officially covers required chat/stream/tool/model-list behavior and shares the locked client with OpenRouter. Native endpoints remain useful reference material for error semantics. [CITED: https://docs.ollama.com/api/openai-compatibility; https://docs.ollama.com/api/streaming] |
| Standard-library startup CLI | A third-party CLI framework | Use `argparse`; the command surface is small and adding a runtime dependency provides no phase-critical capability. [VERIFIED: OPS-01 scope] |
| Adapter-hidden SDK chats | Provider-neutral in-memory transcript owner | Use neither in Phase 2: adapters become history-stateless and the characterized persistence/memory-context path remains continuity until Phases 3/4 define storage and conversation semantics. [VERIFIED: phase boundaries] |
| Broad dependency upgrades | Retain current lock while regrouping/removing proven unused direct dependencies | Retain the lock; mixing major upgrades with provider/lifecycle refactoring would confound failures and violate D-05. [VERIFIED: registry drift and D-05] |

### Dependency grouping recommendation

| Group | Packages/action | Evidence-based rationale |
|-------|-----------------|--------------------------|
| Base | Keep FastAPI/Uvicorn/Pydantic/HTTPX/OpenAI plus the storage dependencies that the existing conversation/persistence path actually imports. | Ollama needs OpenAI transport; persistence still invokes Chroma/embeddings, so removing Torch/sentence-transformers before Phase 3 would break the pinned path. [VERIFIED: import/call scan] |
| `provider-gemini` extra | `google-genai` | Cloud Gemini is explicit and must not load in an Ollama-only import/runtime. [VERIFIED: D-01 and eager import evidence] |
| `mcp` extra | `mcp`, `fastmcp` only where supported entry points use them | External tools are optional; raw schemas must load lazily. [VERIFIED: active import scan and limited-functionality current startup path] |
| `memvid` extra | `memvid-sdk` and its active integration dependencies | Memvid is optional archival functionality and not required for provider contract tests. [VERIFIED: source import scan] |
| `media` extra or remove | `beautifulsoup4`, `ebooklib`, OpenCV, pandas, Pillow, pypdf, pyzbar, qrcode | No active provider/runtime import was found; retain only if a supported non-archive entry point test proves use. [VERIFIED: source import scan] |
| Remove direct declarations after tests | `anthropic`, `asyncio-mqtt`, `faiss-cpu`, `faiss-gpu-cu12`, `websockets`, unused frontend `@google/genai` | No active application import was found for these direct dependencies; transitive needs remain in the lock automatically. Do not remove until clean deterministic/build/entry-point probes pass. [VERIFIED: source import scan] |
| `dev` group | pytest, pytest-asyncio, Ruff (and any test-only helpers) | These should not burden the base runtime install. [CITED: https://docs.astral.sh/uv/concepts/projects/dependencies/#development-dependencies] |

`uv` resolves all project extras/groups together even when it installs only selected groups; conflicts must therefore be resolved at lock time. [CITED: https://docs.astral.sh/uv/concepts/projects/config/#conflicting-dependencies]

### Manifest authority and installation

Do not hand-edit resolved lock contents. Update `pyproject.toml`/`package.json`, regenerate the corresponding lock once, and verify:

```bash
uv lock --check
uv sync --locked --no-default-groups
npm ci
```

`npm ci` requires the lock to agree with `package.json`, removes/recreates `node_modules`, and does not rewrite the manifests; use it in CI and a clean validation workspace, not casually against Ty's active environment. [CITED: https://docs.npmjs.com/cli/commands/npm-ci]

Remove `requirements.txt` as a supported authority and update the Dockerfile to use `pyproject.toml` plus `uv.lock`, or mark the Docker entry point unsupported until Phase 6. Do not leave a second contradictory install path presented as valid. [VERIFIED: D-05/OPS-02 and current Dockerfile]

## Package Legitimacy Audit

The required `gsd-tools query package-legitimacy` seam could not run because the installed GSD shim resolves to a runtime missing `package.json` (`Cannot find module '../../../package.json'`). Registry/version/source/postinstall checks were still performed, but they do not substitute for the mandated legitimacy verdict. [VERIFIED: local GSD tool execution failure]

| Package | Registry | Age/source signals | Postinstall | Verdict | Disposition |
|---------|----------|--------------------|-------------|---------|-------------|
| `openai` | PyPI | Existing lock; official `openai/openai-python` source and docs. [CITED: https://github.com/openai/openai-python] | n/a | NOT RE-RUN | Retain current lock; not a new package. |
| `google-genai` | PyPI | Existing lock; official `googleapis/python-genai` source/docs. [CITED: https://github.com/googleapis/python-genai] | n/a | NOT RE-RUN | Retain current lock; move to explicit extra. |
| `ruff` | PyPI | Already installed locally and configured in project. [VERIFIED: local CLI and `pyproject.toml`] | n/a | UNASSESSED | Planner must add `checkpoint:human-verify` before adding to the dev group unless the seam is repaired. |
| `pyright` | npm | Created 2019; registry points to `Microsoft/pyright`; official Microsoft docs name the npm CLI. [CITED: https://github.com/microsoft/pyright/blob/main/docs/installation.md] | None reported by `npm view`. [VERIFIED: npm registry] | UNASSESSED | Planner must add `checkpoint:human-verify` before installation because the legitimacy seam did not return `OK`. |

**Packages removed due to SLOP verdict:** none; the seam was unavailable, so no SLOP verdict was issued.

**Packages flagged as suspicious SUS:** none; the seam was unavailable, so no SUS verdict was issued.

**Unassessed proposed additions requiring a planner checkpoint:** `ruff`, `pyright`.

No new runtime provider package is recommended. [VERIFIED: shared OpenAI-compatible architecture]

## Error and Cancellation Contract

| Condition | Adapter evidence | Typed Aura outcome | Conversation compatibility mapping |
|-----------|------------------|--------------------|------------------------------------|
| Invalid/unknown provider or missing required credential | Current factory silently falls back; cloud SDKs require credentials. [VERIFIED: factory; official SDK docs] | `configuration` before client construction | Startup/preflight fails; request path is not entered. |
| Ollama service down / DNS/connect failure | OpenAI client raises `APIConnectionError`. [CITED: https://github.com/openai/openai-python#handling-errors] | `unavailable` | Existing seven-field HTTP-200 fallback and session clear. [VERIFIED: Phase 1 contract] |
| Selected Ollama model missing | Ollama documents 404 for model/resource not found and lists models via `/api/tags` or compatible `/v1/models`. [CITED: https://docs.ollama.com/api/errors; https://docs.ollama.com/api/openai-compatibility] | `model_not_found` | Same fallback; readiness is false with safe remediation. |
| Authentication failure | OpenAI SDK exposes `AuthenticationError`; Google exposes client/API errors with status. [CITED: official SDK docs] | `authentication` | Same fallback; log code only, never credential/body. |
| Rate limit | OpenAI SDK exposes `RateLimitError`; OpenRouter documents 429. [CITED: official OpenAI/OpenRouter error docs] | `rate_limited` | Same fallback; no hidden retry in adapter. |
| Timeout | OpenAI SDK exposes `APITimeoutError`; Aura owns finite outer deadline. [CITED: official OpenAI docs] | `timeout` | Same fallback; close response/client operation. |
| Empty choices/content or invalid tool JSON | Current code indexes `choices[0]` and may accept empty content. [VERIFIED: adapters] | `malformed_response` | Same fallback; never `Completed`. |
| Tool-turn/token/resource bound reached | Current adapters return an error string as content. [VERIFIED: adapters] | `resource_limit` | Same fallback; not successful text. |
| Error after stream began | Ollama native streaming and OpenRouter can convey errors after status/stream start. [CITED: https://docs.ollama.com/api/errors; https://openrouter.ai/docs/api/reference/errors-and-debugging] | `stream_interrupted` plus partial-byte count | Close without `Completed`; Phase 2 backend consumer discards partial result unless explicitly audited. |
| Caller cancellation / application shutdown | Upstream cancellation guarantee varies. [CITED: https://openrouter.ai/docs/guides/features/streaming] | propagate `CancelledError`; record `cancelled` internally | No fallback success; remove in-flight task and close stream in `finally`. |

Public health/errors may expose the safe code, selected provider kind, model identifier if not sensitive, retryability, and correlation ID. They may not expose exception strings, URLs containing credentials, headers, prompts, response text, tool arguments/results, or traceback. [VERIFIED: D-02]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ollama transport | A second custom socket/NDJSON client for the main adapter | Locked `AsyncOpenAI` against Ollama `/v1` | Official compatibility covers required chat/stream/tool/model-list behavior and is shared with OpenRouter. [CITED: https://docs.ollama.com/api/openai-compatibility] |
| HTTP timeout machinery | Manual timers around socket reads | `httpx.Timeout` plus one `asyncio.timeout()` at Aura boundary | Distinguishes connection/read/write/pool time and gives Aura one deadline owner. [CITED: official OpenAI/HTTPX docs] |
| Provider retry loops | Nested sleep/retry logic in each adapter | SDK retries disabled; one bounded runtime policy | Avoids multiplicative delays and makes cancellation testable. [CITED: official OpenAI retry docs] |
| App lifecycle | Module globals constructed during import | FastAPI lifespan and `app.state.runtime` | Official lifecycle ensures paired startup/shutdown and test control. [CITED: https://fastapi.tiangolo.com/advanced/events/] |
| Cross-platform launcher framework | More shell/batch condition trees | Python `argparse` entry point plus tiny wrappers | One executable behavior works on Linux/Windows without another dependency. [VERIFIED: current script divergence] |
| Package synchronization | `pip install -r requirements.txt`, `npm install` in startup | `uv sync --locked` by explicit setup and `npm ci` | Locks remain authoritative and startup stays non-mutating. [CITED: official uv/npm docs] |
| Fake streaming | Sleep-and-split a completed string | Scripted async fake controlled by `asyncio.Event` | Proves incremental delivery, cancellation, and terminal-state ordering. [VERIFIED: D-03/AI-03] |
| Cancellation guarantee claim | Claim that closing a stream always stops remote compute | Guarantee local task/connection cleanup; state upstream limitation | OpenRouter documents provider-dependent cancellation and Ollama docs do not promise compute termination. [CITED: official provider docs] |

**Key insight:** The hard part is not HTTP syntax; it is preserving one honest terminal-state contract across SDKs that disagree about retries, errors after streaming begins, stateful chats, and cancellation. Use official clients for transport, but keep policy and truthfulness in Aura's typed runtime.

## Runtime State Inventory

This is a refactor phase, so runtime state was checked explicitly. It is **not** a rename or data-migration authorization. [VERIFIED: phase goal and preservation constraints]

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Conversation/vector/profile data are opened by the current lifespan, but provider choice/session SDK objects are not stored as a database schema key in the audited code path. Original Chroma content was not opened or inspected. [VERIFIED: source audit; task restriction] | **Code edit only:** keep all existing storage paths and persistence arguments unchanged. No data migration. Phase 3 owns storage changes. |
| Live service config | Provider/model/URLs/credentials live in environment variables; MCP live configuration may live in the existing MCP config and spawned services rather than the provider modules. [VERIFIED: env reads and MCP lifecycle] | **Code edit only:** move reads into validated runtime settings without renaming secret keys in this phase; never print values. No external-service mutation. |
| OS-registered state | No user systemd unit or live Aura/Uvicorn process was found by read-only process/unit checks; launch is currently script-driven. [VERIFIED: local `systemctl --user` and process query] | None. Do not register a service in Phase 2. |
| Secrets/env vars | `.env` exists but was not read; `.env.example` defaults `AURA_DEFAULT_PROVIDER=gemini`, and code reads Gemini/OpenRouter/Ollama keys plus model/base URL settings. [VERIFIED: filename/config-key scan without secret access] | **Code edit only:** make the example local-first, preserve recognized key names, validate only the selected provider, and redact all diagnostics. No secret-value migration. |
| Build artifacts / installed packages | `.venv`, `node_modules`, and `dist` exist; locks describe the authoritative reproducible state. [VERIFIED: local inventory] | Validate manifest changes in a clean environment/CI. Do not mutate existing artifacts as part of research and do not treat them as source. No package-name migration. |

**Canonical answer:** After repository edits, no renamed runtime identifier requires migration; the remaining stateful concern is orderly closure of live provider/MCP/database/background-task resources, which the new lifespan runtime must own. [VERIFIED: source and runtime inventory]

## Environment Availability

| Dependency | Required By | Available | Version/evidence | Fallback |
|------------|-------------|-----------|------------------|----------|
| Python | backend/test/runtime CLI | ✓ | 3.12.9 [VERIFIED: local CLI] | none |
| uv | Python lock/run | ✓ | 0.11.21 [VERIFIED: local CLI] | none; startup reports remediation only |
| Node/npm | frontend type/build | ✓ | 24.19.0 / 11.17.0 [VERIFIED: local CLI] | deterministic backend lane can run separately |
| Ollama | local provider/live lane | ✓ | 0.32.14 [VERIFIED: local CLI] | fake lane remains complete; cloud only if explicitly configured |
| `ornith:latest` | optional live check | ✓ | local ID `a75697c14589`, 5.6 GB [VERIFIED: `ollama list` 2026-08-19] | truthful skip if absent/unreachable |
| Python provider/API packages | runtime | ✓ | exact versions in Standard Stack [VERIFIED: import metadata] | none for selected provider |
| Ruff | lint lane | ✓ globally | 0.12.7 [VERIFIED: local CLI] | declare in locked dev group for CI |
| Pyright | Python typing lane | ✗ as project dependency | npm current 1.1.413 [VERIFIED: npm registry] | checkpoint then add official npm CLI; until then report typing lane blocked, not passed |
| GitHub Actions | CI | ✗ workflow absent | no `.github/workflows` files [VERIFIED: local inventory] | local commands remain evidence until workflow added |

**Missing dependency with no fallback:** the reproducible Python typing lane lacks a declared checker. The planner must gate and add the official Pyright npm CLI after legitimacy verification. [CITED: official Pyright installation docs]

**Missing dependencies with fallback:** no live Ollama dependency is required by deterministic tests; if unavailable, the marked lane skips with the exact environment reason. [VERIFIED: D-06]

## Validation Architecture

Nyquist validation is enabled because `.planning/config.json` does not set `workflow.nyquist_validation` to `false`. [VERIFIED: local config]

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0; strict asyncio/markers [VERIFIED: local environment and `pyproject.toml`] |
| Config file | `pyproject.toml` |
| Current collection | 131 tests collected on 2026-08-19; Phase 1 verification recorded 131 passing. [VERIFIED: current collection; Phase 1 verification] |
| Quick run | `uv run --locked --no-sync python -m pytest -q tests/providers tests/runtime tests/characterization/test_companion_contract.py` |
| Full deterministic | `uv run --locked --no-sync python -m pytest -q -m "not live and not ollama and not gpu"` |

### TDD order

1. **Red: domain contract.** Add fake-driven tests for normal, empty/malformed, typed errors, real first-delta-before-completion, midstream error, timeout, cancellation, tool-turn resource limit, and exactly-once close. [VERIFIED: AI-01/02/03]
2. **Green: OpenAI-compatible seam.** Implement shared transport against a scripted fake client/ASGI transport; do not contact Ollama. [CITED: official OpenAI client interfaces]
3. **Green: Gemini async seam.** Inject a fake `client.aio`/chat object; assert no synchronous method is called. [CITED: official google-genai async API]
4. **Red/green: runtime lifecycle.** Assert import causes no client/database/process/filesystem creation; assert partial startup unwinds in reverse; assert shutdown cancels/awaits in-flight streams and closes each resource once. [VERIFIED: D-04]
5. **Compatibility gate.** Re-run Phase 1 route/persistence/local-boundary tests before changing launchers/manifests. [VERIFIED: Phase 1 contracts]
6. **Live lane last.** Only after offline lanes pass, run a bounded `ornith:latest` model-list, non-stream response, first-delta, cancellation/disconnect, and malformed-model test without tools or personal data. [VERIFIED: D-06 and local model availability]

### Phase Requirements → Test Map

| Req ID | Behavior | Test type | Automated command | File exists? |
|--------|----------|-----------|-------------------|--------------|
| TEST-03 | Provider translation, typed failure, legacy route fallback/session clear | unit + API characterization | `uv run --locked --no-sync python -m pytest -q tests/providers tests/characterization/test_companion_contract.py` | ❌ Wave 0 for `tests/providers`; ✅ characterization |
| TEST-05 | Each CI lane has an independent result and environment-blocked is not pass | workflow/static + command smoke | `uv run --locked --no-sync python -m pytest -q tests/test_ci_contract.py` | ❌ Wave 0 |
| AI-01 | Same request/result/tool contract for fake, Ollama, OpenRouter, Gemini with no route provider branch | contract unit | `uv run --locked --no-sync python -m pytest -q tests/providers/test_contract.py` | ❌ Wave 0 |
| AI-02 | Ollama timeout, model missing, true delta stream, midstream failure, caller cancel | adapter unit | `uv run --locked --no-sync python -m pytest -q tests/providers/test_ollama.py` | ❌ Wave 0 |
| AI-03 | Scripted fake covers all required states; Ornith optional/marked/bounded | unit + optional live | `uv run --locked --no-sync python -m pytest -q tests/providers/test_fake.py`; live command below | ❌ Wave 0 |
| OPS-01 | Preflight catches dependency/model/port/storage failures without mutation/redaction leaks | unit + subprocess | `uv run --locked --no-sync python -m pytest -q tests/runtime/test_cli.py` | ❌ Wave 0 |
| OPS-02 | One lock path, groups, no startup installs, frontend unused dependency removed safely | static + clean build | `uv lock --check && npm ci && npm run build` | ❌ Wave 0 contract test; manifests exist |

### Focused deterministic cases

- A scripted async generator blocks after delta 1; the test receives delta 1 before releasing completion. This distinguishes true streaming from buffered replay. [VERIFIED: D-03]
- Cancel the consumer while the fake is blocked; assert its `finally` ran, runtime registry is empty, `Completed` was not emitted, and no fallback result exists. [VERIFIED: D-03]
- Feed text delta then in-stream error; assert `stream_interrupted`, partial-count evidence, no completed result, and no partial persistence. [CITED: official Ollama/OpenRouter error behavior]
- Inject OpenAI `AuthenticationError`, `NotFoundError`, `RateLimitError`, `APITimeoutError`, `APIConnectionError`, and 5xx status errors; assert only safe Aura codes escape. [CITED: official OpenAI error hierarchy]
- Return empty choices, empty content, malformed tool JSON, duplicate sanitized tool names, and max tool turns; assert typed failures. [VERIFIED: current unguarded cases]
- Import `aura_backend.main`, `providers.factory`, and every adapter in a subprocess whose socket/connect, subprocess start, Chroma open, model load, and write primitives raise assertions; assert zero calls. [VERIFIED: existing subprocess-fake pattern in `tests/support/main_subprocess_probe.py`]
- Use `with TestClient(create_app(fake_runtime_builder))` to prove start/close, and plain `TestClient(...)` only where the test intentionally proves lifespan did not run. [CITED: https://fastapi.tiangolo.com/advanced/testing-events/]
- Preserve Phase 1's exact seven response fields, success provider input, immediate persistence `update_profile=True`/timeout, provider failure HTTP 200 fallback, error redaction, and one session clear. [VERIFIED: Phase 1 verification and tests]

### Live Ollama lane

```bash
AURA_RUN_LIVE=1 \
AURA_DEFAULT_PROVIDER=ollama \
OLLAMA_MODEL=ornith:latest \
uv run --locked --no-sync python -m pytest -q \
  tests/live/test_ollama_ornith.py -m "live and ollama"
```

Each test must enforce its own `asyncio.timeout()` and use only synthetic prompts. If `AURA_RUN_LIVE` is absent, Ollama is unreachable, or the model is absent, skip with that exact reason. A configured/run live test that times out or returns a provider error is a **failure**, not an environment skip. [VERIFIED: D-06] Record model name/ID, Ollama version, cold/warm flag, first-delta latency, terminal latency, safe outcome code, and cancellation cleanup; never record prompt/response content. [VERIFIED: D-02/D-06]

### CI lane contract

| Lane/job | Command/behavior | Status rule |
|----------|------------------|-------------|
| deterministic-backend | `uv sync --locked --dev` then full deterministic pytest command | Required; fail on any failure/collection error. [CITED: https://docs.astral.sh/uv/guides/integration/github/] |
| provider-live-ollama | Manual/self-hosted or explicitly provisioned service/model | Separate optional check; skipped/blocked is visible, never counted as deterministic pass. [VERIFIED: D-06] |
| lint | `uv run --locked --no-sync ruff check aura_backend tests` | Required after Ruff is locked. |
| typing-python | `npm run typecheck:python` invoking exact locked `pyright` | Required after legitimacy gate and baseline triage. [CITED: official Pyright docs] |
| typing-frontend | `npm run typecheck:frontend` invoking `tsc --noEmit` | Required. [VERIFIED: current compiler succeeds] |
| frontend-build | `npm ci` then `npm run build` | Required and separately named. [CITED: https://docs.github.com/en/actions/tutorials/build-and-test-code/nodejs] |
| environment-blocked | Runs classified legacy/environment probes and publishes their reason | Never relabel blocked as pass. [VERIFIED: Phase 1 legacy classification contract] |

Pin third-party GitHub Actions to immutable commit SHAs, including `astral-sh/setup-uv`; official uv documentation supports a pinned setup action and `uv sync --locked`. [CITED: https://docs.astral.sh/uv/guides/integration/github/]

### Sampling rate

- **Per provider task commit:** quick provider/runtime/companion command.
- **Per lifecycle/API task commit:** Phase 1 API/local-boundary/companion/persistence tests plus new runtime tests.
- **Per dependency task commit:** `uv lock --check`, deterministic suite, `npm ci`, both type lanes, and frontend build in a clean workspace.
- **Per wave merge:** full deterministic suite plus lint/type/build lanes.
- **Phase gate:** all required offline lanes green; live lane reported separately; Phase 1 contracts green; no unredacted logs; import-effect and reverse-shutdown tests green.

### Wave 0 gaps

- [ ] `tests/providers/test_contract.py` — AI-01 contract matrix.
- [ ] `tests/providers/test_fake.py` — AI-03 scripted fake and terminal-state semantics.
- [ ] `tests/providers/test_ollama.py` — AI-02 adapter with fake transport.
- [ ] `tests/providers/test_openrouter.py` — pre-stream/in-stream error translation.
- [ ] `tests/providers/test_gemini.py` — async-only calls, errors, close.
- [ ] `tests/runtime/test_import_safety.py` — D-04 effects and import baseline.
- [ ] `tests/runtime/test_lifecycle.py` — ordered start, partial unwind, reverse close, cancellation.
- [ ] `tests/runtime/test_health.py` — liveness/readiness/optional provider truthfulness/redaction.
- [ ] `tests/runtime/test_cli.py` — non-mutating preflight matrix.
- [ ] `tests/live/test_ollama_ornith.py` — bounded optional live lane.
- [ ] `tests/test_ci_contract.py` — lane/lock/startup static assertions.
- [ ] Locked Ruff and Pyright declarations after package-legitimacy checkpoint.

## Security Domain

Security enforcement is enabled because `.planning/config.json` does not explicitly set it false. [VERIFIED: local config]

### Applicable ASVS Categories

| ASVS Category | Applies | Standard control |
|---------------|---------|------------------|
| V2 Authentication | no for normal local use | Preserve no mandatory sign-in; do not add auth in this phase. Loopback is the default trust boundary. [VERIFIED: LOCAL-04/D-04] |
| V3 Session Management | yes, application session cleanup | Opaque server-issued session ID already returned; runtime tracks in-flight work and clears on failure/delete/shutdown without treating it as an authenticated session. [VERIFIED: current response/session path] |
| V4 Access Control | yes at network boundary | Existing explicit local origins, strict JSON, and loopback default; LAN remains explicit opt-in. [VERIFIED: Phase 1 verification] |
| V5 Input Validation | yes | Existing Pydantic request models plus validated provider/tool/config DTOs; reject invalid tool JSON/colliding names. [VERIFIED: current FastAPI stack and identified gaps] |
| V6 Cryptography | no new cryptographic function | Use provider TLS through official clients; never hand-roll crypto or store credentials in diagnostics. [CITED: official provider clients] |
| V7 Error/Logging | yes | Safe typed codes, correlation IDs, redaction, no content/raw exception/traceback by default. [VERIFIED: D-02] |
| V13 API | yes | Bounded body/model/tool parameters, honest health, typed adapter boundary, and no error-as-success internally. [VERIFIED: phase requirements] |

### Threat model

| Threat pattern | STRIDE | Current exposure | Required mitigation |
|----------------|--------|------------------|---------------------|
| Browser/site drives privileged localhost API | Spoofing / elevation | Phase 1 already constrained origins and loopback. [VERIFIED: Phase 1 verification] | Preserve exact CORS/host rules; no auth added. |
| Unknown provider typo silently selects Gemini | Spoofing / information disclosure / cost | Factory currently falls back to Gemini. [VERIFIED: factory] | Fail configuration before client creation; cloud is explicit only. |
| Provider/model/tool response is malformed or tool names collide after sanitization | Tampering | Adapters index/parse without full validation; sanitizers can collapse names. [VERIFIED: adapters] | Validate DTO/schema, reject collisions, bound tool turns, and type malformed/resource outcomes. |
| Raw prompts/responses/errors in logs or health | Information disclosure | Main logs large answer previews; adapters log raw exception/tracebacks; health returns `str(e)`. [VERIFIED: local code] | Safe structured logs only; internal exception chaining without default rendering. |
| Slow/unavailable model holds event loop/resources | Denial of service | Gemini sync calls block async loop; OpenAI default timeout/retries are long. [VERIFIED: local code; official SDK defaults] | Async SDK, finite deadlines, zero hidden retries, bounded tool loops, client cancellation and graceful shutdown. |
| Partial stream persisted/reported as complete | Tampering / repudiation | No true current stream; naive implementation risk is explicit. [VERIFIED: D-02/D-03] | Only `Completed` licenses success/persistence; retain terminal state and partial byte count without content. |
| Startup kills unrelated process or downloads code | Tampering / elevation | Shell kills occupied ports and curls uv installer. [VERIFIED: launcher] | Preflight only reports; setup remains explicit user action. |
| Dependency confusion/stale duplicate manifests | Tampering / supply chain | pip requirements and uv lock disagree; proposed tools lack completed legitimacy seam. [VERIFIED: manifests/tool failure] | One lock per ecosystem, `npm ci`/`uv --locked`, action SHA pins, package checkpoint before additions. |
| LAN opt-in accidentally becomes default | Information disclosure | Windows launcher currently binds `0.0.0.0`. [VERIFIED: batch launcher] | One validated host setting defaulting loopback on every OS; explicit warning for LAN. |

The local trust model is deliberately retained. Security work here makes that boundary honest and narrow; it does not introduce accounts, cookies, JWTs, or remote multi-user claims. [VERIFIED: D-04]

## Performance Baselines and Measurement Contract

| Baseline | Current evidence | Interpretation |
|----------|------------------|----------------|
| `import aura_backend.main` | 6.70 s; 1,110,152 KiB max RSS, isolated temp cwd, no files created. [VERIFIED: one `/usr/bin/time` sample] | Import is heavyweight; use only as before baseline, not a stable benchmark. |
| `import aura_backend.providers.factory` | 1.60 s; 118,708 KiB max RSS. [VERIFIED: one sample] | Eager adapter imports impose substantial cost before selection. |
| `import aura_backend.providers.base` | 0.03 s; 18,544 KiB max RSS. [VERIFIED: one sample] | A pure domain module is the intended import profile. |
| Environment size | `.venv` about 6.4 GB; `node_modules` about 92 MB in the audited workspace. [VERIFIED: local disk inventory] | Dependency grouping has potential value, but no savings claim is licensed until clean-install measurements. |
| Provider latency | No live prompt was sent during research. [VERIFIED: research procedure] | Phase 2 must collect cold/warm startup, first-delta, terminal, and cancellation times before any performance claim. |

Capture before/after in the same environment, provider/model ID, prompt class and max-token bound, with at least cold and warm observations. Record median and individual raw durations rather than a single favorable run; keep content out of artifacts. [VERIFIED: D-06 and project evidence standards] Performance optimization itself remains Phase 6. [VERIFIED: ROADMAP]

## Common Pitfalls

### Pitfall 1: Passing adapter tests while the route still uses Gemini globals

**What goes wrong:** Ollama generates the main answer, then the three analysis calls use the OpenAI client as if it were Gemini and silently fall back. [VERIFIED: current call path]

**How to avoid:** Search the entire conversation path for SDK/provider types and add a test whose fake provider handles both response and analysis requests while Gemini/OpenAI constructors are forbidden. Preserve prompts/parsers, not Gemini ownership. [VERIFIED: AI-01/Phase 4 boundary]

### Pitfall 2: Calling a buffered generator “streaming”

**What goes wrong:** A response is complete before the first chunk, so cancellation and time-to-first-token claims are false. [VERIFIED: current adapters]

**How to avoid:** Event-gated fake proves first delta arrives before completion; midstream failure must lack `Completed`. [VERIFIED: D-03]

### Pitfall 3: Double or triple retry multiplication

**What goes wrong:** OpenAI SDK retries, Aura provider loops, and tool loops combine, making a nominal timeout much longer and shutdown slow. [CITED: official OpenAI default retry docs; VERIFIED: current loops]

**How to avoid:** Disable SDK retry, own one absolute deadline/retry budget, and test elapsed upper bounds with fake time/events.

### Pitfall 4: Assuming connection cancellation equals upstream cancellation

**What goes wrong:** Aura reports that work/billing stopped when only the local connection closed. OpenRouter documents that support varies by underlying provider. [CITED: official OpenRouter streaming docs]

**How to avoid:** Promise only local task/stream cleanup; record upstream cancellation as unknown unless the specific provider documents and a live test proves it.

### Pitfall 5: Breaking the Phase 1 fallback while improving internal errors

**What goes wrong:** Typed failures accidentally change `/conversation` to a new HTTP status/body before the frontend/API phase. [VERIFIED: Phase 1 contract]

**How to avoid:** Map every provider terminal failure at the route edge to the existing HTTP-200 seven-field fallback and one session clear; change public semantics only in Phase 5 with new characterization.

### Pitfall 6: Moving Torch/Chroma merely because they are heavy

**What goes wrong:** The base conversation path loses immediate persistence/embedding behavior, violating preservation and crossing into Phase 3. [VERIFIED: current persistence call path]

**How to avoid:** First remove import-time loading and classify direct imports. Move only proven optional/unused packages; retain storage dependencies until Phase 3 supplies a replacement contract.

### Pitfall 7: Making cloud “optional” while importing it eagerly

**What goes wrong:** Ollama-only installs still require/import Google modules because factory, MCP bridge, autonomic, or main imports them. [VERIFIED: current import graph]

**How to avoid:** Lazy selected-adapter imports; neutral MCP schemas; autonomic explicit/disabled unless compatible; import-safety tests run with Gemini modules unavailable.

### Pitfall 8: Health checks that lie or cause work

**What goes wrong:** Object existence is labeled connected, or a health request starts a model/download/generation. [VERIFIED: current health; D-04]

**How to avoid:** Separate `/live`, cached `/ready`, and bounded provider metadata checks; never generate text or initialize missing resources from health.

### Pitfall 9: Dependency cleanup without supported-entry-point probes

**What goes wrong:** A package absent from the main import scan is still required by an alternate supported MCP/Memvid command. [VERIFIED: active alternate entry points]

**How to avoid:** Inventory and smoke each supported entry point, then remove/move one dependency class at a time with lock, tests, and build gates.

### Pitfall 10: Letting CI installation alter authority

**What goes wrong:** `npm install`, unlocked `uv sync`, or floating actions rewrite/ignore locks and produce a green result for a different environment. [CITED: official npm/uv CI docs]

**How to avoid:** `npm ci`, `uv sync --locked`, `uv lock --check`, immutable action SHAs, and named jobs.

## Code Examples

### OpenAI-compatible async stream with explicit client ownership

```python
from openai import AsyncOpenAI
import httpx

client = AsyncOpenAI(
    api_key="ollama",  # syntactically required by SDK; ignored by local Ollama
    base_url="http://127.0.0.1:11434/v1",
    max_retries=0,
    timeout=httpx.Timeout(connect=2.0, read=60.0, write=10.0, pool=2.0),
)

try:
    stream = await client.chat.completions.create(
        model="ornith:latest",
        messages=[{"role": "user", "content": "synthetic live-test prompt"}],
        stream=True,
    )
    async for chunk in stream:
        # Adapter validates and translates; SDK chunks never leave this module.
        ...
finally:
    await client.close()
```

Source: official OpenAI Python async/stream/timeout API and official Ollama OpenAI compatibility. [CITED: https://github.com/openai/openai-python; https://docs.ollama.com/api/openai-compatibility] Exact timeout values above are configuration examples, not researched performance targets; the implementation must lock named settings and test them. [ASSUMED]

### Gemini async lifecycle

```python
from google import genai

client = genai.Client(api_key=api_key)
try:
    response = await client.aio.models.generate_content(
        model=model_name,
        contents="synthetic request",
    )
finally:
    await client.aio.aclose()
```

Source: official google-genai async client documentation. [CITED: https://googleapis.github.io/python-genai/]

### Cancellation-safe runtime boundary

```python
async def stream(self, request: ProviderRequest) -> AsyncIterator[StreamEvent]:
    task = asyncio.current_task()
    self._in_flight.register(request.session_id, task)
    try:
        async with asyncio.timeout(self._settings.request_timeout_seconds):
            async for event in self._provider.stream(request):
                yield event
    except asyncio.CancelledError:
        self._record_terminal("cancelled", request.session_id)
        raise
    except TimeoutError as exc:
        raise ProviderFailure.timeout() from exc
    finally:
        self._in_flight.discard(request.session_id, task)
```

This is the recommended Aura policy derived from the locked cancellation contract and Python 3.12 task semantics. [VERIFIED: D-03; local Python]

### FastAPI lifespan test

```python
from fastapi.testclient import TestClient

runtime = FakeRuntime()
app = create_app(runtime_builder=lambda: runtime)

with TestClient(app) as client:
    assert runtime.started
    assert client.get("/ready").status_code == 200

assert runtime.closed
```

Source: FastAPI requires the context-managed `TestClient` form to run lifespan. [CITED: https://fastapi.tiangolo.com/advanced/testing-events/]

## State of the Art

| Old/current approach | Current recommended approach | Evidence | Impact |
|----------------------|------------------------------|----------|--------|
| Buffer complete provider response, then yield once | Consume official async stream and translate deltas through one state machine | Official clients support async streaming. [CITED: Ollama/OpenAI/Google docs] | Real first-delta, timeout, partial-error, and cancellation behavior become testable. |
| Sync Gemini call inside `async def` | `client.aio` async generate/chat/stream plus `aio.aclose()` | Official google-genai API. [CITED: https://googleapis.github.io/python-genai/] | Event loop remains responsive and shutdown owns connections. |
| Module-global construction and test monkeypatching | Pure app factory plus lifespan-owned runtime | FastAPI lifespan guidance. [CITED: official FastAPI docs] | Import safety, deterministic tests, and partial-start cleanup. |
| pip requirements plus uv lock | PEP 735-style dependency groups/optional extras with one `uv.lock` | Official uv project docs. [CITED: https://docs.astral.sh/uv/concepts/projects/dependencies/] | One Python authority and smaller selected installs without divergent pins. |
| `npm install` during startup | `npm ci` in explicit setup/CI | Official npm behavior. [CITED: https://docs.npmjs.com/cli/commands/npm-ci] | Reproducible lock-faithful frontend install. |
| Uvicorn import-string app with eager globals | explicit factory/runtime entry point; loopback default; graceful shutdown | Uvicorn factory/lifespan settings. [CITED: https://www.uvicorn.org/settings/] | One cross-platform lifecycle and no import-time services. |

**Deprecated/outdated for this project:**

- `requirements.txt` as an independently maintained install authority: replace with `pyproject.toml`/`uv.lock` usage. [VERIFIED: D-05 and manifest drift]
- `start_full_system.*` as installers/port killers: retain only tiny delegates to the Python runtime command or replace documentation references. [VERIFIED: D-05]
- Raw `ProviderResponse.error`/`raw_response`: replace with typed failures and normalized safe result fields. [VERIFIED: D-02]
- Gemini-specific MCP bridge access from conversation orchestration: move conversion into the Gemini adapter. [VERIFIED: AI-01]

## Phase Boundaries

### Included now

- Typed provider request/result/error/stream contract and deterministic fake. [VERIFIED: AI-01/02/03]
- True Ollama/OpenRouter/Gemini async streaming internally, cancellation cleanup, model readiness, and client close. [VERIFIED: D-02/03/04]
- Provider-neutral current emotion/cognitive analysis transport without prompt/schema redesign. [VERIFIED: AI-01 and Phase 4 boundary]
- App/runtime lifecycle, import safety, health split, and non-mutating preflight/serve entry point. [VERIFIED: D-04/05]
- Manifest authority, proven optional groups/removals, lock checks, and separate CI lanes. [VERIFIED: OPS-02/TEST-05]
- Baseline measurement only. [VERIFIED: D-06]

### Explicitly excluded

- No Chroma open/migration/repair/deletion/root consolidation; preserve current storage construction semantics. [VERIFIED: Phase 3 boundary]
- No emotion prompt redesign, psychological-validity claim, evaluation corpus, or quality ranking. [VERIFIED: Phase 4 boundary]
- No public browser streaming UX or frontend modularization. Backend iterator readiness is enough for Phase 2. [VERIFIED: Phase 5 boundary]
- No broad performance optimization or final packaging claim. [VERIFIED: Phase 6 boundary]
- No auth system, remote deployment hardening, original-data inspection, backup mutation, `.trunk` change, or Git-history rewrite. [VERIFIED: locked project constraints]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Example OpenAI-compatible connect/read/write/pool timeout numbers are suitable starting configuration values. [ASSUMED] | Code Examples | Values may be too strict/loose; planner must expose settings and validate bounded fake/live behavior rather than treating them as performance targets. |

All architecture, package, API, and local-runtime claims above are otherwise grounded in local evidence or cited primary official documentation. [VERIFIED: source audit]

## Resolved Questions

1. **Native Ollama or OpenAI-compatible API?** Use the official OpenAI-compatible API for chat, streaming, tools, and model listing because Aura already locks `AsyncOpenAI` for OpenRouter. No new Ollama package. [CITED: https://docs.ollama.com/api/openai-compatibility]
2. **What is the local-first default?** Configuration and `.env.example` should select `ollama`, but normal runtime must require an explicitly configured installed model rather than silently choosing or downloading one. `ornith:latest` is reserved for the opt-in live lane only. Cloud providers require explicit selection/credential. [VERIFIED: D-01 and task constraint]
3. **Who owns sessions?** Adapters are stateless with respect to conversation history. Runtime owns in-flight task/cancellation cleanup; the existing persistence/memory-context path remains continuity until Phase 3/4. [VERIFIED: parity analysis and phase boundary]
4. **Does cancellation guarantee upstream compute stops?** No general claim. Aura guarantees local task/stream/client cleanup and no false completion; upstream cancellation is provider-dependent/unknown unless officially documented and live-verified. [CITED: official OpenRouter/Ollama docs]
5. **Does provider failure change the existing API response now?** No. Internally it becomes typed; `/conversation` retains the Phase 1 HTTP-200 seven-field fallback and session clear through Phase 2. [VERIFIED: Phase 1 contract]
6. **Is a public stream endpoint part of Phase 2?** No. Implement/test the backend provider/runtime iterator; expose browser streaming in Phase 5 after API/UI contract work. [VERIFIED: ROADMAP]
7. **Can autonomic/MCP silently create Gemini in local mode?** No. MCP schemas become neutral; Gemini conversion is adapter-local; autonomic is explicitly compatible/injected or disabled with an honest status, never a silent cloud client. [VERIFIED: D-01/AI-01]
8. **Upgrade dependencies while reorganizing?** No. Retain the verified lock versions and make grouping/authority changes only; major upgrades are separate evidence-bearing work. [VERIFIED: D-05 and registry drift]
9. **Run Ornith during deterministic validation?** No. The 5.6 GB model is installed, but live checks remain opt-in, marked, bounded, synthetic, and separately reported. [VERIFIED: D-06 and local environment]
10. **What blocks planning?** No architectural blocker. The only mandatory checkpoint is package-legitimacy verification before adding Ruff/Pyright to authoritative manifests because the GSD seam is broken. [VERIFIED: local tool failure]

## Sources

### Primary (HIGH confidence)

- Local source, manifests, locks, tests, installed-package metadata, CLI versions, process/unit inventory, `ollama list`, and isolated import benchmarks — current architecture/environment evidence. [VERIFIED: local workspace/runtime on 2026-08-19]
- `.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `02-CONTEXT.md`, Phase 1 verification/01-05/01-07 summaries, and codebase architecture/integration/testing/concerns maps — scope and locked contract evidence. [VERIFIED: local planning files]
- https://docs.ollama.com/api/openai-compatibility — supported OpenAI endpoints/features and model listing.
- https://docs.ollama.com/api/streaming — native stream framing behavior.
- https://docs.ollama.com/api/errors — native HTTP/in-stream error behavior.
- https://docs.ollama.com/api/tags — native model-list API.
- https://github.com/openai/openai-python — async client, streaming, typed errors, retries, timeouts, and close.
- https://googleapis.github.io/python-genai/ and https://github.com/googleapis/python-genai — async client/stream/close, errors, and timeout configuration.
- https://fastapi.tiangolo.com/advanced/events/ — lifespan resource pattern.
- https://fastapi.tiangolo.com/advanced/testing-events/ — lifespan testing via context-managed `TestClient`.
- https://www.uvicorn.org/settings/ — app factory, host, lifespan, and graceful-shutdown controls.
- https://docs.astral.sh/uv/concepts/projects/sync/ — lock/sync/run semantics.
- https://docs.astral.sh/uv/concepts/projects/dependencies/ — dependency groups and optional dependencies.
- https://docs.astral.sh/uv/guides/integration/github/ — locked GitHub Actions workflow.
- https://docs.npmjs.com/cli/commands/npm-ci — lock-faithful clean npm installs.
- https://docs.github.com/en/actions/tutorials/build-and-test-code/nodejs — separate Node build/test CI pattern.
- https://github.com/microsoft/pyright/blob/main/docs/installation.md — official npm CLI package.

### Secondary (MEDIUM confidence)

- https://openrouter.ai/docs/api/reference/errors-and-debugging — OpenRouter pre-stream and midstream error envelope.
- https://openrouter.ai/docs/guides/features/streaming — stream cancellation limits by underlying provider.
- PyPI/npm registry metadata queried 2026-08-19 — existence, versions, publish dates, repository and postinstall metadata; registry presence alone was not treated as legitimacy verification.

### Tertiary (LOW confidence)

- Only the example timeout numbers in A1; all other recommendations are traced to local evidence or primary documentation.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — exact local locks/versions plus official client/framework documentation; no upgrade recommended.
- Architecture: HIGH — exact call/import/lifecycle paths were inspected and locked decisions constrain the design.
- Streaming/error mapping: MEDIUM-HIGH — official APIs define the relevant surfaces, but universal upstream cancellation cannot be guaranteed.
- Dependency cleanup: MEDIUM-HIGH — active import scan is strong, but alternate entry-point smoke tests are required before each removal.
- Package legitimacy: LOW for proposed Ruff/Pyright additions until the broken GSD legitimacy seam is repaired and returns `OK`.
- Pitfalls/security: HIGH — tied to concrete local code paths and locked requirements.

**Research date:** 2026-08-19

**Valid until:** 2026-09-18 for the stable refactor plan; re-check official SDK/registry versions before any manifest change.
