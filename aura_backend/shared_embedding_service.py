"""
Shared Embedding Service for Aura
================================

Provides a centralized, cached embedding service to avoid reloading
SentenceTransformer models multiple times across different components.

This significantly improves performance and reduces GPU memory usage.
"""

import logging
import threading
from typing import List, Optional, Union

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class SharedEmbeddingService:
    """
    Singleton service that provides cached embedding functionality.

    This ensures only one SentenceTransformer model is loaded and shared
    across all components (main API, memvid, vector DB, etc.)
    """

    _instance: Optional["SharedEmbeddingService"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "SharedEmbeddingService":
        """Singleton pattern implementation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the embedding model (only once)"""
        if hasattr(self, "_initialized"):
            return

        self._model_name = "all-MiniLM-L6-v2"
        self._model: Optional[SentenceTransformer] = None
        self._model_lock = threading.Lock()
        self._initialized = True

        logger.info(
            f"🧠 SharedEmbeddingService initialized with model: {self._model_name}"
        )

    def _ensure_model_loaded(self) -> None:
        """Lazy load the model when first needed"""
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    logger.info("📚 Loading embedding model: %s", self._model_name)
                    self._model = SentenceTransformer(self._model_name)
                    logger.info("✅ Embedding model loaded successfully")

    def encode(
        self,
        texts: Union[str, List[str]],
        convert_to_tensor: bool = False,
        normalize_embeddings: bool = False,
    ) -> Union[np.ndarray, List[float]]:
        """
        Encode text(s) into embeddings using the shared model.

        Args:
            texts: Single text string or list of texts
            convert_to_tensor: Whether to return as tensor
            normalize_embeddings: Whether to normalize embeddings

        Returns:
            Embeddings as numpy array or list of floats
        """
        self._ensure_model_loaded()

        try:
            embeddings = self._model.encode(
                texts,
                convert_to_tensor=convert_to_tensor,
                normalize_embeddings=normalize_embeddings,
            )

            # Convert to list of floats for JSON serialization if needed
            if isinstance(texts, str) and not convert_to_tensor:
                return embeddings.tolist()
            elif not convert_to_tensor:
                return [emb.tolist() for emb in embeddings]

            return embeddings

        except Exception as e:
            logger.error("❌ Embedding encoding failed: %s", e)
            raise

    def encode_single(self, text: str) -> List[float]:
        """
        Convenience method to encode a single text and return as list.

        Args:
            text: Text to encode

        Returns:
            List of float values representing the embedding
        """
        return self.encode(text)

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Convenience method to encode multiple texts.

        Args:
            texts: List of texts to encode

        Returns:
            List of embeddings, each as a list of floats
        """
        return self.encode(texts)

    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        self._ensure_model_loaded()

        return {
            "model_name": self._model_name,
            "max_seq_length": getattr(self._model, "max_seq_length", "unknown"),
            "device": str(self._model.device) if self._model else "not_loaded",
            "embedding_dimension": (
                self._model.get_sentence_embedding_dimension()
                if self._model
                else "unknown"
            ),
        }

    def clear_cache(self) -> None:
        """Clear the model cache (for memory management)"""
        with self._model_lock:
            if self._model is not None:
                logger.info("🧹 Clearing embedding model cache")
                del self._model
                self._model = None


# Global instance - import this in other modules
embedding_service = SharedEmbeddingService()


def get_embedding_service() -> SharedEmbeddingService:
    """Get the global embedding service instance"""
    return embedding_service


# Convenience functions for backward compatibility
def encode_text(text: str) -> List[float]:
    """Encode a single text using the shared service"""
    return embedding_service.encode_single(text)


def encode_texts(texts: List[str]) -> List[List[float]]:
    """Encode multiple texts using the shared service"""
    return embedding_service.encode_batch(texts)
