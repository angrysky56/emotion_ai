"""
Aura Memvid-Compatible MCP Tools
Provides memvid-like archival functionality without dependency conflicts
"""

import mcp.types as types
from pydantic import BaseModel
from typing import Optional
import json
import logging

# Import the compatible system
from aura_memvid_compatible import get_aura_memvid_compatible

logger = logging.getLogger(__name__)

class MemvidSearchParams(BaseModel):
    query: str
    user_id: str
    max_results: int = 10

class MemvidArchiveParams(BaseModel):
    user_id: Optional[str] = None

class KnowledgeImportParams(BaseModel):
    source_path: str
    archive_name: str

def add_compatible_memvid_tools(mcp_server):
    """Add memvid-compatible tools to existing MCP server"""
    
    @mcp_server.tool()
    async def search_hybrid_memory(params: MemvidSearchParams) -> types.CallToolResult:
        """
        Search across both active ChromaDB memory and compressed archives
        Provides unified search across Aura's entire memory system
        """
        try:
            system = get_aura_memvid_compatible()
            results = system.search_unified(
                query=params.query,
                user_id=params.user_id,
                max_results=params.max_results
            )
            
            # Format results for better display
            formatted_response = {
                "status": "success",
                "query": params.query,
                "user_id": params.user_id,
                "summary": {
                    "total_results": results["total_results"],
                    "active_results": len(results["active_results"]),
                    "archive_results": len(results["archive_results"])
                },
                "results": results
            }
            
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps(formatted_response, indent=2, default=str)
                )]
            )
            
        except Exception as e:
            logger.error("Error in hybrid memory search: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error", 
                        "error": str(e),
                        "query": params.query,
                        "user_id": params.user_id
                    }, indent=2)
                )],
                isError=True
            )
    
    @mcp_server.tool()
    async def archive_old_conversations(params: MemvidArchiveParams) -> types.CallToolResult:
        """
        Archive old conversations from ChromaDB to compressed format
        Frees up active memory while preserving searchable long-term storage
        """
        try:
            system = get_aura_memvid_compatible()
            result = system.archive_old_conversations(params.user_id)
            
            response_data = {
                "status": "success",
                "archival_summary": {
                    "conversations_archived": result.get("archived_count", 0),
                    "archive_name": result.get("archive_name", "none"),
                    "compression_ratio": result.get("compression_ratio", 0),
                    "size_mb": result.get("compressed_size_mb", 0)
                },
                "full_result": result
            }
            
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2, default=str)
                )]
            )
            
        except Exception as e:
            logger.error("Error archiving conversations: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error", 
                        "error": str(e)
                    }, indent=2)
                )],
                isError=True
            )
    
    @mcp_server.tool()
    async def import_knowledge_archive(params: KnowledgeImportParams) -> types.CallToolResult:
        """
        Import documents into compressed knowledge archive
        Creates searchable compressed archives from external documents
        """
        try:
            system = get_aura_memvid_compatible()
            result = system.import_knowledge_base(
                params.source_path,
                params.archive_name
            )
            
            response_data = {
                "status": "success",
                "import_summary": {
                    "archive_name": result.get("archive_name", params.archive_name),
                    "chunks_imported": result.get("chunks_imported", 0),
                    "compressed_size_mb": result.get("compressed_size_mb", 0),
                    "compression_ratio": result.get("compression_ratio", 0)
                },
                "full_result": result
            }
            
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2, default=str)
                )]
            )
            
        except Exception as e:
            logger.error("Error importing knowledge archive: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error", 
                        "error": str(e),
                        "source_path": params.source_path,
                        "archive_name": params.archive_name
                    }, indent=2)
                )],
                isError=True
            )
    
    @mcp_server.tool()
    async def get_memory_system_stats() -> types.CallToolResult:
        """
        Get comprehensive statistics about the hybrid memory system
        Shows active memory, archives, and compression ratios
        """
        try:
            system = get_aura_memvid_compatible()
            stats = system.get_system_stats()
            
            # Create a summary for easy reading
            summary = {
                "system_type": "Aura Memvid-Compatible",
                "active_memory_total": sum(stats["active_memory"].values()),
                "total_archives": len(stats["archives"]),
                "archive_compatible": stats["archive_compatible"]
            }
            
            response_data = {
                "status": "success",
                "summary": summary,
                "detailed_stats": stats
            }
            
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2, default=str)
                )]
            )
            
        except Exception as e:
            logger.error("Error getting system stats: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error", 
                        "error": str(e)
                    }, indent=2)
                )],
                isError=True
            )
    
    @mcp_server.tool()
    async def list_archives() -> types.CallToolResult:
        """
        List all available memory archives with their details
        """
        try:
            system = get_aura_memvid_compatible()
            stats = system.get_system_stats()
            
            archives_info = []
            for archive_name, archive_stats in stats["archives"].items():
                archives_info.append({
                    "name": archive_name,
                    "chunks": archive_stats.get("total_chunks", 0),
                    "created": archive_stats.get("created", "unknown"),
                    "version": archive_stats.get("version", "unknown")
                })
            
            response_data = {
                "status": "success",
                "total_archives": len(archives_info),
                "archives": archives_info
            }
            
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2, default=str)
                )]
            )
            
        except Exception as e:
            logger.error("Error listing archives: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error", 
                        "error": str(e)
                    }, indent=2)
                )],
                isError=True
            )
    
    logger.info("✅ Added Memvid-compatible tools to Aura MCP server")
