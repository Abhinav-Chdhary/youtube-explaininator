import asyncio
import numpy as np
from sentence_transformers import SentenceTransformer
from app.config import settings


class EmbeddingModel:
    """Local bge-m3 multilingual embedding model."""

    def __init__(self):
        self._model: SentenceTransformer | None = None

    def _load(self):
        if self._model is None:
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    def encode_sync(self, texts: list[str]) -> np.ndarray:
        """Encode texts to dense vectors (blocking)."""
        model = self._load()
        return model.encode(texts, normalize_embeddings=True)

    async def encode(self, texts: list[str]) -> np.ndarray:
        """Async wrapper — runs encoding in a thread pool."""
        return await asyncio.to_thread(self.encode_sync, texts)

    @property
    def dim(self) -> int:
        return settings.embedding_dim


embedding_model = EmbeddingModel()
