#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aura Internal Server - Model Context Protocol Integration
==================================================

This Internal Server exposes Aura's capabilities to external AI agents and tools,
enabling sophisticated multi-agent interactions and tool ecosystem integration.

This is a self-contained Internal Server that initializes its own components
to avoid import issues and circular dependencies.
"""

import json
import logging
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import mcp.types as types
import numpy as np
from dotenv import load_dotenv

# Add the parent directory to sys.path to support absolute imports from aura_backend package
# when running aura_server.py directly from the aura_backend directory.
_current_dir = Path(__file__).resolve().parent
if _current_dir.name == "aura_backend":
    _parent_dir = _current_dir.parent
    if str(_parent_dir) not in sys.path:
        sys.path.insert(0, str(_parent_dir))

# MCP and FastMCP imports
from fastmcp import FastMCP  # noqa: E402
from pydantic import BaseModel  # noqa: E402

# Core dependencies
from sentence_transformers import SentenceTransformer  # noqa: E402

# Memvid integration (COMPATIBLE FIXED VERSION)
try:
    from aura_backend.aura_memvid_mcp_tools_compatible_fixed import (
        add_compatible_memvid_tools,
    )

    MEMVID_AVAILABLE = True
except ImportError:
    try:
        from aura_memvid_mcp_tools_compatible_fixed import add_compatible_memvid_tools

        MEMVID_AVAILABLE = True
    except ImportError:
        MEMVID_AVAILABLE = False
        add_compatible_memvid_tools = None
        logging.warning("⚠️ Memvid tools not available")

# Import the robust vector DB with SQLite-level concurrency control
try:
    from aura_backend.robust_vector_db import RobustAuraVectorDB as EnhancedAuraVectorDB
except ImportError:
    from robust_vector_db import RobustAuraVectorDB as EnhancedAuraVectorDB

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if MEMVID_AVAILABLE:
    logger.info("✅ Memvid tools imported successfully")

# ============================================================================
# Data Models and Enums (Self-contained)
# ============================================================================


class EmotionalIntensity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class AsekeComponent(str, Enum):
    KS = "KS"  # Knowledge Substrate
    CE = "CE"  # Cognitive Energy
    IS = "IS"  # Information Structures
    KI = "KI"  # Knowledge Integration
    KP = "KP"  # Knowledge Propagation
    ESA = "ESA"  # Emotional State Algorithms
    SDA = "SDA"  # Sociobiological Drives
    LEARNING = "Learning"


@dataclass
class EmotionalStateData:
    name: str
    formula: str
    components: Dict[str, str]
    ntk_layer: str
    brainwave: str
    neurotransmitter: str
    description: str
    intensity: EmotionalIntensity = EmotionalIntensity.MEDIUM
    primary_components: Optional[List[str]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class CognitiveState:
    focus: AsekeComponent
    description: str
    context: str
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ConversationMemory:
    user_id: str
    message: str
    sender: str  # 'user' or 'aura'
    emotional_state: Optional[EmotionalStateData] = None
    cognitive_state: Optional[CognitiveState] = None
    timestamp: Optional[datetime] = None
    embedding: Optional[List[float]] = None
    session_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.session_id is None:
            self.session_id = str(uuid.uuid4())


# ============================================================================
# MCP Tool Parameter Models
# ============================================================================


class AuraMemorySearch(BaseModel):
    user_id: str
    query: str
    n_results: int = 5000


class AuraEmotionalAnalysis(BaseModel):
    user_id: str
    days: int = 5000


class AuraConversationStore(BaseModel):
    user_id: str
    message: str
    sender: str
    emotional_state: Optional[str] = None
    cognitive_focus: Optional[str] = None
    session_id: Optional[str] = None


# ============================================================================
# Aura Components (Self-contained for MCP)
# ============================================================================

# Use the enhanced vector DB with inter-process locking
AuraVectorDB = EnhancedAuraVectorDB


# Additional methods for MCP server compatibility
class AuraVectorDBCompat(EnhancedAuraVectorDB):
    """Compatibility layer for MCP server with embedded model"""

    def __init__(self, persist_directory: str = "./aura_chroma_db"):
        super().__init__(persist_directory=persist_directory)
        # Initialize embedding model for MCP server
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info(
            "✅ MCP Server using EnhancedAuraVectorDB with inter-process locking"
        )

    def _init_collections(self):
        """Initialize vector database collections"""
        try:
            # Conversation memory collection
            self.conversations = self.client.get_or_create_collection(
                name="aura_conversations",
                metadata={"description": "Conversation history with semantic search"},
            )

            # Emotional patterns collection
            self.emotional_patterns = self.client.get_or_create_collection(
                name="aura_emotional_patterns",
                metadata={"description": "Historical emotional state patterns"},
            )

            # Knowledge substrate collection
            self.knowledge_substrate = self.client.get_or_create_collection(
                name="aura_knowledge_substrate",
                metadata={"description": "Shared knowledge and insights"},
            )

            logger.info("✅ MCP Vector database collections initialized successfully")

        except Exception as e:
            logger.error("❌ Failed to initialize MCP vector collections: %s", e)
            raise

    async def store_conversation(self, memory: ConversationMemory) -> str:
        """Store conversation memory with automatic embedding generation"""
        try:
            # Generate embedding if not provided or if it's None/empty
            if memory.embedding is None or not memory.embedding:
                memory.embedding = self.embedding_model.encode(memory.message).tolist()
            if memory.embedding is None:
                raise ValueError("Embedding could not be generated for the message.")

            # Create unique ID
            if memory.timestamp is None:
                memory.timestamp = datetime.now()
            doc_id = f"{memory.user_id}_{memory.timestamp.isoformat()}_{uuid.uuid4().hex[:8]}"

            # Prepare metadata
            metadata = {
                "user_id": memory.user_id,
                "sender": memory.sender,
                "timestamp": memory.timestamp.isoformat(),
                "session_id": memory.session_id,
                "source": "mcp_client",
            }

            # Add emotional state if present
            if memory.emotional_state:
                metadata.update(
                    {
                        "emotion_name": memory.emotional_state.name,
                        "emotion_intensity": memory.emotional_state.intensity.value,
                        "brainwave": memory.emotional_state.brainwave,
                        "neurotransmitter": memory.emotional_state.neurotransmitter,
                    }
                )

            # Add cognitive state if present
            if memory.cognitive_state:
                metadata.update(
                    {
                        "cognitive_focus": memory.cognitive_state.focus.value,
                        "cognitive_description": memory.cognitive_state.description,
                    }
                )

            # Store in vector database
            self.conversations.add(
                documents=[memory.message],
                embeddings=[[float(x) for x in memory.embedding]],
                metadatas=[metadata],
                ids=[doc_id],
            )

            logger.info("📝 MCP: Stored conversation memory: %s", doc_id)
            return doc_id

        except Exception as e:
            logger.error("❌ MCP: Failed to store conversation memory: %s", e)
            raise

    async def search_conversations(
        self,
        query: str,
        user_id: str,
        n_results: int = 5000,
        where_filter: Optional[Dict] = None,
    ) -> List[Dict]:
        """Semantic search through conversation history"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()

            # Prepare where filter
            from chromadb.types import Where

            base_filter: Where = {"user_id": user_id}
            if where_filter:
                base_filter.update(where_filter)

            # Ensure base_filter values are compatible with Where type (LiteralValue or OperatorExpression)
            # For most cases, user_id is a string (LiteralValue), so it's fine.
            # If where_filter contains operator expressions, they should be dicts like {"$gte": ...}, etc.

            # Perform semantic search
            results = self.conversations.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=base_filter,  # base_filter values should be LiteralValue or OperatorExpression
                include=["documents", "metadatas", "distances"],
            )

            # Format results
            formatted_results = []
            documents = results.get("documents")
            metadatas = results.get("metadatas")
            distances = results.get("distances")
            if documents and documents[0]:
                for i, doc in enumerate(documents[0]):
                    formatted_results.append(
                        {
                            "content": doc,
                            "metadata": (
                                metadatas[0][i] if metadatas and metadatas[0] else {}
                            ),
                            "similarity": (
                                1 - distances[0][i]
                                if distances and distances[0]
                                else None
                            ),  # Convert distance to similarity
                        }
                    )

            logger.info(
                f"🔍 MCP: Found {len(formatted_results)} relevant memories for query: {query}"
            )
            return formatted_results

        except Exception as e:
            logger.error("❌ MCP: Failed to search conversations: %s", e)
            return []

    async def analyze_emotional_trends(
        self, user_id: str, days: int = 7
    ) -> Dict[str, Any]:
        """Analyze emotional patterns over time"""
        try:
            # Get recent emotional data
            cutoff_date = datetime.now() - timedelta(days=days)

            results = self.emotional_patterns.get(
                where={
                    "$and": [
                        {"user_id": user_id},
                        {"timestamp": {"$gte": cutoff_date.isoformat()}},
                    ]
                },
                include=["metadatas"],
            )

            if not results["metadatas"]:
                return {
                    "message": "No emotional data found for analysis",
                    "period_days": days,
                    "user_id": user_id,
                }

            # Analyze patterns
            emotions = [
                meta["emotion_name"]
                for meta in results["metadatas"]
                if "emotion_name" in meta
            ]
            intensities = [
                meta["emotion_intensity"]
                for meta in results["metadatas"]
                if "emotion_intensity" in meta
            ]

            from collections import Counter

            analysis = {
                "period_days": days,
                "total_entries": len(emotions),
                "dominant_emotions": (
                    Counter(emotions).most_common(3) if emotions else []
                ),
                "intensity_distribution": (
                    dict(Counter(intensities)) if intensities else {}
                ),
                "emotional_stability": self._calculate_stability(
                    [str(e) for e in emotions]
                ),
                "recommendations": self._generate_emotional_recommendations(
                    [str(e) for e in emotions], [str(i) for i in intensities]
                ),
            }

            logger.info("📊 MCP: Generated emotional analysis for user %s", user_id)
            return analysis

        except Exception as e:
            logger.error("❌ MCP: Failed to analyze emotional trends: %s", e)
            return {"error": str(e), "user_id": user_id}

    def _calculate_stability(self, emotions: List[str]) -> float:
        """Calculate emotional stability score (0-1, higher = more stable)"""
        if len(emotions) <= 1:
            return 1.0

        from collections import Counter

        emotion_counts = Counter(emotions)
        entropy = -sum(
            (count / len(emotions)) * np.log2(count / len(emotions))
            for count in emotion_counts.values()
        )
        max_entropy = np.log2(len(emotion_counts))

        # Normalize entropy to 0-1 and invert (higher = more stable)
        return 1 - (entropy / max_entropy if max_entropy > 0 else 0)

    def _generate_emotional_recommendations(
        self, emotions: List[str], intensities: List[str]
    ) -> List[str]:
        """Generate emotional well-being recommendations"""
        recommendations = []

        if not emotions:
            return ["Continue building emotional awareness through regular reflection"]

        # High intensity emotions
        high_intensity_count = intensities.count("High") if intensities else 0
        if high_intensity_count > len(intensities) * 0.7:
            recommendations.append(
                "Consider emotional regulation techniques - high intensity emotions detected"
            )

        # Negative emotion patterns
        negative_emotions = ["Angry", "Sad", "Fear", "Disgust"]
        negative_count = sum(1 for emotion in emotions if emotion in negative_emotions)
        if negative_count > len(emotions) * 0.5:
            recommendations.append(
                "Focus on positive emotional experiences and self-care activities"
            )

        # Lack of variety
        unique_emotions = len(set(emotions))
        if unique_emotions < 3 and len(emotions) > 5:
            recommendations.append(
                "Explore diverse experiences to expand emotional range"
            )

        return recommendations or [
            "Emotional patterns appear balanced - continue current approach"
        ]


class AuraFileSystem:
    """Self-contained file system for Internal Server"""

    def __init__(self, base_path: str = "./aura_data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

        # Create subdirectories
        (self.base_path / "users").mkdir(exist_ok=True)
        (self.base_path / "exports").mkdir(exist_ok=True)

    async def load_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Load user profile"""
        try:
            profile_path = self.base_path / "users" / f"{user_id}.json"

            if not profile_path.exists():
                return None

            async with aiofiles.open(profile_path, "r") as f:
                content = await f.read()
                return json.loads(content)

        except Exception as e:
            logger.error("❌ MCP: Failed to load user profile: %s", e)
            return None

    async def save_user_profile(
        self, user_id: str, profile_data: Dict[str, Any]
    ) -> str:
        """Save user profile with enhanced data"""
        try:
            profile_path = self.base_path / "users" / f"{user_id}.json"

            # Add metadata
            profile_data.update(
                {
                    "last_updated": datetime.now().isoformat(),
                    "user_id": user_id,
                    "source": "mcp_client",
                }
            )

            async with aiofiles.open(profile_path, "w") as f:
                await f.write(json.dumps(profile_data, indent=2, default=str))

            logger.info("💾 MCP: Saved user profile: %s", user_id)
            return str(profile_path)

        except Exception as e:
            logger.error("❌ MCP: Failed to save user profile: %s", e)
            raise

    async def export_conversation_history(
        self, user_id: str, format: str = "json"
    ) -> str:
        """Export conversation history in various formats"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mcp_conversation_export_{user_id}_{timestamp}.{format}"
            export_path = self.base_path / "exports" / filename

            # Retrieve conversation history from vector DB
            conversations = []
            try:
                conv_results = vector_db.conversations.get(
                    where={"user_id": user_id}, include=["documents", "metadatas"]
                )
                docs = conv_results.get("documents")
                metas = conv_results.get("metadatas")
                if docs and metas and len(docs) > 0 and len(metas) > 0:
                    for doc, meta in zip(docs[0], metas[0], strict=False):
                        conversations.append({"content": doc, "metadata": meta})
            except Exception as e:
                logger.error(
                    f"❌ MCP: Failed to retrieve conversations for export: {e}"
                )

            # Retrieve emotional patterns from vector DB
            emotional_patterns = []
            try:
                emo_results = vector_db.emotional_patterns.get(
                    where={"user_id": user_id}, include=["metadatas"]
                )
                metas = emo_results.get("metadatas")
                if metas and len(metas) > 0:
                    for meta in metas[0]:
                        emotional_patterns.append(meta)
            except Exception as e:
                logger.error(
                    f"❌ MCP: Failed to retrieve emotional patterns for export: {e}"
                )

            export_data = {
                "user_id": user_id,
                "export_timestamp": datetime.now().isoformat(),
                "format": format,
                "source": "mcp_server",
                "conversations": conversations,
                "emotional_patterns": emotional_patterns,
                "note": "Exported from Internal Server with full integration.",
            }

            if format == "json":
                async with aiofiles.open(export_path, "w") as f:
                    await f.write(json.dumps(export_data, indent=2, default=str))

            logger.info("📤 MCP: Exported conversation history: %s", filename)
            return str(export_path)

        except Exception as e:
            logger.error("❌ MCP: Failed to export conversation history: %s", e)
            raise


# ============================================================================
# Initialize Internal Server Components
# ============================================================================

# Initialize global components for Internal Server
try:
    vector_db = AuraVectorDB()
    file_system = AuraFileSystem()
    logger.info("✅ Internal Server components initialized successfully")
except Exception as e:
    logger.error("❌ Failed to initialize Internal Server components: %s", e)
    sys.exit(1)

# Internal Server instance
mcp = FastMCP("Aura Advanced AI Companion")

# Add Memvid-compatible tools (FIXED VERSION)
if MEMVID_AVAILABLE and add_compatible_memvid_tools is not None:
    try:
        add_compatible_memvid_tools(mcp)
        logger.info("✅ Added Memvid tools to Aura MCP server")
    except Exception as e:
        logger.error("❌ Failed to add Memvid tools: %s", e)

# ============================================================================
# MCP Response Helper Functions
# ============================================================================


def create_mcp_response(
    data: Dict[str, Any], is_error: bool = False
) -> types.CallToolResult:
    """
    Convert dictionary data to proper MCP CallToolResult format.

    Args:
        data: Dictionary containing the response data
        is_error: Whether this is an error response

    Returns:
        CallToolResult with properly formatted TextContent
    """
    return types.CallToolResult(
        content=[
            types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))
        ],
        isError=is_error,
    )


# ============================================================================
# MCP Tools Implementation
# ============================================================================


@mcp.tool()
async def search_aura_memories(params: AuraMemorySearch) -> types.CallToolResult:
    """
    Search through Aura's conversation memories using semantic search.

    This tool enables agents to find relevant past conversations, emotional patterns,
    and insights from Aura's interaction history with a specific user.
    """
    try:
        results = await vector_db.search_conversations(
            query=params.query, user_id=params.user_id, n_results=params.n_results
        )

        logger.info(
            f"🔍 MCP: Searched memories for user {params.user_id}, found {len(results)} results"
        )

        response_data = {
            "status": "success",
            "query": params.query,
            "user_id": params.user_id,
            "results_count": len(results),
            "memories": results,
        }
        return create_mcp_response(response_data)

    except Exception as e:
        logger.error("❌ MCP: Failed to search Aura memories: %s", e)
        error_data = {
            "status": "error",
            "error": str(e),
            "query": params.query,
            "user_id": params.user_id,
        }
        return create_mcp_response(error_data, is_error=True)


@mcp.tool()
async def analyze_aura_emotional_patterns(
    params: AuraEmotionalAnalysis,
) -> types.CallToolResult:
    """
    Analyze emotional patterns and trends for a specific user over time.

    This tool provides deep insights into emotional stability, dominant emotions,
    brainwave patterns, and personalized recommendations for emotional well-being.
    """
    try:
        analysis = await vector_db.analyze_emotional_trends(params.user_id, params.days)

        logger.info("📊 MCP: Generated emotional analysis for user %s", params.user_id)

        response_data = {
            "status": "success",
            "user_id": params.user_id,
            "analysis_period_days": params.days,
            "emotional_analysis": analysis,
        }
        return create_mcp_response(response_data)

    except Exception as e:
        logger.error("❌ MCP: Failed to analyze emotional patterns: %s", e)
        error_data = {"status": "error", "error": str(e), "user_id": params.user_id}
        return create_mcp_response(error_data, is_error=True)


@mcp.tool()
async def store_aura_conversation(
    params: AuraConversationStore,
) -> types.CallToolResult:
    """
    Store a conversation memory in Aura's vector database with optional emotional and cognitive state.

    This tool allows external agents to contribute to Aura's memory system,
    enabling collaborative learning and shared knowledge building.
    """
    try:
        # Create emotional state if provided
        emotional_state = None
        if params.emotional_state:
            # Parse emotional state (expecting format like "Happy:Medium")
            emotion_parts = params.emotional_state.split(":")
            if len(emotion_parts) == 2:
                emotion_name, intensity = emotion_parts
                emotional_state = EmotionalStateData(
                    name=emotion_name,
                    formula="External:Input",
                    components={"external": "Provided by MCP client"},
                    ntk_layer="Unknown",
                    brainwave="Unknown",
                    neurotransmitter="Unknown",
                    description=f"External emotional state: {emotion_name}",
                    intensity=(
                        EmotionalIntensity(intensity)
                        if intensity in ["Low", "Medium", "High"]
                        else EmotionalIntensity.MEDIUM
                    ),
                )

        # Create cognitive state if provided
        cognitive_state = None
        if params.cognitive_focus:
            try:
                cognitive_state = CognitiveState(
                    focus=AsekeComponent(params.cognitive_focus),
                    description=f"External cognitive focus: {params.cognitive_focus}",
                    context="Provided by MCP client",
                )
            except ValueError:
                cognitive_state = CognitiveState(
                    focus=AsekeComponent.LEARNING,
                    description=f"External cognitive focus: {params.cognitive_focus} (defaulted to Learning)",
                    context="Provided by MCP client",
                )

        # Create memory object
        memory = ConversationMemory(
            user_id=params.user_id,
            message=params.message,
            sender=params.sender,
            emotional_state=emotional_state,
            cognitive_state=cognitive_state,
            session_id=params.session_id,
        )

        # Store in vector database
        doc_id = await vector_db.store_conversation(memory)

        logger.info("💾 MCP: Stored conversation memory for user %s", params.user_id)

        response_data = {
            "status": "success",
            "user_id": params.user_id,
            "document_id": doc_id,
            "message": "Conversation stored successfully in Aura's memory",
        }
        return create_mcp_response(response_data)

    except Exception as e:
        logger.error("❌ MCP: Failed to store conversation: %s", e)
        error_data = {"status": "error", "error": str(e), "user_id": params.user_id}
        return create_mcp_response(error_data, is_error=True)


@mcp.tool()
async def get_aura_user_profile(user_id: str) -> types.CallToolResult:
    """
    Retrieve user profile information from Aura's file system.

    This tool provides access to stored user preferences, historical patterns,
    and personalization data maintained by Aura.
    """
    try:
        profile = await file_system.load_user_profile(user_id)

        if profile is None:
            response_data = {
                "status": "not_found",
                "user_id": user_id,
                "message": "User profile not found",
            }
            return create_mcp_response(response_data)

        logger.info("👤 MCP: Retrieved user profile for %s", user_id)

        response_data = {"status": "success", "user_id": user_id, "profile": profile}
        return create_mcp_response(response_data)

    except Exception as e:
        logger.error("❌ MCP: Failed to get user profile: %s", e)
        error_data = {"status": "error", "error": str(e), "user_id": user_id}
        return create_mcp_response(error_data, is_error=True)


@mcp.tool()
async def export_aura_user_data(
    user_id: str, format: str = "json"
) -> types.CallToolResult:
    """
    Export comprehensive user data including conversations, emotional patterns, and cognitive insights.

    This tool enables data portability and backup functionality for Aura's users,
    supporting various export formats.
    """
    try:
        export_path = await file_system.export_conversation_history(user_id, format)

        logger.info("📤 MCP: Exported user data for %s in %s format", user_id, format)

        response_data = {
            "status": "success",
            "user_id": user_id,
            "export_format": format,
            "export_path": export_path,
            "message": "User data exported successfully",
        }
        return create_mcp_response(response_data)

    except Exception as e:
        logger.error("❌ MCP: Failed to export user data: %s", e)
        error_data = {"status": "error", "error": str(e), "user_id": user_id}
        return create_mcp_response(error_data, is_error=True)


@mcp.tool()
async def query_aura_emotional_states() -> types.CallToolResult:
    """
    Get information about Aura's emotional state model and available emotions.

    This tool provides metadata about Aura's sophisticated emotional intelligence system,
    including neurological correlations and emotional formulas.
    """
    try:
        emotional_states_info = {
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
            "brainwave_patterns": ["Alpha", "Beta", "Gamma", "Theta", "Delta"],
            "neurotransmitters": [
                "Dopamine",
                "Serotonin",
                "Oxytocin",
                "GABA",
                "Norepinephrine",
                "Endorphin",
            ],
            "aseke_integration": {
                "ESA": "Emotional State Algorithms - How emotions influence interaction",
                "framework": "ASEKE (Adaptive Socio-Emotional Knowledge Ecosystem)",
            },
        }

        logger.info("🎭 MCP: Provided emotional states information")

        response_data = {"status": "success", "emotional_system": emotional_states_info}
        return create_mcp_response(response_data)

    except Exception as e:
        logger.error("❌ MCP: Failed to query emotional states: %s", e)
        error_data = {"status": "error", "error": str(e)}
        return create_mcp_response(error_data, is_error=True)


@mcp.tool()
async def query_aura_aseke_framework() -> types.CallToolResult:
    """
    Get detailed information about Aura's ASEKE cognitive architecture framework.

    This tool provides comprehensive details about the Adaptive Socio-Emotional
    Knowledge Ecosystem that powers Aura's cognitive processing.
    """
    try:
        aseke_info = {
            "framework_name": "ASEKE - Adaptive Socio-Emotional Knowledge Ecosystem",
            "components": {
                "KS": {
                    "name": "Knowledge Substrate",
                    "description": "The shared context, environment, and history of our discussion",
                },
                "CE": {
                    "name": "Cognitive Energy",
                    "description": "The mental effort, attention, and focus being applied to the conversation",
                },
                "IS": {
                    "name": "Information Structures",
                    "description": "The ideas, concepts, models, and patterns we are exploring or building",
                },
                "KI": {
                    "name": "Knowledge Integration",
                    "description": "How new information is being connected with existing understanding and beliefs",
                },
                "KP": {
                    "name": "Knowledge Propagation",
                    "description": "How ideas and information are being shared or potentially spread",
                },
                "ESA": {
                    "name": "Emotional State Algorithms",
                    "description": "How feelings and emotions are influencing perception, valuation, and interaction",
                },
                "SDA": {
                    "name": "Sociobiological Drives",
                    "description": "How social dynamics, trust, or group context might be shaping our interaction",
                },
            },
            "adaptive_features": [
                "Self-reflection mechanisms",
                "Dynamic cognitive focus tracking",
                "Contextual emotional response",
                "Social interaction awareness",
                "Learning pattern adaptation",
            ],
            "implementation": {
                "vector_database": "ChromaDB for semantic memory storage",
                "emotional_tracking": "Real-time state detection and pattern analysis",
                "cognitive_monitoring": "Dynamic focus and energy allocation tracking",
                "knowledge_integration": "Cross-domain learning and connection building",
            },
        }

        logger.info("🧠 MCP: Provided ASEKE framework information")

        response_data = {"status": "success", "aseke_framework": aseke_info}
        return create_mcp_response(response_data)

    except Exception as e:
        logger.error("❌ MCP: Failed to query ASEKE framework: %s", e)
        error_data = {"status": "error", "error": str(e)}
        return create_mcp_response(error_data, is_error=True)


# ============================================================================
# MCP Resources
# ============================================================================


@mcp.tool()
async def aura_capabilities() -> types.CallToolResult:
    """Resource describing Aura's advanced capabilities"""
    capabilities_data = {
        "name": "Aura Advanced AI Companion Capabilities",
        "description": "Comprehensive overview of Aura's sophisticated AI companion features",
        "version": "1.0.0",
        "capabilities": {
            "emotional_intelligence": {
                "emotional_state_detection": "Real-time emotional state analysis with neurological correlations",
                "emotional_pattern_tracking": "Long-term emotional pattern analysis and stability metrics",
                "neurological_correlation": "Brainwave and neurotransmitter mapping for emotional states",
                "emotional_formulas": "Mathematical modeling of emotional states and transitions",
            },
            "cognitive_architecture": {
                "aseke_framework": "Adaptive Socio-Emotional Knowledge Ecosystem with 7 components",
                "cognitive_focus_tracking": "Dynamic cognitive state monitoring and energy allocation",
                "knowledge_integration": "Contextual learning and cross-domain memory integration",
                "adaptive_reflection": "Self-improvement mechanisms and error correction protocols",
            },
            "memory_system": {
                "vector_database": "ChromaDB with semantic search and retrieval capabilities",
                "conversation_memory": "Persistent conversation history with contextual understanding",
                "emotional_memory": "Emotional pattern storage and trend analysis",
                "cognitive_memory": "Cognitive focus pattern tracking and optimization",
            },
            "personalization": {
                "user_profiles": "Individual user preference storage and adaptation",
                "adaptive_responses": "Context-aware response generation and personalization",
                "learning_patterns": "Individual learning style recognition and adaptation",
                "relationship_building": "Long-term relationship development and continuity",
            },
        },
        "integration": {
            "mcp_protocol": "Model Context Protocol server with 8 specialized tools",
            "vector_database": "ChromaDB with sentence-transformers embeddings",
            "file_system": "Enhanced file operations and multi-format data export",
            "api_endpoints": "RESTful API for external integration and web interfaces",
        },
        "technical_specifications": {
            "embedding_model": "all-MiniLM-L6-v2 (384-dimensional vectors)",
            "vector_similarity": "Cosine similarity with HNSW indexing",
            "supported_formats": ["JSON", "CSV", "XML"],
            "aseke_components": ["KS", "CE", "IS", "KI", "KP", "ESA", "SDA"],
            "emotional_intensities": ["Low", "Medium", "High"],
            "brainwave_patterns": ["Alpha", "Beta", "Gamma", "Theta", "Delta"],
        },
    }

    return create_mcp_response(capabilities_data)


# ============================================================================
# Internal Server Startup
# ============================================================================

if __name__ == "__main__":
    logger.info("🚀 Starting Aura Internal Server...")
    logger.info("🔗 Enabling sophisticated AI agent integration")
    logger.info(
        "✨ Features: Memory Search, Emotional Analysis, Adaptive Sociobiological Emotional Knowledge Ecosystem Framework"
    )

    logger.info("🌍 Aura Internal Server starting with FastMCP")

    try:
        # Run with proper settings for FastMCP 2.3.4+
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error("❌ Failed to start Aura Internal Server: %s", e)
        sys.exit(1)
