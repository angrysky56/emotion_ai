# Integrations - Emotion AI / Aura

## Core AI Providers
- **Google Gemini**: Primary LLM provider. Used for natural language understanding, generation, and multimodal analysis. Integrated via `@google/genai` on frontend and `google-genai` on backend.
- **Anthropic (Claude)**: Used for advanced reasoning and potentially as the orchestrator in the Reflective Agent Architecture (RAA).
- **OpenAI**: Available for fallback or specific task-oriented models.

## Model Context Protocol (MCP)
- **Aura MCP Server**: The backend exposes its internal tools (memory, vision, emotional analysis) via MCP.
- **MCP Bridge**: `mcp_to_gemini_bridge.py` facilitates communication between Gemini and MCP-enabled tools.
- **MCP Client**: The system can consume external MCP tools to extend its capabilities.

## Data Services
- **ChromaDB**: Core semantic memory store. Handles embedding storage and similarity search for long-term memory.
- **Memvid**: Specialized service for video memory management, archival, and retrieval.
- **Firebase**: Used for logging and potentially real-time persistence/sync.

## System Interfaces
- **Aura API (REST)**: FastAPI-based RESTful interface for frontend-backend communication.
- **WebSockets**: Used for real-time updates (emotional states, cognitive focus, etc.).
- **Local Vision**: Integration with hardware cameras via OpenCV for real-time emotional and presence detection.
