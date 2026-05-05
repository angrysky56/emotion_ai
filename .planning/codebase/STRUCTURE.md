# Structure - Emotion AI / Aura

## Root Directory
- `/aura_backend/`: Core Python backend application.
- `/src/`: Frontend TypeScript logic and services.
- `/docs/`: General project documentation and guides.
- `/scripts/`: Automation scripts (setup, management).
- `/auto_backups/`: Automated system backups.
- `index.tsx`: Main frontend entry point and UI manager.
- `index.css`: Global styles and design system.
- `vite.config.ts`: Frontend build configuration.
- `pyproject.toml`: Root package configuration (if applicable).
- `CLAUDE.md`: AI assistant instructions and project context.
- `BACKEND_API_SPEC.md`: Documentation for backend REST endpoints.

## Aura Backend (`/aura_backend/`)
- `main.py`: FastAPI application entry point.
- `aura_server.py`: Core server logic.
- `thinking_processor.py`: Advanced reasoning and reflection engine.
- `mcp_*.py`: MCP server and client implementations.
- `*_memory_manager.py`: Semantic memory and vector DB handling.
- `aura_data/`: Local storage for embeddings and state.
- `memvid_data/`: Local storage for video memory metadata.
- `memvid_videos/`: Storage for recorded video segments.
- `tests/`: Backend test suite.
- `pyproject.toml` / `uv.lock`: Backend dependency management.

## Frontend Services (`/src/services/`)
- `auraApi.ts`: Singleton API client for backend communication.

## Documentation (`/docs/`)
- `THINKING_GUIDE.md`: Deep dive into the thinking processor logic.
- `STARTUP_GUIDE.md`: Instructions for running the full system.
- `Frontend-README.md`: Frontend-specific developer notes.
