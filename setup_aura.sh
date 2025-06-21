#!/bin/bash
# Aura Setup Script
# =================
# This script automates the setup process for the Aura project,
# including backend and frontend components.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Helper Functions for Colored Output ---
# Colors
RESET='\033[0m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'

# Print functions
_print_msg() {
    local color=$1
    local prefix=$2
    local message=$3
    echo -e "${color}${prefix}${RESET} ${message}"
}

print_status() {
    _print_msg "${BLUE}" "[STATUS]" "$1"
}

print_success() {
    _print_msg "${GREEN}" "[SUCCESS]" "$1"
}

print_warning() {
    _print_msg "${YELLOW}" "[WARNING]" "$1"
}

print_error() {
    _print_msg "${RED}" "[ERROR]" "$1" >&2
}

print_info() {
    _print_msg "${MAGENTA}" "[INFO]" "$1"
}

print_status "Starting Aura setup process..."

# --- Prerequisite Checks ---
print_status "Checking prerequisites..."

# 1. Check for Python 3.12+
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=12
PYTHON_CMD=python3

if ! command -v $PYTHON_CMD &> /dev/null; then
    print_error "$PYTHON_CMD could not be found. Please install Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR or higher."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if ! ([ "$PYTHON_MAJOR" -gt "$MIN_PYTHON_MAJOR" ] || \
      [ "$PYTHON_MAJOR" -eq "$MIN_PYTHON_MAJOR" -a "$PYTHON_MINOR" -ge "$MIN_PYTHON_MINOR" ]); then
    print_error "Python version $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR or higher is required. Found: $PYTHON_VERSION"
    print_error "Please upgrade your Python installation."
    exit 1
fi
print_success "Python $PYTHON_VERSION found."

# 2. Check for uv
if ! command -v uv &> /dev/null; then
    print_error "'uv' command not found. UV is required for Python environment and package management."
    print_info "You can typically install it with pip: 'pip install uv' or 'pipx install uv'."
    print_info "Please install uv and re-run this script: https://github.com/astral-sh/uv"
    exit 1
fi
print_success "uv found: $(uv --version)"

# 3. Check for Node.js and npm
if ! command -v node &> /dev/null; then
    print_error "'node' command not found. Node.js is required for the frontend."
    print_info "Please install Node.js (which includes npm): https://nodejs.org/"
    exit 1
fi
print_success "Node.js found: $(node --version)"

if ! command -v npm &> /dev/null; then
    print_error "'npm' command not found. npm is required for frontend dependency management."
    print_info "npm is usually installed with Node.js. Please check your Node.js installation: https://nodejs.org/"
    exit 1
fi
print_success "npm found: $(npm --version)"

print_success "All prerequisites are met."
echo

# --- Backend Setup ---
print_status "Setting up backend in 'aura_backend' directory..."
AURA_BACKEND_DIR="aura_backend"
ENV_EXAMPLE_FILE=".env.example"
ENV_FILE=".env"
VENV_DIR=".venv"

if [ ! -d "$AURA_BACKEND_DIR" ]; then
    print_error "Directory '$AURA_BACKEND_DIR' not found. Make sure you are in the project root."
    exit 1
fi

if [ ! -f "$AURA_BACKEND_DIR/pyproject.toml" ]; then
    print_error "'pyproject.toml' not found in '$AURA_BACKEND_DIR'. Backend setup cannot continue."
    exit 1
fi

cd "$AURA_BACKEND_DIR" || { print_error "Failed to navigate to $AURA_BACKEND_DIR"; exit 1; }

# 1. Create Python virtual environment using uv
print_status "Creating Python virtual environment using 'uv venv' in '$VENV_DIR'..."
if [ -d "$VENV_DIR" ]; then
    print_warning "Virtual environment '$VENV_DIR' already exists. Skipping creation."
else
    uv venv --python $PYTHON_CMD "$VENV_DIR"
    print_success "Virtual environment created successfully."
fi

# Activate virtual environment for subsequent commands in this script block
# Note: This activates it for the current shell session of the script.
# The user will need to activate it manually or use the start script later.
print_status "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
print_success "Virtual environment activated for this script session."

# 2. Install Python dependencies using uv pip sync
print_status "Installing Python dependencies from 'pyproject.toml' using 'uv pip sync'..."
if uv pip sync pyproject.toml; then
    print_success "Python dependencies installed successfully."
else
    print_error "Failed to install Python dependencies. Check the output above for details."
    # Deactivate venv before exiting if we activated it
    deactivate || true
    cd .. && exit 1
fi

# 3. Setup .env file
print_status "Setting up environment file '$ENV_FILE'..."
if [ ! -f "$ENV_EXAMPLE_FILE" ]; then
    print_error "Environment example file '$ENV_EXAMPLE_FILE' not found. Cannot create '$ENV_FILE'."
    deactivate || true
    cd .. && exit 1
fi

if [ -f "$ENV_FILE" ]; then
    print_warning "'$ENV_FILE' already exists. It will not be overwritten."
    print_info "Please ensure your GOOGLE_API_KEY is correctly set in '$AURA_BACKEND_DIR/$ENV_FILE'."
else
    cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
    print_success "Copied '$ENV_EXAMPLE_FILE' to '$ENV_FILE'."

    print_info "You need to provide your Google API Key for Aura to function."
    # Prompt for Google API Key
    # Using read -r -p within a conditional or subshell can be tricky with set -e
    # So we'll use a temporary variable approach
    API_KEY_INPUT=""
    while [ -z "$API_KEY_INPUT" ]; do
        read -r -p "Enter your GOOGLE_API_KEY: " API_KEY_INPUT
        if [ -z "$API_KEY_INPUT" ]; then
            print_warning "Google API Key cannot be empty. Please try again."
        fi
    done

    # Replace the placeholder in .env file
    # Using a different delimiter for sed in case API key contains slashes
    if sed -i.bak "s|^GOOGLE_API_KEY=.*|GOOGLE_API_KEY=$API_KEY_INPUT|" "$ENV_FILE"; then
        rm -f "${ENV_FILE}.bak" # Remove backup file on success
        print_success "GOOGLE_API_KEY updated in '$ENV_FILE'."
    else
        print_error "Failed to update GOOGLE_API_KEY in '$ENV_FILE'."
        print_info "Please manually edit '$AURA_BACKEND_DIR/$ENV_FILE' and set your GOOGLE_API_KEY."
        # Restore original .env if sed failed badly, though -i.bak helps
        if [ -f "${ENV_FILE}.bak" ]; then
            mv "${ENV_FILE}.bak" "$ENV_FILE"
        fi
    fi
fi

# 4. Create necessary data directories
print_status "Creating data directories..."
mkdir -p aura_chroma_db
mkdir -p aura_data/users
mkdir -p aura_data/sessions
mkdir -p aura_data/exports
mkdir -p aura_data/backups
mkdir -p aura_data/logs
mkdir -p memvid_data
mkdir -p memvid_videos
print_success "Data directories created/ensured under '$AURA_BACKEND_DIR'."

# Deactivate virtual environment as this script part is done
print_status "Deactivating virtual environment for this script session..."
deactivate || print_warning "Failed to deactivate virtualenv, or it was not active."

cd .. || { print_error "Failed to navigate back to project root."; exit 1; }
print_success "Backend setup complete."
echo

# --- Frontend Setup ---
print_status "Setting up frontend in project root..."

if [ ! -f "package.json" ]; then
    print_warning "'package.json' not found in the project root. Skipping frontend dependency installation."
    print_warning "If this project has a frontend, ensure 'package.json' is present and run 'npm install' manually."
else
    print_status "Installing frontend dependencies using 'npm install'..."
    if npm install; then
        print_success "Frontend dependencies installed successfully."
    else
        print_error "Failed to install frontend dependencies. Check the output above for details."
        # We don't necessarily need to exit the whole script if frontend fails,
        # as backend might still be usable. User can troubleshoot npm issues separately.
        print_warning "Frontend setup encountered an issue. The backend might still be functional."
    fi
fi
print_success "Frontend setup section complete."
echo

# --- Final Instructions ---
print_status "Aura setup process is complete!"
echo
print_info "========================================================================"
print_info "NEXT STEPS:"
print_info "========================================================================"
echo
print_info "1. Activate the Python virtual environment (if not already active for your session):"
print_info "   ${BLUE}cd aura_backend && source .venv/bin/activate${RESET}"
echo
print_info "2. Start the Aura backend and frontend services:"
print_info "   (Ensure you are in the 'aura_backend' directory and venv is active)"
print_info "   To start both backend and frontend (recommended):"
print_info "   ${BLUE}./start.sh --with-frontend${RESET}"
echo
print_info "   To start only the backend API server:"
print_info "   ${BLUE}./start.sh${RESET}"
echo
print_info "   Once started:"
print_info "   - Backend API will be available at: ${YELLOW}http://localhost:8000${RESET}"
print_info "   - API Docs (Swagger UI) at: ${YELLOW}http://localhost:8000/docs${RESET}"
print_info "   - Frontend (if started with --with-frontend) at: ${YELLOW}http://localhost:5173${RESET}"
echo
print_info "3. If you only activated the venv for this setup script, you'll need to"
print_info "   activate it again in your terminal before running start.sh:"
print_info "   From project root: ${BLUE}cd aura_backend && source .venv/bin/activate${RESET}"
print_info "   Then run: ${BLUE}./start.sh --with-frontend${RESET}"
echo
print_info "========================================================================"
print_success "Setup finished. Enjoy using Aura!"
echo
# End of script
