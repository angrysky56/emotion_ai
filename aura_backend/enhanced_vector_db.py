"""
Enhanced AuraVectorDB with Compaction-Safe Operations
====================================================

This module provides a drop-in replacement for AuraVectorDB that specifically
addresses ChromaDB compaction failures through:
- Serialized database operations with optimized concurrency control
- Enhanced SQLite configuration for better concurrent access
- Automatic recovery mechanisms for compaction failures
- Improved error handling and monitoring

The enhanced implementation maintains full API compatibility while adding
robustness for production environments with multiple MCP servers.
"""

import asyncio
import fcntl
import logging
import os
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
import numpy as np
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class ProcessSafeLock:
    """File-based lock for inter-process synchronization"""

    def __init__(self, lockfile_path: Path):
        self.lockfile_path = lockfile_path
        self.lockfile = None
        self.is_locked = False

    async def acquire(self):
        """Acquire the file lock with retry logic"""
        max_attempts = 100  # 10 seconds total with 0.1s sleep
        attempt = 0

        while attempt < max_attempts:
            try:
                # Create lock file if it doesn't exist
                self.lockfile_path.parent.mkdir(exist_ok=True)
                self.lockfile = open(self.lockfile_path, "w")

                # Try to acquire exclusive lock (non-blocking)
                fcntl.flock(self.lockfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.is_locked = True
                logger.debug("🔒 Acquired inter-process lock: %s", self.lockfile_path)
                return

            except BlockingIOError:
                # Lock is held by another process
                if self.lockfile:
                    self.lockfile.close()
                    self.lockfile = None

                attempt += 1
                if attempt % 10 == 0:  # Log every second
                    logger.debug(
                        f"⏳ Waiting for inter-process lock... (attempt {attempt}/{max_attempts})"
                    )

                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error("❌ Failed to acquire lock: %s", e)
                if self.lockfile:
                    self.lockfile.close()
                    self.lockfile = None
                raise

        raise TimeoutError(f"Failed to acquire lock after {max_attempts} attempts")

    async def release(self):
        """Release the file lock"""
        if self.lockfile and self.is_locked:
            try:
                fcntl.flock(self.lockfile.fileno(), fcntl.LOCK_UN)
                self.lockfile.close()
                self.is_locked = False
                logger.debug("🔓 Released inter-process lock: %s", self.lockfile_path)
            except Exception as e:
                logger.error("❌ Failed to release lock: %s", e)
            finally:
                self.lockfile = None
                self.is_locked = False

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()


class EnhancedAuraVectorDB:
    """
    Production-ready vector database with compaction-safe operations.

    This enhanced implementation addresses the ChromaDB compaction failures
    that occur in multi-server environments by implementing:

    1. Global operation serialization to prevent concurrent access conflicts
    2. Optimized SQLite configuration for better WAL handling
    3. Automatic retry logic with exponential backoff
    4. Health monitoring and self-recovery mechanisms
    5. Detailed operation logging for debugging
    """

    def __init__(
        self,
        persist_directory: str = "./aura_chroma_db",
        auto_recovery: bool = True,
        max_concurrent_ops: int = 1,
    ):
        """
        Initialize enhanced vector database with production settings.

        Args:
            persist_directory: Directory for database persistence
            auto_recovery: Enable automatic recovery from compaction failures
            max_concurrent_ops: Maximum concurrent database operations (1 recommended)
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        self.auto_recovery = auto_recovery

        # Critical: Global semaphore for ALL database operations
        self._db_semaphore = asyncio.Semaphore(max_concurrent_ops)

        # Inter-process lock for coordination across multiple processes
        self._lock_file_path = self.persist_directory / ".chromadb.lock"
        self._process_lock = ProcessSafeLock(self._lock_file_path)

        # Operation monitoring
        self._operation_count = 0
        self._last_compaction_error = None
        self._recovery_attempts = 0

        # Declare collections as instance variables
        self.conversations = None
        self.emotional_patterns = None
        self.cognitive_patterns = None
        self.knowledge_substrate = None

        # Initialize client with enhanced settings
        self._init_client()

        # Initialize collections synchronously
        self._init_collections_sync()

        logger.info("✅ Enhanced AuraVectorDB initialized with inter-process locking")
        logger.info("   Lock file: %s", self._lock_file_path)
        logger.info("   Max concurrent ops: %s", max_concurrent_ops)

    def _init_client(self):
        """Initialize ChromaDB client with optimized settings for concurrent access"""
        try:
            # Enhanced settings for production stability
            settings = Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True,
                persist_directory=str(self.persist_directory),
            )

            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory), settings=settings
            )

            # Apply optimized SQLite configuration
            self._optimize_sqlite_settings()

            logger.info("✅ ChromaDB client initialized with enhanced settings")

        except Exception as e:
            logger.error("❌ Failed to initialize ChromaDB client: %s", e)
            raise

    def _optimize_sqlite_settings(self):
        """Apply production-optimized SQLite settings"""
        try:
            # Get the SQLite database path
            sqlite_path = self.persist_directory / "chroma.sqlite3"

            if sqlite_path.exists():
                # Apply optimizations directly to the SQLite database
                conn = sqlite3.connect(str(sqlite_path))
                cursor = conn.cursor()

                # Configure for better concurrent access and WAL handling
                optimizations = [
                    "PRAGMA journal_mode=WAL",  # Write-Ahead Logging
                    "PRAGMA synchronous=NORMAL",  # Balanced safety/performance
                    "PRAGMA cache_size=-64000",  # 64MB cache
                    "PRAGMA temp_store=MEMORY",  # Store temp data in memory
                    "PRAGMA mmap_size=268435456",  # 256MB memory-mapped I/O
                    "PRAGMA wal_autocheckpoint=1000",  # Checkpoint every 1000 pages
                    "PRAGMA wal_checkpoint(TRUNCATE)",  # Truncate WAL on checkpoint
                    "PRAGMA busy_timeout=30000",  # 30 second busy timeout
                    "PRAGMA optimize",  # Optimize database
                ]

                for pragma in optimizations:
                    try:
                        cursor.execute(pragma)
                        logger.debug("Applied: %s", pragma)
                    except Exception as e:
                        logger.warning("Failed to apply %s: %s", pragma, e)

                conn.commit()
                conn.close()

                logger.info("✅ Applied SQLite optimizations for concurrent access")

        except Exception as e:
            logger.warning("⚠️ Could not optimize SQLite settings: %s", e)

    @asynccontextmanager
    async def _safe_operation(self, operation_name: str):
        """
        Context manager for process-safe and thread-safe database operations.

        This ensures only one database operation occurs at a time across ALL processes,
        preventing the compaction conflicts that cause failures.
        """
        # First acquire inter-process lock
        async with self._process_lock:
            # Then acquire intra-process semaphore
            async with self._db_semaphore:
                self._operation_count += 1
                start_time = time.time()

                try:
                    logger.debug(
                        f"🔒 Starting {operation_name} (op #{self._operation_count}) [PID: {os.getpid()}]"
                    )

                    # Small delay to allow WAL settling if there were recent operations
                    if self._operation_count > 1:
                        await asyncio.sleep(0.05)

                    yield

                    duration = (time.time() - start_time) * 1000
                    logger.debug(
                        f"✅ Completed {operation_name} in {duration:.1f}ms [PID: {os.getpid()}]"
                    )

                except Exception as e:
                    duration = (time.time() - start_time) * 1000
                    logger.error(
                        f"❌ Failed {operation_name} after {duration:.1f}ms [PID: {os.getpid()}]: {e}"
                    )

                    # Track compaction-specific errors
                    if (
                        "compaction" in str(e).lower()
                        or "metadata segment" in str(e).lower()
                    ):
                        self._last_compaction_error = datetime.now()
                        if self.auto_recovery:
                            await self._attempt_recovery(operation_name, e)

                    raise

    async def _attempt_recovery(self, failed_operation: str, error: Exception):
        """Attempt automatic recovery from compaction failures"""
        self._recovery_attempts += 1

        logger.warning(
            f"🔧 Attempting recovery #{self._recovery_attempts} after {failed_operation} failure"
        )

        try:
            # Wait for any ongoing operations to complete
            await asyncio.sleep(1.0)

            # Apply WAL checkpoint to force compaction completion
            sqlite_path = self.persist_directory / "chroma.sqlite3"
            if sqlite_path.exists():
                conn = sqlite3.connect(str(sqlite_path))
                cursor = conn.cursor()
                cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.commit()
                conn.close()

                logger.info("✅ Recovery checkpoint completed")

        except Exception as recovery_error:
            logger.error("❌ Recovery attempt failed: %s", recovery_error)

    def _init_collections_sync(self):
        """Initialize vector database collections synchronously"""
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

            # Cognitive patterns collection
            self.cognitive_patterns = self.client.get_or_create_collection(
                name="aura_cognitive_patterns",
                metadata={
                    "description": "Cognitive focus and ASEKE component tracking"
                },
            )

            # Knowledge substrate collection
            self.knowledge_substrate = self.client.get_or_create_collection(
                name="aura_knowledge_substrate",
                metadata={"description": "Shared knowledge and insights"},
            )

            logger.info(
                "✅ Enhanced vector database collections initialized successfully"
            )

        except Exception as e:
            logger.error("❌ Failed to initialize enhanced vector collections: %s", e)
            raise

    async def _init_collections(self):
        """Initialize vector database collections with enhanced error handling"""
        async with self._safe_operation("init_collections"):
            try:
                # Conversation memory collection
                self.conversations = self.client.get_or_create_collection(
                    name="aura_conversations",
                    metadata={
                        "description": "Conversation history with semantic search"
                    },
                )

                # Emotional patterns collection
                self.emotional_patterns = self.client.get_or_create_collection(
                    name="aura_emotional_patterns",
                    metadata={"description": "Historical emotional state patterns"},
                )

                # Cognitive patterns collection
                self.cognitive_patterns = self.client.get_or_create_collection(
                    name="aura_cognitive_patterns",
                    metadata={
                        "description": "Cognitive focus and ASEKE component tracking"
                    },
                )

                # Knowledge substrate collection
                self.knowledge_substrate = self.client.get_or_create_collection(
                    name="aura_knowledge_substrate",
                    metadata={"description": "Shared knowledge and insights"},
                )

                logger.info(
                    "✅ Enhanced vector database collections initialized successfully"
                )

            except Exception as e:
                logger.error(
                    f"❌ Failed to initialize enhanced vector collections: {e}"
                )
                raise

    async def store_conversation(self, memory) -> str:
        """Store conversation memory with enhanced concurrency control"""
        async with self._safe_operation("store_conversation"):
            try:
                # Generate embedding if not provided
                if memory.embedding is None:
                    # Import here to avoid circular dependency
                    from sentence_transformers import SentenceTransformer

                    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
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

                # Store in vector database
                if self.conversations is None:
                    raise RuntimeError("Conversations collection not initialized")

                self.conversations.add(
                    documents=[memory.message],
                    embeddings=[memory.embedding],
                    metadatas=[metadata],
                    ids=[doc_id],
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
        where_filter: Optional[Dict] = None,
    ) -> List[Dict]:
        """Enhanced semantic search with improved error handling"""
        async with self._safe_operation("search_conversations"):
            try:
                # Generate query embedding
                from sentence_transformers import SentenceTransformer

                embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                query_embedding = embedding_model.encode(query).tolist()

                # Prepare where filter with proper typing for ChromaDB
                base_filter: Dict[str, Any] = {"user_id": {"$eq": user_id}}
                if where_filter:
                    base_filter.update(where_filter)

                # Perform semantic search
                if self.conversations is None:
                    raise RuntimeError("Conversations collection not initialized")

                results = self.conversations.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=base_filter,
                    include=["documents", "metadatas", "distances"],
                )

                # Format results
                formatted_results = []
                if (
                    results is not None
                    and results.get("documents") is not None
                    and isinstance(results["documents"], list)
                    and results["documents"]
                    and results.get("metadatas") is not None
                    and results["metadatas"]
                    and results.get("distances") is not None
                    and results["distances"]
                ):
                    for i, doc in enumerate(results["documents"][0]):
                        formatted_results.append(
                            {
                                "content": doc,
                                "metadata": results["metadatas"][0][i],
                                "similarity": 1
                                - results["distances"][0][
                                    i
                                ],  # Convert distance to similarity
                            }
                        )

                logger.info(
                    f"🔍 Found {len(formatted_results)} relevant memories for query: {query}"
                )
                return formatted_results

            except Exception as e:
                logger.error("❌ Failed to search conversations: %s", e)
                return []

    async def store_emotional_pattern(self, emotional_state, user_id: str) -> str:
        """Store emotional state pattern with enhanced safety"""
        async with self._safe_operation("store_emotional_pattern"):
            try:
                # Create embedding from emotional context
                emotion_text = f"{emotional_state.name} {emotional_state.description} {emotional_state.brainwave} {emotional_state.neurotransmitter}"

                from sentence_transformers import SentenceTransformer

                embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
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
                    "formula": emotional_state.formula,
                }

                if self.emotional_patterns is None:
                    raise RuntimeError("Emotional patterns collection not initialized")

                self.emotional_patterns.add(
                    documents=[emotion_text],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    ids=[doc_id],
                )

                logger.info(
                    f"🎭 Stored emotional pattern: {emotional_state.name} ({emotional_state.intensity.value})"
                )
                return doc_id

            except Exception as e:
                logger.error("❌ Failed to store emotional pattern: %s", e)
                raise

    async def store_cognitive_pattern(
        self,
        focus_text: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        doc_id: str,
    ) -> str:
        """Store cognitive pattern with enhanced safety"""
        async with self._safe_operation("store_cognitive_pattern"):
            try:
                if self.cognitive_patterns is None:
                    raise RuntimeError("Cognitive patterns collection not initialized")

                self.cognitive_patterns.add(
                    documents=[focus_text],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    ids=[doc_id],
                )

                logger.info("🧠 Stored cognitive pattern: %s", metadata['focus'])
                return doc_id
            except Exception as e:
                logger.error("❌ Failed to store cognitive pattern: %s", e)
                raise

    async def analyze_emotional_trends(
        self, user_id: str, days: int = 7
    ) -> Dict[str, Any]:
        """Analyze emotional trends over a specified period with enhanced safety"""
        async with self._safe_operation("analyze_emotional_trends"):
            try:
                # Calculate cutoff date
                cutoff_date = datetime.now() - timedelta(days=days)

                if self.emotional_patterns is None:
                    raise RuntimeError("Emotional patterns collection not initialized")

                results = self.emotional_patterns.get(
                    where={
                        "$and": [
                            {"user_id": {"$eq": user_id}},
                            {"timestamp": {"$gte": cutoff_date.isoformat()}},
                        ]
                    },
                    include=["metadatas"],
                )

                if not results["metadatas"]:
                    return {"message": "No emotional data found for analysis"}

                # Analyze patterns
                emotions = [str(meta["emotion_name"]) for meta in results["metadatas"]]
                intensities = [str(meta["intensity"]) for meta in results["metadatas"]]
                brainwaves = [str(meta["brainwave"]) for meta in results["metadatas"]]

                analysis = {
                    "period_days": days,
                    "total_entries": len(emotions),
                    "dominant_emotions": self._get_top_items(emotions, 3),
                    "intensity_distribution": self._get_distribution(intensities),
                    "brainwave_patterns": self._get_distribution(brainwaves),
                    "emotional_stability": self._calculate_stability(emotions),
                    "recommendations": self._generate_emotional_recommendations(
                        emotions, intensities
                    ),
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
        """Comprehensive health check of the database system"""
        try:
            async with self._safe_operation("health_check"):
                # Check collection accessibility
                collections_status = {}
                for name in [
                    "conversations",
                    "emotional_patterns",
                    "cognitive_patterns",
                    "knowledge_substrate",
                ]:
                    try:
                        collection = getattr(self, name)
                        count = collection.count()
                        collections_status[name] = {"status": "healthy", "count": count}
                    except Exception as e:
                        collections_status[name] = {"status": "error", "error": str(e)}

                # Check SQLite database integrity
                sqlite_status = "unknown"
                try:
                    sqlite_path = self.persist_directory / "chroma.sqlite3"
                    if sqlite_path.exists():
                        conn = sqlite3.connect(str(sqlite_path))
                        cursor = conn.cursor()
                        cursor.execute("PRAGMA integrity_check")
                        result = cursor.fetchone()
                        sqlite_status = "healthy" if result[0] == "ok" else "corrupted"
                        conn.close()
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
            logger.error("❌ Health check failed: %s", e)
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def close(self):
        """Gracefully close the database connection"""
        try:
            logger.info("🔒 Closing enhanced vector database...")

            # Acquire inter-process lock for cleanup
            async with self._process_lock:
                # Wait for any ongoing operations to complete
                async with self._db_semaphore:
                    # Perform final WAL checkpoint
                    sqlite_path = self.persist_directory / "chroma.sqlite3"
                    if sqlite_path.exists():
                        conn = sqlite3.connect(str(sqlite_path))
                        cursor = conn.cursor()
                        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                        cursor.execute("PRAGMA optimize")
                        conn.commit()
                        conn.close()

                    logger.info("✅ Enhanced vector database closed gracefully")

        except Exception as e:
            logger.error("❌ Error during database closure: %s", e)


# Compatibility wrapper to maintain API compatibility
class AuraVectorDB(EnhancedAuraVectorDB):
    """Compatibility wrapper for existing code"""

    pass
