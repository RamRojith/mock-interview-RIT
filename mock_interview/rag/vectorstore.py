import uuid
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    """Qdrant vector store client for document embeddings."""

    def __init__(self):
        from qdrant_client import QdrantClient
        from qdrant_client.models import (
            Distance,
            VectorParams,
            PointStruct,
            Filter,
            FieldCondition,
            MatchValue,
        )

        config = settings.RAG_CONFIG
        self._client = QdrantClient(url=config["QDRANT_URL"])
        self._collection = config["QDRANT_COLLECTION"]
        self._dimension = config["EMBEDDING_DIMENSION"]
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it does not exist."""
        from qdrant_client.models import Distance, VectorParams

        try:
            collections = self._client.get_collections().collections
            names = {c.name for c in collections}
            if self._collection not in names:
                self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=VectorParams(
                        size=self._dimension,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Created Qdrant collection: %s", self._collection)
        except Exception as exc:
            logger.warning("Could not ensure Qdrant collection: %s", exc)

    def upsert_chunks(
        self,
        chunk_ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict],
    ):
        """Insert or update chunk embeddings with metadata payloads."""
        from qdrant_client.models import PointStruct

        points = [
            PointStruct(
                id=chunk_ids[i],
                vector=vectors[i],
                payload=payloads[i],
            )
            for i in range(len(chunk_ids))
        ]
        self._client.upsert(
            collection_name=self._collection,
            points=points,
        )

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        metadata_filters: Optional[dict] = None,
    ) -> list[dict]:
        """Search for similar chunks with optional metadata filtering."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        query_filter = None
        if metadata_filters:
            conditions = []
            for key, value in metadata_filters.items():
                if value is not None:
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
            if conditions:
                query_filter = Filter(must=conditions)

        results = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=top_k,
            query_filter=query_filter,
        )
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload or {},
            }
            for hit in results.points
        ]

    def delete_by_document(self, document_id: str):
        """Delete all chunks belonging to a specific document."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
        )

    def health(self) -> bool:
        """Check if Qdrant is reachable."""
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False
