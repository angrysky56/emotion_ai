"""
Aura + Memvid Hybrid Memory System
Combines Aura's emotional intelligence with Memvid's revolutionary video-based memory
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Aura imports
import chromadb

# Memvid imports
from memvid import MemvidEncoder, MemvidRetriever

logger = logging.getLogger(__name__)

class AuraMemvidHybrid:
    """
    Hybrid memory system combining:
    - Aura's emotional intelligence and real-time interaction (ChromaDB)
    - Memvid's long-term compressed knowledge storage (Video files)
    """

    def __init__(self,
                 aura_data_dir: str = "./aura_data",
                 memvid_data_dir: str = "./memvid_data",
                 active_memory_days: int = 30,
                 emotional_memory_retention: int = 90):

        self.aura_data_dir = Path(aura_data_dir)
        self.memvid_data_dir = Path(memvid_data_dir)
        self.active_memory_days = active_memory_days
        self.emotional_memory_retention = emotional_memory_retention

        # Create directories
        self.aura_data_dir.mkdir(exist_ok=True)
        self.memvid_data_dir.mkdir(exist_ok=True)

        # Initialize Aura's active memory (ChromaDB)
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.aura_data_dir / "active_memory")
        )

        # Active collections for different types of memories
        self.conversations = self.chroma_client.get_or_create_collection(
            name="active_conversations",
            metadata={"hnsw:space": "cosine"}
        )

        self.emotional_states = self.chroma_client.get_or_create_collection(
            name="emotional_memories",
            metadata={"hnsw:space": "cosine"}
        )

        self.cognitive_patterns = self.chroma_client.get_or_create_collection(
            name="cognitive_patterns",
            metadata={"hnsw:space": "cosine"}
        )

        # Initialize Memvid components for long-term storage
        self.memvid_encoder = MemvidEncoder()
        self.memvid_archives = {}  # {archive_name: MemvidRetriever}

        # Load existing memvid archives
        self._load_existing_archives()

        # Memory usage tracking
        self.usage_tracker = {}

    def _load_existing_archives(self):
        """Load existing memvid archives"""
        for video_file in self.memvid_data_dir.glob("*.mp4"):
            index_file = video_file.with_suffix(".json")
            if index_file.exists():
                archive_name = video_file.stem
                try:
                    self.memvid_archives[archive_name] = MemvidRetriever(
                        str(video_file), str(index_file)
                    )
                    logger.info("Loaded memvid archive: %s", archive_name)
                except Exception as e:
                    logger.error("Failed to load archive %s: %s", archive_name, e)

    def store_conversation(self,
                          user_id: str,
                          message: str,
                          response: str,
                          emotional_state: Optional[str] = None,
                          cognitive_focus: Optional[str] = None,
                          session_id: Optional[str] = None) -> str:
        """Store conversation in active memory with emotional context"""

        timestamp = datetime.now()
        memory_id = f"conv_{timestamp.timestamp()}"

        # Prepare conversation data
        conversation_text = f"User: {message}\nAura: {response}"
        metadata = {
            "user_id": user_id,
            "timestamp": timestamp.isoformat(),
            "emotional_state": emotional_state,
            "cognitive_focus": cognitive_focus,
            "session_id": session_id,
            "memory_type": "conversation",
            "access_count": 0
        }

        # Store in active conversation memory
        self.conversations.add(
            documents=[conversation_text],
            metadatas=[metadata],
            ids=[memory_id]
        )

        # Store emotional context separately if provided
        if emotional_state:
            self._store_emotional_memory(
                user_id, emotional_state, message, timestamp
            )

        # Store cognitive pattern if provided
        if cognitive_focus:
            self._store_cognitive_pattern(
                user_id, cognitive_focus, conversation_text, timestamp
            )

        # Track usage
        self.usage_tracker[memory_id] = {
            "access_count": 0,
            "last_access": timestamp,
            "created": timestamp
        }

        logger.info("Stored conversation memory: %s", memory_id)
        return memory_id

    def _store_emotional_memory(self, user_id: str, emotional_state: str,
                               context: str, timestamp: datetime):
        """Store emotional context in specialized collection"""

        emotion_id = f"emotion_{timestamp.timestamp()}"
        emotional_context = f"Emotional state: {emotional_state}\nContext: {context}"

        self.emotional_states.add(
            documents=[emotional_context],
            metadatas=[{
                "user_id": user_id,
                "emotional_state": emotional_state,
                "timestamp": timestamp.isoformat(),
                "memory_type": "emotional"
            }],
            ids=[emotion_id]
        )

    def _store_cognitive_pattern(self, user_id: str, cognitive_focus: str,
                                context: str, timestamp: datetime):
        """Store cognitive patterns for ASEKE framework"""

        pattern_id = f"cognitive_{timestamp.timestamp()}"
        cognitive_context = f"Cognitive focus: {cognitive_focus}\nContext: {context}"

        self.cognitive_patterns.add(
            documents=[cognitive_context],
            metadatas=[{
                "user_id": user_id,
                "cognitive_focus": cognitive_focus,
                "timestamp": timestamp.isoformat(),
                "memory_type": "cognitive"
            }],
            ids=[pattern_id]
        )

    def search_active_memory(self, query: str, user_id: str,
                           max_results: int = 5,
                           memory_types: Optional[List[str]] = None) -> List[Dict]:
        """Search active memory with emotional and cognitive context"""

        results = []

        # Default to all memory types
        if memory_types is None:
            memory_types = ["conversation", "emotional", "cognitive"]

        # Search conversations
        if "conversation" in memory_types:
            conv_results = self.conversations.query(
                query_texts=[query],
                n_results=max_results,
                where={"user_id": user_id}
            )
            results.extend(self._format_search_results(conv_results, "conversation"))

        # Search emotional memories
        if "emotional" in memory_types:
            emotion_results = self.emotional_states.query(
                query_texts=[query],
                n_results=max_results // 2,
                where={"user_id": user_id}
            )
            results.extend(self._format_search_results(emotion_results, "emotional"))

        # Search cognitive patterns
        if "cognitive" in memory_types:
            cognitive_results = self.cognitive_patterns.query(
                query_texts=[query],
                n_results=max_results // 2,
                where={"user_id": user_id}
            )
            results.extend(self._format_search_results(cognitive_results, "cognitive"))

        # Update access tracking
        for result in results:
            self._update_usage(result["id"])

        # Sort by relevance and limit
        results.sort(key=lambda x: x["distance"])
        return results[:max_results]

    def search_memvid_archives(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search across all memvid archives for long-term knowledge"""

        all_results = []

        for archive_name, retriever in self.memvid_archives.items():
            try:
                # Get results with metadata
                results = retriever.search_with_metadata(query, max_results)

                for result in results:
                    all_results.append({
                        "text": result["text"],
                        "score": result["score"],
                        "source": f"memvid:{archive_name}",
                        "chunk_id": result["chunk_id"],
                        "frame": result["frame"],
                        "archive": archive_name
                    })
            except Exception as e:
                logger.error("Error searching archive %s: %s", archive_name, e)

        # Sort by score and return top results
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:max_results]

    def unified_search(self, query: str, user_id: str, max_results: int = 10) -> Dict:
        """
        Unified search across both active memory and memvid archives
        Returns combined results with source attribution
        """

        # Search active memory (recent, emotional, cognitive)
        active_results = self.search_active_memory(query, user_id, max_results // 2)

        # Search memvid archives (long-term knowledge)
        archive_results = self.search_memvid_archives(query, max_results // 2)

        return {
            "query": query,
            "user_id": user_id,
            "active_memory": active_results,
            "archive_memory": archive_results,
            "total_results": len(active_results) + len(archive_results),
            "search_timestamp": datetime.now().isoformat()
        }

    def archive_old_memories(self, archive_name: Optional[str] = None) -> Dict:
        """
        Archive old active memories to memvid format
        Creates compressed video archives of conversation history
        """

        if archive_name is None:
            archive_name = f"aura_archive_{datetime.now().strftime('%Y%m%d')}"

        # Get old memories for archival
        cutoff_date = datetime.now() - timedelta(days=self.active_memory_days)

        memories_to_archive = []
        ids_to_delete = []

        # Collect old conversation memories
        for memory_id, usage_data in self.usage_tracker.items():
            if usage_data["created"] < cutoff_date and usage_data["access_count"] < 3:
                try:
                    # Get memory from ChromaDB
                    memory_data = self.conversations.get(ids=[memory_id])
                    if memory_data["documents"]:
                        memories_to_archive.append({
                            "id": memory_id,
                            "text": memory_data["documents"][0],
                            "metadata": memory_data["metadatas"][0] if memory_data["metadatas"] else {}
                        })
                        ids_to_delete.append(memory_id)
                except Exception as e:
                    logger.error("Error retrieving memory %s: %s", memory_id, e)

        if not memories_to_archive:
            logger.info("No memories to archive")
            return {"archived_count": 0, "archive_name": archive_name}

        # Create memvid archive
        encoder = MemvidEncoder()

        # Add memories as chunks
        for memory in memories_to_archive:
            # Create rich text representation
            archive_text = f"""
            Memory ID: {memory['id']}
            Timestamp: {memory['metadata'].get('timestamp', 'unknown')}
            User: {memory['metadata'].get('user_id', 'unknown')}
            Emotional State: {memory['metadata'].get('emotional_state', 'none')}
            Cognitive Focus: {memory['metadata'].get('cognitive_focus', 'none')}

            Content:
            {memory['text']}
            """
            encoder.add_text(archive_text.strip())

        # Build video archive
        video_path = self.memvid_data_dir / f"{archive_name}.mp4"
        index_path = self.memvid_data_dir / f"{archive_name}.json"

        build_stats = encoder.build_video(
            str(video_path),
            str(index_path),
            codec="h265",  # High compression for archives
            show_progress=True
        )

        # Load new archive
        self.memvid_archives[archive_name] = MemvidRetriever(
            str(video_path), str(index_path)
        )

        # Remove archived memories from active storage
        self.conversations.delete(ids=ids_to_delete)
        for memory_id in ids_to_delete:
            del self.usage_tracker[memory_id]

        logger.info("Archived %s memories to %s", len(memories_to_archive), archive_name)

        return {
            "archived_count": len(memories_to_archive),
            "archive_name": archive_name,
            "video_size_mb": build_stats.get("video_size_mb", 0),
            "compression_ratio": len(memories_to_archive) / build_stats.get("video_size_mb", 1)
        }

    def import_knowledge_base(self, knowledge_source: str, archive_name: str) -> Dict:
        """
        Import external knowledge into memvid format
        Supports PDFs, text files, and document collections
        """

        encoder = MemvidEncoder()

        source_path = Path(knowledge_source)

        if source_path.is_file():
            if source_path.suffix.lower() == ".pdf":
                encoder.add_pdf(str(source_path))
            elif source_path.suffix.lower() in [".txt", ".md"]:
                with open(source_path, 'r', encoding='utf-8') as f:
                    encoder.add_text(f.read())
            else:
                raise ValueError(f"Unsupported file type: {source_path.suffix}") from e

        elif source_path.is_dir():
            # Process directory of documents
            for file_path in source_path.rglob("*"):
                if file_path.is_file():
                    try:
                        if file_path.suffix.lower() == ".pdf":
                            encoder.add_pdf(str(file_path))
                        elif file_path.suffix.lower() in [".txt", ".md"]:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                encoder.add_text(f.read())
                    except Exception as e:
                        logger.warning("Failed to process %s: %s", file_path, e)

        else:
            raise ValueError(f"Knowledge source not found: {knowledge_source}") from e

        # Build archive
        video_path = self.memvid_data_dir / f"{archive_name}.mp4"
        index_path = self.memvid_data_dir / f"{archive_name}.json"

        build_stats = encoder.build_video(
            str(video_path),
            str(index_path),
            codec="h265",
            show_progress=True
        )

        # Load archive
        self.memvid_archives[archive_name] = MemvidRetriever(
            str(video_path), str(index_path)
        )

        logger.info("Imported knowledge base: %s", archive_name)

        return {
            "archive_name": archive_name,
            "chunks_imported": build_stats.get("total_chunks", 0),
            "video_size_mb": build_stats.get("video_size_mb", 0),
            "source": str(source_path)
        }

    def _format_search_results(self, chroma_results: Any, result_type: str) -> List[Dict]:
        """Format ChromaDB results for unified interface"""

        results = []

        if chroma_results["documents"]:
            for i, (doc, metadata, distance) in enumerate(zip(
                chroma_results["documents"][0],
                chroma_results["metadatas"][0],
                chroma_results["distances"][0]
            )):
                results.append({
                    "id": chroma_results["ids"][0][i],
                    "text": doc,
                    "distance": distance,
                    "score": 1.0 / (1.0 + distance),
                    "metadata": metadata,
                    "source": f"active:{result_type}",
                    "type": result_type
                })

        return results

    def _update_usage(self, memory_id: str):
        """Update usage tracking for memory"""
        if memory_id in self.usage_tracker:
            self.usage_tracker[memory_id]["access_count"] += 1
            self.usage_tracker[memory_id]["last_access"] = datetime.now()

    def get_system_stats(self) -> Dict:
        """Get comprehensive system statistics"""

        # Active memory stats
        active_stats = {
            "conversations": self.conversations.count(),
            "emotional_memories": self.emotional_states.count(),
            "cognitive_patterns": self.cognitive_patterns.count()
        }

        # Archive stats
        archive_stats = {}
        total_archive_size = 0

        for name, retriever in self.memvid_archives.items():
            stats = retriever.get_stats()
            archive_stats[name] = stats

            # Calculate file size
            video_path = Path(stats["video_file"])
            if video_path.exists():
                size_mb = video_path.stat().st_size / (1024 * 1024)
                total_archive_size += size_mb

        return {
            "active_memory": active_stats,
            "archives": archive_stats,
            "total_archive_size_mb": total_archive_size,
            "usage_tracker_entries": len(self.usage_tracker),
            "system_type": "aura_memvid_hybrid"
        }

    def cleanup_old_emotional_memories(self):
        """Clean up very old emotional memories beyond retention period"""

        cutoff_date = datetime.now() - timedelta(days=self.emotional_memory_retention)

        # Note: ChromaDB doesn't support date range queries directly
        # This would need to be implemented with metadata filtering
        # For now, we'll log the intent
        logger.info("Emotional memory cleanup scheduled for memories older than %s", cutoff_date)

    def export_user_data(self, user_id: str, export_format: str = "json") -> Dict:
        """Export all user data across both active and archived memories"""

        # Search active memories
        active_data = self.search_active_memory(
            query="*",  # Get all memories
            user_id=user_id,
            max_results=1000
        )

        # Search archives (note: memvid doesn't have user filtering built-in)
        # This would need custom implementation

        export_data = {
            "user_id": user_id,
            "export_timestamp": datetime.now().isoformat(),
            "active_memories": active_data,
            "format": export_format
        }

        if export_format == "json":
            export_path = self.aura_data_dir / f"export_{user_id}_{datetime.now().strftime('%Y%m%d')}.json"
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)

            return {"export_file": str(export_path), "data": export_data}

        return export_data


# Example usage integration with Aura
class AuraMemvidIntegration:
    """Main integration class for Aura + Memvid"""

    def __init__(self, config_path: Optional[str] = None):
        self.memory_system = AuraMemvidHybrid()
        self.config = self._load_config(config_path)

        # Schedule periodic archival
        self.last_archival = datetime.now()
        self.archival_interval = timedelta(days=7)  # Weekly archival

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration"""
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                return json.load(f)

        return {
            "auto_archival": True,
            "archival_interval_days": 7,
            "max_active_memories": 10000,
            "knowledge_bases": []
        }

    def process_conversation(self, user_id: str, message: str, response: str,
                           emotional_state: Optional[str] = None,
                           cognitive_focus: Optional[str] = None) -> str:
        """Process conversation with full context storage"""

        memory_id = self.memory_system.store_conversation(
            user_id=user_id,
            message=message,
            response=response,
            emotional_state=emotional_state,
            cognitive_focus=cognitive_focus
        )

        # Check if archival is needed
        if self.config.get("auto_archival", True):
            self._check_archival_schedule()

        return memory_id

    def search_comprehensive(self, query: str, user_id: str) -> Dict:
        """Comprehensive search across all memory systems"""
        return self.memory_system.unified_search(query, user_id)

    def _check_archival_schedule(self):
        """Check if scheduled archival should run"""
        if datetime.now() - self.last_archival > self.archival_interval:
            logger.info("Running scheduled memory archival")
            result = self.memory_system.archive_old_memories()
            self.last_archival = datetime.now()
            logger.info("Archival complete: %s", result)
