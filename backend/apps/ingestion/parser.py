"""JSONL record -> model field mapping and idempotent upsert logic."""

import logging

from django.utils.dateparse import parse_datetime

from apps.videos.constants import MULTI_SELECT_FACETS, SINGLE_SELECT_FACETS
from apps.videos.models import Segment, Video, VideoTag

from . import s3
from .media import parse_duration_string

logger = logging.getLogger(__name__)


def extract_video_fields(record: dict) -> dict:
    """Return kwargs for Video fields (excluding shot_id/raw_data/uploaded_from)."""
    provenance = record.get("provenance", {}) or {}
    source_metadata = provenance.get("source_metadata", {}) or {}
    assist = record.get("assist", {}) or {}
    request_case = record.get("request_case", {}) or {}
    taxonomy = request_case.get("taxonomy", {}) or {}

    source_local_path = provenance.get("source", "") or ""
    bucket = s3.get_default_bucket()
    key = s3.resolve_s3_key(source_local_path)

    recorded_at_raw = source_metadata.get("created_at")
    recorded_at = None
    if recorded_at_raw:
        try:
            recorded_at = parse_datetime(recorded_at_raw)
        except (ValueError, TypeError) as exc:
            logger.warning("extract_video_fields: could not parse created_at %r: %s", recorded_at_raw, exc)
            recorded_at = None

    fields = {
        "source_local_path": source_local_path,
        "s3_bucket": bucket,
        "s3_key": key,
        "duration_sec": parse_duration_string(source_metadata.get("duration")),
        "recorded_at": recorded_at,
        "caller_state": source_metadata.get("caller_state", "") or "",
        "caller_country": source_metadata.get("caller_country", "") or "",
        "detected_language": source_metadata.get("detected_language", "") or "",
        "source_label": source_metadata.get("label"),
        "assist_brief": assist.get("brief", "") or "",
        "assist_detailed": assist.get("detailed", "") or "",
        "request_brief": request_case.get("brief", "") or "",
        "request_detailed": request_case.get("detailed", "") or "",
        "request_confidence": request_case.get("confidence", "") or "",
    }

    for key_name in SINGLE_SELECT_FACETS:
        fields[key_name] = taxonomy.get(key_name, "") or ""

    return fields


def extract_tag_rows(record: dict) -> list[tuple[str, str]]:
    """Return (facet, value) pairs for every multi-select taxonomy facet."""
    request_case = record.get("request_case", {}) or {}
    taxonomy = request_case.get("taxonomy", {}) or {}

    rows = []
    for facet in MULTI_SELECT_FACETS:
        values = taxonomy.get(facet) or []
        for value in values:
            rows.append((facet, value))
    return rows


def extract_segments(record: dict) -> list[dict]:
    """Return a list of Segment-field dicts, one per event in record["events"]."""
    segments = []
    for event in record.get("events", []) or []:
        label = event.get("label", "") or ""
        summary = event.get("summary", "") or ""
        text = f"{label}. {summary}".strip(". ").strip()
        confidence = (
            (event.get("evidence", {}) or {}).get("scores", {}) or {}
        ).get("fusion_score", 0.0)

        segments.append({
            "segment_id": event["event_id"],
            "start_s": event["start_s"],
            "end_s": event["end_s"],
            "label": label,
            "text": text,
            "confidence": confidence or 0.0,
        })
    return segments


def ingest_record(record: dict, upload=None) -> "Video":
    """Upsert a Video (+ its tags/segments) from one parsed JSONL record.

    Idempotent: re-ingesting the same shot_id replaces its tags and segments,
    making a corrected re-upload of the same JSONL safe to run repeatedly.
    Does not enqueue any Celery task and does not compute embeddings.
    """
    shot_id = record["shot_id"]
    fields = extract_video_fields(record)

    video, _created = Video.objects.update_or_create(
        shot_id=shot_id,
        defaults={
            **fields,
            "raw_data": record,
            "uploaded_from": upload,
            "ingestion_status": "pending",
            "ingestion_error": "",
        },
    )

    # Replace tags.
    VideoTag.objects.filter(video=video).delete()
    tag_rows = extract_tag_rows(record)
    if tag_rows:
        VideoTag.objects.bulk_create(
            [VideoTag(video=video, facet=facet, value=value) for facet, value in tag_rows]
        )

    # Replace segments.
    Segment.objects.filter(video=video).delete()
    segment_dicts = extract_segments(record)
    if segment_dicts:
        Segment.objects.bulk_create(
            [Segment(video=video, **seg) for seg in segment_dicts]
        )

    return video
