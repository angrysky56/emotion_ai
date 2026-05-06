# Aura Backend Startup Guide

## Quick Start

### Option 1: Start Everything (Backend + Frontend)

```bash
./start_complete.sh
```

This will start:

- API Server (http://localhost:8000)
- MCP Server (internal)
- Frontend UI (http://localhost:5173)

### Option 2: Start Backend Only

```bash
./start_all.sh
```

This will start:

- API Server (http://localhost:8000)
- MCP Server (internal)

### Option 3: Start Services Individually

```bash
# Terminal 1: API Server
./start_api.sh

# Terminal 2: MCP Server
./start_mcp_background.sh

# Terminal 3: Frontend
./start_frontend.sh
# OR manually: cd .. && npm run dev
```

## Verifying Everything Works

1. **Check API Health**:

   ```bash
   curl http://localhost:8000/health
   ```

2. **Check MCP Tools**:

   ```bash
   # Run the test script
   cd /home/ty/Repositories/ai_workspace/emotion_ai/aura_backend
   # From the project root
   source .venv/bin/activate

   # Or from aura_backend
   source ../.venv/bin/activate
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
