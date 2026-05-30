"""Local embedding generation via fastembed (ONNX, CPU, no torch).

The model is downloaded once on first use and cached on disk. Document and query
embeddings use the model's respective methods so asymmetric models (e.g. bge) work right.
"""

from __future__ import annotations

import logging
import time
from functools import lru_cache

from app.core.config import settings
from app.core.logging_config import log_event

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model
        self._model = None

    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding

            logger.info("loading embedding model: %s", self.model_name)
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load()
        start = time.perf_counter()
        vectors = [[float(x) for x in vec] for vec in model.embed(texts)]
        log_event(
            logger,
            "embed.documents",
            count=len(vectors),
            dim=len(vectors[0]) if vectors else 0,
            ms=round((time.perf_counter() - start) * 1000, 1),
        )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        model = self._load()
        vec = next(iter(model.query_embed(text)))
        return [float(x) for x in vec]


@lru_cache
def get_embedder() -> Embedder:
    return Embedder()
