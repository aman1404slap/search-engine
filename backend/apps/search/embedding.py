"""Self-hosted sentence-embedding model, loaded once per process.

Used both by this app's own ranking pipeline and imported directly by the
ingestion app's Celery task (`compute_embeddings`) to embed segment text at
ingest time. Keep `embed_texts`'s signature stable -- other code depends on it.
"""
import numpy as np
from django.conf import settings

_model = None


def get_model():
    """Lazily construct and cache a SentenceTransformer in a module-level global."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Return L2-normalized float32 embeddings, shape (len(texts), EMBEDDING_DIM)."""
    if not texts:
        return np.zeros((0, settings.EMBEDDING_DIM), dtype=np.float32)

    model = get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return embeddings.astype(np.float32)


def embed_query(text: str) -> np.ndarray:
    """Return L2-normalized float32 embedding, shape (EMBEDDING_DIM,)."""
    return embed_texts([text])[0]
