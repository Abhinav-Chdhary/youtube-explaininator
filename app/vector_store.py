import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)
from app.config import settings


class VectorStore:
    """Qdrant vector database wrapper."""

    def __init__(self):
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        self.collection = settings.collection_name

    def ensure_collection(self):
        """Create collection if it doesn't exist."""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection not in collections:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dim,
                    distance=Distance.COSINE,
                ),
            )

    def upsert_chunks(
        self,
        embeddings: list[list[float]],
        chunks: list[dict],
        video_id: str,
        video_url: str,
    ):
        """Store embedded chunks with metadata."""
        points = []
        for emb, chunk in zip(embeddings, chunks):
            point_id = str(uuid.uuid4())
            points.append(
                PointStruct(
                    id=point_id,
                    vector=emb,
                    payload={
                        "text": chunk["text"],
                        "video_id": video_id,
                        "video_url": video_url,
                        "start_time": chunk["start_time"],
                        "end_time": chunk["end_time"],
                    },
                )
            )

        # Batch upsert in groups of 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=self.collection,
                points=points[i : i + batch_size],
            )

    def search(
        self,
        query_vector: list[float],
        video_id: str | None = None,
        top_k: int | None = None,
    ) -> list[dict]:
        """Search for similar chunks, optionally filtered by video_id."""
        search_filter = None
        if video_id:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="video_id",
                        match=MatchValue(value=video_id),
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            query_filter=search_filter,
            limit=top_k or settings.top_k,
        )

        return [
            {
                "text": r.payload["text"],
                "video_id": r.payload["video_id"],
                "video_url": r.payload["video_url"],
                "start_time": r.payload["start_time"],
                "end_time": r.payload["end_time"],
                "score": r.score,
            }
            for r in results.points
        ]

    def video_exists(self, video_id: str) -> bool:
        """Check if a video has already been ingested."""
        results = self.client.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="video_id",
                        match=MatchValue(value=video_id),
                    )
                ]
            ),
            limit=1,
        )
        return len(results[0]) > 0


vector_store = VectorStore()
