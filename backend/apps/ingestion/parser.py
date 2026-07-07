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


def _video_duration_sec(record: dict, video_fields: dict) -> float:
    """Prefer the precise ffprobe-derived duration from provenance.sampling over
    the human-formatted "H:MM:SS" string (already parsed into video_fields by
    extract_video_fields), since the former has sub-second precision."""
    sampling = (record.get("provenance", {}) or {}).get("sampling", {}) or {}
    duration = sampling.get("video_duration_sec")
    if isinstance(duration, (int, float)):
        return float(duration)
    return video_fields.get("duration_sec") or 0.0


def _video_segment(record: dict, video_fields: dict) -> dict | None:
    """One row spanning the whole video: assist/request_case narrative + visual
    gist, so queries about a video's overall subject match even when no single
    event/episode phrase is close on its own."""
    assist = record.get("assist", {}) or {}
    request_case = record.get("request_case", {}) or {}
    visual_context = record.get("visual_context", {}) or {}
    visible_entities = visual_context.get("visible_entities") or []

    parts = [
        assist.get("brief", ""),
        assist.get("detailed", ""),
        request_case.get("brief", ""),
        request_case.get("detailed", ""),
        visual_context.get("video_caption", ""),
    ]
    if visible_entities:
        parts.append("Visible: " + ", ".join(visible_entities))
    text = ". ".join(p.strip().rstrip(".") for p in parts if p and p.strip())
    if not text:
        return None

    return {
        "segment_id": f"{record['shot_id']}:video",
        "granularity": "video",
        "start_s": 0.0,
        "end_s": _video_duration_sec(record, video_fields),
        "label": "",
        "text": text,
    }


def _episode_segments(record: dict) -> list[dict]:
    """One row per episodes[] entry -- a coherent multi-event scene, for queries
    about a whole activity ("identifying symbols on a sound machine") rather
    than a single instant."""
    segments = []
    for episode in record.get("episodes", []) or []:
        label = episode.get("label", "") or ""
        summary = episode.get("summary", "") or ""
        text = f"{label}. {summary}".strip(". ").strip()
        if not text:
            continue

        segments.append({
            "segment_id": episode["episode_id"],
            "granularity": "episode",
            "start_s": episode["start_s"],
            "end_s": episode["end_s"],
            "label": label,
            "text": text,
        })
    return segments


def _event_segments(record: dict) -> list[dict]:
    """One row per events[] entry, enriched with vision.clip_caption, object
    names, speech transcript_span, and the people_visible/conversation_visible/
    main_action of the event's linked visual_segments[] entry (joined via
    links.source_segment_ids.visual) -- none of these are searchable today even
    though they're already parsed into raw_data."""
    visual_by_id = {seg["segment_id"]: seg for seg in (record.get("visual_segments") or [])}

    segments = []
    for event in record.get("events", []) or []:
        label = event.get("label", "") or ""
        summary = event.get("summary", "") or ""
        vision = event.get("vision", {}) or {}
        speech = event.get("speech", {}) or {}
        scores = ((event.get("evidence", {}) or {}).get("scores", {}) or {})

        object_names = list(dict.fromkeys(
            [o.get("name") for o in (event.get("objects") or []) if o.get("name")]
            + list(vision.get("key_objects") or [])
        ))
        actor_roles = [a.get("role") for a in (event.get("actors") or []) if a.get("role")]

        visual_ids = ((event.get("links", {}) or {}).get("source_segment_ids", {}) or {}).get("visual") or []
        visual_seg = visual_by_id.get(visual_ids[0]) if visual_ids else None
        people_visible = visual_seg.get("people_visible") if visual_seg else None
        conversation_visible = visual_seg.get("conversation_visible") if visual_seg else None
        event_type = event.get("event_type", "") or ""
        interaction_kind = event.get("interaction_kind", "") or ""

        text_parts = [f"{label}. {summary}".strip(". ").strip()]
        if vision.get("clip_caption"):
            text_parts.append(vision["clip_caption"])
        if visual_seg and visual_seg.get("main_action"):
            text_parts.append(f"Main action: {visual_seg['main_action']}.")
        if object_names:
            text_parts.append("Objects: " + ", ".join(object_names) + ".")
        # transcript_span carries real transcript text even when `present` is False
        # (that flag means something narrower, e.g. "speech is the dominant
        # modality") -- gating on `present` here silently dropped real transcript
        # text from search, the opposite of what we want.
        if speech.get("transcript_span"):
            text_parts.append(f'Speech: "{speech["transcript_span"]}"')
        if people_visible is True:
            text_parts.append("A person is visible.")
        elif people_visible is False:
            text_parts.append("No person is visible.")
        if event_type:
            text_parts.append(f"Type: {event_type}.")
        if interaction_kind:
            text_parts.append(f"Interaction: {interaction_kind}.")
        text = " ".join(p.strip() for p in text_parts if p and p.strip())
        if not text:
            continue

        segments.append({
            "segment_id": event["event_id"],
            "granularity": "event",
            "start_s": event["start_s"],
            "end_s": event["end_s"],
            "label": label,
            "text": text,
            "confidence": scores.get("fusion_score", 0.0) or 0.0,
            "event_type": event_type,
            "interaction_kind": interaction_kind,
            "people_visible": people_visible,
            "conversation_visible": conversation_visible,
            "object_names": object_names,
            "actor_roles": actor_roles,
            "modality_scores": scores,
            "parent_segment_id": event.get("parent_episode_id", "") or "",
        })
    return segments


def extract_segments(record: dict, video_fields: dict) -> list[dict]:
    """Return Segment-field dicts across all three granularities: one video-level
    row, one row per episode, one row per event (see the three helpers above)."""
    video_segment = _video_segment(record, video_fields)
    return (
        ([video_segment] if video_segment else [])
        + _episode_segments(record)
        + _event_segments(record)
    )


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

    # Replace segments (all granularities).
    Segment.objects.filter(video=video).delete()
    segment_dicts = extract_segments(record, fields)
    if segment_dicts:
        Segment.objects.bulk_create(
            [Segment(video=video, **seg) for seg in segment_dicts]
        )

    return video
