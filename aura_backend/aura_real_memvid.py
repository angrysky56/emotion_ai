"""
Real Aura + Memvid Integration (CHROMADB CONFLICT FIXED)
Uses actual memvid with QR-code video compression!

FIXED: ChromaDB instance conflict resolved - now reuses existing client
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Aura imports
import chromadb
from chromadb.config import Settings

# REAL Memvid SDK (v2)
try:
    import memvid_sdk

    REAL_MEMVID_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Real memvid-sdk (v2) imported successfully!")
except ImportError:
    REAL_MEMVID_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ memvid-sdk not available, using placeholder classes")


# Placeholder classes for when real memvid isn't available
class _MemvidPlaceholder:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def put(self, *args, **kwargs):
        return 0

    def find(self, *args, **kwargs):
        return {"hits": [], "total_hits": 0}

    def ask(self, *args, **kwargs):
        return {"answer": "Memvid not available"}

    def stats(self):
        return {}

    def close(self):
        pass


if not REAL_MEMVID_AVAILABLE:
    Memvid = _MemvidPlaceholder
else:
    # We use the memvid_sdk directly in the code
    pass

logger = logging.getLogger(__name__)


class AuraRealMemvid:
    """
    REAL Memvid integration with Aura (CHROMADB CONFLICT FIXED)
    Uses actual QR-code video compression for revolutionary memory storage!

    FIXED: Now accepts existing ChromaDB client to avoid instance conflicts
    """

    def __init__(
        self,
        aura_chroma_path: str = "./aura_chroma_db",
        memvid_video_path: str = "./memvid_videos",
        active_memory_days: int = 30,
        existing_chroma_client=None,
    ):  # NEW: Accept existing client

        self.aura_chroma_path = Path(aura_chroma_path)
        self.memvid_video_path = Path(memvid_video_path)
        self.active_memory_days = active_memory_days

        # Create video directory
        self.memvid_video_path.mkdir(exist_ok=True)

        # Configure memvid-sdk global defaults from environment
        if REAL_MEMVID_AVAILABLE:
            embedding_provider = os.getenv("MEMVID_EMBEDDING_PROVIDER", "openai")
            self.embedding_model = os.getenv("MEMVID_EMBEDDING_MODEL", "openai-small")

            logger.info(
                f"🎥 Configuring Memvid with provider: {embedding_provider}, model: {self.embedding_model}"
            )

            memvid_sdk.configure(
                {
                    "default_embedding_provider": embedding_provider,
                    "default_memory_kind": "basic",
                }
            )

        # FIXED: Use existing ChromaDB client if provided, otherwise create new one carefully
        if existing_chroma_client is not None:
            logger.info("✅ Using existing ChromaDB client (conflict avoided)")
            self.chroma_client = existing_chroma_client
        else:
            try:
                # Try to connect to existing instance first
                self.chroma_client = chromadb.PersistentClient(
                    path=str(self.aura_chroma_path),
                    settings=Settings(anonymized_telemetry=False),
                )
                logger.info("✅ Connected to existing ChromaDB instance")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.warning("ChromaDB instance conflict detected: %s", e)
                    logger.info("🔄 Attempting to use existing instance...")

                    # Try to get the existing client (this is a workaround)
                    try:
                        self.chroma_client = chromadb.PersistentClient(
                            path=str(self.aura_chroma_path),
                            settings=Settings(
                                anonymized_telemetry=False, allow_reset=True
                            ),
                        )
                        logger.info("✅ Successfully connected after reset")
                    except Exception as e2:
                        logger.error("❌ Could not resolve ChromaDB conflict: %s", e2)
                        raise RuntimeError(
                            f"ChromaDB conflict: {e}. Please restart the application."
                        ) from e2
                else:
                    raise e

        # Get existing collections
        try:
            self.conversations = self.chroma_client.get_collection("aura_conversations")
            self.emotional_patterns = self.chroma_client.get_collection(
                "aura_emotional_patterns"
            )
            logger.info("✅ Connected to existing Aura collections")
        except Exception as e:
            logger.warning("Could not connect to existing collections: %s", e)
            try:
                # Create new collections if they don't exist
                self.conversations = self.chroma_client.get_or_create_collection(
                    "aura_conversations"
                )
                self.emotional_patterns = self.chroma_client.get_or_create_collection(
                    "aura_emotional_patterns"
                )
                logger.info("✅ Created new Aura collections")
            except Exception as e2:
                logger.error("❌ Failed to create collections: %s", e2)
                raise

        # Load existing memvid archives (.mv2)
        self.video_archives = {}
        self._load_existing_video_archives()

        archive_count = len(self.video_archives)
        memvid_status = "REAL" if REAL_MEMVID_AVAILABLE else "PLACEHOLDER"
        logger.info(
            f"🎥 {memvid_status} Memvid integration initialized with {archive_count} archives"
        )

    def _load_existing_video_archives(self):
        """Load existing memvid archives (.mv2)"""
        if not REAL_MEMVID_AVAILABLE:
            logger.info("⚠️ Real memvid not available, skipping archive loading")
            return

        for archive_file in self.memvid_video_path.glob("*.mv2"):
            archive_name = archive_file.stem
            try:
                # In v2, we just open the file
                self.video_archives[archive_name] = memvid_sdk.use(
                    "basic", str(archive_file)
                )
                logger.info("🎬 Loaded archive: %s", archive_name)
            except Exception as e:
                logger.error("Failed to load archive %s: %s", archive_name, e)

        # Migration path: Check for legacy .mp4/.json pairs
        for video_file in self.memvid_video_path.glob("*.mp4"):
            index_file = video_file.with_suffix(".json")
            if index_file.exists():
                mv2_file = video_file.with_suffix(".mv2")
                if not mv2_file.exists():
                    logger.info(
                        "🔄 Found legacy archive %s, migration recommended",
                        video_file.name,
                    )
                    # We don't auto-migrate here to avoid blocking startup,
                    # but we could add a migrate() method.

    def search_unified(self, query: str, user_id: str, max_results: int = 10) -> Dict:
        """
        Unified search across active ChromaDB and REAL memvid video archives
        FIXED: Better error handling for ChromaDB conflicts
        """
        results = {
            "query": query,
            "user_id": user_id,
            "active_results": [],
            "video_archive_results": [],
            "total_results": 0,
            "archive_type": (
                "real_memvid_video" if REAL_MEMVID_AVAILABLE else "placeholder"
            ),
            "errors": [],
        }

        # Search active memory (ChromaDB) with conflict protection
        try:
            from aura_backend.shared_embedding_service import get_embedding_service

            embedding_service = get_embedding_service()
            query_embedding = embedding_service.encode_single(query)

            active_search = self.conversations.query(
                query_embeddings=[query_embedding],
                n_results=max_results // 2,
                where={"user_id": user_id},
                include=["documents", "metadatas", "distances"],
            )

            # More explicit checks for existence and structure of results
            docs_list = active_search.get("documents")
            meta_list = active_search.get("metadatas")
            dist_list = active_search.get("distances")

            if (
                docs_list
                and isinstance(docs_list, list)
                and len(docs_list) > 0
                and docs_list[0] is not None
                and isinstance(docs_list[0], list)
            ):

                actual_documents = docs_list[0]
                actual_metadatas = (
                    meta_list[0]
                    if meta_list
                    and isinstance(meta_list, list)
                    and len(meta_list) > 0
                    and meta_list[0] is not None
                    and isinstance(meta_list[0], list)
                    else []
                )
                actual_distances = (
                    dist_list[0]
                    if dist_list
                    and isinstance(dist_list, list)
                    and len(dist_list) > 0
                    and dist_list[0] is not None
                    and isinstance(dist_list[0], list)
                    else []
                )

                for i, doc_content in enumerate(actual_documents):
                    distance = 0.0
                    if i < len(actual_distances):
                        distance = actual_distances[i]

                    metadata = {}
                    if i < len(actual_metadatas) and actual_metadatas[i] is not None:
                        metadata = actual_metadatas[i]

                    results["active_results"].append(
                        {
                            "text": doc_content,
                            "metadata": metadata,
                            "distance": distance,
                            "source": "active_memory",
                            "score": 1 - distance,
                        }
                    )

        except Exception as e:
            error_msg = f"Error searching active memory: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        # Search REAL memvid archives (v2)
        if REAL_MEMVID_AVAILABLE:
            for archive_name, mv in self.video_archives.items():
                try:
                    # Use v2 find() method
                    search_res = mv.find(
                        query,
                        limit=max_results // 4,
                        embedding_model=self.embedding_model,
                    )
                    hits = search_res.get("hits", [])

                    for hit in hits:
                        results["video_archive_results"].append(
                            {
                                "text": hit.get("snippet", ""),
                                "score": hit.get("score", 0.0),
                                "source": f"archive:{archive_name}",
                                "frame_id": hit.get("frame_id"),
                                "title": hit.get("title", ""),
                                "archive_file": archive_name + ".mv2",
                            }
                        )
                except Exception as e:
                    error_msg = f"Error searching archive {archive_name}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
        else:
            results["errors"].append(
                "Real memvid not available - archive search disabled"
            )

        results["total_results"] = len(results["active_results"]) + len(
            results["video_archive_results"]
        )
        return results

    def archive_conversations_to_video(
        self, user_id: Optional[str] = None, codec: str = "h265"
    ) -> Dict:
        """
        Archive old conversations to REAL memvid video format!
        FIXED: Better error handling for ChromaDB operations
        """
        if not REAL_MEMVID_AVAILABLE:
            return {
                "error": "Real memvid not available",
                "archived_count": 0,
                "message": "Cannot create video archives without real memvid",
            }

        try:
            # Get old conversations from ChromaDB with conflict protection
            cutoff_date = datetime.now() - timedelta(days=self.active_memory_days)

            try:
                # Get all conversations for archival analysis
                all_conversations = self.conversations.get(
                    include=["documents", "metadatas"]
                )

                # Get IDs separately (ChromaDB quirk)
                all_ids = self.conversations.get(include=[])["ids"]
            except Exception as e:
                logger.error("ChromaDB access error during archival: %s", e)
                return {
                    "error": f"Database access failed: {e}",
                    "archived_count": 0,
                    "suggestion": "Restart the application to resolve database conflicts",
                }

            if not all_conversations["documents"]:
                return {"archived_count": 0, "message": "No conversations to archive"}

            # Create REAL memvid v2 archive
            archive_name = f"aura_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            archive_path = self.memvid_video_path / f"{archive_name}.mv2"

            logger.info("🎬 Creating memvid v2 archive: %s", archive_path)

            # Use memvid_sdk.create
            mv = memvid_sdk.create(
                str(archive_path),
                enable_vec=True,  # Aura benefits from semantic search
                enable_lex=True,
            )

            conversations_to_archive = []
            ids_to_delete = []

            # Ensure documents exist before iterating
            documents_to_process = all_conversations.get("documents")
            if documents_to_process:
                for i, doc in enumerate(documents_to_process):
                    metadatas_list = all_conversations.get("metadatas")
                    metadata = (
                        metadatas_list[i]
                        if metadatas_list and i < len(metadatas_list)
                        else {}
                    )
                    doc_id = all_ids[i] if all_ids and i < len(all_ids) else f"doc_{i}"

                    # Check if this should be archived
                    timestamp_str = metadata.get("timestamp", "")
                    if timestamp_str and isinstance(timestamp_str, str):
                        try:
                            doc_timestamp = datetime.fromisoformat(timestamp_str)
                            if doc_timestamp < cutoff_date:
                                conversation_text = str(doc).strip()

                                # Use v2 put() which handles metadata better
                                mv.put(
                                    title=f"Conversation {timestamp_str}",
                                    labels=[
                                        metadata.get("emotion_name", "none"),
                                        "aura_archive",
                                    ],
                                    metadata={
                                        "user_id": metadata.get("user_id", "unknown"),
                                        "timestamp": timestamp_str,
                                        "brainwave": metadata.get("brainwave", "none"),
                                        "emotion": metadata.get("emotion_name", "none"),
                                    },
                                    text=conversation_text,
                                    embedding_model=self.embedding_model,
                                )

                                conversations_to_archive.append(doc_id)
                                ids_to_delete.append(doc_id)
                        except ValueError:
                            pass  # Skip invalid timestamps

            if not conversations_to_archive:
                mv.close()
                if archive_path.exists():
                    archive_path.unlink()
                return {"archived_count": 0, "message": "No old conversations found"}

            # Finalize the archive
            mv.close()

            # Load new archive into memory
            self.video_archives[archive_name] = memvid_sdk.use(
                "basic", str(archive_path)
            )

            # Delete from ChromaDB with conflict protection
            if ids_to_delete:
                try:
                    self.conversations.delete(ids=ids_to_delete)
                    logger.info(
                        f"✅ Deleted {len(ids_to_delete)} conversations from active memory"
                    )
                except Exception as e:
                    logger.error("⚠️ Failed to delete from ChromaDB: %s", e)
                    # Continue anyway - the archive was created successfully

            logger.info(
                f"🎥 Archived {len(conversations_to_archive)} conversations to video: {archive_name}.mp4"
            )

            return {
                "archived_count": len(conversations_to_archive),
                "archive_name": archive_name,
                "archive_file": str(archive_path),
                "archive_type": "memvid_v2",
            }

        except Exception as e:
            logger.error("Error creating video archive: %s", e)
            return {"error": str(e), "archived_count": 0}

    def get_system_stats(self) -> Dict:
        """Get comprehensive system statistics (CHROMADB CONFLICT SAFE)"""
        try:
            stats = {
                "memvid_type": (
                    "v2_single_file" if REAL_MEMVID_AVAILABLE else "placeholder"
                ),
                "real_memvid_available": REAL_MEMVID_AVAILABLE,
                "active_memory": {},
                "archives": {},
                "total_archive_size_mb": 0,
                "chromadb_status": "connected",
            }

            # Safely get active memory stats
            try:
                stats["active_memory"] = {
                    "conversations": (
                        self.conversations.count() if self.conversations else 0
                    ),
                    "emotional_patterns": (
                        self.emotional_patterns.count()
                        if self.emotional_patterns
                        else 0
                    ),
                }
            except Exception as e:
                logger.error("Error getting active memory stats: %s", e)
                stats["active_memory"] = {"error": str(e)}
                stats["chromadb_status"] = "error"

            # Get archive stats
            for name, mv in self.video_archives.items():
                try:
                    archive_stats = mv.stats()
                    stats["archives"][name] = archive_stats

                    # Calculate file size
                    size_mb = archive_stats.get("size_bytes", 0) / (1024 * 1024)
                    stats["total_archive_size_mb"] += size_mb

                except Exception as e:
                    logger.error("Error getting stats for %s: %s", name, e)
                    stats["archives"][name] = {"error": str(e)}

            return stats

        except Exception as e:
            logger.error("Error getting system stats: %s", e)
            return {
                "error": str(e),
                "memvid_type": "error",
                "real_memvid_available": REAL_MEMVID_AVAILABLE,
            }

    def import_knowledge_to_video(self, source_path: str, archive_name: str) -> Dict:
        """
        Import external documents into REAL memvid v2 archive
        """
        if not REAL_MEMVID_AVAILABLE:
            return {
                "error": "Real memvid not available",
                "message": "Cannot create archives without real memvid",
            }

        try:
            # Create archive
            archive_path = self.memvid_video_path / f"{archive_name}.mv2"
            mv = memvid_sdk.create(str(archive_path), enable_vec=True, enable_lex=True)

            source = Path(source_path)

            if source.is_file():
                # For v2, we just use put() and it handles the extension
                mv.put(
                    title=source.name,
                    labels=["import"],
                    metadata={},
                    file=str(source),
                    embedding_model=self.embedding_model,
                )
            elif source.is_dir():
                logger.info("📁 Importing directory to archive: %s", source)
                for file_path in source.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in [
                        ".txt",
                        ".md",
                        ".pdf",
                    ]:
                        mv.put(
                            title=file_path.name,
                            labels=["import"],
                            metadata={},
                            file=str(file_path),
                            embedding_model=self.embedding_model,
                        )

            # Finalize
            mv.close()

            # Load into system
            self.video_archives[archive_name] = memvid_sdk.use(
                "basic", str(archive_path)
            )

            logger.info("🎥 Created knowledge base: %s.mv2", archive_name)

            return {
                "archive_name": archive_name,
                "archive_file": str(archive_path),
                "source": str(source),
                "archive_type": "memvid_v2",
            }

        except Exception as e:
            logger.error("Error creating video knowledge base: %s", e)
            return {"error": str(e)}

    def ask_archive(self, archive_name: str, question: str):
        """
        Ask a question to a specific archive using v2 ask() method
        """
        if not REAL_MEMVID_AVAILABLE:
            raise RuntimeError("Real memvid not available")

        if archive_name not in self.video_archives:
            raise ValueError(f"Archive '{archive_name}' not found")

        mv = self.video_archives[archive_name]
        return mv.ask(question)

    def list_video_archives(self) -> List[Dict]:
        """List all available archives with details"""
        archives = []

        for name, mv in self.video_archives.items():
            try:
                stats = mv.stats()
                archive_info = {
                    "name": name,
                    "file": f"{name}.mv2",
                    "frame_count": stats.get("frame_count", 0),
                    "size_mb": stats.get("size_bytes", 0) / (1024 * 1024),
                    "real_memvid": REAL_MEMVID_AVAILABLE,
                    "type": "memvid_v2",
                }
                archives.append(archive_info)
            except Exception as e:
                logger.error("Error getting info for archive %s: %s", name, e)

        return archives


# Global instance for MCP integration (CHROMADB CONFLICT SAFE)
_aura_real_memvid = None


def get_aura_real_memvid(existing_chroma_client=None):
    """
    Get or create the real memvid system instance
    FIXED: Now properly manages shared ChromaDB client to prevent conflicts
    """
    global _aura_real_memvid
    if _aura_real_memvid is None:
        _aura_real_memvid = AuraRealMemvid(
            existing_chroma_client=existing_chroma_client
        )
    elif (
        existing_chroma_client is not None
        and _aura_real_memvid.chroma_client != existing_chroma_client
    ):
        # Reset instance if a different client is provided to ensure consistency
        logger.info("🔄 Resetting memvid instance to use provided ChromaDB client")
        _aura_real_memvid = AuraRealMemvid(
            existing_chroma_client=existing_chroma_client
        )
    return _aura_real_memvid


def reset_aura_real_memvid():
    """Reset the global instance (useful for resolving conflicts)"""
    global _aura_real_memvid
    _aura_real_memvid = None
