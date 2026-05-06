#!/bin/bash

# Aura AI - Stop All Services Script
# This script stops both backend and frontend services

echo "🛑 Stopping Aura AI Services..."
echo "==============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is in use
port_in_use() {
	lsof -ti:"$1" >/dev/null 2>&1
}

# Function to kill processes on specific ports
kill_port() {
	local port=$1
	local service=$2

	if port_in_use "$port"; then
		echo -e "${YELLOW}Stopping $service on port $port...${NC}"
		fuser -k "$port"/tcp 2>/dev/null || true
		sleep 2

		if port_in_use "$port"; then
			echo -e "${RED}Force killing $service processes...${NC}"
			pkill -f "uvicorn.*$port" 2>/dev/null || true
			pkill -f "vite.*$port" 2>/dev/null || true
			pkill -f "node.*$port" 2>/dev/null || true
			sleep 2
		fi

		if ! port_in_use "$port"; then
			echo -e "${GREEN}✅ $service stopped successfully${NC}"
		else
			echo -e "${RED}❌ Failed to stop $service${NC}"
		fi
	else
		echo -e "${BLUE}$service is not running on port $port${NC}"
	fi
}

# Stop services
echo -e "${BLUE}Stopping Aura AI services...${NC}"

kill_port 8000 "Backend"
kill_port 5173 "Frontend"

# Also kill any remaining processes that might be related
echo -e "${BLUE}Cleaning up remaining processes...${NC}"
pkill -f "aura" 2>/dev/null || true
pkill -f "uvicorn.*main:app" 2>/dev/null || true

echo ""
echo -e "${GREEN}🛑 All Aura AI services stopped${NC}"
echo -e "${BLUE}You can now safely restart the system with ./start_full_system.sh${NC}"
