@echo off
setlocal

where uv >nul 2>&1
if errorlevel 1 (
    >&2 echo Aura: uv is required. See https://docs.astral.sh/uv/getting-started/installation/
    exit /b 127
)

cd /d "%~dp0"
if errorlevel 1 (
    >&2 echo Aura: repository root is unavailable.
    exit /b 1
)

uv run --locked --no-sync python -m aura_backend.runtime serve %*
exit /b %errorlevel%
