#!/bin/bash
echo "🚀 Starting Aura API Server..."
if [ -d "../.venv" ]; then
    VENV_PATH="../.venv"
elif [ -d ".venv" ]; then
    VENV_PATH=".venv"
fi

if [ -n "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    python main.py
else
    echo "❌ Virtual environment not found. Run 'uv venv' in the project root."
    exit 1
fi
