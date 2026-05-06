"""
Memvid-Compatible Archive System for Aura (FIXED VERSION)
A simplified implementation that provides memvid-like functionality
without dependency conflicts

FIXES:
- Database ID conflicts resolved
- Large input handling improved
- Memory usage optimized
- Error handling enhanced
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import sqlite3
import pickle
import gzip

# Core dependencies that Aura already has
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Configuration limits
MAX_CHUNK_SIZE = 2000  # Increased from 1000
MAX_CHUNKS_PER_BATCH = 100  # Limit batch size
MAX_TOTAL_CHUNKS = 10000  # Limit total chunks to prevent memory issues

class AuraArchiveEncoder:
    """
    Simplified archive encoder that compresses memory data
    Uses compression instead of video encoding for compatibility
    FIXED: Better ID handling and large data support
    """

    def __init__(self):
        self.chunks = []
        self.metadata = []

    def add_text(self, text: str, metadata: Optional[Dict] = None):
        """Add text chunk with metadata"""
        if len(self.chunks) >= MAX_TOTAL_CHUNKS:
            logger.warning("Reached maximum chunk limit (%s), skipping additional chunks", MAX_TOTAL_CHUNKS)
            return

        chunk_id = len(self.chunks)

        self.chunks.append(text)
        self.metadata.append({
            "chunk_id": chunk_id,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {})
        })

    def build_archive(self, archive_path: str, index_path: str) -> Dict:
        """Build compressed archive with search index"""

        if not self.chunks:
            raise ValueError("No chunks to archive")

        try:
            # Create embedding model
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

            # Generate embeddings in batches to handle large datasets
            embeddings = []
            batch_size = MAX_CHUNKS_PER_BATCH

            for i in range(0, len(self.chunks), batch_size):
                batch_chunks = self.chunks[i:i+batch_size]
                batch_embeddings = embedding_model.encode(batch_chunks)
                embeddings.extend(batch_embeddings)
                logger.info("Processed embedding batch %s/%s", i//batch_size + 1, (len(self.chunks) + batch_size - 1)//batch_size)

            embeddings = np.array(embeddings)

            # Create archive data
            archive_data = {
                "chunks": self.chunks,
                "metadata": self.metadata,
                "embeddings": embeddings.tolist(),
                "created": datetime.now().isoformat(),
                "version": "1.0.0"
            }

            # Compress and save archive
            archive_path_obj = Path(archive_path)
            with gzip.open(archive_path_obj.with_suffix('.gz'), 'wb') as f:
                pickle.dump(archive_data, f)

            # Create search index (SQLite) - FIXED: Use unique IDs per archive
            index_db = sqlite3.connect(index_path)
            cursor = index_db.cursor()

            # Create tables with better schema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    text TEXT,
                    embedding BLOB,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Generate unique IDs using hash + timestamp to avoid conflicts
            base_id = hashlib.md5(f"{archive_path}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]

            # Insert data with unique IDs
            for i, (chunk, metadata, embedding) in enumerate(zip(
                self.chunks, self.metadata, embeddings
            )):
                unique_id = f"{base_id}_{i:06d}"  # Format: hash_000001, hash_000002, etc.

                cursor.execute(
                    "INSERT OR REPLACE INTO chunks (id, text, embedding, metadata) VALUES (?, ?, ?, ?)",
                    (unique_id, chunk, embedding.tobytes(), json.dumps(metadata))
                )

            index_db.commit()
            index_db.close()

            # Statistics
            original_size = sum(len(chunk.encode('utf-8')) for chunk in self.chunks)
            compressed_size = archive_path_obj.with_suffix('.gz').stat().st_size

            return {
                "archive_path": str(archive_path_obj.with_suffix('.gz')),
                "index_path": str(index_path),
                "total_chunks": len(self.chunks),
                "original_size_mb": original_size / (1024 * 1024),
                "compressed_size_mb": compressed_size / (1024 * 1024),
                "compression_ratio": original_size / compressed_size if compressed_size > 0 else 0,
                "base_id": base_id
            }

        except Exception as e:
            logger.error("Failed to build archive: %s", e)
            raise

class AuraArchiveRetriever:
    """
    Archive retriever for compressed memory archives
    FIXED: Better memory management and error handling
    """

    def __init__(self, archive_path: str, index_path: str):
        self.archive_path = Path(archive_path)
        self.index_path = Path(index_path)

        try:
            # Load archive data
            with gzip.open(self.archive_path, 'rb') as f:
                self.archive_data = pickle.load(f)

            # Load embeddings (with memory optimization)
            embeddings_list = self.archive_data["embeddings"]
            self.embeddings = np.array(embeddings_list, dtype=np.float32)  # Use float32 to save memory

            # Create embedding model for queries
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

            logger.info("Loaded archive with %s chunks", len(self.archive_data['chunks']))

        except Exception as e:
            logger.error("Failed to load archive %s: %s", archive_path, e)
            raise

    def search(self, query: str, max_results: int = 5) -> List[str]:
        """Search archive for relevant chunks"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])

            # Calculate similarities (optimized for large datasets)
            similarities = np.dot(self.embeddings, query_embedding.T).flatten()

            # Get top results
            top_indices = np.argsort(similarities)[::-1][:max_results]

            results = []
            for idx in top_indices:
                if idx < len(self.archive_data["chunks"]):
                    results.append(self.archive_data["chunks"][idx])

            return results

        except Exception as e:
            logger.error("Failed to search archive: %s", e)
            return []

    def search_with_metadata(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search with full metadata"""
        try:
            query_embedding = self.embedding_model.encode([query])
            similarities = np.dot(self.embeddings, query_embedding.T).flatten()
            top_indices = np.argsort(similarities)[::-1][:max_results]

            results = []
            for idx in top_indices:
                if idx < len(self.archive_data["chunks"]):
                    results.append({
                        "text": self.archive_data["chunks"][idx],
                        "score": float(similarities[idx]),
                        "metadata": self.archive_data["metadata"][idx],
                        "chunk_id": int(idx)
                    })

            return results

        except Exception as e:
            logger.error("Failed to search archive with metadata: %s", e)
            return []

    def get_stats(self) -> Dict:
        """Get archive statistics"""
        return {
            "total_chunks": len(self.archive_data["chunks"]),
            "archive_file": str(self.archive_path),
            "index_file": str(self.index_path),
            "created": self.archive_data.get("created", "unknown"),
            "version": self.archive_data.get("version", "unknown"),
            "memory_usage_mb": self.embeddings.nbytes / (1024 * 1024)
        }

class AuraMemvidCompatible:
    """
    Memvid-compatible memory system for Aura
    FIXED: Better error handling and large data support
    """

    def __init__(self,
                 aura_chroma_path: str = "./aura_chroma_db",
                 archive_path: str = "./aura_archives",
                 active_memory_days: int = 30):

        self.aura_chroma_path = Path(aura_chroma_path)
        self.archive_path = Path(archive_path)
        self.active_memory_days = active_memory_days

        # Create archive directory
        self.archive_path.mkdir(exist_ok=True)

        try:
            # Initialize ChromaDB connection to existing Aura collections
            import chromadb
            from chromadb.config import Settings

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

            # Load existing archives
            self.archives = {}
            self._load_existing_archives()

            # Embedding model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        except Exception as e:
            logger.error("Failed to initialize AuraMemvidCompatible: %s", e)
            raise

    def _load_existing_archives(self):
        """Load existing compressed archives"""
        for archive_file in self.archive_path.glob("*.gz"):
            index_file = archive_file.with_suffix('.db')
            if index_file.exists():
                archive_name = archive_file.stem
                try:
                    self.archives[archive_name] = AuraArchiveRetriever(
                        str(archive_file), str(index_file)
                    )
                    logger.info("Loaded archive: %s", archive_name)
                except Exception as e:
                    logger.error("Failed to load archive %s: %s", archive_name, e)

    def search_unified(self, query: str, user_id: str, max_results: int = 10) -> Dict:
        """
        Unified search across active ChromaDB and compressed archives
        FIXED: Better error handling and result limiting
        """
        results = {
            "query": query,
            "user_id": user_id,
            "active_results": [],
            "archive_results": [],
            "total_results": 0,
            "errors": []
        }

        # Limit max_results to prevent memory issues
        max_results = min(max_results, 50)

        # Search active memory (ChromaDB)
        try:
            query_embedding = self.embedding_model.encode(query).tolist()

            active_search = self.conversations.query(
                query_embeddings=[query_embedding],
                n_results=max_results // 2,
                where={"user_id": user_id},
                include=["documents", "metadatas", "distances"]
            )

            if active_search["documents"] and active_search["documents"][0]:
                for i, doc in enumerate(active_search["documents"][0]):
                    metadata = active_search["metadatas"][0][i] if active_search["metadatas"] and active_search["metadatas"][0] else {}
                    distance = active_search["distances"][0][i] if active_search["distances"] and active_search["distances"][0] else 0
                    results["active_results"].append({
                        "text": doc,
                        "metadata": metadata,
                        "distance": distance,
                        "source": "active_memory",
                        "score": 1 - distance
                    })

        except Exception as e:
            error_msg = f"Error searching active memory: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        # Search archives
        for archive_name, retriever in self.archives.items():
            try:
                archive_results = retriever.search_with_metadata(query, max_results // 4)
                for result in archive_results:
                    results["archive_results"].append({
                        "text": result["text"],
                        "score": result["score"],
                        "source": f"archive:{archive_name}",
                        "chunk_id": result["chunk_id"],
                        "metadata": result["metadata"]
                    })
            except Exception as e:
                error_msg = f"Error searching archive {archive_name}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        results["total_results"] = len(results["active_results"]) + len(results["archive_results"])
        return results

    def import_knowledge_base(self, source_path: str, archive_name: str) -> Dict:
        """
        Import external documents into compressed archive
        FIXED: Better file handling and size limits
        """
        try:
            encoder = AuraArchiveEncoder()
            source = Path(source_path)
            total_chunks = 0

            if source.is_file():
                if source.suffix.lower() in [".txt", ".md"]:
                    with open(source, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                        # Limit content size to prevent memory issues
                        max_content_size = 10 * 1024 * 1024  # 10 MB limit
                        if len(content) > max_content_size:
                            logger.warning("Content size (%s chars) exceeds limit, truncating", len(content))
                            content = content[:max_content_size]

                        # Split into chunks with better size management
                        chunks = [content[i:i+MAX_CHUNK_SIZE] for i in range(0, len(content), MAX_CHUNK_SIZE)]
                        for chunk in chunks[:MAX_TOTAL_CHUNKS]:  # Limit total chunks
                            encoder.add_text(chunk, {"source": str(source)})
                            total_chunks += 1

            elif source.is_dir():
                files_processed = 0
                max_files = 100  # Limit number of files to process

                for file_path in source.rglob("*.txt"):
                    if files_processed >= max_files:
                        logger.warning("Reached file limit (%s), stopping processing", max_files)
                        break

                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()

                            # Limit file size
                            if len(content) > 1024 * 1024:  # 1 MB per file limit
                                content = content[:1024 * 1024]

                            chunks = [content[i:i+MAX_CHUNK_SIZE] for i in range(0, len(content), MAX_CHUNK_SIZE)]
                            for chunk in chunks:
                                if total_chunks >= MAX_TOTAL_CHUNKS:
                                    break
                                encoder.add_text(chunk, {"source": str(file_path)})
                                total_chunks += 1

                        files_processed += 1

                    except Exception as e:
                        logger.warning("Failed to process file %s: %s", file_path, e)
                        continue

            if not encoder.chunks:
                return {"error": "No valid content found to import", "archive_name": archive_name}

            # Build archive with unique naming to avoid conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_archive_name = f"{archive_name}_{timestamp}"
            archive_path = self.archive_path / f"{unique_archive_name}.dat"
            index_path = self.archive_path / f"{unique_archive_name}.db"

            build_stats = encoder.build_archive(str(archive_path), str(index_path))

            # Load archive
            self.archives[unique_archive_name] = AuraArchiveRetriever(
                build_stats["archive_path"], build_stats["index_path"]
            )

            return {
                "archive_name": unique_archive_name,
                "chunks_imported": build_stats["total_chunks"],
                "compressed_size_mb": build_stats["compressed_size_mb"],
                "compression_ratio": build_stats["compression_ratio"],
                "original_name": archive_name
            }

        except Exception as e:
            logger.error("Error importing knowledge base: %s", e)
            return {"error": str(e), "archive_name": archive_name}

    def archive_old_conversations(self, user_id: Optional[str] = None) -> Dict:
        """
        Archive old conversations to compressed format
        FIXED: Better handling of large datasets
        """
        try:
            # Get old conversations from ChromaDB
            cutoff_date = datetime.now() - timedelta(days=self.active_memory_days)

            # Get conversations in batches to handle large datasets
            batch_size = 1000  # Process in smaller batches
            all_conversations = []
            all_ids = []

            try:
                # Try to get all at once first
                conversation_data = self.conversations.get(
                    include=["documents", "metadatas"],
                    limit=batch_size
                )

                id_data = self.conversations.get(
                    include=[],
                    limit=batch_size
                )

                all_conversations = conversation_data.get("documents", [])
                all_ids = id_data.get("ids", [])

            except Exception as e:
                logger.warning("Failed to get conversations in batch: %s", e)
                return {"archived_count": 0, "message": "Failed to access conversations", "error": str(e)}

            if not all_conversations:
                return {"archived_count": 0, "message": "No conversations to archive"}

            # Create archive
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_name = f"aura_archive_{timestamp}"
            encoder = AuraArchiveEncoder()

            conversations_to_archive = []
            ids_to_delete = []

            for i, doc in enumerate(all_conversations):
                if i >= len(all_ids):
                    break

                metadatas_list = conversation_data.get("metadatas", [])
                metadata = metadatas_list[i] if metadatas_list and i < len(metadatas_list) else {}
                doc_id = all_ids[i]

                # Check if this should be archived (simplified logic)
                timestamp_str = metadata.get('timestamp', '')
                if timestamp_str and isinstance(timestamp_str, str):
                    try:
                        doc_timestamp = datetime.fromisoformat(timestamp_str)
                        if doc_timestamp < cutoff_date:
                            # Archive this conversation
                            encoder.add_text(doc, dict(metadata) if metadata else None)
                            conversations_to_archive.append(doc_id)
                            ids_to_delete.append(doc_id)
                    except (ValueError, TypeError):
                        pass  # Skip invalid timestamps

            if not conversations_to_archive:
                return {"archived_count": 0, "message": "No old conversations found"}

            # Build archive
            archive_path = self.archive_path / f"{archive_name}.dat"
            index_path = self.archive_path / f"{archive_name}.db"

            build_stats = encoder.build_archive(str(archive_path), str(index_path))

            # Load new archive
            self.archives[archive_name] = AuraArchiveRetriever(
                build_stats["archive_path"], build_stats["index_path"]
            )

            # Delete from ChromaDB in batches
            delete_batch_size = 100
            deleted_count = 0
            for i in range(0, len(ids_to_delete), delete_batch_size):
                batch_ids = ids_to_delete[i:i+delete_batch_size]
                try:
                    self.conversations.delete(ids=batch_ids)
                    deleted_count += len(batch_ids)
                except Exception as e:
                    logger.error("Failed to delete batch %s: %s", i//delete_batch_size + 1, e)

            logger.info("Archived %s conversations to %s", len(conversations_to_archive), archive_name)

            return {
                "archived_count": len(conversations_to_archive),
                "deleted_count": deleted_count,
                "archive_name": archive_name,
                "compression_ratio": build_stats["compression_ratio"],
                "compressed_size_mb": build_stats["compressed_size_mb"]
            }

        except Exception as e:
            logger.error("Error archiving conversations: %s", e)
            return {"error": str(e), "archived_count": 0}

    def get_system_stats(self) -> Dict:
        """Get system statistics"""
        try:
            stats = {
                "active_memory": {
                    "conversations": self.conversations.count() if hasattr(self.conversations, 'count') else 0,
                    "emotional_patterns": self.emotional_patterns.count() if hasattr(self.emotional_patterns, 'count') else 0
                },
                "archives": {},
                "archive_compatible": True,
                "system_limits": {
                    "max_chunk_size": MAX_CHUNK_SIZE,
                    "max_chunks_per_batch": MAX_CHUNKS_PER_BATCH,
                    "max_total_chunks": MAX_TOTAL_CHUNKS
                }
            }

            total_archive_size = 0
            for name, retriever in self.archives.items():
                try:
                    archive_stats = retriever.get_stats()
                    stats["archives"][name] = archive_stats
                    total_archive_size += archive_stats.get("memory_usage_mb", 0)
                except Exception as e:
                    logger.error("Failed to get stats for archive %s: %s", name, e)
                    stats["archives"][name] = {"error": str(e)}

            stats["total_archive_memory_mb"] = total_archive_size
            return stats

        except Exception as e:
            logger.error("Failed to get system stats: %s", e)
            return {"error": str(e), "archive_compatible": False}

# Global instance for integration
_aura_memvid_compatible = None

def get_aura_memvid_compatible():
    """Get or create the compatible system instance"""
    global _aura_memvid_compatible
    if _aura_memvid_compatible is None:
        _aura_memvid_compatible = AuraMemvidCompatible()
    return _aura_memvid_compatible
