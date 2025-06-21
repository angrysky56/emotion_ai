# Aura Backend Startup Guide

This guide assumes you have already run the main setup script (`setup_aura.sh`) from the project root directory and that the Python virtual environment (`.venv/`) has been created inside `aura_backend/`.

## Activating the Environment
Before running any backend scripts, ensure your virtual environment is active:
```bash
source .venv/bin/activate
```
You'll need to do this every time you open a new terminal session to work with the backend.

## Starting Aura Services

There are two main ways to start Aura:

### Option 1: Start Backend and Frontend Together (Recommended for Development)
From the `aura_backend` directory, run:
```bash
./start.sh --with-frontend
```
This script will:
- Start the Aura FastAPI backend server (API available at `http://localhost:8000`).
- Start the frontend development server (UI available at `http://localhost:5173`).

### Option 2: Start Only the Backend API Server
From the `aura_backend` directory, run:
```bash
./start.sh
```
This will start only the Aura FastAPI backend server. You can then start the frontend separately if needed.

### Option 3: Start Frontend Separately
If you want to manage the frontend process independently:
1. Navigate to the project root directory (one level up from `aura_backend`).
2. Run the frontend start script from `aura_backend` (it navigates to the correct directory):
   ```bash
   # Make sure you are in the project root if running this way,
   # or just use the start_frontend.sh from within aura_backend
   cd ..
   ./aura_backend/start_frontend.sh
   ```
   Alternatively, from within the `aura_backend` directory:
   ```bash
   ./start_frontend.sh
   ```
   This script will:
   - Navigate to the parent directory (project root).
   - Run `npm install` if `node_modules` is missing.
   - Start the frontend development server (UI available at `http://localhost:5173`).

## Verifying Everything Works

1. **Check API Health**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check MCP Tools**:
   Ensure your virtual environment is active (`source .venv/bin/activate`). Then, from the `aura_backend` directory:
   ```bash
   # Run the test script
   python test_mcp_tools.py
   ```

3. **Check Tool Availability in UI**:
   - Open http://localhost:5173
   - Ask Aura: "What MCP tools do you have?"
   - Or: "List your available MCP tools"

## About MCP Tools

Aura has access to various MCP tools:

### Internal Tools (aura-companion):
- `search_aura_memories` - Search conversation history
- `analyze_aura_emotional_patterns` - Analyze emotional trends
- `store_aura_conversation` - Store memories
- `get_aura_user_profile` - Get user profiles
- `export_aura_user_data` - Export data
- `query_aura_emotional_states` - Info about emotions
- `query_aura_aseke_framework` - Info about ASEKE

### External Tools (if configured):
- Various tools from sqlite, brave-search, docker-mcp, etc.

## Using MCP Tools

To use a tool, format requests like:
```
@mcp.tool("search_aura_memories", {"user_id": "Ty", "query": "previous conversations"})
```

## Troubleshooting

```bash
fuser -k 8000/tcp
```

### MCP Server Not Starting
- Check `aura_mcp_server.log` for errors
- Ensure FastMCP is installed: `pip install fastmcp`
- Check that `aura_server.py` has correct Python shebang

### No Tools Available
- Ensure MCP server is running: `ps aux | grep aura_mcp_wrapper`
- Check `mcp_client_config.json` includes aura-companion
- Restart all services

### Chat Context Not Working
- The system now properly maintains chat context
- Each conversation has a session_id for continuity
- Memory search is performed for relevant context

## Directory Structure
- `aura_chroma_db/` - Vector database storage
- `aura_data/` - User profiles and exports
- `scripts/` - Helper scripts
- `.venv/` - Python virtual environment

## Logs
- `aura_mcp_server.log` - MCP server logs
- API logs appear in terminal
