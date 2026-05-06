"""
Enhanced Aura MCP Tools with Memvid Integration
"""

import mcp.types as types
from pydantic import BaseModel
from typing import Optional
import json
import logging

# Import the hybrid system. Was moved to archive
from aura_memvid_hybrid import AuraMemvidHybrid

logger = logging.getLogger(__name__)

class MemvidSearchParams(BaseModel):
    query: str
    user_id: str
    max_results: int = 10

class MemvidArchiveParams(BaseModel):
    archive_name: Optional[str] = None

class KnowledgeImportParams(BaseModel):
    source_path: str
    archive_name: str

# Global hybrid system instance
_hybrid_system = None

def get_hybrid_system():
    """Get or create the hybrid system instance"""
    global _hybrid_system
    if _hybrid_system is None:
        _hybrid_system = AuraMemvidHybrid()
    return _hybrid_system

def add_memvid_tools(mcp_server):
    """Add memvid tools to existing MCP server"""

    @mcp_server.tool()
    async def search_hybrid_memory(params: MemvidSearchParams) -> types.CallToolResult:
        """
        Search across both active ChromaDB memory and Memvid archives
        """
        try:
            hybrid_system = get_hybrid_system()
            results = hybrid_system.unified_search(
                query=params.query,
                user_id=params.user_id,
                max_results=params.max_results
            )

            response_data = {
                "status": "success",
                "results": results
            }

            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2, default=str)
                )]
            )

        except Exception as e:
            logger.error("Error in hybrid memory search: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "error": str(e)}, indent=2)
                )],
                isError=True
            )

    @mcp_server.tool()
    async def archive_old_memories(params: MemvidArchiveParams) -> types.CallToolResult:
        """
        Archive old conversations to compressed Memvid format
        """
        try:
            hybrid_system = get_hybrid_system()
            result = hybrid_system.archive_old_memories(params.archive_name)

            response_data = {
                "status": "success",
                "archival_result": result
            }

            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2, default=str)
                )]
            )

        except Exception as e:
            logger.error("Error archiving memories: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "error": str(e)}, indent=2)
                )],
                isError=True
            )

    @mcp_server.tool()
    async def import_knowledge_base(params: KnowledgeImportParams) -> types.CallToolResult:
        """
        Import documents/PDFs into compressed Memvid archives
        """
        try:
            hybrid_system = get_hybrid_system()
            result = hybrid_system.import_knowledge_base(
                params.source_path,
                params.archive_name
            )

            response_data = {
                "status": "success",
                "import_result": result
            }

            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2, default=str)
                )]
            )

        except Exception as e:
            logger.error("Error importing knowledge: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "error": str(e)}, indent=2)
                )],
                isError=True
            )

    @mcp_server.tool()
    async def get_hybrid_system_stats() -> types.CallToolResult:
        """
        Get hybrid memory system statistics
        """
        try:
            hybrid_system = get_hybrid_system()
            stats = hybrid_system.get_system_stats()

            response_data = {
                "status": "success",
                "stats": stats
            }

            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2, default=str)
                )]
            )

        except Exception as e:
            logger.error("Error getting stats: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "error": str(e)}, indent=2)
                )],
                isError=True
            )

    logger.info("✅ Added Memvid tools to Aura MCP server")
