#!/bin/bash

# Aura AI - Full System Startup Script
# This script starts both backend and frontend in separate terminals

# set -e # Exit on any error

echo "🌟 Starting Aura AI Full System..."
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
	command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
	lsof -ti:"$1" >/dev/null 2>&1
}

# Function to kill processes on specific ports
kill_port() {
	if port_in_use "$1"; then
		echo -e "${YELLOW}Killing existing process on port $1...${NC}"
		fuser -k "$1"/tcp 2>/dev/null || true
		sleep 2
	fi
}

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command_exists node; then
	echo -e "${RED}Error: Node.js is not installed. Please install Node.js first.${NC}"
	exit 1
fi

if ! command_exists npm; then
	echo -e "${RED}Error: npm is not installed. Please install npm first.${NC}"
	exit 1
fi

if ! command_exists uv; then
	echo -e "${YELLOW}Warning: uv is not installed. Attempting to install...${NC}"
	curl -LsSf https://astral.sh/uv/install.sh | sh
	# shellcheck source=$HOME/.bashrc
	source "$HOME/.bashrc"
	if ! command_exists uv; then
		echo -e "${RED}Error: Failed to install uv. Please install it manually.${NC}"
		exit 1
	fi
fi

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/aura_backend"
FRONTEND_DIR="$SCRIPT_DIR"

echo -e "${BLUE}Project directory: $SCRIPT_DIR${NC}"

# Check if directories exist
if [ ! -d "$BACKEND_DIR" ]; then
	echo -e "${RED}Error: Backend directory not found at $BACKEND_DIR${NC}"
	exit 1
fi

if [ ! -f "$FRONTEND_DIR/package.json" ]; then
	echo -e "${RED}Error: Frontend package.json not found at $FRONTEND_DIR${NC}"
	exit 1
fi

# Clean up any existing processes
echo -e "${BLUE}Cleaning up existing processes...${NC}"
kill_port 8000 # Backend port
kill_port 5173 # Frontend port

# Function to start backend
start_backend() {
	echo -e "${GREEN}🚀 Starting Backend Server...${NC}"
	cd "$BACKEND_DIR"

	# Check if .env exists
	if [ ! -f ".env" ]; then
		if [ ! -f "deprecated_use_backend.env.example" ]; then
			echo -e "${YELLOW}Warning: No .env file found. Creating basic .env...${NC}"
			cat >.env <<'EOF'
# Aura Backend Configuration
GOOGLE_API_KEY=your-google-api-key-here
CHROMA_PERSIST_DIRECTORY=./aura_chroma_db
AURA_DATA_DIRECTORY=./aura_data
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO
AURA_MODEL=gemini-2.0-flash-exp
AURA_MAX_OUTPUT_TOKENS=1000000
AUTONOMIC_ENABLED=true
EOF
			echo -e "${YELLOW}Please edit $BACKEND_DIR/.env with your Google API key${NC}"
		else
			echo -e "${YELLOW}Copying example .env file...${NC}"
			cp deprecated_use_backend.env.example .env
		fi
	fi

	# Setup environment if needed in the project root
	if [ ! -d "$SCRIPT_DIR/.venv" ]; then
		echo -e "${BLUE}Setting up environment in project root...${NC}"
		(cd "$SCRIPT_DIR" && uv venv --python 3.12 && uv sync)
	fi

	# Start the backend
	echo -e "${GREEN}Starting backend on http://localhost:8000${NC}"
	if [ -f "start.sh" ]; then
		chmod +x start.sh
		./start.sh
	else
		uv run --project "$SCRIPT_DIR" uvicorn main:app --host 0.0.0.0 --port 8000 --reload
	fi
}

# Function to start frontend
start_frontend() {
	echo -e "${GREEN}🎨 Starting Frontend Server...${NC}"
	cd "$FRONTEND_DIR"

	# Install dependencies if needed
	if [ ! -d "node_modules" ]; then
		echo -e "${BLUE}Installing frontend dependencies...${NC}"
		npm install
	fi

	# Start the frontend
	echo -e "${GREEN}Starting frontend on http://localhost:5173${NC}"
	npm run dev
}

# Function to start in new terminal (works with most terminal emulators)
start_in_new_terminal() {
	local title="$1"
	local command="$2"

	# Try different terminal emulators
	if command_exists gnome-terminal; then
		gnome-terminal --title="$title" -- bash -c "$command; exec bash"
	elif command_exists konsole; then
		konsole --title "$title" -e bash -c "$command; exec bash" &
	elif command_exists xfce4-terminal; then
		xfce4-terminal --title="$title" -e "bash -c '$command; exec bash'" &
	elif command_exists xterm; then
		xterm -title "$title" -e "bash -c '$command; exec bash'" &
	elif command_exists terminator; then
		terminator --title="$title" -e "bash -c '$command; exec bash'" &
	else
		echo -e "${YELLOW}No supported terminal emulator found. Starting in background...${NC}"
		bash -c "$command" &
	fi
}

# Main execution
echo -e "${BLUE}Starting services in separate terminals...${NC}"

# Start backend in new terminal
BACKEND_CMD="cd '$BACKEND_DIR' && echo -e '${GREEN}🚀 Aura Backend Starting...${NC}' && $(declare -f start_backend) && start_backend"
start_in_new_terminal "Aura Backend" "$BACKEND_CMD"

# Wait a moment for backend to start
echo -e "${BLUE}Waiting for backend to initialize...${NC}"
sleep 5

# Start frontend in new terminal
FRONTEND_CMD="cd '$FRONTEND_DIR' && echo -e '${GREEN}🎨 Aura Frontend Starting...${NC}' && $(declare -f start_frontend) && start_frontend"
start_in_new_terminal "Aura Frontend" "$FRONTEND_CMD"

# Wait for services to start
echo -e "${BLUE}Waiting for services to start...${NC}"
sleep 8

# Wait for backend with a more robust check
MAX_RETRIES=15
RETRIES=0
BACKEND_STARTED=false

while [ $RETRIES -lt $MAX_RETRIES ]; do
    if port_in_use 8000; then
        echo -e "${GREEN}✅ Backend is running on http://localhost:8000${NC}"
        echo -e "${BLUE}   API Documentation: http://localhost:8000/docs${NC}"
        BACKEND_STARTED=true
        break
    fi
    echo -n "."
    sleep 2
    ((RETRIES++))
done

if [ "$BACKEND_STARTED" = false ]; then
    echo -e "\n${RED}❌ Backend failed to start on port 8000${NC}"
fi

if port_in_use 5173; then
	echo -e "${GREEN}✅ Frontend is running on http://localhost:5173${NC}"
else
	echo -e "${RED}❌ Frontend failed to start on port 5173${NC}"
fi

echo ""
echo -e "${GREEN}🌟 Aura AI System Status:${NC}"
echo -e "${GREEN}========================${NC}"
echo -e "${BLUE}Backend:${NC}  http://localhost:8000"
echo -e "${BLUE}Frontend:${NC} http://localhost:5173"
echo -e "${BLUE}API Docs:${NC} http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}To stop all services, you can run:${NC}"
echo -e "${YELLOW}  fuser -k 8000/tcp && fuser -k 5173/tcp${NC}"
echo ""
echo -e "${GREEN}System startup complete! 🚀${NC}"
