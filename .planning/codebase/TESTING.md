# Testing - Emotion AI / Aura

## Testing Philosophy
Aura emphasizes robustness through automated testing, especially for its complex memory and AI reasoning layers. The project uses a mix of unit, integration, and comprehensive system tests.

## Backend Testing
- **Tool**: `pytest` with `pytest-asyncio`.
- **Location**: `aura_backend/tests/` and root `test_*.py` files.
- **Key Test Suites**:
  - `test_chroma_db/`: Vector database operations and similarity searches.
  - `test_memvid_integration.py`: Video memory lifecycle and retrieval.
  - `test_interprocess_locking.py`: Concurrency and database safety tests.
  - `test_shared_embedding.py`: Validates embedding consistency across services.
  - `test_tool_improvements.py`: Functional tests for MCP tools.

## Frontend Testing
- Currently relies on manual verification and dev-server feedback.
- Future work includes integrating a testing framework (e.g., Vitest or Playwright).

## Continuous Integration
- Linting and formatting are enforced by Trunk.
- Pre-commit checks (via Trunk) run linters and potentially tests before code is committed.

## Running Tests
- **Backend**: `cd aura_backend && pytest`
- **System**: Scripts like `test_comprehensive_fixes.py` can be used to validate the full integration.
