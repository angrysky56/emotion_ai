# Testing Patterns

**Analysis Date:** 2026-08-19

## Test Framework

**Runner:**
- Pytest 9.0.3 is declared in `pyproject.toml`; `pytest-asyncio>=0.24.0` is also declared.
- No `pytest.ini`, `[tool.pytest.ini_options]`, `conftest.py`, marker configuration, or dedicated test script exists.
- There is no JavaScript/TypeScript test runner or DOM/E2E framework in `package.json`.

**Assertion Library:**
- Pytest's native `assert` would be available, but no `assert` statements occur in the active top-level Python files under `aura_backend/tests/`.
- Test-like scripts instead print status and return booleans, for example `aura_backend/tests/test_comprehensive_fixes.py` and `aura_backend/tests/test_numpy_serialization.py`.

**Run Commands:**
```bash
uv run pytest aura_backend/tests             # Intended suite; currently aborts during collection
uv run pytest --collect-only -q aura_backend/tests  # Reproduces the collection failure
npm run build                                # Builds frontend; does not run tests or TypeScript type-checking
npx tsc --noEmit                             # Declared TS quality check; currently fails on archived sources
uv run ruff check aura_backend --exclude aura_backend/archive_unused  # Currently reports six findings
```

`README.md` mentions `pytest tests/`, but from the repository root that path does not match the actual `aura_backend/tests/` location. `aura_backend/THINKING_GUIDE.md` names `tests/test_thinking_integration.py`, which is not present.

## Test File Organization

**Location:**
- Active test and diagnostic scripts are grouped in `aura_backend/tests/` rather than co-located with production modules.
- Historical tests also remain in `aura_backend/archive_unused/`; they are not part of a reliable active suite.
- `aura_backend/scratch/test_memvid_v2.py` is a manual SDK probe outside the test directory.

**Naming:**
- Sixteen top-level files match `aura_backend/tests/test_*.py`; pytest also discovers `quick_test.py` because its filename ends in `_test.py`.
- Non-collected diagnostics use names such as `debug_thinking.py`, `debug_thinking_response.py`, `diagnose_memory_manager.py`, and `validate_gemini_fixes.py`.
- Some matching `test_*.py` files contain only a `main()` entry point and no pytest test, notably `aura_backend/tests/test_mcp_client.py`.

**Structure:**
```text
aura_backend/tests/
├── test_*.py                 # Mixed pytest-discoverable functions and standalone scripts
├── quick_test.py             # Pytest-discoverable smoke functions plus a manual main
├── debug_*.py                # Manual diagnostics
├── diagnose_memory_manager.py
├── validate_gemini_fixes.py
└── test_aura_chroma_db/      # Checked-in binary Chroma test data
```

## Test Structure

**Suite Organization:**
```python
# Representative actual pattern from aura_backend/tests/test_comprehensive_fixes.py
def test_api_endpoints_structure():
    content = open(main_py_path).read()
    if expected_text not in content:
        return False
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

**Patterns:**
- Setup is local and imperative. Scripts mutate `sys.path`, instantiate real services, and use fixed filesystem locations; there are no fixtures in `aura_backend/tests/`.
- Teardown is usually a `finally` block for live MCP clients (`aura_backend/tests/test_mcp_client.py`) or explicit shutdown at the end of a coroutine (`aura_backend/tests/test_mcp_integration.py`).
- “Assertions” are `if` branches that print pass/fail and return booleans. Under pytest, a false return does not fail a test and produces only a return-value warning.
- Many scripts preserve a separate `main()` runner that aggregates booleans and sets the process exit code. Their meaningful behavior therefore depends on direct script execution, not pytest.
- `aura_backend/tests/test_aura_parameter_fix.py` calls `sys.exit(1)` during import when its top-level import fails. As observed on 2026-08-19, this aborts the entire pytest collection after four items are found.
- Async tests are undecorated. They rely on pytest-asyncio's installed behavior without a declared `asyncio_mode` or explicit `@pytest.mark.asyncio`, making execution dependent on plugin defaults.

## Mocking

**Framework:** Not detected.

**Patterns:**
```python
# aura_backend/tests/test_numpy_serialization.py constructs synthetic data,
# but does not replace an application dependency.
mock_tool_result = {
    "count": np.int64(42),
    "scores": np.array([0.95, 0.87, 0.92]),
}
```

**What to Mock:**
- No established repository pattern exists. External model providers, MCP subprocesses, time, filesystem state, ChromaDB, and network clients are generally exercised directly or not exercised.

**What NOT to Mock:**
- No documented boundary exists. The closest thing to unit isolation is hand-built dictionaries used to test serialization and parser logic in `aura_backend/tests/test_numpy_serialization.py` and `aura_backend/tests/test_mcp_integration.py`.

## Fixtures and Factories

**Test Data:**
```python
# Representative inline cases from aura_backend/tests/test_aura_parameter_fix.py
test_cases = [
    {"description": "...", "input": {...}, "expected": {...}},
]
```

**Location:**
- Data is embedded inside scripts rather than exposed through reusable fixtures or factories.
- A persistent ChromaDB artifact is checked into `aura_backend/tests/test_aura_chroma_db/`; tests also create/use local paths such as `./test_db` in `aura_backend/tests/test_ui_improvements.py`.
- There is no fixture lifecycle guaranteeing isolated temporary databases, user IDs, environment variables, or cleanup.

## Coverage

**Requirements:** None enforced. `pytest-cov` is not declared, no coverage configuration exists, and no CI gate was found under `.github/workflows/`.

**View Coverage:**
```bash
# Not currently available from declared dependencies.
# Add/configure pytest-cov before using: uv run pytest --cov=aura_backend aura_backend/tests
```

Because collection aborts and most tests lack assertions, a coverage percentage would not establish behavioral correctness without first repairing the suite.

## Test Types

**Unit Tests:**
- Limited script-level checks cover NumPy conversion (`aura_backend/tests/test_numpy_serialization.py`), parameter-shape manipulation (`aura_backend/tests/test_aura_parameter_fix.py`), and parser-style inputs (`aura_backend/tests/test_mcp_integration.py`).
- Several alleged unit tests reimplement the condition being checked instead of invoking production code. `test_timeout_parameter_fix()` in `aura_backend/tests/test_comprehensive_fixes.py` checks its own local schema logic.
- Source-text tests search files for endpoint strings, CSS class names, and method names in `aura_backend/tests/test_comprehensive_fixes.py` and `aura_backend/tests/test_ui_improvements.py`; these do not verify runtime behavior.

**Integration Tests:**
- `aura_backend/tests/test_vector_db.py` exercises real ChromaDB, embedding models, persistence, and knowledge retrieval; it is environment-heavy and has no isolation or markers.
- `aura_backend/tests/test_mcp_client.py`, `test_mcp_integration.py`, `test_aura_conversation.py`, and `test_aura_server_fix.py` attempt real MCP/backend interactions and primarily print observations.
- `aura_backend/tests/test_interprocess_locking.py` launches concurrent access behavior, but `test_concurrent_access(process_id, num_operations)` is shaped like a pytest test with unresolved fixture parameters and is also called manually.
- No test uses FastAPI `TestClient` or HTTPX `AsyncClient`, so the many routes in `aura_backend/main.py` lack controlled request/response integration tests.

**E2E Tests:**
- Not used. There is no Playwright, Cypress, browser automation, or packaged end-to-end runner in `package.json`.
- `aura_backend/tests/test_ui_improvements.py` checks HTML/CSS/TypeScript source text but does not render the UI or exercise user flows.

## Common Patterns

**Async Testing:**
```python
# Observed in aura_backend/tests/test_mcp_integration.py
async def test_aura_mcp_integration():
    success = await initialize_mcp_client()
    # prints results; no assertion
    await shutdown_mcp_client()

if __name__ == "__main__":
    asyncio.run(test_aura_mcp_integration())
```

**Error Testing:**
```python
# Observed in aura_backend/tests/test_numpy_serialization.py
try:
    json.dumps(mock_tool_result)
    return False
except (TypeError, ValueError):
    pass
```

The error pattern verifies expected exceptions only when the script's returned boolean is consumed by its manual `main()`; pytest does not treat the returned `False` as failure.

## Observed Test Validity

- Full-suite collection is broken: `uv run pytest --collect-only -q aura_backend/tests` aborts in `aura_backend/tests/test_aura_parameter_fix.py` because it imports `smart_mcp_parameter_handler` as a top-level module and then raises `SystemExit`.
- Import conventions vary among tests. `aura_backend/tests/test_numpy_serialization.py` inserts the tests directory but imports `json_serialization_fix`, whose actual active location is `aura_backend/scripts/json_serialization_fix.py`; this cannot be treated as a stable unit test boundary.
- The test suite contains no native assertions in its top-level active Python files. Pytest discovery alone therefore overstates executable verification.
- Absolute workstation paths in `aura_backend/tests/test_ui_improvements.py` and `aura_backend/tests/test_comprehensive_fixes.py` make results non-portable.
- Live integrations are unmarked and unpaired with deterministic fakes, so environmental failures cannot be separated cleanly from regressions.
- `npm run build` succeeds and proves bundling only. TypeScript checking is a separate failing surface because `tsconfig.json` does not exclude archived backups.
- No CI workflow executes tests, lint, type-checking, or builds; `.github/` contains only `.github/prompts/copilot.prompt.md`.

## Missing Coverage

- FastAPI request validation, response contracts, error status codes, lifecycle behavior, and the route set in `aura_backend/main.py` have no controlled API tests.
- Provider adapters in `aura_backend/providers/gemini.py`, `openrouter.py`, `ollama.py`, and `factory.py` have no unit tests for SDK translation, retries, errors, streaming, session reuse, or fallback selection.
- Persistence, deduplication, backup, locking, and recovery across `aura_backend/conversation_persistence_service.py`, `database_protection.py`, `robust_vector_db.py`, and `enhanced_vector_db.py` lack isolated temporary-storage tests.
- MCP schema conversion, tool execution, subprocess cleanup, timeout behavior, and malformed responses in `aura_backend/mcp_client.py`, `mcp_integration.py`, `mcp_to_gemini_bridge.py`, and `smart_mcp_parameter_handler.py` lack deterministic mocks and assertions.
- Frontend request retry/timeout behavior in `src/services/auraApi.ts` and UI state, session deletion, sanitization, storage, accessibility, and rendering in `index.tsx` have no automated tests.
- No security tests cover CORS, user/session authorization boundaries, path handling, prompt/tool input validation, secret exposure, or destructive endpoints in `aura_backend/main.py`.
- No regression tests assert behavior for provider failure, unavailable external services, corrupted Chroma state, concurrent cancellation, or partial persistence failure.

---

*Testing analysis: 2026-08-19*
