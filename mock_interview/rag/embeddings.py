import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

_model_cache = {}


class EmbeddingService:
    """BAAI/bge-m3 embedding generation service."""

    def __init__(self):
        config = settings.RAG_CONFIG
        self._model_name = config["EMBEDDING_MODEL"]
        self._dimension = config["EMBEDDING_DIMENSION"]
        self._model = self._load_model()

    def _load_model(self):
        """Load the embedding model, using cache to avoid reloading."""
        global _model_cache
        if self._model_name not in _model_cache:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading embedding model: %s", self._model_name)
                _model_cache[self._model_name] = SentenceTransformer(
                    self._model_name
                )
                logger.info("Embedding model loaded successfully.")
            except Exception as exc:
                logger.error("Failed to load embedding model: %s", exc)
                raise
        return _model_cache[self._model_name]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a single query text."""
        return self.embed_texts([query])[0]

    @property
    def dimension(self) -> int:
        return self._dimension

    def health(self) -> bool:
        """Check if the embedding model is loaded and functional."""
        try:
            test = self.embed_texts(["test"])
            return len(test) > 0 and len(test[0]) == self._dimension
        except Exception:
            return False
