# External Integrations

**Analysis Date:** 2026-08-19

## APIs & External Services

**Model providers:**
- Google Gemini - default remote LLM provider and separate autonomic-processing provider.
  - SDK/client: `google-genai`, used by `aura_backend/providers/gemini.py`, `aura_backend/main.py`, and `aura_backend/aura_autonomic_system.py`.
  - Auth: `GEMINI_API_KEY` for the main provider; `GOOGLE_API_KEY` for the autonomic subsystem.
  - Selection/configuration: `AURA_DEFAULT_PROVIDER`, `AURA_MODEL`, `AURA_AUTONOMIC_MODEL`, and `THINKING_BUDGET` in `aura_backend/providers/factory.py` and `aura_backend/aura_autonomic_system.py`.
- OpenRouter - optional OpenAI-compatible remote model gateway.
  - SDK/client: `openai.AsyncOpenAI` with `https://openrouter.ai/api/v1` in `aura_backend/providers/openrouter.py`.
  - Auth: `OPENROUTER_API_KEY`; model: `OPENROUTER_MODEL`.
- Ollama - optional local OpenAI-compatible model server.
  - SDK/client: `openai.AsyncOpenAI` in `aura_backend/providers/ollama.py`.
  - Auth: no external credential; a literal placeholder client key is used because Ollama normally does not authenticate locally.
  - Endpoint/model: `OLLAMA_BASE_URL` defaults to `http://localhost:11434/v1`; `OLLAMA_MODEL` defaults to `llama3.1` in `aura_backend/providers/factory.py`.
- Anthropic is declared in `pyproject.toml` and resolved in both Python lock artifacts, but no active backend module imports or selects an Anthropic provider. Treat it as unused inventory, not a working integration.

**Frontend-to-backend API:**
- The browser calls the FastAPI service through `src/services/auraApi.ts`, using `http://localhost:8000` locally and port 8000 on the current hostname otherwise.
- The active API surface includes health, conversations, search, chat history, emotional analysis, exports, persistence, vector-database status, Memvid status, autonomic controls, and MCP operations defined in `aura_backend/main.py` and `aura_backend/mcp_integration.py`.
- The frontend has no direct model-provider integration. Although `vite.config.ts` defines browser-visible Gemini key symbols, `index.tsx` does not import `@google/genai` or use those symbols.

## Data Storage

**Databases:**
- ChromaDB persistent local vector store - primary semantic conversation memory.
  - Connection: local directory `./aura_chroma_db` by default in `aura_backend/robust_vector_db.py`; no environment connection string is used.
  - Client: `chromadb.PersistentClient` in `aura_backend/robust_vector_db.py`.
  - On-disk evidence: `aura_chroma_db/chroma.sqlite3` and multiple backup snapshots under `auto_backups/`.
- SQLite - embedded inside ChromaDB and also opened directly for integrity/optimization work in `aura_backend/robust_vector_db.py` and `aura_backend/main.py`.
  - Connection: filesystem paths, not a network database URL.
  - ORM/client: Python standard-library `sqlite3`; no ORM or migration framework is present.

**File Storage:**
- Local JSON/data hierarchy `./aura_data/{users,sessions,exports,backups}` is created by `AuraFileSystem` in `aura_backend/main.py`.
- Conversation persistence combines the vector database with filesystem-backed records through `aura_backend/conversation_persistence_service.py`.
- Memvid archival writes local `.mv2`/media archives under `./memvid_videos` by default in `aura_backend/aura_real_memvid.py` and `aura_backend/memvid_archival_service.py`.
- Local automatic and recovery backups are managed by `aura_backend/database_protection.py` and `aura_backend/scripts/recover_chromadb.py`; no cloud object-storage client is detected.

**Caching:**
- No Redis, Memcached, or external cache is detected.
- Provider chat sessions, MCP registries, and autonomic queues are process-local in-memory state in `aura_backend/providers/gemini.py`, `aura_backend/mcp_client.py`, and `aura_backend/aura_autonomic_system.py`.

## Authentication & Identity

**Auth Provider:**
- Not detected. FastAPI routes in `aura_backend/main.py` do not install an authentication dependency or identity middleware.
- `user_id` and `session_id` values are application-supplied identifiers in request bodies/paths, not authenticated identities.
- CORS is configurable through `ALLOWED_ORIGINS`; when absent and `DEV_MODE` defaults to true, `aura_backend/main.py` permits wildcard origins while also enabling credentials. CORS is browser access policy, not authentication.

## MCP Integrations

**Aura as MCP client:**
- `aura_backend/mcp_client.py` launches configured MCP servers as subprocesses over stdio, discovers tools/resources, and executes calls through the official Python `mcp` client.
- `aura_backend/mcp_system.py` looks for `mcp_client_config.json` at the project root or inside `aura_backend/`. Neither active config file is present, so the verified default runtime connects to zero external MCP servers unless an uncommitted/local config is supplied.
- `example_mcp_client_config.json` is an example only. It names memory, SQLite, Docker MCP, and Desktop Commander subprocesses, but includes machine-specific paths and is not selected by `aura_backend/mcp_system.py`; do not report these as verified live connections.
- `aura_backend/mcp_to_gemini_bridge.py` converts discovered MCP tools into Gemini function declarations and routes tool results back into model processing.

**Aura as MCP server:**
- `aura_backend/aura_server.py` exposes Aura memory capabilities through FastMCP.
- `aura_backend/aura_as_mcp_server.py` implements a separate lightweight JSON-RPC/stdin-stdout server, but its tool execution is explicitly mock/demo behavior rather than a production data bridge.
- `aura_companion_mcp_server.json.example` shows how an external MCP host could start `aura_backend/aura_server.py`; it is a path template, not an active registration.
- FastAPI also exposes MCP management and execution routes under `/mcp` via `aura_backend/mcp_integration.py` and additional compatibility endpoints in `aura_backend/main.py`.

## Monitoring & Observability

**Error Tracking:**
- No hosted error-tracking integration is detected.

**Logs:**
- Python standard-library `logging` writes structured operational messages to process output throughout `aura_backend/`; MCP server logs are deliberately directed to stderr in `aura_backend/aura_as_mcp_server.py` to keep protocol stdout clean.
- Browser diagnostics use `console.log`, `console.warn`, and request IDs in `src/services/auraApi.ts`.
- Health/status endpoints for the API, MCP, persistence, Memvid, ChromaDB, database protection, and autonomic subsystem are defined in `aura_backend/main.py`.

## CI/CD & Deployment

**Hosting:**
- No managed host is configured. `aura_backend/Dockerfile` is the only verified deployment packaging; `aura_backend/docker-compose.yml` exists but its contents were not inspected because compose files may contain inline secrets.
- Local orchestration is provided by `start_full_system.sh`/`.bat` and matching stop scripts.

**CI Pipeline:**
- Not detected; no workflow files are present under `.github/workflows/`.

## Environment Configuration

**Required env vars:**
- For the default Gemini path: `GEMINI_API_KEY` is required by `aura_backend/providers/factory.py`.
- For optional OpenRouter: `OPENROUTER_API_KEY`; optional selectors are `OPENROUTER_MODEL` and `AURA_DEFAULT_PROVIDER`.
- For the autonomic Gemini subsystem when enabled: `GOOGLE_API_KEY` is read by `aura_backend/aura_autonomic_system.py`.
- Optional local/provider controls: `AURA_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and `THINKING_BUDGET`.
- Optional HTTP/persistence controls: `ALLOWED_ORIGINS`, `DEV_MODE`, `SESSION_RECOVERY_ENABLED`, `IMMEDIATE_PERSISTENCE_ENABLED`, `PERSISTENCE_TIMEOUT`, and `EMERGENCY_PERSISTENCE_RETRIES`.
- Optional autonomic controls: `AUTONOMIC_ENABLED`, `AURA_AUTONOMIC_MODEL`, `AURA_AUTONOMIC_MAX_OUTPUT_TOKENS`, `AUTONOMIC_MAX_CONCURRENT_TASKS`, `AUTONOMIC_TASK_THRESHOLD`, `AUTONOMIC_TIMEOUT_SECONDS`, `AUTONOMIC_RATE_LIMIT_RPM`, `AUTONOMIC_RATE_LIMIT_RPD`, `AUTONOMIC_QUEUE_MAX_SIZE`, and `AFC_AUTONOMIC_MAX_REMOTE_CALLS`.
- Optional tool/thinking controls: `AURA_MAX_OUTPUT_TOKENS`, `THINKING_DEBUG`, `TOOL_CALL_MAX_RETRIES`, `TOOL_CALL_RETRY_DELAY`, `TOOL_CALL_EXPONENTIAL_BACKOFF`, `TOOL_CALL_SEQUENTIAL_MODE`, `TOOL_CALL_TIMEOUT`, and `TOOL_CALL_HEARTBEAT_INTERVAL`.
- Optional Memvid controls: `MEMVID_EMBEDDING_PROVIDER` and `MEMVID_EMBEDDING_MODEL`.

**Secrets location:**
- `.env` and `.env.example` exist at the project root. Their contents and all values were intentionally not read. Runtime loading occurs through `python-dotenv` in `aura_backend/main.py`.
- MCP server configurations may carry per-server environment maps in `mcp_client_config.json`, as supported by `aura_backend/mcp_client.py`; no active config file is committed.
- `vite.config.ts` is capable of embedding `GEMINI_API_KEY` into client JavaScript. This is not a safe secrets boundary even though current frontend code does not consume the injected value.

## Webhooks & Callbacks

**Incoming:**
- No webhook-specific endpoint, signature verification, or third-party callback handler is detected in `aura_backend/main.py` or `aura_backend/mcp_integration.py`.
- Ordinary incoming HTTP API routes and MCP-over-HTTP management endpoints are present, but they are not registered third-party webhooks.

**Outgoing:**
- No outgoing webhook delivery mechanism is detected.
- Outbound network activity is limited to the selected model provider and optional local Ollama endpoint; optional MCP servers run as stdio subprocesses rather than webhook callbacks.

## Operational Dependencies

- The backend expects writable local directories for ChromaDB, user/session/export data, backups, and Memvid archives, created or referenced by `aura_backend/main.py`, `aura_backend/robust_vector_db.py`, and `aura_backend/memvid_archival_service.py`.
- The shared embedding service loads a `sentence-transformers` model in `aura_backend/shared_embedding_service.py`, which may require first-run model download/cache access even though no explicit hosted embedding API is configured.
- External MCP use requires executables named in a user-supplied `mcp_client_config.json` (commonly `uv`, `uvx`, `npx`, or another server command) to exist on the host; `aura_backend/mcp_client.py` does not install them.
- Memvid is optional at runtime: `aura_backend/aura_real_memvid.py` and `aura_backend/memvid_archival_service.py` explicitly degrade to unavailable/mock behavior when the SDK cannot initialize.

---

*Integration audit: 2026-08-19*
