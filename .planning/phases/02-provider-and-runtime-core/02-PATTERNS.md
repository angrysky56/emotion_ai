# Phase 2: Provider and Runtime Core - Pattern Map

**Mapped:** 2026-08-19
**Files analyzed:** 31 likely new/modified files (including generated locks and grouped tests)
**Analogs found:** 24 / 31; only 10 are safe to copy substantially

## File Classification

| New/Modified File | Role | Data Flow | Closest Existing Analog | Match Quality |
|---|---|---|---|---|
| `aura_backend/providers/base.py` | model/protocol | request-response + streaming | `aura_backend/preservation/manifest.py` | role-partial, typing exact |
| `aura_backend/providers/errors.py` | model/error | transform | `aura_backend/runtime_security.py` | role-match |
| `aura_backend/providers/config.py` | config | transform | `aura_backend/runtime_security.py` | role-match |
| `aura_backend/providers/openai_compatible.py` | service/adapter | request-response + streaming | `providers/ollama.py`, `providers/openrouter.py` | partial; reuse conversion only |
| `aura_backend/providers/ollama.py` | service/adapter | request-response + streaming | current `providers/ollama.py` | same file, unsafe core |
| `aura_backend/providers/openrouter.py` | service/adapter | request-response + streaming | current `providers/openrouter.py` | same file, unsafe core |
| `aura_backend/providers/gemini.py` | service/adapter | request-response + streaming | current `providers/gemini.py` | same file, unsafe core |
| `aura_backend/providers/factory.py` | factory/config | request-response | current `providers/factory.py` | same role; replace eager/silent behavior |
| `aura_backend/providers/runtime.py` | service/provider | streaming + event-driven | `main.py::lifespan` | partial |
| `aura_backend/providers/fake.py` or `tests/providers/fakes.py` | test utility | scripted streaming | `tests/support/main_subprocess_probe.py` | partial |
| `aura_backend/runtime/__init__.py` | package | request-response | `aura_backend/preservation/__init__.py` | exact |
| `aura_backend/runtime/config.py` | config | transform | `aura_backend/runtime_security.py` | exact style |
| `aura_backend/runtime/health.py` | model/service | request-response | `preservation/manifest.py` | status-model match |
| `aura_backend/runtime/app.py` | provider/composition root | event-driven | `main.py::lifespan` | role-match, replace globals |
| `aura_backend/runtime/cli.py` | utility/CLI | batch + request-response | `preservation/cli.py` | exact shell/exit pattern |
| `aura_backend/runtime/__main__.py` | route/entry point | request-response | `preservation/cli.py::main` | role-match |
| `aura_backend/conversation/analysis.py` | service | request-response + transform | `main.py::detect_*` | extraction analog |
| `aura_backend/main.py` | controller/composition | request-response + event-driven | current route/lifespan | exact compatibility seam |
| `aura_backend/mcp_system.py`, `mcp_to_gemini_bridge.py` | service/adapter | event-driven + request-response | provider OpenAI tool conversion | partial; no safe neutral catalog analog |
| `aura_backend/aura_autonomic_system.py` | service | event-driven | current lifespan optional-start branch | partial |
| `tests/providers/test_contract.py` | test | request-response | `tests/test_runtime_security.py` | test-style match |
| `tests/providers/test_streaming.py` | test | streaming + event-driven | no safe streaming test exists | none |
| `tests/providers/test_adapters.py` | test | request-response + streaming | characterization recording fakes | partial |
| `tests/runtime/test_import_safety.py` | test | batch/subprocess | `tests/support/main_subprocess_probe.py` | exact |
| `tests/runtime/test_lifespan.py`, `test_health.py` | test | event-driven + request-response | `tests/api/test_filesystem_contract.py` + subprocess probe | role-match |
| `tests/runtime/test_cli.py` | test | batch | `tests/preservation/test_backup_restore.py` CLI tests | exact |
| `tests/api/test_provider_compatibility.py` | test | request-response | `tests/characterization/test_companion_contract.py` | exact |
| `tests/live/test_ollama_ornith.py` | test | streaming/live request-response | no trustworthy live-test analog | none |
| `.github/workflows/ci.yml` | config | batch | no workflow exists | none |
| `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`, `.env.example`, `Dockerfile` | config/manifests | batch | current manifests | same files; reconcile, do not broadly upgrade |
| launcher/docs files (`start_full_system.*`, backend wrappers, README/startup guide) | config/utility | batch | `preservation/cli.py` command boundary | partial; wrappers delegate only |

## Pattern Assignments

### Provider domain types: `providers/base.py`, `providers/errors.py`, `providers/config.py`

**Primary analog:** `aura_backend/preservation/manifest.py`

**Typed status pattern** (lines 23-30, 42-49, 111-127):

```python
class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"
    NOT_APPLICABLE = "not_applicable"

@dataclass(frozen=True, slots=True)
class RootDeclaration:
    alias: str
    repository_relative_path: str
    role: RootRole
    required: bool = True

@dataclass(frozen=True, slots=True)
class EvidenceCheck:
    name: str
    status: CheckStatus
    evidence_sha256: str
```

Copy the conventions, not the preservation names: string-valued enum codes, `frozen=True, slots=True`, validation at construction, immutable tuples, and distinct terminal states. Provider success must be a result type; non-success must be `ProviderFailure`, with cancellation propagated as `CancelledError`. Do not preserve `ProviderResponse.error` or `raw_response: Any` from `providers/base.py:39-46`.

**Safe public/private separation analog** (`preservation/manifest.py:147-166`): public DTOs should be built from an explicit allowlist, never by dumping an exception/SDK response and deleting fields afterward.

**Validation/error hierarchy analog** (`runtime_security.py:19-32,35-41`):

```python
class StoragePathError(ValueError): ...
class InvalidStorageIdentifier(StoragePathError): ...

def server_host(configured_host: str | None) -> str:
    return configured_host.strip() if configured_host and configured_host.strip() else "127.0.0.1"
```

Use named error subclasses and pure normalization helpers. Provider config should default to Ollama, validate only the selected provider, reject an unknown name, and never log credentials.

### OpenAI-compatible transport: `openai_compatible.py`, `ollama.py`, `openrouter.py`

**Analogs:** current `ollama.py:94-137` and `openrouter.py:103-149`.

Reuse the provider-neutral message/tool conversion shape:

```python
openai_messages = []
if system_instruction:
    openai_messages.append({"role": "system", "content": system_instruction})
for msg in messages:
    m = {"role": msg.role, "content": msg.content}
    # tool calls become OpenAI-compatible id/function/arguments objects
    openai_messages.append(m)
response = await self.client.chat.completions.create(**kwargs)
```

Also reuse the tool-name mapping idea from `ollama.py:46-76`, but centralize it. There is no justification for the two current copies to diverge (`re.sub(...)` versus only replacing dots).

**Must replace:** client construction at `ollama.py:41` and `openrouter.py:42-49` lacks explicit timeouts, disables neither SDK retries nor leakage; both `stream_response` methods buffer a complete response (`ollama.py:202-215`, `openrouter.py:228-242`); both return error strings as successful responses and expose raw SDK objects. The new shared adapter owns `AsyncOpenAI`, `max_retries=0`, `httpx.Timeout`, true async iteration, stream terminal validation, tool-delta assembly, error mapping, and `aclose()`.

Ollama subclasses/config supplies local `/v1`, syntactic `api_key="ollama"`, model policy and bounded model-list health only. OpenRouter supplies URL/headers/auth plus documented in-stream error detection. A partial stream followed by failure must never emit `Completed`.

### Gemini adapter: `providers/gemini.py` and `thinking_processor.py`

**Analog:** current `gemini.py:77-88,114-144,163-170` only for message/config/result translation.

Retain conversion into `types.Content`, generation settings and normalized answer/thought-summary extraction. Replace client construction during `__init__` (`47-56`), hidden session cache (`59-60,128-144`), synchronous chat use inside async flow, catch-all raw logging (`172-179`), and buffered stream (`181-193`). Use the official `client.aio` path and close it through runtime lifecycle. Adapters remain history-stateless; `session_id` is a correlation/cancellation key.

### Factory and provider runtime: `providers/factory.py`, `providers/runtime.py`

**Factory analog:** current `factory.py:24-64` establishes the one selection branch and existing environment key names.

Keep one factory and the recognized keys, but move each adapter import inside its selected branch. Replace default Gemini (`line 34`) with validated local Ollama. Replace unknown-provider fallback (`66-74`) with a configuration failure. Cloud constructors run only when explicitly selected and credential validation has passed.

**Lifecycle/cancellation analog:** `main.py:1219-1347` establishes dependency-order startup and reverse-order shutdown, but not partial-start safety. ProviderRuntime should register the current task before generation/streaming, use one absolute deadline, remove it in `finally`, explicitly re-raise `asyncio.CancelledError`, and close stream/client resources. There is no safe existing in-flight registry analog; follow the research state machine rather than copying a legacy module.

### Runtime configuration, health, application and CLI

**Configuration analog:** `runtime_security.py:35-41,110-122` is the strongest pure-module precedent: no heavyweight imports, deterministic input/output, loopback default, explicit rejection of unsafe configuration.

**Health analog:** `preservation/manifest.py:285-290` always emits every status bucket so absence cannot appear successful. Apply the same fail-closed idea to typed liveness/readiness/provider DTOs. Do not copy `main.py:1504-1531`: object existence is not connectivity, status is always “operational,” and raw `str(e)` is public.

Required semantic split:

- `/live`: process/event-loop only, no network work.
- `/ready`: cached required-runtime/selected-provider readiness; 503 when required state is unavailable.
- `/health/providers`: safe diagnostic state; unselected cloud is `not_configured`, not failure.
- `/health`: compatibility composite derived from the above, no raw exception text.

**App lifecycle analog:** retain `@asynccontextmanager` and FastAPI `lifespan=` wiring from `main.py:1219-1223,1351-1356`, plus the current local CORS settings at `1358-1369`. Replace the global assignments (`1225-1229`) with `app.state.runtime`. `ApplicationRuntime.start()` owns construction in dependency order and `aclose()` closes successfully started resources in strict reverse order, including partial-start cleanup. `app = create_app()` must remain import-compatible but resource-free.

**CLI analog:** `preservation/cli.py:149-213,216-240`:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(...)
    subcommands = parser.add_subparsers(dest="command", required=True)
    ...
    return parser

def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        ...
    except KnownBlockedCondition:
        print("safe redacted message", file=sys.stderr)
        return 3
```

Copy standard-library `argparse`, typed `Sequence[str]`, one integer exit contract, and redacted known failure categories. Preflight checks executable/version presence, locks, selected-provider configuration, port, storage writability, service/model availability, and readiness. It reports remediation; it never installs, syncs, downloads, writes `.env`, changes permissions, kills a process, or enables reload.

### Conversation analysis, MCP neutrality, autonomic behavior and `main.py`

**Extraction analog:** preserve prompts/parsers/default outputs in `main.py::detect_user_emotion` (`905-1020`), `detect_aura_emotion` (`1021-1131`), and `detect_aura_cognitive_focus` (`1132-1215`), but inject/use the typed provider boundary. This phase changes transport ownership, not emotion quality.

**Route compatibility seam:** `main.py:1674-1697` shows the provider call location; `1986-2028` is the pinned fallback and one-session-clear behavior. The route must continue returning the seven-field HTTP-200 fallback during Phase 2. Replace provider globals with `request.app.state.runtime.provider_runtime`; do not branch on provider names or SDK types. Remove raw response/thought preview logging at `1700-1723` and raw recovery exception/session logging at `1986-2004`.

**No safe analog:** `main.py:1637-1663` reads `MCPGeminiBridge` and a private `_tool_mapping`; this must be replaced by a neutral tool catalog/executor. Likewise, the autonomic system must be injected with a compatible selected provider or truthfully disabled; no local-selected path may construct Gemini implicitly.

### Provider and runtime tests

**Simple unit-test style:** `tests/test_runtime_security.py:13-63` uses descriptive behavior names, exact values, `pytest.raises`, and parameterized invalid inputs. Use this for config/error-code/result serialization tests.

**Offline fail-closed subprocess pattern:** `tests/support/main_subprocess_probe.py:67-130,139-147`:

```python
completed = subprocess.run(..., timeout=timeout, check=False)
if completed.returncode != 0:
    raise ProbeFailure(...)
result = json.loads(completed.stdout)
if result["complete"] is not True or result["status"] != "ok":
    raise ProbeFailure(...)

socket.create_connection = forbidden_connect
socket.socket.connect = forbidden_connect
```

Use this for `import aura_backend.main`, importing each provider module with optional SDKs unavailable, and canonical startup/preflight probes. Keep the sanitized environment (`lines 67-80`), bounded diagnostics (`83-86`), temp working directory, and repository-data-root before/after snapshot. Phase 2 should invert the Phase 1 fake at `162-166`: imports must not call the provider factory at all.

**Route compatibility test:** preserve `tests/characterization/test_companion_contract.py:21-68`: real route through a recording fake, exact seven-field schema, no provider error leakage, provider call count 1, clear-session count 1 on failure, zero persistence calls, no hidden reasoning, unchanged repository roots.

**Lifespan test:** use `TestClient` as a context manager with an injected fake runtime; assert start inside the context and close after it. Current direct constructions at `tests/api/test_filesystem_contract.py:305` deliberately bypass lifespan and are not the template for lifecycle assertions.

**Streaming test (no existing analog):** implement a scripted fake controlled by `asyncio.Event`. Assert the consumer receives `TextDelta` before completion is allowed; terminal success occurs exactly once; malformed/timeout/missing-model/unavailable/auth/resource-limit/midstream failure emit no `Completed`; cancelling the consumer closes the generator and clears the in-flight registry. Do not use sleep-and-split or replay a completed string.

**Live test (no existing analog):** mark both `live` and `ollama`, wrap the whole operation in `asyncio.timeout`, use only a synthetic prompt and configured `ornith:latest`, and skip with a precise service/model reason. Never run it in the root deterministic lane; never turn timeout/resource failure into skip or pass once prerequisites were confirmed.

### Manifests, CI, Docker and launchers

Current `pyproject.toml:5-38` is the authoritative declaration but mixes runtime, provider, media, GPU and test dependencies. Preserve locked versions; introduce evidence-backed groups/extras only. Do not hand-edit `uv.lock`. `package.json:6-19` provides the existing build scripts; remove `@google/genai` only after import scan and clean `npm ci`/build evidence, then regenerate `package-lock.json` once.

There is no safe CI analog in this repository. Create separately named lanes for deterministic pytest, optional live Ollama, Python lint, Python typing, TypeScript checking, frontend build, and environment-blocked checks. Use `uv lock --check`, locked/no-sync execution where appropriate, and `npm ci`; do not combine a blocked lane into a green deterministic result. Pin action revisions immutably.

Docker and shell/batch launchers currently embody the wrong dependency authority and mutating startup behavior. Wrappers may only delegate to the Python runtime CLI. The canonical entry points are `python -m aura_backend.runtime preflight` and `... serve` under the locked uv command described in research.

Ruff and Pyright additions require the research-mandated human legitimacy checkpoint; neither registry presence nor local availability licenses silently adding them.

## Shared Patterns

### Truthful terminal states

**Source:** `aura_backend/preservation/manifest.py:23-30,285-290`

Apply to provider outcomes, streams, readiness, preflight, live tests and CI. Missing, partial, blocked, unavailable, resource-limited or cancelled work is never success. Only `Completed` licenses a streamed answer.

### Privacy-safe diagnostics

**Source:** `aura_backend/preservation/manifest.py:155-166` and `tests/support/main_subprocess_probe.py:83-86`

Construct public payloads from allowlisted safe fields. Default logs may contain correlation ID, safe code, provider kind, model identifier where safe, duration and counts—not prompts, conversation content, tool arguments/results, credentials, raw URLs/headers, SDK objects, traceback, or exception strings.

### Pure import boundary

**Source:** `aura_backend/runtime_security.py:1-6` and Phase 1 subprocess probe.

Domain/config/health modules should be cheap and independently importable. Importing main or providers must not create clients, connect, scan/download models, spawn subprocesses or open databases. Lazy import the selected cloud adapter.

### Preserve the characterized public contract

**Source:** `tests/characterization/test_companion_contract.py:10-68`

Keep seven response keys, non-empty visible fallback, HTTP 200 on current provider failure, exactly one session clear, zero persistence on provider failure, and no hidden reasoning. Internally typed failures are an implementation truthfulness improvement; public API semantics change later.

### Local-only security boundary

**Source:** `runtime_security.py:13-16,35-41,110-122` and `main.py:1358-1369`

Retain loopback default, explicit origins and `allow_credentials=False`; do not add mandatory sign-in or accidentally make Windows/LAN binding the default.

### Test isolation

**Source:** `tests/support/main_subprocess_probe.py:89-130,139-220`

Use fakes behind production seams, network prohibition, bounded subprocesses, temporary working/storage roots, normalized volatile values, and explicit complete evidence. Deterministic tests require no Ollama, cloud, GPU, MCP server or persistent database.

## Patterns to Reuse vs Replace

| Reuse | Replace |
|---|---|
| Frozen/slotted typed records and string enums | Mutable `ProviderResponse` with `error` and `raw_response` |
| Explicit public allowlists | Serializing/logging raw exceptions or SDK objects |
| Pure validation helpers and named exceptions | Ambient environment parsing throughout constructors/routes |
| OpenAI-compatible message/tool schema conversion | Duplicate Ollama/OpenRouter transport loops |
| FastAPI lifespan hook and reverse shutdown intent | Global resource mutation and incomplete partial-start cleanup |
| Recording fakes, subprocess timeout, network prohibition | Live services or buffered streams in deterministic tests |
| Existing `/conversation` fallback and persistence call shape | Provider-name/SDK branching and Gemini-only analysis calls |
| `argparse` plus truthful integer exits | Install/sync/download/kill behavior in startup scripts |
| Strict pytest markers already in `pyproject.toml:51-59` | Collapsing live, lint, typing, build or blocked results into one green lane |

## No Safe Analog Found

| File/Concern | Reason | Planner Direction |
|---|---|---|
| `providers/runtime.py` stream state machine | Current providers buffer completed responses and have no cancellation registry. | Use the researched event/terminal contract; test first with event-gated fake. |
| Neutral MCP tool catalog/executor | Current orchestration depends on Gemini bridge internals. | Define provider-neutral immutable schemas; conversions stay adapter-local. |
| `tests/providers/test_streaming.py` | No real incremental stream test exists. | Build deterministic event-controlled tests; no sleeps as correctness evidence. |
| `tests/live/test_ollama_ornith.py` | Legacy live scripts print observations and are excluded from trustworthy pytest. | New marked, bounded, synthetic, truthfully skipped live lane. |
| `.github/workflows/ci.yml` | Repository has no workflow. | Follow the separate-lane contract and official locked uv/npm patterns from research. |
| Upstream cancellation guarantee | Existing code and provider docs cannot prove remote compute/billing stops. | Claim only local task/stream/client cleanup; report upstream cancellation as unknown. |
| Dependency cleanup safety for alternate entry points | Main import scan alone does not cover MCP/Memvid/Docker entry points. | Smoke supported entry points before each removal/group move; do not cross Phase 3 storage ownership. |

## Landmines and Stop Conditions

- Do not treat current provider files as authoritative for streaming, errors, retries, timeouts, session state, logging or close behavior.
- Do not let provider adapter tests pass while `main.py` analysis functions or MCP/autonomic paths still construct/use Gemini globals.
- Do not change the Phase 1 fallback, immediate persistence argument shape, local/no-auth behavior, storage paths, Chroma roots, or unresolved eight-row FK evidence.
- Do not call `BaseException`/broad catch paths around cancellation; cleanup then re-raise `CancelledError`.
- Do not claim startup/provider performance improvement from the single research baseline. Capture comparable cold/warm, first-delta, terminal and cancellation measurements.
- Do not read or print `.env` secret values. Preserve recognized key names and update only `.env.example` to a local-first, non-secret example.
- Do not remove Torch/Chroma merely because they are heavy; the characterized persistence path still uses them and Phase 3 owns storage replacement.
- Do not run `npm ci` casually against Ty's active `node_modules`; validate clean-install behavior in CI or a clean worktree/environment.
- Stop dependency-tool additions at the human checkpoint until Ruff/Pyright package legitimacy receives the required verdict.

## Metadata

**Analog search scope:** `aura_backend/providers`, `aura_backend/main.py`, `aura_backend/runtime_security.py`, `aura_backend/preservation`, root `tests`, manifests/launchers, Phase 1 verification/summaries, and all `.planning/codebase` maps.

**Files scanned:** 70+ source, test, planning and manifest candidates; 10 implementation/test analogs read closely.

**Pattern extraction date:** 2026-08-19

**Evidence note:** Phase 1 verification reports 131 deterministic tests passing and explicitly preserves the companion, persistence, local-only and fail-closed evidence contracts. That is the trusted baseline; legacy `aura_backend/tests` scripts are not analogs for new verification.
