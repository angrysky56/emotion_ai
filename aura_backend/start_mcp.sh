#!/bin/bash
echo "🔗 Starting Aura MCP Server..."
if [ -d "../.venv" ]; then
    VENV_PATH="../.venv"
elif [ -d ".venv" ]; then
    VENV_PATH=".venv"
fi

if [ -n "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    python mcp_server.py
else
    echo "❌ Virtual environment not found. Run 'uv venv' in the project root."
    exit 1
fi
