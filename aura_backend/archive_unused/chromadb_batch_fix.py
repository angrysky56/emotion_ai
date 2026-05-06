"""
Immediate fix for ChromaDB batch operation conflict with memvid
==============================================================

This patch ensures proper serialization of database operations to prevent
compaction conflicts between memory storage batches.
"""

import asyncio
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)

class SerializedDatabaseOperations:
    """
    Ensures database operations are properly serialized to prevent
    concurrent write conflicts during compaction.

    This addresses the architectural conflict where multiple background
    tasks attempt simultaneous batch operations on ChromaDB collections.
    """

    def __init__(self):
        self._operation_lock = asyncio.Lock()
        self._compaction_delay = 0.5  # Allow compaction to complete

    async def execute_serialized(self, operation: Callable, *args, **kwargs) -> Any:
        """
        Execute a database operation with proper serialization and
        compaction delay to prevent conflicts.
        """
        async with self._operation_lock:
            try:
                result = await operation(*args, **kwargs)
                # Allow ChromaDB compaction to complete before next operation
                await asyncio.sleep(self._compaction_delay)
                return result
            except Exception as e:
                logger.error("Serialized operation failed: %s", e)
                raise

# Global instance for the application
db_operations = SerializedDatabaseOperations()

# ============================================================================
# Patch for main.py - Replace the background task additions
# ============================================================================

async def store_memories_sequentially(
    vector_db,
    user_memory,
    aura_memory,
    aura_emotional_state_data,
    user_emotional_state,
    user_id
):
    """
    Store memories sequentially to prevent batch operation conflicts.

    This replaces the parallel background task approach with a serialized
    execution that respects ChromaDB's compaction requirements.
    """
    try:
        # Store user memory first
        await db_operations.execute_serialized(
            vector_db.store_conversation,
            user_memory
        )
        logger.info("✅ Stored user memory for %s", user_id)

        # Store Aura memory after compaction completes
        await db_operations.execute_serialized(
            vector_db.store_conversation,
            aura_memory
        )
        logger.info("✅ Stored Aura memory for %s", user_id)

        # Store emotional patterns if present
        if aura_emotional_state_data:
            await db_operations.execute_serialized(
                vector_db.store_emotional_pattern,
                aura_emotional_state_data,
                "aura"
            )

        if user_emotional_state:
            await db_operations.execute_serialized(
                vector_db.store_emotional_pattern,
                user_emotional_state,
                user_id
            )

    except Exception as e:
        logger.error("Failed to store memories: %s", e)
        # Continue processing even if storage fails

# ============================================================================
# Alternative: Batch-aware ChromaDB wrapper
# ============================================================================

class BatchAwareChromaCollection:
    """
    Wrapper that ensures proper batch handling for ChromaDB collections.
    Prevents concurrent batch operations that can cause compaction conflicts.
    """

    def __init__(self, collection, batch_delay: float = 0.5):
        self._collection = collection
        self._batch_delay = batch_delay
        self._batch_lock = asyncio.Lock()

    async def add_with_delay(self, **kwargs):
        """Add to collection with post-operation delay for compaction"""
        async with self._batch_lock:
            self._collection.add(**kwargs)
            # Allow compaction to complete
            await asyncio.sleep(self._batch_delay)

    def __getattr__(self, name):
        """Proxy all other methods to the underlying collection"""
        return getattr(self._collection, name)
