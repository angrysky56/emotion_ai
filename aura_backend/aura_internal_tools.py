"""
Aura Internal Tools Integration
===============================

This module integrates Aura's internal capabilities directly into the main API,
eliminating the need for a separate MCP server process.
"""

import logging
from typing import Any, Dict, List

# Import memvid internal tools
try:
    from aura_backend.aura_intelligent_memory_manager import (
        MemoryArchiveSpec,
        MemoryArchiveType,
        MemoryPriority,
        get_intelligent_memory_manager,
    )
    from aura_backend.aura_internal_memvid_tools import get_aura_internal_memvid_tools

    MEMVID_TOOLS_AVAILABLE = True
except ImportError:
    MEMVID_TOOLS_AVAILABLE = False
    get_aura_internal_memvid_tools = None
    get_intelligent_memory_manager = None
    MemoryArchiveSpec = None
    MemoryArchiveType = None
    MemoryPriority = None

logger = logging.getLogger(__name__)


class AuraInternalTools:
    """Direct integration of Aura's internal tool capabilities"""

    def __init__(self, vector_db, file_system):
        self.vector_db = vector_db
        self.file_system = file_system

        # Initialize memvid tools if available
        self.memvid_tools = None
        self.intelligent_memory = None
        if (
            MEMVID_TOOLS_AVAILABLE
            and get_aura_internal_memvid_tools is not None
            and get_intelligent_memory_manager is not None
        ):
            try:
                # CRITICAL FIX: Pass the shared ChromaDB client to prevent conflicts
                # The vector_db.client is already initialized and connected - reuse it
                shared_chroma_client = getattr(vector_db, "client", None)
                if shared_chroma_client is None:
                    logger.error(
                        "❌ Vector DB client not available - memvid tools disabled"
                    )
                    self.memvid_tools = None
                    self.intelligent_memory = None
                else:
                    logger.info(
                        "🔗 Using shared ChromaDB client for memvid tools (conflict prevention)"
                    )
                    self.memvid_tools = get_aura_internal_memvid_tools(
                        shared_chroma_client
                    )
                    self.intelligent_memory = get_intelligent_memory_manager(
                        shared_chroma_client
                    )
                    logger.info(
                        "✅ Memvid internal tools and intelligent memory manager initialized with shared client"
                    )
            except Exception as e:
                logger.error("❌ Failed to initialize memvid tools: %s", e)
                logger.error("❌ Error details: %s: %s", type(e).__name__, e)
                self.memvid_tools = None
                self.intelligent_memory = None

        self.tools = self._register_tools()
        logger.info("✅ Aura internal tools initialized with %s tools", len(self.tools))

        if self.memvid_tools:
            logger.info("🎥 Memvid video compression tools available for Aura")

        # Log the actual vector_db connection status
        logger.info("🔗 Internal tools connected to vector_db: %s", type(self.vector_db))
        logger.info(
            f"🔗 Vector DB has collections: conversations={hasattr(self.vector_db, 'conversations')}"
        )

    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        """Register all Aura internal tools"""
        tools = {
            "aura.search_memories": {
                "name": "aura.search_memories",
                "description": "Search through Aura's conversation memories using semantic search",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID"},
                        "query": {"type": "string", "description": "Search query"},
                        "n_results": {
                            "type": "integer",
                            "description": "Number of results",
                            "default": 5,
                        },
                    },
                    "required": ["user_id", "query"],
                },
                "handler": self.search_memories,
            },
            "aura.analyze_emotional_patterns": {
                "name": "aura.analyze_emotional_patterns",
                "description": "Analyze emotional patterns and trends over time",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID"},
                        "days": {
                            "type": "integer",
                            "description": "Number of days to analyze",
                            "default": 7,
                        },
                    },
                    "required": ["user_id"],
                },
                "handler": self.analyze_emotional_patterns,
            },
            "aura.get_user_profile": {
                "name": "aura.get_user_profile",
                "description": "Retrieve user profile information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID"}
                    },
                    "required": ["user_id"],
                },
                "handler": self.get_user_profile,
            },
            "aura.query_emotional_states": {
                "name": "aura.query_emotional_states",
                "description": "Get information about Aura's emotional state model",
                "parameters": {"type": "object", "properties": {}, "required": []},
                "handler": self.query_emotional_states,
            },
            "aura.query_aseke_framework": {
                "name": "aura.query_aseke_framework",
                "description": "Get details about Aura's ASEKE cognitive architecture",
                "parameters": {"type": "object", "properties": {}, "required": []},
                "handler": self.query_aseke_framework,
            },
        }

        # Add memvid tools if available
        if self.memvid_tools:
            memvid_tools = {
                "aura.list_video_archives": {
                    "name": "aura.list_video_archives",
                    "description": "List all video memory archives with compression statistics",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                    "handler": self.list_video_archives,
                },
                "aura.search_all_memories": {
                    "name": "aura.search_all_memories",
                    "description": "Search across ALL memory systems (active + video archives) using unified search",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "user_id": {"type": "string", "description": "User ID"},
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 10,
                            },
                        },
                        "required": ["query", "user_id"],
                    },
                    "handler": self.search_all_memories,
                },
                "aura.archive_old_conversations": {
                    "name": "aura.archive_old_conversations",
                    "description": "Archive old conversations to compressed video format for efficient storage",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "User ID (optional for all users)",
                            },
                            "codec": {
                                "type": "string",
                                "description": "Video codec (h264, h265)",
                                "default": "h264",
                            },
                        },
                        "required": [],
                    },
                    "handler": self.archive_old_conversations,
                },
                "aura.get_memory_statistics": {
                    "name": "aura.get_memory_statistics",
                    "description": "Get comprehensive memory system statistics including video compression metrics",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                    "handler": self.get_memory_statistics,
                },
                "aura.create_knowledge_summary": {
                    "name": "aura.create_knowledge_summary",
                    "description": "Create a summary of content in a specific video archive",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "archive_name": {
                                "type": "string",
                                "description": "Name of the video archive",
                            },
                            "max_entries": {
                                "type": "integer",
                                "description": "Maximum entries to include",
                                "default": 10,
                            },
                        },
                        "required": ["archive_name"],
                    },
                    "handler": self.create_knowledge_summary,
                },
            }
            tools.update(memvid_tools)
            logger.info(
                f"🎥 Added {len(memvid_tools)} memvid tools to Aura's internal toolkit"
            )

        # Add intelligent memory tools if available
        if self.intelligent_memory:
            intelligent_tools = {
                "aura.create_custom_archive": {
                    "name": "aura.create_custom_archive",
                    "description": "Create a custom memory archive on demand with specific criteria (e.g., 'Save conversations about quantum physics')",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "archive_name": {
                                "type": "string",
                                "description": "Name for the archive",
                            },
                            "archive_type": {
                                "type": "string",
                                "description": "Type: books, principles, templates, conversations, knowledge, skills, projects, emotions, research, personal",
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the archive purpose",
                            },
                            "search_query": {
                                "type": "string",
                                "description": "Query to find content for the archive",
                            },
                            "user_id": {"type": "string", "description": "User ID"},
                            "content_type": {
                                "type": "string",
                                "description": "Optional content type filter",
                                "default": "any",
                            },
                            "time_range": {
                                "type": "string",
                                "description": "Time range: today, week, month, year, all",
                                "default": "all",
                            },
                            "max_items": {
                                "type": "integer",
                                "description": "Maximum items to include",
                                "default": 50,
                            },
                            "priority": {
                                "type": "string",
                                "description": "Priority: critical, high, medium, low, disposable",
                                "default": "medium",
                            },
                        },
                        "required": [
                            "archive_name",
                            "archive_type",
                            "description",
                            "search_query",
                            "user_id",
                        ],
                    },
                    "handler": self.create_custom_archive,
                },
                "aura.suggest_archive_opportunities": {
                    "name": "aura.suggest_archive_opportunities",
                    "description": "Analyze memory patterns and suggest intelligent archiving opportunities",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"}
                        },
                        "required": ["user_id"],
                    },
                    "handler": self.suggest_archive_opportunities,
                },
                "aura.get_memory_navigation_map": {
                    "name": "aura.get_memory_navigation_map",
                    "description": "Get an intelligent navigation map showing hierarchical memory organization",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"}
                        },
                        "required": ["user_id"],
                    },
                    "handler": self.get_memory_navigation_map,
                },
                "aura.auto_organize_memory": {
                    "name": "aura.auto_organize_memory",
                    "description": "Automatically organize memory based on intelligent analysis - Aura's autonomous memory management",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"}
                        },
                        "required": ["user_id"],
                    },
                    "handler": self.auto_organize_memory,
                },
                "aura.selective_archive_conversations": {
                    "name": "aura.selective_archive_conversations",
                    "description": "Selectively archive conversations based on topic/criteria rather than just age",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"},
                            "search_criteria": {
                                "type": "string",
                                "description": "Topic or criteria to search for",
                            },
                            "archive_name": {
                                "type": "string",
                                "description": "Name for the topical archive",
                            },
                            "max_conversations": {
                                "type": "integer",
                                "description": "Maximum conversations to include",
                                "default": 50,
                            },
                        },
                        "required": ["user_id", "search_criteria", "archive_name"],
                    },
                    "handler": self.selective_archive_conversations,
                },
            }
            tools.update(intelligent_tools)
            logger.info(
                f"🧠 Added {len(intelligent_tools)} intelligent memory tools to Aura's toolkit"
            )

        return tools

    async def search_memories(
        self, user_id: str, query: str, n_results: int = 5
    ) -> Dict[str, Any]:
        """
        Search through conversation memories using semantic search.

        Args:
            user_id: The ID of the user whose memories to search
            query: The search query string
            n_results: Number of results to return (default: 5)

        Returns:
            Dict containing search results with status, query info, and memories
        """
        try:
            logger.info("🔍 Searching memories for user %s with query: %s", user_id, query)

            # Verify vector_db connection
            if not hasattr(self.vector_db, "search_conversations"):
                logger.error("❌ vector_db does not have search_conversations method")
                return {
                    "status": "error",
                    "error": "Vector database not properly initialized",
                }

            results = await self.vector_db.search_conversations(
                query=query, user_id=user_id, n_results=n_results
            )

            logger.info("✅ Found %s memories for user %s", len(results), user_id)

            return {
                "status": "success",
                "query": query,
                "user_id": user_id,
                "results_count": len(results),
                "memories": results,
            }
        except Exception as e:
            logger.error("❌ Failed to search memories: %s", e)
            logger.error("❌ vector_db type: %s", type(self.vector_db))
            logger.error("❌ vector_db attributes: %s", dir(self.vector_db))
            return {"status": "error", "error": str(e)}

    async def analyze_emotional_patterns(
        self, user_id: str, days: int = 7
    ) -> Dict[str, Any]:
        """
        Analyze emotional patterns and trends over a specified time period.

        Args:
            user_id: The ID of the user to analyze
            days: Number of days to analyze (default: 7)

        Returns:
            Dict containing emotional analysis results and statistics
        """
        try:
            logger.info(
                f"📊 Analyzing emotional patterns for user {user_id} over {days} days"
            )

            # Verify vector_db connection
            if not hasattr(self.vector_db, "analyze_emotional_trends"):
                logger.error(
                    "❌ vector_db does not have analyze_emotional_trends method"
                )
                return {
                    "status": "error",
                    "error": "Vector database not properly initialized",
                }

            analysis = await self.vector_db.analyze_emotional_trends(user_id, days)

            logger.info("✅ Generated emotional analysis for user %s", user_id)

            return {
                "status": "success",
                "user_id": user_id,
                "analysis_period_days": days,
                "emotional_analysis": analysis,
            }
        except Exception as e:
            logger.error("❌ Failed to analyze emotional patterns: %s", e)
            return {"status": "error", "error": str(e)}

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieve user profile information from the file system.

        Args:
            user_id: The ID of the user whose profile to retrieve

        Returns:
            Dict containing user profile data or error/not found status
        """
        try:
            logger.info("👤 Loading user profile for %s", user_id)

            # Verify file_system connection
            if not hasattr(self.file_system, "load_user_profile"):
                logger.error("❌ file_system does not have load_user_profile method")
                return {
                    "status": "error",
                    "error": "File system not properly initialized",
                }

            profile = await self.file_system.load_user_profile(user_id)

            if profile is None:
                logger.info("👤 No profile found for user %s", user_id)
                return {
                    "status": "not_found",
                    "user_id": user_id,
                    "message": "User profile not found",
                }

            logger.info("✅ Loaded profile for user %s", user_id)
            return {"status": "success", "user_id": user_id, "profile": profile}
        except Exception as e:
            logger.error("❌ Failed to get user profile: %s", e)
            return {"status": "error", "error": str(e)}

    async def query_emotional_states(self) -> Dict[str, Any]:
        """
        Get information about Aura's emotional state model and capabilities.

        Returns:
            Dict containing detailed information about the emotional system
        """
        return {
            "status": "success",
            "emotional_system": {
                "total_emotions": "22+",
                "categories": [
                    "Basic emotions (Normal, Happy, Sad, Angry, Excited, Fear, Disgust, Surprise)",
                    "Complex emotions (Joy, Love, Peace, Creativity, DeepMeditation, Friendliness, Curiosity)",
                    "Combined emotions (Hope, Optimism, Awe, Remorse)",
                    "Social emotions (RomanticLove, PlatonicLove, ParentalLove)",
                ],
                "features": [
                    "Neurological correlations (Brainwaves, Neurotransmitters)",
                    "Mathematical formulas for emotional states",
                    "Intensity levels (Low, Medium, High)",
                    "Emotional component tracking",
                    "NTK (Neural Tensor Kernel) layer mapping",
                ],
            },
        }

    async def query_aseke_framework(self) -> Dict[str, Any]:
        """
        Get information about Aura's ASEKE cognitive architecture framework.

        Returns:
            Dict containing detailed information about the ASEKE framework components
        """
        return {
            "status": "success",
            "aseke_framework": {
                "framework_name": "ASEKE - Adaptive Socio-Emotional Knowledge Ecosystem",
                "components": {
                    "KS": "Knowledge Substrate - shared context and history",
                    "CE": "Cognitive Energy - focus and mental effort",
                    "IS": "Information Structures - ideas and concepts",
                    "KI": "Knowledge Integration - connecting understanding",
                    "KP": "Knowledge Propagation - sharing ideas",
                    "ESA": "Emotional State Algorithms - emotional influence",
                    "SDA": "Sociobiological Drives - social dynamics",
                },
            },
        }

    def get_tool_list(self) -> List[Dict[str, Any]]:
        """
        Get a list of all available internal tools with their metadata.

        Returns:
            List of dicts containing tool names, descriptions, and parameters
        """
        return [
            {
                "name": name,
                "description": tool["description"],
                "server": "aura-internal",
                "parameters": tool["parameters"],
            }
            for name, tool in self.tools.items()
        ]

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get tool definitions for the MCP bridge integration.

        Returns:
            Dict mapping tool names to their descriptions and parameters
        """
        definitions = {}
        for name, tool in self.tools.items():
            definitions[name] = {
                "description": tool["description"],
                "parameters": tool["parameters"],
            }
        return definitions

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute an internal tool by name with the provided arguments.

        Args:
            tool_name: Name of the tool to execute (with or without 'aura.' prefix)
            arguments: Dict of arguments to pass to the tool

        Returns:
            Result from the tool execution

        Raises:
            ValueError: If the tool is not found
        """
        logger.info("🔧 Executing internal tool: %s with args: %s", tool_name, arguments)

        # Normalize tool name
        if not tool_name.startswith("aura."):
            tool_name = f"aura.{tool_name}"

        if tool_name not in self.tools:
            available_tools = list(self.tools.keys())
            logger.error(
                f"❌ Tool {tool_name} not found. Available tools: {available_tools}"
            )
            raise ValueError(
                f"Tool {tool_name} not found. Available tools: {available_tools}"
            )

        try:
            handler = self.tools[tool_name]["handler"]
            result = await handler(**arguments)
            logger.info("✅ Tool %s executed successfully", tool_name)
            return result
        except Exception as e:
            logger.error("❌ Tool %s execution failed: %s", tool_name, e)
            raise

    # ============================================================================
    # Memvid Tool Handlers
    # ============================================================================

    async def list_video_archives(self) -> Dict[str, Any]:
        """
        List all video memory archives with compression statistics.

        Returns:
            Dict containing list of video archives and their metadata
        """
        if not self.memvid_tools:
            return {"status": "error", "message": "Memvid tools not available"}

        return await self.memvid_tools.list_video_archives()

    async def search_all_memories(
        self, query: str, user_id: str, max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search across ALL memory systems (active + video archives) using unified search.

        Args:
            query: The search query string
            user_id: The ID of the user whose memories to search
            max_results: Maximum number of results to return (default: 10)

        Returns:
            Dict containing unified search results from all memory systems
        """
        if not self.memvid_tools:
            return {"status": "error", "message": "Memvid tools not available"}

        return await self.memvid_tools.search_all_memories(query, user_id, max_results)

    async def archive_old_conversations(
        self, user_id: str | None = None, codec: str = "h264"
    ) -> Dict[str, Any]:
        """
        Archive old conversations to compressed video format for efficient storage.

        Args:
            user_id: The ID of the user whose conversations to archive (None for all users)
            codec: Video codec to use for compression ('h264' or 'h265', default: 'h264')

        Returns:
            Dict containing archival results and compression statistics
        """
        if not self.memvid_tools:
            return {"status": "error", "message": "Memvid tools not available"}

        return await self.memvid_tools.archive_old_conversations(user_id, codec)

    async def get_memory_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive memory system statistics including video compression metrics.

        Returns:
            Dict containing detailed statistics about all memory systems
        """
        if not self.memvid_tools:
            return {"status": "error", "message": "Memvid tools not available"}

        return await self.memvid_tools.get_memory_statistics()

    async def create_knowledge_summary(
        self, archive_name: str, max_entries: int = 10
    ) -> Dict[str, Any]:
        """
        Create a summary of content in a specific video archive.

        Args:
            archive_name: Name of the video archive to summarize
            max_entries: Maximum number of entries to include in summary (default: 10)

        Returns:
            Dict containing the knowledge summary and archive metadata
        """
        if not self.memvid_tools:
            return {"status": "error", "message": "Memvid tools not available"}

        return await self.memvid_tools.create_knowledge_summary(
            archive_name, max_entries
        )

    # ============================================================================
    # Intelligent Memory Tool Handlers
    # ============================================================================

    async def create_custom_archive(
        self,
        archive_name: str,
        archive_type: str,
        description: str,
        search_query: str,
        user_id: str,
        content_type: str = "any",
        time_range: str = "all",
        max_items: int = 50,
        priority: str = "medium",
    ) -> Dict[str, Any]:
        """
        Create a custom memory archive on demand with specific criteria.

        Args:
            archive_name: Name for the new archive
            archive_type: Type of archive (books, principles, templates, etc.)
            description: Description of the archive purpose
            search_query: Query to find content for the archive
            user_id: The ID of the user creating the archive
            content_type: Optional content type filter (default: "any")
            time_range: Time range to search (today, week, month, year, all; default: "all")
            max_items: Maximum items to include (default: 50)
            priority: Archive priority level (critical, high, medium, low, disposable; default: "medium")

        Returns:
            Dict containing the result of archive creation
        """
        if not self.intelligent_memory:
            return {
                "status": "error",
                "message": "Intelligent memory manager not available",
            }

        if not (MemoryArchiveSpec and MemoryArchiveType and MemoryPriority):
            return {
                "status": "error",
                "message": "Memory archive classes not available",
            }

        try:
            # Create archive specification
            archive_spec = MemoryArchiveSpec(
                name=archive_name,
                archive_type=MemoryArchiveType(archive_type),
                description=description,
                content_criteria={
                    "query": search_query,
                    "content_type": content_type,
                    "time_range": time_range,
                    "max_results": max_items,
                },
                priority=MemoryPriority(priority),
                auto_update=False,
            )

            result = await self.intelligent_memory.create_custom_archive(
                archive_spec=archive_spec, user_id=user_id, execute_immediately=True
            )

            return result

        except Exception as e:
            logger.error("Failed to create custom archive: %s", e)
            return {"status": "error", "message": str(e)}

    async def suggest_archive_opportunities(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze memory patterns and suggest intelligent archiving opportunities.

        Args:
            user_id: The ID of the user to analyze for archive opportunities

        Returns:
            Dict containing suggested archive opportunities and analysis
        """
        if not self.intelligent_memory:
            return {
                "status": "error",
                "message": "Intelligent memory manager not available",
            }

        try:
            suggestions = await self.intelligent_memory.suggest_archive_opportunities(
                user_id
            )

            return {
                "status": "success",
                "user_id": user_id,
                "suggestions_count": len(suggestions),
                "suggestions": suggestions,
            }

        except Exception as e:
            logger.error("Failed to suggest archive opportunities: %s", e)
            return {"status": "error", "message": str(e)}

    async def get_memory_navigation_map(self, user_id: str) -> Dict[str, Any]:
        """
        Get an intelligent navigation map showing hierarchical memory organization.

        Args:
            user_id: The ID of the user whose memory map to retrieve

        Returns:
            Dict containing the hierarchical memory navigation structure
        """
        if not self.intelligent_memory:
            return {
                "status": "error",
                "message": "Intelligent memory manager not available",
            }

        return await self.intelligent_memory.get_memory_navigation_map(user_id)

    async def auto_organize_memory(self, user_id: str) -> Dict[str, Any]:
        """
        Automatically organize memory based on intelligent analysis - Aura's autonomous memory management.

        Args:
            user_id: The ID of the user whose memory to organize

        Returns:
            Dict containing the results of automatic memory organization
        """
        if not self.intelligent_memory:
            return {
                "status": "error",
                "message": "Intelligent memory manager not available",
            }

        return await self.intelligent_memory.auto_organize_memory(user_id)

    async def selective_archive_conversations(
        self,
        user_id: str,
        search_criteria: str,
        archive_name: str,
        max_conversations: int = 50,
    ) -> Dict[str, Any]:
        """
        Selectively archive conversations based on topic/criteria rather than just age.

        Args:
            user_id: The ID of the user whose conversations to archive
            search_criteria: Topic or criteria to search for when selecting conversations
            archive_name: Name for the topical archive
            max_conversations: Maximum number of conversations to include (default: 50)

        Returns:
            Dict containing the results of selective conversation archiving
        """
        if not self.memvid_tools:
            return {"status": "error", "message": "Memvid tools not available"}

        return await self.memvid_tools.selective_archive_conversations(
            user_id=user_id,
            search_criteria=search_criteria,
            archive_name=archive_name,
            max_conversations=max_conversations,
        )
