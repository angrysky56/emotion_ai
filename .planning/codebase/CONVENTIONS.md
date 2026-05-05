# Conventions - Emotion AI / Aura

## Development Standards
- **Linter/Formatter**: [Trunk](https://trunk.io/) is the source of truth for all formatting and linting.
  - Python: `ruff`, `black`, `isort`, `bandit`.
  - Frontend: `prettier`, `typescript-eslint`.
  - Other: `shellcheck`, `markdownlint`, `yamllint`.
- **Typing**: Strict typing is required in both TypeScript and Python (using `typing` and `pydantic`).
- **Commits**: Follow [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat:`, `fix:`, `docs:`).

## Python Conventions
- **Version**: Python 3.13 is the target version.
- **Environment**: Use `uv` for environment and package management (`uv venv`, `uv pip install`).
- **Docstrings**: Use clear, descriptive docstrings for all functions and classes.
- **Error Handling**: Use explicit exception handling; avoid broad `try: ... except: pass`. Use `HTTPException` in FastAPI endpoints.
- **Logging**: Use the standard `logging` module with lazy formatting.

## TypeScript/Frontend Conventions
- **Modules**: Use ES Modules (`import`/`export`).
- **Architecture**: Preference for Singleton patterns in services (`auraApi.ts`).
- **Documentation**: Use TSDoc (`/** ... */`) for documenting components and methods.
- **State Management**: Centralized UI management class in `index.tsx`.

## Testing Conventions
- **Framework**: `pytest` for Python.
- **Naming**: Test files must be prefixed with `test_`.
- **TDD**: The project encourages Test-Driven Development (TDD).
- **Asynchronous**: Extensive use of `pytest-asyncio` for testing backend services.
