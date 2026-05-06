"""
Aura Intelligent Memory Manager
==============================

Enhanced memvid integration providing sophisticated memory management capabilities:
1. Custom memvid archives on demand ("Save this conversation about quantum physics")
2. Organized knowledge libraries (Books MP4, Principles MP4, Templates MP4)
3. Selective archiving based on content criteria rather than age
4. Hierarchical memory organization with intelligent routing

This builds on the existing aura_real_memvid.py foundation to add intelligence.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import existing memvid integration
try:
    try:
        from aura_backend.aura_internal_memvid_tools import (
            get_aura_internal_memvid_tools,
        )
        from aura_backend.aura_real_memvid import (
            REAL_MEMVID_AVAILABLE,
            get_aura_real_memvid,
        )
    except ImportError:
        from aura_internal_memvid_tools import get_aura_internal_memvid_tools
        from aura_real_memvid import REAL_MEMVID_AVAILABLE, get_aura_real_memvid
except ImportError:
    REAL_MEMVID_AVAILABLE = False
    get_aura_real_memvid = None
    get_aura_internal_memvid_tools = None

logger = logging.getLogger(__name__)


class MemoryArchiveType(str, Enum):
    """Types of memory archives for intelligent organization"""

    BOOKS = "books"
    PRINCIPLES = "principles"
    TEMPLATES = "templates"
    CONVERSATIONS = "conversations"
    KNOWLEDGE = "knowledge"
    SKILLS = "skills"
    PROJECTS = "projects"
    EMOTIONS = "emotions"
    RESEARCH = "research"
    PERSONAL = "personal"


class MemoryPriority(str, Enum):
    """Priority levels for memory importance"""

    CRITICAL = "critical"  # Must never be lost
    HIGH = "high"  # Very important
    MEDIUM = "medium"  # Standard importance
    LOW = "low"  # Can be compressed/summarized
    DISPOSABLE = "disposable"  # Can be deleted if needed


@dataclass
class MemoryArchiveSpec:
    """
    Specification for creating a custom memory archive.

    Attributes:
        name: Human-readable name for the archive
        archive_type: Type of archive from MemoryArchiveType enum
        description: Detailed description of archive purpose
        content_criteria: Search/filter criteria for selecting content
        priority: Priority level for memory retention
        auto_update: Whether to automatically add new matching content
        retention_days: Days to keep in active memory after archiving
        tags: List of tags for categorization and search
    """

    name: str
    archive_type: MemoryArchiveType
    description: str
    content_criteria: Dict[str, Any]  # Search/filter criteria
    priority: MemoryPriority = MemoryPriority.MEDIUM
    auto_update: bool = False  # Whether to automatically add new matching content
    retention_days: Optional[int] = (
        None  # How long to keep in active memory after archiving
    )
    tags: List[str] = field(default_factory=list)

    # Note: __post_init__ removed - default_factory=list ensures tags is never None


@dataclass
class MemoryInsight:
    """
    Insights about memory patterns and usage.

    Attributes:
        category: Category of insight (e.g., 'performance', 'organization')
        insight_type: Type of insight (pattern, recommendation, alert, statistic)
        title: Brief title describing the insight
        description: Detailed description of the insight
        confidence: Confidence level from 0-1
        actionable: Whether the insight has actionable recommendations
        suggested_actions: List of suggested actions to take
    """

    category: str
    insight_type: str  # pattern, recommendation, alert, statistic
    title: str
    description: str
    confidence: float  # 0-1
    actionable: bool
    suggested_actions: List[str] = field(default_factory=list)

    # Note: __post_init__ removed - default_factory=list ensures suggested_actions is never None


class AuraIntelligentMemoryManager:
    """
    Intelligent Memory Management System for Aura

    Provides sophisticated memory organization beyond simple age-based archiving:
    - Content-aware categorization
    - Demand-based archive creation
    - Intelligent memory routing
    - Hierarchical organization
    """

    def __init__(self, vector_db_client: Optional[Any] = None) -> None:
        """
        Initialize the Intelligent Memory Manager.

        Args:
            vector_db_client: Optional existing vector database client for integration
        """
        self.vector_db_client = vector_db_client

        # Initialize the underlying memvid systems
        if (
            REAL_MEMVID_AVAILABLE
            and get_aura_real_memvid is not None
            and get_aura_internal_memvid_tools is not None
        ):
            try:
                self.memvid_system = get_aura_real_memvid(
                    existing_chroma_client=vector_db_client
                )
                self.internal_tools = get_aura_internal_memvid_tools(vector_db_client)
                logger.info(
                    "✅ Intelligent memory manager initialized with real memvid"
                )
            except Exception as e:
                logger.error("❌ Failed to initialize memvid systems: %s", e)
                self.memvid_system = None
                self.internal_tools = None
        else:
            logger.warning("⚠️ Real memvid not available - intelligent memory disabled")
            self.memvid_system = None
            self.internal_tools = None

        # Memory organization configuration
        self.archive_config_path = Path("./memvid_data/archive_configs.json")
        self.memory_insights_path = Path("./memvid_data/memory_insights.json")

        # Ensure data directory exists
        self.archive_config_path.parent.mkdir(exist_ok=True)

        # Load existing configurations
        self.archive_specs = self._load_archive_specs()
        self.memory_hierarchies = self._initialize_memory_hierarchies()

    @property
    def is_available(self) -> bool:
        """
        Check if the memory system is available and operational.

        Returns:
            True if both memvid system and internal tools are available
        """
        return self.memvid_system is not None and self.internal_tools is not None

    def _require_memory_system(self, operation_name: str) -> None:
        """
        Raise a descriptive error if memory system is not available.

        Args:
            operation_name: Name of the operation requiring memory system

        Raises:
            ValueError: If memory system is not available
        """
        if not self.is_available:
            raise ValueError(
                f"Cannot perform {operation_name}: Memory system not available. "
                "Ensure memvid integration is properly configured."
            )

    def _load_archive_specs(self) -> Dict[str, MemoryArchiveSpec]:
        """
        Load existing archive specifications from disk.

        Returns:
            Dictionary mapping archive names to their specifications
        """
        try:
            if self.archive_config_path.exists():
                with open(self.archive_config_path, "r") as f:
                    data = json.load(f)
                    return {
                        name: MemoryArchiveSpec(**spec) for name, spec in data.items()
                    }
        except Exception as e:
            logger.error("Failed to load archive specs: %s", e)

        return {}

    def _save_archive_specs(self) -> None:
        """
        Save archive specifications to disk.

        Saves the current archive specifications to the configured JSON file.
        """
        try:
            data = {name: asdict(spec) for name, spec in self.archive_specs.items()}
            with open(self.archive_config_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to save archive specs: %s", e)

    def _initialize_memory_hierarchies(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Initialize hierarchical memory organization structures.

        Returns:
            Dictionary containing organized memory hierarchy structures
        """
        return {
            "knowledge_domains": {
                "science": ["physics", "chemistry", "biology", "mathematics"],
                "technology": ["programming", "ai", "web_development", "systems"],
                "arts": ["literature", "music", "visual_arts", "writing"],
                "personal": ["goals", "relationships", "experiences", "reflections"],
                "professional": ["skills", "projects", "networking", "career"],
            },
            "content_types": {
                "factual": ["definitions", "explanations", "data", "references"],
                "procedural": ["instructions", "tutorials", "processes", "methods"],
                "creative": ["ideas", "brainstorming", "inspiration", "concepts"],
                "emotional": ["feelings", "support", "therapy", "personal_growth"],
                "social": ["conversations", "relationships", "communication"],
            },
            "importance_signals": {
                "high_value": ["bookmark", "save", "important", "remember", "critical"],
                "reference": ["definition", "how to", "tutorial", "guide", "manual"],
                "temporal": ["deadline", "urgent", "schedule", "appointment"],
                "personal": ["goal", "dream", "fear", "hope", "love"],
            },
        }

    async def create_custom_archive(
        self,
        archive_spec: MemoryArchiveSpec,
        user_id: str,
        execute_immediately: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a custom memory archive based on sophisticated criteria.

        Args:
            archive_spec: Specification for the archive to create
            user_id: User identifier for memory search
            execute_immediately: Whether to create the archive now or just save the spec

        Returns:
            Dictionary containing creation status and results
        """
        try:
            self._require_memory_system("custom archive creation")

            # Save the archive specification
            self.archive_specs[archive_spec.name] = archive_spec
            self._save_archive_specs()

            result = {
                "status": "success",
                "archive_name": archive_spec.name,
                "archive_type": archive_spec.archive_type.value,
                "specification_saved": True,
                "executed": False,
            }

            if execute_immediately:
                # Execute the archive creation
                execution_result = await self._execute_archive_creation(
                    archive_spec, user_id
                )
                result.update(execution_result)
                result["executed"] = execution_result.get("status") == "success"

            logger.info(
                "📚 Created custom archive specification: %s", archive_spec.name
            )
            return result

        except ValueError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error("❌ Failed to create custom archive: %s", e)
            return {"status": "error", "message": str(e)}

    async def _execute_archive_creation(
        self, archive_spec: MemoryArchiveSpec, user_id: str
    ) -> Dict[str, Any]:
        """
        Execute the actual creation of a memory archive.

        Args:
            archive_spec: Specification for the archive to create
            user_id: User identifier for content search

        Returns:
            Dictionary containing execution results and status
        """
        try:
            # Step 1: Search for content matching the criteria
            matching_content = await self._find_matching_content(
                archive_spec.content_criteria, user_id
            )

            if not matching_content:
                return {
                    "status": "warning",
                    "message": f"No content found matching criteria for '{archive_spec.name}'",
                }

            # Step 2: Prepare content for archiving based on type
            if self.internal_tools is None:
                return {
                    "status": "error",
                    "message": "Memory internal tools not initialized or available",
                }

            if archive_spec.archive_type == MemoryArchiveType.CONVERSATIONS:
                # Use selective conversation archiving
                result = await self.internal_tools.selective_archive_conversations(
                    user_id=user_id,
                    search_criteria=archive_spec.content_criteria.get("query", ""),
                    archive_name=archive_spec.name,
                    max_conversations=archive_spec.content_criteria.get(
                        "max_items", 50
                    ),
                )
            else:
                # Create knowledge library
                knowledge_sources = [
                    {
                        "content": content["content"],
                        "source_type": archive_spec.archive_type.value,
                        "name": content.get("metadata", {}).get("timestamp", "Unknown"),
                    }
                    for content in matching_content
                ]

                result = await self.internal_tools.create_knowledge_library(
                    library_name=archive_spec.name,
                    knowledge_sources=knowledge_sources,
                    library_type=archive_spec.archive_type.value,
                )

            # Step 3: Update archive with metadata
            if result.get("status") == "success":
                await self._add_archive_metadata(
                    archive_spec.name, archive_spec, result
                )

            return result

        except Exception as e:
            logger.error("❌ Failed to execute archive creation: %s", e)
            return {"status": "error", "message": str(e)}

    async def _find_matching_content(
        self, criteria: Dict[str, Any], user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Find content matching sophisticated search criteria.

        Args:
            criteria: Dictionary of search and filter criteria
            user_id: User identifier for content search

        Returns:
            List of content items matching the criteria
        """
        try:
            # Note: internal_tools availability already verified by caller
            if self.internal_tools is None:
                return []

            # Extract search parameters with clear defaults
            search_params = {
                "query": criteria.get("query", ""),
                "content_type": criteria.get("content_type", "any"),
                "time_range": criteria.get("time_range", "all"),
                "emotional_state": criteria.get("emotional_state", "any"),
                "sender": criteria.get("sender", "any"),
                "max_results": criteria.get("max_results", 100),
            }

            # Perform unified search across all memory systems
            search_result = await self.internal_tools.search_all_memories(
                query=search_params["query"],
                user_id=user_id,
                max_results=search_params["max_results"],
            )

            # Filter and transform results
            all_results = search_result.get("all_results", [])
            matching_content = []

            for result in all_results:
                metadata = result.get("metadata", {})

                # Apply content filters
                if not self._matches_content_filters(metadata, search_params):
                    continue

                # Transform to standardized format
                content_item = {
                    "content": result.get("content", ""),
                    "metadata": metadata,
                    "source": result.get("source", "unknown"),
                    "relevance_score": result.get("score", 0),
                }

                matching_content.append(content_item)

            # Sort by relevance score
            matching_content.sort(key=lambda x: x["relevance_score"], reverse=True)

            logger.info("🔍 Found %s items matching criteria", len(matching_content))
            return matching_content

        except Exception as e:
            logger.error("❌ Failed to find matching content: %s", e)
            return []

    def _matches_content_filters(
        self, metadata: Dict[str, Any], search_params: Dict[str, Any]
    ) -> bool:
        """
        Check if content matches the specified filters.

        Args:
            metadata: Content metadata to check
            search_params: Filter parameters to apply

        Returns:
            True if content matches all specified filters
        """
        # Sender filter
        if (
            search_params["sender"] != "any"
            and metadata.get("sender") != search_params["sender"]
        ):
            return False

        # Emotional state filter
        if (
            search_params["emotional_state"] != "any"
            and metadata.get("emotion_name", "").lower()
            != search_params["emotional_state"].lower()
        ):
            return False

        # Time range filter
        if search_params["time_range"] != "all":
            timestamp_str = metadata.get("timestamp", "")
            if timestamp_str and not self._matches_time_range(
                timestamp_str, search_params["time_range"]
            ):
                return False

        return True

    def _matches_time_range(self, timestamp_str: str, time_range: str) -> bool:
        """
        Check if timestamp matches specified time range.

        Args:
            timestamp_str: ISO format timestamp string
            time_range: Time range specification ('today', 'week', 'month', 'year')

        Returns:
            True if timestamp falls within the specified range
        """
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            now = datetime.now()

            if time_range == "today":
                return timestamp.date() == now.date()
            elif time_range == "week":
                return timestamp >= now - timedelta(days=7)
            elif time_range == "month":
                return timestamp >= now - timedelta(days=30)
            elif time_range == "year":
                return timestamp >= now - timedelta(days=365)

            return True  # Default to include if unknown range

        except Exception:
            return True  # Include if timestamp parsing fails

    async def _add_archive_metadata(
        self,
        archive_name: str,
        archive_spec: MemoryArchiveSpec,
        creation_result: Dict[str, Any],
    ) -> None:
        """
        Add intelligent metadata to a newly created archive.

        Args:
            archive_name: Name of the created archive
            archive_spec: Original specification used for creation
            creation_result: Results from the archive creation process
        """
        try:
            metadata = {
                "created_at": datetime.now().isoformat(),
                "archive_type": archive_spec.archive_type.value,
                "priority": archive_spec.priority.value,
                "description": archive_spec.description,
                "tags": archive_spec.tags,
                "auto_update": archive_spec.auto_update,
                "retention_days": archive_spec.retention_days,
                "content_criteria": archive_spec.content_criteria,
                "creation_stats": creation_result,
            }

            # Save metadata file
            metadata_path = Path(f"./memvid_data/{archive_name}_metadata.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)

            logger.info("📝 Added metadata for archive: %s", archive_name)

        except Exception as e:
            logger.error("Failed to add archive metadata: %s", e)

    async def suggest_archive_opportunities(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Analyze memory patterns and suggest intelligent archiving opportunities.

        Args:
            user_id: User identifier for memory analysis

        Returns:
            List of suggested archive opportunities with relevance scores
        """
        try:
            self._require_memory_system("archive opportunity analysis")
            if self.internal_tools is None:
                return []

            # Gather suggestions from different analysis approaches
            suggestion_generators = [
                self._suggest_topical_archives(user_id),
                self._suggest_emotional_archives(user_id),
                self._suggest_knowledge_archives(user_id),
            ]

            # Collect all suggestions concurrently
            all_suggestions = []
            for suggestions in await asyncio.gather(
                *suggestion_generators, return_exceptions=True
            ):
                if isinstance(suggestions, Exception):
                    logger.warning("Suggestion generator failed: %s", suggestions)
                    continue
                # Type check to ensure suggestions is a list before extending
                if isinstance(suggestions, list):
                    all_suggestions.extend(suggestions)

            # Sort by relevance and return top suggestions
            all_suggestions.sort(
                key=lambda x: x.get("relevance_score", 0), reverse=True
            )

            logger.info(
                f"💡 Generated {len(all_suggestions)} archive suggestions for {user_id}"
            )
            return all_suggestions[:10]  # Return top 10 suggestions

        except ValueError as e:
            logger.warning("Archive opportunities unavailable: %s", e)
            return []
        except Exception as e:
            logger.error("❌ Failed to suggest archive opportunities: %s", e)
            return []

    async def _suggest_topical_archives(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Suggest archives based on conversation topics.

        Args:
            user_id: User identifier for topic analysis

        Returns:
            List of topical archive suggestions
        """
        # Note: Memory system availability verified by caller
        if self.internal_tools is None:
            return []

        # Define topic clusters for intelligent categorization
        topic_clusters = {
            "technology": [
                "programming",
                "coding",
                "development",
                "python",
                "javascript",
            ],
            "ai_ml": ["ai", "machine learning", "artificial intelligence"],
            "professional": ["work", "project", "business", "career"],
            "wellness": ["health", "fitness", "exercise", "wellness"],
            "travel": ["travel", "vacation", "trip", "adventure"],
            "learning": ["learning", "education", "study", "course"],
            "social": ["relationships", "family", "friends", "social"],
        }

        suggestions = []

        try:
            for cluster_name, topics in topic_clusters.items():
                # Search across all topics in the cluster
                cluster_query = " OR ".join(topics)

                search_result = await self.internal_tools.search_all_memories(
                    query=cluster_query, user_id=user_id, max_results=20
                )

                total_results = search_result.get("total_results", 0)

                if total_results >= 5:  # Sufficient content threshold
                    suggestions.append(
                        self._create_topical_suggestion(
                            cluster_name, topics, total_results
                        )
                    )

        except Exception as e:
            logger.error("Failed to suggest topical archives: %s", e)

        return suggestions

    def _create_topical_suggestion(
        self, cluster_name: str, topics: List[str], result_count: int
    ) -> Dict[str, Any]:
        """
        Create a standardized topical archive suggestion.

        Args:
            cluster_name: Name of the topic cluster
            topics: List of topic keywords
            result_count: Number of matching items found

        Returns:
            Formatted suggestion dictionary
        """
        return {
            "type": "topical_archive",
            "suggested_name": f"{cluster_name.title()}_Knowledge",
            "archive_type": MemoryArchiveType.CONVERSATIONS.value,
            "description": f"Archive conversations about {cluster_name.replace('_', ' ')}",
            "content_criteria": {
                "query": " OR ".join(topics),
                "content_type": "conversation",
                "max_results": 50,
            },
            "estimated_items": result_count,
            "relevance_score": min(result_count / 10, 1.0),
            "reasoning": f"Found {result_count} conversations in {cluster_name} domain",
        }

    async def _suggest_emotional_archives(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Suggest archives based on emotional patterns.

        Args:
            user_id: User identifier for emotional pattern analysis

        Returns:
            List of emotional archive suggestions
        """
        # Note: Memory system availability verified by caller
        if self.internal_tools is None:
            return []

        # Define emotional patterns for journey archiving
        emotional_patterns = ["happy", "excited", "creative", "peaceful", "curious"]

        suggestions = []

        try:
            for emotion in emotional_patterns:
                search_result = await self.internal_tools.search_all_memories(
                    query=f"emotional state {emotion}", user_id=user_id, max_results=15
                )

                result_count = search_result.get("total_results", 0)

                if result_count >= 3:  # Minimum threshold for emotional archive
                    suggestions.append(
                        self._create_emotional_suggestion(emotion, result_count)
                    )

        except Exception as e:
            logger.error("Failed to suggest emotional archives: %s", e)

        return suggestions

    async def _suggest_knowledge_archives(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Suggest knowledge domain archives.

        Args:
            user_id: User identifier for knowledge domain analysis

        Returns:
            List of knowledge archive suggestions
        """
        # Note: Memory system availability verified by caller
        if self.internal_tools is None:
            return []

        # Define knowledge domain clusters
        knowledge_domains = {
            "Science_Technology": ["science", "technology", "research", "innovation"],
            "Personal_Development": ["learning", "growth", "skill", "improvement"],
            "Creative_Projects": ["creative", "art", "design", "writing", "music"],
            "Problem_Solving": ["problem", "solution", "debugging", "troubleshooting"],
        }

        suggestions = []

        try:
            for domain_name, keywords in knowledge_domains.items():
                combined_query = " OR ".join(keywords)

                search_result = await self.internal_tools.search_all_memories(
                    query=combined_query, user_id=user_id, max_results=25
                )

                total_items = search_result.get("total_results", 0)

                if total_items >= 4:  # Sufficient content threshold
                    suggestions.append(
                        self._create_knowledge_suggestion(
                            domain_name, combined_query, total_items
                        )
                    )

        except Exception as e:
            logger.error("Failed to suggest knowledge archives: %s", e)

        return suggestions

    def _create_emotional_suggestion(
        self, emotion: str, result_count: int
    ) -> Dict[str, Any]:
        """
        Create a standardized emotional archive suggestion.

        Args:
            emotion: Emotion type for the archive
            result_count: Number of matching emotional moments

        Returns:
            Formatted emotional suggestion dictionary
        """
        return {
            "type": "emotional_archive",
            "suggested_name": f"{emotion.title()}_Moments",
            "archive_type": MemoryArchiveType.EMOTIONS.value,
            "description": f"Archive moments of {emotion} emotional states",
            "content_criteria": {
                "query": emotion,
                "emotional_state": emotion,
                "max_results": 30,
            },
            "estimated_items": result_count,
            "relevance_score": min(result_count / 8, 1.0),
            "reasoning": f"Found {result_count} moments with {emotion} emotional state",
        }

    def _create_knowledge_suggestion(
        self, domain_name: str, query: str, total_items: int
    ) -> Dict[str, Any]:
        """
        Create a standardized knowledge archive suggestion.

        Args:
            domain_name: Name of the knowledge domain
            query: Search query used to find items
            total_items: Total number of items found

        Returns:
            Formatted knowledge suggestion dictionary
        """
        return {
            "type": "knowledge_archive",
            "suggested_name": domain_name,
            "archive_type": MemoryArchiveType.KNOWLEDGE.value,
            "description": f"Knowledge archive for {domain_name.replace('_', ' ').lower()}",
            "content_criteria": {
                "query": query,
                "content_type": "knowledge",
                "max_results": 40,
            },
            "estimated_items": total_items,
            "relevance_score": min(total_items / 12, 1.0),
            "reasoning": f"Knowledge cluster identified in {domain_name.replace('_', ' ').lower()}",
        }

    async def get_memory_navigation_map(self, user_id: str) -> Dict[str, Any]:
        """
        Create an intelligent navigation map of all memory archives.
        Shows hierarchical organization and relationships.

        Args:
            user_id: User identifier for personalized navigation

        Returns:
            Dictionary containing the complete navigation map structure
        """
        try:
            self._require_memory_system("memory navigation map generation")
            if self.internal_tools is None:
                return {
                    "status": "error",
                    "message": "Memory internal tools not available",
                }

            # Gather navigation data concurrently where possible
            archives_task = self.internal_tools.list_video_archives()
            organization_task = self.internal_tools.organize_memory_categories()

            archives, organization = await asyncio.gather(
                archives_task, organization_task
            )

            # Build comprehensive navigation structure
            navigation_map = await self._build_navigation_structure(
                archives, organization, user_id
            )

            logger.info("🗺️ Generated memory navigation map for %s", user_id)
            return {"status": "success", "navigation_map": navigation_map}

        except ValueError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error("❌ Failed to create memory navigation map: %s", e)
            return {"status": "error", "message": str(e)}

    async def _build_navigation_structure(
        self, archives: Dict[str, Any], organization: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        """
        Build the complete navigation structure with all components.

        Args:
            archives: Archive information from the system
            organization: Organization data for categorization
            user_id: User identifier for personalization

        Returns:
            Complete navigation structure dictionary
        """
        categories = organization.get("categories", {})

        # Gather additional navigation components
        quick_access_task = self._identify_quick_access_archives(user_id)
        recommendations_task = self._generate_navigation_recommendations(user_id)

        quick_access, recommendations = await asyncio.gather(
            quick_access_task, recommendations_task, return_exceptions=True
        )

        # Handle potential errors in parallel tasks
        if isinstance(quick_access, Exception):
            logger.warning("Quick access generation failed: %s", quick_access)
            quick_access = []
        if isinstance(recommendations, Exception):
            logger.warning("Recommendations generation failed: %s", recommendations)
            recommendations = []

        return {
            "total_archives": archives.get("total_archives", 0),
            "total_size_mb": archives.get("total_size_mb", 0),
            "categories": categories,
            "archive_hierarchy": self._build_archive_hierarchy(categories),
            "quick_access": quick_access,
            "recommendations": recommendations,
            "search_hints": self._generate_search_hints(),
            "last_updated": datetime.now().isoformat(),
        }

    def _build_archive_hierarchy(self, categories: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a hierarchical view of archives.

        Args:
            categories: Category information for archive organization

        Returns:
            Hierarchical structure of archive categories
        """
        hierarchy = {
            "knowledge_bases": {
                "description": "Organized knowledge and reference materials",
                "categories": [],
            },
            "conversation_archives": {
                "description": "Archived conversations by topic and time",
                "categories": [],
            },
            "specialized_libraries": {
                "description": "Domain-specific knowledge collections",
                "categories": [],
            },
        }

        # Categorize archives into hierarchy
        for category, data in categories.items():
            if category in ["books", "knowledge", "references"]:
                hierarchy["knowledge_bases"]["categories"].append(
                    {
                        "name": category,
                        "count": data["count"],
                        "size_mb": data["total_size_mb"],
                        "archives": data["archives"],
                    }
                )
            elif category in ["conversations"]:
                hierarchy["conversation_archives"]["categories"].append(
                    {
                        "name": category,
                        "count": data["count"],
                        "size_mb": data["total_size_mb"],
                        "archives": data["archives"],
                    }
                )
            else:
                hierarchy["specialized_libraries"]["categories"].append(
                    {
                        "name": category,
                        "count": data["count"],
                        "size_mb": data["total_size_mb"],
                        "archives": data["archives"],
                    }
                )

        return hierarchy

    async def _identify_quick_access_archives(
        self, user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Identify frequently accessed or important archives for quick access.

        Args:
            user_id: User identifier for access pattern analysis

        Returns:
            List of quick access archive recommendations
        """
        try:
            if not self.internal_tools:
                return []

            # For now, suggest recently created archives and large archives
            archives_result = await self.internal_tools.list_video_archives()
            archives = archives_result.get("archives", [])

            # Sort by size (larger archives likely more important)
            archives.sort(key=lambda x: x.get("video_size_mb", 0), reverse=True)

            quick_access = []
            for archive in archives[:5]:  # Top 5 by size
                quick_access.append(
                    {
                        "name": archive["name"],
                        "size_mb": archive.get("video_size_mb", 0),
                        "type": "large_archive",
                        "reason": "Large knowledge base",
                    }
                )

            return quick_access

        except Exception as e:
            logger.error("Failed to identify quick access archives: %s", e)
            return []

    async def _generate_navigation_recommendations(self, user_id: str) -> List[str]:
        """
        Generate navigation recommendations for the user.

        Args:
            user_id: User identifier for personalized recommendations

        Returns:
            List of navigation recommendation strings
        """
        recommendations = [
            "Use 'search_all_memories' for comprehensive searches across all archives",
            "Create topical archives for frequently discussed subjects",
            "Archive old conversations periodically to keep active memory efficient",
            "Use descriptive names for archives to improve findability",
        ]

        try:
            # Get memory statistics for personalized recommendations
            if not self.internal_tools:
                return recommendations

            stats = await self.internal_tools.get_memory_statistics()

            active_memory = stats.get("active_memory", {})
            total_conversations = active_memory.get("conversations", 0)

            if total_conversations > 1000:
                recommendations.insert(
                    0,
                    "Consider archiving older conversations - you have a large active memory",
                )

            video_archives = stats.get("video_archives", {})
            if len(video_archives) > 10:
                recommendations.append(
                    "Consider organizing archives into categories for better navigation"
                )

        except Exception as e:
            logger.error("Failed to generate navigation recommendations: %s", e)

        return recommendations

    def _generate_search_hints(self) -> List[str]:
        """
        Generate helpful search hints for users.

        Returns:
            List of search hint strings to help users navigate memory
        """
        return [
            "Search by topic: 'programming', 'health', 'travel'",
            "Search by emotion: 'happy conversations', 'creative moments'",
            "Search by time: combine with 'recent', 'last month', 'yesterday'",
            "Search by type: 'questions I asked', 'problems solved', 'ideas shared'",
            "Use quotes for exact phrases: '\"machine learning basics\"'",
            "Combine terms: 'python AND tutorial', 'travel OR vacation'",
        ]

    async def auto_organize_memory(self, user_id: str) -> Dict[str, Any]:
        """
        Automatically organize memory based on intelligent analysis.
        This is Aura's autonomous memory management capability.

        Args:
            user_id: User identifier for memory organization

        Returns:
            Dictionary containing organization results and actions taken
        """
        try:
            self._require_memory_system("auto-organization")
            if self.internal_tools is None:
                return {
                    "status": "error",
                    "message": "Memory internal tools not available",
                }

            # Initialize organization tracking
            organization_tracker = self._create_organization_tracker()

            # Step 1: Analyze current memory state and auto-archive if needed
            initial_stats = await self.internal_tools.get_memory_statistics()
            await self._auto_archive_if_needed(
                user_id, initial_stats, organization_tracker
            )

            # Step 2: Generate and process archive suggestions
            await self._process_archive_suggestions(user_id, organization_tracker)

            # Step 3: Calculate efficiency improvements
            await self._calculate_efficiency_improvements(
                initial_stats, organization_tracker
            )

            logger.info(
                "🤖 Auto-organized memory for %s: %s archives created, %s conversations archived",
                user_id,
                organization_tracker["archives_created"],
                organization_tracker["conversations_archived"],
            )

            return organization_tracker

        except ValueError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error("❌ Failed to auto-organize memory: %s", e)
            return {"status": "error", "message": str(e)}

    def _create_organization_tracker(self) -> Dict[str, Any]:
        """
        Create a standardized organization results tracker.

        Returns:
            Dictionary for tracking organization progress and results
        """
        return {
            "status": "success",
            "actions_taken": [],
            "suggestions_created": [],
            "archives_created": 0,
            "conversations_archived": 0,
            "efficiency_gained": 0,
        }

    async def _auto_archive_if_needed(
        self, user_id: str, stats: Dict[str, Any], tracker: Dict[str, Any]
    ) -> None:
        """
        Auto-archive old conversations if memory usage is high.

        Args:
            user_id: User identifier for archiving operations
            stats: Current memory statistics
            tracker: Organization tracker to update with results
        """
        if self.internal_tools is None:
            return

        active_conversations = stats.get("active_memory", {}).get("conversations", 0)

        if active_conversations > 500:  # Memory threshold
            archive_result = await self.internal_tools.archive_old_conversations(
                user_id=user_id, codec="h264"
            )

            if archive_result.get("status") == "success":
                archived_count = archive_result.get("archived_count", 0)
                tracker["actions_taken"].append(
                    f"Auto-archived {archived_count} old conversations"
                )
                tracker["conversations_archived"] = archived_count

    async def _process_archive_suggestions(
        self, user_id: str, tracker: Dict[str, Any]
    ) -> None:
        """
        Process archive suggestions and auto-create high-confidence ones.

        Args:
            user_id: User identifier for suggestion processing
            tracker: Organization tracker to update with results
        """
        suggestions = await self.suggest_archive_opportunities(user_id)

        high_confidence_threshold = 0.8

        # Separate high and low confidence suggestions
        high_confidence = [
            s
            for s in suggestions
            if s.get("relevance_score", 0) > high_confidence_threshold
        ]
        low_confidence = [
            s
            for s in suggestions
            if s.get("relevance_score", 0) <= high_confidence_threshold
        ]

        # Auto-create high-confidence archives
        for suggestion in high_confidence:
            success = await self._try_create_suggested_archive(
                suggestion, user_id, tracker
            )
            if success:
                tracker["archives_created"] += 1

        # Add low-confidence suggestions for user review
        tracker["suggestions_created"].extend(low_confidence)

    async def _try_create_suggested_archive(
        self, suggestion: Dict[str, Any], user_id: str, tracker: Dict[str, Any]
    ) -> bool:
        """
        Attempt to create an archive from a suggestion.

        Args:
            suggestion: Archive suggestion to attempt creating
            user_id: User identifier for archive creation
            tracker: Organization tracker to update with results

        Returns:
            True if archive was successfully created
        """
        try:
            archive_spec = MemoryArchiveSpec(
                name=suggestion["suggested_name"],
                archive_type=MemoryArchiveType(suggestion["archive_type"]),
                description=suggestion["description"],
                content_criteria=suggestion["content_criteria"],
                priority=MemoryPriority.MEDIUM,
                auto_update=False,
            )

            create_result = await self.create_custom_archive(
                archive_spec=archive_spec, user_id=user_id, execute_immediately=True
            )

            if create_result.get("executed"):
                tracker["actions_taken"].append(
                    f"Auto-created archive: {suggestion['suggested_name']}"
                )
                return True

        except Exception as e:
            logger.error(
                "Failed to auto-create archive %s: %s", suggestion["suggested_name"], e
            )

        return False

    async def _calculate_efficiency_improvements(
        self, initial_stats: Dict[str, Any], tracker: Dict[str, Any]
    ) -> None:
        """
        Calculate and record efficiency improvements from organization.

        Args:
            initial_stats: Memory statistics before organization
            tracker: Organization tracker to update with efficiency metrics
        """
        if self.internal_tools is None:
            return

        new_stats = await self.internal_tools.get_memory_statistics()

        initial_conversations = initial_stats.get("active_memory", {}).get(
            "conversations", 0
        )
        new_conversations = new_stats.get("active_memory", {}).get("conversations", 0)

        if new_conversations < initial_conversations:
            efficiency_improvement = (
                (initial_conversations - new_conversations) / initial_conversations
            ) * 100
            tracker["efficiency_gained"] = round(efficiency_improvement, 1)


# Global instance
_intelligent_memory_manager: Optional[AuraIntelligentMemoryManager] = None


def get_intelligent_memory_manager(
    vector_db_client: Optional[Any] = None,
) -> AuraIntelligentMemoryManager:
    """
    Get or create the intelligent memory manager instance.

    Args:
        vector_db_client: Optional vector database client for integration

    Returns:
        The global AuraIntelligentMemoryManager instance
    """
    global _intelligent_memory_manager
    if _intelligent_memory_manager is None:
        _intelligent_memory_manager = AuraIntelligentMemoryManager(vector_db_client)
    return _intelligent_memory_manager


def reset_intelligent_memory_manager() -> None:
    """
    Reset the global instance.

    Used primarily for testing or reinitialization scenarios.
    """
    global _intelligent_memory_manager
    _intelligent_memory_manager = None
