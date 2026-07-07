"""Hybrid (dense + keyword) search over segments, merged into per-video spans.

Two extra stages on top of the base dense+keyword fusion:

1. Query decomposition (apps.search.decomposition): compound queries are
   split into concept clauses, each clause is scored independently, and the
   per-segment fused score is the MIN across clauses -- a segment strong on
   only one clause of "walking while it rains" no longer scores as if it
   matched the whole query. Single-clause queries are unaffected (min of one
   value).
2. Cross-encoder reranking (apps.search.reranker): a generous shortlist of
   merged spans (settings.SEARCH_RERANK_POOL_SIZE, floored so it's always at
   least a few spans per requested video) gets a second, joint-attention
   relevance score from a cross-encoder, which can judge "does this segment
   actually satisfy the whole query" far better than comparing two
   independently-computed vectors. This runs *before* grouping by video and
   is sized so that in practice every span with a real shot at a top_k slot
   gets reranked -- otherwise some returned results would carry a
   cross-encoder sigmoid score and others the un-reranked min-max-normalized
   fusion score, two different scales rendered identically as "confidence" by
   the frontend. Only ever applied to that shortlist, so its cost doesn't
   grow with corpus size. Spans beyond the shortlist keep their stage-1 score
   and are appended after the reranked block, but shouldn't ordinarily
   surface within top_k.
"""
import re

import numpy as np
from django.conf import settings

from apps.search.decomposition import decompose_query
from apps.search.embedding import embed_query
from apps.search.index import get_segment_index

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _min_max_normalize(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores
    lo = scores.min()
    hi = scores.max()
    if hi == lo:
        return np.zeros_like(scores)
    return (scores - lo) / (hi - lo)


def _fused_scores_for_concept(concept_text: str, idx: dict, bm25) -> np.ndarray:
    query_vec = embed_query(concept_text)
    dense = idx["embeddings"] @ query_vec

    tokenized_query = _tokenize(concept_text)
    keyword = np.array(bm25.get_scores(tokenized_query), dtype=np.float64)

    dense_norm = _min_max_normalize(np.asarray(dense, dtype=np.float64))
    keyword_norm = _min_max_normalize(keyword)
    return settings.SEARCH_DENSE_WEIGHT * dense_norm + settings.SEARCH_KEYWORD_WEIGHT * keyword_norm


def hybrid_search(query_text: str, filters: dict, top_k: int = 20, min_confidence: float = 0.0) -> list[dict]:
    from apps.videos.filters import apply_video_filters
    from apps.videos.models import Video

    filters = filters or {}
    video_qs = apply_video_filters(Video.objects.all(), filters)
    video_ids = set(video_qs.values_list("shot_id", flat=True))

    # Empty filters -> no restriction (pass None). Non-empty filters that match
    # zero videos -> a real empty set, which should yield no results.
    index_filter = video_ids if filters else None
    idx = get_segment_index(video_ids=index_filter)

    n = len(idx["segment_ids"])
    if n == 0:
        return []

    # --- per-concept dense+keyword fusion, combined via min() for AND semantics ---
    from rank_bm25 import BM25Okapi

    tokenized_corpus = [_tokenize(t) for t in idx["texts"]]
    bm25 = BM25Okapi(tokenized_corpus)

    concepts = decompose_query(query_text) if settings.SEARCH_DECOMPOSE_QUERY else [query_text]
    concept_scores = np.vstack([_fused_scores_for_concept(c, idx, bm25) for c in concepts])
    fused = concept_scores.min(axis=0)

    keep_mask = fused >= min_confidence
    if not np.any(keep_mask):
        return []

    kept_indices = np.nonzero(keep_mask)[0]

    # --- group surviving segments by video, sort by start_s, merge nearby spans ---
    by_video = {}
    for i in kept_indices:
        vid = idx["video_ids"][i]
        by_video.setdefault(vid, []).append(
            {
                "start_s": idx["start_s"][i],
                "end_s": idx["end_s"][i],
                "text": idx["texts"][i],
                "fused": fused[i],
                "concept_scores": concept_scores[:, i],
            }
        )

    gap = settings.SEARCH_SPAN_MERGE_GAP_SECONDS
    spans = []

    for vid, segs in by_video.items():
        segs.sort(key=lambda s: s["start_s"])

        current = None
        for seg in segs:
            if current is None:
                current = {
                    "start_s": seg["start_s"],
                    "end_s": seg["end_s"],
                    "best_fused": seg["fused"],
                    "best_text": seg["text"],
                    "best_concept_scores": seg["concept_scores"],
                }
                continue

            if (seg["start_s"] - current["end_s"]) <= gap:
                current["start_s"] = min(current["start_s"], seg["start_s"])
                current["end_s"] = max(current["end_s"], seg["end_s"])
                if seg["fused"] > current["best_fused"]:
                    current["best_fused"] = seg["fused"]
                    current["best_text"] = seg["text"]
                    current["best_concept_scores"] = seg["concept_scores"]
            else:
                spans.append((vid, current))
                current = {
                    "start_s": seg["start_s"],
                    "end_s": seg["end_s"],
                    "best_fused": seg["fused"],
                    "best_text": seg["text"],
                    "best_concept_scores": seg["concept_scores"],
                }

        if current is not None:
            spans.append((vid, current))

    results = [
        {
            "video_id": vid,
            "start_s": float(span["start_s"]),
            "end_s": float(span["end_s"]),
            "confidence": round(float(span["best_fused"]), 3),
            "matched_text": span["best_text"],
            "concept_matches": [
                {"concept": c, "score": round(float(s), 3)}
                for c, s in zip(concepts, span["best_concept_scores"])
            ],
        }
        for vid, span in spans
    ]

    results.sort(key=lambda r: r["confidence"], reverse=True)

    if settings.SEARCH_RERANK_ENABLED and results:
        from apps.search.reranker import rerank

        # At least 4 spans per requested video so grouping (next step) has a
        # reranked span to pick from for essentially every video that could
        # plausibly make the final top_k, not just an arbitrary fixed count.
        n = max(settings.SEARCH_RERANK_POOL_SIZE, top_k * 4)
        head, tail = results[:n], results[n:]
        rerank_scores = rerank(query_text, [r["matched_text"] for r in head])
        for r, score in zip(head, rerank_scores):
            r["confidence"] = round(float(score), 3)
            r["reranked"] = True
        head.sort(key=lambda r: r["confidence"], reverse=True)
        # Reranked head and not-reranked tail use different score scales (cross-encoder
        # sigmoid vs. min-max-normalized fusion) so they're deliberately NOT re-sorted
        # together -- the reranked block always leads, in its own new order.
        results = head + tail

    return _group_by_video(results, top_k)


def _group_by_video(results: list[dict], top_k: int) -> list[dict]:
    """Collapse per-span results into one entry per video, since a video that
    matches in several disjoint timeframes should surface once in a result
    list, not once per timeframe. The video-level confidence is its
    best-matching span's; each span keeps its own confidence untouched.
    `top_k` now bounds the number of videos returned, not spans."""
    by_video = {}
    for r in results:
        by_video.setdefault(r["video_id"], []).append(r)

    grouped = []
    for video_id, spans in by_video.items():
        best = max(spans, key=lambda s: s["confidence"])
        grouped.append(
            {
                "video_id": video_id,
                "confidence": best["confidence"],
                "matched_text": best["matched_text"],
                "spans": sorted(spans, key=lambda s: s["start_s"]),
            }
        )

    grouped.sort(key=lambda r: r["confidence"], reverse=True)
    return grouped[:top_k]
