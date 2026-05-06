# Phase 1: Environment & Dependency Refresh

## Goal
Initialize a stable, modern development environment, sync dependencies to latest stable versions, and address immediate repository "messiness" as requested by the user.

## Context
- The project is described as "quite messy".
- Root directory contains many images and loose test files.
- `aura_backend` has redundant setup scripts and loose log files.
- Python 3.13 is available and should be fully supported.
- `uv` is the preferred package manager.

## Tasks

### 1. Dependency Refresh
- [x] **Backend**: Update `aura_backend/pyproject.toml` dependencies:
  - `fastapi` -> latest (0.136.1)
  - `pydantic` -> latest (2.13.3)
  - `torch` -> stable version (2.11.0)
  - `chromadb` -> latest stable
- [x] **Frontend**: Update `package.json` dependencies to latest stable.
- [x] **Locking**: Run `uv pip compile aura_backend/pyproject.toml -o aura_backend/requirements.txt` to sync.
- [x] **Sync**: Run `uv pip sync aura_backend/requirements.txt` in the backend.

### 2. Environment Stabilization
- [x] **Clean Venv**: Re-create `.venv` using `uv venv --python 3.13` to ensure a fresh start.
- [x] **NPM Sync**: Run `npm install` to ensure frontend dependencies are locked.
- [x] **Env Check**: Verify `.env.example` matches current requirements.

### 3. Repository Cleanup ("The Mess")
- [x] **Assets**: Create `docs/assets` and move all root-level `image-*.png` and `image.png` files there.
- [x] **Tests**: Move root-level `test_*.py` files to `aura_backend/tests/legacy` or a dedicated `tests/root` folder if they are still needed.
- [x] **Backend Scripts**: Move setup scripts (`setup.sh`, `setup_uv.sh`, `install_mcp_deps.sh`) to `aura_backend/scripts/setup` or archive them if redundant.
- [x] **Backend Logs**: Move `*.log` and `debug_*.py` files in `aura_backend` to `aura_backend/archive/debug`.
- [x] **Redundant Files**: Remove `index_backup.tsx` and other clearly redundant backups after verification.

### 4. Verification
- [x] **Backend Boot**: Ensure `uvicorn main:app` starts without errors.
- [x] **Frontend Boot**: Ensure `npm run dev` starts and connects to the backend.
- [x] **Linting**: Run `trunk check` or equivalent to verify basic code health.

## Success Criteria
- [x] Clean repository root (only core project files and folders).
- [x] All dependencies are on latest stable versions.
- [x] `uv` virtual environment is healthy and running Python 3.13.
- [x] Backend and Frontend start without errors.
