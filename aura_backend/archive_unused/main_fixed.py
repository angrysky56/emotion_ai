"""
Aura Backend - Advanced AI Companion Architecture (FIXED VERSION)
===============================================

Fixed version that handles large system instructions properly to prevent API errors.

Core backend system for Aura (Adaptive Reflective Companion) featuring:
- Vector database integration for semantic memory
- MCP server for tool integration
- Advanced state management and persistence
- Emotional and cognitive pattern analysis
- ASEKE framework implementation
- MCP client integration for extended capabilities

FIXES:
- Limits system instruction size to prevent 500 errors
- Better tool selection and truncation
- Memory context size limits
- Error handling for API limits
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

import chromadb
from chromadb.config import Settings
import numpy as np
from sentence_transformers import SentenceTransformer

from google import genai

from dotenv import load_dotenv
import os
import aiofiles

# Import MCP-Gemini Bridge

# Import MCP integration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Load and configure Gemini API
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    logger.error("❌ GOOGLE_API_KEY not found in environment variables")
    raise ValueError("GOOGLE_API_KEY environment variable is required")

client = genai.Client(api_key=api_key)

# Initialize embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

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

class AuraVectorDB:
    """Advanced vector database for Aura's memory and knowledge management"""

    def __init__(self, persist_directory: str = "./aura_chroma_db"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Initialize collections
        self._init_collections()

    def _init_collections(self):
        """Initialize vector database collections"""
        try:
            # Conversation memory collection
            self.conversations = self.client.get_or_create_collection(
                name="aura_conversations",
                metadata={"description": "Conversation history with semantic search"}
            )

            # Emotional patterns collection
            self.emotional_patterns = self.client.get_or_create_collection(
                name="aura_emotional_patterns",
                metadata={"description": "Historical emotional state patterns"}
            )

            # Cognitive patterns collection
            self.cognitive_patterns = self.client.get_or_create_collection(
                name="aura_cognitive_patterns",
                metadata={"description": "Cognitive focus and ASEKE component tracking"}
            )

            # Knowledge substrate collection
            self.knowledge_substrate = self.client.get_or_create_collection(
                name="aura_knowledge_substrate",
                metadata={"description": "Shared knowledge and insights"}
            )

            logger.info("✅ Vector database collections initialized successfully")

        except Exception as e:
            logger.error("❌ Failed to initialize vector collections: %s", e)
            raise

    async def store_conversation(self, memory: ConversationMemory) -> str:
        """Store conversation memory with automatic embedding generation"""
        try:
            # Generate embedding if not provided
            if memory.embedding is None:
                memory.embedding = embedding_model.encode(memory.message).tolist()

            # Create unique ID
            if memory.timestamp is None:
                memory.timestamp = datetime.now()
            doc_id = f"{memory.user_id}_{memory.timestamp.isoformat()}_{uuid.uuid4().hex[:8]}"

            # Prepare metadata
            metadata = {
                "user_id": memory.user_id,
                "sender": memory.sender,
                "timestamp": memory.timestamp.isoformat(),
                "session_id": memory.session_id
            }

            # Add emotional state if present
            if memory.emotional_state:
                metadata.update({
                    "emotion_name": memory.emotional_state.name,
                    "emotion_intensity": memory.emotional_state.intensity.value,
                    "brainwave": memory.emotional_state.brainwave,
                    "neurotransmitter": memory.emotional_state.neurotransmitter
                })

            # Add cognitive state if present
            if memory.cognitive_state:
                metadata.update({
                    "cognitive_focus": memory.cognitive_state.focus.value,
                    "cognitive_description": memory.cognitive_state.description
                })

            # Store in vector database
            self.conversations.add(
                documents=[memory.message],
                embeddings=memory.embedding,
                metadatas=[metadata],
                ids=[doc_id]
            )

            logger.info("📝 Stored conversation memory: %s", doc_id)
            return doc_id

        except Exception as e:
            logger.error("❌ Failed to store conversation memory: %s", e)
            raise
    async def search_conversations(
        self,
        query: str,
        user_id: str,
        n_results: int = 5,
        where_filter: Optional[Dict] = None
    ) -> List[Dict]:
        """Semantic search through conversation history"""
        try:
            # Generate query embedding
            query_embedding = embedding_model.encode(query).tolist()

            # Prepare where filter with proper typing for ChromaDB
            base_filter: Dict[str, Any] = {"user_id": {"$eq": user_id}}
            if where_filter:
                base_filter.update(where_filter)

            # Perform semantic search
            results = self.conversations.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=base_filter,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            formatted_results = []
            if (results is not None and
                results.get('documents') is not None and
                isinstance(results['documents'], list) and
                results['documents'] and
                results.get('metadatas') is not None and
                results['metadatas'] and
                results.get('distances') is not None and
                results['distances']):
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        "content": doc,
                        "metadata": results['metadatas'][0][i],
                        "similarity": 1 - results['distances'][0][i]  # Convert distance to similarity
                    })

            logger.info("🔍 Found %s relevant memories for query: %s", len(formatted_results), query)
            return formatted_results

        except Exception as e:
            logger.error("❌ Failed to search conversations: %s", e)
            return []
    async def store_emotional_pattern(self, emotional_state: EmotionalStateData, user_id: str) -> str:
        """Store emotional state pattern for analysis"""
        try:
            # Create embedding from emotional context
            emotion_text = f"{emotional_state.name} {emotional_state.description} {emotional_state.brainwave} {emotional_state.neurotransmitter}"
            embedding = embedding_model.encode(emotion_text).tolist()

            # Ensure timestamp is set
            if emotional_state.timestamp is None:
                emotional_state.timestamp = datetime.now()
            doc_id = f"emotion_{user_id}_{emotional_state.timestamp.isoformat()}_{uuid.uuid4().hex[:8]}"

            metadata = {
                "user_id": user_id,
                "emotion_name": emotional_state.name,
                "intensity": emotional_state.intensity.value,
                "brainwave": emotional_state.brainwave,
                "neurotransmitter": emotional_state.neurotransmitter,
                "timestamp": emotional_state.timestamp.isoformat(),
                "formula": emotional_state.formula
            }

            self.emotional_patterns.add(
                documents=[emotion_text],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id]
            )

            logger.info("🎭 Stored emotional pattern: %s (%s)", emotional_state.name, emotional_state.intensity.value)
            return doc_id

        except Exception as e:
            logger.error("❌ Failed to store emotional pattern: %s", e)
            raise

    async def analyze_emotional_trends(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Analyze emotional patterns over time"""
        try:
            # Get recent emotional data
            cutoff_date = datetime.now() - timedelta(days=days)

            results = self.emotional_patterns.get(
                where={
                    "$and": [
                        {"user_id": {"$eq": user_id}},
                        {"timestamp": {"$gte": cutoff_date.isoformat()}}
                    ]
                },
                include=["metadatas"]
            )

            if not results['metadatas']:
                return {"message": "No emotional data found for analysis"}

            # Analyze patterns
            emotions = [str(meta['emotion_name']) for meta in results['metadatas']]
            intensities = [str(meta['intensity']) for meta in results['metadatas']]
            brainwaves = [str(meta['brainwave']) for meta in results['metadatas']]

            analysis = {
                "period_days": days,
                "total_entries": len(emotions),
                "dominant_emotions": self._get_top_items(emotions, 3),
                "intensity_distribution": self._get_distribution(intensities),
                "brainwave_patterns": self._get_distribution(brainwaves),
                "emotional_stability": self._calculate_stability(emotions),
                "recommendations": self._generate_emotional_recommendations(emotions, intensities)
            }

            logger.info("📊 Generated emotional analysis for user %s", user_id)
            return analysis

        except Exception as e:
            logger.error("❌ Failed to analyze emotional trends: %s", e)
            return {"error": str(e)}
    def _get_top_items(self, items: List[str], top_n: int) -> List[Tuple[str, int]]:
        """Get top N most frequent items"""
        from collections import Counter
        counter = Counter(items)
        return counter.most_common(top_n)

    def _get_distribution(self, items: List[str]) -> Dict[str, int]:
        """Get distribution of items"""
        from collections import Counter
        return dict(Counter(items))

    def _calculate_stability(self, emotions: List[str]) -> float:
        """Calculate emotional stability score (0-1, higher = more stable)"""
        if len(emotions) <= 1:
            return 1.0

        from collections import Counter
        emotion_counts = Counter(emotions)
        entropy = -sum((count/len(emotions)) * np.log2(count/len(emotions))
                      for count in emotion_counts.values())
        max_entropy = np.log2(len(emotion_counts))

        # Normalize entropy to 0-1 and invert (higher = more stable)
        return 1 - (entropy / max_entropy if max_entropy > 0 else 0)

    def _generate_emotional_recommendations(self, emotions: List[str], intensities: List[str]) -> List[str]:
        """Generate emotional well-being recommendations"""
        recommendations = []

        # High intensity emotions
        high_intensity_count = intensities.count("High")
        if high_intensity_count > len(intensities) * 0.7:
            recommendations.append("Consider emotional regulation techniques - high intensity emotions detected")

        # Negative emotion patterns
        negative_emotions = ["Angry", "Sad", "Fear", "Disgust"]
        negative_count = sum(1 for emotion in emotions if emotion in negative_emotions)
        if negative_count > len(emotions) * 0.5:
            recommendations.append("Focus on positive emotional experiences and self-care activities")

        # Lack of variety
        unique_emotions = len(set(emotions))
        if unique_emotions < 3 and len(emotions) > 5:
            recommendations.append("Explore diverse experiences to expand emotional range")

        return recommendations or ["Emotional patterns appear balanced - continue current approach"]

class AuraFileSystem:
    """Enhanced file system operations for Aura"""

    def __init__(self, base_path: str = "./aura_data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

        # Create subdirectories
        (self.base_path / "users").mkdir(exist_ok=True)
        (self.base_path / "sessions").mkdir(exist_ok=True)
        (self.base_path / "exports").mkdir(exist_ok=True)
        (self.base_path / "backups").mkdir(exist_ok=True)

    async def save_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> str:
        """Save user profile with enhanced data"""
        try:
            profile_path = self.base_path / "users" / f"{user_id}.json"

            # Add metadata
            profile_data.update({
                "last_updated": datetime.now().isoformat(),
                "user_id": user_id
            })

            async with aiofiles.open(profile_path, 'w') as f:
                await f.write(json.dumps(profile_data, indent=2, default=str))

            logger.info("💾 Saved user profile: %s", user_id)
            return str(profile_path)

        except Exception as e:
            logger.error("❌ Failed to save user profile: %s", e)
            raise

    async def load_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Load user profile"""
        try:
            profile_path = self.base_path / "users" / f"{user_id}.json"

            if not profile_path.exists():
                return None

            async with aiofiles.open(profile_path, 'r') as f:
                content = await f.read()
                return json.loads(content)

        except Exception as e:
            logger.error("❌ Failed to load user profile: %s", e)
            return None

    async def export_conversation_history(self, user_id: str, format: str = "json") -> str:
        """Export conversation history in various formats"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_export_{user_id}_{timestamp}.{format}"
            export_path = self.base_path / "aura_data/exports" / filename

            # This would integrate with the vector DB to get conversation history
            # For now, creating a placeholder structure
            # This should not be a placeholder anymore as the db is functional!!!
            export_data = {
                "user_id": user_id,
                "export_timestamp": datetime.now().isoformat(),
                "format": format,
                "conversations": [],  # Would be populated from vector DB
                "emotional_patterns": [],  # Would be populated from vector DB
                "cognitive_patterns": []  # Would be populated from vector DB
            }

            if format == "json":
                async with aiofiles.open(export_path, 'w') as f:
                    await f.write(json.dumps(export_data, indent=2, default=str))

            logger.info("📤 Exported conversation history: %s", filename)
            return str(export_path)

        except Exception as e:
            logger.error("❌ Failed to export conversation history: %s", e)
            raise

class AuraStateManager:
    """Advanced state management with automated database operations"""

    def __init__(self, vector_db: AuraVectorDB, aura_file_system: AuraFileSystem):
        self.vector_db = vector_db
        self.aura_file_system = aura_file_system
        self.active_sessions: Dict[str, Dict] = {}

    async def on_emotional_state_change(
        self,
        user_id: str,
        old_state: Optional[EmotionalStateData],
        new_state: EmotionalStateData
    ):
        """Automated actions when emotional state changes"""
        try:
            # Store emotional pattern
            await self.vector_db.store_emotional_pattern(new_state, user_id)

            # Check for significant changes
            if old_state and old_state.name != new_state.name:
                logger.info("🎭 Emotional transition: %s → %s", old_state.name, new_state.name)

                # Trigger specific actions based on transitions
                await self._handle_emotional_transition(user_id, old_state, new_state)

            # Update user profile
            profile = await self.aura_file_system.load_user_profile(user_id) or {}
            profile["last_emotional_state"] = asdict(new_state)
            await self.aura_file_system.save_user_profile(user_id, profile)

        except Exception as e:
            logger.error("❌ Failed to handle emotional state change: %s", e)

    async def _handle_emotional_transition(
        self,
        user_id: str,
        old_state: EmotionalStateData,
        new_state: EmotionalStateData
    ):
        """Handle specific emotional transitions"""
        # Define concerning transitions
        concerning_transitions = [
            ("Happy", "Sad"),
            ("Joy", "Angry"),
            ("Peace", "Angry"),
            ("Normal", "Sad")
        ]

        transition = (old_state.name, new_state.name)

        if transition in concerning_transitions:
            # Store intervention recommendation
            recommendation = {
                "type": "emotional_support",
                "transition": transition,
                "timestamp": datetime.now().isoformat(),
                "suggestion": f"Noticed transition from {old_state.name} to {new_state.name}. Consider gentle conversation topics."
            }

            # Log the recommendation details and store for potential future use
            logger.info("🔔 Emotional support recommendation for %s: %s", user_id, recommendation['suggestion'])

            # TODO: Could store recommendation in database for analysis or trigger gentle conversation adjustments
            #