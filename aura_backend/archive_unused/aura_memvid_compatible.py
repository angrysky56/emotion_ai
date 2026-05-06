"""
Memvid-Compatible Archive System for Aura
A simplified implementation that provides memvid-like functionality
without dependency conflicts
"""

import json
import logging
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

class AuraArchiveEncoder:
    """
    Simplified archive encoder that compresses memory data
    Uses compression instead of video encoding for compatibility
    """

    def __init__(self):
        self.chunks = []
        self.metadata = []

    def add_text(self, text: str, metadata: Optional[Dict] = None):
        """Add text chunk with metadata"""
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

        # Create embedding model
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Generate embeddings for all chunks
        embeddings = embedding_model.encode(self.chunks)

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

        # Create search index (SQLite)
        index_db = sqlite3.connect(index_path)
        cursor = index_db.cursor()

        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY,
                text TEXT,
                embedding BLOB,
                metadata TEXT
            )
        ''')

        # Insert data
        for i, (chunk, metadata, embedding) in enumerate(zip(
            self.chunks, self.metadata, embeddings
        )):
            cursor.execute(
                "INSERT INTO chunks (id, text, embedding, metadata) VALUES (?, ?, ?, ?)",
                (i, chunk, embedding.tobytes(), json.dumps(metadata))
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
            "compression_ratio": original_size / compressed_size if compressed_size > 0 else 0
        }

class AuraArchiveRetriever:
    """
    Archive retriever for compressed memory archives
    """

    def __init__(self, archive_path: str, index_path: str):
        self.archive_path = Path(archive_path)
        self.index_path = Path(index_path)

        # Load archive data
        with gzip.open(self.archive_path, 'rb') as f:
            self.archive_data = pickle.load(f)

        # Load embeddings
        self.embeddings = np.array(self.archive_data["embeddings"])

        # Create embedding model for queries
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        logger.info("Loaded archive with %s chunks", len(self.archive_data['chunks']))

    def search(self, query: str, max_results: int = 5) -> List[str]:
        """Search archive for relevant chunks"""

        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])

        # Calculate similarities
        similarities = np.dot(self.embeddings, query_embedding.T).flatten()

        # Get top results
        top_indices = np.argsort(similarities)[::-1][:max_results]

        results = []
        for idx in top_indices:
            results.append(self.archive_data["chunks"][idx])

        return results

    def search_with_metadata(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search with full metadata"""

        query_embedding = self.embedding_model.encode([query])
        similarities = np.dot(self.embeddings, query_embedding.T).flatten()
        top_indices = np.argsort(similarities)[::-1][:max_results]

        results = []
        for idx in top_indices:
            results.append({
                "text": self.archive_data["chunks"][idx],
                "score": float(similarities[idx]),
                "metadata": self.archive_data["metadata"][idx],
                "chunk_id": int(idx)
            })

        return results

    def get_stats(self) -> Dict:
        """Get archive statistics"""
        return {
            "total_chunks": len(self.archive_data["chunks"]),
            "archive_file": str(self.archive_path),
            "index_file": str(self.index_path),
            "created": self.archive_data.get("created", "unknown"),
            "version": self.archive_data.get("version", "unknown")
        }

class AuraMemvidCompatible:
    """
    Memvid-compatible memory system for Aura
    Integrates with existing ChromaDB while providing archival capabilities
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
        """
        results = {
            "query": query,
            "user_id": user_id,
            "active_results": [],
            "archive_results": [],
            "total_results": 0
        }

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
            logger.error("Error searching active memory: %s", e)

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
                logger.error("Error searching archive %s: %s", archive_name, e)

        results["total_results"] = len(results["active_results"]) + len(results["archive_results"])
        return results

    def archive_old_conversations(self, user_id: Optional[str] = None) -> Dict:
        """
        Archive old conversations to compressed format
        """
        try:
            # Get old conversations from ChromaDB
            cutoff_date = datetime.now() - timedelta(days=self.active_memory_days)

            # Note: This is a simplified approach
            # In production, you'd want to properly filter by date
            all_conversations = self.conversations.get(
                include=["documents", "metadatas"]
            )

            # Get IDs separately
            all_ids = self.conversations.get(
                include=[]
            )["ids"]

            if not all_conversations["documents"]:
                return {"archived_count": 0, "message": "No conversations to archive"}

            # Create archive
            archive_name = f"aura_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            encoder = AuraArchiveEncoder()

            conversations_to_archive = []
            ids_to_delete = []

            for i, doc in enumerate(all_conversations["documents"]):
                metadata = all_conversations["metadatas"][i] if all_conversations["metadatas"] else {}
                doc_id = all_ids[i] if all_ids and i < len(all_ids) else f"doc_{i}"

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

            # Delete from ChromaDB
            if ids_to_delete:
                self.conversations.delete(ids=ids_to_delete)

            logger.info("Archived %s conversations to %s", len(conversations_to_archive), archive_name)

            return {
                "archived_count": len(conversations_to_archive),
                "archive_name": archive_name,
                "compression_ratio": build_stats["compression_ratio"],
                "compressed_size_mb": build_stats["compressed_size_mb"]
            }

        except Exception as e:
            logger.error("Error archiving conversations: %s", e)
            return {"error": str(e), "archived_count": 0}

    def import_knowledge_base(self, source_path: str, archive_name: str) -> Dict:
        """
        Import external documents into compressed archive
        """
        try:
            encoder = AuraArchiveEncoder()
            source = Path(source_path)

            if source.is_file():
                if source.suffix.lower() in [".txt", ".md"]:
                    with open(source, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Split into chunks
                        chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
                        for chunk in chunks:
                            encoder.add_text(chunk, {"source": str(source)})

            elif source.is_dir():
                for file_path in source.rglob("*.txt"):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
                        for chunk in chunks:
                            encoder.add_text(chunk, {"source": str(file_path)})

            # Build archive
            archive_path = self.archive_path / f"{archive_name}.dat"
            index_path = self.archive_path / f"{archive_name}.db"

            build_stats = encoder.build_archive(str(archive_path), str(index_path))

            # Load archive
            self.archives[archive_name] = AuraArchiveRetriever(
                build_stats["archive_path"], build_stats["index_path"]
            )

            return {
                "archive_name": archive_name,
                "chunks_imported": build_stats["total_chunks"],
                "compressed_size_mb": build_stats["compressed_size_mb"],
                "compression_ratio": build_stats["compression_ratio"]
            }

        except Exception as e:
            logger.error("Error importing knowledge base: %s", e)
            return {"error": str(e)}

    def get_system_stats(self) -> Dict:
        """Get system statistics"""
        stats = {
            "active_memory": {
                "conversations": self.conversations.count(),
                "emotional_patterns": self.emotional_patterns.count()
            },
            "archives": {},
            "archive_compatible": True
        }

        for name, retriever in self.archives.items():
            archive_stats = retriever.get_stats()
            stats["archives"][name] = archive_stats

        return stats

# Global instance for integration
_aura_memvid_compatible = None

def get_aura_memvid_compatible():
    """Get or create the compatible system instance"""
    global _aura_memvid_compatible
    if _aura_memvid_compatible is None:
        _aura_memvid_compatible = AuraMemvidCompatible()
    return _aura_memvid_compatible
