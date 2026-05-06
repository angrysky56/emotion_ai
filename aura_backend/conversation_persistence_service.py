"""
Conversation Persistence Service
================================

This service encapsulates all conversation storage concerns, providing a clean
abstraction over the underlying vector database operations. It ensures proper
serialization of operations and handles the complexity of multi-step persistence.

This reduces cognitive load by presenting a single, cohesive interface for
conversation storage rather than scattered database operations.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

# Import types needed - these will be passed in as dependencies
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import aiofiles

# Import database protection service
from aura_backend.database_protection import get_protection_service

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class ConversationExchange:
    """
    Represents a complete conversational exchange between user and AI.

    This data structure captures all artifacts of a single conversation turn,
    providing a cohesive view of the interaction rather than scattered components.
    """

    user_memory: Any  # Will be ConversationMemory when imported
    ai_memory: Any  # Will be ConversationMemory when imported
    user_emotional_state: Optional[Any] = (
        None  # Will be EmotionalStateData when imported
    )
    ai_emotional_state: Optional[Any] = None  # Will be EmotionalStateData when imported
    ai_cognitive_state: Optional[Any] = None  # Will be CognitiveState when imported
    session_id: str = ""
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if (
            not self.session_id
            and hasattr(self.user_memory, "session_id")
            and self.user_memory.session_id
        ):
            self.session_id = self.user_memory.session_id


class ConversationPersistenceService:
    """
    Encapsulates all conversation storage concerns with proper serialization.

    This service provides:
    - Atomic persistence of conversation exchanges
    - Proper serialization to prevent ChromaDB compaction conflicts
    - Graceful error handling with detailed logging
    - Performance metrics for monitoring
    - Cleanup and archival capabilities
    - Recovery mechanisms for failed operations
    - ChromaDB-specific error handling and recovery

    By centralizing persistence logic, we reduce the cognitive overhead of
    understanding how conversations are stored throughout the application.
    """

    def __init__(
        self,
        vector_db: Any,  # Will be AuraVectorDB when imported
        file_system: Any,  # Will be AuraFileSystem when imported
        compaction_delay: float = 0.5,  # Increased default delay
        max_retries: int = 3,
        backup_enabled: bool = True,
        chromadb_recovery_enabled: bool = True,
        emergency_recovery_enabled: bool = True,  # New parameter
        use_database_protection: bool = True,  # Integrate with database protection service
    ):
        self.vector_db = vector_db
        self.file_system = file_system
        self.compaction_delay = compaction_delay
        self.max_retries = max_retries
        self.backup_enabled = backup_enabled
        self.chromadb_recovery_enabled = chromadb_recovery_enabled
        self.emergency_recovery_enabled = emergency_recovery_enabled
        self.use_database_protection = use_database_protection
        self._consecutive_failures = 0
        self._emergency_recovery_threshold = (
            5  # Trigger emergency recovery after 5 consecutive failures
        )

        # Initialize database protection service if enabled
        if self.use_database_protection:
            try:
                self._protection_service = get_protection_service()
                logger.info("🛡️ Database protection service integrated")
            except Exception as e:
                logger.warning(
                    f"⚠️ Failed to initialize database protection service: {e}"
                )
                self._protection_service = None
                self.use_database_protection = False
        else:
            self._protection_service = None

        # Semaphore ensures only one persistence operation at a time
        # This prevents the root cause of ChromaDB compaction conflicts
        self._write_semaphore = asyncio.Semaphore(1)

        # Track ChromaDB health
        self._chromadb_error_count = 0
        self._last_chromadb_error = None

        # Metrics for monitoring performance
        self._metrics = {
            "total_exchanges_stored": 0,
            "failed_stores": 0,
            "average_store_time": 0.0,
            "last_error": None,
            "retries_performed": 0,
            "backups_created": 0,
            "cleanups_performed": 0,
            "archives_created": 0,
        }

        # Failed operation queue for retry
        self._failed_operations: List[Dict[str, Any]] = []

        # Event callbacks for monitoring
        self._event_callbacks: Dict[str, List[Callable]] = {
            "exchange_stored": [],
            "storage_failed": [],
            "cleanup_completed": [],
            "archive_created": [],
        }

    def _is_chromadb_compaction_error(self, error: Exception) -> bool:
        """Check if error is related to ChromaDB compaction issues"""
        error_str = str(error).lower()
        compaction_indicators = [
            "failed to apply logs to the metadata segment",
            "error sending backfill request to compactor",
            "error executing plan",
            "compaction",
            "metadata segment",
            "database is locked",
            "disk i/o error",
            "database corruption",
            "no such table",
            "sqlite_busy",
            "sqlite_locked",
            "wal file",
            "shim file",
        ]
        return any(indicator in error_str for indicator in compaction_indicators)

    async def _handle_chromadb_error(self, error: Exception, operation: str) -> bool:
        """
        Handle ChromaDB-specific errors with recovery attempts.

        Args:
            error: The exception that occurred
            operation: Description of the operation that failed

        Returns:
            True if recovery was attempted, False otherwise
        """
        if not self._is_chromadb_compaction_error(error):
            return False

        self._chromadb_error_count += 1
        self._consecutive_failures += 1
        self._last_chromadb_error = datetime.now()

        logger.error("🚨 ChromaDB error during %s: %s", operation, error)
        logger.error("📊 Consecutive failures: %s", self._consecutive_failures)

        # Check if we should trigger emergency recovery
        if (
            self.emergency_recovery_enabled
            and self._consecutive_failures >= self._emergency_recovery_threshold
        ):
            logger.critical(
                f"🚨 CRITICAL: {self._consecutive_failures} consecutive failures - triggering emergency recovery"
            )
            return await self._trigger_emergency_recovery()

        if not self.chromadb_recovery_enabled:
            logger.warning("⚠️ ChromaDB recovery disabled - error not handled")
            return False

        try:
            logger.info("🔧 Attempting ChromaDB recovery...")

            # Wait longer to allow any ongoing operations to complete
            await asyncio.sleep(2.0)

            # Try to force checkpoint if possible
            if hasattr(self.vector_db, "client"):
                try:
                    # Try to get a heartbeat from ChromaDB
                    self.vector_db.client.heartbeat()
                    logger.info("💓 ChromaDB heartbeat successful")
                except Exception as heartbeat_error:
                    logger.warning("⚠️ ChromaDB heartbeat failed: %s", heartbeat_error)

            # Clear any pending operations by waiting
            await asyncio.sleep(self.compaction_delay * 3)

            logger.info("✅ ChromaDB recovery attempt completed")
            return True

        except Exception as recovery_error:
            logger.error("❌ ChromaDB recovery failed: %s", recovery_error)
            return False

    async def _trigger_emergency_recovery(self) -> bool:
        """
        Trigger emergency database recovery using the database protection service.

        Returns:
            True if emergency recovery was initiated, False otherwise
        """
        try:
            logger.critical("🚨 INITIATING EMERGENCY DATABASE RECOVERY")
            logger.critical(
                "⚠️ Using database protection service for coordinated recovery!"
            )

            # Use the database protection service for emergency backup
            protection_service = get_protection_service()
            backup_path = protection_service.emergency_backup()

            if backup_path:
                logger.critical("✅ Emergency backup created successfully")
                logger.critical(f"💾 Backup location: {backup_path}")

                # Instead of using recovery tool that creates conflicts,
                # we'll reset our database connection and let it reinitialize
                logger.critical("🔄 Resetting database connection to resolve conflicts")

                try:
                    # Close current database connection if possible
                    if hasattr(self.vector_db, "client"):
                        self.vector_db.client = None

                    # Signal that application needs restart for clean state
                    logger.critical(
                        "🔄 Application needs restart to reinitialize database cleanly"
                    )

                    # Reset failure counters
                    self._consecutive_failures = 0
                    self._chromadb_error_count = 0

                    return True

                except Exception as reset_error:
                    logger.critical(f"❌ Database reset failed: {reset_error}")
                    return False
            else:
                logger.critical("❌ Failed to create emergency backup")
                return False

        except Exception as e:
            logger.critical(f"❌ Emergency recovery trigger failed: {e}")
            return False

    async def persist_conversation_exchange(
        self, exchange: ConversationExchange, update_profile: bool = True
    ) -> Dict[str, Any]:
        """
        Atomically persists a complete conversational exchange with enhanced error handling.

        This method ensures all components of a conversation are stored in the
        correct sequence with proper delays to prevent compaction conflicts.

        Args:
            exchange: Complete conversation exchange data
            update_profile: Whether to update user profile after storage

        Returns:
            Dictionary containing storage results and any errors
        """
        # Use database protection service if available
        if self.use_database_protection and self._protection_service:
            return await self._perform_protected_operation(
                "conversation_exchange_persistence",
                self._persist_conversation_exchange_internal,
                exchange,
                update_profile,
            )
        else:
            return await self._persist_conversation_exchange_internal(
                exchange, update_profile
            )

    async def _persist_conversation_exchange_internal(
        self, exchange: ConversationExchange, update_profile: bool = True
    ) -> Dict[str, Any]:
        """
        Internal persistence method that does the actual work.
        """
        async with self._write_semaphore:
            start_time = datetime.now()
            results = {
                "success": True,
                "stored_components": [],
                "errors": [],
                "duration_ms": 0,
                "retry_count": 0,
            }

            for attempt in range(self.max_retries):
                try:
                    results["retry_count"] = attempt

                    # Increase delay for retry attempts
                    if attempt > 0:
                        delay = self.compaction_delay * (attempt + 1) * 2
                        logger.info(
                            f"🔄 Retry attempt {attempt + 1} after {delay:.1f}s delay"
                        )
                        await asyncio.sleep(delay)

                    # Phase 1: Store conversation memories
                    await self._store_conversation_pair(exchange, results)

                    # Phase 2: Store emotional patterns
                    await self._store_emotional_patterns(exchange, results)

                    # Phase 3: Update user profile if requested
                    if update_profile:
                        await self._update_user_profile(exchange, results)

                    # Update metrics on success
                    self._metrics["total_exchanges_stored"] += 1

                    # Reset consecutive failures on successful operation
                    self._consecutive_failures = 0

                    # Reset error count on success
                    if self._chromadb_error_count > 0:
                        logger.info(
                            f"✅ ChromaDB persistence recovered after {self._chromadb_error_count} errors"
                        )
                        self._chromadb_error_count = 0

                    break  # Success - exit retry loop

                except Exception as e:
                    logger.error("❌ Persistence attempt %s failed: %s", attempt + 1, e)
                    results["errors"].append(f"attempt_{attempt + 1}: {e}")

                    # Handle ChromaDB-specific errors
                    if self._is_chromadb_compaction_error(e):
                        recovery_attempted = await self._handle_chromadb_error(
                            e, f"persistence (attempt {attempt + 1})"
                        )

                        if recovery_attempted and attempt < self.max_retries - 1:
                            logger.info(
                                "🔄 Retrying persistence after ChromaDB recovery"
                            )
                            continue

                    # If this is the last attempt, mark as failed
                    if attempt == self.max_retries - 1:
                        results["success"] = False
                        self._metrics["failed_stores"] += 1
                        self._metrics["last_error"] = str(e)

                        # Queue for retry if this was a ChromaDB error
                        if self._is_chromadb_compaction_error(e):
                            self._failed_operations.append(
                                {
                                    "type": "conversation_exchange",
                                    "exchange": exchange,
                                    "update_profile": update_profile,
                                    "failed_at": datetime.now().isoformat(),
                                    "error": str(e),
                                }
                            )

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds() * 1000
            results["duration_ms"] = duration

            # Update average store time
            self._update_average_store_time(duration)

            status = "✅" if results["success"] else "❌"
            logger.info(
                f"{status} Persistence completed in {duration:.1f}ms - "
                f"Success: {results['success']}, "
                f"Components: {len(results['stored_components'])}, "
                f"Retries: {results['retry_count']}"
            )

            return results

    async def persist_conversation_exchange_immediate(
        self,
        exchange: ConversationExchange,
        update_profile: bool = True,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Immediate persistence with timeout for critical chat history saving.

        This method prioritizes speed and reliability for real-time chat history storage.
        It uses optimized settings and aggressive error recovery to ensure conversations
        are saved consistently.

        Args:
            exchange: Complete conversation exchange data
            update_profile: Whether to update user profile after storage
            timeout (float): Maximum time to spend on persistence (seconds)

        Returns:
            Dictionary containing storage results and any errors
        """
        start_time = datetime.now()

        try:
            # Use timeout wrapper for critical persistence
            result = await asyncio.wait_for(
                self._persist_conversation_exchange_optimized(exchange, update_profile),
                timeout=timeout,
            )

            # Add timing information
            duration = (datetime.now() - start_time).total_seconds() * 1000
            result["duration_ms"] = duration
            result["method"] = "immediate_optimized"

            return result

        except asyncio.TimeoutError:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(
                f"⏱️ Immediate persistence timeout after {timeout}s for {exchange.user_memory.user_id}"
            )

            return {
                "success": False,
                "stored_components": [],
                "errors": [f"Persistence timeout after {timeout}s"],
                "duration_ms": duration,
                "retry_count": 0,
                "method": "immediate_timeout",
            }

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(
                f"❌ Immediate persistence failed for {exchange.user_memory.user_id}: {e}"
            )

            return {
                "success": False,
                "stored_components": [],
                "errors": [str(e)],
                "duration_ms": duration,
                "retry_count": 0,
                "method": "immediate_exception",
            }

    async def _persist_conversation_exchange_optimized(
        self, exchange: ConversationExchange, update_profile: bool = True
    ) -> Dict[str, Any]:
        """
        Optimized persistence method for immediate execution.

        Uses reduced delays and streamlined error handling for speed.
        """
        async with self._write_semaphore:
            results = {
                "success": True,
                "stored_components": [],
                "errors": [],
                "retry_count": 0,
            }

            # Reduced retry count for immediate persistence (prioritize speed)
            max_immediate_retries = 2

            for attempt in range(max_immediate_retries):
                try:
                    results["retry_count"] = attempt

                    # Reduced delay for immediate persistence
                    if attempt > 0:
                        delay = (
                            self.compaction_delay * 0.5
                        )  # Faster retry for immediate mode
                        logger.debug(
                            f"🔄 Immediate retry {attempt + 1} after {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)

                    # Optimized storage sequence
                    await self._store_conversation_pair_optimized(exchange, results)

                    # Store emotional patterns (non-blocking for immediate mode)
                    try:
                        await self._store_emotional_patterns(exchange, results)
                    except Exception as emotion_error:
                        logger.warning(
                            f"⚠️ Emotional pattern storage failed (non-critical): {emotion_error}"
                        )
                        results["errors"].append(f"emotional_patterns: {emotion_error}")

                    # Update user profile (non-blocking for immediate mode)
                    if update_profile:
                        try:
                            await self._update_user_profile(exchange, results)
                        except Exception as profile_error:
                            logger.warning(
                                f"⚠️ Profile update failed (non-critical): {profile_error}"
                            )
                            results["errors"].append(f"profile_update: {profile_error}")

                    # Update metrics on success
                    self._metrics["total_exchanges_stored"] += 1
                    self._consecutive_failures = 0

                    logger.debug(
                        f"✅ Immediate persistence successful for {exchange.user_memory.user_id}"
                    )
                    break  # Success - exit retry loop

                except Exception as e:
                    logger.error(
                        f"❌ Immediate persistence attempt {attempt + 1} failed: {e}"
                    )
                    results["errors"].append(f"attempt_{attempt + 1}: {e}")

                    # For immediate persistence, don't spend time on recovery
                    if attempt == max_immediate_retries - 1:
                        results["success"] = False
                        self._metrics["failed_stores"] += 1

            return results

    async def _store_conversation_pair_optimized(
        self, exchange: ConversationExchange, results: Dict[str, Any]
    ) -> None:
        """
        Optimized conversation pair storage for immediate persistence.

        Uses minimal delays while maintaining data integrity.
        """
        try:
            # Store user message first
            user_doc_id = await self.vector_db.store_conversation(exchange.user_memory)
            results["stored_components"].append(f"user_message:{user_doc_id}")

            # Minimal delay for immediate persistence
            await asyncio.sleep(self.compaction_delay * 0.3)

            # Store AI response
            ai_doc_id = await self.vector_db.store_conversation(exchange.ai_memory)
            results["stored_components"].append(f"ai_message:{ai_doc_id}")

        except Exception as e:
            logger.error("Failed to store optimized conversation pair: %s", e)
            results["errors"].append(f"conversation_storage: {e}")
            raise

    async def _store_conversation_pair(
        self, exchange: ConversationExchange, results: Dict[str, Any]
    ) -> None:
        """
        Stores the user-AI conversation pair with proper sequencing.

        The delay between operations allows ChromaDB's write-ahead log to
        flush and prevents compaction conflicts.
        """
        try:
            # Store user message first - establishes context
            user_doc_id = await self.vector_db.store_conversation(exchange.user_memory)
            results["stored_components"].append(f"user_message:{user_doc_id}")

            # Critical: Allow WAL flush and potential compaction
            await asyncio.sleep(self.compaction_delay)

            # Store AI response - completes the exchange
            ai_doc_id = await self.vector_db.store_conversation(exchange.ai_memory)
            results["stored_components"].append(f"ai_message:{ai_doc_id}")

        except Exception as e:
            logger.error("Failed to store conversation pair: %s", e)
            results["errors"].append(f"conversation_storage: {e}")
            raise

    async def _store_emotional_patterns(
        self, exchange: ConversationExchange, results: Dict[str, Any]
    ) -> None:
        """
        Stores emotional patterns for both user and AI.

        Emotional patterns are stored as metadata after primary conversation
        data to maintain proper data hierarchy.
        """
        try:
            if exchange.ai_emotional_state:
                await self.vector_db.store_emotional_pattern(
                    exchange.ai_emotional_state,
                    "aura",  # AI emotions tracked under 'aura' entity
                )
                results["stored_components"].append("ai_emotional_pattern")

            if exchange.user_emotional_state:
                await self.vector_db.store_emotional_pattern(
                    exchange.user_emotional_state, exchange.user_memory.user_id
                )
                results["stored_components"].append("user_emotional_pattern")

        except Exception as e:
            logger.error("Failed to store emotional patterns: %s", e)
            results["errors"].append(f"emotional_storage: {e}")
            # Non-critical error - don't propagate

    async def _update_user_profile(
        self, exchange: ConversationExchange, results: Dict[str, Any]
    ) -> None:
        """
        Updates user profile with latest interaction data.

        Profile updates are non-critical and failures don't affect
        the core conversation storage.
        """
        try:
            user_id = exchange.user_memory.user_id
            profile = await self.file_system.load_user_profile(user_id) or {
                "name": user_id,
                "created_at": datetime.now().isoformat(),
            }

            # Update interaction metadata
            profile["last_interaction"] = datetime.now().isoformat()
            profile["total_messages"] = int(profile.get("total_messages", 0)) + 1

            # Store latest emotional states for quick access
            if exchange.user_emotional_state:
                profile["last_emotional_state"] = {
                    "name": exchange.user_emotional_state.name,
                    "intensity": exchange.user_emotional_state.intensity.value,
                    "timestamp": (
                        exchange.user_emotional_state.timestamp.isoformat()
                        if exchange.user_emotional_state.timestamp
                        else None
                    ),
                }

            await self.file_system.save_user_profile(user_id, profile)
            results["stored_components"].append("user_profile_update")

        except Exception as e:
            logger.error("Failed to update user profile: %s", e)
            results["errors"].append(f"profile_update: {e}")
            # Non-critical error - don't propagate

    def _update_average_store_time(self, duration_ms: float) -> None:
        """Updates rolling average of storage duration for monitoring."""
        current_avg = self._metrics["average_store_time"]
        total_stores = self._metrics["total_exchanges_stored"]

        if total_stores == 0:
            # First measurement - no division needed
            self._metrics["average_store_time"] = duration_ms
        elif total_stores == 1:
            self._metrics["average_store_time"] = duration_ms
        else:
            # Rolling average calculation
            self._metrics["average_store_time"] = (
                current_avg * (total_stores - 1) + duration_ms
            ) / total_stores

    async def cleanup_old_conversations(
        self,
        user_id: str,
        days_to_keep: int = 30000,
        archive_before_cleanup: bool = True,
    ) -> Dict[str, Any]:
        """
        Clean up old conversations with optional archival.

        Args:
            user_id: User whose conversations to clean up
            days_to_keep: Number of days of conversations to retain
            archive_before_cleanup: Whether to archive before deleting

        Returns:
            Dictionary containing cleanup results
        """
        # Use database protection service for this risky operation
        if self.use_database_protection and self._protection_service:
            return await self._perform_protected_operation(
                "cleanup_old_conversations",
                self._cleanup_old_conversations_internal,
                user_id,
                days_to_keep,
                archive_before_cleanup,
            )
        else:
            return await self._cleanup_old_conversations_internal(
                user_id, days_to_keep, archive_before_cleanup
            )

    async def _cleanup_old_conversations_internal(
        self,
        user_id: str,
        days_to_keep: int = 30000,
        archive_before_cleanup: bool = True,
    ) -> Dict[str, Any]:
        """
        Internal cleanup method that does the actual work.
        """
        async with self._write_semaphore:
            start_time = datetime.now()
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            results = {
                "success": True,
                "conversations_found": 0,
                "conversations_archived": 0,
                "conversations_deleted": 0,
                "errors": [],
                "duration_ms": 0,
            }

            try:
                # Find old conversations
                old_conversations = self.vector_db.conversations.get(
                    where={
                        "$and": [
                            {"user_id": {"$eq": user_id}},
                            {"timestamp": {"$lt": cutoff_date.isoformat()}},
                        ]
                    },
                    include=["documents", "metadatas", "embeddings"],
                )

                if not old_conversations or not old_conversations.get("ids"):
                    results["conversations_found"] = 0
                    return results

                results["conversations_found"] = len(old_conversations["ids"])

                # Archive conversations if requested
                if archive_before_cleanup and results["conversations_found"] > 0:
                    archive_result = await self._archive_conversations_to_backup(
                        user_id, old_conversations
                    )
                    results["conversations_archived"] = archive_result.get(
                        "archived_count", 0
                    )
                    if archive_result.get("errors"):
                        results["errors"].extend(archive_result["errors"])

                # Delete old conversations
                self.vector_db.conversations.delete(ids=old_conversations["ids"])
                results["conversations_deleted"] = len(old_conversations["ids"])

                # Update metrics
                self._metrics["cleanups_performed"] += 1

                # Trigger event callbacks
                await self._trigger_event_callbacks(
                    "cleanup_completed",
                    {"user_id": user_id, "cleanup_results": results},
                )

                logger.info(
                    f"🧹 Cleaned up {results['conversations_deleted']} old conversations for {user_id}"
                )

            except Exception as e:
                logger.error("❌ Failed to cleanup conversations: %s", e)
                results["success"] = False
                results["errors"].append(str(e))

            finally:
                results["duration_ms"] = (
                    datetime.now() - start_time
                ).total_seconds() * 1000

            return results

    async def _archive_conversations_to_backup(
        self, user_id: str, conversations_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Archive conversations to backup files before deletion.

        Args:
            user_id: User ID for the backup
            conversations_data: Raw conversation data from ChromaDB

        Returns:
            Archival results
        """
        try:
            if not self.backup_enabled:
                return {"archived_count": 0, "message": "Backup disabled"}

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"conversations_backup_{user_id}_{timestamp}.json"
            backup_path = self.file_system.base_path / "backups" / backup_filename

            # Ensure backup directory exists
            backup_path.parent.mkdir(exist_ok=True)

            # Prepare backup data
            backup_data = {
                "user_id": user_id,
                "backup_timestamp": datetime.now().isoformat(),
                "conversation_count": len(conversations_data.get("ids", [])),
                "conversations": [],
            }

            # Process each conversation
            for i, doc_id in enumerate(conversations_data.get("ids", [])):
                conversation = {
                    "id": doc_id,
                    "content": (
                        conversations_data["documents"][i]
                        if conversations_data.get("documents")
                        else ""
                    ),
                    "metadata": (
                        conversations_data["metadatas"][i]
                        if conversations_data.get("metadatas")
                        else {}
                    ),
                    "embedding": (
                        conversations_data["embeddings"][i]
                        if conversations_data.get("embeddings")
                        else None
                    ),
                }
                backup_data["conversations"].append(conversation)

            # Save backup file using aiofiles directly
            async with aiofiles.open(backup_path, "w") as f:
                await f.write(json.dumps(backup_data, indent=2, default=str))

            self._metrics["backups_created"] += 1

            return {
                "archived_count": len(conversations_data.get("ids", [])),
                "backup_file": str(backup_path),
                "errors": [],
            }

        except Exception as e:
            logger.error("❌ Failed to archive conversations: %s", e)
            return {"archived_count": 0, "errors": [str(e)]}

    async def search_with_context_enrichment(
        self,
        query: str,
        user_id: str,
        n_results: int = 5000,
        include_emotional_context: bool = True,
        include_temporal_context: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Enhanced search with contextual enrichment.

        Args:
            query: Search query
            user_id: User ID for scoped search
            n_results: Number of results to return
            include_emotional_context: Whether to include emotional state context
            include_temporal_context: Whether to include temporal context

        Returns:
            Enriched search results with additional context
        """
        async with self._write_semaphore:
            try:
                # Get basic search results
                base_results = await self.vector_db.search_conversations(
                    query=query, user_id=user_id, n_results=n_results
                )

                enriched_results = []

                for result in base_results:
                    enriched_result = result.copy()

                    # Add emotional context if requested
                    if include_emotional_context:
                        emotional_context = (
                            await self._get_emotional_context_for_message(
                                result, user_id
                            )
                        )
                        enriched_result["emotional_context"] = emotional_context

                    # Add temporal context if requested
                    if include_temporal_context:
                        temporal_context = await self._get_temporal_context_for_message(
                            result, user_id
                        )
                        enriched_result["temporal_context"] = temporal_context

                    enriched_results.append(enriched_result)

                return enriched_results

            except Exception as e:
                logger.error("❌ Enhanced search failed: %s", e)
                return []

    async def _get_emotional_context_for_message(
        self, message_result: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        """
        Get emotional context around a specific message.

        Args:
            message_result: Message search result
            user_id: User ID for context search

        Returns:
            Emotional context information
        """
        try:
            timestamp = message_result.get("metadata", {}).get("timestamp")
            if not timestamp:
                return {"context_available": False}

            # Get emotional patterns around this time
            message_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            context_window = timedelta(hours=2)  # 2-hour window around message

            emotional_patterns = self.vector_db.emotional_patterns.get(
                where={
                    "$and": [
                        {"user_id": {"$eq": user_id}},
                        {
                            "timestamp": {
                                "$gte": (message_time - context_window).isoformat()
                            }
                        },
                        {
                            "timestamp": {
                                "$lte": (message_time + context_window).isoformat()
                            }
                        },
                    ]
                },
                include=["metadatas"],
            )

            if not emotional_patterns or not emotional_patterns.get("metadatas"):
                return {"context_available": False}

            # Analyze emotional patterns
            emotions = [
                meta.get("emotion_name", "Unknown")
                for meta in emotional_patterns["metadatas"]
            ]
            intensities = [
                meta.get("intensity", "Medium")
                for meta in emotional_patterns["metadatas"]
            ]

            return {
                "context_available": True,
                "dominant_emotions": list(set(emotions)),
                "intensity_range": list(set(intensities)),
                "pattern_count": len(emotions),
                "timeframe_hours": 2,
            }

        except Exception as e:
            logger.error("❌ Failed to get emotional context: %s", e)
            return {"context_available": False, "error": str(e)}

    async def _get_temporal_context_for_message(
        self, message_result: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        """
        Get temporal context around a specific message by performing multiple queries.

        This method performs two separate queries: one for messages before and one for messages after
        the given message's timestamp. The context is determined based on the presence of messages
        surrounding the target message, which helps assess conversation continuity or isolation.

        Args:
            message_result: Message search result
            user_id: User ID for context search

        Returns:
            Temporal context information, including counts of messages before and after,
            and flags for conversation continuity or isolation.
        """
        try:
            timestamp = message_result.get("metadata", {}).get("timestamp")
            if not timestamp:
                return {"context_available": False}

            # Consolidated block: Query for messages before and after the given timestamp
            # This helps determine conversation continuity and isolation in a maintainable way.
            before_after_results = {}
            for direction, op in [("before", "$lt"), ("after", "$gt")]:
                before_after_results[direction] = self.vector_db.search_conversations(
                    query="",  # Empty query to get by time only
                    user_id=user_id,
                    n_results=2,
                    where_filter={"timestamp": {op: timestamp}},
                )

            before_messages, after_messages = await asyncio.gather(
                before_after_results["before"], before_after_results["after"]
            )

            return {
                "context_available": True,
                "messages_before": len(before_messages),
                "messages_after": len(after_messages),
                "conversation_continuity": len(before_messages) > 0
                and len(after_messages) > 0,
                "isolated_message": len(before_messages) == 0
                and len(after_messages) == 0,
            }

        except Exception as e:
            logger.error("❌ Failed to get temporal context: %s", e)
            return {"context_available": False, "error": str(e)}

    async def get_conversation_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive conversation statistics for a user.

        Args:
            user_id: User ID for statistics

        Returns:
            Detailed conversation statistics
        """
        try:
            # Get all conversations for user
            all_conversations = self.vector_db.conversations.get(
                where={"user_id": {"$eq": user_id}}, include=["metadatas"]
            )

            if not all_conversations or not all_conversations.get("metadatas"):
                return {
                    "user_id": user_id,
                    "total_conversations": 0,
                    "message": "No conversations found",
                }

            metadata_list = all_conversations["metadatas"]

            # Calculate statistics
            total_conversations = len(metadata_list)
            senders = [meta.get("sender", "unknown") for meta in metadata_list]
            sessions = list(
                set(meta.get("session_id", "unknown") for meta in metadata_list)
            )
            emotions = [
                meta.get("emotion_name")
                for meta in metadata_list
                if meta.get("emotion_name")
            ]

            # Time analysis
            timestamps = [
                datetime.fromisoformat(meta.get("timestamp", "").replace("Z", "+00:00"))
                for meta in metadata_list
                if meta.get("timestamp")
            ]

            stats = {
                "user_id": user_id,
                "total_conversations": total_conversations,
                "unique_sessions": len(sessions),
                "message_breakdown": {
                    "user_messages": senders.count("user"),
                    "aura_messages": senders.count("aura"),
                    "other_messages": total_conversations
                    - senders.count("user")
                    - senders.count("aura"),
                },
                "emotional_summary": {
                    "emotions_recorded": len(emotions),
                    "unique_emotions": len(set(emotions)) if emotions else 0,
                    "most_common_emotions": (
                        self._get_top_emotions(emotions, 3) if emotions else []
                    ),
                },
                "temporal_analysis": (
                    self._analyze_conversation_timing(timestamps) if timestamps else {}
                ),
            }

            return stats

        except Exception as e:
            logger.error("❌ Failed to get conversation statistics: %s", e)
            return {"user_id": user_id, "error": str(e), "total_conversations": 0}

    def _get_top_emotions(
        self, emotions: List[str], top_n: int
    ) -> List[Dict[str, Any]]:
        """Get top N most frequent emotions with counts."""
        from collections import Counter

        emotion_counts = Counter(emotions)
        return [
            {"emotion": emotion, "count": count}
            for emotion, count in emotion_counts.most_common(top_n)
        ]

    def _analyze_conversation_timing(
        self, timestamps: List[datetime]
    ) -> Dict[str, Any]:
        """Analyze conversation timing patterns."""
        if not timestamps:
            return {}

        sorted_times = sorted(timestamps)

        return {
            "first_conversation": sorted_times[0].isoformat(),
            "last_conversation": sorted_times[-1].isoformat(),
            "conversation_span_days": (sorted_times[-1] - sorted_times[0]).days,
            "most_active_hour": self._find_most_active_hour(timestamps),
            "average_daily_conversations": len(timestamps)
            / max((sorted_times[-1] - sorted_times[0]).days, 1),
        }

    def _find_most_active_hour(self, timestamps: List[datetime]) -> int:
        """Find the hour of day with most conversation activity."""
        from collections import Counter

        hours = [ts.hour for ts in timestamps]
        hour_counts = Counter(hours)
        return hour_counts.most_common(1)[0][0] if hour_counts else 0

    async def register_event_callback(
        self, event_type: str, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register callback for persistence events.

        Args:
            event_type: Type of event to listen for
            callback: Function to call when event occurs
        """
        if event_type not in self._event_callbacks:
            self._event_callbacks[event_type] = []

        self._event_callbacks[event_type].append(callback)
        logger.info("📡 Registered callback for event: %s", event_type)

    async def _trigger_event_callbacks(
        self, event_type: str, event_data: Dict[str, Any]
    ) -> None:
        """Trigger all callbacks for a specific event type."""
        if event_type in self._event_callbacks:
            for callback in self._event_callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event_data)
                    else:
                        callback(event_data)
                except Exception as e:
                    logger.error("❌ Event callback failed for %s: %s", event_type, e)

    async def get_persistence_metrics(self) -> Dict[str, Any]:
        """
        Returns current persistence metrics for monitoring.

        These metrics help identify performance issues and bottlenecks
        in the storage pipeline.
        """
        metrics = {
            **self._metrics,
            "semaphore_available": self._write_semaphore._value,
            "failed_operations_queued": len(self._failed_operations),
            "event_callbacks_registered": sum(
                len(callbacks) for callbacks in self._event_callbacks.values()
            ),
            "chromadb_error_count": self._chromadb_error_count,
            "consecutive_failures": self._consecutive_failures,
            "emergency_recovery_threshold": self._emergency_recovery_threshold,
            "emergency_recovery_enabled": self.emergency_recovery_enabled,
            "last_chromadb_error": (
                self._last_chromadb_error.isoformat()
                if self._last_chromadb_error
                else None
            ),
            "chromadb_recovery_enabled": self.chromadb_recovery_enabled,
            "database_protection_enabled": self.use_database_protection,
            "timestamp": datetime.now().isoformat(),
        }

        # Add protection service health if available
        if self.use_database_protection and self._protection_service:
            try:
                protection_health = self._protection_service.get_health_status()
                metrics["protection_service"] = protection_health
            except Exception as e:
                metrics["protection_service"] = {
                    "error": str(e),
                    "status": "unavailable",
                }
        else:
            metrics["protection_service"] = {"status": "disabled"}

        return metrics

    async def safe_search_conversations(
        self,
        query: str,
        user_id: str,
        n_results: int = 5000,
        where_filter: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Thread-safe search through conversation history with ChromaDB error handling.

        Uses the same semaphore as persistence operations to prevent
        compaction conflicts during concurrent database access.
        """
        async with self._write_semaphore:
            for attempt in range(self.max_retries):
                try:
                    # Allow brief settling time if there were recent writes
                    await asyncio.sleep(
                        0.1 * (attempt + 1)
                    )  # Increasing delay per attempt

                    results = await self.vector_db.search_conversations(
                        query=query,
                        user_id=user_id,
                        n_results=n_results,
                        where_filter=where_filter,
                    )

                    # Reset consecutive failures on successful operation
                    self._consecutive_failures = 0

                    # Reset error count on success
                    if self._chromadb_error_count > 0:
                        logger.info(
                            f"✅ ChromaDB search recovered after {self._chromadb_error_count} errors"
                        )
                        self._chromadb_error_count = 0

                    return results

                except Exception as e:
                    logger.error("❌ Safe search attempt %s failed: %s", attempt + 1, e)

                    # Handle ChromaDB-specific errors
                    if self._is_chromadb_compaction_error(e):
                        recovery_attempted = await self._handle_chromadb_error(
                            e, f"search (attempt {attempt + 1})"
                        )

                        if recovery_attempted and attempt < self.max_retries - 1:
                            logger.info(
                                f"🔄 Retrying search after ChromaDB recovery (attempt {attempt + 2})"
                            )
                            continue

                    # If this is the last attempt or not a ChromaDB error, give up
                    if attempt == self.max_retries - 1:
                        logger.error("❌ All search attempts failed. Last error: %s", e)
                        return []

            return []

    async def safe_get_chat_history(
        self, user_id: str, limit: int = 5000
    ) -> Dict[str, Any]:
        """
        Thread-safe retrieval of chat history with enhanced error handling.

        Uses the same semaphore to prevent concurrent access conflicts
        during history retrieval operations.
        """
        async with self._write_semaphore:
            try:
                # Allow brief settling time
                await asyncio.sleep(0.05)

                # Get recent conversations from vector DB with better error handling
                try:
                    results = self.vector_db.conversations.get(
                        where={"user_id": {"$eq": user_id}},
                        limit=limit,
                        include=["documents", "metadatas"],
                    )
                except Exception as db_error:
                    logger.error(
                        f"❌ Database query failed for chat history: {db_error}"
                    )
                    return {
                        "sessions": [],
                        "total": 0,
                        "error": "Database query failed",
                    }

                if (
                    not results
                    or not results.get("documents")
                    or not isinstance(results["documents"], list)
                ):
                    logger.info("📭 No chat history found for user %s", user_id)
                    return {"sessions": [], "total": 0}

                # Group by session with enhanced processing and deduplication
                sessions = {}
                processed_messages = 0
                skipped_duplicates = 0
                seen_message_ids = set()  # Track unique messages to prevent duplicates

                for i, doc in enumerate(results["documents"]):
                    try:
                        metadata = (
                            results["metadatas"][i]
                            if results.get("metadatas")
                            and results["metadatas"] is not None
                            else {}
                        )
                        doc_id = (
                            results["ids"][i]
                            if results.get("ids") and i < len(results["ids"])
                            else f"unknown_{i}"
                        )
                        session_id = metadata.get("session_id", "unknown")

                        # Skip duplicate messages (can happen with database conflicts)
                        if doc_id in seen_message_ids:
                            logger.debug("⚠️ Skipping duplicate message %s", doc_id)
                            skipped_duplicates += 1
                            continue

                        seen_message_ids.add(doc_id)

                        # Validate essential fields
                        if not doc or not metadata.get("timestamp"):
                            logger.warning(
                                f"⚠️ Skipping invalid message at index {i}: missing content or timestamp"
                            )
                            continue

                        # Create session entry if new
                        if session_id not in sessions:
                            sessions[session_id] = {
                                "session_id": session_id,
                                "messages": [],
                                "start_time": metadata.get("timestamp", ""),
                                "last_time": metadata.get("timestamp", ""),
                                "message_ids": set(),  # Track message IDs per session
                            }

                        # Skip if this message is already in this session (additional deduplication)
                        if doc_id in sessions[session_id]["message_ids"]:
                            logger.debug(
                                f"⚠️ Skipping duplicate message {doc_id} in session {session_id}"
                            )
                            continue

                        sessions[session_id]["message_ids"].add(doc_id)

                        # Add message with validation and unique ID
                        message = {
                            "id": doc_id,
                            "content": str(doc),
                            "sender": metadata.get("sender", "unknown"),
                            "timestamp": metadata.get("timestamp", ""),
                            "emotion": metadata.get("emotion_name", "Normal"),
                            "session_id": session_id,
                        }

                        sessions[session_id]["messages"].append(message)
                        processed_messages += 1

                        # Update session times with proper timestamp comparison
                        timestamp = metadata.get("timestamp", "")
                        if timestamp:
                            # Use string comparison for ISO timestamps (works correctly)
                            if (
                                not sessions[session_id]["start_time"]
                                or timestamp < sessions[session_id]["start_time"]
                            ):
                                sessions[session_id]["start_time"] = timestamp
                            if (
                                not sessions[session_id]["last_time"]
                                or timestamp > sessions[session_id]["last_time"]
                            ):
                                sessions[session_id]["last_time"] = timestamp

                    except Exception as message_error:
                        logger.error(
                            f"❌ Error processing message {i}: {message_error}"
                        )
                        continue

                # Clean up temporary tracking data before returning
                for session in sessions.values():
                    if "message_ids" in session:
                        del session["message_ids"]

                # Convert to list and sort by last activity
                session_list = list(sessions.values())

                # Sort sessions by last_time (most recent first)
                session_list.sort(key=lambda x: x.get("last_time", ""), reverse=True)

                # Sort messages within each session by timestamp (chronological order)
                for session in session_list:
                    session["messages"].sort(key=lambda m: m.get("timestamp", ""))

                logger.info(
                    f"✅ Retrieved {len(session_list)} sessions with {processed_messages} total messages for {user_id} (skipped {skipped_duplicates} duplicates)"
                )
                return {
                    "sessions": session_list,
                    "total": len(session_list),
                    "processed_messages": processed_messages,
                    "skipped_duplicates": skipped_duplicates,
                }

            except Exception as e:
                logger.error("❌ Safe chat history retrieval failed: %s", e)
                return {"sessions": [], "total": 0, "error": str(e)}

    async def get_fresh_chat_history(
        self, user_id: str, limit: int = 5000
    ) -> Dict[str, Any]:
        """
        Get fresh chat history with aggressive deduplication for fixing stale UI data.

        This method addresses the specific issue of repeated/stale chat history entries
        by implementing strict deduplication and fresh database queries.
        """
        logger.info("🔄 Getting fresh chat history for %s (limit: %s)", user_id, limit)

        async with self._write_semaphore:
            try:
                # Force a fresh query with no caching
                await asyncio.sleep(0.1)

                # Query last 30 days to get comprehensive session data
                from datetime import datetime, timedelta

                cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()

                results = self.vector_db.conversations.get(
                    where={
                        "$and": [
                            {"user_id": {"$eq": user_id}},
                            {"timestamp": {"$gte": cutoff_date}},
                        ]
                    },
                    include=["documents", "metadatas", "ids"],
                )

                if not results or not results.get("ids"):
                    return {"sessions": [], "total": 0, "fresh": True}

                # Strict deduplication and session mapping
                session_map = {}
                message_fingerprints = set()

                for i, _doc_id in enumerate(results["ids"]):
                    try:
                        doc = (
                            results["documents"][i]
                            if i < len(results["documents"])
                            else ""
                        )
                        metadata = (
                            results["metadatas"][i]
                            if i < len(results["metadatas"])
                            else {}
                        )

                        session_id = metadata.get("session_id", "unknown")
                        sender = metadata.get("sender", "unknown")
                        timestamp = metadata.get("timestamp", "")

                        # Skip invalid entries
                        if not doc or not timestamp or sender not in ["user", "aura"]:
                            continue

                        # Global deduplication fingerprint
                        message_fingerprint = (
                            f"{session_id}:{sender}:{doc[:50]}:{timestamp}"
                        )
                        if message_fingerprint in message_fingerprints:
                            continue
                        message_fingerprints.add(message_fingerprint)

                        # Initialize session
                        if session_id not in session_map:
                            session_map[session_id] = {
                                "session_id": session_id,
                                "messages": [],
                                "last_timestamp": timestamp,
                                "message_count": 0,
                            }

                        # Add message
                        session_map[session_id]["messages"].append(
                            {
                                "content": doc.strip(),
                                "sender": sender,
                                "timestamp": timestamp,
                            }
                        )
                        session_map[session_id]["message_count"] += 1

                        if timestamp > session_map[session_id]["last_timestamp"]:
                            session_map[session_id]["last_timestamp"] = timestamp

                    except Exception as item_error:
                        logger.error("❌ Error processing item %s: %s", i, item_error)
                        continue

                # Convert and sort sessions
                fresh_sessions = []
                for session_data in session_map.values():
                    if session_data["message_count"] >= 1:
                        session_data["messages"].sort(
                            key=lambda m: m.get("timestamp", "")
                        )

                        # Get last message preview
                        last_message = ""
                        for msg in reversed(session_data["messages"]):
                            if msg.get("content"):
                                content = msg["content"]
                                last_message = (
                                    content[:10000] + "..."
                                    if len(content) > 10000
                                    else content
                                )
                                break

                        fresh_sessions.append(
                            {
                                "session_id": session_data["session_id"],
                                "timestamp": session_data["last_timestamp"],
                                "message_count": session_data["message_count"],
                                "last_message": last_message,
                            }
                        )

                fresh_sessions.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
                if len(fresh_sessions) > limit:
                    fresh_sessions = fresh_sessions[:limit]

                logger.info(
                    f"✅ Fresh chat history: {len(fresh_sessions)} distinct sessions for {user_id}"
                )
                return {
                    "sessions": fresh_sessions,
                    "total": len(fresh_sessions),
                    "fresh": True,
                }

            except Exception as e:
                logger.error("❌ Fresh chat history failed: %s", e)
                return {"sessions": [], "total": 0, "error": str(e)}

    async def safe_get_session_messages(
        self, user_id: str, session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Thread-safe retrieval of messages for a specific session with enhanced error handling.

        Uses the same semaphore to prevent concurrent access conflicts during
        session message retrieval operations. Provides proper error recovery
        and ChromaDB protection.

        Args:
            user_id: The user ID to filter messages
            session_id: The session ID to filter messages

        Returns:
            List of message dictionaries sorted by timestamp
        """
        async with self._write_semaphore:
            for attempt in range(self.max_retries):
                try:
                    # Allow brief settling time
                    await asyncio.sleep(0.05)

                    # Get session messages from vector DB with better error handling
                    try:
                        results = self.vector_db.conversations.get(
                            where={
                                "$and": [
                                    {"user_id": {"$eq": user_id}},
                                    {"session_id": {"$eq": session_id}},
                                ]
                            },
                            include=["documents", "metadatas"],
                        )
                    except Exception as db_error:
                        logger.error(
                            f"❌ Database query failed for session messages: {db_error}"
                        )

                        # Handle ChromaDB-specific errors
                        if self._is_chromadb_compaction_error(db_error):
                            recovery_attempted = await self._handle_chromadb_error(
                                db_error,
                                f"get_session_messages (attempt {attempt + 1})",
                            )

                            if recovery_attempted and attempt < self.max_retries - 1:
                                logger.info(
                                    f"🔄 Retrying session message retrieval after ChromaDB recovery (attempt {attempt + 2})"
                                )
                                continue

                        # If this is the last attempt or not a ChromaDB error, raise
                        if attempt == self.max_retries - 1:
                            raise db_error
                        continue

                    if not results or not results.get("ids"):
                        logger.info(
                            f"📭 No messages found for session {session_id} for user {user_id}"
                        )
                        return []

                    messages = []
                    ids_list = results["ids"]
                    documents_list = results.get("documents", [])
                    metadatas_list = results.get("metadatas", [])

                    for i in range(len(ids_list)):
                        try:
                            doc = documents_list[i] if i < len(documents_list) else None
                            meta = metadatas_list[i] if i < len(metadatas_list) else {}

                            if not doc:
                                logger.warning(
                                    f"⚠️ Skipping message with missing document at index {i}"
                                )
                                continue

                            message_item = {
                                "id": ids_list[i],
                                "message": doc,  # Corresponds to ConversationMemory.message
                                **meta,  # Spreads all metadata like sender, timestamp, etc.
                            }

                            # Attempt to parse complex fields if they are stored as JSON strings
                            for key in ["emotional_state", "cognitive_state"]:
                                if key in message_item and isinstance(
                                    message_item[key], str
                                ):
                                    try:
                                        message_item[key] = json.loads(
                                            message_item[key]
                                        )
                                    except json.JSONDecodeError:
                                        logger.warning(
                                            f"Failed to parse JSON for {key} in message {message_item['id']}"
                                        )

                            messages.append(message_item)

                        except Exception as message_error:
                            logger.error(
                                f"❌ Error processing message {i} in session {session_id}: {message_error}"
                            )
                            continue

                    # Sort messages by timestamp to ensure proper order
                    messages.sort(key=lambda x: x.get("timestamp", ""))

                    # Reset error count on success
                    if self._chromadb_error_count > 0:
                        logger.info(
                            f"✅ ChromaDB session message retrieval recovered after {self._chromadb_error_count} errors"
                        )
                        self._chromadb_error_count = 0

                    logger.info(
                        f"✅ Retrieved {len(messages)} messages for session {session_id} for user {user_id}"
                    )
                    return messages

                except Exception as e:
                    logger.error(
                        f"❌ Safe session message retrieval attempt {attempt + 1} failed: {e}"
                    )

                    # Handle ChromaDB-specific errors
                    if self._is_chromadb_compaction_error(e):
                        recovery_attempted = await self._handle_chromadb_error(
                            e, f"get_session_messages (attempt {attempt + 1})"
                        )

                        if recovery_attempted and attempt < self.max_retries - 1:
                            logger.info(
                                f"🔄 Retrying session message retrieval after ChromaDB recovery (attempt {attempt + 2})"
                            )
                            continue

                    # If this is the last attempt or not a ChromaDB error, give up
                    if attempt == self.max_retries - 1:
                        logger.error(
                            f"❌ All session message retrieval attempts failed. Last error: {e}"
                        )
                        return []

            return []

    async def batch_persist_exchanges(
        self, exchanges: List[ConversationExchange], batch_delay: float = 0.5
    ) -> Dict[str, Any]:
        """
        Persists multiple conversation exchanges with proper spacing.

        This method is useful for bulk operations like importing conversation
        history or processing queued messages.

        Args:
            exchanges: List of conversation exchanges to persist
            batch_delay: Delay between exchanges to prevent overload

        Returns:
            Summary of batch operation results
        """
        results = {
            "total_exchanges": len(exchanges),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "duration_ms": 0,
        }

        start_time = datetime.now()

        for i, exchange in enumerate(exchanges):
            try:
                exchange_result = await self.persist_conversation_exchange(exchange)

                if exchange_result["success"]:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].extend(exchange_result["errors"])

                # Delay between exchanges (except for the last one)
                if i < len(exchanges) - 1:
                    await asyncio.sleep(batch_delay)

            except Exception as e:
                logger.error("Failed to persist exchange %s/%s: %s", i+1, len(exchanges), e)
                results["failed"] += 1
                results["errors"].append(f"exchange_{i}: {e}")

        results["duration_ms"] = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            f"Batch persistence completed: "
            f"{results['successful']}/{results['total_exchanges']} successful "
            f"in {results['duration_ms']:.1f}ms"
        )

        return results

    async def _perform_protected_operation(
        self, operation_name: str, operation_func: Callable, *args, **kwargs
    ):
        """
        Perform a database operation with protection service coordination.

        Args:
            operation_name: Name of the operation for logging
            operation_func: The function to execute
            *args, **kwargs: Arguments to pass to the operation function

        Returns:
            Result of the operation function
        """
        try:
            # Use database protection service for risky operations
            protection_service = get_protection_service()

            with protection_service.protected_operation(operation_name):
                return await operation_func(*args, **kwargs)

        except Exception as e:
            logger.error("❌ Protected operation '%s' failed: %s", operation_name, e)
            raise


class PersistenceHealthCheck:
    """
    Monitors the health of the persistence layer.

    This provides early warning of issues like:
    - ChromaDB compaction problems
    - Slow storage operations
    - High error rates
    - Failed operation accumulation
    """

    def __init__(self, persistence_service: ConversationPersistenceService):
        self.service = persistence_service
        self.health_thresholds = {
            "max_average_store_time_ms": 500,
            "max_error_rate": 0.05,  # 5% error rate
            "min_success_rate": 0.95,
            "max_failed_operations_queued": 10,
            "max_hours_since_last_cleanup": 2400000,
        }

    async def check_health(self) -> Dict[str, Any]:
        """
        Performs comprehensive health check of persistence layer.

        Returns:
            Health status with specific issues identified
        """
        metrics = await self.service.get_persistence_metrics()

        health_status = {
            "healthy": True,
            "issues": [],
            "recommendations": [],
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
        }

        # Check average store time
        if (
            metrics["average_store_time"]
            > self.health_thresholds["max_average_store_time_ms"]
        ):
            health_status["healthy"] = False
            health_status["issues"].append(
                f"Slow storage operations: {metrics['average_store_time']:.1f}ms average"
            )
            health_status["recommendations"].append(
                "Consider increasing compaction_delay or investigating ChromaDB performance"
            )

        # Check error rate
        total_attempts = metrics["total_exchanges_stored"] + metrics["failed_stores"]
        if total_attempts > 0:
            error_rate = metrics["failed_stores"] / total_attempts
            if error_rate > self.health_thresholds["max_error_rate"]:
                health_status["healthy"] = False
                health_status["issues"].append(f"High error rate: {error_rate:.1%}")
                health_status["recommendations"].append(
                    "Review error logs and consider system maintenance"
                )

        # Check failed operations queue
        if (
            metrics["failed_operations_queued"]
            > self.health_thresholds["max_failed_operations_queued"]
        ):
            health_status["healthy"] = False
            health_status["issues"].append(
                f"Too many failed operations queued: {metrics['failed_operations_queued']}"
            )
            health_status["recommendations"].append(
                "Run retry_failed_operations() to clear queue"
            )

        # Check for recent errors
        if metrics["last_error"]:
            health_status["issues"].append(f"Recent error: {metrics['last_error']}")

        # Add performance recommendations
        if (
            metrics["total_exchanges_stored"] > 1000
            and metrics["cleanups_performed"] == 0
        ):
            health_status["recommendations"].append(
                "Consider running cleanup_old_conversations() for better performance"
            )

        return health_status
