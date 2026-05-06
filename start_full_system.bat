@echo off
REM Aura AI - Full System Startup Script for Windows
REM This script starts both backend and frontend in separate command prompts

echo 🌟 Starting Aura AI Full System...
echo ==================================

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Node.js is not installed. Please install Node.js first.
    pause
    exit /b 1
)

REM Check if npm is installed
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: npm is not installed. Please install npm first.
    pause
    exit /b 1
)

REM Check if uv is installed
uv --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Warning: uv is not installed. Please install uv first.
    echo You can install it from: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

REM Get current directory
set "PROJECT_DIR=%~dp0"
set "BACKEND_DIR=%PROJECT_DIR%aura_backend"

REM Check if directories exist
if not exist "%BACKEND_DIR%" (
    echo ❌ Error: Backend directory not found at %BACKEND_DIR%
    pause
    exit /b 1
)

if not exist "%PROJECT_DIR%package.json" (
    echo ❌ Error: Frontend package.json not found at %PROJECT_DIR%
    pause
    exit /b 1
)

echo 🚀 Starting Backend Server in new window...
start "Aura Backend" cmd /k "cd /d "%BACKEND_DIR%" && echo 🚀 Aura Backend Starting... && if not exist ..\.venv (echo Setting up environment in project root... && cd .. && uv venv --python 3.12 --seed && uv sync && cd aura_backend) && if exist start.sh (bash start.sh) else (uv run --project .. uvicorn main:app --host 0.0.0.0 --port 8000 --reload)"

echo ⏳ Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

echo 🎨 Starting Frontend Server in new window...
start "Aura Frontend" cmd /k "cd /d "%PROJECT_DIR%" && echo 🎨 Aura Frontend Starting... && if not exist node_modules (echo Installing frontend dependencies... && npm install) && npm run dev"

echo ⏳ Waiting for services to start...
timeout /t 8 /nobreak >nul

echo.
echo 🌟 Aura AI System Started!
echo ========================
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo To stop services, close the terminal windows or run stop_full_system.bat
echo.
pause
