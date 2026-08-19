# Codebase Structure

**Analysis Date:** 2026-08-19

## Directory Layout

```text
emotion_ai/
├── index.html                    # Browser shell and complete DOM layout
├── index.tsx                     # Imperative frontend application entry point
├── index.css                     # Global application styling
├── src/
│   └── services/
│       └── auraApi.ts            # Typed HTTP facade for the backend
├── aura_backend/
│   ├── main.py                   # FastAPI composition root and primary API
│   ├── providers/                # Model-provider abstraction/adapters
│   ├── tests/                    # Active backend test suite and test artifacts
│   ├── scripts/                  # Setup, cleanup, recovery, and wrapper scripts
│   ├── db_protection/            # Standalone backup/health utilities
│   ├── static/assets/            # Backend-side static image copies
│   ├── aura_data/                # Backend-local runtime JSON/log/export data
│   ├── aura_chroma_db/           # Backend-local live Chroma database
│   ├── memvid_data/              # Archive metadata/runtime data
│   ├── memvid_videos/            # Memvid archive binaries and WALs
│   ├── auto_backups/             # Generated database backups
│   ├── chromadb_backups/         # Generated/historical Chroma backups
│   └── archive_unused/           # Retired code, repair scripts, and old DB copies
├── aura_chroma_db/               # Root-level live/runtime Chroma database
├── aura_data/                    # Root-level runtime data tree
├── auto_backups/                 # Root-level generated database backups
├── memvid_data/                  # Root-level archive data directory
├── memvid_videos/                # Root-level archive binary directory
├── docs/                         # Current and archived operational documents/code
├── archive/                      # Retired frontend source
├── scratch/                      # Ad hoc workspace
├── .planning/                    # GSD project state, plans, and codebase maps
├── package.json                  # Frontend scripts/dependencies
├── pyproject.toml                # Python project/dependencies/tool configuration
├── vite.config.ts                # Vite configuration and root alias
├── tsconfig.json                 # TypeScript compiler configuration
├── start_full_system.sh          # Linux full-system launcher
└── stop_full_system.sh           # Linux full-system stopper
```

## Directory Purposes

**Repository root:**
- Purpose: Houses the Vite frontend, shared project configuration, launchers, and several runtime data trees.
- Contains: `index.html`, `index.tsx`, `index.css`, package manifests, API documentation, and shell/batch scripts.
- Key files: `index.tsx`, `package.json`, `pyproject.toml`, `start_full_system.sh`

**`src/services/`:**
- Purpose: Isolate browser-to-backend transport.
- Contains: TypeScript DTOs and the singleton `AuraAPI` client.
- Key files: `src/services/auraApi.ts`

**`aura_backend/`:**
- Purpose: Contains the Python API, provider adapters, persistence, MCP integration, memory/archival systems, operational scripts, tests, and backend-local data.
- Contains: Active Python modules plus generated data and extensive archived material.
- Key files: `aura_backend/main.py`, `aura_backend/conversation_persistence_service.py`, `aura_backend/robust_vector_db.py`, `aura_backend/mcp_system.py`

**`aura_backend/providers/`:**
- Purpose: Keep model-vendor implementations behind one normalized contract.
- Contains: Abstract DTO/provider definitions, factory, and Gemini/Ollama/OpenRouter adapters.
- Key files: `aura_backend/providers/base.py`, `aura_backend/providers/factory.py`, `aura_backend/providers/gemini.py`

**`aura_backend/tests/`:**
- Purpose: Exercise API, MCP, vector database, embeddings, serialization, setup, and regression fixes.
- Contains: `test_*.py`, diagnostic scripts, and a checked-in test Chroma database.
- Key files: `aura_backend/tests/test_aura_conversation.py`, `aura_backend/tests/test_vector_db.py`, `aura_backend/tests/test_mcp_integration.py`

**`aura_backend/scripts/`:**
- Purpose: Support installation, MCP wrapping/stopping, Chroma cleanup/recovery, and maintenance.
- Contains: Shell and Python operator scripts.
- Key files: `aura_backend/scripts/setup_uv.sh`, `aura_backend/scripts/aura_mcp_wrapper.py`, `aura_backend/scripts/recover_chromadb.py`

**`aura_backend/db_protection/`:**
- Purpose: Provide independently invocable database backup and health checks.
- Contains: Small Python utilities.
- Key files: `aura_backend/db_protection/auto_backup.py`, `aura_backend/db_protection/health_check.py`

**`docs/`:**
- Purpose: Hold a vision document plus retired deployment/integration material.
- Contains: `docs/aura_vision_assistance.md`, `docs/archive/`, and a stray `docs/main.py` snapshot/variant.
- Key files: `docs/aura_vision_assistance.md`, `docs/archive/INTEGRATION_GUIDE.md`

**Archive directories:**
- Purpose: Preserve obsolete implementations and backups outside the active module path.
- Contains: `archive/index_backup.tsx` and the much larger `aura_backend/archive_unused/` tree.
- Key files: `archive/index_backup.tsx`, `aura_backend/archive_unused/ARCHITECTURE.md`

## Key File Locations

**Entry Points:**
- `index.html`: Loads the Vite frontend module and defines the DOM contract.
- `index.tsx`: Constructs and initializes `AuraUIManager`.
- `aura_backend/main.py`: Defines the primary `FastAPI` app and direct Uvicorn launcher.
- `aura_backend/aura_server.py`: Standalone FastMCP server for Aura-native tools.
- `aura_backend/aura_as_mcp_server.py`: MCP-facing wrapper around Aura.
- `start_full_system.sh`: Starts backend and frontend processes on Linux.
- `aura_backend/start.sh`: Backend-specific startup path used by the full launcher.

**Configuration:**
- `package.json`: Vite build/dev commands and frontend dependencies.
- `pyproject.toml`: Python package metadata, dependencies, and tool configuration.
- `vite.config.ts`: Loads Vite environment data and defines `@` as the repository-root alias.
- `tsconfig.json`: TypeScript compiler behavior.
- `mcp_client_config.json`: Root MCP client/server configuration.
- `aura_backend/mcp_client_config.json`: Backend-local MCP configuration variant.
- `aura_backend/aura_as_mcp_config.json`: Configuration for the Aura MCP wrapper.
- `.env.example`: Example environment configuration; `.env` exists but its contents are intentionally not read.

**Core Logic:**
- `aura_backend/main.py`: HTTP routing and backend composition.
- `aura_backend/providers/`: Model provider contract and adapters.
- `aura_backend/conversation_persistence_service.py`: Conversation persistence coordinator.
- `aura_backend/robust_vector_db.py`: Active vector database used by `main.py`.
- `aura_backend/aura_internal_tools.py`: Aura-native callable tools.
- `aura_backend/mcp_system.py`: Active MCP startup facade.
- `aura_backend/aura_autonomic_system.py`: Optional background task subsystem.
- `aura_backend/memvid_archival_service.py`: Archive queue/service.

**Testing:**
- `aura_backend/tests/`: Primary test location.
- `aura_backend/scratch/test_memvid_v2.py`: Experimental Memvid test outside the main suite.
- `aura_backend/archive_unused/test_*.py`: Archived tests; do not treat as the active suite.

## Naming Conventions

**Files:**
- Python modules use lowercase snake_case: `conversation_persistence_service.py`, `shared_embedding_service.py`.
- Python tests use `test_<subject>.py`: `aura_backend/tests/test_vector_db.py`.
- Provider adapters use the provider name: `aura_backend/providers/gemini.py`, `aura_backend/providers/ollama.py`.
- The frontend entry uses the conventional root name `index.tsx`; the service uses camelCase `auraApi.ts`.
- Operational scripts use verb-oriented snake_case: `start_full_system.sh`, `recover_chromadb.py`.
- Archive/backup names frequently carry timestamps: `aura_backend/auto_backups/auto_backup_20260505_210800/`.

**Directories:**
- Python/runtime directories use lowercase snake_case: `aura_backend/`, `aura_chroma_db/`, `memvid_data/`.
- Provider and service grouping is shallow; most backend services remain directly under `aura_backend/`.
- Retired material is explicitly grouped under `archive/`, `docs/archive/`, or `aura_backend/archive_unused/`.

## Where to Add New Code

**New frontend feature:**
- Primary code: add a focused module under a new `src/` subdirectory and import it from `index.tsx`; avoid growing the 1,942-line UI manager.
- Backend calls: add typed methods and DTOs in `src/services/auraApi.ts`.
- Markup/style: update `index.html` and `index.css` only when the feature changes the DOM contract or global visuals.
- Tests: no frontend test directory or runner is currently detected; establish `src/**/*.test.ts` with a configured runner before adding isolated frontend tests.

**New API feature:**
- Primary code: create a focused service module under `aura_backend/`.
- Route: add a router module under a new `aura_backend/routers/` package and include it from `aura_backend/main.py`; do not add another large route body directly to `main.py`.
- Request/response models: colocate route-specific Pydantic models with the router, or shared models under a new `aura_backend/models/` package.
- Tests: `aura_backend/tests/test_<feature>.py`.

**New model provider:**
- Contract implementation: `aura_backend/providers/<provider>.py`.
- Registration/selection: `aura_backend/providers/factory.py`.
- Tests: `aura_backend/tests/test_<provider>_provider.py`.

**New internal tool:**
- Definition and dispatcher: `aura_backend/aura_internal_tools.py`.
- MCP/model schema translation only when required: `aura_backend/mcp_to_gemini_bridge.py`.
- Tests: `aura_backend/tests/test_<tool_subject>.py` or the existing `aura_backend/tests/test_tool_improvements.py` when extending that behavior.

**New persistence capability:**
- Conversation orchestration: `aura_backend/conversation_persistence_service.py`.
- Chroma-specific operations: `aura_backend/robust_vector_db.py`.
- File-based durable state: extract a shared module from `AuraFileSystem` in `aura_backend/main.py` before extending it, so HTTP and MCP entry points can share it.
- Tests: `aura_backend/tests/test_<persistence_subject>.py`.

**Utilities:**
- Shared backend helpers: add a narrowly named module under `aura_backend/`; no general utilities package exists.
- Operator/recovery utilities: `aura_backend/scripts/`.
- Do not place active code in `docs/`, `scratch/`, `archive/`, or `aura_backend/archive_unused/`.

## Special Directories

**`aura_chroma_db/` and `aura_backend/aura_chroma_db/`:**
- Purpose: Chroma/SQLite vector database state.
- Generated: Yes.
- Committed: Partly; root SQLite state and some backend collection files are tracked. Treat as user data, not source.

**`aura_data/` and `aura_backend/aura_data/`:**
- Purpose: User profiles, sessions, exports, logs, and backups.
- Generated: Yes.
- Committed: Mostly placeholders, with at least `aura_backend/aura_data/users/test_user.json` tracked.

**`auto_backups/`, `aura_backend/auto_backups/`, `aura_backend/chromadb_backups/`:**
- Purpose: Recovery snapshots and reports.
- Generated: Yes.
- Committed: Mixed; placeholders and many historical root database snapshots are tracked.

**`aura_backend/memvid_data/`, `aura_backend/memvid_videos/`, `aura_backend/aura_archives/`:**
- Purpose: Archive metadata, Memvid binaries/WALs, and compressed knowledge archives.
- Generated: Yes.
- Committed: Mixed; placeholders, demo archives, metadata, and archive binaries are tracked.

**`aura_backend/archive_unused/`:**
- Purpose: Retired implementations, repair/migration scripts, old tests, and damaged/backup database artifacts.
- Generated: No as a directory; much of its content is historical runtime output.
- Committed: Yes, extensively.

**`.venv/`, `aura_backend/.venv/`, `node_modules/`:**
- Purpose: Local Python and Node dependency installations.
- Generated: Yes.
- Committed: No.

**`.pytest_cache/`, `.ruff_cache/`, `.trunk/`:**
- Purpose: Test/lint/tool caches and Trunk tooling state.
- Generated: Yes.
- Committed: No in the inspected git index.

**`.planning/`:**
- Purpose: GSD project definition, roadmap, phase plans, state, and codebase reference maps.
- Generated: Tool-maintained planning material.
- Committed: Yes.

**`aura_backend/tests/test_aura_chroma_db/`:**
- Purpose: Persistent Chroma fixture/artifact used by vector database tests.
- Generated: Yes.
- Committed: Yes.

---

*Structure analysis: 2026-08-19*
