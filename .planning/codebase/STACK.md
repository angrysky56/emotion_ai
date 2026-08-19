# Technology Stack

**Analysis Date:** 2026-08-19

## Languages

**Primary:**
- Python 3.12+ - FastAPI backend, MCP client/server, model-provider adapters, vector memory, persistence, and operational scripts in `aura_backend/`; the requirement is declared in `pyproject.toml` and the container base is Python 3.12 in `aura_backend/Dockerfile`.
- TypeScript 5.7 - Browser application in `index.tsx` and API client in `src/services/auraApi.ts`; compiler settings are in `tsconfig.json`.

**Secondary:**
- HTML and CSS - Vite entry shell and application styling in `index.html` and `index.css`.
- Bash and Windows batch - local lifecycle automation in `start_full_system.sh`, `stop_full_system.sh`, `start_full_system.bat`, and `stop_full_system.bat`.
- SQL/SQLite - Chroma persistence and direct maintenance queries in `aura_backend/robust_vector_db.py` and `aura_backend/main.py`; no separate schema or migration framework is present.

## Runtime

**Environment:**
- Python >=3.12 is the declared backend runtime in `pyproject.toml`; the inspected workspace provides Python 3.12.9.
- Node.js >=20 is effectively required by the locked `@google/genai` package in `package-lock.json`; the inspected workspace provides Node 24.19.0.
- Browser runtime with ES2020 and DOM APIs is targeted by `tsconfig.json`.

**Package Manager:**
- uv 0.11.21 is available and is the intended Python workflow, evidenced by `uv.lock`, `start_full_system.sh`, and `aura_backend/scripts/setup_uv.sh`.
- npm 11.17.0 is available for the frontend; `package-lock.json` lockfile version 3 is present.
- Python has two competing resolution artifacts: `uv.lock` and the pip-compatible `requirements.txt`. Their resolved versions differ (for example, `anthropic` 0.54.0 in `uv.lock` versus 0.99.0 in `requirements.txt`), so treat `uv.lock` as the uv environment and `requirements.txt` as the Docker/pip environment rather than assuming they are identical.

## Frameworks

**Core:**
- FastAPI 0.136.1 - HTTP API and lifecycle orchestration in `aura_backend/main.py`; MCP HTTP routes are added from `aura_backend/mcp_integration.py`.
- Uvicorn >=0.34.0 - ASGI server imported and launched by `aura_backend/main.py`.
- FastMCP 3.2.4 and MCP 1.27.0 in the resolved pip set - MCP server/client protocol support in `aura_backend/aura_server.py`, `aura_backend/mcp_client.py`, and `aura_backend/mcp_integration.py`.
- Vite 8.0.0 - frontend development server and production build configured by `vite.config.ts`.
- No frontend component framework is actually imported. `index.tsx` is a direct DOM/browser application even though `tsconfig.json` enables `react-jsx`.

**Testing:**
- pytest 9.0.3 and pytest-asyncio >=0.24.0 are declared in `pyproject.toml`; backend tests live under `aura_backend/tests/`.
- No JavaScript test runner is declared in `package.json` and there is no frontend test script.

**Build/Dev:**
- TypeScript ~5.7.2 performs strict, no-emit checking via `tsconfig.json` as part of Vite builds.
- Ruff and Pyright are configured in `pyproject.toml`; Ruff targets Python 3.12 with an 88-character line length, while Pyright uses basic type checking for `aura_backend/`.
- Docker builds a Python 3.12-slim backend image using `aura_backend/Dockerfile`; `aura_backend/docker-compose.yml` exists but was not inspected because compose files may contain inline secrets.

## Key Dependencies

**Critical and actually imported:**
- `google-genai` - primary Gemini provider and autonomic model calls in `aura_backend/providers/gemini.py`, `aura_backend/main.py`, and `aura_backend/aura_autonomic_system.py`.
- `openai` - OpenAI-compatible client used for both OpenRouter and Ollama in `aura_backend/providers/openrouter.py` and `aura_backend/providers/ollama.py`.
- `chromadb`, `numpy`, and `sentence-transformers` - persistent semantic memory and shared local embeddings in `aura_backend/robust_vector_db.py` and `aura_backend/shared_embedding_service.py`.
- `memvid-sdk` - optional compressed archival storage in `aura_backend/aura_real_memvid.py`; code explicitly falls back to placeholder/mock behavior if import or initialization fails.
- `aiofiles` and Pydantic - asynchronous filesystem persistence and API/protocol models in `aura_backend/main.py`, `aura_backend/conversation_persistence_service.py`, and `aura_backend/aura_server.py`.
- `marked` 18.0.3 - Markdown rendering imported by `index.tsx`.

**Declared but not imported by the active application path:**
- Python declarations `anthropic`, `asyncio-mqtt`, `beautifulsoup4`, `ebooklib`, `faiss-cpu`, `faiss-gpu-cu12`, `httpx`, `opencv-python`, `pandas`, `pillow`, `pypdf`, `pyzbar`, `qrcode`, and `websockets` are present in `pyproject.toml`, but repository-wide inspection found no imports in the active backend modules. Some appear only in setup/archive/test code such as `aura_backend/aura_memvid_setup.py` or are transitive/anticipated capabilities.
- Frontend `@google/genai` is declared in `package.json` and locked in `package-lock.json`, but neither `index.tsx` nor `src/services/auraApi.ts` imports it. Model calls occur in the backend.
- `torch` 2.11.0 is declared directly in `pyproject.toml` but is consumed indirectly by `sentence-transformers`; active code does not import `torch` itself.

## Configuration

**Environment:**
- Python loads dotenv configuration in `aura_backend/main.py`; `.env` and `.env.example` are present, but their contents were not read.
- Provider selection uses `AURA_DEFAULT_PROVIDER`; provider credentials/settings use `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and `AURA_MODEL` in `aura_backend/providers/factory.py`.
- The autonomic subsystem separately reads `GOOGLE_API_KEY`, `AURA_AUTONOMIC_MODEL`, `AUTONOMIC_ENABLED`, concurrency/rate/timeout variables, and `AFC_AUTONOMIC_MAX_REMOTE_CALLS` in `aura_backend/aura_autonomic_system.py`.
- Tool calling, persistence, thinking, CORS, and Memvid behavior are controlled through named variables read in `aura_backend/main.py`, `aura_backend/thinking_processor.py`, `aura_backend/mcp_to_gemini_bridge.py`, and `aura_backend/aura_real_memvid.py`.
- `vite.config.ts` injects `GEMINI_API_KEY` into the browser bundle as `process.env.API_KEY` and `process.env.GEMINI_API_KEY`; active frontend code does not consume either symbol. Do not add client-side model calls using this mechanism because it would expose the key.

**Build:**
- `package.json`, `package-lock.json`, `vite.config.ts`, and `tsconfig.json` define the frontend build.
- `pyproject.toml`, `uv.lock`, and `requirements.txt` define backend environments; `aura_backend/Dockerfile` installs the root-style `requirements.txt` name from its Docker build context, so the build context must make that file available.
- No `.nvmrc`, Node `engines` declaration, or Python version pin file was detected; runtime floors come from dependency metadata and `pyproject.toml`.

## Platform Requirements

**Development:**
- Python 3.12+, uv, Node.js 20+, and npm are required for the standard two-process workflow in `start_full_system.sh`.
- Default local ports are backend `8000` and Vite frontend `5173`, referenced in `start_full_system.sh` and `src/services/auraApi.ts`.
- Sentence-transformer model assets and Chroma data require local disk; optional Memvid support may require its own native/media dependencies. GPU packages are declared, but CPU FAISS is also declared and the active code does not prove that CUDA is mandatory.

**Production:**
- A backend Docker image is defined in `aura_backend/Dockerfile`, exposing ports 8000 and 8001 and running as a non-root `aura` user.
- No hosting platform, reverse proxy, deployment manifest, or CI workflow was detected. The frontend API client assumes the backend is reachable on port 8000 of the same hostname in `src/services/auraApi.ts`.

---

*Stack analysis: 2026-08-19*
