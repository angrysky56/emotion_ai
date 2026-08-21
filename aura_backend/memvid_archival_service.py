"""
Memvid Archival Service
======================

This service provides a clean architectural boundary between Aura's active
memory system and the memvid archival system. By maintaining separate database
contexts, we eliminate the shared state conflicts that cause compaction errors.

The service follows the Bounded Context pattern from Domain-Driven Design,
ensuring that the archival system's implementation details don't leak into
the core application.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ArchivalPriority(Enum):
    """Defines the urgency of archival operations"""

    IMMEDIATE = "immediate"  # Archive as soon as possible
    SCHEDULED = "scheduled"  # Archive during off-peak hours
    BACKGROUND = "background"  # Archive when system is idle
    MANUAL = "manual"  # Only archive on explicit request


@dataclass
class ArchivalRequest:
    """
    Represents a request to archive conversations.

    This abstraction allows the archival system to operate independently
    of the active memory system's implementation details.
    """

    user_id: Optional[str]
    criteria: Dict[str, Any]
    priority: ArchivalPriority
    codec: str = "h264"
    requested_at: Optional[datetime] = None

    def __post_init__(self):
        if self.requested_at is None:
            self.requested_at = datetime.now()


@dataclass
class ArchivalResult:
    """
    Represents the result of an archival operation.

    This provides a consistent interface regardless of the underlying
    archival implementation (memvid, compressed files, cloud storage, etc.)
    """

    success: bool
    archive_id: str
    conversations_archived: int
    archive_size_mb: float
    compression_ratio: float
    errors: List[str]
    metadata: Dict[str, Any]


class MemvidArchivalService:
    """
    Clean boundary between active memory and archival system.

    This service encapsulates all interactions with the memvid system,
    preventing shared database references and ensuring proper isolation.

    Key architectural principles:
    - No shared database connections with the main application
    - All data transfer happens through well-defined interfaces
    - The archival system can be replaced without affecting core logic
    - Operations are idempotent and can be safely retried
    """

    def __init__(
        self,
        chroma_db_path: str = "./aura_chroma_db",
        archive_path: str = "./memvid_videos",
        isolation_mode: bool = True,
    ):
        self.chroma_db_path = Path(chroma_db_path)
        self.archive_path = Path(archive_path)
        self.archive_path.mkdir(exist_ok=True)

        # Isolation mode ensures we create our own database connections
        self.isolation_mode = isolation_mode

        # Lazy initialization of archival system
        self._archive_system = None
        self._initialization_lock = asyncio.Lock()

        # Queue for archival requests
        self._archival_queue = asyncio.Queue()
        self._processing_task = None

        logger.info(
            f"Memvid Archival Service initialized - "
            f"Isolation mode: {isolation_mode}, "
            f"Archive path: {archive_path}"
        )

    async def _ensure_initialized(self):
        """
        Lazily initializes the archival system with proper isolation.

        This prevents initialization conflicts during application startup
        and ensures the archival system has its own database context.
        """
        if self._archive_system is not None:
            return

        async with self._initialization_lock:
            # Double-check after acquiring lock
            if self._archive_system is not None:
                return

            try:
                if self.isolation_mode:
                    # Create isolated database client for archival
                    await self._initialize_isolated_system()
                else:
                    # Use shared system (for testing/development)
                    await self._initialize_shared_system()

                # Start background processing
                self._processing_task = asyncio.create_task(
                    self._process_archival_queue()
                )

                logger.info("✅ Archival system initialized successfully")

            except Exception as e:
                logger.error("Failed to initialize archival system: %s", e)
                raise

    async def _initialize_isolated_system(self):
        """
        Initializes archival system with complete isolation.

        This creates a separate database connection that doesn't interfere
        with the main application's database operations.
        """
        try:
            # Dynamic import to avoid circular dependencies
            REAL_MEMVID_AVAILABLE = False  # Initialize to False
            AuraRealMemvid = None  # Initialize AuraRealMemvid to None
            try:
                from aura_real_memvid import (
                    REAL_MEMVID_AVAILABLE,
                )
                from aura_real_memvid import AuraRealMemvid as _AuraRealMemvid

                AuraRealMemvid = _AuraRealMemvid  # Assign to the outer scope
            except ImportError:
                logger.warning("aura_real_memvid module not available")
                # REAL_MEMVID_AVAILABLE = False  # No need to set it here, it's already initialized

            if not REAL_MEMVID_AVAILABLE or AuraRealMemvid is None:
                logger.warning("Real memvid not available - using mock archival")
                self._archive_system = MockArchivalSystem()
                return

            # Create isolated instance with its own database connection
            # Note: We explicitly DO NOT pass the existing ChromaDB client
            self._archive_system = AuraRealMemvid(
                aura_chroma_path=str(self.chroma_db_path),
                memvid_video_path=str(self.archive_path),
                active_memory_days=30,
                existing_chroma_client=None,  # Force new connection
            )

        except ImportError:
            logger.warning("Memvid module not available - using mock archival")
            self._archive_system = MockArchivalSystem()

    async def _initialize_shared_system(self):
        """
        Initializes archival system with shared database (development mode).

        This mode is only for testing and should not be used in production
        as it can cause the compaction conflicts we're trying to avoid.
        """
        logger.warning(
            "⚠️ Initializing archival in SHARED mode - "
            "This may cause database conflicts!"
        )

        # This would get the shared client - NOT RECOMMENDED
        # Left here for completeness but should be avoided
        raise NotImplementedError(
            "Shared mode initialization not implemented - "
            "Use isolation mode for production"
        )

    async def request_archival(self, request: ArchivalRequest) -> str:
        """
        Submits an archival request to the processing queue.

        This asynchronous approach prevents blocking the main application
        while archival operations are performed.

        Args:
            request: Archival request with criteria and priority

        Returns:
            Request ID for tracking the archival operation
        """
        await self._ensure_initialized()

        # Generate unique request ID
        request_id = f"archival_{request.user_id or 'all'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Add to queue with priority handling
        await self._archival_queue.put((request.priority.value, request_id, request))

        logger.info(
            f"Archival request submitted: {request_id} "
            f"(Priority: {request.priority.value})"
        )

        return request_id

    async def _process_archival_queue(self):
        """
        Background task that processes archival requests.

        This runs continuously, processing requests based on priority
        and system load. It ensures archival operations don't interfere
        with active system operations.
        """
        logger.info("Archival queue processor started")

        while True:
            try:
                # Get next request (blocks until available)
                priority, request_id, request = await self._archival_queue.get()

                logger.info("Processing archival request: %s", request_id)

                # Process based on priority
                if request.priority == ArchivalPriority.IMMEDIATE:
                    result = await self._perform_archival(request)
                elif request.priority == ArchivalPriority.SCHEDULED:
                    # Wait for off-peak hours (e.g., 2-6 AM)
                    await self._wait_for_off_peak()
                    result = await self._perform_archival(request)
                elif request.priority == ArchivalPriority.BACKGROUND:
                    # Wait for system idle
                    await self._wait_for_idle()
                    result = await self._perform_archival(request)
                else:
                    # Manual - skip (shouldn't be in queue)
                    continue

                # Store result for retrieval
                await self._store_archival_result(request_id, result)

            except Exception as e:
                logger.error("Error processing archival request: %s", e)
                await asyncio.sleep(5)  # Brief pause before continuing

    async def _perform_archival(self, request: ArchivalRequest) -> ArchivalResult:
        """
        Performs the actual archival operation.

        This method handles the interaction with the archival system,
        ensuring proper error handling and result formatting.
        """
        try:
            # In Memvid v2, AuraRealMemvid handles the query and deletion internally
            # to maintain isolation and database consistency.
            if not self._archive_system:
                raise RuntimeError("Archival system not initialized")

            # Perform archival through the isolated system
            archive_result = self._archive_system.archive_conversations_to_video(
                user_id=request.user_id
            )

            # Convert to standard result format
            success = "error" not in archive_result
            return ArchivalResult(
                success=success,
                archive_id=str(archive_result.get("archive_name", "")),
                conversations_archived=int(archive_result.get("archived_count", 0) or 0),
                archive_size_mb=float(
                    archive_result.get("size_mb", archive_result.get("video_size_mb", 0)) or 0
                ),
                compression_ratio=float(archive_result.get("compression_ratio", 0) or 0),
                errors=[archive_result["error"]] if not success else [],
                metadata={
                    "archive_file": archive_result.get("archive_file", ""),
                    "archive_type": archive_result.get("archive_type", "memvid_v2"),
                },
            )

        except Exception as e:
            logger.error("Archival operation failed: %s", e)
            return ArchivalResult(
                success=False,
                archive_id="",
                conversations_archived=0,
                archive_size_mb=0,
                compression_ratio=0,
                errors=[str(e)],
                metadata={"error_type": type(e).__name__},
            )

    async def _fetch_conversations_for_archival(
        self, request: ArchivalRequest
    ) -> List[Dict[str, Any]]:
        """
        Fetches conversations that match archival criteria.

        This method queries the database in a way that doesn't interfere
        with active operations, using read-only transactions where possible.
        """
        # Implementation depends on the specific criteria
        # This is a simplified example

        if "age_days" in request.criteria:
            cutoff_date = datetime.now() - timedelta(days=request.criteria["age_days"])
            # Query logic here - using cutoff_date for filtering
            logger.debug("Archiving conversations older than: %s", cutoff_date)

        # Return formatted conversation data
        return []

    async def _execute_archival(
        self, conversations: List[Dict[str, Any]], codec: str
    ) -> Dict[str, Any]:
        """
        Executes the archival through the isolated archival system.
        Note: In v2, this is largely handled within AuraRealMemvid.
        """
        if not self._archive_system:
            return {"success": False, "errors": ["System not initialized"]}

        return self._archive_system.archive_conversations_to_video()

    async def _wait_for_off_peak(self):
        """Waits until off-peak hours for scheduled archival."""
        current_hour = datetime.now().hour
        if 2 <= current_hour <= 6:
            return  # Already in off-peak

        # Calculate time until 2 AM
        hours_until_off_peak = (26 - current_hour) % 24
        await asyncio.sleep(hours_until_off_peak * 3600)

    async def _wait_for_idle(self):
        """Waits for system idle state for background archival."""
        # Simple implementation - wait 5 minutes
        # In production, this would check system metrics
        await asyncio.sleep(300)

    async def _store_archival_result(self, request_id: str, result: ArchivalResult):
        """Stores archival result for later retrieval."""
        # In a production system, this would use a persistent store
        # For now, we just log it
        logger.info(
            f"Archival completed: {request_id} - "
            f"Success: {result.success}, "
            f"Archived: {result.conversations_archived}"
        )

    async def get_archival_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the status of an archival request.

        This allows the main application to check on archival progress
        without blocking on the operation.
        """
        # Implementation would check persistent store
        return None

    async def search_archives(
        self, query: str, user_id: Optional[str] = None, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Searches through archived conversations.

        This provides read-only access to archived data without requiring
        the main application to understand the archival format.
        """
        await self._ensure_initialized()

        try:
            if self._archive_system and hasattr(self._archive_system, "search_unified"):
                results = self._archive_system.search_unified(
                    query=query, user_id=user_id or "all", max_results=max_results
                )

                # If result is a coroutine, await it
                if asyncio.iscoroutine(results):
                    results = await results

                # Return only video archive results
                return results.get("video_archive_results", [])
            else:
                return []

        except Exception as e:
            logger.error("Archive search failed: %s", e)
            return []

    async def list_archives(self) -> List[Dict[str, Any]]:
        """
        Lists all available archives.

        This provides metadata about archives without exposing
        implementation details.
        """
        await self._ensure_initialized()

        try:
            if self._archive_system and hasattr(
                self._archive_system, "list_video_archives"
            ):
                # Call the method
                result = self._archive_system.list_video_archives()

                # If result is a coroutine, await it
                if asyncio.iscoroutine(result):
                    result = await result

                # Ensure the result is a list of dictionaries, as per the method's type hint
                if isinstance(result, dict):
                    # If a single dictionary is returned, wrap it in a list
                    return [result]
                elif isinstance(result, list):
                    # If it's already a list, return it
                    # (Further validation of list contents could be added if necessary)
                    return result
                else:
                    # Log unexpected type and return empty list to maintain contract
                    logger.warning(
                        f"list_video_archives returned unexpected type: {type(result)}"
                    )
                    return []
            else:
                return []

        except Exception as e:
            logger.error("Failed to list archives: %s", e)
            return []

    async def shutdown(self):
        """
        Gracefully shuts down the archival service.

        This ensures all pending operations complete and resources
        are properly released.
        """
        logger.info("Shutting down archival service...")

        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

    async def search_unified(self, **kwargs):
        return {"video_archive_results": []}

    async def list_video_archives(self):  # Make method asynchronous for consistency
        return []

    async def close(self):
        pass


class MockArchivalSystem:
    """
    Mock implementation for when memvid is not available.

    This ensures the application can run even without the archival
    system, following the principle of graceful degradation.
    """

    async def search_unified(self, **kwargs):
        return {"video_archive_results": []}

    def archive_conversations_to_video(self, **kwargs):
        return {"error": "Mock archival system - memvid not available"}

    async def list_video_archives(self):  # Make method asynchronous
        return []

    async def close(self):
        pass


class ArchivalPolicy:
    """
    Defines policies for automatic archival operations.

    This separates the "what to archive" decision from the "how to archive"
    implementation, allowing policies to evolve independently.
    """

    def __init__(
        self,
        age_threshold_days: int = 30,
        size_threshold_mb: int = 100,
        enable_auto_archival: bool = True,
    ):
        self.age_threshold_days = age_threshold_days
        self.size_threshold_mb = size_threshold_mb
        self.enable_auto_archival = enable_auto_archival

    def should_archive_conversation(
        self, conversation_metadata: Dict[str, Any]
    ) -> bool:
        """
        Determines if a conversation should be archived.

        This centralizes the archival decision logic, making it
        easy to adjust policies without touching the archival mechanism.
        """
        if not self.enable_auto_archival:
            return False

        # Check age
        timestamp_str = conversation_metadata.get("timestamp", "")
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                age_days = (datetime.now() - timestamp).days
                if age_days > self.age_threshold_days:
                    return True
            except ValueError:
                pass

        return False

    def get_archival_criteria(self) -> Dict[str, Any]:
        """
        Returns criteria for bulk archival operations.

        This translates high-level policies into specific
        query criteria for the archival system.
        """
        return {
            "age_days": self.age_threshold_days,
            "exclude_pinned": True,  # Don't archive pinned conversations
            "exclude_starred": True,  # Don't archive starred conversations
        }
