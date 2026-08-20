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

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sqlite3
import sys
import uuid
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Tuple

import aiofiles
import numpy as np
import uvicorn
from fastapi import APIRouter, BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add the parent directory to sys.path to support absolute imports from aura_backend package
# when running main.py directly from the aura_backend directory.
_current_dir = Path(__file__).resolve().parent
if _current_dir.name == "aura_backend":
    _parent_dir = _current_dir.parent
    if str(_parent_dir) not in sys.path:
        sys.path.insert(0, str(_parent_dir))


# Import-light domain and request types only. Resource-owning integrations are
# imported by the lifespan composition path, never while importing this module.
from aura_backend.conversation_persistence_service import (  # noqa: E402
    ConversationExchange,
    ConversationPersistenceService,
    PersistenceHealthCheck,
)
from aura_backend.conversation import (  # noqa: E402
    AsekeComponent,
    CognitiveState,
    EmotionalIntensity as EmotionalIntensity,
    EmotionalStateData,
    detect_aura_cognitive_focus,
    detect_aura_emotion,
    detect_user_emotion,
)
from aura_backend.providers.base import (  # noqa: E402
    BaseProvider,
    Message,
    ProviderHealth,
    ProviderHealthStatus,
    ProviderMessage,
    ProviderRequest,
    ProviderResult,
)
from aura_backend.providers.config import ProviderKind  # noqa: E402
from aura_backend.providers.errors import (  # noqa: E402
    ProviderErrorCode,
    ProviderFailure,
)
from aura_backend.providers.tools import ToolCatalog  # noqa: E402
from aura_backend.runtime.health import (  # noqa: E402
    HealthSnapshot,
    aggregate_health,
    public_readiness,
)
from aura_backend.runtime_security import (  # noqa: E402
    StoragePathError,
    allowed_browser_origins,
    safe_export_path,
    safe_profile_path,
    server_host,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The configured value is applied by the lifespan-owned runtime builder. Keeping
# the compatibility default here lets route definitions remain importable without
# reading process configuration or logging environment-derived values.
thinking_budget = -1

# The client and provider will be initialized in the lifespan
provider: Optional[BaseProvider] = None
thinking_processor: Any = None
mcp_gemini_bridge: Any = None
client: Any = None
embedding_service: Any = None

# Transitional integration callables are populated only by lifespan startup.
execute_mcp_tool: Any = None
get_all_available_tools: Any = None
get_mcp_status: Any = None
_mcp_provider_client: Any = None


def ensure_json_serializable(data: Any) -> Any:
    """Basic fallback for JSON serialization"""

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

    async def save_user_profile(
        self, user_id: str, profile_data: Dict[str, Any]
    ) -> str:
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
            profile_path = safe_profile_path(self.base_path, user_id)

            # Add metadata
            profile_data.update(
                {"last_updated": datetime.now().isoformat(), "user_id": user_id}
            )

            async with aiofiles.open(profile_path, "w") as f:
                await f.write(json.dumps(profile_data, indent=2, default=str))

            logger.info("💾 Saved user profile: %s", user_id)
            return str(profile_path)

        except Exception as e:
            logger.error("❌ Failed to save user profile: %s", e)
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
            profile_path = safe_profile_path(self.base_path, user_id)

            if not profile_path.exists():
                return None

            async with aiofiles.open(profile_path, "r") as f:
                content = await f.read()
                return json.loads(content)

        except StoragePathError:
            logger.warning("Rejected invalid user profile path")
            raise
        except Exception as e:
            logger.error("❌ Failed to load user profile: %s", e)
            return None

    async def export_conversation_history(
        self, user_id: str, output_format: str = "json"
    ) -> str:
        """
        Export conversation history in various formats for data portability.

        Writes the currently captured Phase 1 baseline. Conversation and pattern
        arrays remain empty until later lifecycle work wires their data sources.

        Args:
            user_id: Unique identifier for the user whose data to export
            output_format: Output format specification (default: "json")
                   Supported formats: "json", "csv", "xml", "yaml"

        Returns:
            Absolute path to the generated export file

        Export Structure:
            - user_id: User identifier
            - export_timestamp: ISO timestamp of export generation
            - output_format: Export format specification
            - conversations: Empty Phase 1 baseline array
            - emotional_patterns: Empty Phase 1 baseline array
            - cognitive_patterns: Empty Phase 1 baseline array

        Raises:
            ValueError: If output_format is not supported
            OSError: If file write operations fail
            json.JSONEncodeError: If data serialization fails

        Example:
            >>> fs = AuraFileSystem()
            >>> export_path = await fs.export_conversation_history("user123", "json")
            >>> assert export_path.endswith(".json")
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = safe_export_path(
                self.base_path,
                user_id,
                timestamp,
                output_format,
            )
            safe_format = export_path.suffix.removeprefix(".")

            # This would integrate with the vector DB to get conversation history
            export_data = {
                "user_id": user_id,
                "export_timestamp": datetime.now().isoformat(),
                "format": safe_format,
                "conversations": [],  # Would be populated from vector DB
                "emotional_patterns": [],  # Would be populated from vector DB
                "cognitive_patterns": [],  # Would be populated from vector DB
            }

            async with aiofiles.open(export_path, "w") as f:
                await f.write(json.dumps(export_data, indent=2, default=str))

            logger.info("📤 Exported conversation history: %s", export_path.name)
            return str(export_path)

        except Exception as e:
            logger.error("❌ Failed to export conversation history: %s", e)
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

    def __init__(self, vector_db: Any, aura_file_system: AuraFileSystem) -> None:
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
        new_state: EmotionalStateData,
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
                logger.info(
                    f"🎭 Emotional transition: {old_state.name} → {new_state.name}"
                )

                # Trigger specific actions based on transitions
                await self._handle_emotional_transition(user_id, old_state, new_state)

            # Update user profile
            profile = await self.aura_file_system.load_user_profile(user_id) or {}
            profile["last_emotional_state"] = asdict(new_state)
            await self.aura_file_system.save_user_profile(user_id, profile)

        except Exception as e:
            logger.error("❌ Failed to handle emotional state change: %s", e)

    async def _handle_emotional_transition(
        self, user_id: str, old_state: EmotionalStateData, new_state: EmotionalStateData
    ):
        """Handle specific emotional transitions"""
        # Define concerning transitions
        concerning_transitions = [
            ("Happy", "Sad"),
            ("Joy", "Angry"),
            ("Peace", "Angry"),
            ("Normal", "Sad"),
        ]

        transition = (old_state.name, new_state.name)

        if transition in concerning_transitions:
            # Store intervention recommendation
            recommendation = {
                "type": "emotional_support",
                "transition": transition,
                "timestamp": datetime.now().isoformat(),
                "suggestion": f"Noticed transition from {old_state.name} to {new_state.name}. Consider gentle conversation topics.",
            }

            # Log the recommendation details and store for potential future use
            logger.info(
                f"🔔 Emotional support recommendation for {user_id}: {recommendation['suggestion']}"
            )

    async def on_cognitive_focus_change(
        self,
        user_id: str,
        old_focus: Optional[CognitiveState],
        new_focus: CognitiveState,
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
            embedding = embedding_service.encode_single(focus_text)

            if new_focus.timestamp is None:
                new_focus.timestamp = datetime.now()
            doc_id = f"cognitive_{user_id}_{new_focus.timestamp.isoformat()}_{uuid.uuid4().hex[:8]}"

            metadata = {
                "user_id": user_id,
                "focus": new_focus.focus.value,
                "description": new_focus.description,
                "context": new_focus.context,
                "timestamp": new_focus.timestamp.isoformat(),
            }

            await self.vector_db.store_cognitive_pattern(
                focus_text, embedding, metadata, doc_id
            )

            logger.info("🧠 Stored cognitive focus: %s", new_focus.focus.value)

        except Exception as e:
            logger.error("❌ Failed to handle cognitive focus change: %s", e)


# API Models
class ConversationRequest(BaseModel):
    """
    Request model for initiating a conversation.

    Fields:
        user_id: Unique identifier for the user.
        message: The user's input message.
        session_id: Optional session identifier for conversation continuity.
    """

    user_id: Annotated[str, Field(description="Unique identifier for the user")]
    message: Annotated[str, Field(description="User's message content")]
    session_id: Annotated[
        Optional[str], Field(default=None, description="Optional session identifier")
    ] = None


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

    response: Annotated[str, Field(description="The generated AI response text")]
    emotional_state: Annotated[
        Dict[str, Any], Field(description="Detected emotional state information")
    ]
    cognitive_state: Annotated[
        Dict[str, Any], Field(description="Cognitive focus analysis results")
    ]
    session_id: Annotated[
        str, Field(description="Identifier for the conversation session")
    ]
    thinking_content: Annotated[
        Optional[str], Field(default=None, description="AI reasoning process content")
    ] = None
    thinking_metrics: Annotated[
        Optional[Dict[str, Any]],
        Field(default=None, description="Metrics about thinking processing"),
    ] = None
    has_thinking: Annotated[
        bool, Field(default=False, description="Whether thinking data was captured")
    ] = False


class SearchRequest(BaseModel):
    """
    Request model for searching conversation memories.

    Fields:
        user_id: Unique identifier for the user whose memories to search.
        query: Search query string.
        n_results: Number of results to return (default: 25).
    """

    user_id: Annotated[str, Field(description="Unique identifier for the user")]
    query: Annotated[str, Field(description="Search query string")]
    n_results: Annotated[
        int, Field(default=5000, description="Number of results to return")
    ] = 5000


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
vector_db: Any = None
aura_file_system: Optional[AuraFileSystem] = None
state_manager: Optional[AuraStateManager] = None
aura_internal_tools: Any = None
conversation_persistence: Optional[ConversationPersistenceService] = None
memvid_archival: Any = None
mcp_gemini_bridge: Any = None
autonomic_system: Any = None
db_protection_service: Any = None
thinking_processor: Any = None
provider: Optional[BaseProvider] = None

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
    available_tools: Optional[List[Dict[str, Any]]] = None,
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
            server = tool.get("server", "unknown")
            if server not in tools_by_server:
                tools_by_server[server] = []
            tools_by_server[server].append(tool)

        # Add external tools section to system instruction
        if tools_by_server:
            instruction += "\n\n**External MCP Tools Available:**\n"
            instruction += "You also have access to these external MCP tools for extended capabilities:\n\n"

            for server, server_tools in tools_by_server.items():
                if (
                    server != "aura-internal"
                ):  # Skip internal tools as they're already listed
                    instruction += f"**From {server} server:**\n"
                    for (
                        tool
                    ) in server_tools:  # Use ALL tools - don't artificially limit!
                        clean_name = tool.get("clean_name", tool["name"])
                        description = tool.get("description", "No description")
                        instruction += f"- **{clean_name}** - {description}\n"
                    instruction += "\n"

    if user_name:
        instruction += f"\n\nYour current user's name is {user_name}. Use it naturally to personalize the shared Knowledge Substrate (KS)."

    if memory_context:
        instruction += f"\n\n**Relevant Context from Previous Interactions:**\n{memory_context}\n\nUse this context naturally to maintain conversation continuity."

    return instruction


# FastAPI application lifecycle and composition
@dataclass(slots=True)
class _LegacyRuntimeResources:
    """Resources still consumed through compatibility globals during Phase 2."""

    mcp_router: Any
    tool_catalog: ToolCatalog | None = None


def _clear_runtime_aliases() -> None:
    """Remove compatibility references without constructing replacement resources."""
    global vector_db, aura_file_system, state_manager, aura_internal_tools
    global conversation_persistence, memvid_archival, mcp_gemini_bridge
    global autonomic_system, db_protection_service, thinking_processor, provider
    global client, embedding_service, execute_mcp_tool, get_all_available_tools
    global get_mcp_status, _mcp_provider_client

    vector_db = None
    aura_file_system = None
    state_manager = None
    aura_internal_tools = None
    conversation_persistence = None
    memvid_archival = None
    mcp_gemini_bridge = None
    autonomic_system = None
    db_protection_service = None
    thinking_processor = None
    provider = None
    client = None
    embedding_service = None
    execute_mcp_tool = None
    get_all_available_tools = None
    get_mcp_status = None
    _mcp_provider_client = None


async def _start_legacy_resources() -> Any:
    """Compatibility alias for the required base-services lifecycle stage."""
    return await _start_base_resources()


async def _start_base_resources() -> Any:
    """Construct only required base services after FastAPI enters lifespan."""
    global vector_db, aura_file_system, state_manager, aura_internal_tools
    global conversation_persistence, db_protection_service, embedding_service

    from aura_backend.aura_internal_tools import AuraInternalTools
    from aura_backend.database_protection import get_protection_service
    from aura_backend.robust_vector_db import RobustAuraVectorDB
    from aura_backend.runtime import StartedResource
    from aura_backend.shared_embedding_service import get_embedding_service

    stack = AsyncExitStack()
    try:
        db_protection_service = get_protection_service()
        stack.callback(db_protection_service.stop_protection)

        vector_db = RobustAuraVectorDB()
        stack.push_async_callback(vector_db.close)
        aura_file_system = AuraFileSystem()
        state_manager = AuraStateManager(vector_db, aura_file_system)
        aura_internal_tools = AuraInternalTools(vector_db, aura_file_system)
        embedding_service = get_embedding_service()

        conversation_persistence = ConversationPersistenceService(
            vector_db,
            aura_file_system,
        )
        resources = _LegacyRuntimeResources(mcp_router=None)

        async def close_resources() -> None:
            try:
                await stack.aclose()
            finally:
                _clear_runtime_aliases()

        return StartedResource(value=resources, close=close_resources)
    except BaseException:
        try:
            await stack.aclose()
        finally:
            _clear_runtime_aliases()
        raise


async def _start_mcp_resource() -> Any:
    """Start the provider-neutral MCP client behind its explicit feature gate."""
    global execute_mcp_tool, get_all_available_tools, get_mcp_status
    global _mcp_provider_client

    from aura_backend.mcp_integration import (
        execute_mcp_tool as legacy_execute_mcp_tool,
        mcp_router,
        shutdown_mcp_client,
    )
    from aura_backend.mcp_system import (
        get_all_available_tools as list_available_tools,
        get_mcp_client,
        get_mcp_status as read_mcp_status,
        initialize_mcp_system,
        shutdown_mcp_system,
    )
    from aura_backend.runtime import StartedResource

    stack = AsyncExitStack()
    stack.push_async_callback(shutdown_mcp_client)
    stack.push_async_callback(shutdown_mcp_system)
    try:
        await initialize_mcp_system(aura_internal_tools)
        _mcp_provider_client = get_mcp_client()
        execute_mcp_tool = legacy_execute_mcp_tool
        get_all_available_tools = list_available_tools
        get_mcp_status = read_mcp_status

        async def close_mcp() -> None:
            global execute_mcp_tool, get_all_available_tools, get_mcp_status
            global _mcp_provider_client
            try:
                await stack.aclose()
            finally:
                execute_mcp_tool = None
                get_all_available_tools = None
                get_mcp_status = None
                _mcp_provider_client = None

        return StartedResource(value=mcp_router, close=close_mcp)
    except BaseException:
        await stack.aclose()
        _mcp_provider_client = None
        raise


async def _start_gemini_bridge_resource() -> Any:
    """Start Gemini tool conversion only after explicit Gemini selection."""
    global mcp_gemini_bridge, global_tool_version

    from aura_backend.mcp_system import (
        initialize_gemini_bridge,
        shutdown_gemini_bridge,
    )
    from aura_backend.runtime import StartedResource

    stack = AsyncExitStack()
    stack.push_async_callback(shutdown_gemini_bridge)
    try:
        mcp_gemini_bridge = await initialize_gemini_bridge()
        global_tool_version += 1

        async def close_bridge() -> None:
            global mcp_gemini_bridge
            try:
                await stack.aclose()
            finally:
                mcp_gemini_bridge = None

        return StartedResource(value=mcp_gemini_bridge, close=close_bridge)
    except BaseException:
        await stack.aclose()
        mcp_gemini_bridge = None
        raise


async def _start_memvid_resource() -> Any:
    """Start the archival facade only when its declared extra is available."""
    global memvid_archival

    import importlib

    from aura_backend.runtime import StartedResource

    importlib.import_module("memvid_sdk")
    from aura_backend.memvid_archival_service import MemvidArchivalService

    async def close_memvid() -> None:
        global memvid_archival
        service, memvid_archival = memvid_archival, None
        close = getattr(service, "close", None)
        if callable(close):
            await close()

    # Bind cleanup before running the legacy constructor.  This keeps a
    # partially initialized facade inside the same exactly-once stage boundary.
    service = MemvidArchivalService.__new__(MemvidArchivalService)
    memvid_archival = service
    try:
        MemvidArchivalService.__init__(service)
    except BaseException:
        await close_memvid()
        raise
    return StartedResource(value=service, close=close_memvid)


class _DeferredProviderRuntime:
    """Provider-neutral target used before the selected provider starts last."""

    def __init__(self) -> None:
        self._target: Any = None

    def bind(self, target: Any) -> None:
        if self._target is not None:
            raise RuntimeError("provider runtime is already bound")
        self._target = target

    async def generate(self, request: ProviderRequest) -> ProviderResult:
        if self._target is None:
            raise ProviderFailure(
                code=ProviderErrorCode.UNAVAILABLE,
                provider="selected",
                retryable=True,
            )
        return await self._target.generate(request)


async def _start_autonomic_resource(provider_runtime: Any) -> Any:
    """Start optional provider-neutral autonomic work with owned cleanup."""
    global autonomic_system

    from aura_backend.aura_autonomic_system import (
        initialize_autonomic_system,
        shutdown_autonomic_system,
    )
    from aura_backend.runtime import StartedResource

    stack = AsyncExitStack()
    stack.push_async_callback(shutdown_autonomic_system)
    try:
        autonomic_system = await initialize_autonomic_system(
            mcp_bridge=mcp_gemini_bridge,
            internal_tools=aura_internal_tools,
            provider_runtime=provider_runtime,
        )

        async def close_autonomic() -> None:
            global autonomic_system
            try:
                await stack.aclose()
            finally:
                autonomic_system = None

        return StartedResource(value=autonomic_system, close=close_autonomic)
    except BaseException:
        await stack.aclose()
        autonomic_system = None
        raise


def _composition_environment() -> dict[str, str]:
    """Load the local dotenv once at composition and return an explicit mapping."""
    from dotenv import load_dotenv

    load_dotenv()
    return dict(os.environ)


def _build_application_runtime() -> Any:
    """Build the pure lifecycle owner; concrete resources start later."""
    global thinking_budget, provider, thinking_processor, client

    from aura_backend.mcp_system import (
        get_provider_tool_catalog,
        get_provider_tool_executor,
    )
    from aura_backend.providers.factory import ModelProviderFactory
    from aura_backend.providers.runtime import ProviderRuntime
    from aura_backend.runtime import (
        ApplicationRuntime,
        ResourceFactory,
        RuntimeSettings,
    )

    settings = RuntimeSettings.from_mapping(_composition_environment())
    thinking_budget = settings.provider.thinking_budget
    tool_executor: Any = None
    base_resources: _LegacyRuntimeResources | None = None
    deferred_provider = _DeferredProviderRuntime()

    async def start_base_services() -> Any:
        """Start base services and build an internal-only neutral tool surface."""
        nonlocal base_resources, tool_executor

        started = await _start_base_resources()
        try:
            catalog = await get_provider_tool_catalog(
                internal_tools=aura_internal_tools,
            )
            tool_executor = get_provider_tool_executor(
                catalog,
                internal_tools=aura_internal_tools,
            )
            started.value.tool_catalog = catalog
            base_resources = started.value
            return started
        except BaseException:
            await started.close()
            raise

    async def start_mcp() -> Any:
        nonlocal tool_executor
        if not settings.mcp_enabled:
            return None
        started = await _start_mcp_resource()
        try:
            catalog = await get_provider_tool_catalog(
                mcp_client=_mcp_provider_client,
                internal_tools=aura_internal_tools,
            )
            tool_executor = get_provider_tool_executor(
                catalog,
                mcp_client=_mcp_provider_client,
                internal_tools=aura_internal_tools,
            )
            if base_resources is not None:
                base_resources.mcp_router = started.value
                base_resources.tool_catalog = catalog
            return started
        except BaseException:
            await started.close()
            raise

    async def start_gemini_bridge() -> Any:
        if (
            not settings.mcp_enabled
            or settings.provider.kind is not ProviderKind.GEMINI
        ):
            return None
        return await _start_gemini_bridge_resource()

    async def start_memvid() -> Any:
        if not settings.memvid_enabled:
            return None
        return await _start_memvid_resource()

    async def start_autonomic() -> Any:
        if not settings.autonomic_enabled:
            return None
        return await _start_autonomic_resource(deferred_provider)

    async def start_provider() -> ProviderRuntime:
        global provider, thinking_processor, client

        if tool_executor is None:
            raise RuntimeError("provider tool executor is unavailable")
        selected = ModelProviderFactory.create_provider(
            settings.provider,
            tool_executor=tool_executor,
        )
        runtime = ProviderRuntime(
            selected,
            timeout_seconds=settings.provider.request_timeout_seconds,
        )
        deferred_provider.bind(runtime)
        provider = selected  # type: ignore[assignment]
        thinking_processor = getattr(selected, "thinking_processor", None)
        client = getattr(selected, "client", None)
        return runtime

    return ApplicationRuntime(
        settings=settings,
        resources=(
            ResourceFactory(
                name="legacy_services",
                start=start_base_services,
                required=True,
            ),
            ResourceFactory(name="mcp", start=start_mcp, required=False),
            ResourceFactory(
                name="gemini_bridge",
                start=start_gemini_bridge,
                required=False,
            ),
            ResourceFactory(name="memvid", start=start_memvid, required=False),
            ResourceFactory(
                name="autonomic",
                start=start_autonomic,
                required=False,
            ),
        ),
        provider_factory=start_provider,
    )


def _install_lifespan_routes(app: FastAPI, runtime: Any) -> None:
    """Install the legacy MCP router at most once after its owned import."""
    if getattr(app.state, "legacy_mcp_router_installed", False):
        return
    resource_getter = getattr(runtime, "resource", None)
    if not callable(resource_getter):
        return
    resources = resource_getter("legacy_services")
    router = getattr(resources, "mcp_router", None)
    if router is not None:
        app.include_router(router)
        app.state.legacy_mcp_router_installed = True


def _unstarted_health_snapshot() -> HealthSnapshot:
    """Return an import-safe fail-closed snapshot before/after lifespan."""
    return aggregate_health(
        runtime_snapshot=None,
        selected_provider="ollama",
        selected_model="unknown",
        selected_health=None,
    )


def _runtime_health_selection(runtime: Any) -> tuple[str, str, float] | None:
    """Read validated provider identifiers and the bounded preflight timeout."""
    settings = getattr(runtime, "settings", None)
    provider_settings = getattr(settings, "provider", None)
    kind = getattr(provider_settings, "kind", None)
    provider_name = getattr(kind, "value", kind)
    model = getattr(provider_settings, "model", None)
    timeout = getattr(settings, "preflight_timeout_seconds", None)
    if (
        not isinstance(provider_name, str)
        or not isinstance(model, str)
        or isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or timeout <= 0
    ):
        return None
    return provider_name, model, float(timeout)


async def _capture_runtime_health(runtime: Any) -> HealthSnapshot:
    """Capture one bounded startup observation for later side-effect-free reads."""
    selection = _runtime_health_selection(runtime)
    snapshot_reader = getattr(runtime, "snapshot", None)
    if selection is None or not callable(snapshot_reader):
        return _unstarted_health_snapshot()

    selected_provider, selected_model, timeout_seconds = selection
    runtime_snapshot = snapshot_reader()
    selected_health: ProviderHealth | None = None
    try:
        provider_runtime = runtime.provider_runtime
        health_reader = getattr(provider_runtime, "health", None)
        if not callable(health_reader):
            raise TypeError("provider runtime has no health reader")
        async with asyncio.timeout(timeout_seconds):
            observed = await health_reader()
        if not isinstance(observed, ProviderHealth):
            raise TypeError("provider health returned an invalid result")
        selected_health = observed
    except asyncio.CancelledError:
        raise
    except Exception:
        # The public status records only the safe category.  Source exceptions,
        # URLs, credentials, prompts, and SDK objects are never stored or logged.
        selected_health = ProviderHealth(
            provider=selected_provider,
            model=selected_model,
            status=ProviderHealthStatus.UNAVAILABLE,
            retryable=True,
        )

    return aggregate_health(
        runtime_snapshot=runtime_snapshot,
        selected_provider=selected_provider,
        selected_model=selected_model,
        selected_health=selected_health,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Own exactly one runtime and never publish partial startup state."""
    runtime_builder = app.state.runtime_builder
    runtime = runtime_builder()
    try:
        await runtime.start()
        app.state.health_snapshot = await _capture_runtime_health(runtime)
        app.state.runtime = runtime
        _install_lifespan_routes(app, runtime)
        yield
    finally:
        app.state.runtime = None
        app.state.health_snapshot = _unstarted_health_snapshot()
        await runtime.aclose()


api_router = APIRouter()


def create_app(runtime_builder: Any = _build_application_runtime) -> FastAPI:
    """Return an import-compatible app without constructing runtime resources."""
    created = FastAPI(
        title="Aura Backend",
        description="Advanced AI Companion with Vector Database and MCP Integration",
        version="1.0.0",
        lifespan=lifespan,
    )
    created.state.runtime_builder = runtime_builder
    created.state.runtime = None
    created.state.health_snapshot = _unstarted_health_snapshot()
    created.state.legacy_mcp_router_installed = False
    created.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_browser_origins(os.getenv("ALLOWED_ORIGINS"))),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID", "X-Attempt"],
    )
    created.include_router(api_router)
    return created


@api_router.get("/")
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
            "Cognitive Focus Tracking",
        ],
    }


def _health_correlation_id(request: Request) -> str:
    """Generate a content-free identifier without reflecting request headers."""
    del request
    return uuid.uuid4().hex


def _cached_health_payload(request: Request) -> dict[str, Any]:
    """Serialize app-cached health without probing or constructing anything."""
    snapshot = getattr(request.app.state, "health_snapshot", None)
    if not isinstance(snapshot, HealthSnapshot):
        snapshot = _unstarted_health_snapshot()
    payload = public_readiness(
        snapshot,
        correlation_id=_health_correlation_id(request),
    )
    payload["providers"] = [
        {**provider, "ready": provider["status"] == "ready"}
        for provider in payload["providers"]
    ]
    return payload


@api_router.get("/live")
async def live(request: Request) -> JSONResponse:
    """Report only that this process and event loop can serve a request."""
    correlation_id = _health_correlation_id(request)
    payload = {
        "status": "live",
        "live": True,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "correlation_id": correlation_id,
    }
    return JSONResponse(status_code=200, content=payload)


@api_router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    """Return cached application readiness with conventional 200/503 status."""
    payload = _cached_health_payload(request)
    return JSONResponse(status_code=200 if payload["ready"] else 503, content=payload)


@api_router.get("/health/providers")
async def provider_health(request: Request) -> JSONResponse:
    """Return cached selected/optional provider diagnostics without polling."""
    readiness = _cached_health_payload(request)
    selected = next(
        provider for provider in readiness["providers"] if provider["selected"]
    )
    payload = {
        "status": selected["status"],
        "ready": selected["ready"],
        "code": selected["code"],
        "timestamp": readiness["timestamp"],
        "age_seconds": readiness["age_seconds"],
        "correlation_id": readiness["correlation_id"],
        "providers": readiness["providers"],
    }
    return JSONResponse(status_code=200, content=payload)


@api_router.get("/health")
async def health_check(request: Request) -> JSONResponse:
    """Keep the legacy route as a composite of the same cached health truth."""
    readiness = _cached_health_payload(request)
    payload = {
        "status": "operational" if readiness["ready"] else "unhealthy",
        "timestamp": readiness["timestamp"],
        "age_seconds": readiness["age_seconds"],
        "correlation_id": readiness["correlation_id"],
        "liveness": {"status": "live", "live": True},
        "readiness": {
            "status": readiness["status"],
            "ready": readiness["ready"],
            "code": readiness["code"],
        },
        "providers": readiness["providers"],
        "resources": readiness["resources"],
    }
    return JSONResponse(status_code=200, content=payload)


async def _legacy_process_conversation(
    request: ConversationRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
) -> ConversationResponse:
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
    global provider
    session_recovery_enabled = (
        os.getenv("SESSION_RECOVERY_ENABLED", "true").lower() == "true"
    )
    session_key: Optional[str] = (
        None  # Initialize session_key to ensure it's always bound
    )

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
                relevant_memories = (
                    await conversation_persistence.safe_search_conversations(
                        query=request.message,
                        user_id=request.user_id,
                        n_results=5,  # Restored proper search capability
                    )
                )
                if relevant_memories:
                    memory_context = "\n".join(
                        [
                            f"Previous context: {mem['content']}"  # Use full content, not truncated
                            for mem in relevant_memories[
                                :3
                            ]  # Use multiple relevant memories
                        ]
                    )
                    if memory_context:
                        logger.debug(
                            f"🧠 Retrieved memory context: {len(memory_context)} chars"
                        )
            except Exception as e:
                logger.debug("⚠️ Memory context retrieval failed (non-critical): %s", e)
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
                match = re.search(r"\(MCP tool: (.+?)\)", func.get("description", ""))
                mcp_name = match.group(1) if match else func["name"]

                # Find the server from tool mapping
                server = "unknown"
                for tool_name, tool_info in mcp_gemini_bridge._tool_mapping.items():
                    if tool_name == func["name"]:
                        server = tool_info.get("server", "unknown")
                        break

                available_tools_info.append(
                    {
                        "name": mcp_name,
                        "clean_name": func["name"],
                        "description": func.get("description", ""),
                        "server": server,
                    }
                )

        # Build system instruction with context and available tools
        system_instruction = get_aura_system_instruction(
            user_name=user_profile.get("name") if user_profile else request.user_id,
            memory_context=memory_context,
            available_tools=available_tools_info,
        )

        # Enhanced session management with recovery capabilities
        session_key = f"{request.user_id}_{session_id}"

        # Convert history and current message to Provider Message format
        # Note: We rely on the provider's session management for history if session_id is provided
        provider_messages = [Message(role="user", content=request.message)]

        # Execute conversation using the Unified Model Provider

        if not provider:
            logger.error("❌ Model provider not initialized")
            raise HTTPException(
                status_code=500, detail="Model provider not initialized"
            )

        provider_response = await provider.generate_response(
            messages=provider_messages,
            system_instruction=system_instruction,
            session_id=session_key,
            temperature=0.7,
        )

        if provider_response.error:
            logger.error(
                f"❌ Provider error for {request.user_id}: {provider_response.error}"
            )
            raise HTTPException(status_code=500, detail=provider_response.error)

        aura_response = provider_response.content
        thinking_result = provider_response.raw_response

        # Track active session for cleanup purposes
        active_chat_sessions[session_key] = True

        # Debug thinking result
        if thinking_result:
            logger.info("🧠 Thinking result debug for %s:", request.user_id)
            logger.info(
                "   - has_thinking: %s", getattr(thinking_result, "has_thinking", False)
            )
            logger.info(
                f"   - thoughts length: {len(getattr(thinking_result, 'thoughts', '')) if hasattr(thinking_result, 'thoughts') else 0}"
            )
            logger.info(
                f"   - answer length: {len(getattr(thinking_result, 'answer', '')) if hasattr(thinking_result, 'answer') else 0}"
            )
            logger.info(
                f"   - answer preview: {getattr(thinking_result, 'answer', '')[:100] if hasattr(thinking_result, 'answer') else 'None'}"
            )
            logger.info(
                f"   - aura_response length: {len(aura_response) if aura_response else 0}"
            )
            logger.info(
                f"   - aura_response preview: {aura_response[:100000] if aura_response else 'None'}"
            )
        else:
            logger.warning("⚠️ No thinking result returned for %s", request.user_id)

        if not aura_response:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate a valid response after all recovery attempts.",
            )

        # Autonomic task analysis - let the intelligent system decide what to process
        if autonomic_system and autonomic_system._running:
            try:
                # Analyze conversation for potential autonomic tasks
                autonomic_tasks = await _analyze_conversation_for_autonomic_tasks(
                    user_message=request.message,
                    aura_response=aura_response,
                    user_id=request.user_id,
                    session_id=session_id,
                )

                # Submit tasks to autonomic system for intelligent processing
                for task_description, task_payload in autonomic_tasks:
                    was_offloaded, task_id = await autonomic_system.submit_task(
                        description=task_description,
                        payload=task_payload,
                        user_id=request.user_id,
                        session_id=session_id,
                    )

                    if was_offloaded:
                        logger.debug("🤖 Offloaded autonomic task: %s", task_id)
            except Exception as e:
                logger.debug("⚠️ Autonomic analysis failed (non-critical): %s", e)
                # Don't let autonomic system failures affect main conversation

        application_runtime = http_request.app.state.runtime
        analysis_generate = application_runtime.provider_runtime.generate

        # Process emotional state detection for both user and Aura
        user_emotional_state = await detect_user_emotion(
            user_message=request.message,
            user_id=request.user_id,
            generate=analysis_generate,
        )

        emotional_state_data = await detect_aura_emotion(
            conversation_snippet=f"User: {request.message}\nAura: {aura_response}",
            user_id=request.user_id,
            generate=analysis_generate,
        )

        # Process cognitive focus detection
        cognitive_state_data = await detect_aura_cognitive_focus(
            conversation_snippet=f"User: {request.message}\nAura: {aura_response}",
            user_id=request.user_id,
            generate=analysis_generate,
        )

        # Create memory objects
        user_memory = ConversationMemory(
            user_id=request.user_id,
            message=request.message,
            sender="user",
            emotional_state=user_emotional_state,
            session_id=session_id,
        )

        aura_memory = ConversationMemory(
            user_id=request.user_id,
            message=aura_response,
            sender="aura",
            emotional_state=emotional_state_data,
            cognitive_state=cognitive_state_data,
            session_id=session_id,
        )
        # Ensure emotional state and cognitive state are not None
        # Create conversation exchange object for atomic persistence
        conversation_exchange = ConversationExchange(
            user_memory=user_memory,
            ai_memory=aura_memory,
            user_emotional_state=user_emotional_state,
            ai_emotional_state=emotional_state_data,
            ai_cognitive_state=cognitive_state_data,
            session_id=session_id,
        )

        # IMMEDIATE PERSISTENCE - Use optimized immediate persistence for reliable chat history saving
        persistence_success = False
        immediate_persistence_enabled = (
            os.getenv("IMMEDIATE_PERSISTENCE_ENABLED", "true").lower() == "true"
        )
        persistence_timeout = float(
            os.getenv("PERSISTENCE_TIMEOUT", "15.0")
        )  # Increased from 5.0 to 15.0 for GPU/embedding operations
        emergency_retries = int(os.getenv("EMERGENCY_PERSISTENCE_RETRIES", "2"))

        if conversation_persistence and immediate_persistence_enabled:
            try:
                logger.info(
                    f"💾 Starting optimized immediate persistence for {request.user_id}"
                )

                # Use the immediate persistence method
                result = await conversation_persistence.persist_conversation_exchange_immediate(
                    conversation_exchange,
                    update_profile=True,
                    timeout=persistence_timeout,
                )

                if result["success"]:
                    persistence_success = True
                    logger.info(
                        f"✅ Chat history saved immediately for {request.user_id}"
                    )
                    logger.debug("   Method: %s", result.get("method", "immediate"))
                    logger.debug(
                        "   Stored components: %s", result["stored_components"]
                    )
                    logger.debug("   Duration: %.1fms", result["duration_ms"])
                else:
                    logger.warning(
                        f"⚠️ Immediate persistence had issues for {request.user_id}: {result['errors']}"
                    )

                    # Emergency fallback with retries
                    for emergency_attempt in range(emergency_retries):
                        try:
                            await asyncio.sleep(0.3 * (emergency_attempt + 1))
                            logger.info(
                                f"🚑 Emergency persistence attempt {emergency_attempt + 1}/{emergency_retries}"
                            )

                            emergency_result = await conversation_persistence.persist_conversation_exchange_immediate(
                                conversation_exchange,
                                update_profile=True,
                                timeout=persistence_timeout
                                * 0.8,  # Shorter timeout for emergency
                            )

                            if emergency_result["success"]:
                                persistence_success = True
                                logger.info(
                                    f"✅ Emergency persistence succeeded for {request.user_id} (attempt {emergency_attempt + 1})"
                                )
                                break
                            else:
                                logger.warning(
                                    f"⚠️ Emergency attempt {emergency_attempt + 1} failed: {emergency_result['errors']}"
                                )

                        except Exception as emergency_error:
                            logger.error(
                                f"❌ Emergency attempt {emergency_attempt + 1} exception: {emergency_error}"
                            )

                    if not persistence_success:
                        logger.error(
                            f"💥 All emergency persistence attempts failed for {request.user_id}"
                        )

            except Exception as e:
                logger.error(
                    f"❌ Critical immediate persistence failure for {request.user_id}: {e}"
                )

        elif conversation_persistence:
            # Fallback to regular persistence if immediate is disabled
            try:
                logger.info("💾 Using regular persistence for %s", request.user_id)
                result = await conversation_persistence.persist_conversation_exchange(
                    conversation_exchange
                )
                if result["success"]:
                    persistence_success = True
                    logger.info(
                        f"✅ Chat history saved with regular persistence for {request.user_id}"
                    )
                else:
                    logger.warning(
                        f"⚠️ Regular persistence failed for {request.user_id}: {result['errors']}"
                    )
            except Exception as e:
                logger.error(
                    f"❌ Regular persistence exception for {request.user_id}: {e}"
                )

        # Enhanced background persistence as backup (but primary is immediate)
        async def backup_persistence_monitor():
            """Background monitor to ensure persistence completed successfully"""
            if not persistence_success and conversation_persistence:
                logger.warning("🔄 Running backup persistence for %s", request.user_id)
                try:
                    await asyncio.sleep(1.0)  # Brief delay
                    backup_result = (
                        await conversation_persistence.persist_conversation_exchange(
                            conversation_exchange
                        )
                    )
                    if backup_result["success"]:
                        logger.info(
                            f"✅ Backup persistence succeeded for {request.user_id}"
                        )
                    else:
                        logger.error(
                            f"❌ Backup persistence failed for {request.user_id}: {backup_result['errors']}"
                        )
                except Exception as e:
                    logger.error(
                        f"💥 Backup persistence exception for {request.user_id}: {e}"
                    )

        # Only run background backup if immediate persistence failed
        if not persistence_success:
            background_tasks.add_task(backup_persistence_monitor)

        # Format response with thinking data
        response = ConversationResponse(
            response=aura_response,
            emotional_state={
                "name": emotional_state_data.name if emotional_state_data else "Normal",
                "intensity": (
                    emotional_state_data.intensity.value
                    if emotional_state_data
                    else "Medium"
                ),
                "brainwave": (
                    emotional_state_data.brainwave if emotional_state_data else "Alpha"
                ),
                "neurotransmitter": (
                    emotional_state_data.neurotransmitter
                    if emotional_state_data
                    else "Serotonin"
                ),
            },
            cognitive_state={
                "focus": (
                    cognitive_state_data.focus.value
                    if cognitive_state_data
                    else "Learning"
                ),
                "description": (
                    cognitive_state_data.description
                    if cognitive_state_data
                    else "Processing user input"
                ),
            },
            session_id=session_id,
            thinking_summary=provider_response.thoughts,
            thinking_metrics=(
                {
                    "total_chunks": getattr(thinking_result, "total_chunks", 1),
                    "thinking_chunks": getattr(
                        thinking_result,
                        "thinking_chunks",
                        1 if provider_response.thoughts else 0,
                    ),
                    "answer_chunks": getattr(thinking_result, "answer_chunks", 1),
                    "processing_time_ms": getattr(
                        thinking_result, "processing_time_ms", 0.0
                    ),
                }
                if thinking_result
                else None
            ),
            has_thinking=getattr(
                thinking_result, "has_thinking", bool(provider_response.thoughts)
            )
            if thinking_result
            else False,
        )

        # Debug the final response thinking data
        logger.info("🔍 Final response thinking debug for %s:", request.user_id)
        # logger.info("   - response.thinking_summary: %s", response.thinking_summary) # Be careful not to break the autonomous system, I do not want a summary! I want the entire thinking process.
        logger.info("   - response.has_thinking: %s", response.has_thinking)
        logger.info("   - response.thinking_metrics: %s", response.thinking_metrics)

        logger.info("✅ Processed conversation for user %s", request.user_id)
        return response
    except Exception as e:
        logger.error("❌ Failed to process conversation: %s", e)
        # Default fallback message
        fallback_response = "I'm having a bit of trouble connecting to my reasoning modules right now, but I'm still here. Could you try your message again? I've cleared the session to help us get back on track."

        # Try to recover the session if enabled
        if session_recovery_enabled and session_key:
            try:
                if provider:
                    await provider.clear_session(session_key)
                if session_key in active_chat_sessions:
                    del active_chat_sessions[session_key]
                logger.info(
                    f"🧹 Cleared failed session for {request.user_id} (session: {session_key})"
                )
            except Exception as recovery_error:
                logger.error(
                    f"❌ Session recovery failed for session {session_key}: {recovery_error}"
                )
                fallback_response = "I encountered a critical error and couldn't recover the session. Please try refreshing or starting a new conversation."

        return ConversationResponse(
            response=fallback_response,
            session_id=session_id,
            emotional_state=asdict(
                EmotionalStateData(
                    name="Concerned",
                    formula="C(E) + I(S)",
                    components={"CE": "High", "IS": "Medium"},
                    ntk_layer="L3",
                    brainwave="Gamma",
                    neurotransmitter="Cortisol",
                    description="System encountered an error during processing",
                )
            ),
            cognitive_state=asdict(
                CognitiveState(
                    focus=AsekeComponent.CE,
                    description="Error recovery and session reset",
                    context="System failure",
                )
            ),
        )


def _provider_tool_info(catalog: ToolCatalog) -> list[dict[str, str]]:
    """Return neutral tool descriptions without inspecting provider bridge state."""
    return [
        {
            "name": registration.original_name,
            "clean_name": registration.provider_name,
            "description": registration.definition.description,
            "server": registration.server,
        }
        for registration in catalog.registrations
    ]


async def _persist_conversation_exchange(
    exchange: ConversationExchange,
    background_tasks: BackgroundTasks,
) -> None:
    """Preserve the characterized immediate write and one degraded retry."""
    persistence_success = False
    immediate_enabled = (
        os.getenv("IMMEDIATE_PERSISTENCE_ENABLED", "true").lower() == "true"
    )
    persistence_timeout = float(os.getenv("PERSISTENCE_TIMEOUT", "15.0"))

    if conversation_persistence and immediate_enabled:
        try:
            result = (
                await conversation_persistence.persist_conversation_exchange_immediate(
                    exchange,
                    update_profile=True,
                    timeout=persistence_timeout,
                )
            )
            persistence_success = bool(result.get("success"))
            if persistence_success:
                logger.info("Conversation persisted immediately")
            else:
                logger.warning("Immediate conversation persistence degraded")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error("Immediate conversation persistence failed")
    elif conversation_persistence:
        try:
            result = await conversation_persistence.persist_conversation_exchange(
                exchange
            )
            persistence_success = bool(result.get("success"))
            if persistence_success:
                logger.info("Conversation persisted")
            else:
                logger.warning("Conversation persistence degraded")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error("Conversation persistence failed")

    async def retry_once() -> None:
        if conversation_persistence is None:
            return
        try:
            await asyncio.sleep(1.0)
            await conversation_persistence.persist_conversation_exchange(exchange)
            logger.info("Background conversation persistence attempted")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error("Background conversation persistence failed")

    if not persistence_success:
        background_tasks.add_task(retry_once)


async def _conversation_fallback(
    *,
    provider_runtime: Any,
    session_id: str,
    session_key: str | None,
    recovery_enabled: bool,
) -> ConversationResponse:
    """Return the Phase 1 fallback after one content-free session recovery."""
    fallback_response = "I'm having a bit of trouble connecting to my reasoning modules right now, but I'm still here. Could you try your message again? I've cleared the session to help us get back on track."

    if recovery_enabled and session_key:
        try:
            if provider_runtime is not None:
                await provider_runtime.clear_session(session_key)
            active_chat_sessions.pop(session_key, None)
            logger.info("Failed conversation session cleared")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error("Failed conversation session recovery failed")
            fallback_response = "I encountered a critical error and couldn't recover the session. Please try refreshing or starting a new conversation."

    return ConversationResponse(
        response=fallback_response,
        session_id=session_id,
        emotional_state=asdict(
            EmotionalStateData(
                name="Concerned",
                formula="C(E) + I(S)",
                components={"CE": "High", "IS": "Medium"},
                ntk_layer="L3",
                brainwave="Gamma",
                neurotransmitter="Cortisol",
                description="System encountered an error during processing",
            )
        ),
        cognitive_state=asdict(
            CognitiveState(
                focus=AsekeComponent.CE,
                description="Error recovery and session reset",
                context="System failure",
            )
        ),
    )


@api_router.post("/conversation", response_model=ConversationResponse)
async def process_conversation(
    request: ConversationRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
) -> ConversationResponse:
    """Run one provider-neutral conversation while preserving public behavior."""
    session_id = request.session_id or str(uuid.uuid4())
    session_key = f"{request.user_id}_{session_id}"
    recovery_enabled = os.getenv("SESSION_RECOVERY_ENABLED", "true").lower() == "true"
    provider_runtime: Any = None
    stage = "runtime"

    try:
        application_runtime = http_request.app.state.runtime
        if application_runtime is None:
            raise RuntimeError("application runtime is unavailable")
        provider_runtime = application_runtime.provider_runtime
        runtime_resources = application_runtime.resource("legacy_services")
        tool_catalog = getattr(runtime_resources, "tool_catalog", None)
        if not isinstance(tool_catalog, ToolCatalog):
            raise ProviderFailure(
                code=ProviderErrorCode.UNAVAILABLE,
                provider="tools",
                retryable=False,
            )

        stage = "context"
        user_profile = None
        if aura_file_system:
            user_profile = await aura_file_system.load_user_profile(request.user_id)

        memory_context = ""
        if len(request.message.split()) > 2 and conversation_persistence:
            try:
                relevant_memories = (
                    await conversation_persistence.safe_search_conversations(
                        query=request.message,
                        user_id=request.user_id,
                        n_results=5,
                    )
                )
                memory_context = "\n".join(
                    f"Previous context: {memory['content']}"
                    for memory in relevant_memories[:3]
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.debug("Memory context retrieval unavailable")

        stage = "prompt"
        system_instruction = get_aura_system_instruction(
            user_name=user_profile.get("name") if user_profile else request.user_id,
            memory_context=memory_context,
            available_tools=_provider_tool_info(tool_catalog),
        )
        correlation_id = uuid.uuid4().hex
        stage = "provider"
        provider_result = await provider_runtime.generate(
            ProviderRequest(
                messages=(ProviderMessage(role="user", content=request.message),),
                system_instruction=system_instruction,
                tools=tool_catalog.definitions,
                temperature=0.7,
                session_id=session_key,
                correlation_id=correlation_id,
            )
        )
        if not isinstance(provider_result, ProviderResult):
            raise ProviderFailure(
                code=ProviderErrorCode.MALFORMED_RESPONSE,
                correlation_id=correlation_id,
            )
        aura_response = provider_result.content
        if not aura_response.strip():
            raise ProviderFailure(
                code=ProviderErrorCode.MALFORMED_RESPONSE,
                correlation_id=correlation_id,
            )
        active_chat_sessions[session_key] = True

        stage = "autonomic"
        if autonomic_system and autonomic_system._running:
            try:
                autonomic_tasks = await _analyze_conversation_for_autonomic_tasks(
                    user_message=request.message,
                    aura_response=aura_response,
                    user_id=request.user_id,
                    session_id=session_id,
                )
                for task_description, task_payload in autonomic_tasks:
                    await autonomic_system.submit_task(
                        description=task_description,
                        payload=task_payload,
                        user_id=request.user_id,
                        session_id=session_id,
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.debug("Autonomic conversation analysis unavailable")

        stage = "analysis"
        user_emotional_state = await detect_user_emotion(
            user_message=request.message,
            user_id=request.user_id,
            generate=provider_runtime.generate,
        )
        conversation_snippet = f"User: {request.message}\nAura: {aura_response}"
        emotional_state_data = await detect_aura_emotion(
            conversation_snippet=conversation_snippet,
            user_id=request.user_id,
            generate=provider_runtime.generate,
        )
        cognitive_state_data = await detect_aura_cognitive_focus(
            conversation_snippet=conversation_snippet,
            user_id=request.user_id,
            generate=provider_runtime.generate,
        )

        stage = "exchange"
        user_memory = ConversationMemory(
            user_id=request.user_id,
            message=request.message,
            sender="user",
            emotional_state=user_emotional_state,
            session_id=session_id,
        )
        aura_memory = ConversationMemory(
            user_id=request.user_id,
            message=aura_response,
            sender="aura",
            emotional_state=emotional_state_data,
            cognitive_state=cognitive_state_data,
            session_id=session_id,
        )
        exchange = ConversationExchange(
            user_memory=user_memory,
            ai_memory=aura_memory,
            user_emotional_state=user_emotional_state,
            ai_emotional_state=emotional_state_data,
            ai_cognitive_state=cognitive_state_data,
            session_id=session_id,
        )
        stage = "persistence"
        await _persist_conversation_exchange(exchange, background_tasks)

        stage = "response"
        logger.info("Conversation processed")
        return ConversationResponse(
            response=aura_response,
            emotional_state={
                "name": emotional_state_data.name if emotional_state_data else "Normal",
                "intensity": (
                    emotional_state_data.intensity.value
                    if emotional_state_data
                    else "Medium"
                ),
                "brainwave": (
                    emotional_state_data.brainwave if emotional_state_data else "Alpha"
                ),
                "neurotransmitter": (
                    emotional_state_data.neurotransmitter
                    if emotional_state_data
                    else "Serotonin"
                ),
            },
            cognitive_state={
                "focus": (
                    cognitive_state_data.focus.value
                    if cognitive_state_data
                    else "Learning"
                ),
                "description": (
                    cognitive_state_data.description
                    if cognitive_state_data
                    else "Processing user input"
                ),
            },
            session_id=session_id,
            thinking_content=provider_result.reflection_summary,
            thinking_metrics=None,
            has_thinking=bool(provider_result.reflection_summary),
        )
    except asyncio.CancelledError:
        active_chat_sessions.pop(session_key, None)
        raise
    except ProviderFailure as failure:
        logger.warning(
            "Conversation provider failure code=%s correlation_id=%s",
            failure.code.value,
            failure.correlation_id,
        )
    except Exception as error:
        logger.error(
            "Conversation processing failed stage=%s code=%s",
            stage,
            type(error).__name__,
        )

    return await _conversation_fallback(
        provider_runtime=provider_runtime,
        session_id=session_id,
        session_key=session_key,
        recovery_enabled=recovery_enabled,
    )


# Redundant session management removed as it's now handled by the Model Provider

# Note: Previous session management and thinking processing logic has been moved to
# the aura_backend/providers/ directory as part of the Unified Model Provider abstraction.


async def _analyze_conversation_for_autonomic_tasks(
    user_message: str, aura_response: str, user_id: str, session_id: str
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
        logger.debug(
            "🤖 Autonomic system not available or not running, skipping task analysis"
        )
        return submitted_tasks

    # Calculate conversation metrics
    conversation_length = len(user_message.split()) + len(aura_response.split())
    user_message_lower = user_message.lower()
    aura_response_lower = aura_response.lower()
    combined_text_lower = user_message_lower + " " + aura_response_lower

    # Minimum threshold for basic autonomic processing
    if conversation_length < 10:
        logger.debug(
            f"🤖 Conversation too short ({conversation_length} words) for autonomic processing"
        )
        return submitted_tasks

    try:
        # Track task opportunities
        task_opportunities = []

        # 1. EMOTIONAL PATTERN ANALYSIS - for conversations with emotional content
        emotional_indicators = [
            "feel",
            "emotion",
            "happy",
            "sad",
            "angry",
            "anxious",
            "worried",
            "excited",
            "frustrated",
            "love",
            "hate",
            "personal",
            "sharing",
            "struggle",
            "difficult",
        ]

        has_emotional_content = any(
            indicator in user_message_lower for indicator in emotional_indicators
        )

        if has_emotional_content or conversation_length > 50:
            task_opportunities.append(
                {
                    "description": f"Deep emotional pattern analysis for user {user_id}",
                    "payload": {
                        "tool_name": "analyze_emotional_patterns",
                        "arguments": {
                            "user_id": user_id,
                            "days": 30,  # Analyze last 30 days
                            "include_conversation": True,
                        },
                        "conversation_context": {
                            "user_message": user_message,
                            "aura_response": aura_response,
                            "emotional_indicators_found": [
                                ind
                                for ind in emotional_indicators
                                if ind in user_message_lower
                            ],
                        },
                    },
                    "task_type_hint": "DATA_ANALYSIS",
                    "priority_boost": 0.2 if has_emotional_content else 0.1,
                }
            )

        # 2. MEMORY SEARCH AND CONSOLIDATION - for knowledge-seeking conversations
        knowledge_indicators = [
            "remember",
            "recall",
            "previously",
            "last time",
            "before",
            "search",
            "find",
            "look for",
            "history",
            "past conversation",
        ]
        memory_indicators = [
            "learn",
            "understand",
            "explain",
            "teach",
            "how",
            "what",
            "why",
            "tell me about",
            "help me understand",
        ]

        needs_memory_search = any(
            indicator in combined_text_lower for indicator in knowledge_indicators
        )
        needs_knowledge_building = any(
            indicator in combined_text_lower for indicator in memory_indicators
        )

        if needs_memory_search or (
            conversation_length > 30 and needs_knowledge_building
        ):
            # Extract potential search query from conversation
            search_query = (
                user_message
                if len(user_message) > 20
                else f"{user_message} {aura_response[:100]}"
            )

            task_opportunities.append(
                {
                    "description": f"Comprehensive memory search and pattern extraction for user {user_id}",
                    "payload": {
                        "tool_name": "search_all_memories",
                        "arguments": {
                            "query": search_query,
                            "user_id": user_id,
                            "max_results": 20,
                        },
                        "analysis_required": True,
                        "consolidate_findings": needs_knowledge_building,
                    },
                    "task_type_hint": "MEMORY_SEARCH",
                    "priority_boost": 0.3 if needs_memory_search else 0.1,
                }
            )

        # 3. PATTERN RECOGNITION - for complex analytical conversations
        analytical_indicators = [
            "analyze",
            "pattern",
            "trend",
            "insight",
            "data",
            "statistics",
            "correlation",
            "relationship",
            "connection",
        ]

        needs_pattern_analysis = (
            any(indicator in combined_text_lower for indicator in analytical_indicators)
            or conversation_length > 100
        )

        if needs_pattern_analysis:
            task_opportunities.append(
                {
                    "description": f"Advanced pattern recognition and insight generation for user {user_id}",
                    "payload": {
                        "analysis_type": "conversation_patterns",
                        "user_id": user_id,
                        "session_id": session_id,
                        "conversation_data": {
                            "message": user_message,
                            "response": aura_response,
                            "length": conversation_length,
                            "complexity_score": len(set(combined_text_lower.split()))
                            / conversation_length,  # Vocabulary diversity
                        },
                        "extract_insights": True,
                    },
                    "task_type_hint": "PATTERN_ANALYSIS",
                    "priority_boost": 0.2,
                }
            )

        # 4. KNOWLEDGE ARCHIVAL - for very long or information-rich conversations
        if conversation_length > 150 or (
            conversation_length > 80 and needs_knowledge_building
        ):
            task_opportunities.append(
                {
                    "description": f"Archive and compress conversation knowledge for user {user_id}",
                    "payload": {
                        "tool_name": "archive_old_conversations",
                        "arguments": {
                            "user_id": user_id,
                            "session_id": session_id,
                            "priority_content": True,
                        },
                        "conversation_summary": {
                            "key_topics": "auto_extract",
                            "emotional_tone": "analyze",
                            "knowledge_gained": "summarize",
                        },
                    },
                    "task_type_hint": "BACKGROUND_PROCESSING",
                    "priority_boost": 0.1,
                }
            )

        # 5. COMPLEX REASONING - for philosophical or deep thinking conversations
        reasoning_indicators = [
            "philosophy",
            "meaning",
            "purpose",
            "think about",
            "wonder",
            "hypothetical",
            "imagine",
            "suppose",
            "theory",
            "concept",
        ]

        needs_deep_reasoning = any(
            indicator in combined_text_lower for indicator in reasoning_indicators
        )

        if needs_deep_reasoning and conversation_length > 40:
            task_opportunities.append(
                {
                    "description": f"Deep reasoning and philosophical analysis for user {user_id}",
                    "payload": {
                        "reasoning_type": "philosophical_analysis",
                        "conversation_context": f"User: {user_message}\nAura: {aura_response}",
                        "user_id": user_id,
                        "explore_concepts": True,
                        "generate_insights": True,
                    },
                    "task_type_hint": "COMPLEX_REASONING",
                    "priority_boost": 0.25,
                }
            )

        # 6. REAL-TIME TOOL EXECUTION - for conversations mentioning specific tools
        tool_indicators = [
            "create",
            "generate",
            "make",
            "build",
            "code",
            "script",
            "program",
            "calculate",
            "compute",
            "visualize",
        ]

        needs_tool_execution = any(
            indicator in combined_text_lower for indicator in tool_indicators
        )

        if needs_tool_execution:
            task_opportunities.append(
                {
                    "description": f"Background tool execution and code generation for user {user_id}",
                    "payload": {
                        "execution_type": "deferred_tool_call",
                        "conversation_request": user_message,
                        "preliminary_response": aura_response,
                        "user_id": user_id,
                        "generate_artifacts": True,
                    },
                    "task_type_hint": "CODE_GENERATION",
                    "priority_boost": 0.3,
                }
            )

        # Submit each identified task opportunity to the autonomic system
        for task_opp in task_opportunities:
            try:
                # Create enhanced user context for better classification
                user_context = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "conversation_length": conversation_length,
                    "is_substantial": conversation_length > 40,
                    "task_type_hint": task_opp.get(
                        "task_type_hint", "BACKGROUND_PROCESSING"
                    ),
                    "priority_boost": task_opp.get("priority_boost", 0.0),
                    "user_waiting": False,  # Background tasks don't block user
                }

                # Use the autonomic system's TaskClassifier
                (
                    should_offload,
                    task_type,
                    priority,
                ) = await autonomic_system.classifier.should_offload_task(
                    task_description=task_opp["description"],
                    task_payload=task_opp["payload"],
                    user_context=user_context,
                )

                if should_offload:
                    # Submit task to autonomic system
                    was_offloaded, task_id = await autonomic_system.submit_task(
                        description=task_opp["description"],
                        payload=task_opp["payload"],
                        user_id=user_id,
                        session_id=session_id,
                    )

                    if was_offloaded:
                        logger.info(
                            f"🤖 Successfully submitted autonomic task: {task_id}"
                        )
                        logger.info(
                            f"   Type: {task_type.value}, Priority: {priority.value}"
                        )
                        logger.info(
                            f"   Description: {task_opp['description'][:100]}..."
                        )

                        # Add to submitted tasks list
                        submitted_tasks.append(
                            (task_opp["description"], task_opp["payload"])
                        )
                    else:
                        logger.debug(
                            f"🤖 Task not offloaded (queue/rate limit): {task_opp['description'][:50]}..."
                        )
                else:
                    logger.debug(
                        f"🤖 Task classified as not needing offload: {task_opp['description'][:50]}..."
                    )

            except Exception as task_error:
                logger.debug("⚠️ Failed to submit individual task: %s", task_error)
                # Continue with other tasks even if one fails

        # Log final autonomic system status if tasks were submitted
        if submitted_tasks:
            system_status = autonomic_system.get_system_status()
            logger.info("🤖 Autonomic system status after submissions:")
            logger.info("   Submitted tasks: %s", len(submitted_tasks))
            logger.info(
                f"   Queue status: {system_status['queued_tasks']} queued, {system_status['active_tasks']} active"
            )
            logger.info(
                f"   Queue utilization: {system_status['queue_utilization']:.1f}%"
            )

            # Log rate limiting status
            rate_status = system_status.get("rate_limiting", {})
            if rate_status:
                logger.debug(
                    f"   Rate limit: {rate_status.get('rpm_current', 0)}/{rate_status.get('rpm_limit', 30)} RPM"
                )

    except Exception as e:
        logger.warning("⚠️ Autonomic task analysis failed: %s", e)
        logger.debug("   Error details: %s: %s", type(e).__name__, str(e))
        # Don't let autonomic system failures affect main conversation

    return submitted_tasks


@api_router.post("/search")
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
                        "max_results": request.n_results,
                    },
                )

                logger.info("🔧 Advanced search raw result: %s", advanced_result)

                if advanced_result and advanced_result.get("status") == "success":
                    # Check multiple possible result keys in the response
                    memories = (
                        advanced_result.get("memories", [])
                        or advanced_result.get("results", [])
                        or advanced_result.get("data", [])
                        or advanced_result.get("all_results", [])
                        or []
                    )

                    # If still empty, check if the result itself is a list
                    if not memories and isinstance(advanced_result.get("result"), list):
                        memories = advanced_result.get("result", [])

                    # Convert to expected frontend format
                    formatted_results = []
                    for memory in memories:
                        # Handle different memory formats
                        if isinstance(memory, dict):
                            formatted_results.append(
                                {
                                    "content": memory.get(
                                        "content",
                                        memory.get(
                                            "text", memory.get("document", str(memory))
                                        ),
                                    ),
                                    "metadata": memory.get(
                                        "metadata", memory.get("meta", {})
                                    ),
                                    "similarity": float(
                                        memory.get(
                                            "similarity",
                                            memory.get(
                                                "score", memory.get("distance", 0.0)
                                            ),
                                        )
                                    ),
                                }
                            )
                        else:
                            # Handle string results
                            formatted_results.append(
                                {
                                    "content": str(memory),
                                    "metadata": {},
                                    "similarity": 0.5,
                                }
                            )

                    logger.info(
                        f"🔍 Advanced search found {len(formatted_results)} memories using video + active search"
                    )

                    if formatted_results:
                        return {
                            "results": formatted_results,
                            "query": request.query,
                            "total_found": len(formatted_results),
                            "search_type": "unified_memory_search",
                            "includes_video_archives": True,
                        }

            except Exception as e:
                logger.warning(
                    f"⚠️ Advanced search failed, falling back to basic search: {e}"
                )

            # Fallback to basic memory search if advanced fails
            try:
                basic_result = await aura_internal_tools.execute_tool(
                    "aura.search_memories",
                    {
                        "query": request.query,
                        "user_id": request.user_id,
                        "n_results": request.n_results,
                    },
                )

                if basic_result and basic_result.get("status") == "success":
                    memories = basic_result.get("memories", [])
                    logger.info(
                        f"🔍 Basic search found {len(memories)} memories using active search"
                    )
                    return {
                        "results": memories,
                        "query": request.query,
                        "total_found": len(memories),
                        "search_type": "active_memory_search",
                        "includes_video_archives": False,
                    }

            except Exception as e:
                logger.warning(
                    f"⚠️ Basic MCP search failed, using direct persistence: {e}"
                )

        # Final fallback to direct persistence service if MCP tools fail
        if conversation_persistence:
            results = await conversation_persistence.safe_search_conversations(
                query=request.query,
                user_id=request.user_id,
                n_results=request.n_results,
            )

            logger.info("🔍 Direct persistence search found %s memories", len(results))
            return {
                "results": results,
                "query": request.query,
                "total_found": len(results),
                "search_type": "persistence_fallback",
                "includes_video_archives": False,
            }
        else:
            logger.error("❌ Conversation persistence service not available")
            return {
                "results": [],
                "query": request.query,
                "total_found": 0,
                "search_type": "no_persistence_available",
                "includes_video_archives": False,
                "error": "Persistence service not initialized",
            }

    except Exception as e:
        logger.error("❌ Failed to search memories: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from None


async def _cleanup_session_related_data(user_id: str, session_id: str):
    """
    Background task to clean up any additional session-related data.

    This runs asynchronously to avoid blocking the main delete operation.
    """
    try:
        logger.info("🧹 Background cleanup for session %s", session_id)

        # Clean up any cached session data
        session_key = f"{user_id}_{session_id}"
        if session_key in active_chat_sessions:
            del active_chat_sessions[session_key]
            logger.debug("🧹 Cleared cached session %s", session_key)

        if session_key in session_tool_versions:
            del session_tool_versions[session_key]
            logger.debug("🧹 Cleared session tool version %s", session_key)

        # Additional cleanup can be added here if needed

    except Exception as e:
        logger.error("❌ Background cleanup failed for session %s: %s", session_id, e)


@api_router.get("/thinking-status")
async def get_thinking_status() -> Dict[str, Any]:
    """
    Get the current status and configuration of the thinking system.

    Returns information about thinking capabilities, configuration,
    and system readiness for transparent AI reasoning.
    """
    try:
        budget = int(os.getenv("THINKING_BUDGET", "-1"))
        effective_budget = (
            budget  # No conversion - pass through -1 for adaptive thinking
        )

        thinking_config = {
            "thinking_enabled": thinking_processor is not None,
            "thinking_budget": effective_budget,
            "thinking_budget_raw": budget,
            "thinking_budget_max": 24576,
            "include_thinking_in_response": os.getenv(
                "INCLUDE_THINKING_IN_RESPONSE", "false"
            ).lower()
            == "true",
            "model": os.getenv("AURA_MODEL", "gemini-2.5-flash"),
            "supports_thinking": True,  # Gemini models support thinking
        }

        system_status = {
            "thinking_processor_initialized": thinking_processor is not None,
            "mcp_bridge_available": mcp_gemini_bridge is not None,
            "function_calls_with_thinking": thinking_processor is not None
            and mcp_gemini_bridge is not None,
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
                "Cognitive transparency reporting",
            ],
        }

    except Exception as e:
        logger.error("❌ Failed to get thinking status: %s", e)
        return {"status": "error", "error": str(e), "thinking_enabled": False}


@api_router.get("/emotional-analysis/{user_id}")
async def get_emotional_analysis(
    user_id: str, period: str = "week", custom_days: Optional[int] = None
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
            "hour": 1 / 24,  # Last hour
            "day": 1,  # Last 24 hours
            "week": 7,  # Last 7 days
            "month": 30,  # Last 30 days
            "year": 365,  # Last year
            "multi-year": 1825,  # Last 5 years
        }

        # Use custom days if provided, otherwise use period mapping
        days = custom_days if custom_days is not None else period_mapping.get(period, 7)

        if not vector_db:
            raise HTTPException(
                status_code=500, detail="Vector database not initialized"
            )

        analysis = await vector_db.analyze_emotional_trends(user_id, days)
        analysis["period_type"] = period
        analysis["custom_days"] = custom_days

        return analysis

    except Exception as e:
        logger.error("❌ Failed to get emotional analysis: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@api_router.post("/export/{user_id}")
async def export_user_data(user_id: str, format_type: str = "json"):
    """Export user conversation history and patterns"""
    try:
        if not aura_file_system:
            raise HTTPException(
                status_code=500, detail="File system not initialized"
            ) from None

        export_path = await aura_file_system.export_conversation_history(
            user_id, format_type
        )
        written_path = Path(export_path)
        if not written_path.is_file():
            raise RuntimeError("Export writer returned an unwritten path")
        json.loads(written_path.read_text(encoding="utf-8"))
        return {"export_path": export_path, "message": "Export completed successfully"}

    except StoragePathError:
        logger.warning("Rejected invalid export request")
        raise HTTPException(status_code=400, detail="Invalid export request") from None
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to export user data: %s", e)
        raise HTTPException(status_code=500, detail="Export failed") from None


@api_router.get("/chat-history/{user_id}")
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
            raise HTTPException(
                status_code=500,
                detail="Conversation persistence service not initialized",
            )

        # Use the persistence service's thread-safe method
        result = await conversation_persistence.safe_get_chat_history(user_id, limit)

        # Transform the result to match frontend expectations
        transformed_sessions = []
        for session in result.get("sessions", []):
            # Get the last message content for preview
            messages = session.get("messages", [])
            last_message_content = (
                messages[-1]["content"] if messages else "No messages"
            )

            transformed_session = {
                "session_id": session["session_id"],
                "last_message": (
                    last_message_content[:10000] + "..."
                    if len(last_message_content) > 10000
                    else last_message_content
                ),
                "message_count": len(messages),
                "timestamp": session.get(
                    "last_time", session.get("start_time", "")
                ),  # Use last_time as timestamp
            }
            transformed_sessions.append(transformed_session)

        # Transform response to match frontend interface
        return {
            "sessions": transformed_sessions,
            "total_sessions": result.get(
                "total", 0
            ),  # Frontend expects 'total_sessions'
            "user_id": user_id,  # Frontend expects user_id in response
        }

    except Exception as e:
        logger.error("❌ Failed to get chat history: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@api_router.get("/chat-history/{user_id}/{session_id}")
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
            raise HTTPException(
                status_code=500,
                detail="Conversation persistence service not initialized",
            )

        # Use the safe_get_session_messages method from conversation persistence service
        messages = await conversation_persistence.safe_get_session_messages(
            user_id, session_id
        )

        if not messages:
            logger.info(
                f"No messages found for session {session_id} for user {user_id}"
            )
            return []

        logger.info(
            "✅ Retrieved %s messages for session %s", len(messages), session_id
        )
        return messages

    except Exception as e:
        logger.error("❌ Failed to get session messages for %s: %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@api_router.delete("/chat-history/{user_id}/{session_id}")
async def delete_chat_session(user_id: str, session_id: str):
    """Delete a specific chat session using enhanced database operations"""
    try:
        if not vector_db or not vector_db.conversations:
            raise HTTPException(
                status_code=500, detail="Vector database not properly initialized"
            )

        # Get all messages for this session (no longer need nested _safe_operation since delete_messages handles it)
        results = vector_db.conversations.get(
            where={
                "$and": [
                    {"user_id": {"$eq": user_id}},
                    {"session_id": {"$eq": session_id}},
                ]
            },
            include=["documents", "metadatas"],
        )

        if results and results.get("ids"):
            # Delete all messages in this session using the robust delete method
            delete_result = await vector_db.delete_messages(
                ids=results["ids"], collection_name="conversations"
            )

            if not delete_result["success"]:
                logger.error(
                    f"❌ Database deletion failed for session {session_id}: {delete_result['errors']}"
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to delete session from database: {'; '.join(delete_result['errors'])}",
                )

            # Also remove from active sessions using the provider
            session_key = f"{user_id}_{session_id}"
            global provider
            if provider:
                await provider.clear_session(session_key)

            logger.info(
                f"✅ Successfully deleted session {session_id} for user {user_id} ({delete_result['deleted_count']} messages)"
            )
            return {
                "message": f"Deleted session {session_id}",
                "deleted_count": delete_result["deleted_count"],
            }
        else:
            return {"message": "Session not found", "deleted_count": 0}

    except Exception as e:
        logger.error("❌ Failed to delete chat session: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@api_router.post("/mcp/execute-tool", response_model=ExecuteToolResponse)
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
        logger.info(
            f"🔧 Executing tool '{request.tool_name}' for user {request.user_id}"
        )

        # Validate tool execution capability
        if not aura_internal_tools:
            return ExecuteToolResponse(
                status="error",
                tool_name=request.tool_name,
                error="Internal tools not initialized",
                execution_time=asyncio.get_event_loop().time() - start_time,
                timestamp=datetime.now().isoformat(),
                metadata={"error_type": "initialization_error"},
            )

        # Execute tool with timeout
        try:
            if request.timeout:
                result = await asyncio.wait_for(
                    execute_mcp_tool(
                        tool_name=request.tool_name,
                        arguments=request.arguments,
                        user_id=request.user_id,
                        aura_internal_tools=aura_internal_tools,
                    ),
                    timeout=request.timeout,
                )
            else:
                result = await execute_mcp_tool(
                    tool_name=request.tool_name,
                    arguments=request.arguments,
                    user_id=request.user_id,
                    aura_internal_tools=aura_internal_tools,
                )
        except asyncio.TimeoutError:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.warning(
                f"⏰ Tool '{request.tool_name}' timed out after {request.timeout}s"
            )
            return ExecuteToolResponse(
                status="timeout",
                tool_name=request.tool_name,
                error=f"Tool execution timed out after {request.timeout} seconds",
                execution_time=execution_time,
                timestamp=datetime.now().isoformat(),
                metadata={"timeout_duration": request.timeout},
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
                    "request_metadata": request.metadata,
                },
            )

        # Successful execution
        logger.info(
            f"✅ Tool '{request.tool_name}' executed successfully in {execution_time:.3f}s"
        )
        return ExecuteToolResponse(
            status="success",
            tool_name=request.tool_name,
            result=result,
            execution_time=execution_time,
            timestamp=datetime.now().isoformat(),
            metadata={
                "request_metadata": request.metadata,
                "result_type": type(result).__name__,
            },
        )

    except ValueError as e:
        # Handle validation errors
        execution_time = asyncio.get_event_loop().time() - start_time
        logger.error("❌ Validation error for tool '%s': %s", request.tool_name, e)
        return ExecuteToolResponse(
            status="error",
            tool_name=request.tool_name,
            error=f"Validation error: {str(e)}",
            execution_time=execution_time,
            timestamp=datetime.now().isoformat(),
            metadata={"error_type": "validation_error"},
        )

    except Exception as e:
        # Handle unexpected errors
        execution_time = asyncio.get_event_loop().time() - start_time
        logger.error(
            "❌ Unexpected error executing tool '%s': %s", request.tool_name, e
        )
        return ExecuteToolResponse(
            status="error",
            tool_name=request.tool_name,
            error=f"Execution failed: {str(e)}",
            execution_time=execution_time,
            timestamp=datetime.now().isoformat(),
            metadata={
                "error_type": "execution_error",
                "exception_type": type(e).__name__,
            },
        )


@api_router.get("/mcp/tools")
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
                available_tools.append(
                    {
                        "name": tool_name,
                        "type": "internal",
                        "description": tool_info.get(
                            "description", "No description available"
                        ),
                        "parameters": tool_info.get("parameters", {}),
                        "examples": tool_info.get("examples", []),
                    }
                )

        # Get external MCP tools
        try:
            external_tools = await get_all_available_tools()
            for tool in external_tools:
                available_tools.append(
                    {
                        "name": tool.get("name", "unknown"),
                        "type": "external",
                        "description": tool.get(
                            "description", "No description available"
                        ),
                        "parameters": tool.get("inputSchema", {}).get("properties", {}),
                        "required": tool.get("inputSchema", {}).get("required", []),
                    }
                )
        except Exception as e:
            logger.warning("⚠️ Could not fetch external MCP tools: %s", e)

        # Sort tools by name for easier browsing
        available_tools.sort(key=lambda x: x["name"])

        return {
            "status": "success",
            "total_tools": len(available_tools),
            "tools": available_tools,
            "categories": {
                "internal": len(
                    [t for t in available_tools if t["type"] == "internal"]
                ),
                "external": len(
                    [t for t in available_tools if t["type"] == "external"]
                ),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("❌ Failed to list available tools: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve tools: {str(e)}"
        ) from e


@api_router.get("/mcp/tools/{tool_name}")
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
                    "description": tool_info.get(
                        "description", "No description available"
                    ),
                    "parameters": tool_info.get("parameters", {}),
                    "examples": tool_info.get("examples", []),
                    "usage_notes": tool_info.get("usage_notes", []),
                    "timestamp": datetime.now().isoformat(),
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
                        "description": tool.get(
                            "description", "No description available"
                        ),
                        "parameters": tool.get("inputSchema", {}).get("properties", {}),
                        "required": tool.get("inputSchema", {}).get("required", []),
                        "schema": tool.get("inputSchema", {}),
                        "timestamp": datetime.now().isoformat(),
                    }
        except Exception as e:
            logger.warning("⚠️ Could not search external MCP tools: %s", e)

        # Tool not found
        return {
            "name": tool_name,
            "found": False,
            "error": "Tool not found in available tools",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("❌ Failed to get tool info for '%s': %s", tool_name, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to get tool info: {str(e)}"
        ) from e


@api_router.post("/mcp/tools/validate")
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
            "timestamp": datetime.now().isoformat(),
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
                validation_result["warnings"].append(
                    f"Could not check external tools: {str(e)}"
                )

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
                    validation_result["errors"].append(
                        f"Missing required parameter: {param}"
                    )

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
                        validation_result["errors"].append(
                            f"Parameter '{param}' should be a string"
                        )
                        validation_result["valid"] = False
                    elif expected_type == "integer" and not isinstance(value, int):
                        validation_result["errors"].append(
                            f"Parameter '{param}' should be an integer"
                        )
                        validation_result["valid"] = False
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        validation_result["errors"].append(
                            f"Parameter '{param}' should be a boolean"
                        )
                        validation_result["valid"] = False
                    elif expected_type == "array" and not isinstance(value, list):
                        validation_result["errors"].append(
                            f"Parameter '{param}' should be an array"
                        )
                        validation_result["valid"] = False
                    elif expected_type == "object" and not isinstance(value, dict):
                        validation_result["errors"].append(
                            f"Parameter '{param}' should be an object"
                        )
                        validation_result["valid"] = False

        # Add helpful suggestions
        if validation_result["valid"]:
            validation_result["suggestions"].append(
                "Tool request is valid and ready for execution"
            )
        else:
            validation_result["suggestions"].append(
                "Fix the errors above before executing the tool"
            )
            if tool_info and "description" in tool_info:
                validation_result["suggestions"].append(
                    f"Tool description: {tool_info['description']}"
                )

        return validation_result

    except Exception as e:
        logger.error("❌ Failed to validate tool request: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Validation failed: {str(e)}"
        ) from None


@api_router.delete("/sessions/{user_id}")
async def clear_user_sessions(user_id: str):
    """Clear chat sessions for a user"""
    try:
        global active_chat_sessions
        sessions_cleared = 0

        # Find and remove all sessions for this user
        sessions_to_remove = [
            key for key in active_chat_sessions.keys() if key.startswith(f"{user_id}_")
        ]

        global provider
        for session_key in sessions_to_remove:
            if provider:
                await provider.clear_session(session_key)
            sessions_cleared += 1

        logger.info(
            "🧹 Cleared %s chat sessions for user %s", sessions_cleared, user_id
        )

        return {
            "message": f"Cleared {sessions_cleared} chat sessions for user {user_id}",
            "user_id": user_id,
            "sessions_cleared": sessions_cleared,
        }

    except Exception as e:
        logger.error("❌ Failed to clear sessions for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@api_router.get("/mcp/bridge-status")
async def get_mcp_bridge_status():
    """Get MCP-Gemini bridge status and statistics"""
    try:
        if not mcp_gemini_bridge:
            return {
                "status": "not_initialized",
                "message": "MCP-Gemini bridge is not initialized",
            }

        stats = mcp_gemini_bridge.get_execution_stats()
        available_functions = mcp_gemini_bridge.get_available_functions()

        return {
            "status": "active",
            "available_functions": len(available_functions),
            "execution_stats": stats,
            "sample_functions": available_functions[:5],  # Show first 5 functions
        }

    except Exception as e:
        logger.error("❌ Failed to get bridge status: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@api_router.get("/mcp/system-status")
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
                tools_by_server[server].append(
                    {
                        "name": tool["name"],
                        "description": (
                            tool["description"][:10000] + "..."
                            if len(tool["description"]) > 10000
                            else tool["description"]
                        ),
                    }
                )

            status["tools_by_server"] = tools_by_server
            status["total_tools"] = len(tools)

        return status

    except Exception as e:
        logger.error("❌ Failed to get MCP system status: %s", e)
        return {"status": "error", "error": str(e), "initialized": False}


@api_router.get("/persistence/health")
async def get_persistence_health():
    """Get persistence layer health status"""
    try:
        if not conversation_persistence:
            return {
                "status": "not_initialized",
                "error": "Conversation persistence service not initialized",
                "timestamp": datetime.now().isoformat(),
            }

        metrics = await conversation_persistence.get_persistence_metrics()

        health_checker = PersistenceHealthCheck(conversation_persistence)
        health_status = await health_checker.check_health()

        return {
            "status": "healthy" if health_status["healthy"] else "unhealthy",
            "metrics": metrics,
            "health_check": health_status,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("❌ Failed to get persistence health: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@api_router.post("/test/persistence")
async def test_persistence_reliability():
    """Test endpoint to validate chat persistence reliability"""
    try:
        if not conversation_persistence:
            return {
                "status": "error",
                "message": "Conversation persistence service not initialized",
            }

        test_user_id = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        test_session_id = str(uuid.uuid4())

        user_memory = ConversationMemory(
            user_id=test_user_id,
            message="This is a test message to validate persistence reliability",
            sender="user",
            session_id=test_session_id,
        )

        aura_memory = ConversationMemory(
            user_id=test_user_id,
            message="This is a test response to validate that chat history saves correctly",
            sender="aura",
            session_id=test_session_id,
        )

        test_exchange = ConversationExchange(
            user_memory=user_memory, ai_memory=aura_memory, session_id=test_session_id
        )

        # Test immediate persistence
        immediate_result = (
            await conversation_persistence.persist_conversation_exchange_immediate(
                test_exchange, update_profile=False, timeout=3.0
            )
        )

        # Verify the conversation was stored by searching for it
        search_result = await conversation_persistence.safe_search_conversations(
            query="test message to validate persistence",
            user_id=test_user_id,
            n_results=2,
        )

        # Check chat history retrieval
        history_result = await conversation_persistence.safe_get_chat_history(
            test_user_id, limit=10
        )

        return {
            "status": "success",
            "test_results": {
                "immediate_persistence": {
                    "success": immediate_result["success"],
                    "duration_ms": immediate_result["duration_ms"],
                    "stored_components": immediate_result["stored_components"],
                    "method": immediate_result.get("method", "unknown"),
                },
                "search_verification": {
                    "found_messages": len(search_result),
                    "search_successful": len(search_result) >= 2,
                },
                "history_retrieval": {
                    "sessions_found": len(history_result.get("sessions", [])),
                    "retrieval_successful": len(history_result.get("sessions", [])) > 0,
                },
            },
            "test_user_id": test_user_id,
            "persistence_validated": (
                immediate_result["success"]
                and len(search_result) >= 2
                and len(history_result.get("sessions", [])) > 0
            ),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("❌ Persistence test failed: %s", e)
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@api_router.get("/memvid/status")
async def get_memvid_status():
    """Get memvid archival service status"""
    try:
        if not memvid_archival:
            return {
                "status": "not_initialized",
                "error": "Memvid archival service not initialized",
                "timestamp": datetime.now().isoformat(),
            }

        # Get basic status info
        archives = await memvid_archival.list_archives()

        return {
            "status": "operational",
            "archives_count": len(archives),
            "archives": archives[:5],  # Show first 5 archives
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("❌ Failed to get memvid status: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@api_router.get("/vector-db/health")
async def get_vector_db_health():
    """Get detailed vector database health information"""
    try:
        if not vector_db:
            return {
                "status": "not_initialized",
                "error": "Vector database not initialized",
                "timestamp": datetime.now().isoformat(),
            }

        health_info = await vector_db.health_check()
        return health_info

    except Exception as e:
        logger.error("❌ Failed to get vector database health: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@api_router.get("/database-protection/status")
async def get_database_protection_status():
    """Get database protection service status and health"""
    try:
        if not db_protection_service:
            return {
                "status": "not_initialized",
                "error": "Database protection service not initialized",
                "timestamp": datetime.now().isoformat(),
            }

        health_status = db_protection_service.get_health_status()

        return {
            "status": (
                "operational" if health_status["protection_active"] else "inactive"
            ),
            "health_status": health_status,
            "backup_directory": str(db_protection_service.backup_dir),
            "protection_features": [
                "Automatic backup before risky operations",
                "Health monitoring",
                "Emergency recovery triggers",
                "Transaction-like safety for database operations",
            ],
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("❌ Failed to get database protection status: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@api_router.post("/database-protection/emergency-backup")
async def trigger_emergency_backup():
    """Trigger emergency database backup manually"""
    try:
        if not db_protection_service:
            raise HTTPException(
                status_code=500, detail="Database protection service not initialized"
            )

        backup_path = db_protection_service.emergency_backup()

        if backup_path:
            return {
                "status": "success",
                "message": "Emergency backup created successfully",
                "backup_path": str(backup_path),
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "status": "failed",
                "message": "Emergency backup failed to create",
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.error("❌ Failed to create emergency backup: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@api_router.get("/autonomic/status")
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
        autonomic_enabled = os.getenv("AUTONOMIC_ENABLED", "true").lower() == "true"

        if not autonomic_enabled:
            return {
                "status": "disabled",
                "message": "Autonomic nervous system is disabled in configuration",
                "timestamp": datetime.now().isoformat(),
            }

        if not autonomic_system:
            return {
                "status": "not_initialized",
                "error": "Autonomic nervous system not initialized",
                "timestamp": datetime.now().isoformat(),
            }

        status = autonomic_system.get_system_status()
        return {
            "status": "operational" if status["running"] else "stopped",
            "system_status": status,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("❌ Failed to get autonomic status: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@api_router.get("/autonomic/tasks/{user_id}")
async def get_user_autonomic_tasks(user_id: str, limit: int = 20):
    """Get autonomic tasks for a specific user"""
    try:
        if not autonomic_system:
            raise HTTPException(
                status_code=500, detail="Autonomic system not initialized"
            )

        # Get completed tasks for the user
        user_tasks = []
        for _task_id, task in autonomic_system.completed_tasks.items():
            if task.user_id == user_id:
                user_tasks.append(
                    {
                        "task_id": task.task_id,
                        "task_type": task.task_type.value,
                        "priority": task.priority.value,
                        "description": task.description,
                        "status": task.status.value,
                        "created_at": (
                            task.created_at.isoformat() if task.created_at else None
                        ),
                        "completed_at": (
                            task.completed_at.isoformat() if task.completed_at else None
                        ),
                        "execution_time_ms": task.execution_time_ms,
                        "has_result": task.result is not None,
                        "has_error": task.error is not None,
                    }
                )

        # Get active tasks for the user
        active_user_tasks = []
        for _task_id, task in autonomic_system.active_tasks.items():
            if task.user_id == user_id:
                active_user_tasks.append(
                    {
                        "task_id": task.task_id,
                        "task_type": task.task_type.value,
                        "priority": task.priority.value,
                        "description": task.description,
                        "status": task.status.value,
                        "created_at": (
                            task.created_at.isoformat() if task.created_at else None
                        ),
                        "started_at": (
                            task.started_at.isoformat() if task.started_at else None
                        ),
                    }
                )

        # Sort by creation time (newest first) and limit
        user_tasks.sort(key=lambda x: x["created_at"] or "", reverse=True)
        user_tasks = user_tasks[:limit]

        return {
            "user_id": user_id,
            "active_tasks": active_user_tasks,
            "completed_tasks": user_tasks,
            "total_active": len(active_user_tasks),
            "total_completed": len(user_tasks),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("❌ Failed to get user autonomic tasks: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@api_router.get("/autonomic/task/{task_id}")
async def get_autonomic_task_details(task_id: str):
    """Get detailed information about a specific autonomic task"""
    try:
        if not autonomic_system:
            raise HTTPException(
                status_code=500, detail="Autonomic system not initialized"
            )

        # Check completed tasks first
        task = autonomic_system.completed_tasks.get(task_id)
        if not task:
            # Check active tasks
            task = autonomic_system.active_tasks.get(task_id)

        if not task:
            raise HTTPException(
                status_code=404, detail=f"Task {task_id} not found"
            ) from None

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
            "completed_at": (
                task.completed_at.isoformat() if task.completed_at else None
            ),
            "execution_time_ms": task.execution_time_ms,
            "payload": task.payload,
            "result": task.result,
            "error": task.error,
        }

        return task_details

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get task details: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@api_router.post("/autonomic/submit-task")
async def submit_autonomic_task(
    description: str,
    payload: Dict[str, Any],
    user_id: str,
    session_id: Optional[str] = None,
    force_offload: bool = False,
):
    """Manually submit a task to the autonomic system"""
    try:
        if not autonomic_system:
            raise HTTPException(
                status_code=500, detail="Autonomic system not initialized"
            )

        was_offloaded, task_id = await autonomic_system.submit_task(
            description=description,
            payload=payload,
            user_id=user_id,
            session_id=session_id,
            force_offload=force_offload,
        )

        if was_offloaded and task_id:
            return {
                "status": "submitted",
                "task_id": task_id,
                "message": f"Task {task_id} submitted to autonomic system",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "status": "not_offloaded",
                "message": "Task did not meet criteria for autonomic processing",
                "force_offload_option": "Set force_offload=true to override",
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.error("❌ Failed to submit autonomic task: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@api_router.get("/autonomic/task/{task_id}/result")
async def get_autonomic_task_result(task_id: str, timeout: Optional[float] = None):
    """Get the result of an autonomic task, optionally waiting for completion"""
    try:
        if not autonomic_system:
            raise HTTPException(
                status_code=500, detail="Autonomic system not initialized"
            )

        task = await autonomic_system.get_task_result(task_id, timeout)

        if not task:
            raise HTTPException(
                status_code=404, detail=f"Task {task_id} not found"
            ) from None

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
            "execution_time_ms": task.execution_time_ms,
            "completed_at": (
                task.completed_at.isoformat() if task.completed_at else None
            ),
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get task result: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@api_router.post("/autonomic/control/{action}")
async def control_autonomic_system(action: str):
    """Control autonomic system (start/stop/restart)"""
    try:
        if not autonomic_system:
            raise HTTPException(
                status_code=500, detail="Autonomic system not initialized"
            )

        if action == "start":
            if autonomic_system._running:
                return {
                    "status": "already_running",
                    "message": "Autonomic system is already running",
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                await autonomic_system.start()
                return {
                    "status": "started",
                    "message": "Autonomic system started successfully",
                    "timestamp": datetime.now().isoformat(),
                }

        elif action == "stop":
            if not autonomic_system._running:
                return {
                    "status": "already_stopped",
                    "message": "Autonomic system is already stopped",
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                await autonomic_system.stop()
                return {
                    "status": "stopped",
                    "message": "Autonomic system stopped successfully",
                    "timestamp": datetime.now().isoformat(),
                }

        elif action == "restart":
            await autonomic_system.stop()
            await autonomic_system.start()
            return {
                "status": "restarted",
                "message": "Autonomic system restarted successfully",
                "timestamp": datetime.now().isoformat(),
            }

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action: {action}. Use start, stop, or restart",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to control autonomic system: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@api_router.post("/vector-db/optimize")
async def optimize_vector_db():
    """Trigger vector database optimization"""
    try:
        if not vector_db:
            raise HTTPException(
                status_code=500, detail="Vector database not initialized"
            )

        # Perform SQLite optimization through the enhanced database
        async with vector_db._safe_operation("optimize_database"):
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
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("❌ Failed to optimize vector database: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from None


# Compatibility import target for Uvicorn, tests, and existing local launchers.
# Route registration is complete before the pure factory is called.
app = create_app()


if __name__ == "__main__":
    logger.info("🚀 Starting Aura Backend Server...")
    logger.info("✨ Features: Vector DB, MCP Integration, Advanced State Management")
    logger.info(
        "🔧 MCP Tools will be loaded on startup - check logs for available tools"
    )
    logger.info("💡 To see available tools, ask Aura: 'What MCP tools do you have?'")

    uvicorn.run(
        "aura_backend.main:app",
        host=server_host(os.getenv("AURA_HOST")),
        port=8000,
        reload=os.getenv("AURA_RELOAD", "false").lower() == "true",
        log_level="info",
    )
