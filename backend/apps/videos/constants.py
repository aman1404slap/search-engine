# Facet keys, matching taxonomy.txt / request_case.taxonomy in the source JSONL.
#
# Single-select facets are stored as plain CharField columns directly on Video.
# Multi-select facets are stored as VideoTag rows (one row per video/facet/value).
SINGLE_SELECT_FACETS = [
    "request",
    "interaction_pattern",
    "capture_medium",
    "capture_quality",
    "setting",
    "weather",
    "environment_domain",
    "outcome",
]

MULTI_SELECT_FACETS = [
    "secondary_requests",
    "reasoning_demands",
    "target_entity",
    "perceptual_properties",
]

ALL_TAXONOMY_FACETS = SINGLE_SELECT_FACETS + MULTI_SELECT_FACETS

# taxonomy.txt has no dedicated "secondary_requests:" section -- its values are
# drawn from the same option set as "request". The seeder copies values across.
FACET_VALUE_SOURCE_OVERRIDES = {
    "secondary_requests": "request",
}

REQUEST_CONFIDENCE_CHOICES = [
    ("high", "High"),
    ("medium", "Medium"),
    ("low", "Low"),
]

INGESTION_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("processing", "Processing"),
    ("ready", "Ready"),
    ("failed", "Failed"),
]
