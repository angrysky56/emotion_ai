#!/bin/bash
# Aura Clean Start Script
# Simplified startup that properly handles the architecture

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[Aura]${NC} $1"; }
error() { echo -e "${RED}[Error]${NC} $1" >&2; }

# Cleanup on exit
cleanup() {
	log "Stopping services..."
	pkill -P $$ 2>/dev/null || true
	wait
	log "Services stopped"
	exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Find virtual environment
# We prioritize the project root .venv
if [[ -d "../.venv" ]]; then
    VENV_PATH="../.venv"
    log "Found root virtual environment at $VENV_PATH"
elif [[ -d ".venv" ]]; then
    VENV_PATH=".venv"
    log "Found local virtual environment at $VENV_PATH (Warning: root venv preferred)"
else
    error "Virtual environment not found in root or local directory!"
    error "Run: uv venv in the project root."
    exit 1
fi

# Activate venv
# shellcheck disable=SC1091
source "$VENV_PATH/bin/activate"

# Start API (which includes Aura internal tools)
log "Starting Aura API Server..."
python main.py &
export API_PID=$!

# Wait for API
log "Waiting for API to start..."
for _ in {1..30}; do
	if curl -s http://localhost:8000/health >/dev/null 2>&1; then
		log "API is ready!"
		break
	fi
	sleep 1
done

# Optional: Start frontend- this has to be made to run in the parent directory in another terminal
if ! command -v npm &>/dev/null; then
	error "npm is not installed! Please install Node.js and npm."
	exit 1
fi
if [[ $1 == "--with-frontend" ]]; then
	log "Starting frontend..."
	(cd .. && npm run dev) &
	sleep 3
	log "Frontend started!"
fi

# Show status
echo ""
log "✅ Aura is running!"
echo "  📡 API: http://localhost:8000"
echo "  📖 Docs: http://localhost:8000/docs"
[[ $1 == "--with-frontend" ]] && echo "  🌐 UI: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop"

# Keep running
wait
