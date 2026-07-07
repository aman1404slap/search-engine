"""In-memory vector index over all embedded segments.

The index (numpy arrays + parallel lists) is cached in this process's memory.
Redis only stores a small integer "version" used to know when to invalidate --
the ingestion pipeline calls `bump_version()` after writing new embeddings, and
the next `get_segment_index()` call in *this* process notices the version
changed and rebuilds from the DB.

Embeddings are stored in Postgres as a real pgvector column (see
apps.videos.models.Segment.embedding), not raw bytes -- pgvector-django hands
back each row's embedding as a numpy float32 array already, so no manual
struct packing/unpacking is needed here. Query-time scoring still does exact
brute-force cosine over this in-memory array (rather than pgvector's ANN
index) because the ranking fusion in apps.search.ranking needs full-pool score
statistics (min-max normalization across every filtered candidate), not just
an approximate top-K neighbor list -- at this corpus size that's cheap enough
to keep exact.
"""
import numpy as np
from django.conf import settings
from django.core.cache import cache

SEARCH_INDEX_VERSION_CACHE_KEY = "search_index_version"

_cached_index = None
_cached_version = None


def bump_version():
    """Invalidate the in-memory index for all processes by incrementing the shared version."""
    try:
        cache.incr(SEARCH_INDEX_VERSION_CACHE_KEY)
    except ValueError:
        cache.set(SEARCH_INDEX_VERSION_CACHE_KEY, 1)


def _empty_index():
    return {
        "segment_ids": [],
        "video_ids": [],
        "start_s": np.zeros((0,), dtype=np.float64),
        "end_s": np.zeros((0,), dtype=np.float64),
        "texts": [],
        "confidences": np.zeros((0,), dtype=np.float64),
        "embeddings": np.zeros((0, settings.EMBEDDING_DIM), dtype=np.float32),
    }


def _build_index():
    from apps.videos.models import Segment

    segment_ids = []
    video_ids = []
    start_s = []
    end_s = []
    texts = []
    confidences = []
    embeddings = []

    qs = Segment.objects.filter(embedding__isnull=False).values(
        "segment_id", "video_id", "start_s", "end_s", "text", "confidence", "embedding"
    )
    for row in qs:
        vec = row["embedding"]
        if vec is None or vec.shape[0] != settings.EMBEDDING_DIM:
            # Skip missing/malformed/mismatched-dimension rows rather than corrupting the index.
            continue
        segment_ids.append(row["segment_id"])
        video_ids.append(row["video_id"])
        start_s.append(row["start_s"])
        end_s.append(row["end_s"])
        texts.append(row["text"])
        confidences.append(row["confidence"])
        embeddings.append(vec)

    if not embeddings:
        return _empty_index()

    return {
        "segment_ids": segment_ids,
        "video_ids": video_ids,
        "start_s": np.array(start_s, dtype=np.float64),
        "end_s": np.array(end_s, dtype=np.float64),
        "texts": texts,
        "confidences": np.array(confidences, dtype=np.float64),
        "embeddings": np.stack(embeddings).astype(np.float32),
    }


def _filter_index(index, video_ids):
    video_id_set = set(video_ids)
    mask = np.array([vid in video_id_set for vid in index["video_ids"]], dtype=bool)

    if mask.size == 0:
        return _empty_index()

    return {
        "segment_ids": [sid for sid, keep in zip(index["segment_ids"], mask) if keep],
        "video_ids": [vid for vid, keep in zip(index["video_ids"], mask) if keep],
        "start_s": index["start_s"][mask],
        "end_s": index["end_s"][mask],
        "texts": [t for t, keep in zip(index["texts"], mask) if keep],
        "confidences": index["confidences"][mask],
        "embeddings": index["embeddings"][mask],
    }


def get_segment_index(video_ids=None):
    """
    Return the cached in-memory segment index, rebuilding it if the Redis-backed
    version counter has changed since it was last built. If `video_ids` is given,
    return a filtered view restricted to those video pks (no DB hit for the filter).
    """
    global _cached_index, _cached_version

    current_version = cache.get(SEARCH_INDEX_VERSION_CACHE_KEY)

    if _cached_index is None or current_version != _cached_version:
        _cached_index = _build_index()
        _cached_version = current_version

    index = _cached_index

    if video_ids is not None:
        index = _filter_index(index, video_ids)

    return index
