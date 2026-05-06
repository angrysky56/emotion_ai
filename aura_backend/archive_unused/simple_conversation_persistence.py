"""
Simple Conversation Persistence Service
======================================

This service provides clean, reliable conversation storage without unnecessary complexity.
It replaces the overly complex conversation_persistence_service.py with a straightforward approach.
"""

import asyncio
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SimpleConversationExchange:
    """Simple representation of a conversation exchange"""
    user_memory: Any  # ConversationMemory
    ai_memory: Any    # ConversationMemory
    user_emotional_state: Optional[Any] = None  # EmotionalStateData
    ai_emotional_state: Optional[Any] = None    # EmotionalStateData
    ai_cognitive_state: Optional[Any] = None    # CognitiveState
    session_id: str = ""
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if not self.session_id and hasattr(self.user_memory, 'session_id') and self.user_memory.session_id:
            self.session_id = self.user_memory.session_id


class SimpleConversationPersistence:
    """
    Clean, straightforward conversation persistence without unnecessary complexity.
    
    This replaces the overly complex persistence service with a simple, reliable approach.
    """

    def __init__(self, vector_db: Any, file_system: Any):
        self.vector_db = vector_db
        self.file_system = file_system
        
        # Simple metrics tracking
        self.conversations_stored = 0
        self.storage_failures = 0
        
        logger.info("✅ Simple Conversation Persistence initialized")

    async def store_conversation_exchange(
        self,
        exchange: SimpleConversationExchange,
        update_profile: bool = True
    ) -> Dict[str, Any]:
        """
        Store a conversation exchange simply and reliably.
        
        Args:
            exchange: The conversation exchange to store
            update_profile: Whether to update user profile
            
        Returns:
            Dict with storage results
        """
        try:
            start_time = datetime.now()
            stored_components = []
            
            logger.info("💾 Storing conversation for %s", exchange.user_memory.user_id)
            
            # Store user message
            try:
                user_doc_id = await self.vector_db.store_conversation(exchange.user_memory)
                stored_components.append(f"user_message:{user_doc_id}")
                logger.debug("✅ Stored user message: %s", user_doc_id)
            except Exception as e:
                logger.error("❌ Failed to store user message: %s", e)
                raise
            
            # Small delay to prevent conflicts
            await asyncio.sleep(0.1)
            
            # Store AI response
            try:
                ai_doc_id = await self.vector_db.store_conversation(exchange.ai_memory)
                stored_components.append(f"ai_message:{ai_doc_id}")
                logger.debug("✅ Stored AI message: %s", ai_doc_id)
            except Exception as e:
                logger.error("❌ Failed to store AI message: %s", e)
                raise
            
            # Store emotional patterns if present
            try:
                if exchange.ai_emotional_state:
                    await self.vector_db.store_emotional_pattern(
                        exchange.ai_emotional_state,
                        "aura"
                    )
                    stored_components.append("ai_emotional_pattern")
                
                if exchange.user_emotional_state:
                    await self.vector_db.store_emotional_pattern(
                        exchange.user_emotional_state,
                        exchange.user_memory.user_id
                    )
                    stored_components.append("user_emotional_pattern")
            except Exception as e:
                logger.warning("⚠️ Failed to store emotional patterns: %s", e)
                # Non-critical, don't fail the whole operation
            
            # Update user profile if requested
            if update_profile:
                try:
                    await self._update_user_profile(exchange)
                    stored_components.append("user_profile")
                except Exception as e:
                    logger.warning("⚠️ Failed to update user profile: %s", e)
                    # Non-critical, don't fail the whole operation
            
            # Update metrics
            self.conversations_stored += 1
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            result = {
                "success": True,
                "stored_components": stored_components,
                "duration_ms": duration,
                "user_id": exchange.user_memory.user_id,
                "session_id": exchange.session_id
            }
            
            logger.info("✅ Conversation stored successfully in %sms", duration)
            return result
            
        except Exception as e:
            self.storage_failures += 1
            logger.error("❌ Failed to store conversation: %s", e)
            
            return {
                "success": False,
                "error": str(e),
                "stored_components": [],
                "duration_ms": 0,
                "user_id": exchange.user_memory.user_id if hasattr(exchange, 'user_memory') else "unknown",
                "session_id": exchange.session_id if hasattr(exchange, 'session_id') else "unknown"
            }

    async def _update_user_profile(self, exchange: SimpleConversationExchange):
        """Update user profile with interaction data"""
        try:
            user_id = exchange.user_memory.user_id
            profile = await self.file_system.load_user_profile(user_id) or {
                "name": user_id,
                "created_at": datetime.now().isoformat()
            }
            
            # Update interaction metadata
            profile["last_interaction"] = datetime.now().isoformat()
            profile["total_messages"] = int(profile.get("total_messages", 0)) + 1
            
            # Store latest emotional states for quick access
            if exchange.user_emotional_state:
                profile["last_emotional_state"] = {
                    "name": exchange.user_emotional_state.name,
                    "intensity": exchange.user_emotional_state.intensity.value,
                    "timestamp": exchange.user_emotional_state.timestamp.isoformat() if exchange.user_emotional_state.timestamp else None
                }
            
            await self.file_system.save_user_profile(user_id, profile)
            logger.debug("✅ Updated profile for %s", user_id)
            
        except Exception as e:
            logger.error("❌ Failed to update user profile: %s", e)
            raise

    async def get_chat_history(self, user_id: str, limit: int = 50) -> Dict[str, Any]:
        """
        Get chat history for a user with simple, reliable retrieval.
        
        Args:
            user_id: User ID to get history for
            limit: Maximum number of conversations to return
            
        Returns:
            Dict with sessions and message data
        """
        try:
            logger.info("📖 Getting chat history for %s", user_id)
            
            # Get conversations from vector DB
            results = self.vector_db.conversations.get(
                where={"user_id": {"$eq": user_id}},
                limit=limit,
                include=["documents", "metadatas"]
            )
            
            if not results or not results.get('documents'):
                logger.info("📭 No chat history found for %s", user_id)
                return {"sessions": [], "total": 0}
            
            # Group by session
            sessions = {}
            processed_messages = 0
            
            for i, doc in enumerate(results['documents']):
                try:
                    metadata = results['metadatas'][i] if results.get('metadatas') else {}
                    session_id = metadata.get('session_id', 'unknown')
                    
                    if not doc or not metadata.get('timestamp'):
                        continue
                    
                    if session_id not in sessions:
                        sessions[session_id] = {
                            "session_id": session_id,
                            "messages": [],
                            "start_time": metadata.get('timestamp', ''),
                            "last_time": metadata.get('timestamp', '')
                        }
                    
                    message = {
                        "content": str(doc),
                        "sender": metadata.get('sender', 'unknown'),
                        "timestamp": metadata.get('timestamp', ''),
                        "emotion": metadata.get('emotion_name', 'Normal')
                    }
                    
                    sessions[session_id]["messages"].append(message)
                    processed_messages += 1
                    
                    # Update session times
                    timestamp = metadata.get('timestamp', '')
                    if timestamp:
                        if timestamp < sessions[session_id]["start_time"] or not sessions[session_id]["start_time"]:
                            sessions[session_id]["start_time"] = timestamp
                        if timestamp > sessions[session_id]["last_time"] or not sessions[session_id]["last_time"]:
                            sessions[session_id]["last_time"] = timestamp
                            
                except Exception as e:
                    logger.warning("⚠️ Error processing message %s: %s", i, e)
                    continue
            
            # Convert to list and sort
            session_list = list(sessions.values())
            session_list.sort(key=lambda x: x.get("last_time", ""), reverse=True)
            
            # Sort messages within each session
            for session in session_list:
                session["messages"].sort(key=lambda m: m.get("timestamp", ""))
            
            logger.info("✅ Retrieved %s sessions with %s messages", len(session_list), processed_messages)
            return {"sessions": session_list, "total": len(session_list)}
            
        except Exception as e:
            logger.error("❌ Failed to get chat history: %s", e)
            return {"sessions": [], "total": 0, "error": str(e)}

    async def get_session_messages(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """
        Get messages for a specific session.
        
        Args:
            user_id: User ID
            session_id: Session ID
            
        Returns:
            List of message dictionaries
        """
        try:
            logger.info("📖 Getting session %s for %s", session_id, user_id)
            
            results = self.vector_db.conversations.get(
                where={
                    "$and": [
                        {"user_id": {"$eq": user_id}},
                        {"session_id": {"$eq": session_id}}
                    ]
                },
                include=["documents", "metadatas"]
            )
            
            if not results or not results.get('ids'):
                logger.info("📭 No messages found for session %s", session_id)
                return []
            
            messages = []
            ids_list = results['ids']
            documents_list = results.get('documents', [])
            metadatas_list = results.get('metadatas', [])
            
            for i in range(len(ids_list)):
                try:
                    doc = documents_list[i] if i < len(documents_list) else None
                    meta = metadatas_list[i] if i < len(metadatas_list) else {}
                    
                    if not doc:
                        continue
                    
                    message_item = {
                        "id": ids_list[i],
                        "message": doc,
                        **meta
                    }
                    
                    messages.append(message_item)
                    
                except Exception as e:
                    logger.warning("⚠️ Error processing message %s: %s", i, e)
                    continue
            
            # Sort by timestamp
            messages.sort(key=lambda x: x.get('timestamp', ''))
            
            logger.info("✅ Retrieved %s messages for session %s", len(messages), session_id)
            return messages
            
        except Exception as e:
            logger.error("❌ Failed to get session messages: %s", e)
            return []

    async def search_conversations(
        self,
        query: str,
        user_id: str,
        n_results: int = 5,
        where_filter: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search conversations with simple, reliable method.
        
        Args:
            query: Search query
            user_id: User ID
            n_results: Number of results
            where_filter: Additional filters
            
        Returns:
            List of search results
        """
        try:
            logger.info("🔍 Searching conversations for %s: %s", user_id, query)
            
            results = await self.vector_db.search_conversations(
                query=query,
                user_id=user_id,
                n_results=n_results,
                where_filter=where_filter
            )
            
            logger.info("✅ Found %s conversation results", len(results))
            return results
            
        except Exception as e:
            logger.error("❌ Search failed: %s", e)
            return []

    def get_metrics(self) -> Dict[str, Any]:
        """Get simple persistence metrics"""
        return {
            "conversations_stored": self.conversations_stored,
            "storage_failures": self.storage_failures,
            "success_rate": (
                self.conversations_stored / (self.conversations_stored + self.storage_failures)
                if (self.conversations_stored + self.storage_failures) > 0 else 1.0
            ),
            "timestamp": datetime.now().isoformat()
        }
