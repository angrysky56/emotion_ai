#!/bin/bash
# This should be using uv
# Install all required dependencies for Aura MCP integration

echo "Installing Aura MCP dependencies..."

# Try to detect the Python command
if command -v python3 >/dev/null 2>&1; then
	PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
	PYTHON_CMD="python"
else
	echo "ERROR: Neither python3 nor python commands found. Please install Python."
	exit 1
fi

# Install pip if not available
if ! command -v pip >/dev/null 2>&1 && ! command -v pip3 >/dev/null 2>&1; then
	echo "Installing pip..."
	$PYTHON_CMD -m ensurepip --upgrade || curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && $PYTHON_CMD get-pip.py
fi

# Determine pip command
if command -v pip3 >/dev/null 2>&1; then
	PIP_CMD="pip3"
else
	PIP_CMD="pip"
fi

echo "Using Python: $($PYTHON_CMD --version)"
echo "Using Pip: $($PIP_CMD --version)"

# Install the core dependencies
echo "Installing sentence-transformers..."
$PIP_CMD install sentence-transformers

echo "Installing MCP dependencies..."
$PIP_CMD install "mcp>=1.9.2" "fastmcp>=2.5.2"

echo "Installing ChromaDB..."
$PIP_CMD install chromadb

echo "Installing aiofiles..."
$PIP_CMD install aiofiles

echo "Installing required tools for MCP..."
$PIP_CMD install typing-extensions pydantic fastapi uvicorn >=2.0.0

echo "All dependencies installed successfully!"
