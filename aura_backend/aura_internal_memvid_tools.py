"""
Aura Internal Memvid Management Tools
===================================

Internal tools that allow Aura to directly manage its own memvid system.
These are different from the MCP tools - these are for Aura's internal use.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import existing memvid integration
try:
    try:
        from aura_backend.aura_real_memvid import (
            REAL_MEMVID_AVAILABLE,
            get_aura_real_memvid,
        )
    except ImportError:
        from aura_real_memvid import REAL_MEMVID_AVAILABLE, get_aura_real_memvid

    INTERNAL_MEMVID_AVAILABLE = True

    # Import v2 SDK
    try:
        import memvid_sdk
    except ImportError:
        memvid_sdk = None
except ImportError:
    REAL_MEMVID_AVAILABLE = False
    get_aura_real_memvid = None
    INTERNAL_MEMVID_AVAILABLE = False
    memvid_sdk = None

logger = logging.getLogger(__name__)


class AuraInternalMemvidTools:
    """
    Internal tools for Aura to manage its own memvid system.
    These are NOT MCP tools - these are for Aura's direct use.

    Provides sophisticated video memory management capabilities including:
    - Archive creation and management
    - Knowledge library organization
    - Selective conversation archiving
    - Memory statistics and analysis
    """

    def __init__(self, vector_db_client: Optional[Any] = None) -> None:
        """
        Initialize the internal memvid tools.

        Args:
            vector_db_client: Optional existing vector database client for integration
        """
        self.vector_db_client = vector_db_client
        if INTERNAL_MEMVID_AVAILABLE and get_aura_real_memvid is not None:
            try:
                # Initialize with existing ChromaDB client to avoid conflicts
                self.memvid_system = get_aura_real_memvid(
                    existing_chroma_client=vector_db_client
                )
                logger.info("✅ Aura internal memvid tools initialized successfully")
            except Exception as e:
                logger.error("❌ Failed to initialize internal memvid tools: %s", e)
                self.memvid_system = None
        else:
            logger.warning("⚠️ Real memvid not available for internal tools")
            self.memvid_system = None

    async def list_video_archives(self) -> Dict[str, Any]:
        """
        List all video archives available to Aura.

        Returns comprehensive information about video memory archives including
        size, compression statistics, and searchability status.

        Returns:
            Dictionary containing archive list and statistics
        """
        if not self.memvid_system:
            return {
                "status": "error",
                "message": "Memvid system not available",
                "archives": [],
                "total_archives": 0,
            }

        try:
            archives = self.memvid_system.list_video_archives()

            result = {
                "status": "success",
                "archives": archives,
                "total_archives": len(archives),
                "total_size_mb": sum(
                    archive.get("video_size_mb", 0) for archive in archives
                ),
                "compression_technology": "Real QR-code video compression",
                "searchable": True,
            }

            logger.info("📋 Listed %s video archives for Aura", len(archives))
            return result

        except Exception as e:
            logger.error("❌ Failed to list video archives: %s", e)
            return {
                "status": "error",
                "message": str(e),
                "archives": [],
                "total_archives": 0,
            }

    async def search_all_memories(
        self, query: str, user_id: str, max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search across ALL memory systems (active + video archives).

        This is Aura's unified memory search capability that searches both
        active vector database memories and compressed video archives.

        Args:
            query: Search query string
            user_id: User identifier for scoped search
            max_results: Maximum number of results to return

        Returns:
            Dictionary containing unified search results from all memory systems
        """
        if not self.memvid_system:
            return {
                "status": "error",
                "message": "Memvid system not available",
                "results": [],
                "total_results": 0,
            }

        try:
            # Perform unified search
            search_results = self.memvid_system.search_unified(
                query=query, user_id=user_id, max_results=max_results
            )

            # Format for internal use
            result = {
                "status": "success",
                "query": query,
                "user_id": user_id,
                "total_results": search_results["total_results"],
                "active_memory_results": len(search_results["active_results"]),
                "video_archive_results": len(search_results["video_archive_results"]),
                "all_results": search_results["active_results"]
                + search_results["video_archive_results"],
                "search_technology": "Unified vector + video search",
                "errors": search_results.get("errors", []),
            }

            logger.info(
                f"🔍 Unified search completed: {result['total_results']} results for '{query}'"
            )
            return result

        except Exception as e:
            logger.error("❌ Failed to search all memories: %s", e)
            return {
                "status": "error",
                "message": str(e),
                "results": [],
                "total_results": 0,
            }

    async def archive_old_conversations(
        self, user_id: Optional[str] = None, codec: str = "h264"
    ) -> Dict[str, Any]:
        """
        Archive old conversations to video format.

        Aura can use this to manage its own memory efficiently by converting
        old conversations to compressed video format while maintaining searchability.

        Args:
            user_id: Optional user ID to filter conversations for archiving
            codec: Video codec to use for compression (default: h264)

        Returns:
            Dictionary containing archiving results and statistics
        """
        if not self.memvid_system:
            return {
                "status": "error",
                "message": "Memvid system not available",
                "archived_count": 0,
            }

        try:
            # Archive conversations to video
            result = self.memvid_system.archive_conversations_to_video(
                user_id=user_id, codec=codec
            )

            if "error" in result:
                return {
                    "status": "error",
                    "message": result["error"],
                    "archived_count": 0,
                }

            # Format success response
            response = {
                "status": "success",
                "archived_count": result.get("archived_count", 0),
                "archive_name": result.get("archive_name", "unknown"),
                "video_file": result.get("video_file", ""),
                "video_size_mb": result.get("video_size_mb", 0),
                "compression_ratio": result.get("compression_ratio", 0),
                "technology": "QR-code video compression",
                "codec_used": codec,
            }

            logger.info(
                f"🎬 Archived {response['archived_count']} conversations to video"
            )
            return response

        except Exception as e:
            logger.error("❌ Failed to archive conversations: %s", e)
            return {"status": "error", "message": str(e), "archived_count": 0}

    async def import_knowledge(
        self, source_path: str, archive_name: str, codec: str = "h264"
    ) -> Dict[str, Any]:
        """
        Import external knowledge into video archives.

        Aura can use this to expand its knowledge base by importing external
        content and converting it to searchable video archives.

        Args:
            source_path: Path to the source file containing knowledge to import
            archive_name: Name for the created archive
            codec: Video codec to use for compression (default: h264)

        Returns:
            Dictionary containing import results and archive statistics
        """
        if not self.memvid_system:
            return {"status": "error", "message": "Memvid system not available"}

        try:
            # Import knowledge to video
            result = self.memvid_system.import_knowledge_to_video(
                source_path=source_path, archive_name=archive_name, codec=codec
            )

            if "error" in result:
                return {"status": "error", "message": result["error"]}

            # Format success response
            response = {
                "status": "success",
                "archive_name": result.get("archive_name", archive_name),
                "chunks_imported": result.get("chunks_imported", 0),
                "video_size_mb": result.get("video_size_mb", 0),
                "compression_ratio": result.get("compression_ratio", 0),
                "source_file": source_path,
                "technology": "QR-code video compression",
                "codec_used": codec,
            }

            logger.info("📚 Imported knowledge to video archive: %s", archive_name)
            return response

        except Exception as e:
            logger.error("❌ Failed to import knowledge: %s", e)
            return {"status": "error", "message": str(e)}

    async def get_memory_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive memory system statistics.

        Aura can use this to understand its own memory state, including
        active memory usage, video archive statistics, and efficiency metrics.

        Returns:
            Dictionary containing detailed memory system statistics and metrics
        """
        if not self.memvid_system:
            return {
                "status": "error",
                "message": "Memvid system not available",
                "statistics": {},
            }

        try:
            # Get system stats
            stats = self.memvid_system.get_system_stats()

            # Add additional analysis
            archives = self.memvid_system.list_video_archives()

            result = {
                "status": "success",
                "memory_type": stats.get("memvid_type", "unknown"),
                "real_memvid_available": stats.get("real_memvid_available", False),
                "active_memory": stats.get("active_memory", {}),
                "video_archives": {
                    "count": len(archives),
                    "total_size_mb": stats.get("total_video_size_mb", 0),
                    "archives": archives,
                },
                "technology": "Real QR-code video compression",
                "chromadb_status": stats.get("chromadb_status", "unknown"),
                "efficiency_metrics": {
                    "compression_active": True,
                    "searchable_videos": True,
                    "unified_search": True,
                },
            }

            logger.info("📊 Generated memory system statistics for Aura")
            return result

        except Exception as e:
            logger.error("❌ Failed to get memory statistics: %s", e)
            return {"status": "error", "message": str(e), "statistics": {}}

    async def create_knowledge_summary(
        self, archive_name: str, max_entries: int = 10
    ) -> Dict[str, Any]:
        """
        Create a summary of what's in a video archive.

        Aura can use this to understand its own knowledge by generating
        summaries of archive contents and key information.

        Args:
            archive_name: Name of the archive to summarize
            max_entries: Maximum number of sample entries to include

        Returns:
            Dictionary containing archive summary with sample content and statistics
        """
        if not self.memvid_system:
            return {"status": "error", "message": "Memvid system not available"}

        try:
            # Check if archive exists
            archives = self.memvid_system.list_video_archives()
            target_archive = None

            for archive in archives:
                if archive["name"] == archive_name:
                    target_archive = archive
                    break

            if not target_archive:
                return {
                    "status": "error",
                    "message": f"Archive '{archive_name}' not found",
                }

            # Search for general content to get a sample
            sample_search = self.memvid_system.search_unified(
                query="content knowledge information",
                user_id="aura_internal",  # Special user ID for Aura's internal searches
                max_results=max_entries,
            )

            # Filter for this specific archive
            archive_results = [
                result
                for result in sample_search.get("video_archive_results", [])
                if result.get("source", "").startswith(f"video_archive:{archive_name}")
            ]

            result = {
                "status": "success",
                "archive_name": archive_name,
                "total_frames": target_archive.get("total_frames", 0),
                "video_size_mb": target_archive.get("video_size_mb", 0),
                "sample_content": [
                    {
                        "text_preview": (
                            result["text"][:200] + "..."
                            if len(result["text"]) > 200
                            else result["text"]
                        ),
                        "relevance_score": result.get("score", 0),
                        "frame": result.get("frame", 0),
                    }
                    for result in archive_results[:max_entries]
                ],
                "content_count": len(archive_results),
                "technology": "QR-code compressed video",
            }

            logger.info("📖 Created knowledge summary for archive: %s", archive_name)
            return result

        except Exception as e:
            logger.error("❌ Failed to create knowledge summary: %s", e)
            return {"status": "error", "message": str(e)}

    async def create_custom_memory_archive(
        self,
        archive_name: str,
        content_list: List[str],
        archive_type: str = "knowledge",
        description: str = "",
        codec: str = "h264",
    ) -> Dict[str, Any]:
        """
        Create a custom memvid archive from specific content.

        Aura can use this to create targeted memory libraries by taking
        specific content and creating organized, searchable video archives.

        Args:
            archive_name: Name for the new archive
            content_list: List of text content to include in the archive
            archive_type: Type of archive (knowledge, conversations, principles, etc.)
            description: Description of what this archive contains
            codec: Video codec to use for compression

        Returns:
            Dictionary containing archive creation results and metadata
        """
        if not self.memvid_system or not REAL_MEMVID_AVAILABLE or not memvid_sdk:
            return {"status": "error", "message": "Memvid v2 SDK not available"}

        try:
            # Build the archive path
            archive_path = Path("./memvid_videos") / f"{archive_name}.mv2"

            # Ensure directory exists
            archive_path.parent.mkdir(exist_ok=True)

            logger.info("🎬 Creating custom %s archive: %s", archive_type, archive_name)

            # Create archive using v2 SDK
            mv = memvid_sdk.create(str(archive_path), enable_vec=True, enable_lex=True)

            # Add content with enhanced metadata
            for i, content in enumerate(content_list):
                # Create rich context for each piece
                enhanced_content = f"""
AURA CUSTOM MEMORY ARCHIVE
==========================
Archive: {archive_name}
Type: {archive_type}
Description: {description}
Entry: {i+1}/{len(content_list)}
Created: {datetime.now().isoformat()}

CONTENT:
{content}
==========================
"""
                # Use v2 put()
                mv.put(
                    title=f"{archive_name} Entry {i+1}",
                    labels=[archive_type, "custom_archive"],
                    metadata={
                        "archive_name": archive_name,
                        "archive_type": archive_type,
                        "entry_index": i,
                    },
                    text=enhanced_content.strip(),
                )

            # Finalize the archive
            mv.close()

            # Get stats for the return result
            archive_stats = {}
            try:
                # Re-open briefly to get stats or just check file size
                file_size_mb = archive_path.stat().st_size / (1024 * 1024)
                archive_stats["size_mb"] = file_size_mb
            except Exception:
                archive_stats["size_mb"] = 0

            # Register the new archive with the memvid system
            self.memvid_system.video_archives[archive_name] = memvid_sdk.use(
                "basic", str(archive_path)
            )

            result = {
                "status": "success",
                "archive_name": archive_name,
                "archive_type": archive_type,
                "description": description,
                "content_count": len(content_list),
                "archive_file": str(archive_path),
                "size_mb": archive_stats.get("size_mb", 0),
                "compression_ratio": len(content_list)
                / max(archive_stats.get("size_mb", 1), 0.1),
                "technology": "Memvid v2 Single-File Archive",
                "created_at": datetime.now().isoformat(),
            }

            logger.info(
                f"✅ Created custom archive '{archive_name}' with {len(content_list)} entries"
            )
            return result

        except Exception as e:
            logger.error("❌ Failed to create custom archive: %s", e)
            return {"status": "error", "message": str(e)}

    async def selective_archive_conversations(
        self,
        user_id: str,
        search_criteria: str,
        archive_name: str,
        max_conversations: int = 50,
    ) -> Dict[str, Any]:
        """
        Selectively archive conversations based on content criteria.

        Aura can use this to organize conversations by topic rather than just age,
        creating topical archives that preserve important conversation themes.

        Args:
            user_id: User whose conversations to search and archive
            search_criteria: What to search for (topic, keywords, etc.)
            archive_name: Name for the new topical archive
            max_conversations: Maximum number of conversations to include

        Returns:
            Dictionary containing selective archiving results and statistics
        """
        if not self.memvid_system:
            return {"status": "error", "message": "Memvid system not available"}

        try:
            # Search for conversations matching criteria using the unified search
            search_results = self.memvid_system.search_unified(
                query=search_criteria, user_id=user_id, max_results=max_conversations
            )

            # Extract active memory results as relevant conversations
            relevant_conversations = search_results.get("active_results", [])

            if not relevant_conversations:
                return {
                    "status": "error",
                    "message": f"No conversations found matching '{search_criteria}'",
                }

            # Extract conversation content
            content_list = []
            conversation_ids = []

            for conv in relevant_conversations:
                content = conv.get("content", "")
                metadata = conv.get("metadata", {})

                # Create rich conversation context
                conversation_entry = f"""
CONVERSATION ARCHIVE ENTRY
=========================
Topic: {search_criteria}
User: {user_id}
Timestamp: {metadata.get('timestamp', 'unknown')}
Sender: {metadata.get('sender', 'unknown')}
Emotional State: {metadata.get('emotion_name', 'normal')}
Similarity Score: {conv.get('similarity', 0):.3f}

CONTENT:
{content}
=========================
"""
                content_list.append(conversation_entry.strip())

                # Track for potential removal from active memory
                if "id" in metadata:
                    conversation_ids.append(metadata["id"])

            # Create the custom archive
            result = await self.create_custom_memory_archive(
                archive_name=archive_name,
                content_list=content_list,
                archive_type="conversations",
                description=f"Conversations about: {search_criteria}",
                codec="h264",
            )

            if result.get("status") == "success":
                result.update(
                    {
                        "search_criteria": search_criteria,
                        "conversations_archived": len(content_list),
                        "conversations_found": len(relevant_conversations),
                        "user_id": user_id,
                    }
                )

                logger.info(
                    f"📂 Selectively archived {len(content_list)} conversations about '{search_criteria}'"
                )

            return result

        except Exception as e:
            logger.error("❌ Failed to selectively archive conversations: %s", e)
            return {"status": "error", "message": str(e)}

    async def create_knowledge_library(
        self,
        library_name: str,
        knowledge_sources: List[Dict[str, str]],
        library_type: str = "reference",
    ) -> Dict[str, Any]:
        """
        Create a specialized knowledge library from multiple sources.

        Aura can use this to build domain-specific memory libraries by
        combining knowledge from various sources into organized collections.

        Args:
            library_name: Name for the knowledge library
            knowledge_sources: List of dicts with 'content', 'source_type', and optional 'name' keys
            library_type: Type of library (reference, principles, templates, etc.)

        Returns:
            Dictionary containing library creation results and metadata
        """
        if not self.memvid_system:
            return {"status": "error", "message": "Memvid system not available"}

        try:
            content_list = []

            for i, source in enumerate(knowledge_sources):
                content = source.get("content", "")
                source_type = source.get("source_type", "unknown")
                source_name = source.get("name", f"Entry {i+1}")

                # Create structured knowledge entry
                knowledge_entry = f"""
KNOWLEDGE LIBRARY ENTRY
======================
Library: {library_name}
Type: {library_type}
Source Type: {source_type}
Source Name: {source_name}
Entry: {i+1}/{len(knowledge_sources)}
Created: {datetime.now().isoformat()}

KNOWLEDGE CONTENT:
{content}
======================
"""
                content_list.append(knowledge_entry.strip())

            # Create the library archive
            result = await self.create_custom_memory_archive(
                archive_name=library_name,
                content_list=content_list,
                archive_type=library_type,
                description=f"{library_type.title()} library with {len(knowledge_sources)} sources",
                codec="h264",
            )

            if result.get("status") == "success":
                result.update(
                    {
                        "library_type": library_type,
                        "sources_count": len(knowledge_sources),
                        "source_types": list(
                            set(
                                source.get("source_type", "unknown")
                                for source in knowledge_sources
                            )
                        ),
                    }
                )

                logger.info(
                    f"📚 Created {library_type} library '{library_name}' with {len(knowledge_sources)} sources"
                )

            return result

        except Exception as e:
            logger.error("❌ Failed to create knowledge library: %s", e)
            return {"status": "error", "message": str(e)}

    async def search_memory_libraries(
        self, query: str, library_filter: Optional[str] = None, max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search across organized memory libraries.

        Aura can use this to find which libraries contain relevant information
        and get targeted results from specific knowledge domains.

        Args:
            query: What to search for across libraries
            library_filter: Optional filter for specific library types or names
            max_results: Maximum results to return across all libraries

        Returns:
            Dictionary containing search results organized by library with relevance scores
        """
        if not self.memvid_system:
            return {"status": "error", "message": "Memvid system not available"}

        try:
            # Get all archives
            archives = self.memvid_system.list_video_archives()

            # Filter by library type if specified
            if library_filter:
                archives = [
                    archive
                    for archive in archives
                    if library_filter.lower() in archive.get("name", "").lower()
                ]

            # Search each archive and collect results
            library_results = {}

            for archive in archives:
                archive_name = archive["name"]

                try:
                    # Search this specific archive
                    search_results = self.memvid_system.search_unified(
                        query=query,
                        user_id="aura_internal",
                        max_results=max_results // max(len(archives), 1),
                    )

                    # Filter for this archive
                    archive_matches = [
                        result
                        for result in search_results.get("video_archive_results", [])
                        if archive_name in result.get("source", "")
                        or archive_name in result.get("archive_file", "")
                    ]

                    if archive_matches:
                        library_results[archive_name] = {
                            "archive_info": archive,
                            "matches": archive_matches[:5],  # Top 5 matches per library
                            "match_count": len(archive_matches),
                            "best_score": (
                                max(match.get("score", 0) for match in archive_matches)
                                if archive_matches
                                else 0
                            ),
                        }

                except Exception as e:
                    logger.warning(
                        "⚠️ Failed to search archive %s: %s", archive_name, e
                    )
                    continue

            # Sort libraries by best match score
            sorted_libraries = sorted(
                library_results.items(), key=lambda x: x[1]["best_score"], reverse=True
            )

            result = {
                "status": "success",
                "query": query,
                "library_filter": library_filter,
                "total_libraries_searched": len(archives),
                "libraries_with_matches": len(library_results),
                "library_results": dict(sorted_libraries[:max_results]),
                "search_summary": [
                    {
                        "library_name": name,
                        "match_count": info["match_count"],
                        "best_score": info["best_score"],
                        "library_size_mb": info["archive_info"].get("size_mb", 0),
                    }
                    for name, info in sorted_libraries[:max_results]
                ],
            }

            logger.info(
                f"🔍 Searched {len(archives)} libraries, found matches in {len(library_results)} for '{query}'"
            )
            return result

        except Exception as e:
            logger.error("❌ Failed to search memory libraries: %s", e)
            return {"status": "error", "message": str(e)}

    async def organize_memory_categories(self) -> Dict[str, Any]:
        """
        Analyze and organize existing archives by category.

        Aura can use this to understand its memory organization and get
        suggestions for improving the categorization of its knowledge.

        Returns:
            Dictionary containing categorized archives and organization suggestions
        """
        if not self.memvid_system:
            return {"status": "error", "message": "Memvid system not available"}

        try:
            archives = self.memvid_system.list_video_archives()

            # Categorize archives by type/purpose
            categories = {
                "conversations": [],
                "knowledge": [],
                "principles": [],
                "references": [],
                "templates": [],
                "books": [],
                "uncategorized": [],
            }

            # Simple categorization based on archive names and content analysis
            for archive in archives:
                name = archive["name"].lower()
                categorized = False

                for category in categories.keys():
                    if category in name or any(
                        keyword in name
                        for keyword in self._get_category_keywords(category)
                    ):
                        categories[category].append(archive)
                        categorized = True
                        break

                if not categorized:
                    categories["uncategorized"].append(archive)

            # Calculate statistics
            total_archives = len(archives)
            total_size_mb = sum(archive.get("video_size_mb", 0) for archive in archives)

            result = {
                "status": "success",
                "total_archives": total_archives,
                "total_size_mb": total_size_mb,
                "categories": {
                    category: {
                        "count": len(archives_list),
                        "archives": [
                            {
                                "name": archive["name"],
                                "size_mb": archive.get("size_mb", 0),
                                "frames": archive.get("frame_count", 0),
                            }
                            for archive in archives_list
                        ],
                        "total_size_mb": sum(
                            archive.get("size_mb", 0) for archive in archives_list
                        ),
                    }
                    for category, archives_list in categories.items()
                    if archives_list  # Only include categories with content
                },
                "organization_suggestions": self._generate_organization_suggestions(
                    categories
                ),
            }

            logger.info(
                f"📊 Organized {total_archives} archives across {len([c for c in categories.values() if c])} categories"
            )
            return result

        except Exception as e:
            logger.error("❌ Failed to organize memory categories: %s", e)
            return {"status": "error", "message": str(e)}

    def _get_category_keywords(self, category: str) -> List[str]:
        """
        Get keywords for categorizing archives.

        Args:
            category: Category name to get keywords for

        Returns:
            List of keywords associated with the category
        """
        keyword_map = {
            "conversations": ["chat", "talk", "conversation", "dialogue"],
            "knowledge": ["knowledge", "info", "data", "facts"],
            "principles": ["principles", "rules", "guidelines", "standards"],
            "references": ["reference", "manual", "guide", "documentation"],
            "templates": ["template", "prompt", "format", "pattern"],
            "books": ["book", "novel", "textbook", "publication", "literature"],
        }
        return keyword_map.get(category, [])

    def _generate_organization_suggestions(
        self, categories: Dict[str, List[Dict[str, Any]]]
    ) -> List[str]:
        """
        Generate suggestions for better memory organization.

        Args:
            categories: Dictionary of categorized archives

        Returns:
            List of suggestion strings for improving memory organization
        """
        suggestions = []

        # Check for uncategorized archives
        if categories.get("uncategorized"):
            suggestions.append(
                f"Consider categorizing {len(categories['uncategorized'])} uncategorized archives"
            )

        # Check for size imbalances
        sizes = {
            cat: sum(archive.get("size_mb", 0) for archive in archives)
            for cat, archives in categories.items()
            if archives
        }

        if sizes:
            largest_category = max(sizes, key=lambda cat: sizes[cat])
            if sizes[largest_category] > sum(sizes.values()) * 0.5:
                suggestions.append(
                    f"Consider splitting large '{largest_category}' category into subcategories"
                )

        # Check for missing common categories
        empty_categories = [cat for cat, archives in categories.items() if not archives]
        if len(empty_categories) > 3:
            suggestions.append(
                "Consider creating specialized archives for common knowledge domains"
            )

        return suggestions or ["Memory organization looks well-balanced"]


# Global instance
_aura_internal_memvid_tools: Optional[AuraInternalMemvidTools] = None


def get_aura_internal_memvid_tools(
    vector_db_client: Optional[Any] = None,
) -> AuraInternalMemvidTools:
    """
    Get or create the internal memvid tools instance.

    Args:
        vector_db_client: Optional vector database client for integration

    Returns:
        The global AuraInternalMemvidTools instance
    """
    global _aura_internal_memvid_tools
    if _aura_internal_memvid_tools is None:
        _aura_internal_memvid_tools = AuraInternalMemvidTools(vector_db_client)
    return _aura_internal_memvid_tools


def reset_aura_internal_memvid_tools() -> None:
    """
    Reset the global instance.

    Used primarily for testing or reinitialization scenarios.
    """
    global _aura_internal_memvid_tools
    _aura_internal_memvid_tools = None
