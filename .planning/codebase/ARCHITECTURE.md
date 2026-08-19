<!-- refreshed: 2026-08-19 -->
# Architecture

**Analysis Date:** 2026-08-19

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│ Browser UI (Vite, imperative DOM)                           │
│ `index.html` → `index.tsx`                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ JSON over HTTP, localhost/:8000
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Typed frontend API singleton                                │
│ `src/services/auraApi.ts`                                   │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ FastAPI application and orchestration                       │
│ `aura_backend/main.py`                                      │
├─────────────────┬──────────────────┬────────────────────────┤
│ Model providers │ MCP/tool system  │ Emotion/cognition      │
│ `providers/`    │ `mcp_*.py`       │ functions in `main.py` │
└────────┬────────┴────────┬─────────┴───────────┬────────────┘
         │                 │                     │
         ▼                 ▼                     ▼
┌─────────────────┐ ┌──────────────────┐ ┌────────────────────┐
│ Gemini/Ollama/  │ │ MCP subprocesses │ │ Persistence        │
│ OpenRouter APIs │ │ + internal tools │ │ Chroma + JSON      │
└─────────────────┘ └──────────────────┘ │ `aura_chroma_db/`  │
                                         │ `aura_data/`       │
                                         └────────────────────┘
```

Verified: the normal user-facing runtime is the Vite browser process plus the FastAPI process started by `start_full_system.sh`. `aura_backend/aura_server.py` and `aura_backend/aura_as_mcp_server.py` are separate MCP-server entry points, not part of the browser-to-FastAPI request path.

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Browser shell | Supplies the complete static DOM targeted by the UI manager | `index.html` |
| UI manager | Owns browser state, DOM mutation, events, chat rendering, history, status panels, and local username persistence | `index.tsx` |
| API client | Defines frontend request/response types and centralizes HTTP timeout, retry, health, conversation, search, history, and diagnostic calls | `src/services/auraApi.ts` |
| API composition root | Creates global services during FastAPI lifespan and exposes all HTTP routes | `aura_backend/main.py` |
| Provider contract | Normalizes messages, responses, tool calls, streaming, and session cleanup | `aura_backend/providers/base.py` |
| Provider selection | Selects Gemini, Ollama, or OpenRouter from configuration | `aura_backend/providers/factory.py` |
| Provider adapters | Implement provider-specific generation and session/tool behavior | `aura_backend/providers/gemini.py`, `aura_backend/providers/ollama.py`, `aura_backend/providers/openrouter.py` |
| Conversation persistence | Coordinates atomic/immediate storage, fallback retries, history retrieval, and profile updates | `aura_backend/conversation_persistence_service.py` |
| Vector store | Provides process-safe Chroma collections and conversation/emotion/cognition operations | `aura_backend/robust_vector_db.py` |
| File store | Stores JSON profiles, sessions, logs, and exports | `AuraFileSystem` in `aura_backend/main.py` |
| Internal tools | Exposes memory, profile, emotional-analysis, archive, and organization operations to the tool layer | `aura_backend/aura_internal_tools.py` |
| MCP composition | Initializes the active MCP client and Gemini bridge used by `main.py` | `aura_backend/mcp_system.py` |
| MCP client/bridge | Discovers external MCP tools and translates/executes model function calls | `aura_backend/mcp_client.py`, `aura_backend/mcp_to_gemini_bridge.py` |
| Autonomic worker | Queues and executes optional background tasks derived from conversations | `aura_backend/aura_autonomic_system.py` |
| Memvid archive | Queues archival work and searches/list archives | `aura_backend/memvid_archival_service.py` |
| Database protection | Creates backups and supplies health/protection operations | `aura_backend/database_protection.py` |

## Pattern Overview

**Overall:** Layered client/server application with a monolithic API composition root and adapter-based model providers.

**Key Characteristics:**
- Keep browser transport behind the `AuraAPI` singleton in `src/services/auraApi.ts`; `index.tsx` should consume that interface rather than add direct `fetch` calls.
- Construct backend services in the `lifespan` function in `aura_backend/main.py`; routes depend on module-level references populated at startup.
- Implement model-specific behavior behind `BaseProvider` in `aura_backend/providers/base.py`, selected through `ModelProviderFactory` in `aura_backend/providers/factory.py`.
- Treat conversation storage as dual persistence: Chroma collections through `aura_backend/robust_vector_db.py` plus JSON/files through `AuraFileSystem` in `aura_backend/main.py`.
- Treat external tools as a process boundary: MCP servers are configured in `mcp_client_config.json`, discovered by `aura_backend/mcp_client.py`, and adapted by `aura_backend/mcp_to_gemini_bridge.py`.

## Layers

**Presentation:**
- Purpose: Render chat, settings, history, emotion/cognition state, thinking detail, and system status.
- Location: `index.html`, `index.css`, `index.tsx`
- Contains: Static markup plus one large imperative `AuraUIManager` class.
- Depends on: Browser DOM/localStorage, `marked`, and `src/services/auraApi.ts`.
- Used by: The end user through the Vite entry point.

**Client transport:**
- Purpose: Provide stable typed methods over backend HTTP endpoints.
- Location: `src/services/auraApi.ts`
- Contains: DTO interfaces, connection state, request IDs, retries, timeout control, and endpoint methods.
- Depends on: Browser `fetch`, `AbortController`, and `window.location`.
- Used by: `AuraUIManager` in `index.tsx`.

**HTTP application/orchestration:**
- Purpose: Validate requests, coordinate providers/tools/memory, and shape responses.
- Location: `aura_backend/main.py`
- Contains: FastAPI lifecycle, route handlers, domain dataclasses, emotion/cognition detection, filesystem state, and service globals.
- Depends on: Nearly every active backend subsystem.
- Used by: `src/services/auraApi.ts` and operational clients.

**Model provider adapters:**
- Purpose: Normalize generation across hosted Gemini, local Ollama, and OpenRouter.
- Location: `aura_backend/providers/`
- Contains: `BaseProvider`, normalized DTOs, factory, and three concrete adapters.
- Depends on: Google GenAI or OpenAI-compatible SDKs; optional MCP client/internal tools.
- Used by: Conversation processing in `aura_backend/main.py`.

**Tool integration:**
- Purpose: Combine Aura-native memory tools with tools exposed by external MCP servers.
- Location: `aura_backend/mcp_system.py`, `aura_backend/mcp_client.py`, `aura_backend/mcp_to_gemini_bridge.py`, `aura_backend/aura_internal_tools.py`
- Contains: Discovery, schema conversion, invocation, retry/progress tracking, and internal tool dispatch.
- Depends on: MCP server configuration and persistence services.
- Used by: Provider adapters and `/mcp/*` HTTP routes in `aura_backend/main.py`.

**Persistence and archival:**
- Purpose: Persist conversations and derived state, retrieve semantic history, protect databases, and move old material to Memvid archives.
- Location: `aura_backend/conversation_persistence_service.py`, `aura_backend/robust_vector_db.py`, `aura_backend/database_protection.py`, `aura_backend/memvid_archival_service.py`
- Contains: Immediate/fallback writes, Chroma access, file locks, backup operations, and archive queues.
- Depends on: Chroma/SQLite, embeddings, filesystem paths, and optional Memvid support.
- Used by: API routes, internal tools, and background autonomic work.

## Data Flow

### Primary Conversation Path

1. Form events in `AuraUIManager` collect the message and current user/session state (`index.tsx:23`).
2. The UI calls the singleton transport, which POSTs a typed payload to `/conversation` with timeout/retry handling (`src/services/auraApi.ts:114`).
3. FastAPI validates `ConversationRequest`, resolves or creates the session, and retrieves relevant prior conversations (`aura_backend/main.py:1542`).
4. `get_aura_system_instruction` composes user, memory, and available-tool context (`aura_backend/main.py:742`).
5. The configured `BaseProvider` generates a normalized `ProviderResponse`; provider code may invoke internal or MCP tools (`aura_backend/providers/base.py`, `aura_backend/providers/gemini.py`).
6. The route optionally submits autonomic work and runs user emotion, Aura emotion, and cognitive-focus detection (`aura_backend/main.py:892`, `aura_backend/main.py:1008`, `aura_backend/main.py:1119`).
7. `ConversationPersistenceService` attempts immediate dual persistence with emergency retry and background fallback (`aura_backend/conversation_persistence_service.py`, `aura_backend/main.py:1542`).
8. FastAPI returns `ConversationResponse`; `AuraUIManager` renders text via `marked` and updates emotion/cognition/status DOM (`index.tsx`).

### Startup and Shutdown Flow

1. `start_full_system.sh` starts backend and frontend in separate terminals; Vite serves port 5173 and Uvicorn serves port 8000.
2. FastAPI lifespan initializes protection first, then vector/file/state/internal tools, MCP, provider, persistence, archival, and optional autonomic services (`aura_backend/main.py:1207`).
3. On shutdown, lifespan closes background and external resources in reverse operational order (`aura_backend/main.py:1207`).

### Memory Search and History

1. `/search` and `/chat-history/{user_id}` enter through routes in `aura_backend/main.py:2431` and `aura_backend/main.py:2849`.
2. `ConversationPersistenceService` coordinates vector results and filesystem/session records (`aura_backend/conversation_persistence_service.py`).
3. `RobustAuraVectorDB` queries Chroma collections and returns normalized dictionaries (`aura_backend/robust_vector_db.py`).
4. `AuraAPI` converts responses to frontend DTOs and `AuraUIManager` rebuilds the history list/message view (`src/services/auraApi.ts`, `index.tsx`).

### Tool Execution Boundary

1. `initialize_mcp_system` loads configured MCP servers and registers Aura internal tools (`aura_backend/mcp_system.py:26`).
2. `MCPGeminiBridge` converts discovered schemas into model-callable function definitions (`aura_backend/mcp_to_gemini_bridge.py:128`).
3. A provider-originated function call is routed either to `AuraInternalTools.execute_tool` or an MCP subprocess through the client (`aura_backend/aura_internal_tools.py:564`, `aura_backend/mcp_client.py`).
4. Results are made JSON-safe and returned to the model; `/mcp/execute-tool` also exposes explicit HTTP invocation (`aura_backend/main.py:3113`).

**State Management:**
- Browser state is held inside one `AuraUIManager` instance; username persists in localStorage (`index.tsx`).
- Backend state is largely module-global and initialized during FastAPI lifespan: provider, vector DB, file system, persistence, bridge, autonomic service, and active session maps (`aura_backend/main.py`).
- Durable state lives in Chroma/SQLite directories and JSON session/user directories; generated archives/backups occupy separate runtime directories.

## Key Abstractions

**`AuraAPI`:**
- Purpose: Backend facade for the browser.
- Examples: `src/services/auraApi.ts`
- Pattern: Eager singleton with generic request helper and typed endpoint methods.

**`BaseProvider`:**
- Purpose: Isolate backend orchestration from model vendor APIs.
- Examples: `aura_backend/providers/base.py`, `aura_backend/providers/gemini.py`, `aura_backend/providers/ollama.py`, `aura_backend/providers/openrouter.py`
- Pattern: Abstract adapter plus factory.

**`ConversationPersistenceService`:**
- Purpose: Make a user/assistant exchange the persistence unit and coordinate multiple stores/recovery paths.
- Examples: `aura_backend/conversation_persistence_service.py`
- Pattern: Service layer with an exchange DTO and immediate/fallback write strategies.

**`RobustAuraVectorDB`:**
- Purpose: Encapsulate Chroma collections, locking, recovery, searches, analytics, and deletion.
- Examples: `aura_backend/robust_vector_db.py`
- Pattern: Process-wide singleton (`__new__`) with async operation guards.

**`AuraInternalTools`:**
- Purpose: Present memory and profile capabilities through the same callable-tool shape as external MCP tools.
- Examples: `aura_backend/aura_internal_tools.py`
- Pattern: Registry/dispatcher.

## Entry Points

**Browser application:**
- Location: `index.html`, `index.tsx:1934`
- Triggers: Vite loads the TypeScript module; DOM readiness triggers `AuraUIManager.initialize()`.
- Responsibilities: Bind DOM, check backend, load user/history, start chat, and schedule refreshes.

**FastAPI application:**
- Location: `aura_backend/main.py:1207`, `aura_backend/main.py:4242`
- Triggers: `uvicorn aura_backend.main:app` or direct Python execution.
- Responsibilities: Own lifecycle, HTTP endpoints, service composition, and background tasks.

**Aura MCP server:**
- Location: `aura_backend/aura_server.py:1006`
- Triggers: Direct script/process invocation.
- Responsibilities: Expose Aura memory/emotion/profile/capability tools through FastMCP.

**Companion MCP wrapper:**
- Location: `aura_backend/aura_as_mcp_server.py`
- Triggers: MCP client configuration invoking the script.
- Responsibilities: Present the running Aura backend as an MCP-accessible service.

**Operational launchers:**
- Location: `start_full_system.sh`, `aura_backend/start.sh`, `aura_backend/start_all.sh`, `aura_backend/start_api.sh`, `aura_backend/start_mcp.sh`
- Triggers: Operator shell invocation.
- Responsibilities: Start specific combinations of frontend, API, and MCP processes.

## Architectural Constraints

- **Threading:** FastAPI and MCP work use an asyncio event loop; blocking database/model libraries are wrapped inconsistently, while autonomic and archival services maintain background queues/tasks in `aura_backend/aura_autonomic_system.py` and `aura_backend/memvid_archival_service.py`.
- **Global state:** The API relies on mutable module globals and maps in `aura_backend/main.py`; service access before lifespan completion is invalid.
- **Single-instance assumptions:** `AuraAPI` in `src/services/auraApi.ts` and `RobustAuraVectorDB` in `aura_backend/robust_vector_db.py` are singletons. Multi-worker deployment requires verifying Chroma and session-map semantics.
- **Filesystem coupling:** Relative data paths depend on launch working directory; startup scripts deliberately change into `aura_backend/`, while some root-level runtime directories also exist.
- **No authentication boundary:** HTTP routes accept caller-supplied `user_id`; no authentication middleware is present in `aura_backend/main.py`.
- **Circular imports:** No circular chain was verified in the inspected active modules. The dense cross-import graph around `main.py`, MCP, internal tools, and persistence makes new reverse imports into `main.py` unsafe.

## Anti-Patterns

### Bypassing the Frontend API Facade

**What happens:** `index.tsx:1729` directly fetches `http://localhost:8000/memvid/status` even though other backend calls use `AuraAPI`.
**Why it's wrong:** It bypasses base-URL selection, request IDs, retry/timeout behavior, and production-host support in `src/services/auraApi.ts`.
**Do this instead:** Add an endpoint method to `AuraAPI` in `src/services/auraApi.ts` and call it from `index.tsx`.

### Multiple Competing MCP Implementations

**What happens:** Active-looking MCP orchestration exists in `aura_backend/mcp_system.py`/`aura_backend/mcp_client.py`, while a second manager/router stack remains in `aura_backend/mcp_integration.py`; standalone servers add further paths in `aura_backend/aura_server.py` and `aura_backend/aura_as_mcp_server.py`.
**Why it's wrong:** Ownership and lifecycle are ambiguous; `main.py` imports the router from one stack but initializes another, increasing drift risk.
**Do this instead:** Treat `aura_backend/mcp_system.py` plus `aura_backend/mcp_client.py` as the startup authority, document explicit standalone server boundaries, and consolidate HTTP routing behind that authority.

### Monolithic Composition and Domain Module

**What happens:** `aura_backend/main.py` combines lifecycle wiring, DTOs, filesystem persistence, emotion/cognition inference, session state, and more than twenty routes in 4,256 lines.
**Why it's wrong:** Changes cross unrelated responsibilities and make import/lifecycle testing difficult.
**Do this instead:** Keep `main.py` as the composition root, move route groups into routers and domain logic into services, following the existing provider boundary in `aura_backend/providers/`.

### Duplicate Domain and Storage Implementations

**What happens:** Emotional DTOs and `AuraFileSystem` exist in both `aura_backend/main.py` and `aura_backend/aura_server.py`; vector classes exist in `aura_backend/enhanced_vector_db.py`, `aura_backend/robust_vector_db.py`, and compatibility code.
**Why it's wrong:** Behavior can diverge between HTTP and MCP entry points.
**Do this instead:** Extract shared domain models/filesystem services and designate `aura_backend/robust_vector_db.py` as the current backend store adapter used by `main.py`.

## Error Handling

**Strategy:** Best-effort degradation with extensive logging, explicit HTTP errors for validation/route failures, and fallback behavior for model, tool, and persistence failures.

**Patterns:**
- `AuraAPI.makeRequest` retries retryable failures with exponential backoff and jitter, and aborts on a long request timeout (`src/services/auraApi.ts`).
- FastAPI routes catch broad exceptions, log them, and either raise `HTTPException` or return fallback responses (`aura_backend/main.py`).
- Conversation writes attempt immediate persistence, emergency retries, then a background backup (`aura_backend/main.py`, `aura_backend/conversation_persistence_service.py`).
- MCP bridge calls track execution, retry selected failures, and make tool results JSON-safe (`aura_backend/mcp_to_gemini_bridge.py`).

## Cross-Cutting Concerns

**Logging:** Python modules use the standard `logging` package with emoji-heavy operational messages; frontend code uses `console` (`aura_backend/main.py`, `index.tsx`).
**Validation:** Pydantic validates HTTP and MCP request models; provider and persistence boundaries still pass many `Dict[str, Any]` values (`aura_backend/main.py`, `aura_backend/providers/base.py`).
**Authentication:** Not detected in the active FastAPI middleware/routes (`aura_backend/main.py`).
**Serialization:** NumPy and provider/tool values are normalized before HTTP/model use in `aura_backend/main.py` and `aura_backend/mcp_to_gemini_bridge.py`.
**Data protection:** Backup-before-operation and health endpoints are supplied by `aura_backend/database_protection.py` and wired in `aura_backend/main.py`.

---

*Architecture analysis: 2026-08-19*
