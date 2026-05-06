#!/bin/bash
# aura_backend/stop_mcp_services.sh
# Helper script to stop Aura's services

echo "Stopping Aura Services..."

# Stop the Aura  server - handle both python and python3 commands
if pgrep -f "python3? aura_server.py" > /dev/null; then
    echo "Stopping Aura server..."
    pkill -f "python3? aura_server.py"
    echo "Aura server stopped."
else
    echo "Aura server is not running."
fi

echo "All Aura services stopped."
