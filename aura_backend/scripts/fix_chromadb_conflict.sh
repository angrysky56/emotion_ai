#!/bin/bash

echo "🔧 Fixing ChromaDB Instance Conflicts..."
echo "========================================="

# Stop all services
echo "🛑 Stopping all services..."
./stop_mcp_services.sh 2>/dev/null || true

# Kill any remaining Python processes that might be holding ChromaDB
echo "🔍 Checking for running Python processes..."
pkill -f "main.py" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "aura_server" 2>/dev/null || true

# Wait a moment for processes to clean up
echo "⏳ Waiting for cleanup..."
sleep 3

# Check if ChromaDB directory exists and is accessible
if [ -d "./aura_chroma_db" ]; then
    echo "📁 ChromaDB directory found"
    ls -la ./aura_chroma_db/ 2>/dev/null || echo "⚠️ Cannot access ChromaDB directory"
else
    echo "📁 ChromaDB directory not found - will be created on startup"
fi

# Check disk space
echo "💾 Checking disk space..."
df -h . | head -2

# Restart services cleanly
echo "🚀 Starting services..."
echo "Starting API server..."
./start_api.sh &

echo "✅ ChromaDB conflict fix complete!"
echo "The backend should now be running without conflicts."
echo "You can now refresh the frontend page."
