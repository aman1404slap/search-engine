"""Heuristic query decomposition for compound queries like "walking while it rains".

Dense/keyword scoring against a single query vector treats a query as one bag
of meaning, so a segment that's strongly about only ONE half of a compound
query ("rain", no walking) can still score high -- there's no requirement
that all stated conditions actually co-occur. Splitting the query into
concept clauses and requiring every clause to score reasonably (via a min
across clauses, see ranking.hybrid_search) approximates AND semantics.

This is intentionally simple regex-based splitting, not real parsing -- it
handles "X while/during/when/and/then/after/before Y" patterns well and does
nothing (falls back to the whole query as one concept) on queries without a
connective.

"in" and "with" are deliberately NOT connectives here even though they can
join two independent conditions ("walking in rain"), because they're just as
commonly a plain preposition inside ONE descriptive clause ("people in the
kitchen", "person with a hammer") -- splitting those wrongly treats the
sentence's own subject/location as a separate required condition, and the
min()-across-concepts combination in ranking.hybrid_search then caps a
perfectly matching segment's score at whatever its weaker, spuriously-split
half achieves. The words kept below are far more reliably two-clause markers.
"""
import re

_CONNECTIVE_RE = re.compile(
    r"\b(?:while|during|when|and|then|after|before)\b|,", re.IGNORECASE
)
_MAX_CONCEPTS = 4
_MIN_CONCEPT_CHARS = 2


def decompose_query(query: str) -> list[str]:
    """Split into concept clauses; returns [query] unchanged if nothing to split."""
    query = (query or "").strip()
    if not query:
        return []

    fragments = [f.strip() for f in _CONNECTIVE_RE.split(query)]
    concepts = []
    seen = set()
    for frag in fragments:
        key = frag.lower()
        if len(frag) >= _MIN_CONCEPT_CHARS and key not in seen:
            seen.add(key)
            concepts.append(frag)

    if len(concepts) <= 1:
        return [query]

    return concepts[:_MAX_CONCEPTS]
