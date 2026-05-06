"""
Real Aura + Memvid Integration
Uses actual memvid with QR-code video compression!
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

# Aura imports
import chromadb
from chromadb.config import Settings

# REAL Memvid imports!
from memvid import MemvidEncoder, MemvidRetriever, MemvidChat

logger = logging.getLogger(__name__)

class AuraRealMemvid:
    """
    REAL Memvid integration with Aura
    Uses actual QR-code video compression for revolutionary memory storage!
    """

    def __init__(self,
                 aura_chroma_path: str = "./aura_chroma_db",
                 memvid_video_path: str = "./memvid_videos",
                 active_memory_days: int = 30):

        self.aura_chroma_path = Path(aura_chroma_path)
        self.memvid_video_path = Path(memvid_video_path)
        self.active_memory_days = active_memory_days

        # Create video directory
        self.memvid_video_path.mkdir(exist_ok=True)

        # Initialize ChromaDB connection to existing Aura collections
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.aura_chroma_path),
            settings=Settings(anonymized_telemetry=False)
        )

        # Get existing collections
        try:
            self.conversations = self.chroma_client.get_collection("aura_conversations")
            self.emotional_patterns = self.chroma_client.get_collection("aura_emotional_patterns")
            logger.info("✅ Connected to existing Aura collections")
        except Exception as e:
            logger.warning("Could not connect to existing collections: %s", e)
            # Create new collections if they don't exist
            self.conversations = self.chroma_client.get_or_create_collection("aura_conversations")
            self.emotional_patterns = self.chroma_client.get_or_create_collection("aura_emotional_patterns")

        # Load existing memvid video archives
        self.video_archives = {}
        self._load_existing_video_archives()

        logger.info("🎥 Real Memvid integration initialized with %s video archives", len(self.video_archives))

    def _load_existing_video_archives(self):
        """Load existing memvid video archives"""
        for video_file in self.memvid_video_path.glob("*.mp4"):
            index_file = video_file.with_suffix(".json")
            if index_file.exists():
                archive_name = video_file.stem
                try:
                    self.video_archives[archive_name] = MemvidRetriever(
                        str(video_file), str(index_file)
                    )
                    logger.info("🎬 Loaded video archive: %s", archive_name)
                except Exception as e:
                    logger.error("Failed to load video archive %s: %s", archive_name, e)

    def search_unified(self, query: str, user_id: str, max_results: int = 10) -> Dict:
        """
        Unified search across active ChromaDB and REAL memvid video archives
        """
        results = {
            "query": query,
            "user_id": user_id,
            "active_results": [],
            "video_archive_results": [],
            "total_results": 0,
            "archive_type": "real_memvid_video"
        }

        # Search active memory (ChromaDB)
        try:
            from sentence_transformers import SentenceTransformer
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            query_embedding = embedding_model.encode(query).tolist()

            active_search = self.conversations.query(
                query_embeddings=[query_embedding],
                n_results=max_results // 2,
                where={"user_id": user_id},
                include=["documents", "metadatas", "distances"]
            )

            if active_search["documents"] and active_search["documents"][0]:
                for i, doc in enumerate(active_search["documents"][0]):
                    distance = active_search["distances"][0][i] if active_search["distances"] and active_search["distances"][0] else 0.0
                    metadata = active_search["metadatas"][0][i] if active_search["metadatas"] and active_search["metadatas"][0] else {}
                    results["active_results"].append({
                        "text": doc,
                        "metadata": metadata,
                        "distance": distance,
                        "source": "active_memory",
                        "score": 1 - distance
                    })

        except Exception as e:
            logger.error("Error searching active memory: %s", e)

        # Search REAL memvid video archives!
        for archive_name, retriever in self.video_archives.items():
            try:
                # Use real memvid search with metadata
                video_results = retriever.search_with_metadata(query, max_results // 4)
                for result in video_results:
                    results["video_archive_results"].append({
                        "text": result["text"],
                        "score": result["score"],
                        "source": f"video_archive:{archive_name}",
                        "chunk_id": result["chunk_id"],
                        "frame": result["frame"],
                        "video_file": archive_name + ".mp4"
                    })
            except Exception as e:
                logger.error("Error searching video archive %s: %s", archive_name, e)

        results["total_results"] = len(results["active_results"]) + len(results["video_archive_results"])
        return results

    def archive_conversations_to_video(self, user_id: Optional[str] = None,
                                      codec: str = "h265") -> Dict:
        """
        Archive old conversations to REAL memvid video format!
        Creates MP4 files with QR-encoded conversation data
        """
        try:
            # Get old conversations from ChromaDB
            cutoff_date = datetime.now() - timedelta(days=self.active_memory_days)

            # Get all conversations for archival analysis
            all_conversations = self.conversations.get(
                include=["documents", "metadatas"]
            )

            # Get IDs separately (ChromaDB quirk)
            all_ids = self.conversations.get(include=[])["ids"]

            if not all_conversations["documents"]:
                return {"archived_count": 0, "message": "No conversations to archive"}

            # Create REAL memvid encoder
            encoder = MemvidEncoder()

            conversations_to_archive = []
            ids_to_delete = []

            for i, doc in enumerate(all_conversations["documents"]):
                metadata = all_conversations["metadatas"][i] if all_conversations["metadatas"] else {}
                doc_id = all_ids[i] if all_ids and i < len(all_ids) else f"doc_{i}"

                # Check if this should be archived
                timestamp_str = metadata.get('timestamp', '')
                if timestamp_str and isinstance(timestamp_str, str):
                    try:
                        doc_timestamp = datetime.fromisoformat(timestamp_str)
                        if doc_timestamp < cutoff_date:
                            # Create rich memory context for video encoding
                            video_memory_text = f"""
AURA MEMORY ARCHIVE
==================
ID: {doc_id}
User: {metadata.get('user_id', 'unknown')}
Timestamp: {timestamp_str}
Emotional State: {metadata.get('emotion_name', 'none')}
Intensity: {metadata.get('emotion_intensity', 'none')}
Cognitive Focus: {metadata.get('cognitive_focus', 'none')}
Brainwave: {metadata.get('brainwave', 'none')}
Neurotransmitter: {metadata.get('neurotransmitter', 'none')}

CONVERSATION:
{doc}
==================
"""

                            encoder.add_text(video_memory_text.strip())

                            conversations_to_archive.append(doc_id)
                            ids_to_delete.append(doc_id)
                    except ValueError:
                        pass  # Skip invalid timestamps

            if not conversations_to_archive:
                return {"archived_count": 0, "message": "No old conversations found"}

            # Build REAL memvid video archive!
            archive_name = f"aura_video_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            video_path = self.memvid_video_path / f"{archive_name}.mp4"
            index_path = self.memvid_video_path / f"{archive_name}.json"

            logger.info("🎬 Creating video archive with %s codec...", codec)

            build_stats = encoder.build_video(
                str(video_path),
                str(index_path),
                codec=codec,  # Use advanced video compression!
                show_progress=True
            )

            # Load new video archive
            self.video_archives[archive_name] = MemvidRetriever(
                str(video_path), str(index_path)
            )

            # Delete from ChromaDB
            if ids_to_delete:
                self.conversations.delete(ids=ids_to_delete)

            logger.info("🎥 Archived %s conversations to video: %s.mp4", len(conversations_to_archive), archive_name)

            return {
                "archived_count": len(conversations_to_archive),
                "archive_name": archive_name,
                "video_file": str(video_path),
                "video_codec": codec,
                "video_size_mb": build_stats.get("video_size_mb", 0),
                "compression_ratio": len(conversations_to_archive) / max(build_stats.get("video_size_mb", 1), 0.1),
                "total_frames": build_stats.get("total_frames", 0),
                "duration_seconds": build_stats.get("duration_seconds", 0),
                "archive_type": "real_memvid_video"
            }

        except Exception as e:
            logger.error("Error creating video archive: %s", e)
            return {"error": str(e), "archived_count": 0}

    def import_knowledge_to_video(self, source_path: str, archive_name: str,
                                 codec: str = "h265") -> Dict:
        """
        Import external documents into REAL memvid video archive
        Creates searchable MP4 files from documents!
        """
        try:
            # Create real memvid encoder
            encoder = MemvidEncoder()
            source = Path(source_path)

            if source.is_file():
                if source.suffix.lower() == ".pdf":
                    logger.info("📄 Importing PDF to video: %s", source)
                    encoder.add_pdf(str(source))
                elif source.suffix.lower() in [".txt", ".md"]:
                    logger.info("📝 Importing text to video: %s", source)
                    with open(source, 'r', encoding='utf-8') as f:
                        encoder.add_text(f.read())
                else:
                    raise ValueError(f"Unsupported file type: {source.suffix}") from e

            elif source.is_dir():
                logger.info("📁 Importing directory to video: %s", source)
                for file_path in source.rglob("*.txt"):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        encoder.add_text(f.read())
                for file_path in source.rglob("*.pdf"):
                    encoder.add_pdf(str(file_path))
                for file_path in source.rglob("*.md"):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        encoder.add_text(f.read())

            # Build REAL video archive
            video_path = self.memvid_video_path / f"{archive_name}.mp4"
            index_path = self.memvid_video_path / f"{archive_name}.json"

            logger.info("🎬 Building video archive with %s compression...", codec)

            build_stats = encoder.build_video(
                str(video_path),
                str(index_path),
                codec=codec,
                show_progress=True
            )

            # Load video archive
            self.video_archives[archive_name] = MemvidRetriever(
                str(video_path), str(index_path)
            )

            logger.info("🎥 Created video knowledge base: %s.mp4", archive_name)

            return {
                "archive_name": archive_name,
                "video_file": str(video_path),
                "video_codec": codec,
                "chunks_imported": build_stats.get("total_chunks", 0),
                "video_size_mb": build_stats.get("video_size_mb", 0),
                "compression_ratio": build_stats.get("total_chunks", 0) / max(build_stats.get("video_size_mb", 1), 0.1),
                "total_frames": build_stats.get("total_frames", 0),
                "duration_seconds": build_stats.get("duration_seconds", 0),
                "fps": build_stats.get("fps", 0),
                "source": str(source),
                "archive_type": "real_memvid_video"
            }

        except Exception as e:
            logger.error("Error creating video knowledge base: %s", e)
            return {"error": str(e)}

    def get_system_stats(self) -> Dict:
        """Get comprehensive system statistics"""
        stats = {
            "active_memory": {
                "conversations": self.conversations.count(),
                "emotional_patterns": self.emotional_patterns.count()
            },
            "video_archives": {},
            "total_video_size_mb": 0,
            "memvid_type": "real_video_compression"
        }

        for name, retriever in self.video_archives.items():
            try:
                archive_stats = retriever.get_stats()
                stats["video_archives"][name] = archive_stats

                # Calculate video file size
                video_path = Path(archive_stats["video_file"])
                if video_path.exists():
                    size_mb = video_path.stat().st_size / (1024 * 1024)
                    stats["total_video_size_mb"] += size_mb

            except Exception as e:
                logger.error("Error getting stats for %s: %s", name, e)

        return stats

    def create_memvid_chat(self, archive_name: str) -> MemvidChat:
        """
        Create a MemvidChat instance for interactive conversation with a video archive
        """
        if archive_name not in self.video_archives:
            raise ValueError(f"Video archive '{archive_name}' not found") from e

        retriever = self.video_archives[archive_name]
        video_file = retriever.video_file
        index_file = retriever.index_file

        return MemvidChat(video_file, index_file)

    def list_video_archives(self) -> List[Dict]:
        """List all available video archives with details"""
        archives = []

        for name, retriever in self.video_archives.items():
            try:
                stats = retriever.get_stats()
                video_path = Path(stats["video_file"])

                archive_info = {
                    "name": name,
                    "video_file": stats["video_file"],
                    "total_frames": stats.get("total_frames", 0),
                    "fps": stats.get("fps", 0),
                    "cache_size": stats.get("cache_size", 0),
                    "video_size_mb": video_path.stat().st_size / (1024 * 1024) if video_path.exists() else 0,
                    "can_play_as_video": True  # The revolutionary feature!
                }

                archives.append(archive_info)

            except Exception as e:
                logger.error("Error getting info for archive %s: %s", name, e)

        return archives

# Global instance for MCP integration
_aura_real_memvid = None

def get_aura_real_memvid():
    """Get or create the real memvid system instance"""
    global _aura_real_memvid
    if _aura_real_memvid is None:
        _aura_real_memvid = AuraRealMemvid()
    return _aura_real_memvid
