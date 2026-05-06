# Roadmap: Aura Modernization

## Milestone 1: Foundation & Providers
- [x] **Phase 1: Environment & Dependency Refresh**
  - [x] Update `pyproject.toml` and `package.json` to latest versions.
  - [x] Fix breaking changes in Pydantic/FastAPI.
  - [x] Set up `uv` virtual environment.
- **Phase 2: Unified Model Provider**
  - Create `ModelProvider` interface.
  - Implement OpenRouter driver.
  - Implement Ollama driver.
  - Add fallback logic.

## Milestone 2: Backend Refactoring
- **Phase 3: Modularization**
  - Extract services (Memory, Vision, Thinking) from `main.py`.
  - Implement FastAPI routers.
  - Harden JSON serialization.
- **Phase 4: Memory Stability**
  - Refactor ChromaDB integration for better concurrency.
  - Fix conflict/recovery scripts by making them unnecessary.

## Milestone 3: Frontend & UI Polish
- **Phase 5: State Management Refactor**
  - Separate `AuraUIManager` into UI Components and a State Store.
  - Polish the "Thinking" visualization.
- **Phase 6: Integration Testing & Optimization**
  - End-to-end testing of the new provider flow.
  - Performance profiling and latency reduction.

## Milestone 4: Final Polish
- **Phase 7: Final Cleanup & Documentation**
  - Remove deprecated scripts/files.
  - Update `BACKEND_API_SPEC.md`.
  - Final stability audit.
