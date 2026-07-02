"""Shared, request-agnostic video filtering helpers.

`apply_video_filters` is imported directly by the search app (and used by the
views in this app), so it deliberately takes a plain dict rather than an
HttpRequest/QueryDict -- callers can build that dict from query params, a
JSON POST body, or anywhere else.
"""

from apps.videos.constants import MULTI_SELECT_FACETS, SINGLE_SELECT_FACETS


def _as_list(value):
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def apply_video_filters(queryset, params: dict):
    """Apply single-select, request_confidence, and multi-select facet filters.

    `params` keys are facet names; values are either a single string or a
    list/tuple of strings. Unrecognized keys are ignored.
    """
    for key in SINGLE_SELECT_FACETS:
        if key in params:
            values = _as_list(params[key])
            queryset = queryset.filter(**{f"{key}__in": values})

    if "request_confidence" in params:
        values = _as_list(params["request_confidence"])
        queryset = queryset.filter(request_confidence__in=values)

    for key in MULTI_SELECT_FACETS:
        if key in params:
            values = _as_list(params[key])
            queryset = queryset.filter(tags__facet=key, tags__value__in=values)
            queryset = queryset.distinct()

    return queryset


def normalize_query_params(query_params) -> dict:
    """Convert a QueryDict-like object into the plain-dict shape `apply_video_filters` expects.

    - MULTI_SELECT_FACETS: uses .getlist(key) (supports repeated ?key=a&key=b)
    - SINGLE_SELECT_FACETS + "request_confidence": uses .get(key) (single value)

    Only keys that are actually present/non-empty are included.
    """
    result = {}

    for key in MULTI_SELECT_FACETS:
        values = query_params.getlist(key)
        if values:
            result[key] = values

    for key in SINGLE_SELECT_FACETS + ["request_confidence"]:
        value = query_params.get(key)
        if value:
            result[key] = value

    return result
