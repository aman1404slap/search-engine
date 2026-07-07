from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from pgvector.django import HnswIndex, VectorField

from apps.videos.constants import (
    GRANULARITY_CHOICES,
    INGESTION_STATUS_CHOICES,
    REQUEST_CONFIDENCE_CHOICES,
)


class Video(models.Model):
    """One shot/video record, one row per line in an ingested JSONL file."""

    shot_id = models.CharField(max_length=255, primary_key=True)

    # --- source / S3 -------------------------------------------------
    source_local_path = models.CharField(max_length=1000, help_text="raw provenance.source path")
    s3_bucket = models.CharField(max_length=200, blank=True)
    s3_key = models.CharField(max_length=1000, blank=True)
    duration_sec = models.FloatField(null=True, blank=True)
    recorded_at = models.DateTimeField(null=True, blank=True)
    caller_state = models.CharField(max_length=100, blank=True)
    caller_country = models.CharField(max_length=100, blank=True)
    detected_language = models.CharField(max_length=20, blank=True)
    source_label = models.CharField(max_length=100, blank=True, null=True)

    # --- narrative text ------------------------------------------------
    assist_brief = models.TextField(blank=True)
    assist_detailed = models.TextField(blank=True)
    request_brief = models.TextField(blank=True)
    request_detailed = models.TextField(blank=True)
    request_confidence = models.CharField(
        max_length=10, choices=REQUEST_CONFIDENCE_CHOICES, blank=True
    )

    # --- single-select taxonomy (see apps.videos.constants) -----------
    request = models.CharField(max_length=100, blank=True, db_index=True)
    interaction_pattern = models.CharField(max_length=100, blank=True, db_index=True)
    capture_medium = models.CharField(max_length=100, blank=True, db_index=True)
    capture_quality = models.CharField(max_length=100, blank=True, db_index=True)
    setting = models.CharField(max_length=100, blank=True, db_index=True)
    weather = models.CharField(max_length=100, blank=True, db_index=True)
    environment_domain = models.CharField(max_length=100, blank=True, db_index=True)
    outcome = models.CharField(max_length=100, blank=True, db_index=True)

    # --- media pipeline state ------------------------------------------
    thumbnail = models.ImageField(upload_to="thumbnails/", null=True, blank=True)
    ingestion_status = models.CharField(
        max_length=20, choices=INGESTION_STATUS_CHOICES, default="pending", db_index=True
    )
    ingestion_error = models.TextField(blank=True)

    # --- bookkeeping -----------------------------------------------------
    raw_data = models.JSONField(help_text="full original JSONL record, for detail display")
    uploaded_from = models.ForeignKey(
        "ingestion.Upload", null=True, blank=True, on_delete=models.SET_NULL, related_name="videos"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.shot_id


class VideoTag(models.Model):
    """One row per (video, multi-select facet, value) -- e.g. target_entity=appliance."""

    video = models.ForeignKey(Video, related_name="tags", on_delete=models.CASCADE)
    facet = models.CharField(max_length=100, db_index=True)
    value = models.CharField(max_length=150, db_index=True)

    class Meta:
        unique_together = ("video", "facet", "value")
        indexes = [models.Index(fields=["facet", "value"])]

    def __str__(self):
        return f"{self.video_id}:{self.facet}={self.value}"


class Segment(models.Model):
    """One searchable chunk of a video, at one of three granularities:

    - "video": one per video, spanning its full duration -- assist/request_case
      narrative + visual_context, for queries about the overall gist.
    - "episode": one per episodes[] entry -- a coherent multi-event scene, for
      queries about a whole activity rather than one instant.
    - "event": one per events[] entry (the original unit), enriched with
      vision.clip_caption, object names, speech transcript_span, and the
      people_visible/conversation_visible/main_action of its linked visual
      segment (see apps.ingestion.parser).

    All three granularities are embedded the same way and compete directly in
    ranking (apps.search.ranking) -- there's no separate index per granularity.
    """

    segment_id = models.CharField(max_length=200, unique=True, help_text="source event_id/episode_id, or f'{shot_id}:video'")
    video = models.ForeignKey(Video, related_name="segments", on_delete=models.CASCADE)
    granularity = models.CharField(max_length=10, choices=GRANULARITY_CHOICES, db_index=True)
    start_s = models.FloatField()
    end_s = models.FloatField()
    label = models.CharField(max_length=500, blank=True)
    text = models.TextField(help_text="embedded and keyword-indexed")
    confidence = models.FloatField(default=0.0, help_text="evidence.scores.fusion_score (event); unset otherwise")
    embedding = VectorField(dimensions=settings.EMBEDDING_DIM, null=True, blank=True)

    # --- event-only structured fields, from events[] + their linked visual_segments entry ---
    event_type = models.CharField(max_length=50, blank=True)
    interaction_kind = models.CharField(max_length=50, blank=True)
    people_visible = models.BooleanField(null=True, blank=True)
    conversation_visible = models.BooleanField(null=True, blank=True)
    object_names = ArrayField(models.CharField(max_length=200), default=list, blank=True)
    actor_roles = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    modality_scores = models.JSONField(default=dict, blank=True, help_text="evidence.scores: video/speech/sound/fusion")
    parent_segment_id = models.CharField(max_length=200, blank=True, help_text="event's parent episode's segment_id")

    class Meta:
        ordering = ["video_id", "start_s"]
        indexes = [
            models.Index(fields=["video", "start_s"]),
            models.Index(fields=["granularity"]),
            GinIndex(fields=["object_names"]),
            HnswIndex(
                name="segment_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self):
        return self.segment_id
