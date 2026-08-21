"""
Aura + Memvid MCP Tools Integration (FIXED VERSION)
===================================================

This module provides MCP tools for integrating real memvid functionality
with Aura's memory system. Uses actual memvid QR-code video compression!
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import mcp.types as types

# Import the real memvid integration
try:
    try:
        from aura_backend.aura_real_memvid import (
            REAL_MEMVID_AVAILABLE,
            get_aura_real_memvid,
        )
    except ImportError:
        from aura_real_memvid import REAL_MEMVID_AVAILABLE, get_aura_real_memvid
except ImportError:
    REAL_MEMVID_AVAILABLE = False
    get_aura_real_memvid = None

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ============================================================================
# MCP Tool Parameter Models
# ============================================================================


class MemvidSearchParams(BaseModel):
    query: str
    user_id: str
    max_results: int = 10


class MemvidArchiveParams(BaseModel):
    user_id: Optional[str] = None


class MemvidImportParams(BaseModel):
    source_path: str
    archive_name: str


class MemvidChatParams(BaseModel):
    archive_name: str
    message: str


# ============================================================================
# MCP Response Helper
# ============================================================================


def create_memvid_response(
    data: Dict[str, Any], is_error: bool = False
) -> types.CallToolResult:
    """Create properly formatted MCP response"""
    return types.CallToolResult(
        content=[
            types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))
        ],
        isError=is_error,
    )


# ============================================================================
# Helper Functions
# ============================================================================


def get_chroma_client():
    """Get ChromaDB client, either from main module or create fallback"""
    try:
        try:
            from main import vector_db
        except ImportError:
            from aura_backend.main import vector_db

        return vector_db.client if vector_db else None
    except ImportError:
        # Fallback to create our own instance if needed
        from pathlib import Path

        import chromadb
        from chromadb.config import Settings

        persist_directory = Path("./aura_chroma_db")
        persist_directory.mkdir(exist_ok=True)
        return chromadb.PersistentClient(
            path=str(persist_directory),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )


# ============================================================================
# MCP Tools Integration Function
# ============================================================================


def add_compatible_memvid_tools(mcp_instance):
    """
    Add memvid-compatible tools to the MCP server instance

    Args:
        mcp_instance: FastMCP instance to add tools to
    """

    if not REAL_MEMVID_AVAILABLE:
        logger.warning("⚠️ Real memvid not available, memvid tools will be disabled")
        return

    @mcp_instance.tool()
    async def search_memvid_archives(
        params: MemvidSearchParams,
    ) -> types.CallToolResult:
        """
        Search across Aura's memory systems including real memvid archives

        This tool searches both active ChromaDB memory and compressed
        archives created with memvid's revolutionary MV2 single-file technology!
        """
        try:
            if not REAL_MEMVID_AVAILABLE or get_aura_real_memvid is None:
                raise RuntimeError("Real memvid integration not available")
            chroma_client = get_chroma_client()
            memvid_system = get_aura_real_memvid(existing_chroma_client=chroma_client)

            # Perform unified search across active memory and video archives
            results = memvid_system.search_unified(
                query=params.query,
                user_id=params.user_id,
                max_results=params.max_results,
            )

            logger.info(
                f"🎥 Memvid search completed: {results['total_results']} results found"
            )

            response_data = {
                "status": "success",
                "search_results": results,
                "memvid_enabled": True,
                "video_archives_searched": len(results.get("video_archive_results", []))
                > 0,
            }

            return create_memvid_response(response_data)

        except Exception as e:
            logger.error("❌ Memvid search failed: %s", e)
            error_data = {
                "status": "error",
                "error": str(e),
                "query": params.query,
                "user_id": params.user_id,
            }
            return create_memvid_response(error_data, is_error=True)

    @mcp_instance.tool()
    async def archive_conversations_to_video(
        params: MemvidArchiveParams,
    ) -> types.CallToolResult:
        """
        Archive old conversations to compressed MV2 format using real memvid

        This feature compresses conversation history into high-performance
        single-file archives while maintaining full searchability!
        """
        try:
            if not REAL_MEMVID_AVAILABLE or get_aura_real_memvid is None:
                raise RuntimeError("Real memvid integration not available")
            chroma_client = get_chroma_client()
            memvid_system = get_aura_real_memvid(existing_chroma_client=chroma_client)

            # Archive conversations
            result = memvid_system.archive_conversations_to_video(
                user_id=params.user_id
            )

            logger.info(
                f"🎬 Video archival completed: {result.get('archived_count', 0)} conversations"
            )

            response_data = {
                "status": "success",
                "archival_result": result,
                "compression_enabled": True,
            }

            return create_memvid_response(response_data)

        except Exception as e:
            logger.error("❌ Video archival failed: %s", e)
            error_data = {"status": "error", "error": str(e), "user_id": params.user_id}
            return create_memvid_response(error_data, is_error=True)

    @mcp_instance.tool()
    async def import_knowledge_to_video(
        params: MemvidImportParams,
    ) -> types.CallToolResult:
        """
        Import external documents and create searchable memvid knowledge bases

        Converts PDFs, text files, and directories into compressed, searchable
        single-file archives using memvid's revolutionary MV2 technology!
        """
        try:
            # Get the existing ChromaDB client using globals or import from main
            try:
                from main import vector_db
            except ImportError:
                # Fallback to create our own instance if needed
                from pathlib import Path

                import chromadb
                from chromadb.config import Settings

                persist_directory = Path("./aura_chroma_db")
                persist_directory.mkdir(exist_ok=True)
                client = chromadb.PersistentClient(
                    path=str(persist_directory),
                    settings=Settings(anonymized_telemetry=False, allow_reset=True),
                )

                # Create a simple wrapper for client access
                class VectorDBWrapper:
                    def __init__(self, client):
                        self.client = client

                vector_db = VectorDBWrapper(client)

            # Initialize AuraRealMemvid with existing ChromaDB client
            if not REAL_MEMVID_AVAILABLE or get_aura_real_memvid is None:
                raise RuntimeError("Real memvid integration not available")
            chroma_client = vector_db.client if vector_db else None
            memvid_system = get_aura_real_memvid(existing_chroma_client=chroma_client)

            # Import knowledge
            result = memvid_system.import_knowledge_to_video(
                source_path=params.source_path,
                archive_name=params.archive_name,
            )

            logger.info("📚 Knowledge import completed: %s", params.archive_name)

            response_data = {
                "status": "success",
                "import_result": result,
                "archive_created": True,
                "archive_name": params.archive_name,
            }

            return create_memvid_response(response_data)

        except Exception as e:
            logger.error("❌ Knowledge import failed: %s", e)
            error_data = {
                "status": "error",
                "error": str(e),
                "source_path": params.source_path,
                "archive_name": params.archive_name,
            }
            return create_memvid_response(error_data, is_error=True)

    @mcp_instance.tool()
    async def list_memvid_archives() -> types.CallToolResult:
        """
        List all available memvid archives with details

        Shows all compressed knowledge bases created with memvid,
        including file sizes and searchable content stats.
        """
        try:
            # Get the existing ChromaDB client using globals or import from main
            try:
                from main import vector_db
            except ImportError:
                # Fallback to create our own instance if needed
                from pathlib import Path

                import chromadb
                from chromadb.config import Settings

                persist_directory = Path("./aura_chroma_db")
                persist_directory.mkdir(exist_ok=True)
                client = chromadb.PersistentClient(
                    path=str(persist_directory),
                    settings=Settings(anonymized_telemetry=False, allow_reset=True),
                )

                # Create a simple wrapper for client access
                class VectorDBWrapper:
                    def __init__(self, client):
                        self.client = client

                vector_db = VectorDBWrapper(client)
            # Initialize AuraRealMemvid with existing ChromaDB client
            if not REAL_MEMVID_AVAILABLE or get_aura_real_memvid is None:
                raise RuntimeError("Real memvid integration not available")
            chroma_client = vector_db.client if vector_db else None
            memvid_system = get_aura_real_memvid(existing_chroma_client=chroma_client)

            # List video archives
            archives = memvid_system.list_video_archives()

            # Get system stats
            stats = memvid_system.get_system_stats()

            logger.info("📋 Listed %s video archives", len(archives))

            response_data = {
                "status": "success",
                "archives": archives,
                "system_stats": stats,
                "total_archives": len(archives),
                "memvid_technology": "MV2 single-file memory",
            }

            return create_memvid_response(response_data)

        except Exception as e:
            logger.error("❌ Failed to list archives: %s", e)
            error_data = {"status": "error", "error": str(e)}
            return create_memvid_response(error_data, is_error=True)

    @mcp_instance.tool()
    async def get_memvid_system_stats() -> types.CallToolResult:
        """
        Get comprehensive statistics about the memvid system

        Provides detailed information about memory compression performance,
        storage efficiency, and system status.
        """
        try:
            # Get the existing ChromaDB client using globals or import from main
            try:
                from main import vector_db
            except ImportError:
                # Fallback to create our own instance if needed
                from pathlib import Path

                import chromadb
                from chromadb.config import Settings

                persist_directory = Path("./aura_chroma_db")
                persist_directory.mkdir(exist_ok=True)
                client = chromadb.PersistentClient(
                    path=str(persist_directory),
                    settings=Settings(anonymized_telemetry=False, allow_reset=True),
                )

                # Create a simple wrapper for client access
                class VectorDBWrapper:
                    def __init__(self, client):
                        self.client = client

                vector_db = VectorDBWrapper(client)

            # Initialize AuraRealMemvid with existing ChromaDB client
            if not REAL_MEMVID_AVAILABLE or get_aura_real_memvid is None:
                raise RuntimeError("Real memvid integration not available")
            chroma_client = vector_db.client if vector_db else None
            memvid_system = get_aura_real_memvid(existing_chroma_client=chroma_client)

            # Get comprehensive stats
            stats = memvid_system.get_system_stats()

            logger.info("📊 Generated memvid system statistics")

            response_data = {
                "status": "success",
                "system_statistics": stats,
                "real_memvid_available": REAL_MEMVID_AVAILABLE,
                "technology": "MV2 single-file memory compression",
                "timestamp": datetime.now().isoformat(),
            }

            return create_memvid_response(response_data)

        except Exception as e:
            logger.error("❌ Failed to get system stats: %s", e)
            error_data = {"status": "error", "error": str(e)}
            return create_memvid_response(error_data, is_error=True)

    logger.info("✅ Added 5 memvid-compatible MCP tools successfully")
    logger.info(
        "🎥 Tools: search_memvid_archives, archive_conversations_to_video, import_knowledge_to_video, list_memvid_archives, get_memvid_system_stats"
    )
