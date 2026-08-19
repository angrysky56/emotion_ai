# Coding Conventions

**Analysis Date:** 2026-08-19

## Naming Patterns

**Files:**
- Python production modules use lowercase snake case, for example `aura_backend/conversation_persistence_service.py`, `aura_backend/shared_embedding_service.py`, and `aura_backend/providers/openrouter.py`.
- Python test-like files use `test_*.py`, but the directory also contains executable diagnostics named `quick_test.py`, `debug_thinking.py`, `diagnose_memory_manager.py`, and `validate_gemini_fixes.py` under `aura_backend/tests/`.
- TypeScript uses camel-case service filenames (`src/services/auraApi.ts`) and a root entry point (`index.tsx`).
- Suffixes such as `_fixed`, `_compatible_fixed`, and `_v2` remain in active source (`aura_backend/aura_memvid_mcp_tools_compatible_fixed.py`, `aura_backend/scratch/test_memvid_v2.py`), so filenames do not consistently distinguish canonical implementations from repair variants.

**Functions:**
- Python functions and methods use `snake_case`; private helpers use a leading underscore, as in `_convert_messages_to_history()` in `aura_backend/providers/gemini.py`.
- Async work is explicitly declared with `async def`; names do not add an `async_` prefix (`generate_response`, `stream_response`, `process_conversation`).
- TypeScript methods use `camelCase`, with access modifiers and explicit return types in `src/services/auraApi.ts` and `index.tsx`.

**Variables:**
- Python local and instance variables use `snake_case`; module constants use `UPPER_SNAKE_CASE`, for example `TOOL_CALL_MAX_RETRIES` in `aura_backend/providers/gemini.py`.
- TypeScript fields and locals use `camelCase`; private fields are declared with `private` rather than an underscore (`src/services/auraApi.ts`, `index.tsx`).

**Types:**
- Python classes and dataclasses use `PascalCase` (`BaseProvider`, `ProviderResponse`, `ModelProviderFactory`) in `aura_backend/providers/`.
- TypeScript interfaces and classes use `PascalCase` (`ConversationRequest`, `AuraAPI`, `AuraUIManager`) in `src/services/auraApi.ts` and `index.tsx`.
- Python typing is mixed between legacy containers (`Dict`, `List`, `Optional`) and built-ins; `aura_backend/providers/base.py` is representative of the legacy style.

## Code Style

**Formatting:**
- Ruff declares Python 3.12 and an 88-character line length in `pyproject.toml`; no formatter configuration or formatting command is declared.
- Recently structured provider modules such as `aura_backend/providers/base.py` and `aura_backend/providers/factory.py` resemble Black/Ruff formatting, while older large modules and test scripts contain inconsistent blank lines, long lines, and ad hoc formatting.
- TypeScript generally uses two-space indentation, semicolons, and single quotes in `src/services/auraApi.ts`; `vite.config.ts` uses inconsistent indentation. No Prettier configuration is present.

**Linting:**
- Ruff is configured only with `src`, `target-version`, and `line-length` in `pyproject.toml`; no rule selection, exclusions, or repository script enforces it.
- Observed command `uv run ruff check aura_backend --exclude aura_backend/archive_unused` fails with six unused-import findings, including `aura_backend/tests/quick_test.py` and `aura_backend/scratch/test_memvid_v2.py`.
- TypeScript strictness is declared in `tsconfig.json`: `strict`, unused-local/parameter checks, fallthrough prevention, side-effect import checking, and casing enforcement.
- `npm run build` succeeds, but it invokes Vite only (`package.json`) and does not type-check. `npx tsc --noEmit` fails because `tsconfig.json` includes archived `.tsx` backups with missing imports and implicit-any/unused errors under `archive/` and `aura_backend/archive_unused/backups/`.
- Pyright basic mode is declared for `aura_backend` in `pyproject.toml`, but Pyright is not a project dependency and `uv run pyright` cannot execute.
- No ESLint, Prettier, mypy, pre-commit, or Trunk workflow is configured for the active project. `.trunk/configs/ruff.toml` exists as tool-managed data, not an evidenced project command.

## Import Organization

**Order:**
1. Standard-library imports.
2. Third-party imports.
3. `aura_backend.*` project imports.

This grouping is clearest in `aura_backend/main.py`, `aura_backend/providers/gemini.py`, and `aura_backend/mcp_integration.py`. Relative imports are used within the provider package in `aura_backend/providers/factory.py`, while most other production modules use absolute `aura_backend.*` imports.

**Path Aliases:**
- TypeScript declares `@/*` to resolve from the repository root in `tsconfig.json`, with a matching `@` alias in `vite.config.ts`; active TypeScript currently imports relatively (`index.tsx`, `src/services/auraApi.ts`).
- Python has no installed-package or pytest path configuration. Several tests mutate `sys.path`, and some hard-code `/home/ty/Repositories/ai_workspace/emotion_ai`, notably `aura_backend/tests/test_ui_improvements.py` and `aura_backend/tests/test_comprehensive_fixes.py`.

## Error Handling

**Patterns:**
- Provider boundaries catch broad `Exception`, log details, and return an error-bearing response rather than re-raising, as in `aura_backend/providers/gemini.py`.
- FastAPI endpoints use `HTTPException` and broad exception guards in the monolithic `aura_backend/main.py`.
- Optional subsystems frequently degrade to warning logs and limited functionality, especially MCP and persistence initialization in `aura_backend/mcp_integration.py` and `aura_backend/main.py`.
- Standalone validation scripts catch exceptions, print emoji-prefixed status, and return booleans; these booleans are generally not asserted by pytest (`aura_backend/tests/test_comprehensive_fixes.py`, `aura_backend/tests/test_ui_improvements.py`).

## Logging

**Framework:** Python standard `logging`; browser `console` methods in TypeScript.

**Patterns:**
- Use `logger = logging.getLogger(__name__)` at module scope and parameterized messages (`logger.info("... %s", value)`) in newer Python modules such as `aura_backend/providers/factory.py`.
- Emoji prefixes encode operational categories throughout production and test output (`aura_backend/providers/gemini.py`, `src/services/auraApi.ts`).
- Exception paths sometimes emit both a summary and a full traceback (`aura_backend/providers/gemini.py`).
- Frontend code uses `console.log`, `console.warn`, and `console.error` directly in `src/services/auraApi.ts` and `index.tsx`; there is no log abstraction or production stripping.

## Comments

**When to Comment:**
- Python modules begin with explanatory docstrings and use numbered comments for multi-stage workflows, as in `aura_backend/providers/gemini.py`.
- TypeScript uses large banner comments to divide concerns in `src/services/auraApi.ts` and `index.tsx`.
- Comments frequently explain intent and operational history; some describe temporary states such as “Simple conversion for now” in `aura_backend/providers/gemini.py`.

**JSDoc/TSDoc:**
- Public TypeScript interfaces are usually self-describing; class and method JSDoc is concentrated in `src/services/auraApi.ts`.
- Python public classes and methods generally have docstrings in `aura_backend/providers/`, but coverage is inconsistent in the older service modules.

## Function Design

**Size:**
- Small provider abstractions are used in `aura_backend/providers/`, but major orchestration remains in very large functions and one 4,000-plus-line module, `aura_backend/main.py`.
- Frontend behavior is concentrated in the single `AuraUIManager` class in `index.tsx`; API transport is separated into `src/services/auraApi.ts`.

**Parameters:**
- Python service APIs use explicit type hints and optional keyword defaults in newer modules (`aura_backend/providers/base.py`); older modules and scripts are less consistent.
- FastAPI input contracts use Pydantic models in `aura_backend/main.py`.
- TypeScript request/response shapes are interfaces in `src/services/auraApi.ts`; `any` remains in external metadata and request plumbing.

**Return Values:**
- Provider operations return `ProviderResponse` instead of raw SDK objects (`aura_backend/providers/base.py`).
- Backend services often return `Dict[str, Any]` rather than dedicated models (`aura_backend/main.py`, `aura_backend/mcp_system.py`).
- Test scripts return `True`/`False` and print summaries; pytest ignores a returned false value unless explicitly asserted.

## Module Design

**Exports:**
- Python modules expose classes/functions directly; `aura_backend/providers/__init__.py` is minimal and consumers import concrete files.
- TypeScript uses named exports for API contracts and the `AuraAPI` class in `src/services/auraApi.ts`; `index.tsx` owns browser startup behavior.

**Barrel Files:**
- No TypeScript barrel files are used.
- `aura_backend/providers/__init__.py` marks the package but is not used as a public re-export surface.

---

*Convention analysis: 2026-08-19*
