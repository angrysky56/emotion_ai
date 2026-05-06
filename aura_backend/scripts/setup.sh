#!/bin/bash

# Aura Backend Setup Script
# ==========================

echo "🚀 Setting up Aura Advanced AI Companion Backend..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
	echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
	echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
	echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
	echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
	print_error "requirements.txt not found. Please run this script from the aura_backend directory."
	exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oP 'Python \K[0-9.]+')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
	print_error "Python 3.10+ required. Current version: $python_version"
	exit 1
fi

print_success "Python version check passed: $python_version"

# Create virtual environment
print_status "Creating Python virtual environment..."
if [ -d ".venv" ]; then
	VENV_PATH=".venv"
elif [ -d "../.venv" ]; then
	VENV_PATH="../.venv"
elif [ -d "../../.venv" ]; then
	VENV_PATH="../../.venv"
else
	VENV_PATH=".venv"
fi

if [ ! -d "$VENV_PATH" ]; then
	python3 -m venv "$VENV_PATH"
	print_success "Virtual environment created at $VENV_PATH"
else
	print_warning "Virtual environment already exists at $VENV_PATH"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install requirements
print_status "Installing Python dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
	print_success "Dependencies installed successfully"
else
	print_error "Failed to install dependencies"
	exit 1
fi

# Create environment file
print_status "Setting up environment configuration..."
if [ ! -f ".env" ]; then
	cat >.env <<EOF
# Aura Backend Configuration
# ==========================

# Google API Configuration
GOOGLE_API_KEY=your_google_api_key_here

# Database Configuration
CHROMA_PERSIST_DIRECTORY=./aura_chroma_db
AURA_DATA_DIRECTORY=./aura_data

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true

# Logging Configuration
LOG_LEVEL=INFO

# MCP Server Configuration
MCP_SERVER_NAME=aura-companion
MCP_SERVER_VERSION=1.0.0

# Security Configuration
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]

# Features Configuration
ENABLE_EMOTIONAL_ANALYSIS=true
ENABLE_COGNITIVE_TRACKING=true
ENABLE_VECTOR_SEARCH=true
ENABLE_FILE_EXPORTS=true
EOF
	print_success "Environment file created (.env)"
	print_warning "Please edit .env and add your Google API key!"
else
	print_warning "Environment file already exists"
fi

# Create data directories
print_status "Creating data directories..."
mkdir -p aura_chroma_db
mkdir -p aura_data/{users,sessions,exports,backups}
print_success "Data directories created"

# Create startup scripts
print_status "Creating startup scripts..."

# Main API server startup script
cat >start_api.sh <<'EOF'
#!/bin/bash
echo "🚀 Starting Aura API Server..."
source "$VENV_PATH/bin/activate"
python main.py
EOF
chmod +x start_api.sh

# MCP server startup script
cat >start_mcp.sh <<'EOF'
#!/bin/bash
echo "🔗 Starting Aura MCP Server..."
source "$VENV_PATH/bin/activate"
python mcp_server.py
EOF
chmod +x start_mcp.sh

# Combined startup script
cat >start_all.sh <<'EOF'
#!/bin/bash
echo "🌟 Starting Aura Complete Backend System..."

# Function to cleanup background processes
cleanup() {
    echo "Stopping all Aura services..."
    kill $(jobs -p) 2>/dev/null
    exit
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start API server in background
echo "🚀 Starting API Server..."
./start_api.sh &
API_PID=$!

# Wait a moment for API server to start
sleep 3

# Start MCP server in background
echo "🔗 Starting MCP Server..."
./start_mcp.sh &
MCP_PID=$!

echo "✅ All services started!"
echo "📡 API Server: http://localhost:8000"
echo "🔗 MCP Server: Available for external connections"
echo "📖 API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for all background processes
wait
EOF
chmod +x start_all.sh

print_success "Startup scripts created"

# Create systemd service file (optional)
print_status "Creating systemd service template..."
cat >aura-backend.service <<EOF
[Unit]
Description=Aura Advanced AI Companion Backend
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/.venv/bin:/usr/bin:/bin
ExecStart=$(pwd)/.venv/bin/python $(pwd)/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

print_success "Systemd service template created (aura-backend.service)"

# Test installation
print_status "Testing installation..."
python -c "
import chromadb
import sentence_transformers
import fastapi
import google.generativeai
print('✅ All core dependencies imported successfully')
"

if [ $? -eq 0 ]; then
	print_success "Installation test passed"
else
	print_error "Installation test failed"
	exit 1
fi

# Create simple test script
cat >test_setup.py <<'EOF'
#!/usr/bin/env python3
"""
Simple test script to verify Aura backend setup
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_setup():
    try:
        # Test vector database
        from main import vector_db
        print("✅ Vector database initialized")

        # Test file system
        from main import file_system
        print("✅ File system initialized")

        # Test state manager
        from main import state_manager
        print("✅ State manager initialized")

        print("\n🎉 Aura backend setup test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Setup test failed: {e}")
        return False

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_setup())
    sys.exit(0 if success else 1)
EOF
chmod +x test_setup.py

print_success "Test script created (test_setup.py)"

# Final instructions
echo ""
echo "🎉 Aura Backend Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Edit .env and add your Google API key"
echo "2. Run: ./test_setup.py (to verify setup)"
echo "3. Run: ./start_all.sh (to start all services)"
echo ""
echo "🔧 Available Scripts:"
echo "• ./start_api.sh      - Start API server only"
echo "• ./start_mcp.sh      - Start MCP server only"
echo "• ./start_all.sh      - Start all services"
echo "• ./test_setup.py     - Test installation"
echo ""
echo "📚 Documentation:"
echo "• API Docs: http://localhost:8000/docs (after starting)"
echo "• Health Check: http://localhost:8000/health"
echo ""
echo "🔗 Integration:"
echo "• Frontend: Update API endpoints to http://localhost:8000"
echo "• MCP: Configure external tools to connect to MCP server"
echo ""
print_warning "Remember to add this directory to your PATH or use full paths"

# Make sure the virtual environment is activated for the user
echo ""
echo "To activate the virtual environment manually:"
echo "source $VENV_PATH/bin/activate"
