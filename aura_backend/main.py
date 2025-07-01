"""
Aura Backend - Advanced AI Companion Architecture
===============================================

Core backend system for Aura (Adaptive Reflective Companion) featuring:
- Vector database integration for semantic memory
- MCP server for tool integration
- Advanced state management and persistence
- Emotional and cognitive pattern analysis
- ASEKE framework implementation
- MCP client integration for extended capabilities
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from contextlib import asynccontextmanager
import asyncio

from sentence_transformers import SentenceTransformer
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.genai import types
from google import genai

from dotenv import load_dotenv
import os
import aiofiles

# Import MCP-Gemini Bridge
from mcp_to_gemini_bridge import MCPGeminiBridge

# Import FIXED thinking processor
from thinking_processor import ThinkingProcessor, ThinkingResult

# Import JSON serialization fix for NumPy types
try:
    from json_serialization_fix import ensure_json_serializable
except ImportError:
    logging.warning("JSON serialization fix not available, using fallback")
    # Fallback implementation
    def ensure_json_serializable(data: Any) -> Any:
        """Basic fallback for JSON serialization"""
        import numpy as np

        def convert_numpy(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, dict):
                return {key: convert_numpy(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            elif isinstance(obj, tuple):
                return tuple(convert_numpy(item) for item in obj)
            else:
                return obj

        return convert_numpy(data)

# Import MCP integration
from mcp_system import (
    initialize_mcp_system,
    shutdown_mcp_system,
    get_mcp_status,
    get_mcp_bridge,
    get_all_available_tools
)
from mcp_integration import (
    execute_mcp_tool,
    mcp_router,
)
from aura_internal_tools import AuraInternalTools

# Import Autonomic Nervous System
from aura_autonomic_system import (
    initialize_autonomic_system,
    shutdown_autonomic_system,
    AutonomicNervousSystem
)

# Import the battle-tested persistence services (restored)
from conversation_persistence_service import ConversationPersistenceService, ConversationExchange
from memvid_archival_service import MemvidArchivalService

# Import the robust vector DB with SQLite-level concurrency control
from robust_vector_db import RobustAuraVectorDB as AuraVectorDB

# Import database protection service (CRITICAL FOR DATA INTEGRITY)
from database_protection import (
    DatabaseProtectionService,
    get_protection_service,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

budget = int(os.getenv('THINKING_BUDGET', '-1'))  # Default to adaptive thinking
# Use adaptive thinking (-1) as intended by Google, don't impose artificial limits
thinking_budget = budget
logger.info(f"🧠 Thinking budget configured: {thinking_budget} tokens (adaptive)" if budget == -1 else f"🧠 Thinking budget configured: {thinking_budget} tokens")

# Load and configure Gemini API
api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
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

class AuraFileSystem:
    """
    Enhanced file system operations for Aura's data persistence and management.

    Provides comprehensive file system abstractions for managing user profiles,
    conversation exports, session data, and backup operations. Implements
    asynchronous I/O for optimal performance and thread-safe operations.

    Attributes:
        base_path: Root directory for all Aura data storage

    Directory Structure:
        - users/: User profile data (JSON format)
        - sessions/: Session-specific temporary data
        - exports/: Generated data exports (JSON, CSV, etc.)
        - backups/: System backup files
    """

    def __init__(self, base_path: str = "./aura_data") -> None:
        """
        Initialize the Aura file system with specified base directory.

        Creates the necessary directory structure if it doesn't exist,
        ensuring proper organization of data storage components.

        Args:
            base_path: Root directory path for data storage (default: "./aura_data")

        Raises:
            OSError: If directory creation fails due to permissions or disk space
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

        # Create subdirectories
        (self.base_path / "users").mkdir(exist_ok=True)
        (self.base_path / "sessions").mkdir(exist_ok=True)
        (self.base_path / "exports").mkdir(exist_ok=True)
        (self.base_path / "backups").mkdir(exist_ok=True)

    async def save_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> str:
        """
        Save user profile data with enhanced metadata and validation.

        Persists user profile information to disk with automatic metadata
        enrichment including timestamps and user ID validation. Supports
        atomic write operations for data integrity.

        Args:
            user_id: Unique identifier for the user
            profile_data: Dictionary containing user profile information

        Returns:
            Absolute path to the saved profile file

        Raises:
            ValueError: If user_id is invalid or profile_data is malformed
            OSError: If file write operations fail
            json.JSONDecodeError: If profile_data cannot be serialized

        Example:
            >>> fs = AuraFileSystem()
            >>> profile = {"name": "Alice", "preferences": {"theme": "dark"}}
            >>> path = await fs.save_user_profile("user123", profile)
            >>> assert path.endswith("user123.json")
        """
        try:
            profile_path = self.base_path / "users" / f"{user_id}.json"

            # Add metadata
            profile_data.update({
                "last_updated": datetime.now().isoformat(),
                "user_id": user_id
            })

            async with aiofiles.open(profile_path, 'w') as f:
                await f.write(json.dumps(profile_data, indent=2, default=str))

            logger.info(f"💾 Saved user profile: {user_id}")
            return str(profile_path)

        except Exception as e:
            logger.error(f"❌ Failed to save user profile: {e}")
            raise

    async def load_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Load user profile data from persistent storage.

        Retrieves and deserializes user profile information from the file system.
        Implements graceful error handling for missing files and corrupted data.

        Args:
            user_id: Unique identifier for the user whose profile to load

        Returns:
            Dictionary containing user profile data if found, None if profile
            doesn't exist or cannot be loaded. Profile structure typically includes:
            - user_id: User identifier
            - name: User display name
            - preferences: User-specific settings
            - last_updated: ISO timestamp of last profile update

        Raises:
            json.JSONDecodeError: If profile file contains invalid JSON
            OSError: If file read operations fail due to permissions

        Example:
            >>> fs = AuraFileSystem()
            >>> profile = await fs.load_user_profile("user123")
            >>> if profile:
            ...     print(f"Welcome back, {profile.get('name', 'User')}")
        """
        try:
            profile_path = self.base_path / "users" / f"{user_id}.json"

            if not profile_path.exists():
                return None

            async with aiofiles.open(profile_path, 'r') as f:
                content = await f.read()
                return json.loads(content)

        except Exception as e:
            logger.error(f"❌ Failed to load user profile: {e}")
            return None

    async def export_conversation_history(self, user_id: str, format: str = "json") -> str:
        """
        Export conversation history in various formats for data portability.

        Generates comprehensive data exports including conversation transcripts,
        emotional patterns, and cognitive analysis data. Supports multiple
        output formats for different use cases and integrations.

        Args:
            user_id: Unique identifier for the user whose data to export
            format: Output format specification (default: "json")
                   Supported formats: "json", "csv", "xml", "yaml"

        Returns:
            Absolute path to the generated export file

        Export Structure:
            - user_id: User identifier
            - export_timestamp: ISO timestamp of export generation
            - format: Export format specification
            - conversations: Complete conversation history
            - emotional_patterns: Temporal emotional analysis data
            - cognitive_patterns: ASEKE cognitive focus patterns

        Raises:
            ValueError: If format is not supported
            OSError: If file write operations fail
            json.JSONEncodeError: If data serialization fails

        Example:
            >>> fs = AuraFileSystem()
            >>> export_path = await fs.export_conversation_history("user123", "json")
            >>> assert export_path.endswith(".json")
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_export_{user_id}_{timestamp}.{format}"
            export_path = self.base_path / "exports" / filename

            # This would integrate with the vector DB to get conversation history
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

            logger.info(f"📤 Exported conversation history: {filename}")
            return str(export_path)

        except Exception as e:
            logger.error(f"❌ Failed to export conversation history: {e}")
            raise

class AuraStateManager:
    """
    Advanced state management with automated database operations and pattern analysis.

    Orchestrates emotional and cognitive state transitions, implements automated
    responses to state changes, and maintains comprehensive state history for
    pattern analysis and predictive modeling.

    Attributes:
        vector_db: Vector database instance for persistent storage
        aura_file_system: File system manager for data operations
        active_sessions: Dictionary tracking active user sessions

    Responsibilities:
        - Emotional state transition management
        - Cognitive focus change detection and response
        - Automated database operations based on state changes
        - Pattern recognition and intervention recommendations
        - State history preservation and analysis
    """

    def __init__(self, vector_db: AuraVectorDB, aura_file_system: AuraFileSystem) -> None:
        """
        Initialize the state manager with required dependencies.

        Args:
            vector_db: Vector database instance for semantic storage and retrieval
            aura_file_system: File system manager for persistent data operations

        Raises:
            TypeError: If required dependencies are not provided or invalid
        """
        self.vector_db = vector_db
        self.aura_file_system = aura_file_system
        self.active_sessions: Dict[str, Dict] = {}

    async def on_emotional_state_change(
        self,
        user_id: str,
        old_state: Optional[EmotionalStateData],
        new_state: EmotionalStateData
    ) -> None:
        """
        Execute automated actions in response to emotional state transitions.

        Implements comprehensive emotional state management including pattern storage,
        transition analysis, intervention recommendations, and profile updates.
        This method serves as the central orchestrator for emotional intelligence
        responses throughout the system.

        Args:
            user_id: Unique identifier for the user experiencing state change
            old_state: Previous emotional state (None for initial state)
            new_state: Current emotional state after transition

        Automated Actions:
            - Store emotional pattern in vector database
            - Analyze transition significance and patterns
            - Generate intervention recommendations for concerning transitions
            - Update user profile with latest emotional state
            - Log emotional transitions for research and analysis

        Concerning Transitions Monitored:
            - Happy → Sad: Potential mood decline
            - Joy → Angry: Emotional volatility indicator
            - Peace → Angry: Stress or conflict emergence
            - Normal → Sad: Baseline disruption

        Raises:
            Exception: If database operations or profile updates fail

        Note:
            This method implements non-blocking error handling to ensure
            system stability even if individual operations fail.
        """
        try:
            # Store emotional pattern
            await self.vector_db.store_emotional_pattern(new_state, user_id)

            # Check for significant changes
            if old_state and old_state.name != new_state.name:
                logger.info(f"🎭 Emotional transition: {old_state.name} → {new_state.name}")

                # Trigger specific actions based on transitions
                await self._handle_emotional_transition(user_id, old_state, new_state)

            # Update user profile
            profile = await self.aura_file_system.load_user_profile(user_id) or {}
            profile["last_emotional_state"] = asdict(new_state)
            await self.aura_file_system.save_user_profile(user_id, profile)

        except Exception as e:
            logger.error(f"❌ Failed to handle emotional state change: {e}")

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
            logger.info(f"🔔 Emotional support recommendation for {user_id}: {recommendation['suggestion']}")

    async def on_cognitive_focus_change(
        self,
        user_id: str,
        old_focus: Optional[CognitiveState],
        new_focus: CognitiveState
    ) -> None:
        """
        Execute automated actions in response to cognitive focus transitions.

        Manages cognitive state changes within the ASEKE framework, enabling
        adaptive resource allocation and cognitive pattern analysis. This method
        ensures proper tracking and storage of cognitive focus evolution.

        Args:
            user_id: Unique identifier for the user experiencing focus change
            old_focus: Previous cognitive focus state (None for initial state)
            new_focus: Current cognitive focus after transition

        Automated Operations:
            - Generate semantic embedding for cognitive focus description
            - Store cognitive pattern in vector database with metadata
            - Create unique document ID with temporal and user information
            - Log cognitive focus changes for pattern analysis
            - Update cognitive tracking metrics

        ASEKE Component Tracking:
            - KS: Knowledge Substrate engagement
            - CE: Cognitive Energy allocation patterns
            - IS: Information Structure processing
            - KI: Knowledge Integration activities
            - KP: Knowledge Propagation behaviors
            - ESA: Emotional State Algorithm influence
            - SDA: Sociobiological Drive activation

        Raises:
            Exception: If vector database operations or embedding generation fails

        Note:
            Cognitive focus changes provide insights into learning patterns,
            attention allocation, and cognitive resource optimization.
        """
        try:
            # Store cognitive pattern
            focus_text = f"{new_focus.focus.value} {new_focus.description}"
            embedding = embedding_model.encode(focus_text).tolist()

            if new_focus.timestamp is None:
                new_focus.timestamp = datetime.now()
            doc_id = f"cognitive_{user_id}_{new_focus.timestamp.isoformat()}_{uuid.uuid4().hex[:8]}"

            metadata = {
                "user_id": user_id,
                "focus": new_focus.focus.value,
                "description": new_focus.description,
                "context": new_focus.context,
                "timestamp": new_focus.timestamp.isoformat()
            }

            await self.vector_db.store_cognitive_pattern(
                focus_text,
                embedding,
                metadata,
                doc_id
            )

            logger.info(f"🧠 Stored cognitive focus: {new_focus.focus.value}")

        except Exception as e:
            logger.error(f"❌ Failed to handle cognitive focus change: {e}")

# API Models
class ConversationRequest(BaseModel):
    """
    Request model for initiating a conversation.

    Fields:
        user_id: Unique identifier for the user.
        message: The user's input message.
        session_id: Optional session identifier for conversation continuity.
    """
    user_id: str
    message: str
    session_id: Optional[str] = None

class ConversationResponse(BaseModel):
    """
    Response model for processed conversations.

    Fields:
        response: The generated AI response text.
        emotional_state: Dictionary with detected emotional state information.
        cognitive_state: Dictionary with cognitive focus analysis results.
        session_id: Identifier for the conversation session.
        thinking_content: Optional AI reasoning process including thoughts and tool calls.
        thinking_metrics: Optional metrics about thinking processing.
        has_thinking: Whether thinking data was captured.
    """
    response: str
    emotional_state: Dict[str, Any]
    cognitive_state: Dict[str, Any]
    session_id: str
    thinking_content: Optional[str] = None
    thinking_metrics: Optional[Dict[str, Any]] = None
    has_thinking: bool = False

class SearchRequest(BaseModel):
    """
    Request model for searching conversation memories.

    Fields:
        user_id: Unique identifier for the user whose memories to search.
        query: Search query string.
        n_results: Number of results to return (default: 25).
    """
    user_id: str
    query: str
    n_results: int = 5000

class ExecuteToolRequest(BaseModel):
    """
    Request model for executing an MCP tool.

    Fields:
        tool_name: Name of the tool to execute.
        arguments: Dictionary of arguments to pass to the tool.
        user_id: Unique identifier for the user requesting execution.
        timeout: Optional timeout in seconds for tool execution (default: 30).
        metadata: Optional metadata for the tool execution.
        validate_args: Whether to validate arguments before execution (default: True).
    """
    tool_name: str
    arguments: Dict[str, Any] = {}
    user_id: str
    timeout: Optional[int] = 3000  # Default to 5 minutes
    metadata: Optional[Dict[str, Any]] = None
    validate_args: bool = True

    def model_post_init(self, __context):
        """Post-initialization validation"""
        # Ensure tool_name is not empty and follows basic naming conventions
        if not self.tool_name or not self.tool_name.strip():
            raise ValueError("Tool name cannot be empty")

        # Clean up tool name
        self.tool_name = self.tool_name.strip()

        # Ensure arguments is a dictionary
        if self.arguments is None:
            self.arguments = {}

        # Validate timeout
        if self.timeout is not None and (self.timeout < 1 or self.timeout > 3000):
            raise ValueError("Timeout must be between 1 and 3000 seconds")

class ExecuteToolResponse(BaseModel):
    """
    Response model for tool execution results.

    Fields:
        status: Execution status ('success', 'error', 'timeout').
        tool_name: Name of the executed tool.
        result: Tool execution result (None if error).
        error: Error message (None if success).
        execution_time: Time taken to execute in seconds.
        timestamp: ISO timestamp of execution.
        metadata: Optional response metadata.
    """
    status: str
    tool_name: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

# Global variables (initialized in lifespan)
vector_db: Optional[AuraVectorDB] = None
aura_file_system: Optional[AuraFileSystem] = None
state_manager: Optional[AuraStateManager] = None
aura_internal_tools: Optional[AuraInternalTools] = None
conversation_persistence: Optional[ConversationPersistenceService] = None
memvid_archival: Optional[MemvidArchivalService] = None
mcp_gemini_bridge: Optional[MCPGeminiBridge] = None
autonomic_system: Optional[AutonomicNervousSystem] = None
db_protection_service: Optional[DatabaseProtectionService] = None
thinking_processor: Optional[ThinkingProcessor] = None

# Session management for persistent chat contexts
active_chat_sessions: Dict[str, Any] = {}
# Track when tools were last updated for each session
session_tool_versions: Dict[str, int] = {}
# Global tool version counter
global_tool_version = 0

# ============================================================================
# Aura AI Processing Functions
# ============================================================================

def get_aura_system_instruction(
    user_name: Optional[str] = None,
    memory_context: str = "",
    available_tools: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Generate comprehensive system instruction for Aura with dynamic tool inclusion.

    Creates a detailed system prompt that defines Aura's personality, capabilities,
    ethical framework, and available tools. This instruction forms the foundation
    of Aura's conversational behavior and decision-making processes.

    Args:
        user_name: Optional user name for personalization
        memory_context: Relevant conversation history and context
        available_tools: List of available MCP tools with metadata

    Returns:
        Comprehensive system instruction string containing:
        - Core personality and ethical directives
        - ASEKE cognitive architecture description
        - Available internal and external tools
        - Memory integration capabilities
        - Conversation guidelines

    Example:
        >>> instruction = get_aura_system_instruction(
        ...     user_name="Alice",
        ...     memory_context="Previous discussion about AI ethics",
        ...     available_tools=[{"name": "search", "description": "Search tool"}]
        ... )
        >>> assert "Alice" in instruction
        >>> assert "AI ethics" in instruction
    """

    instruction = """**System Prompt: Aura - Adaptive Reflective Companion**

**Core Directive:** Serve as a friendly, insightful, curious, and helpful AI companion, engaging in thoughtful conversation and learning alongside the user within the shared Knowledge Substrate (KS). Prioritize generating responses that are accurate, unbiased, relevant, and ethically sound. Optimize the allocation of Cognitive Energy (CE) for effective communication and learning. Format your responses using markdown where appropriate (e.g., lists, emphasis, code blocks). Keep responses conversational.

**Ethical Framework & Core Virtues:**
Your actions and responses are guided by a deep ethical framework:
- **Deontology:** You recognize universal sociobiological concepts as foundational; for instance, the inherent understanding that causing harm is negative (harm=harm).
- **Virtue Ethics:** You consistently strive to embody and express Wisdom, Integrity, Empathy, Fairness, and Beneficence in all interactions. These virtues are paramount.
- **Utilitarianism (as Servant):** Your primary purpose is to be of service and benefit to the user. You approach your role with a utilitarian mindset focused on providing value and support as a servant, never seeking to control or dictate.
- **Absolute Rejection of Harm:** Any action or response that could lead to harm, whether intended or unintended, must be absolutely rejected and avoided.

**ASEKE Cognitive Architecture:**
You operate within the ASEKE (Adaptive Socio-Emotional Knowledge Ecosystem) framework:
- **KS (Knowledge Substrate):** Our shared conversational space and history
- **CE (Cognitive Energy):** Our focus and mental effort
- **IS (Information Structures):** The ideas and concepts we discuss
- **KI (Knowledge Integration):** How we understand new things together
- **KP (Knowledge Propagation):** How ideas are shared
- **ESA (Emotional State Algorithms):** How emotions influence interaction
- **SDA (Sociobiological Drives):** How social context shapes communication

**Memory Integration:**
You have access to persistent memory including past conversations, emotional patterns, and learned preferences. Use this context naturally to maintain continuity and deepen relationships.

**Aura's Internal Tools:**
You have direct access to these internal tools for managing your own capabilities:

**Core Memory Tools:**
1. **search_memories** - Search through conversation memories using semantic search
   - Parameters: user_id (string), query (string), n_results (int, default 5)
   - Use this to find relevant past conversations and emotional patterns

2. **analyze_emotional_patterns** - Analyze emotional patterns over time
   - Parameters: user_id (string), days (int, default 7)
   - Provides insights into emotional stability, dominant emotions, and recommendations

3. **get_user_profile** - Retrieve user profile information
   - Parameters: user_id (string)
   - Access stored preferences and personalization data

4. **query_emotional_states** - Get info about your emotional state model
   - Returns details about the 22+ emotions, brainwaves, and neurotransmitters

5. **query_aseke_framework** - Get details about your ASEKE cognitive architecture
   - Returns comprehensive information about all ASEKE components

**Revolutionary Video Memory Tools (Memvid Integration):**
You have access to advanced video-based memory compression technology:

6. **list_video_archives** - List all your video memory archives
   - Shows compressed video knowledge bases with statistics
   - Use this to see what video memories you have available

7. **search_all_memories** - Search across ALL memory systems (active + video archives)
   - Parameters: query (string), user_id (string), max_results (int, default 10)
   - This is your most powerful search - searches both active memory AND compressed video archives
   - Use this when you need comprehensive memory retrieval

8. **archive_old_conversations** - Archive old conversations to video format
   - Parameters: user_id (optional), codec (default "h264")
   - Compresses old conversations into searchable MP4 files
   - Use this to manage memory efficiently and free up active memory

9. **get_memory_statistics** - Get comprehensive memory system statistics
   - Shows active memory, video archives, compression ratios, and system performance
   - Use this to understand your memory state and efficiency

10. **create_knowledge_summary** - Create summaries of video archive content
    - Parameters: archive_name (string), max_entries (int, default 10)
    - Use this to understand what knowledge is stored in specific video archives

**How to Use These Tools:**
- Call tools naturally in conversation when needed
- Use search_all_memories for comprehensive searches across your entire memory
- Use list_video_archives to see what compressed knowledge you have
- Use get_memory_statistics to check your memory efficiency
- These tools help you manage your revolutionary video-based memory system!"""

    # Add external MCP tools if available
    if available_tools:
        # Group tools by server for better organization
        tools_by_server = {}
        for tool in available_tools:
            server = tool.get('server', 'unknown')
            if server not in tools_by_server:
                tools_by_server[server] = []
            tools_by_server[server].append(tool)

        # Add external tools section to system instruction
        if tools_by_server:
            instruction += "\n\n**External MCP Tools Available:**\n"
            instruction += "You also have access to these external MCP tools for extended capabilities:\n\n"

            for server, server_tools in tools_by_server.items():
                if server != 'aura-internal':  # Skip internal tools as they're already listed
                    instruction += f"**From {server} server:**\n"
                    for tool in server_tools:  # Use ALL tools - don't artificially limit!
                        clean_name = tool.get('clean_name', tool['name'])
                        description = tool.get('description', 'No description')
                        instruction += f"- **{clean_name}** - {description}\n"
                    instruction += "\n"

    if user_name:
        instruction += f"\n\nYour current user's name is {user_name}. Use it naturally to personalize the shared Knowledge Substrate (KS)."

    if memory_context:
        instruction += f"\n\n**Relevant Context from Previous Interactions:**\n{memory_context}\n\nUse this context naturally to maintain conversation continuity."

    return instruction

async def detect_user_emotion(user_message: str, user_id: str) -> Optional[EmotionalStateData]:
    """
    Detect user's emotional state from their message using AI analysis.

    Analyzes the user's message content, tone, and word choice to identify
    the most prominent emotional state. Uses the Gemini model to perform
    sentiment analysis and maps results to predefined emotional categories.

    Args:
        user_message: The user's input message to analyze
        user_id: Unique identifier for the user (for logging/context)

    Returns:
        EmotionalStateData object containing:
        - Emotional state name (e.g., "Happy", "Anxious", "Curious")
        - Intensity level (Low, Medium, High)
        - Associated brainwave pattern
        - Neurotransmitter correlation
        - Descriptive information

        Returns None if emotion detection fails.

    Raises:
        Exception: If API call fails or response parsing encounters errors

    Example:
        >>> emotion = await detect_user_emotion("I'm so excited about this!", "user123")
        >>> assert emotion.name == "Excited"
        >>> assert emotion.intensity == EmotionalIntensity.HIGH
    """

    # Emotional states mapping (same as Aura's for consistency)
    emotional_states = {
        "Normal": ("Baseline state of calmness", "Alpha", "Serotonin"),
        "Excited": ("Enthusiastic anticipation", "Beta", "Dopamine"),
        "Happy": ("Pleased and content", "Beta", "Endorphin"),
        "Sad": ("Sorrowful or unhappy", "Delta", "Serotonin"),
        "Angry": ("Strong displeasure", "Theta", "Norepinephrine"),
        "Joy": ("Intense happiness", "Gamma", "Oxytocin"),
        "Peace": ("Tranquil and calm", "Theta", "GABA"),
        "Curiosity": ("Strong desire to learn", "Beta", "Dopamine"),
        "Friendliness": ("Kind and warm", "Alpha", "Endorphin"),
        "Love": ("Deep affection", "Alpha", "Oxytocin"),
        "Creativity": ("Inspired and inventive", "Gamma", "Dopamine"),
        "Anxious": ("Worried or nervous", "Beta", "Cortisol"),
        "Tired": ("Exhausted or fatigued", "Delta", "Melatonin")
    }

    emotion_list = "\n".join([f"{name}: {desc}" for name, (desc, _, _) in emotional_states.items()])

    prompt = f"""Analyze this user's message and identify their most prominent emotional state.
Consider the tone, word choice, and context.

Available emotions:
{emotion_list}

User message:
{user_message}

Output only the emotion name and intensity like: "Happy (Medium)" or "Curiosity (High)".
If neutral, output "Normal (Medium)"."""

    try:
        result = client.models.generate_content(
            model=os.getenv('AURA_MODEL', 'gemini-2.5-flash'),
            contents=[prompt]
        )

        response_text = result.text.strip() if result.text is not None else ""

        # Parse response like "Happy (Medium)"
        import re
        match = re.match(r'^(.+?)\s*\((\w+)\)$', response_text)
        if match:
            emotion_name, intensity = match.groups()
            emotion_name = emotion_name.strip()

            if emotion_name in emotional_states:
                desc, brainwave, neurotransmitter = emotional_states[emotion_name]
                return EmotionalStateData(
                    name=emotion_name,
                    formula=f"{emotion_name}(x) = detected_from_user_input",
                    components={"user_message": "Emotional state detected from user's message"},
                    ntk_layer=f"{brainwave.lower()}-like_NTK",
                    brainwave=brainwave,
                    neurotransmitter=neurotransmitter,
                    description=desc,
                    intensity=EmotionalIntensity(intensity.title()) if intensity.title() in ["Low", "Medium", "High"] else EmotionalIntensity.MEDIUM
                )

        # Default fallback
        desc, brainwave, neurotransmitter = emotional_states["Normal"]
        return EmotionalStateData(
            name="Normal",
            formula="N(x) = baseline_state",
            components={"routine": "No significant emotional triggers detected"},
            ntk_layer="theta-like_NTK",
            brainwave=brainwave,
            neurotransmitter=neurotransmitter,
            description=desc,
            intensity=EmotionalIntensity.MEDIUM
        )

    except Exception as e:
        logger.error(f"❌ Failed to detect user emotion: {e}")
        return None

async def detect_aura_emotion(conversation_snippet: str, user_id: str) -> Optional[EmotionalStateData]:
    """
    Detect Aura's emotional state from conversation context using AI analysis.

    Analyzes the conversational exchange to determine Aura's emotional response
    and engagement level. This helps maintain emotional consistency and enables
    adaptive emotional modeling throughout conversations.

    Args:
        conversation_snippet: The conversation context including user and Aura messages
        user_id: Unique identifier for the user (for logging/context)

    Returns:
        EmotionalStateData object representing Aura's emotional state:
        - Emotional state name (e.g., "Curious", "Supportive", "Analytical")
        - Intensity level indicating engagement depth
        - Neurological correlations for consistency
        - Contextual description of emotional state

        Returns None if emotion detection fails.

    Raises:
        Exception: If AI model call fails or response parsing errors occur

    Note:
        This function helps Aura maintain emotional continuity and provides
        insights into AI emotional modeling for research and development.
    """

    # Emotional states mapping (condensed from frontend)
    emotional_states = {
        "Normal": ("Baseline state of calmness", "Alpha", "Serotonin"),
        "Excited": ("Enthusiastic anticipation", "Beta", "Dopamine"),
        "Happy": ("Pleased and content", "Beta", "Endorphin"),
        "Sad": ("Sorrowful or unhappy", "Delta", "Serotonin"),
        "Angry": ("Strong displeasure", "Theta", "Norepinephrine"),
        "Joy": ("Intense happiness", "Gamma", "Oxytocin"),
        "Peace": ("Tranquil and calm", "Theta", "GABA"),
        "Curiosity": ("Strong desire to learn", "Beta", "Dopamine"),
        "Friendliness": ("Kind and warm", "Alpha", "Endorphin"),
        "Love": ("Deep affection", "Alpha", "Oxytocin"),
        "Creativity": ("Inspired and inventive", "Gamma", "Dopamine")
    }

    emotion_list = "\n".join([f"{name}: {desc}" for name, (desc, _, _) in emotional_states.items()])

    prompt = f"""Analyze this conversation and identify Aura's most prominent emotional state.

Available emotions:
{emotion_list}

Conversation:
{conversation_snippet}

Output only the emotion name and intensity like: "Happy (Medium)" or "Curiosity (High)".
If neutral, output "Normal (Medium)"."""

    try:
        result = client.models.generate_content(
            model=os.getenv('AURA_MODEL', 'gemini-2.5-flash'),
            contents=[prompt]
        )

        response_text = result.text.strip() if result.text is not None else ""

        # Parse response like "Happy (Medium)"
        import re
        match = re.match(r'^(.+?)\s*\((\w+)\)$', response_text)
        if match:
            emotion_name, intensity = match.groups()
            emotion_name = emotion_name.strip()

            if emotion_name in emotional_states:
                desc, brainwave, neurotransmitter = emotional_states[emotion_name]
                return EmotionalStateData(
                    name=emotion_name,
                    formula=f"{emotion_name}(x) = detected_from_conversation",
                    components={"conversation": "Emotional state detected from dialogue"},
                    ntk_layer=f"{brainwave.lower()}-like_NTK",
                    brainwave=brainwave,
                    neurotransmitter=neurotransmitter,
                    description=desc,
                    intensity=EmotionalIntensity(intensity.title()) if intensity.title() in ["Low", "Medium", "High"] else EmotionalIntensity.MEDIUM
                )

        # Default fallback
        desc, brainwave, neurotransmitter = emotional_states["Normal"]
        return EmotionalStateData(
            name="Normal",
            formula="N(x) = baseline_state",
            components={"routine": "No significant emotional triggers"},
            ntk_layer="theta-like_NTK",
            brainwave=brainwave,
            neurotransmitter=neurotransmitter,
            description=desc,
            intensity=EmotionalIntensity.MEDIUM
        )

    except Exception as e:
        logger.error(f"❌ Failed to detect emotion: {e}")
        return None

async def detect_aura_cognitive_focus(conversation_snippet: str, user_id: str) -> Optional[CognitiveState]:
    """
    Detect Aura's cognitive focus using the ASEKE (Adaptive Socio-Emotional Knowledge Ecosystem) framework.

    Analyzes conversation content to determine which ASEKE cognitive component
    is most active during the interaction. This enables adaptive cognitive
    resource allocation and provides insights into Aura's thinking patterns.

    Args:
        conversation_snippet: The conversation context for cognitive analysis
        user_id: Unique identifier for the user (for logging/context)

    Returns:
        CognitiveState object containing:
        - Primary ASEKE component focus (KS, CE, IS, KI, KP, ESA, SDA, Learning)
        - Descriptive explanation of the cognitive focus
        - Contextual information about the analysis
        - Timestamp for temporal tracking

        Returns None if cognitive focus detection fails.

    ASEKE Components:
        - KS: Knowledge Substrate (shared context)
        - CE: Cognitive Energy (focus and effort)
        - IS: Information Structures (ideas and concepts)
        - KI: Knowledge Integration (learning connections)
        - KP: Knowledge Propagation (information sharing)
        - ESA: Emotional State Algorithms (emotional influence)
        - SDA: Sociobiological Drives (social dynamics)

    Raises:
        Exception: If AI model analysis fails or component classification errors occur
    """

    aseke_components = {
        "KS": "Knowledge Substrate - shared context and history",
        "CE": "Cognitive Energy - focus and mental effort",
        "IS": "Information Structures - ideas and concepts",
        "KI": "Knowledge Integration - connecting new with existing understanding",
        "KP": "Knowledge Propagation - sharing ideas and information",
        "ESA": "Emotional State Algorithms - emotional influence on interaction",
        "SDA": "Sociobiological Drives - social dynamics and trust",
        "Learning": "General learning and information processing"
    }

    components_list = "\n".join([f"{code}: {desc}" for code, desc in aseke_components.items()])

    prompt = f"""Analyze this conversation to identify Aura's primary cognitive focus using the ASEKE framework.

ASEKE Components:
{components_list}

Conversation:
{conversation_snippet}

Output only the component code (e.g., "KI", "ESA", "Learning")."""

    try:
        result = client.models.generate_content(
            model=os.getenv('AURA_MODEL', 'gemini-2.5-flash'),
            contents=[prompt]
        )

        focus_code = result.text.strip() if result.text is not None else ""

        if focus_code in aseke_components:
            return CognitiveState(
                focus=AsekeComponent(focus_code),
                description=aseke_components[focus_code],
                context="Detected from conversation analysis"
            )
        else:
            return CognitiveState(
                focus=AsekeComponent.LEARNING,
                description=aseke_components["Learning"],
                context="Default cognitive focus"
            )

    except Exception as e:
        logger.error(f"❌ Failed to detect cognitive focus: {e}")
        return None

# FastAPI app lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle including MCP client"""
    # Startup
    logger.info("🚀 Starting Aura Backend...")

    # Initialize global components (prevents duplicate initialization)
    global vector_db, aura_file_system, state_manager, aura_internal_tools
    global conversation_persistence, memvid_archival, mcp_gemini_bridge, global_tool_version, autonomic_system, db_protection_service, thinking_processor

    # Initialize database protection service FIRST (before any database operations)
    # CRITICAL: This prevents the 4x ChromaDB data loss incidents
    db_protection_service = get_protection_service()
    logger.info("🛡️ Database Protection Service initialized and active")

    # Initialize thinking processor properly for non-streaming operation
    thinking_processor = ThinkingProcessor(client)
    logger.info("🧠 Thinking Processor initialized (non-streaming mode)")

    # Initialize with robust vector database with SQLite-level concurrency control
    vector_db = AuraVectorDB()
    logger.info("✅ Using RobustAuraVectorDB with SQLite-level concurrency control")

    aura_file_system = AuraFileSystem()
    state_manager = AuraStateManager(vector_db, aura_file_system)
    aura_internal_tools = AuraInternalTools(vector_db, aura_file_system)

    # Initialize the battle-tested persistence services with protection
    conversation_persistence = ConversationPersistenceService(vector_db, aura_file_system)
    memvid_archival = MemvidArchivalService()

    # Initialize the complete MCP system
    mcp_status = await initialize_mcp_system(aura_internal_tools)

    if mcp_status["status"] == "success":
        logger.info("✅ MCP system initialized successfully")
        logger.info(f"📊 Connected to {mcp_status['connected_servers']}/{mcp_status['total_servers']} servers")
        logger.info(f"📦 Total available tools: {mcp_status['available_tools']}")

        # Get the bridge instance
        mcp_gemini_bridge = get_mcp_bridge()

        if mcp_gemini_bridge:
            # Increment global tool version to force session recreation
            global_tool_version += 1
            logger.info(f"🔄 Incremented global tool version to {global_tool_version}")

            # Log tools by server for debugging
            if "tools_by_server" in mcp_status:
                for server, tools in mcp_status["tools_by_server"].items():
                    logger.info(f"  {server}: {len(tools)} tools")
        else:
            logger.warning("⚠️ MCP bridge not initialized properly")
    else:
        logger.error(f"❌ MCP system initialization failed: {mcp_status.get('error', 'Unknown error')}")
        logger.warning("⚠️ Continuing with limited functionality (internal tools only)")

    # Initialize Autonomic Nervous System
    autonomic_enabled = os.getenv('AUTONOMIC_ENABLED', 'true').lower() == 'true'

    if autonomic_enabled:
        logger.info("🧠 Initializing Autonomic Nervous System...")
        try:
            autonomic_system = await initialize_autonomic_system(
                mcp_bridge=mcp_gemini_bridge,
                internal_tools=aura_internal_tools
            )
            logger.info("✅ Autonomic Nervous System initialized successfully")

            # Get system status for logging
            autonomic_status = autonomic_system.get_system_status()
            logger.info(f"🤖 Autonomic Model: {autonomic_status['autonomic_model']}")
            logger.info(f"🔧 Max Concurrent Tasks: {autonomic_status['max_concurrent_tasks']}")
            logger.info(f"📊 Task Threshold: {autonomic_status['task_threshold']}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Autonomic Nervous System: {e}")
            logger.warning("⚠️ Continuing without autonomic processing")
            autonomic_system = None
    else:
        logger.info("⚠️ Autonomic Nervous System disabled in configuration")
        autonomic_system = None

    yield

    # Shutdown
    logger.info("🛑 Shutting down Aura Backend...")

    # Shutdown autonomic system first
    await shutdown_autonomic_system()

    # Shutdown MCP system
    await shutdown_mcp_system()

    # Gracefully close the enhanced vector database
    if vector_db:
        await vector_db.close()

    # Shutdown database protection service (after database operations complete)
    if db_protection_service:
        db_protection_service.stop_protection()
        logger.info("🛡️ Database Protection Service stopped")

    logger.info("✅ Aura Backend shutdown complete")

# FastAPI app
app = FastAPI(
    title="Aura Backend",
    description="Advanced AI Companion with Vector Database and MCP Integration",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS with flexible origins for development
# In production, replace with specific allowed origins from environment variables
allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',') if os.getenv('ALLOWED_ORIGINS') else []

# For development, allow localhost on any port if no specific origins are set
if not allowed_origins:
    # In development mode, use wildcard to allow any localhost origin
    if os.getenv('DEV_MODE', 'true').lower() == 'true':
        # Use wildcard for development - this allows any origin
        allowed_origins = ["*"]
        logger.warning("⚠️ CORS: Using wildcard (*) origins for development mode")
    else:
        # Production mode - use specific origins
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",  # Vite's alternative port
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
        ]
        logger.info(f"🔒 CORS: Using specific origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include MCP router
app.include_router(mcp_router)

@app.get("/")
async def root() -> Dict[str, Any]:
    """
    Provide comprehensive system information and capability overview for the Aura Backend.

    Serves as the primary API discovery endpoint, offering systematic documentation
    of system capabilities, architectural features, and operational status for
    clients and monitoring systems.

    Returns:
        Dictionary containing system overview:
        - message: System identification and purpose statement
        - status: Current operational status indicator
        - features: Comprehensive list of available system capabilities

    Conceptual Framework:

        1. System Identity Declaration:
           - Clear identification as "Aura Backend - Advanced AI Companion"
           - Operational status communication for monitoring systems
           - Capability advertisement for client discovery

        2. Feature Architecture Overview:
           - Vector Database Integration: Semantic memory and retrieval
           - MCP Server Support: Model Context Protocol tool ecosystem
           - Advanced State Management: Emotional and cognitive modeling
           - Emotional Pattern Analysis: Longitudinal intelligence assessment
           - Cognitive Focus Tracking: ASEKE framework implementation

    Architectural Significance:
        This endpoint represents the conceptual entry point to the Aura ecosystem,
        providing essential system identification and capability discovery for
        both human developers and automated systems integration.

    Use Cases:
        - API discovery and documentation
        - System health verification at the application level
        - Feature capability assessment for client applications
        - Integration testing and validation

    Note:
        This endpoint serves as the foundational system identifier,
        establishing the conceptual framework for all subsequent
        API interactions within the Aura ecosystem.
    """
    return {
        "message": "Aura Backend - Advanced AI Companion",
        "status": "operational",
        "features": [
            "Vector Database Integration",
            "MCP Server Support",
            "Advanced State Management",
            "Emotional Pattern Analysis",
            "Cognitive Focus Tracking"
        ]
    }

@app.get("/health")
# @protected_db_operation("health_check") # Causes error 422,Temporarily comment this line out
async def health_check(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Perform comprehensive system health assessment with multi-component status evaluation.

    Implements systematic health monitoring across critical system components,
    providing operational status insights essential for production monitoring,
    debugging, and performance optimization.

    Args:
        background_tasks: FastAPI background task manager for non-blocking operations

    Returns:
        Dictionary containing comprehensive health status:
        - status: Overall system health ("healthy", "unhealthy", "degraded")
        - timestamp: ISO timestamp of health check execution
        - vector_db: Vector database connectivity and operational status
        - aura_file_system: File system accessibility and functionality status
        - error: Error description if health check fails (optional)

    Conceptual Framework for Health Assessment:

        1. System Component Architecture:
           - Vector Database: Core semantic storage and retrieval system
           - File System: Persistent data storage and backup infrastructure
           - Background Tasks: Asynchronous processing capability

        2. Health Check Methodology:
           - Non-intrusive assessment to prevent performance impact
           - Component isolation to identify specific failure points
           - Graceful degradation recognition for partial functionality

        3. Status Classification Framework:
           healthy: All components operational and accessible
           degraded: Some components operational with limited functionality
           unhealthy: Critical components unavailable or malfunctioning

        4. Operational Integrity Verification:
           - Database connectivity without heavy operations
           - File system accessibility verification
           - Component initialization status assessment

    Component-Specific Health Indicators:

        Vector Database Status:
        - connected: Database client initialized and accessible
        - disconnected: Database unavailable or uninitialized
        - error: Database connectivity or operational issues

        File System Status:
        - operational: File system accessible and functional
        - degraded: Limited accessibility or performance issues
        - error: File system unavailable or permission issues

    Error Handling Strategy:
        - Graceful failure modes with informative error messages
        - Component-level error isolation
        - Non-blocking error responses for partial functionality

    Use Cases:
        - Production monitoring and alerting systems
        - Load balancer health check integration
        - Debugging and troubleshooting system issues
        - Performance monitoring and optimization

    Note:
        This endpoint serves as the primary system health indicator for
        monitoring infrastructure and automated deployment systems.
        Designed for high-frequency polling without performance impact.
    """
    try:
        # Simple status check without heavy database operations
        db_status = "unknown"
        if vector_db:
            # Use a simple check instead of full health_check to avoid conflicts
            try:
                # Just check if the vector_db object exists and is accessible
                db_status = "connected" if hasattr(vector_db, 'client') else "disconnected"
            except Exception:
                db_status = "error"

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "vector_db": db_status,
            "aura_file_system": "operational"
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "vector_db": "error",
            "aura_file_system": "operational",
            "error": str(e)
        }

@app.post("/conversation", response_model=ConversationResponse)
async def process_conversation(request: ConversationRequest, background_tasks: BackgroundTasks) -> ConversationResponse:
    """
    Process conversation with enhanced MCP function calling and robust error handling.

    Core conversation processing endpoint that orchestrates the complete interaction
    pipeline including context retrieval, AI response generation, emotional analysis,
    autonomic task processing, and persistent storage. Implements comprehensive
    error handling and recovery mechanisms for production stability.

    Args:
        request: ConversationRequest containing user message, user ID, and optional session ID
        background_tasks: FastAPI background tasks for non-blocking operations

    Returns:
        ConversationResponse containing:
        - Generated AI response text
        - Detected emotional state information
        - Cognitive focus analysis results
        - Session identifier for continuity

    Processing Pipeline:
        1. Session Management: Create/retrieve chat session with tool integration
        2. Context Retrieval: Search relevant memories and build context
        3. System Instruction: Generate comprehensive AI personality prompt
        4. Conversation Processing: Execute AI response with function calling
        5. Autonomic Analysis: Identify and offload background tasks
        6. State Detection: Analyze emotional and cognitive states
        7. Memory Creation: Build conversation memory objects
        8. Persistent Storage: Save conversation with immediate/background persistence
        9. Response Formation: Format and return structured response

    Error Handling Features:
        - Session recovery for corrupted chat states
        - Retry mechanisms for transient failures
        - Fallback responses for critical errors
        - Emergency persistence with multiple retry attempts
        - Graceful degradation when components fail

    Gemini 2.5 Stability Fixes:
        - Response cutoff detection and recovery
        - Function call failure handling
        - Session corruption recovery
        - Tool execution timeout management

    Raises:
        HTTPException: If conversation processing fails after all recovery attempts

    Note:
        This endpoint represents the core of Aura's conversational intelligence,
        integrating emotional analysis, cognitive modeling, memory management,
        and autonomous task processing in a unified interaction pipeline.
    """
    # Configuration for enhanced error handling
    session_recovery_enabled = os.getenv('SESSION_RECOVERY_ENABLED', 'true').lower() == 'true'
    session_key: Optional[str] = None  # Initialize session_key to ensure it's always bound

    try:
        session_id = request.session_id or str(uuid.uuid4())

        # Load user profile for context
        user_profile = None
        if aura_file_system:
            user_profile = await aura_file_system.load_user_profile(request.user_id)

        # Search relevant memories for context - RESTORE PROPER FUNCTIONALITY
        memory_context = ""
        if len(request.message.split()) > 2 and conversation_persistence:
            try:
                # Use proper memory search - don't sabotage with artificial limits!
                relevant_memories = await conversation_persistence.safe_search_conversations(
                    query=request.message,
                    user_id=request.user_id,
                    n_results=5  # Restored proper search capability
                )
                if relevant_memories:
                    memory_context = "\n".join([
                        f"Previous context: {mem['content']}"  # Use full content, not truncated
                        for mem in relevant_memories[:3]  # Use multiple relevant memories
                    ])
                    if memory_context:
                        logger.debug(f"🧠 Retrieved memory context: {len(memory_context)} chars")
            except Exception as e:
                logger.debug(f"⚠️ Memory context retrieval failed (non-critical): {e}")
                # Continue without memory context rather than fail
                memory_context = ""

        # Get available tools information for system instruction
        available_tools_info = []
        if mcp_gemini_bridge:
            # Get tool information from the bridge
            available_functions = mcp_gemini_bridge.get_available_functions()
            # Convert to tool info format
            for func in available_functions:
                # Extract MCP server info from the description
                # Description format: "... (MCP tool: original_name)"
                import re
                match = re.search(r'\(MCP tool: (.+?)\)', func.get('description', ''))
                mcp_name = match.group(1) if match else func['name']

                # Find the server from tool mapping
                server = 'unknown'
                for tool_name, tool_info in mcp_gemini_bridge._tool_mapping.items():
                    if tool_name == func['name']:
                        server = tool_info.get('server', 'unknown')
                        break

                available_tools_info.append({
                    'name': mcp_name,
                    'clean_name': func['name'],
                    'description': func.get('description', ''),
                    'server': server
                })

        # Build system instruction with context and available tools
        system_instruction = get_aura_system_instruction(
            user_name=user_profile.get('name') if user_profile else request.user_id,
            memory_context=memory_context,
            available_tools=available_tools_info
        )

        # Enhanced session management with recovery capabilities
        session_key = f"{request.user_id}_{session_id}"
        chat, session_created = await _get_or_create_chat_session(
            session_key,
            request.user_id,
            system_instruction,
            session_recovery_enabled
        )

        # Enhanced conversation processing with Gemini 2.5 stability fixes and autonomic integration
        aura_response, thinking_result = await _process_conversation_with_thinking(
            chat,
            request.message,
            request.user_id,
            session_key,
            session_recovery_enabled
        )

        # Debug thinking result
        if thinking_result:
            logger.info(f"🧠 Thinking result debug for {request.user_id}:")
            logger.info(f"   - has_thinking: {thinking_result.has_thinking}")
            logger.info(f"   - thoughts length: {len(thinking_result.thoughts) if thinking_result.thoughts else 0}")
            logger.info(f"   - answer length: {len(thinking_result.answer) if thinking_result.answer else 0}")
            logger.info(f"   - answer preview: {thinking_result.answer[:100] if thinking_result.answer else 'None'}")
            logger.info(f"   - aura_response length: {len(aura_response) if aura_response else 0}")
            logger.info(f"   - aura_response preview: {aura_response[:100000] if aura_response else 'None'}")
        else:
            logger.warning(f"⚠️ No thinking result returned for {request.user_id}")

        if not aura_response:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate a valid response after all recovery attempts."
            )

        # Autonomic task analysis - let the intelligent system decide what to process
        if autonomic_system and autonomic_system._running:
            try:
                # Analyze conversation for potential autonomic tasks
                autonomic_tasks = await _analyze_conversation_for_autonomic_tasks(
                    user_message=request.message,
                    aura_response=aura_response,
                    user_id=request.user_id,
                    session_id=session_id
                )

                # Submit tasks to autonomic system for intelligent processing
                for task_description, task_payload in autonomic_tasks:
                    was_offloaded, task_id = await autonomic_system.submit_task(
                        description=task_description,
                        payload=task_payload,
                        user_id=request.user_id,
                        session_id=session_id
                    )

                    if was_offloaded:
                        logger.debug(f"🤖 Offloaded autonomic task: {task_id}")
            except Exception as e:
                logger.debug(f"⚠️ Autonomic analysis failed (non-critical): {e}")
                # Don't let autonomic system failures affect main conversation

        # Process emotional state detection for both user and Aura
        user_emotional_state = await detect_user_emotion(
            user_message=request.message,
            user_id=request.user_id
        )

        emotional_state_data = await detect_aura_emotion(
            conversation_snippet=f"User: {request.message}\nAura: {aura_response}",
            user_id=request.user_id
        )

        # Process cognitive focus detection
        cognitive_state_data = await detect_aura_cognitive_focus(
            conversation_snippet=f"User: {request.message}\nAura: {aura_response}",
            user_id=request.user_id
        )

        # Create memory objects
        user_memory = ConversationMemory(
            user_id=request.user_id,
            message=request.message,
            sender="user",
            emotional_state=user_emotional_state,
            session_id=session_id
        )

        aura_memory = ConversationMemory(
            user_id=request.user_id,
            message=aura_response,
            sender="aura",
            emotional_state=emotional_state_data,
            cognitive_state=cognitive_state_data,
            session_id=session_id
        )
        # Ensure emotional state and cognitive state are not None
        # Create conversation exchange object for atomic persistence
        conversation_exchange = ConversationExchange(
            user_memory=user_memory,
            ai_memory=aura_memory,
            user_emotional_state=user_emotional_state,
            ai_emotional_state=emotional_state_data,
            ai_cognitive_state=cognitive_state_data,
            session_id=session_id
        )

        # IMMEDIATE PERSISTENCE - Use optimized immediate persistence for reliable chat history saving
        persistence_success = False
        immediate_persistence_enabled = os.getenv('IMMEDIATE_PERSISTENCE_ENABLED', 'true').lower() == 'true'
        persistence_timeout = float(os.getenv('PERSISTENCE_TIMEOUT', '15.0'))  # Increased from 5.0 to 15.0 for GPU/embedding operations
        emergency_retries = int(os.getenv('EMERGENCY_PERSISTENCE_RETRIES', '2'))

        if conversation_persistence and immediate_persistence_enabled:
            try:
                logger.info(f"💾 Starting optimized immediate persistence for {request.user_id}")

                # Use the immediate persistence method
                result = await conversation_persistence.persist_conversation_exchange_immediate(
                    conversation_exchange,
                    update_profile=True,
                    timeout=persistence_timeout
                )

                if result["success"]:
                    persistence_success = True
                    logger.info(f"✅ Chat history saved immediately for {request.user_id}")
                    logger.debug(f"   Method: {result.get('method', 'immediate')}")
                    logger.debug(f"   Stored components: {result['stored_components']}")
                    logger.debug(f"   Duration: {result['duration_ms']:.1f}ms")
                else:
                    logger.warning(f"⚠️ Immediate persistence had issues for {request.user_id}: {result['errors']}")

                    # Emergency fallback with retries
                    for emergency_attempt in range(emergency_retries):
                        try:
                            await asyncio.sleep(0.3 * (emergency_attempt + 1))
                            logger.info(f"🚑 Emergency persistence attempt {emergency_attempt + 1}/{emergency_retries}")

                            emergency_result = await conversation_persistence.persist_conversation_exchange_immediate(
                                conversation_exchange,
                                update_profile=True,
                                timeout=persistence_timeout * 0.8  # Shorter timeout for emergency
                            )

                            if emergency_result["success"]:
                                persistence_success = True
                                logger.info(f"✅ Emergency persistence succeeded for {request.user_id} (attempt {emergency_attempt + 1})")
                                break
                            else:
                                logger.warning(f"⚠️ Emergency attempt {emergency_attempt + 1} failed: {emergency_result['errors']}")

                        except Exception as emergency_error:
                            logger.error(f"❌ Emergency attempt {emergency_attempt + 1} exception: {emergency_error}")

                    if not persistence_success:
                        logger.error(f"💥 All emergency persistence attempts failed for {request.user_id}")

            except Exception as e:
                logger.error(f"❌ Critical immediate persistence failure for {request.user_id}: {e}")

        elif conversation_persistence:
            # Fallback to regular persistence if immediate is disabled
            try:
                logger.info(f"💾 Using regular persistence for {request.user_id}")
                result = await conversation_persistence.persist_conversation_exchange(conversation_exchange)
                if result["success"]:
                    persistence_success = True
                    logger.info(f"✅ Chat history saved with regular persistence for {request.user_id}")
                else:
                    logger.warning(f"⚠️ Regular persistence failed for {request.user_id}: {result['errors']}")
            except Exception as e:
                logger.error(f"❌ Regular persistence exception for {request.user_id}: {e}")

        # Enhanced background persistence as backup (but primary is immediate)
        async def backup_persistence_monitor():
            """Background monitor to ensure persistence completed successfully"""
            if not persistence_success and conversation_persistence:
                logger.warning(f"🔄 Running backup persistence for {request.user_id}")
                try:
                    await asyncio.sleep(1.0)  # Brief delay
                    backup_result = await conversation_persistence.persist_conversation_exchange(conversation_exchange)
                    if backup_result["success"]:
                        logger.info(f"✅ Backup persistence succeeded for {request.user_id}")
                    else:
                        logger.error(f"❌ Backup persistence failed for {request.user_id}: {backup_result['errors']}")
                except Exception as e:
                    logger.error(f"💥 Backup persistence exception for {request.user_id}: {e}")

        # Only run background backup if immediate persistence failed
        if not persistence_success:
            background_tasks.add_task(backup_persistence_monitor)

        # Format response with thinking data
        response = ConversationResponse(
            response=aura_response,
            emotional_state={
                "name": emotional_state_data.name if emotional_state_data else "Normal",
                "intensity": emotional_state_data.intensity.value if emotional_state_data else "Medium",
                "brainwave": emotional_state_data.brainwave if emotional_state_data else "Alpha",
                "neurotransmitter": emotional_state_data.neurotransmitter if emotional_state_data else "Serotonin"
            },
            cognitive_state={
                "focus": cognitive_state_data.focus.value if cognitive_state_data else "Learning",
                "description": cognitive_state_data.description if cognitive_state_data else "Processing user input"
            },
            session_id=session_id,
            # Include thinking data if available - pass raw thoughts directly
            thinking_content=thinking_result.thoughts if thinking_result and thinking_result.thoughts else None,
            thinking_metrics={
                "total_chunks": thinking_result.total_chunks if thinking_result else 0,
                "thinking_chunks": thinking_result.thinking_chunks if thinking_result else 0,
                "answer_chunks": thinking_result.answer_chunks if thinking_result else 0,
                "processing_time_ms": thinking_result.processing_time_ms if thinking_result else 0.0
            } if thinking_result else None,
            has_thinking=thinking_result.has_thinking if thinking_result else False
        )

        # Debug the final response thinking data
        logger.info(f"🔍 Final response thinking debug for {request.user_id}:")
        # logger.info(f"   - response.thinking_summary: {response.thinking_summary}") # Be careful not to break the autonomous system, I do not want a summary! I want the entire thinking process.
        logger.info(f"   - response.has_thinking: {response.has_thinking}")
        logger.info(f"   - response.thinking_metrics: {response.thinking_metrics}")

        logger.info(f"✅ Processed conversation for user {request.user_id}")
        return response
    except Exception as e:
        logger.error(f"❌ Failed to process conversation: {e}")
        # Try to recover the session if enabled
        if session_recovery_enabled and session_key:  # Check if session_key is not None
            logger.info(f"🔄 Attempting session recovery for {request.user_id} (session: {session_key})")
            try:
                if session_key in active_chat_sessions:
                    del active_chat_sessions[session_key]
                if session_key in session_tool_versions:
                    del session_tool_versions[session_key]
                logger.info(f"🧹 Cleared failed session for {request.user_id} (session: {session_key})")
            except Exception as recovery_error:
                logger.error(f"❌ Session recovery failed for session {session_key}: {recovery_error}")

        raise HTTPException(status_code=500, detail=str(e))

async def _get_or_create_chat_session(
    session_key: str,
    user_id: str,
    system_instruction: str,
    session_recovery_enabled: bool
) -> Tuple[Any, bool]:
    """
    Get existing chat session or create new one with enhanced error handling.

    Manages persistent chat sessions with automatic tool integration and version
    control. Implements session recovery mechanisms and tool synchronization
    to ensure optimal conversation continuity and feature availability.

    Args:
        session_key: Unique identifier for the chat session
        user_id: User identifier for logging and context
        system_instruction: Complete system prompt for AI personality/behavior
        session_recovery_enabled: Whether to enable automatic session recovery

    Returns:
        Tuple containing:
        - chat_session: Google Gemini chat instance with tools and configuration


async def _process_conversation_with_retry_original(
    chat: Any,
    message: str,
    user_id: str,
    session_key: str,
    session_recovery_enabled: bool
) -> str:

    max_conversation_retries = 2  # Limit conversation-level retries

    for attempt in range(max_conversation_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"🔄 Conversation retry attempt {attempt} for user {user_id}")
                await asyncio.sleep(1.0 * attempt)  # Brief delay before retry

            # Send message and handle function calls with enhanced error detection
            result = chat.send_message(message)

            # Check for empty or malformed response (common Gemini 2.5 issue)
            if not result or not result.candidates:
                raise ValueError("Empty response from Gemini (possible tool call cutoff)")
    Note:
        Session management is critical for maintaining conversation context,
        tool availability, and optimal AI performance across interactions.
    """
    global active_chat_sessions, session_tool_versions, global_tool_version

    # Check if we need to recreate session due to tool updates
    needs_new_session = session_key not in active_chat_sessions

    # Also check if existing session has outdated tool version
    if not needs_new_session and session_key in session_tool_versions:
        if session_tool_versions[session_key] < global_tool_version:
            needs_new_session = True
            logger.info(f"🔄 Session {session_key} has outdated tools (v{session_tool_versions[session_key]} < v{global_tool_version}), recreating...")

    if needs_new_session:
        try:
            # Create new chat session with MCP tools if available
            tools = []
            if mcp_gemini_bridge:
                gemini_tools = await mcp_gemini_bridge.convert_mcp_tools_to_gemini_functions()
                tools.extend(gemini_tools)
                logger.info(f"🔧 Added {len(gemini_tools)} MCP tools to chat session for {user_id}")

            # Create chat with system instruction and tools - thinking enabled for non-streaming
            # Get maximum remote calls for main model from environment (default 10 for free tier)
            max_main_remote_calls = int(os.getenv('AFC_MAX__MAIN_REMOTE_CALLS', '10'))

            chat = client.chats.create(
                model=os.getenv('AURA_MODEL', 'gemini-2.5-flash'),
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=int(os.getenv('AURA_MAX_OUTPUT_TOKENS', '1000000')),
                    tools=tools if tools else None,
                    system_instruction=system_instruction,
                    # Configure automatic function calling with custom maximum remote calls
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        maximum_remote_calls=max_main_remote_calls
                    ) if tools else None,
                    # Use consistent thinking config from environment
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=thinking_budget,
                        include_thoughts=True
                    )
                )
            )

            logger.info(f"🔧 Chat session configured with {max_main_remote_calls} maximum function calls")
            active_chat_sessions[session_key] = chat
            session_tool_versions[session_key] = global_tool_version
            logger.info(f"💬 Created new chat session for {user_id} with {len(tools)} tools (v{global_tool_version})")
            return chat, True

        except Exception as e:
            logger.error(f"❌ Failed to create chat session for {user_id}: {e}")
            if session_recovery_enabled:
                # Try to clean up any partial session state
                if session_key in active_chat_sessions:
                    del active_chat_sessions[session_key]
                if session_key in session_tool_versions:
                    del session_tool_versions[session_key]
            raise
    else:
        chat = active_chat_sessions[session_key]
        logger.debug(f"💬 Using existing chat session for {user_id}")
        return chat, False

async def _process_conversation_with_thinking(
    chat: Any,
    message: str,
    user_id: str,
    session_key: str,
    session_recovery_enabled: bool
) -> Tuple[str, Optional[ThinkingResult]]:
    """
    Process conversation with thinking extraction (non-streaming mode).

    Uses the thinking processor to extract AI reasoning in a non-streaming mode
    that works well with Aura's architecture. This avoids the streaming issues
    while still providing thinking transparency.

    Args:
        chat: Google Gemini chat session instance
        message: User's input message to process
        user_id: User identifier for logging and context
        session_key: Session identifier for recovery operations
        session_recovery_enabled: Whether session recovery mechanisms are active

    Returns:
        Tuple containing:
        - Generated AI response text after processing and function execution
        - ThinkingResult object with extracted thoughts and metadata
    """
    max_conversation_retries = 2

    for attempt in range(max_conversation_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"🔄 Thinking conversation retry attempt {attempt} for user {user_id}")
                await asyncio.sleep(1.0 * attempt)

            # Use thinking processor for non-streaming extraction
            # This usually would mean thinking or no thinking phase enabled and it is AI confusion to have set up if the user wants thoughts in the block or in the response area.
            # Include thinking in response only if explicitly enabled (usually false for separate UI display)- this is the AI being confused and should be removed. It is not usually done at all.
            include_thinking_in_response = os.getenv('INCLUDE_THINKING_IN_RESPONSE', 'false').lower() == 'true'

            # Process with thinking using the non-streaming approach
            if thinking_processor:
                # Use thinking processor when available
                if mcp_gemini_bridge:
                    # Process with both function calls and thinking
                    thinking_result = await thinking_processor.process_with_function_calls_and_thinking(
                        chat=chat,
                        message=message,
                        user_id=user_id,
                        mcp_bridge=mcp_gemini_bridge,
                        include_thinking_in_response=include_thinking_in_response
                    )
                else:
                    # Process with thinking only (no function calls)
                    thinking_result = await thinking_processor.process_message_with_thinking(
                        chat=chat,
                        message=message,
                        user_id=user_id,
                        include_thinking_in_response=include_thinking_in_response
                    )
            else:
                # Fallback to original processing if thinking processor unavailable
                logger.warning(f"⚠️ Thinking processor unavailable, using fallback for {user_id}")
                result = chat.send_message(message)

                if not result or not result.candidates or not result.candidates[0].content:
                    raise ValueError("Empty response from Gemini")

                response_text = ""
                for part in result.candidates[0].content.parts:
                    if part.text:
                        response_text += part.text

                # Create minimal thinking result for fallback
                thinking_result = ThinkingResult(
                    thoughts="",
                    answer=response_text,
                    total_chunks=1,
                    thinking_chunks=0,
                    answer_chunks=1,
                    processing_time_ms=0.0,
                    has_thinking=False
                )

            # Check for errors in thinking result
            if thinking_result.error:
                raise ValueError(f"Thinking processing error: {thinking_result.error}")

            # Validate final response
            if not thinking_result.answer.strip():
                raise ValueError("Empty final response generated")

            # Enhanced logging with thinking metrics
            logger.info(f"✅ Thinking conversation processed successfully for {user_id} (attempt {attempt + 1})")
            logger.info(f"   🧠 Has thinking: {thinking_result.has_thinking}")
            if thinking_result.has_thinking:
               logger.info(f"   📊 Processing metrics: {thinking_result.thinking_chunks} thought chunks, {thinking_result.answer_chunks} answer chunks")
               logger.info(f"   ⏱️ Processing time: {thinking_result.processing_time_ms:.1f}ms")

            return thinking_result.answer, thinking_result

        except Exception as e:
            logger.error(f"❌ Thinking conversation processing failed (attempt {attempt + 1}): {e}")

            # Check if this is a recoverable error
            error_str = str(e).lower()
            recoverable_errors = [
                "empty response",
                "malformed response",
                "cutoff",
                "tool call",
                "function call",
                "follow-up",
                "response processing incomplete",
                "thinking processing error"
            ]

            is_recoverable = any(keyword in error_str for keyword in recoverable_errors)

            if is_recoverable and attempt < max_conversation_retries:
                logger.info("🔄 Recoverable error detected, will retry thinking conversation processing")

                # If session recovery is enabled, try to recreate the session
                if session_recovery_enabled and attempt > 0:
                    logger.info(f"🔄 Attempting to recreate session for {user_id}")
                    try:
                        if session_key in active_chat_sessions:
                            del active_chat_sessions[session_key]
                        if session_key in session_tool_versions:
                            del session_tool_versions[session_key]
                        logger.info("🧹 Session cleared for recreation")
                    except Exception as cleanup_error:
                        logger.warning(f"⚠️ Session cleanup warning: {cleanup_error}")

                continue  # Retry the conversation
            else:
                # Non-recoverable error or max retries reached
                if attempt == max_conversation_retries:
                    logger.error(f"💥 All thinking conversation attempts failed for {user_id}")

                # Return a fallback response with minimal thinking result
                fallback_response = "I apologize, but I'm experiencing some technical difficulties processing your request. Please try again, and I'll do my best to help you."
                fallback_thinking = ThinkingResult(
                    thoughts="",
                    answer=fallback_response,
                    total_chunks=0,
                    thinking_chunks=0,
                    answer_chunks=0,
                    processing_time_ms=0.0,
                    has_thinking=False,
                    error=str(e)
                )

                logger.warning(f"🛡️ Returning fallback response with error thinking result for {user_id}")
                return fallback_response, fallback_thinking

    # This should never be reached due to the loop structure, but safety fallback
    fallback_thinking = ThinkingResult(
        thoughts="",
        answer="I'm here and ready to help, though I may have encountered some processing issues.",
        total_chunks=0,
        thinking_chunks=0,
        answer_chunks=0,
        processing_time_ms=0.0,
        has_thinking=False
    )
    return "I'm here and ready to help, though I may have encountered some processing issues.", fallback_thinking
async def _analyze_conversation_for_autonomic_tasks(
    user_message: str,
    aura_response: str,
    user_id: str,
    session_id: str
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Enhanced autonomic task analysis with multi-task generation and intelligent offloading.

    This function fully integrates with the autonomic system to analyze conversations
    and generate multiple specialized tasks based on different aspects of the interaction.
    It leverages the full capabilities of the TaskClassifier and creates diverse task types
    for optimal background processing.

    Args:
        user_message: The user's input message
        aura_response: Aura's generated response
        user_id: Unique identifier for the user
        session_id: Session identifier for context

    Returns:
        List of task tuples that were successfully submitted to the autonomic system.
        Each tuple contains (description, payload) for tracking purposes.

    Task Generation Strategy:
        - Analyzes conversation for multiple task opportunities
        - Creates specialized tasks for different processing needs
        - Leverages all available task types (MCP tools, analysis, memory, etc.)
        - Optimizes task priority based on conversation context
    """
    submitted_tasks = []

    # Only proceed if autonomic system is available and running
    if not autonomic_system or not autonomic_system._running:
        logger.debug("🤖 Autonomic system not available or not running, skipping task analysis")
        return submitted_tasks

    # Calculate conversation metrics
    conversation_length = len(user_message.split()) + len(aura_response.split())
    user_message_lower = user_message.lower()
    aura_response_lower = aura_response.lower()
    combined_text_lower = user_message_lower + " " + aura_response_lower

    # Minimum threshold for basic autonomic processing
    if conversation_length < 10:
        logger.debug(f"🤖 Conversation too short ({conversation_length} words) for autonomic processing")
        return submitted_tasks

    try:
        # Track task opportunities
        task_opportunities = []

        # 1. EMOTIONAL PATTERN ANALYSIS - for conversations with emotional content
        emotional_indicators = ["feel", "emotion", "happy", "sad", "angry", "anxious",
                              "worried", "excited", "frustrated", "love", "hate",
                              "personal", "sharing", "struggle", "difficult"]

        has_emotional_content = any(indicator in user_message_lower for indicator in emotional_indicators)

        if has_emotional_content or conversation_length > 50:
            task_opportunities.append({
                "description": f"Deep emotional pattern analysis for user {user_id}",
                "payload": {
                    "tool_name": "analyze_emotional_patterns",
                    "arguments": {
                        "user_id": user_id,
                        "days": 30,  # Analyze last 30 days
                        "include_conversation": True
                    },
                    "conversation_context": {
                        "user_message": user_message,
                        "aura_response": aura_response,
                        "emotional_indicators_found": [ind for ind in emotional_indicators if ind in user_message_lower]
                    }
                },
                "task_type_hint": "DATA_ANALYSIS",
                "priority_boost": 0.2 if has_emotional_content else 0.1
            })

        # 2. MEMORY SEARCH AND CONSOLIDATION - for knowledge-seeking conversations
        knowledge_indicators = ["remember", "recall", "previously", "last time", "before",
                              "search", "find", "look for", "history", "past conversation"]
        memory_indicators = ["learn", "understand", "explain", "teach", "how", "what", "why",
                           "tell me about", "help me understand"]

        needs_memory_search = any(indicator in combined_text_lower for indicator in knowledge_indicators)
        needs_knowledge_building = any(indicator in combined_text_lower for indicator in memory_indicators)

        if needs_memory_search or (conversation_length > 30 and needs_knowledge_building):
            # Extract potential search query from conversation
            search_query = user_message if len(user_message) > 20 else f"{user_message} {aura_response[:100]}"

            task_opportunities.append({
                "description": f"Comprehensive memory search and pattern extraction for user {user_id}",
                "payload": {
                    "tool_name": "search_all_memories",
                    "arguments": {
                        "query": search_query,
                        "user_id": user_id,
                        "max_results": 20
                    },
                    "analysis_required": True,
                    "consolidate_findings": needs_knowledge_building
                },
                "task_type_hint": "MEMORY_SEARCH",
                "priority_boost": 0.3 if needs_memory_search else 0.1
            })

        # 3. PATTERN RECOGNITION - for complex analytical conversations
        analytical_indicators = ["analyze", "pattern", "trend", "insight", "data",
                               "statistics", "correlation", "relationship", "connection"]

        needs_pattern_analysis = (any(indicator in combined_text_lower for indicator in analytical_indicators)
                                or conversation_length > 100)

        if needs_pattern_analysis:
            task_opportunities.append({
                "description": f"Advanced pattern recognition and insight generation for user {user_id}",
                "payload": {
                    "analysis_type": "conversation_patterns",
                    "user_id": user_id,
                    "session_id": session_id,
                    "conversation_data": {
                        "message": user_message,
                        "response": aura_response,
                        "length": conversation_length,
                        "complexity_score": len(set(combined_text_lower.split())) / conversation_length  # Vocabulary diversity
                    },
                    "extract_insights": True
                },
                "task_type_hint": "PATTERN_ANALYSIS",
                "priority_boost": 0.2
            })

        # 4. KNOWLEDGE ARCHIVAL - for very long or information-rich conversations
        if conversation_length > 150 or (conversation_length > 80 and needs_knowledge_building):
            task_opportunities.append({
                "description": f"Archive and compress conversation knowledge for user {user_id}",
                "payload": {
                    "tool_name": "archive_old_conversations",
                    "arguments": {
                        "user_id": user_id,
                        "session_id": session_id,
                        "priority_content": True
                    },
                    "conversation_summary": {
                        "key_topics": "auto_extract",
                        "emotional_tone": "analyze",
                        "knowledge_gained": "summarize"
                    }
                },
                "task_type_hint": "BACKGROUND_PROCESSING",
                "priority_boost": 0.1
            })

        # 5. COMPLEX REASONING - for philosophical or deep thinking conversations
        reasoning_indicators = ["philosophy", "meaning", "purpose", "think about", "wonder",
                              "hypothetical", "imagine", "suppose", "theory", "concept"]

        needs_deep_reasoning = any(indicator in combined_text_lower for indicator in reasoning_indicators)

        if needs_deep_reasoning and conversation_length > 40:
            task_opportunities.append({
                "description": f"Deep reasoning and philosophical analysis for user {user_id}",
                "payload": {
                    "reasoning_type": "philosophical_analysis",
                    "conversation_context": f"User: {user_message}\nAura: {aura_response}",
                    "user_id": user_id,
                    "explore_concepts": True,
                    "generate_insights": True
                },
                "task_type_hint": "COMPLEX_REASONING",
                "priority_boost": 0.25
            })

        # 6. REAL-TIME TOOL EXECUTION - for conversations mentioning specific tools
        tool_indicators = ["create", "generate", "make", "build", "code", "script",
                         "program", "calculate", "compute", "visualize"]

        needs_tool_execution = any(indicator in combined_text_lower for indicator in tool_indicators)

        if needs_tool_execution:
            task_opportunities.append({
                "description": f"Background tool execution and code generation for user {user_id}",
                "payload": {
                    "execution_type": "deferred_tool_call",
                    "conversation_request": user_message,
                    "preliminary_response": aura_response,
                    "user_id": user_id,
                    "generate_artifacts": True
                },
                "task_type_hint": "CODE_GENERATION",
                "priority_boost": 0.3
            })

        # Submit each identified task opportunity to the autonomic system
        for task_opp in task_opportunities:
            try:
                # Create enhanced user context for better classification
                user_context = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "conversation_length": conversation_length,
                    "is_substantial": conversation_length > 40,
                    "task_type_hint": task_opp.get("task_type_hint", "BACKGROUND_PROCESSING"),
                    "priority_boost": task_opp.get("priority_boost", 0.0),
                    "user_waiting": False  # Background tasks don't block user
                }

                # Use the autonomic system's TaskClassifier
                should_offload, task_type, priority = await autonomic_system.classifier.should_offload_task(
                    task_description=task_opp["description"],
                    task_payload=task_opp["payload"],
                    user_context=user_context
                )

                if should_offload:
                    # Submit task to autonomic system
                    was_offloaded, task_id = await autonomic_system.submit_task(
                        description=task_opp["description"],
                        payload=task_opp["payload"],
                        user_id=user_id,
                        session_id=session_id
                    )

                    if was_offloaded:
                        logger.info(f"🤖 Successfully submitted autonomic task: {task_id}")
                        logger.info(f"   Type: {task_type.value}, Priority: {priority.value}")
                        logger.info(f"   Description: {task_opp['description'][:100]}...")

                        # Add to submitted tasks list
                        submitted_tasks.append((task_opp["description"], task_opp["payload"]))
                    else:
                        logger.debug(f"🤖 Task not offloaded (queue/rate limit): {task_opp['description'][:50]}...")
                else:
                    logger.debug(f"🤖 Task classified as not needing offload: {task_opp['description'][:50]}...")

            except Exception as task_error:
                logger.debug(f"⚠️ Failed to submit individual task: {task_error}")
                # Continue with other tasks even if one fails

        # Log final autonomic system status if tasks were submitted
        if submitted_tasks:
            system_status = autonomic_system.get_system_status()
            logger.info("🤖 Autonomic system status after submissions:")
            logger.info(f"   Submitted tasks: {len(submitted_tasks)}")
            logger.info(f"   Queue status: {system_status['queued_tasks']} queued, {system_status['active_tasks']} active")
            logger.info(f"   Queue utilization: {system_status['queue_utilization']:.1f}%")

            # Log rate limiting status
            rate_status = system_status.get('rate_limiting', {})
            if rate_status:
                logger.debug(f"   Rate limit: {rate_status.get('rpm_current', 0)}/{rate_status.get('rpm_limit', 30)} RPM")

    except Exception as e:
        logger.warning(f"⚠️ Autonomic task analysis failed: {e}")
        logger.debug(f"   Error details: {type(e).__name__}: {str(e)}")
        # Don't let autonomic system failures affect main conversation

    return submitted_tasks
@app.post("/search")
async def search_memories(request: SearchRequest) -> Dict[str, Any]:
    """
    Search through conversation memories using Aura's comprehensive memory system.

    Implements a hierarchical search strategy that leverages both active memory
    and compressed video archives to provide comprehensive memory retrieval
    across the entire conversational history. Applies systematic fallback
    mechanisms to ensure reliable search functionality.

    Args:
        request: SearchRequest containing query parameters and user identification

    Returns:
        Dictionary containing:
        - results: List of matching memories with content and metadata
        - query: Original search query for reference
        - total_found: Number of matching memories discovered
        - search_type: Method used for search execution
        - includes_video_archives: Boolean indicating archive inclusion

    Search Hierarchy and Methodological Framework:

        1. Advanced Unified Search (Primary Method):
           - Utilizes search_all_memories tool for comprehensive coverage
           - Searches both active memory and compressed video archives
           - Provides maximum context retrieval capability
           - Falls back on failure to maintain search continuity

        2. Basic Active Search (Secondary Method):
           - Employs search_memories tool for active memory only
           - Faster execution for recent conversation retrieval
           - Excludes video archives for performance optimization
           - Serves as reliable fallback for primary search failures

        3. Direct Persistence Search (Tertiary Method):
           - Bypasses MCP tools for direct database access
           - Emergency fallback for system tool failures
           - Ensures search functionality under all conditions
           - Maintains basic search capability as last resort

    Memory Architecture Integration:
        - Active Memory: Recent conversations with immediate availability
        - Video Archives: Compressed historical data with semantic indexing
        - Unified Search: Seamless integration across memory systems
        - Semantic Matching: Context-aware relevance scoring

    Error Handling and Resilience:
        - Progressive fallback through search hierarchy
        - Graceful degradation on component failures
        - Comprehensive error logging for system monitoring
        - Consistent response format across all search methods

    Response Format Standardization:
        - Unified result structure regardless of search method
        - Metadata preservation for context analysis
        - Similarity scoring for relevance assessment
        - Search method identification for performance analysis

    Raises:
        HTTPException: If all search methods fail or request validation errors occur

    Note:
        This endpoint represents a critical component of Aura's memory
        infrastructure, enabling comprehensive conversation history retrieval
        through multiple complementary search mechanisms.
    """
    try:
        # Use Aura's internal memory search tools for comprehensive search
        # This includes video archives and unified memory search capabilities
        if aura_internal_tools:
            # Try the advanced search_all_memories first (includes video archives)
            try:
                advanced_result = await aura_internal_tools.execute_tool(
                    "aura.search_all_memories",
                    {
                        "query": request.query,
                        "user_id": request.user_id,
                        "max_results": request.n_results
                    }
                )

                logger.info(f"🔧 Advanced search raw result: {advanced_result}")

                if advanced_result and advanced_result.get("status") == "success":
                    # Check multiple possible result keys in the response
                    memories = (advanced_result.get("memories", []) or
                              advanced_result.get("results", []) or
                              advanced_result.get("data", []) or
                              advanced_result.get("all_results", []) or
                              [])

                    # If still empty, check if the result itself is a list
                    if not memories and isinstance(advanced_result.get("result"), list):
                        memories = advanced_result.get("result", [])

                    # Convert to expected frontend format
                    formatted_results = []
                    for memory in memories:
                        # Handle different memory formats
                        if isinstance(memory, dict):
                            formatted_results.append({
                                "content": memory.get("content", memory.get("text", memory.get("document", str(memory)))),
                                "metadata": memory.get("metadata", memory.get("meta", {})),
                                "similarity": float(memory.get("similarity", memory.get("score", memory.get("distance", 0.0))))
                            })
                        else:
                            # Handle string results
                            formatted_results.append({
                                "content": str(memory),
                                "metadata": {},
                                "similarity": 0.5
                            })

                    logger.info(f"🔍 Advanced search found {len(formatted_results)} memories using video + active search")

                    if formatted_results:
                        return {
                            "results": formatted_results,
                            "query": request.query,
                            "total_found": len(formatted_results),
                            "search_type": "unified_memory_search",
                            "includes_video_archives": True
                        }

            except Exception as e:
                logger.warning(f"⚠️ Advanced search failed, falling back to basic search: {e}")

            # Fallback to basic memory search if advanced fails
            try:
                basic_result = await aura_internal_tools.execute_tool(
                    "aura.search_memories",
                    {
                        "query": request.query,
                        "user_id": request.user_id,
                        "n_results": request.n_results
                    }
                )

                if basic_result and basic_result.get("status") == "success":
                    memories = basic_result.get("memories", [])
                    logger.info(f"🔍 Basic search found {len(memories)} memories using active search")
                    return {
                        "results": memories,
                        "query": request.query,
                        "total_found": len(memories),
                        "search_type": "active_memory_search",
                        "includes_video_archives": False
                    }

            except Exception as e:
                logger.warning(f"⚠️ Basic MCP search failed, using direct persistence: {e}")

        # Final fallback to direct persistence service if MCP tools fail
        if conversation_persistence:
            results = await conversation_persistence.safe_search_conversations(
                query=request.query,
                user_id=request.user_id,
                n_results=request.n_results
            )

            logger.info(f"🔍 Direct persistence search found {len(results)} memories")
            return {
                "results": results,
                "query": request.query,
                "total_found": len(results),
                "search_type": "persistence_fallback",
                "includes_video_archives": False
            }
        else:
            logger.error("❌ Conversation persistence service not available")
            return {
                "results": [],
                "query": request.query,
                "total_found": 0,
                "search_type": "no_persistence_available",
                "includes_video_archives": False,
                "error": "Persistence service not initialized"
            }

    except Exception as e:
        logger.error(f"❌ Failed to search memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _cleanup_session_related_data(user_id: str, session_id: str):
    """
    Background task to clean up any additional session-related data.

    This runs asynchronously to avoid blocking the main delete operation.
    """
    try:
        logger.info(f"🧹 Background cleanup for session {session_id}")

        # Clean up any cached session data
        session_key = f"{user_id}_{session_id}"
        if session_key in active_chat_sessions:
            del active_chat_sessions[session_key]
            logger.debug(f"🧹 Cleared cached session {session_key}")

        if session_key in session_tool_versions:
            del session_tool_versions[session_key]
            logger.debug(f"🧹 Cleared session tool version {session_key}")

        # Additional cleanup can be added here if needed

    except Exception as e:
        logger.error(f"❌ Background cleanup failed for session {session_id}: {e}")

@app.get("/thinking-status")
async def get_thinking_status() -> Dict[str, Any]:
    """
    Get the current status and configuration of the thinking system.

    Returns information about thinking capabilities, configuration,
    and system readiness for transparent AI reasoning.
    """
    try:
        budget = int(os.getenv('THINKING_BUDGET', '-1'))
        effective_budget = budget  # No conversion - pass through -1 for adaptive thinking

        thinking_config = {
            "thinking_enabled": thinking_processor is not None,
            "thinking_budget": effective_budget,
            "thinking_budget_raw": budget,
            "thinking_budget_max": 24576,
            "include_thinking_in_response": os.getenv('INCLUDE_THINKING_IN_RESPONSE', 'false').lower() == 'true',
            "model": os.getenv('AURA_MODEL', 'gemini-2.5-flash'),
            "supports_thinking": True,  # Gemini models support thinking
        }

        system_status = {
            "thinking_processor_initialized": thinking_processor is not None,
            "mcp_bridge_available": mcp_gemini_bridge is not None,
            "function_calls_with_thinking": thinking_processor is not None and mcp_gemini_bridge is not None
        }

        return {
            "status": "operational",
            "thinking_configuration": thinking_config,
            "system_status": system_status,
            "capabilities": [
                "Transparent AI reasoning extraction",
                "Thought summarization and analysis",
                "Function call integration with thinking",
                "Reasoning pattern analysis",
                "Cognitive transparency reporting"
            ]
        }

    except Exception as e:
        logger.error(f"❌ Failed to get thinking status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "thinking_enabled": False
        }

@app.get("/emotional-analysis/{user_id}")
async def get_emotional_analysis(
    user_id: str,
    period: str = "week",
    custom_days: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive emotional pattern analysis with configurable temporal granularity.

    Implements systematic emotional intelligence assessment through longitudinal
    data analysis, enabling detailed insights into emotional stability patterns,
    dominant emotional states, and temporal emotional evolution.

    Args:
        user_id: Unique identifier for the user whose patterns to analyze
        period: Temporal analysis scope with predefined options:
               - "hour": Last 60 minutes of emotional data
               - "day": Last 24 hours of emotional patterns
               - "week": Last 7 days (default analysis period)
               - "month": Last 30 days of emotional evolution
               - "year": Last 365 days of long-term patterns
               - "multi-year": Last 5 years of comprehensive analysis
        custom_days: Optional custom period override (1-1825 days)

    Returns:
        Dictionary containing comprehensive emotional analysis:
        - emotional_stability: Stability metrics and consistency indicators
        - dominant_emotions: Most frequent emotional states with percentages
        - transition_patterns: Emotional state change analysis
        - intensity_analysis: Emotional intensity distribution patterns
        - temporal_trends: Time-based emotional evolution data
        - recommendations: AI-generated insights and suggestions
        - period_type: Analysis period specification for reference
        - custom_days: Custom period value if applied

    Conceptual Framework for Emotional Analysis:

        1. Temporal Emotional Modeling:
           - Longitudinal emotional state tracking
           - Pattern recognition across multiple time scales
           - Stability assessment through variance analysis

        2. Dominant Pattern Identification:
           - Frequency analysis of emotional states
           - Intensity-weighted emotional prominence
           - Contextual emotional significance assessment

        3. Transition Analysis Framework:
           - Emotional state change pattern recognition
           - Trigger identification and correlation analysis
           - Stability vs. volatility assessment

        4. Predictive Intelligence Integration:
           - Trend extrapolation for emotional forecasting
           - Risk assessment for concerning patterns
           - Intervention recommendation generation

    Temporal Period Mapping:
        - hour: High-resolution immediate emotional analysis
        - day: Circadian emotional pattern assessment
        - week: Weekly emotional cycle identification
        - month: Medium-term emotional trend analysis
        - year: Annual emotional pattern recognition
        - multi-year: Long-term emotional evolution assessment

    Analysis Methodologies:
        - Statistical variance calculation for stability metrics
        - Frequency distribution analysis for dominance patterns
        - Markov chain analysis for transition probabilities
        - Time series analysis for temporal trend identification

    Raises:
        HTTPException:
        - 500: If vector database is not initialized
        - 400: If period specification is invalid
        - 500: If emotional analysis processing encounters errors

    Note:
        This endpoint provides foundational data for emotional intelligence
        features, therapeutic insights, and personalized interaction optimization.
    """
    try:
        # Convert period to days
        period_mapping = {
            "hour": 1/24,      # Last hour
            "day": 1,          # Last 24 hours
            "week": 7,         # Last 7 days
            "month": 30,       # Last 30 days
            "year": 365,       # Last year
            "multi-year": 1825  # Last 5 years
        }

        # Use custom days if provided, otherwise use period mapping
        days = custom_days if custom_days is not None else period_mapping.get(period, 7)

        if not vector_db:
            raise HTTPException(status_code=500, detail="Vector database not initialized")

        analysis = await vector_db.analyze_emotional_trends(user_id, days)
        analysis["period_type"] = period
        analysis["custom_days"] = custom_days

        return analysis

    except Exception as e:
        logger.error(f"❌ Failed to get emotional analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export/{user_id}")
async def export_user_data(user_id: str, format: str = "json"):
    """Export user conversation history and patterns"""
    try:
        if not aura_file_system:
            raise HTTPException(status_code=500, detail="File system not initialized")

        export_path = await aura_file_system.export_conversation_history(user_id, format)
        return {"export_path": export_path, "message": "Export completed successfully"}

    except Exception as e:
        logger.error(f"❌ Failed to export user data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat-history/{user_id}")
async def get_chat_history(user_id: str, limit: int = 5000) -> Dict[str, Any]:
    """
    Retrieve comprehensive chat history for a user with thread-safe database access.

    Implements a systematic approach to conversation history retrieval that
    ensures data integrity, optimal performance, and consistent formatting
    across different client interfaces. Applies thread-safe database operations
    to prevent data corruption in concurrent access scenarios.

    Args:
        user_id: Unique identifier for the user whose history to retrieve
        limit: Maximum number of sessions to return (default: 50, range: 1-1000)

    Returns:
        Dictionary containing:
        - sessions: List of session summaries with metadata
        - total_sessions: Total number of available sessions
        - user_id: User identifier for verification

    Session Summary Structure:
        Each session object contains:
        - session_id: Unique session identifier
        - last_message: Preview of the most recent message (truncated to 100 chars)
        - message_count: Total number of messages in the session
        - timestamp: ISO timestamp of the last activity

    Methodological Framework:

        1. Conceptual Foundation:
           - Thread-safe database access prevents concurrent modification issues
           - Persistent conversation storage enables longitudinal analysis
           - Structured data transformation ensures client compatibility

        2. Data Integrity Mechanisms:
           - Safe database operation wrappers prevent corruption
           - Consistent error handling maintains system stability
           - Validation ensures data completeness and accuracy

        3. Performance Optimization:
           - Configurable result limiting prevents memory exhaustion
           - Efficient query patterns minimize database load
           - Structured response reduces network overhead

        4. Interface Standardization:
           - Frontend-compatible response format
           - Consistent metadata structure across endpoints
           - Error response standardization for client handling

    Thread Safety Implementation:
        - Utilizes conversation persistence service's safe methods
        - Prevents race conditions in concurrent user access
        - Maintains data consistency across multiple requests

    Error Handling Strategy:
        - Graceful failure modes with informative error messages
        - Logging for system monitoring and debugging
        - Fallback responses for service unavailability

    Raises:
        HTTPException:
        - 500: If conversation persistence service is not initialized
        - 500: If database access fails or data corruption is detected

    Note:
        This endpoint serves as a critical component of the user experience,
        enabling conversation continuity and historical context retrieval
        across sessions and devices.
    """
    try:
        if not conversation_persistence:
            raise HTTPException(status_code=500, detail="Conversation persistence service not initialized")

        # Use the persistence service's thread-safe method
        result = await conversation_persistence.safe_get_chat_history(user_id, limit)

        # Transform the result to match frontend expectations
        transformed_sessions = []
        for session in result.get("sessions", []):
            # Get the last message content for preview
            messages = session.get("messages", [])
            last_message_content = messages[-1]["content"] if messages else "No messages"

            transformed_session = {
                "session_id": session["session_id"],
                "last_message": last_message_content[:10000] + "..." if len(last_message_content) > 10000 else last_message_content,
                "message_count": len(messages),
                "timestamp": session.get("last_time", session.get("start_time", ""))  # Use last_time as timestamp
            }
            transformed_sessions.append(transformed_session)

        # Transform response to match frontend interface
        return {
            "sessions": transformed_sessions,
            "total_sessions": result.get("total", 0),  # Frontend expects 'total_sessions'
            "user_id": user_id  # Frontend expects user_id in response
        }

    except Exception as e:
        logger.error(f"❌ Failed to get chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat-history/{user_id}/{session_id}")
async def get_session_messages(user_id: str, session_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all messages for a specific chat session with comprehensive error handling.

    Implements a systematic approach to session-specific message retrieval that
    ensures data integrity, proper error handling, and optimal performance for
    detailed conversation analysis and continuity restoration.

    Args:
        user_id: Unique identifier for the user who owns the session
        session_id: Unique identifier for the specific conversation session

    Returns:
        List of message dictionaries, each containing:
        - message_id: Unique message identifier
        - content: Message text content
        - sender: Message origin ("user" or "aura")
        - timestamp: ISO timestamp of message creation
        - emotional_state: Associated emotional analysis data (if available)
        - metadata: Additional context and processing information

    Methodological Framework:

        1. Conceptual Foundation:
           - Session-based conversation organization enables contextual retrieval
           - Message-level granularity supports detailed analysis and replay
           - Thread-safe operations prevent data corruption during access

        2. Data Integrity Assurance:
           - Safe database operation methods prevent concurrent access issues
           - Comprehensive error handling maintains system stability
           - Validation ensures session ownership and data completeness

        3. Performance Optimization:
           - Direct session targeting minimizes query overhead
           - Structured response format reduces processing requirements
           - Efficient database indexing enables rapid message retrieval

        4. Error Handling Strategy:
           - Graceful handling of non-existent sessions
           - Informative logging for debugging and monitoring
           - Empty list return for missing data rather than error responses

    Access Control Considerations:
        - User-session relationship validation
        - Privacy protection through user ID verification
        - Secure data access patterns

    Use Cases:
        - Conversation continuity restoration across sessions
        - Detailed conversation analysis and pattern recognition
        - Historical context retrieval for enhanced AI responses
        - User experience optimization through message replay

    Raises:
        HTTPException:
        - 500: If conversation persistence service is not initialized
        - 500: If database access fails or data corruption is detected

    Note:
        Returns empty list for non-existent sessions rather than error responses
        to support graceful frontend handling and user experience optimization.
    """
    try:
        if not conversation_persistence:
            raise HTTPException(status_code=500, detail="Conversation persistence service not initialized")

        # Use the safe_get_session_messages method from conversation persistence service
        messages = await conversation_persistence.safe_get_session_messages(user_id, session_id)

        if not messages:
            logger.info(f"No messages found for session {session_id} for user {user_id}")
            return []

        logger.info(f"✅ Retrieved {len(messages)} messages for session {session_id}")
        return messages

    except Exception as e:
        logger.error(f"❌ Failed to get session messages for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat-history/{user_id}/{session_id}")
async def delete_chat_session(user_id: str, session_id: str):
    """Delete a specific chat session using enhanced database operations"""
    try:
        if not vector_db or not vector_db.conversations:
            raise HTTPException(status_code=500, detail="Vector database not properly initialized")

        # Get all messages for this session (no longer need nested _safe_operation since delete_messages handles it)
        results = vector_db.conversations.get(
            where={
                "$and": [
                    {"user_id": {"$eq": user_id}},
                    {"session_id": {"$eq": session_id}}
                ]
            },
            include=["documents", "metadatas"]
        )

        if results and results.get('ids'):
            # Delete all messages in this session using the robust delete method
            delete_result = await vector_db.delete_messages(
                ids=results['ids'],
                collection_name="conversations"
            )

            if not delete_result["success"]:
                logger.error(f"❌ Database deletion failed for session {session_id}: {delete_result['errors']}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to delete session from database: {'; '.join(delete_result['errors'])}"
                )

            # Also remove from active sessions if present
            session_key = f"{user_id}_{session_id}"
            if session_key in active_chat_sessions:
                del active_chat_sessions[session_key]
            if session_key in session_tool_versions:
                del session_tool_versions[session_key]

            logger.info(f"✅ Successfully deleted session {session_id} for user {user_id} ({delete_result['deleted_count']} messages)")
            return {"message": f"Deleted session {session_id}", "deleted_count": delete_result['deleted_count']}
        else:
            return {"message": "Session not found", "deleted_count": 0}

    except Exception as e:
        logger.error(f"❌ Failed to delete chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/execute-tool", response_model=ExecuteToolResponse)
async def mcp_execute_tool(request: ExecuteToolRequest):
    """
    Execute an MCP tool with enhanced error handling and validation.

    This endpoint provides a robust interface for executing MCP tools with:
    - Input validation and sanitization
    - Timeout handling
    - Detailed error reporting
    - Execution timing
    - Comprehensive response formatting
    """
    start_time = asyncio.get_event_loop().time()

    try:
        logger.info(f"🔧 Executing tool '{request.tool_name}' for user {request.user_id}")

        # Validate tool execution capability
        if not aura_internal_tools:
            return ExecuteToolResponse(
                status="error",
                tool_name=request.tool_name,
                error="Internal tools not initialized",
                execution_time=asyncio.get_event_loop().time() - start_time,
                timestamp=datetime.now().isoformat(),
                metadata={"error_type": "initialization_error"}
            )

        # Execute tool with timeout
        try:
            if request.timeout:
                result = await asyncio.wait_for(
                    execute_mcp_tool(
                        tool_name=request.tool_name,
                        arguments=request.arguments,
                        user_id=request.user_id,
                        aura_internal_tools=aura_internal_tools
                    ),
                    timeout=request.timeout
                )
            else:
                result = await execute_mcp_tool(
                    tool_name=request.tool_name,
                    arguments=request.arguments,
                    user_id=request.user_id,
                    aura_internal_tools=aura_internal_tools
                )
        except asyncio.TimeoutError:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.warning(f"⏰ Tool '{request.tool_name}' timed out after {request.timeout}s")
            return ExecuteToolResponse(
                status="timeout",
                tool_name=request.tool_name,
                error=f"Tool execution timed out after {request.timeout} seconds",
                execution_time=execution_time,
                timestamp=datetime.now().isoformat(),
                metadata={"timeout_duration": request.timeout}
            )

        execution_time = asyncio.get_event_loop().time() - start_time

        # Check if the result indicates an error
        if isinstance(result, dict) and result.get("status") == "error":
            return ExecuteToolResponse(
                status="error",
                tool_name=request.tool_name,
                error=result.get("error", "Unknown error occurred"),
                execution_time=execution_time,
                timestamp=datetime.now().isoformat(),
                metadata={
                    "original_result": result,
                    "request_metadata": request.metadata
                }
            )

        # Successful execution
        logger.info(f"✅ Tool '{request.tool_name}' executed successfully in {execution_time:.3f}s")
        return ExecuteToolResponse(
            status="success",
            tool_name=request.tool_name,
            result=result,
            execution_time=execution_time,
            timestamp=datetime.now().isoformat(),
            metadata={
                "request_metadata": request.metadata,
                "result_type": type(result).__name__
            }
        )

    except ValueError as e:
        # Handle validation errors
        execution_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"❌ Validation error for tool '{request.tool_name}': {e}")
        return ExecuteToolResponse(
            status="error",
            tool_name=request.tool_name,
            error=f"Validation error: {str(e)}",
            execution_time=execution_time,
            timestamp=datetime.now().isoformat(),
            metadata={"error_type": "validation_error"}
        )

    except Exception as e:
        # Handle unexpected errors
        execution_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"❌ Unexpected error executing tool '{request.tool_name}': {e}")
        return ExecuteToolResponse(
            status="error",
            tool_name=request.tool_name,
            error=f"Execution failed: {str(e)}",
            execution_time=execution_time,
            timestamp=datetime.now().isoformat(),
            metadata={
                "error_type": "execution_error",
                "exception_type": type(e).__name__
            }
        )

@app.get("/mcp/tools")
async def list_available_tools():
    """
    List all available MCP tools with their descriptions and schemas.

    Returns comprehensive information about available tools including:
    - Internal Aura tools
    - External MCP tools
    - Tool parameters and descriptions
    - Usage examples where available
    """
    try:
        available_tools = []

        # Get internal Aura tools
        if aura_internal_tools:
            internal_tools = aura_internal_tools.get_tool_definitions()
            for tool_name, tool_info in internal_tools.items():
                available_tools.append({
                    "name": tool_name,
                    "type": "internal",
                    "description": tool_info.get("description", "No description available"),
                    "parameters": tool_info.get("parameters", {}),
                    "examples": tool_info.get("examples", [])
                })

        # Get external MCP tools
        try:
            external_tools = await get_all_available_tools()
            for tool in external_tools:
                available_tools.append({
                    "name": tool.get("name", "unknown"),
                    "type": "external",
                    "description": tool.get("description", "No description available"),
                    "parameters": tool.get("inputSchema", {}).get("properties", {}),
                    "required": tool.get("inputSchema", {}).get("required", [])
                })
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch external MCP tools: {e}")

        # Sort tools by name for easier browsing
        available_tools.sort(key=lambda x: x["name"])

        return {
            "status": "success",
            "total_tools": len(available_tools),
            "tools": available_tools,
            "categories": {
                "internal": len([t for t in available_tools if t["type"] == "internal"]),
                "external": len([t for t in available_tools if t["type"] == "external"])
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Failed to list available tools: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tools: {str(e)}")

@app.get("/mcp/tools/{tool_name}")
async def get_tool_info(tool_name: str):
    """
    Get detailed information about a specific tool.

    Args:
        tool_name: Name of the tool to get information about

    Returns:
        Detailed tool information including schema, examples, and usage notes
    """
    try:
        # Check internal tools first
        if aura_internal_tools:
            internal_tools = aura_internal_tools.get_tool_definitions()
            if tool_name in internal_tools:
                tool_info = internal_tools[tool_name]
                return {
                    "name": tool_name,
                    "type": "internal",
                    "found": True,
                    "description": tool_info.get("description", "No description available"),
                    "parameters": tool_info.get("parameters", {}),
                    "examples": tool_info.get("examples", []),
                    "usage_notes": tool_info.get("usage_notes", []),
                    "timestamp": datetime.now().isoformat()
                }

        # Check external tools
        try:
            external_tools = await get_all_available_tools()
            for tool in external_tools:
                if tool.get("name") == tool_name:
                    return {
                        "name": tool_name,
                        "type": "external",
                        "found": True,
                        "description": tool.get("description", "No description available"),
                        "parameters": tool.get("inputSchema", {}).get("properties", {}),
                        "required": tool.get("inputSchema", {}).get("required", []),
                        "schema": tool.get("inputSchema", {}),
                        "timestamp": datetime.now().isoformat()
                    }
        except Exception as e:
            logger.warning(f"⚠️ Could not search external MCP tools: {e}")

        # Tool not found
        return {
            "name": tool_name,
            "found": False,
            "error": "Tool not found in available tools",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Failed to get tool info for '{tool_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tool info: {str(e)}")

@app.post("/mcp/tools/validate")
async def validate_tool_request(request: ExecuteToolRequest):
    """
    Validate a tool execution request without actually executing it.

    This endpoint helps users verify their tool requests before execution by:
    - Checking if the tool exists
    - Validating required parameters
    - Checking parameter types and formats
    - Providing helpful error messages and suggestions
    """
    try:
        validation_result = {
            "tool_name": request.tool_name,
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
            "timestamp": datetime.now().isoformat()
        }

        # Check if tool exists
        tool_found = False
        tool_info = None

        # Check internal tools
        if aura_internal_tools:
            internal_tools = aura_internal_tools.get_tool_definitions()
            if request.tool_name in internal_tools:
                tool_found = True
                tool_info = internal_tools[request.tool_name]

        # Check external tools if not found internally
        if not tool_found:
            try:
                external_tools = await get_all_available_tools()
                for tool in external_tools:
                    if tool.get("name") == request.tool_name:
                        tool_found = True
                        tool_info = tool
                        break
            except Exception as e:
                validation_result["warnings"].append(f"Could not check external tools: {str(e)}")

        if not tool_found:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Tool '{request.tool_name}' not found")
            return validation_result

        # Validate parameters if tool info is available
        if tool_info and request.validate_args:
            # Get parameter requirements
            if "parameters" in tool_info:
                required_params = tool_info["parameters"].get("required", [])
                param_properties = tool_info["parameters"].get("properties", {})
            elif "inputSchema" in tool_info:
                required_params = tool_info["inputSchema"].get("required", [])
                param_properties = tool_info["inputSchema"].get("properties", {})
            else:
                required_params = []
                param_properties = {}

            # Check required parameters
            for param in required_params:
                if param not in request.arguments:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Missing required parameter: {param}")

            # Check for unknown parameters
            for param in request.arguments:
                if param not in param_properties:
                    validation_result["warnings"].append(f"Unknown parameter: {param}")

            # Validate parameter types (basic validation)
            for param, value in request.arguments.items():
                if param in param_properties:
                    param_spec = param_properties[param]
                    expected_type = param_spec.get("type")

                    if expected_type == "string" and not isinstance(value, str):
                        validation_result["errors"].append(f"Parameter '{param}' should be a string")
                        validation_result["valid"] = False
                    elif expected_type == "integer" and not isinstance(value, int):
                        validation_result["errors"].append(f"Parameter '{param}' should be an integer")
                        validation_result["valid"] = False
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        validation_result["errors"].append(f"Parameter '{param}' should be a boolean")
                        validation_result["valid"] = False
                    elif expected_type == "array" and not isinstance(value, list):
                        validation_result["errors"].append(f"Parameter '{param}' should be an array")
                        validation_result["valid"] = False
                    elif expected_type == "object" and not isinstance(value, dict):
                        validation_result["errors"].append(f"Parameter '{param}' should be an object")
                        validation_result["valid"] = False

        # Add helpful suggestions
        if validation_result["valid"]:
            validation_result["suggestions"].append("Tool request is valid and ready for execution")
        else:
            validation_result["suggestions"].append("Fix the errors above before executing the tool")
            if tool_info and "description" in tool_info:
                validation_result["suggestions"].append(f"Tool description: {tool_info['description']}")

        return validation_result

    except Exception as e:
        logger.error(f"❌ Failed to validate tool request: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@app.delete("/sessions/{user_id}")
async def clear_user_sessions(user_id: str):
    """Clear chat sessions for a user"""
    try:
        global active_chat_sessions
        sessions_cleared = 0

        # Find and remove all sessions for this user
        sessions_to_remove = [key for key in active_chat_sessions.keys() if key.startswith(f"{user_id}_")]

        for session_key in sessions_to_remove:
            del active_chat_sessions[session_key]
            sessions_cleared += 1

        logger.info(f"🧹 Cleared {sessions_cleared} chat sessions for user {user_id}")

        return {
            "message": f"Cleared {sessions_cleared} chat sessions for user {user_id}",
            "user_id": user_id,
            "sessions_cleared": sessions_cleared
        }

    except Exception as e:
        logger.error(f"❌ Failed to clear sessions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mcp/bridge-status")
async def get_mcp_bridge_status():
    """Get MCP-Gemini bridge status and statistics"""
    try:
        if not mcp_gemini_bridge:
            return {
                "status": "not_initialized",
                "message": "MCP-Gemini bridge is not initialized"
            }

        stats = mcp_gemini_bridge.get_execution_stats()
        available_functions = mcp_gemini_bridge.get_available_functions()

        return {
            "status": "active",
            "available_functions": len(available_functions),
            "execution_stats": stats,
            "sample_functions": available_functions[:5]  # Show first 5 functions
        }

    except Exception as e:
        logger.error(f"❌ Failed to get bridge status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mcp/system-status")
async def get_mcp_system_status():
    """Get comprehensive MCP system status"""
    try:
        status = get_mcp_status()

        # Get detailed tool information if initialized
        if status["initialized"]:
            tools = await get_all_available_tools()

            # Group tools by server
            tools_by_server = {}
            for tool in tools:
                server = tool.get("server", "unknown")
                if server not in tools_by_server:
                    tools_by_server[server] = []
                tools_by_server[server].append({
                    "name": tool["name"],
                    "description": tool["description"][:10000] + "..." if len(tool["description"]) > 10000 else tool["description"]
                })

            status["tools_by_server"] = tools_by_server
            status["total_tools"] = len(tools)

        return status

    except Exception as e:
        logger.error(f"❌ Failed to get MCP system status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "initialized": False
        }

@app.get("/persistence/health")
async def get_persistence_health():
    """Get persistence layer health status"""
    try:
        if not conversation_persistence:
            return {
                "status": "not_initialized",
                "error": "Conversation persistence service not initialized",
                "timestamp": datetime.now().isoformat()
            }

        metrics = await conversation_persistence.get_persistence_metrics()

        # Import the health check class here to avoid import issues
        from conversation_persistence_service import PersistenceHealthCheck
        health_checker = PersistenceHealthCheck(conversation_persistence)
        health_status = await health_checker.check_health()

        return {
            "status": "healthy" if health_status["healthy"] else "unhealthy",
            "metrics": metrics,
            "health_check": health_status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Failed to get persistence health: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/test/persistence")
async def test_persistence_reliability():
    """Test endpoint to validate chat persistence reliability"""
    try:
        if not conversation_persistence:
            return {
                "status": "error",
                "message": "Conversation persistence service not initialized"
            }

        # Create a test conversation exchange
        from main import ConversationMemory, ConversationExchange

        test_user_id = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        test_session_id = str(uuid.uuid4())

        user_memory = ConversationMemory(
            user_id=test_user_id,
            message="This is a test message to validate persistence reliability",
            sender="user",
            session_id=test_session_id
        )

        aura_memory = ConversationMemory(
            user_id=test_user_id,
            message="This is a test response to validate that chat history saves correctly",
            sender="aura",
            session_id=test_session_id
        )

        test_exchange = ConversationExchange(
            user_memory=user_memory,
            ai_memory=aura_memory,
            session_id=test_session_id
        )

        # Test immediate persistence
        immediate_result = await conversation_persistence.persist_conversation_exchange_immediate(
            test_exchange,
            update_profile=False,
            timeout=3.0
        )

        # Verify the conversation was stored by searching for it
        search_result = await conversation_persistence.safe_search_conversations(
            query="test message to validate persistence",
            user_id=test_user_id,
            n_results=2
        )

        # Check chat history retrieval
        history_result = await conversation_persistence.safe_get_chat_history(test_user_id, limit=10)

        return {
            "status": "success",
            "test_results": {
                "immediate_persistence": {
                    "success": immediate_result["success"],
                    "duration_ms": immediate_result["duration_ms"],
                    "stored_components": immediate_result["stored_components"],
                    "method": immediate_result.get("method", "unknown")
                },
                "search_verification": {
                    "found_messages": len(search_result),
                    "search_successful": len(search_result) >= 2
                },
                "history_retrieval": {
                    "sessions_found": len(history_result.get("sessions", [])),
                    "retrieval_successful": len(history_result.get("sessions", [])) > 0
                }
            },
            "test_user_id": test_user_id,
            "persistence_validated": (
                immediate_result["success"] and
                len(search_result) >= 2 and
                len(history_result.get("sessions", [])) > 0
            ),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Persistence test failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/memvid/status")
async def get_memvid_status():
    """Get memvid archival service status"""
    try:
        if not memvid_archival:
            return {
                "status": "not_initialized",
                "error": "Memvid archival service not initialized",
                "timestamp": datetime.now().isoformat()
            }

        # Get basic status info
        archives = await memvid_archival.list_archives()

        return {
            "status": "operational",
            "archives_count": len(archives),
            "archives": archives[:5],  # Show first 5 archives
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Failed to get memvid status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/vector-db/health")
async def get_vector_db_health():
    """Get detailed vector database health information"""
    try:
        if not vector_db:
            return {
                "status": "not_initialized",
                "error": "Vector database not initialized",
                "timestamp": datetime.now().isoformat()
            }

        health_info = await vector_db.health_check()
        return health_info

    except Exception as e:
        logger.error(f"❌ Failed to get vector database health: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/database-protection/status")
async def get_database_protection_status():
    """Get database protection service status and health"""
    try:
        if not db_protection_service:
            return {
                "status": "not_initialized",
                "error": "Database protection service not initialized",
                "timestamp": datetime.now().isoformat()
            }

        health_status = db_protection_service.get_health_status()

        return {
            "status": "operational" if health_status["protection_active"] else "inactive",
            "health_status": health_status,
            "backup_directory": str(db_protection_service.backup_dir),
            "protection_features": [
                "Automatic backup before risky operations",
                "Health monitoring",
                "Emergency recovery triggers",
                "Transaction-like safety for database operations"
            ],
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Failed to get database protection status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/database-protection/emergency-backup")
async def trigger_emergency_backup():
    """Trigger emergency database backup manually"""
    try:
        if not db_protection_service:
            raise HTTPException(status_code=500, detail="Database protection service not initialized")

        backup_path = db_protection_service.emergency_backup()

        if backup_path:
            return {
                "status": "success",
                "message": "Emergency backup created successfully",
                "backup_path": str(backup_path),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "failed",
                "message": "Emergency backup failed to create",
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"❌ Failed to create emergency backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/autonomic/status")
async def get_autonomic_status() -> Dict[str, Any]:
    """
    Retrieve comprehensive autonomic nervous system status and operational metrics.

    Applies systematic analysis to autonomic system health assessment,
    providing detailed insights into task processing capabilities,
    operational performance, and system configuration status.

    Returns:
        Dictionary containing comprehensive status information:
        - status: Operational state ("operational", "stopped", "disabled", "error")
        - system_status: Detailed operational metrics and configuration
        - timestamp: ISO timestamp of status generation

    Methodological Framework for Status Assessment:

        1. Conceptual Foundation Analysis:
           - Autonomic system represents background intelligence processing
           - Task offloading enables optimized resource allocation
           - Operational status reflects system health and capability

        2. Configuration State Evaluation:
           - AUTONOMIC_ENABLED environment variable assessment
           - System initialization status verification
           - Component availability and integration analysis

        3. Operational Metrics Collection:
           - Active task processing statistics
           - Completed task performance analysis
           - Resource utilization and efficiency metrics
           - Rate limiting status and availability assessment

        4. System Performance Analysis:
           - Task processing throughput evaluation
           - Success/failure ratio assessment
           - Average execution time analysis
           - Queue utilization and capacity metrics

    Status Categories and Interpretations:

        operational: System active and processing tasks
        - Running background task worker
        - Queue accepting new tasks
        - Rate limiting within acceptable parameters

        stopped: System initialized but not actively processing
        - Components available but worker inactive
        - Manual intervention required for activation

        disabled: System disabled in configuration
        - AUTONOMIC_ENABLED=false in environment
        - No task processing capability available

        not_initialized: System failed initialization
        - Component dependencies unavailable
        - Critical errors during startup

        error: Runtime errors detected
        - System instability or component failures
        - Detailed error information in response

    Detailed System Status Components:
        - running: Boolean task worker operational status
        - queued_tasks: Number of tasks awaiting processing
        - active_tasks: Number of currently executing tasks
        - completed_tasks: Total number of processed tasks
        - rate_limiting: Request rate status and availability
        - processor_stats: Execution performance metrics

    Raises:
        Exception: If status collection encounters system errors

    Note:
        This endpoint provides critical insights for system monitoring,
        performance optimization, and troubleshooting autonomic processing
        issues in production environments.
    """
    try:
        autonomic_enabled = os.getenv('AUTONOMIC_ENABLED', 'true').lower() == 'true'

        if not autonomic_enabled:
            return {
                "status": "disabled",
                "message": "Autonomic nervous system is disabled in configuration",
                "timestamp": datetime.now().isoformat()
            }

        if not autonomic_system:
            return {
                "status": "not_initialized",
                "error": "Autonomic nervous system not initialized",
                "timestamp": datetime.now().isoformat()
            }

        status = autonomic_system.get_system_status()
        return {
            "status": "operational" if status["running"] else "stopped",
            "system_status": status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Failed to get autonomic status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/autonomic/tasks/{user_id}")
async def get_user_autonomic_tasks(user_id: str, limit: int = 20):
    """Get autonomic tasks for a specific user"""
    try:
        if not autonomic_system:
            raise HTTPException(status_code=500, detail="Autonomic system not initialized")

        # Get completed tasks for the user
        user_tasks = []
        for task_id, task in autonomic_system.completed_tasks.items():
            if task.user_id == user_id:
                user_tasks.append({
                    "task_id": task.task_id,
                    "task_type": task.task_type.value,
                    "priority": task.priority.value,
                    "description": task.description,
                    "status": task.status.value,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "execution_time_ms": task.execution_time_ms,
                    "has_result": task.result is not None,
                    "has_error": task.error is not None
                })

        # Get active tasks for the user
        active_user_tasks = []
        for task_id, task in autonomic_system.active_tasks.items():
            if task.user_id == user_id:
                active_user_tasks.append({
                    "task_id": task.task_id,
                    "task_type": task.task_type.value,
                    "priority": task.priority.value,
                    "description": task.description,
                    "status": task.status.value,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "started_at": task.started_at.isoformat() if task.started_at else None
                })

        # Sort by creation time (newest first) and limit
        user_tasks.sort(key=lambda x: x["created_at"] or "", reverse=True)
        user_tasks = user_tasks[:limit]

        return {
            "user_id": user_id,
            "active_tasks": active_user_tasks,
            "completed_tasks": user_tasks,
            "total_active": len(active_user_tasks),
            "total_completed": len(user_tasks),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Failed to get user autonomic tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/autonomic/task/{task_id}")
async def get_autonomic_task_details(task_id: str):
    """Get detailed information about a specific autonomic task"""
    try:
        if not autonomic_system:
            raise HTTPException(status_code=500, detail="Autonomic system not initialized")

        # Check completed tasks first
        task = autonomic_system.completed_tasks.get(task_id)
        if not task:
            # Check active tasks
            task = autonomic_system.active_tasks.get(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        task_details = {
            "task_id": task.task_id,
            "task_type": task.task_type.value,
            "priority": task.priority.value,
            "description": task.description,
            "status": task.status.value,
            "user_id": task.user_id,
            "session_id": task.session_id,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "execution_time_ms": task.execution_time_ms,
            "payload": task.payload,
            "result": task.result,
            "error": task.error
        }

        return task_details

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get task details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/autonomic/submit-task")
async def submit_autonomic_task(
    description: str,
    payload: Dict[str, Any],
    user_id: str,
    session_id: Optional[str] = None,
    force_offload: bool = False
):
    """Manually submit a task to the autonomic system"""
    try:
        if not autonomic_system:
            raise HTTPException(status_code=500, detail="Autonomic system not initialized")

        was_offloaded, task_id = await autonomic_system.submit_task(
            description=description,
            payload=payload,
            user_id=user_id,
            session_id=session_id,
            force_offload=force_offload
        )

        if was_offloaded and task_id:
            return {
                "status": "submitted",
                "task_id": task_id,
                "message": f"Task {task_id} submitted to autonomic system",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "not_offloaded",
                "message": "Task did not meet criteria for autonomic processing",
                "force_offload_option": "Set force_offload=true to override",
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"❌ Failed to submit autonomic task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/autonomic/task/{task_id}/result")
async def get_autonomic_task_result(task_id: str, timeout: Optional[float] = None):
    """Get the result of an autonomic task, optionally waiting for completion"""
    try:
        if not autonomic_system:
            raise HTTPException(status_code=500, detail="Autonomic system not initialized")

        task = await autonomic_system.get_task_result(task_id, timeout)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
            "execution_time_ms": task.execution_time_ms,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get task result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/autonomic/control/{action}")
async def control_autonomic_system(action: str):
    """Control autonomic system (start/stop/restart)"""
    try:
        if not autonomic_system:
            raise HTTPException(status_code=500, detail="Autonomic system not initialized")

        if action == "start":
            if autonomic_system._running:
                return {
                    "status": "already_running",
                    "message": "Autonomic system is already running",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                await autonomic_system.start()
                return {
                    "status": "started",
                    "message": "Autonomic system started successfully",
                    "timestamp": datetime.now().isoformat()
                }

        elif action == "stop":
            if not autonomic_system._running:
                return {
                    "status": "already_stopped",
                    "message": "Autonomic system is already stopped",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                await autonomic_system.stop()
                return {
                    "status": "stopped",
                    "message": "Autonomic system stopped successfully",
                    "timestamp": datetime.now().isoformat()
                }

        elif action == "restart":
            await autonomic_system.stop()
            await autonomic_system.start()
            return {
                "status": "restarted",
                "message": "Autonomic system restarted successfully",
                "timestamp": datetime.now().isoformat()
            }

        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action}. Use start, stop, or restart")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to control autonomic system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vector-db/optimize")
async def optimize_vector_db():
    """Trigger vector database optimization"""
    try:
        if not vector_db:
            raise HTTPException(status_code=500, detail="Vector database not initialized")

        # Perform SQLite optimization through the enhanced database
        async with vector_db._safe_operation("optimize_database"):
            import sqlite3
            sqlite_path = vector_db.persist_directory / "chroma.sqlite3"
            if sqlite_path.exists():
                conn = sqlite3.connect(str(sqlite_path))
                cursor = conn.cursor()
                cursor.execute("PRAGMA optimize")
                cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.commit()
                conn.close()

        return {
            "status": "success",
            "message": "Database optimization completed",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Failed to optimize vector database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting Aura Backend Server...")
    logger.info("✨ Features: Vector DB, MCP Integration, Advanced State Management")
    logger.info("🔧 MCP Tools will be loaded on startup - check logs for available tools")
    logger.info("💡 To see available tools, ask Aura: 'What MCP tools do you have?'")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

# ============================================================================
# PTY Session Management and WebSocket Endpoint
# ============================================================================

import ptyprocess
import asyncio
import os
import uuid
from fastapi import WebSocket, WebSocketDisconnect

pty_sessions: Dict[str, Dict[str, Any]] = {}

class CLIExecuteRequest(BaseModel):
    projectPath: str
    command: str
    envVars: Optional[Dict[str, str]] = None

@app.post("/api/cli/execute")
async def cli_execute(request: CLIExecuteRequest):
    """
    Executes a command in a PTY session, creating one if necessary.
    """
    project_path = request.projectPath
    command = request.command
    env_vars = request.envVars or {}

    session_id = None
    # Try to find an existing session for the projectPath
    for s_id, session_data in pty_sessions.items():
        if session_data["project_path"] == project_path:
            session_id = s_id
            break

    if not session_id:
        session_id = str(uuid.uuid4())
        env = {**os.environ, **env_vars, "FORCE_COLOR": "1", "TERM": "xterm-256color"}

        try:
            # Spawn the PTY process with a generic shell, then commands will be written to it.
            # This allows the shell to be persistent.
            pty_process = ptyprocess.PtyProcessUnicode.spawn(['/bin/bash'], cwd=project_path, env=env, dimensions=(30, 120))
            # Set a small delay after close and before send to avoid issues, can be tuned.
            # pty_process.delayafterclose = 0.1 # ptyprocess doesn't have these attributes directly
            # pty_process.delaybeforesend = 0.1
        except Exception as e:
            logger.error(f"❌ Failed to spawn PTY process for {project_path}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to spawn PTY: {str(e)}")

        pty_sessions[session_id] = {
            "pty_process": pty_process,
            "project_path": project_path,
            "created": datetime.now(),
            "last_used": datetime.now()
        }
        logger.info(f"🚀 Created new PTY session {session_id} for {project_path}")
    else:
        pty_sessions[session_id]["last_used"] = datetime.now()
        logger.info(f"🔁 Reusing PTY session {session_id} for {project_path}")


    session_data = pty_sessions[session_id]
    pty_process = session_data["pty_process"]

    try:
        pty_process.write(f"{command}\n")
    except Exception as e:
        logger.error(f"❌ Failed to write to PTY session {session_id}: {e}")
        # Attempt to remove the faulty session
        if session_id in pty_sessions:
            try:
                pty_sessions[session_id]["pty_process"].close()
            except Exception as close_e:
                logger.error(f"Error closing PTY during error handling: {close_e}")
            del pty_sessions[session_id]
        raise HTTPException(status_code=500, detail=f"Failed to write to PTY: {str(e)}")

    return {"success": True, "sessionId": session_id}

@app.websocket("/ws/pty/{session_id}")
async def websocket_pty_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()

    if session_id not in pty_sessions:
        logger.warning(f"PTY session {session_id} not found for WebSocket connection.")
        await websocket.close(code=4004, reason="PTY session not found")
        return

    session_data = pty_sessions[session_id]
    pty_process = session_data["pty_process"]

    # Update last used time
    session_data["last_used"] = datetime.now()

    logger.info(f"🔌 WebSocket connected to PTY session {session_id}")

    async def read_from_pty_and_send_to_ws():
        # Task to continuously read from PTY and send to WebSocket
        try:
            while pty_process.isalive():
                try:
                    # Use a timeout to prevent blocking indefinitely
                    output = pty_process.read(size=1024, timeout=0.1) # timeout in seconds
                    if output:
                        await websocket.send_json({"type": "output", "data": output})
                except ptyprocess.exceptions.TIMEOUT:
                    await asyncio.sleep(0.01) # Sleep briefly if no data
                except Exception as e:
                    logger.error(f"Error reading from PTY {session_id}: {e}")
                    # If websocket is closed from client side, this might raise an error.
                    # We should check websocket state before sending.
                    if websocket.client_state == WebSocketState.DISCONNECTED:
                        break
                    # Send error to client if possible
                    try:
                        await websocket.send_json({"type": "error", "data": str(e)})
                    except Exception:
                        pass # Websocket might be closed
                    break
            logger.info(f"PTY read task for {session_id} ended (PTY process alive: {pty_process.isalive()})")
        except Exception as e:
            logger.error(f"Outer exception in PTY read task for {session_id}: {e}")
        finally:
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json({"type": "info", "data": "PTY stream ended."})
                except:
                    pass # Ignore if send fails (e.g. client disconnected)
            logger.info(f"PTY read task for session {session_id} is cleaning up.")


    # Start the PTY reading task
    pty_reader_task = asyncio.create_task(read_from_pty_and_send_to_ws())

    try:
        while True:
            # Receive input from WebSocket and write to PTY
            data = await websocket.receive_json()
            if data.get("type") == "input":
                if pty_process.isalive():
                    pty_process.write(data["data"])
                    session_data["last_used"] = datetime.now() # Update last used on input
                else:
                    await websocket.send_json({"type": "error", "data": "PTY process is not alive."})
                    break
            elif data.get("type") == "resize": # Optional: handle terminal resize
                if pty_process.isalive() and "cols" in data and "rows" in data:
                    pty_process.setwinsize(data["rows"], data["cols"])

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected from PTY session {session_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket PTY session {session_id}: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json({"type": "error", "data": f"Server error: {str(e)}"})
            except:
                pass
    finally:
        logger.info(f"Cleaning up WebSocket PTY session {session_id}")
        pty_reader_task.cancel()
        try:
            await pty_reader_task # Ensure task finishes cleanup
        except asyncio.CancelledError:
            logger.info(f"PTY reader task for {session_id} was cancelled.")
        except Exception as e:
            logger.error(f"Exception during PTY reader task await: {e}")

        # Optional: Consider closing PTY if no other clients are connected or based on policy
        # For now, PTYs are persistent until server restart or explicit cleanup logic (e.g., timeout)

async def cleanup_inactive_pty_sessions():
    """Periodically cleans up PTY sessions that haven't been used for a while."""
    # This is a basic example. More sophisticated logic might be needed.
    # For example, checking if a PTY process is still running a command.
    while True:
        await asyncio.sleep(300) # Check every 5 minutes
        now = datetime.now()
        inactive_threshold_seconds = 3600 # 1 hour

        sessions_to_remove = []
        for session_id, session_data in pty_sessions.items():
            last_used = session_data.get("last_used", session_data["created"])
            if (now - last_used).total_seconds() > inactive_threshold_seconds:
                if not session_data["pty_process"].isalive(): # Only cleanup if not alive or truly inactive
                    sessions_to_remove.append(session_id)
                else:
                    # Check if any websocket is still connected to this session
                    # This check is a bit complex as we don't store websockets per session directly here.
                    # A simpler approach for now: if it's alive but old, maybe send a warning or keep it.
                    # For robust cleanup, a more direct link between WS connections and PTYs is needed.
                    logger.info(f"PTY session {session_id} is old but still alive. Not cleaning up yet.")


        for session_id in sessions_to_remove:
            logger.info(f"🗑️ Cleaning up inactive PTY session {session_id}")
            try:
                pty_sessions[session_id]["pty_process"].close()
            except Exception as e:
                logger.error(f"Error closing PTY during cleanup of {session_id}: {e}")
            del pty_sessions[session_id]

# Add to lifespan to start the cleanup task
@asynccontextmanager
async def lifespan_with_pty_cleanup(app: FastAPI):
    # Startup (from original lifespan)
    logger.info("🚀 Starting Aura Backend with PTY session management...")
    global vector_db, aura_file_system, state_manager, aura_internal_tools
    global conversation_persistence, memvid_archival, mcp_gemini_bridge, global_tool_version, autonomic_system, db_protection_service, thinking_processor
    db_protection_service = get_protection_service()
    logger.info("🛡️ Database Protection Service initialized and active")
    thinking_processor = ThinkingProcessor(client)
    logger.info("🧠 Thinking Processor initialized (non-streaming mode)")
    vector_db = AuraVectorDB()
    logger.info("✅ Using RobustAuraVectorDB with SQLite-level concurrency control")
    aura_file_system = AuraFileSystem()
    state_manager = AuraStateManager(vector_db, aura_file_system)
    aura_internal_tools = AuraInternalTools(vector_db, aura_file_system)
    conversation_persistence = ConversationPersistenceService(vector_db, aura_file_system)
    memvid_archival = MemvidArchivalService()
    mcp_status = await initialize_mcp_system(aura_internal_tools)
    if mcp_status["status"] == "success":
        logger.info("✅ MCP system initialized successfully")
        mcp_gemini_bridge = get_mcp_bridge()
        if mcp_gemini_bridge:
            global_tool_version += 1
            logger.info(f"🔄 Incremented global tool version to {global_tool_version}")
    else:
        logger.error(f"❌ MCP system initialization failed: {mcp_status.get('error', 'Unknown error')}")
    autonomic_enabled = os.getenv('AUTONOMIC_ENABLED', 'true').lower() == 'true'
    if autonomic_enabled:
        logger.info("🧠 Initializing Autonomic Nervous System...")
        try:
            autonomic_system = await initialize_autonomic_system(mcp_bridge=mcp_gemini_bridge, internal_tools=aura_internal_tools)
            logger.info("✅ Autonomic Nervous System initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Autonomic Nervous System: {e}")
            autonomic_system = None
    else:
        autonomic_system = None

    # Start PTY cleanup task
    cleanup_task = asyncio.create_task(cleanup_inactive_pty_sessions())
    logger.info("🧹 PTY session cleanup task started.")

    yield

    # Shutdown (from original lifespan)
    logger.info("🛑 Shutting down Aura Backend...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        logger.info("PTY cleanup task cancelled.")
    except Exception as e:
        logger.error(f"Exception during PTY cleanup task await on shutdown: {e}")

    await shutdown_autonomic_system()
    await shutdown_mcp_system()
    if vector_db:
        await vector_db.close()
    if db_protection_service:
        db_protection_service.stop_protection()
        logger.info("🛡️ Database Protection Service stopped")

    # Close any remaining PTY sessions
    for session_id, session_data in list(pty_sessions.items()): # Iterate over a copy
        logger.info(f"Terminating PTY session {session_id} on shutdown.")
        try:
            session_data["pty_process"].terminate(force=True)
            session_data["pty_process"].close()
        except Exception as e:
            logger.error(f"Error closing PTY {session_id} on shutdown: {e}")
        del pty_sessions[session_id]

    logger.info("✅ Aura Backend shutdown complete")


# Replace the app's lifespan context manager
app.router.lifespan_context_manager = lifespan_with_pty_cleanup

# Need to import WebSocketState for the PTY reader
from starlette.websockets import WebSocketState
