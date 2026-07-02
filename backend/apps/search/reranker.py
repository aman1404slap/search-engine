"""Cross-encoder reranking of the top-N stage-1 candidates.

Unlike the bi-encoder in embedding.py (query and document embedded
independently, compared via cosine similarity), a cross-encoder scores a
(query, document) pair jointly -- it can actually judge whether a passage
satisfies a compound condition rather than just being "close" to it in
vector space. That joint attention means scores can't be precomputed per
segment, so this only ever runs on a small shortlist, never the full corpus.
"""
import numpy as np
from django.conf import settings

_model = None


def get_cross_encoder():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder

        _model = CrossEncoder(settings.SEARCH_RERANK_MODEL_NAME)
    return _model


def rerank(query: str, texts: list[str]) -> list[float]:
    """Returns one score per text, roughly in [0, 1] (sigmoid of the model's raw logit)."""
    if not texts:
        return []
    model = get_cross_encoder()
    raw_scores = np.asarray(model.predict([(query, t) for t in texts]), dtype=np.float64)
    return (1.0 / (1.0 + np.exp(-raw_scores))).tolist()
