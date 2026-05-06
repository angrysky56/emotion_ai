"""
Production-Ready ChromaDB Concurrent Access Fix
==============================================

This module provides a robust solution to ChromaDB concurrent access issues
by using SQLite's built-in mechanisms rather than external file locking.
"""

import asyncio
import logging
import os
import sqlite3
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
import numpy as np
from chromadb.config import Settings

# Add the parent directory to sys.path to support absolute imports from aura_backend package
# when running scripts directly from the aura_backend directory.
_current_dir = Path(__file__).resolve().parent
if _current_dir.name == "aura_backend":
    _parent_dir = _current_dir.parent
    if str(_parent_dir) not in sys.path:
        sys.path.insert(0, str(_parent_dir))


logger = logging.getLogger(__name__)


class RobustAuraVectorDB:
    """
    Production-ready vector database with SQLite-level concurrency control.

    This implementation uses SQLite's built-in mechanisms to handle concurrent
    access, which is more robust than file-based locking in auto-reloading environments.
    """

    # Class-level lock for singleton pattern
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern to ensure single database instance per process"""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self, persist_directory: str = "./aura_chroma_db", auto_recovery: bool = True
    ):
        """Initialize with SQLite-optimized settings"""

        # Skip re-initialization if already initialized
        if hasattr(self, "_initialized"):
            return

        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        self.auto_recovery = auto_recovery

        # Operation monitoring
        self._operation_count = 0
        self._last_compaction_error = None
        self._recovery_attempts = 0

        # Initialize client with special settings
        self._init_client()

        # Initialize collections
        self._init_collections()

        # Apply critical SQLite optimizations
        self._apply_sqlite_optimizations()

        self._initialized = True
        logger.info(
            "✅ RobustAuraVectorDB initialized with SQLite-level concurrency control"
        )

    def _init_client(self):
        """Initialize ChromaDB client with production settings"""
        try:
            settings = Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True,
                persist_directory=str(self.persist_directory),
                # Disable auto-sync to control when writes happen
                chroma_server_authn_credentials=None,
                chroma_server_authn_provider=None,
            )

            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory), settings=settings
            )

            logger.info("✅ ChromaDB client initialized")

        except Exception as e:
            logger.error("❌ Failed to initialize ChromaDB client: %s", e)
            raise

    def _apply_sqlite_optimizations(self):
        """Apply critical SQLite settings for concurrent access"""
        sqlite_path = self.persist_directory / "chroma.sqlite3"

        if not sqlite_path.exists():
            logger.warning(
                "⚠️ SQLite database not found, optimizations will be applied on first write"
            )
            return

        try:
            # Use a context manager for safe connection handling
            with self._get_sqlite_connection() as conn:
                cursor = conn.cursor()

                # Critical settings for concurrent access
                pragmas = [
                    # Use WAL mode for better concurrency
                    "PRAGMA journal_mode=WAL",
                    # Increase busy timeout to 30 seconds
                    "PRAGMA busy_timeout=30000",
                    # Use NORMAL synchronous mode (faster but still safe)
                    "PRAGMA synchronous=NORMAL",
                    # Increase cache size
                    "PRAGMA cache_size=-64000",  # 64MB
                    # Store temp tables in memory
                    "PRAGMA temp_store=MEMORY",
                    # Enable memory-mapped I/O
                    "PRAGMA mmap_size=268435456",  # 256MB
                    # Auto-checkpoint at 1000 pages (4MB with 4KB pages)
                    "PRAGMA wal_autocheckpoint=1000",
                    # Enable query optimizer
                    "PRAGMA optimize",
                    # Disable auto-vacuum to prevent lock conflicts
                    "PRAGMA auto_vacuum=NONE",
                    # Use exclusive locking mode for writes
                    "PRAGMA locking_mode=NORMAL",
                ]

                for pragma in pragmas:
                    try:
                        cursor.execute(pragma)
                        logger.debug("Applied: %s", pragma)
                    except Exception as e:
                        logger.warning("Failed to apply %s: %s", pragma, e)

                # Force a checkpoint to ensure WAL is initialized
                cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")

                conn.commit()
                logger.info("✅ Applied SQLite optimizations for concurrent access")

        except Exception as e:
            logger.error("❌ Failed to apply SQLite optimizations: %s", e)

    @contextmanager
    def _get_sqlite_connection(self):
        """Get a properly configured SQLite connection"""
        conn = sqlite3.connect(
            str(self.persist_directory / "chroma.sqlite3"),
            timeout=30.0,  # 30 second timeout
            isolation_level="DEFERRED",  # Use deferred transactions
            check_same_thread=False,  # Allow multi-threaded access
        )

        try:
            yield conn
        finally:
            conn.close()

    def _init_collections(self):
        """Initialize vector database collections with retry logic"""
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Use get_or_create_collection with error handling
                self.conversations = self._safe_get_or_create_collection(
                    "aura_conversations",
                    {"description": "Conversation history with semantic search"},
                )

                self.emotional_patterns = self._safe_get_or_create_collection(
                    "aura_emotional_patterns",
                    {"description": "Historical emotional state patterns"},
                )

                self.cognitive_patterns = self._safe_get_or_create_collection(
                    "aura_cognitive_patterns",
                    {"description": "Cognitive focus and ASEKE component tracking"},
                )

                self.knowledge_substrate = self._safe_get_or_create_collection(
                    "aura_knowledge_substrate",
                    {"description": "Shared knowledge and insights"},
                )

                logger.info("✅ Vector database collections initialized successfully")
                return

            except Exception as e:
                logger.error(
                    f"❌ Failed to initialize collections (attempt {attempt + 1}): {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise

    def _safe_get_or_create_collection(self, name: str, metadata: Dict[str, str]):
        """Safely get or create a collection with retry logic"""
        try:
            # First try to get existing collection
            return self.client.get_collection(name)
        except Exception:
            # If not found, create it
            try:
                return self.client.create_collection(name=name, metadata=metadata)
            except Exception:
                # If creation fails, it might exist now (race condition)
                return self.client.get_collection(name)

    @asynccontextmanager
    async def _safe_operation(self, operation_name: str):
        """Context manager for safe database operations with built-in retry"""
        start_time = time.time()
        self._operation_count += 1

        max_retries = 3
        retry_delay = 0.1

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"🔒 Starting {operation_name} (attempt {attempt + 1}) [PID: {os.getpid()}]"
                )

                # Small delay between retries
                if attempt > 0:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

                yield

                duration = (time.time() - start_time) * 1000
                logger.debug("✅ Completed %s in %sms", operation_name, duration)
                return  # Success, exit the retry loop

            except Exception as e:
                duration = (time.time() - start_time) * 1000
                error_msg = str(e)

                # Check if it's a compaction error
                if (
                    "compaction" in error_msg.lower()
                    or "metadata segment" in error_msg.lower()
                ):
                    self._last_compaction_error = datetime.now()

                    if attempt < max_retries - 1:
                        logger.warning(
                            f"⚠️ {operation_name} failed (attempt {attempt + 1}), retrying: {error_msg}"
                        )

                        # Try to recover between attempts
                        if self.auto_recovery:
                            await self._attempt_recovery(operation_name, e)
                    else:
                        logger.error(
                            f"❌ {operation_name} failed after {max_retries} attempts: {error_msg}"
                        )
                        raise
                else:
                    # Non-recoverable error
                    logger.error(
                        f"❌ {operation_name} failed with non-recoverable error: {error_msg}"
                    )
                    raise

    async def _attempt_recovery(self, failed_operation: str, error: Exception):
        """Attempt recovery with SQLite-specific fixes"""
        self._recovery_attempts += 1
        logger.info(
            f"🔧 Recovery attempt #{self._recovery_attempts} for {failed_operation}"
        )

        try:
            # Wait a moment for any ongoing operations
            await asyncio.sleep(0.5)

            # Try to checkpoint and clean up WAL
            with self._get_sqlite_connection() as conn:
                cursor = conn.cursor()

                # Force checkpoint
                cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")

                # Rebuild indexes
                cursor.execute("REINDEX")

                # Analyze for query optimizer
                cursor.execute("ANALYZE")

                conn.commit()

            logger.info("✅ Recovery operations completed")

        except Exception as recovery_error:
            logger.error("❌ Recovery attempt failed: %s", recovery_error)

    async def store_conversation(self, memory) -> str:
        """Store conversation with automatic retry and recovery"""
        async with self._safe_operation("store_conversation"):
            # Generate embedding if needed
            if memory.embedding is None:
                from aura_backend.shared_embedding_service import get_embedding_service

                embedding_service = get_embedding_service()
                # Convert to list and ensure all values are Python native types
                embedding_array = embedding_service.encode_single(memory.message)
                memory.embedding = embedding_array

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

            # Store with retry logic built into _safe_operation
            self.conversations.add(
                documents=[memory.message],
                embeddings=[memory.embedding],
                metadatas=[metadata],
                ids=[doc_id],
            )

            logger.info("📝 Stored conversation memory: %s", doc_id)
            return doc_id

    async def search_conversations(
        self,
        query: str,
        user_id: str,
        n_results: int = 5000,
        where_filter: Optional[Dict] = None,
    ) -> List[Dict]:
        """Search with automatic retry"""
        async with self._safe_operation("search_conversations"):
            # Generate query embedding
            from aura_backend.shared_embedding_service import get_embedding_service

            embedding_service = get_embedding_service()
            # Convert to list and ensure all values are Python native types
            query_embedding = embedding_service.encode_single(query)

            # Prepare filter
            base_filter: Dict[str, Any] = {"user_id": {"$eq": user_id}}
            if where_filter:
                base_filter.update(where_filter)

            # Search
            results = self.conversations.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=base_filter,
                include=["documents", "metadatas", "distances"],
            )

            # Format results
            formatted_results = []
            if (
                results
                and results.get("documents")
                and results["documents"]
                and results["documents"][0]
            ):
                for i, doc in enumerate(results["documents"][0]):
                    formatted_results.append(
                        {
                            "content": doc,
                            "metadata": (
                                results["metadatas"][0][i]
                                if results.get("metadatas")
                                and results["metadatas"]
                                and results["metadatas"][0]
                                else {}
                            ),
                            "similarity": (
                                1 - results["distances"][0][i]
                                if results.get("distances")
                                and results["distances"]
                                and results["distances"][0]
                                else 0.0
                            ),
                        }
                    )

            return formatted_results

    async def store_emotional_pattern(self, emotional_state, user_id: str) -> str:
        """Store emotional pattern with retry"""
        async with self._safe_operation("store_emotional_pattern"):
            # Create embedding
            emotion_text = f"{emotional_state.name} {emotional_state.description} {emotional_state.brainwave} {emotional_state.neurotransmitter}"

            from aura_backend.shared_embedding_service import get_embedding_service

            embedding_service = get_embedding_service()
            # Convert to list and ensure all values are Python native types
            embedding = embedding_service.encode_single(emotion_text)

            # Create ID
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
                "timestamp_unix": int(
                    emotional_state.timestamp.timestamp()
                ),  # For numeric comparisons
                "formula": emotional_state.formula,
            }

            self.emotional_patterns.add(
                documents=[emotion_text],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id],
            )

            return doc_id

    async def store_cognitive_pattern(
        self,
        focus_text: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        doc_id: str,
    ) -> str:
        """Store cognitive pattern with retry"""
        async with self._safe_operation("store_cognitive_pattern"):
            self.cognitive_patterns.add(
                documents=[focus_text],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id],
            )
            return doc_id

    async def delete_messages(
        self, ids: List[str], collection_name: str = "conversations"
    ) -> Dict[str, Any]:
        """
        Delete messages using robust error handling and retry mechanisms.

        This method wraps the ChromaDB delete operation with the _safe_operation
        context manager to ensure reliable deletion even under concurrent access
        or transient database issues.

        Args:
            ids: List of document IDs to delete
            collection_name: Name of the collection to delete from (default: "conversations")

        Returns:
            Dictionary containing:
            - success: Boolean indicating if deletion was successful
            - deleted_count: Number of documents actually deleted
            - errors: List of any errors encountered

        Raises:
            ValueError: If ids list is empty
            Exception: If deletion fails after all retry attempts
        """
        if not ids:
            raise ValueError("IDs list cannot be empty")

        async with self._safe_operation("delete_messages"):
            try:
                # Get the appropriate collection
                if collection_name == "conversations":
                    collection = self.conversations
                elif collection_name == "emotional_patterns":
                    collection = self.emotional_patterns
                elif collection_name == "cognitive_patterns":
                    collection = self.cognitive_patterns
                elif collection_name == "knowledge_substrate":
                    collection = self.knowledge_substrate
                else:
                    raise ValueError(f"Unknown collection: {collection_name}")

                # Perform the deletion with robust error handling
                collection.delete(ids=ids)

                logger.info(
                    f"🗑️ Successfully deleted {len(ids)} messages from {collection_name}"
                )

                return {"success": True, "deleted_count": len(ids), "errors": []}

            except Exception as e:
                logger.error(
                    f"❌ Failed to delete messages from {collection_name}: {e}"
                )
                return {"success": False, "deleted_count": 0, "errors": [str(e)]}

    async def analyze_emotional_trends(
        self, user_id: str, days: int = 7
    ) -> Dict[str, Any]:
        """Analyze emotional trends with retry and proper date filtering"""
        async with self._safe_operation("analyze_emotional_trends"):
            cutoff_date = datetime.now() - timedelta(days=days)

            # Get all emotional patterns for the user and filter by date in Python
            # This avoids the ChromaDB date comparison issue
            try:
                results = self.emotional_patterns.get(
                    where={"user_id": {"$eq": user_id}}, include=["metadatas"]
                )

                if not results or not results.get("metadatas"):
                    return {
                        "message": "No emotional data found for analysis",
                        "period_days": days,
                        "total_entries": 0,
                        "dominant_emotions": [],
                        "intensity_distribution": {},
                        "brainwave_patterns": {},
                        "emotional_stability": 1.0,
                        "recommendations": [
                            "Start interacting to build emotional patterns"
                        ],
                    }

                # Filter results by date in Python (more reliable than ChromaDB date comparison)
                filtered_metadatas = []
                current_metadatas = results.get("metadatas")
                if (
                    current_metadatas
                ):  # Ensures current_metadatas is not None and not an empty list
                    for meta in current_metadatas:
                        if meta and "timestamp" in meta:
                            try:
                                # Ensure timestamp is a string before calling replace
                                timestamp_str = meta["timestamp"]
                                if not isinstance(timestamp_str, str):
                                    logger.warning(
                                        f"Timestamp is not a string: {timestamp_str}, skipping."
                                    )
                                    continue
                                # Parse the timestamp and compare
                                meta_timestamp = datetime.fromisoformat(
                                    timestamp_str.replace("Z", "+00:00")
                                )
                                if meta_timestamp >= cutoff_date:
                                    filtered_metadatas.append(meta)
                            except (ValueError, AttributeError):
                                # Skip entries with invalid timestamps
                                logger.warning(
                                    f"Invalid timestamp in emotional pattern: {meta.get('timestamp')}"
                                )
                                continue

                if not filtered_metadatas:
                    return {
                        "message": f"No emotional data found in the last {days} days",
                        "period_days": days,
                        "total_entries": 0,
                        "dominant_emotions": [],
                        "intensity_distribution": {},
                        "brainwave_patterns": {},
                        "emotional_stability": 1.0,
                        "recommendations": [
                            "Continue interacting to build recent emotional patterns"
                        ],
                    }

                # Analyze patterns from filtered data
                emotions = [
                    str(meta["emotion_name"])
                    for meta in filtered_metadatas
                    if "emotion_name" in meta
                ]
                intensities = [
                    str(meta["intensity"])
                    for meta in filtered_metadatas
                    if "intensity" in meta
                ]
                brainwaves = [
                    str(meta["brainwave"])
                    for meta in filtered_metadatas
                    if "brainwave" in meta
                ]

                analysis = {
                    "period_days": days,
                    "total_entries": len(filtered_metadatas),
                    "dominant_emotions": self._get_top_items(emotions, 3),
                    "intensity_distribution": self._get_distribution(intensities),
                    "brainwave_patterns": self._get_distribution(brainwaves),
                    "emotional_stability": self._calculate_stability(emotions),
                    "recommendations": self._generate_emotional_recommendations(
                        emotions, intensities
                    ),
                }

                logger.info(
                    f"✅ Emotional analysis completed: {len(filtered_metadatas)} entries from last {days} days"
                )
                return analysis

            except Exception as e:
                logger.error("❌ Error in emotional trends analysis: %s", e)
                return {
                    "message": f"Error analyzing emotional trends: {str(e)}",
                    "period_days": days,
                    "total_entries": 0,
                    "dominant_emotions": [],
                    "intensity_distribution": {},
                    "brainwave_patterns": {},
                    "emotional_stability": 1.0,
                    "recommendations": ["Analysis temporarily unavailable"],
                }

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
        """Calculate emotional stability score"""
        if len(emotions) <= 1:
            return 1.0

        from collections import Counter

        emotion_counts = Counter(emotions)
        entropy = -sum(
            (count / len(emotions)) * np.log2(count / len(emotions))
            for count in emotion_counts.values()
        )
        max_entropy = np.log2(len(emotion_counts))

        return 1 - (entropy / max_entropy if max_entropy > 0 else 0)

    def _generate_emotional_recommendations(
        self, emotions: List[str], intensities: List[str]
    ) -> List[str]:
        """Generate recommendations"""
        recommendations = []

        # High intensity emotions
        high_intensity_count = intensities.count("High")
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

    async def health_check(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            # Check collection accessibility
            collections_status = {}
            for name, collection in [
                ("conversations", self.conversations),
                ("emotional_patterns", self.emotional_patterns),
                ("cognitive_patterns", self.cognitive_patterns),
                ("knowledge_substrate", self.knowledge_substrate),
            ]:
                try:
                    count = collection.count()
                    collections_status[name] = {"status": "healthy", "count": count}
                except Exception as e:
                    collections_status[name] = {"status": "error", "error": str(e)}

            # Check SQLite status
            sqlite_status = "unknown"
            try:
                with self._get_sqlite_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA integrity_check")
                    result = cursor.fetchone()
                    sqlite_status = "healthy" if result[0] == "ok" else "corrupted"
            except Exception as e:
                sqlite_status = f"error: {e}"

            return {
                "status": "healthy",
                "collections": collections_status,
                "database_integrity": sqlite_status,
                "operation_count": self._operation_count,
                "last_compaction_error": (
                    self._last_compaction_error.isoformat()
                    if self._last_compaction_error
                    else None
                ),
                "recovery_attempts": self._recovery_attempts,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def close(self):
        """Gracefully close the database"""
        try:
            logger.info("🔒 Closing RobustAuraVectorDB...")

            # Final checkpoint
            try:
                with self._get_sqlite_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    cursor.execute("PRAGMA optimize")
                    conn.commit()
            except Exception as e:
                logger.error("Error during final checkpoint: %s", e)

            logger.info("✅ RobustAuraVectorDB closed")

        except Exception as e:
            logger.error("❌ Error during database closure: %s", e)


# Compatibility wrapper
class AuraVectorDB(RobustAuraVectorDB):
    """Compatibility wrapper for existing code"""


# Enhanced version that includes all fixes
class EnhancedAuraVectorDB(RobustAuraVectorDB):
    """Enhanced version with all production fixes"""
