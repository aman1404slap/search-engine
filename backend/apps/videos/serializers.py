from rest_framework import serializers

from apps.videos.constants import ALL_TAXONOMY_FACETS, MULTI_SELECT_FACETS, SINGLE_SELECT_FACETS
from apps.videos.models import Segment, Video


class SegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Segment
        fields = ["segment_id", "start_s", "end_s", "label", "text", "confidence"]


class VideoSummarySerializer(serializers.ModelSerializer):
    """Used in the paginated list view AND embedded in search results (imported by the search app)."""

    thumbnail_url = serializers.SerializerMethodField()
    taxonomy = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            "shot_id",
            "thumbnail_url",
            "duration_sec",
            "assist_brief",
            "request_brief",
            "request_confidence",
            "source_label",
            "ingestion_status",
            "taxonomy",
        ]

    def get_thumbnail_url(self, obj):
        if not obj.thumbnail:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.thumbnail.url) if request else obj.thumbnail.url

    def get_taxonomy(self, obj):
        # obj.tags is expected to be prefetched by the caller's queryset
        # (.prefetch_related("tags")) so obj.tags.all() below hits no extra query.
        tags_by_facet = {}
        for tag in obj.tags.all():
            tags_by_facet.setdefault(tag.facet, []).append(tag.value)

        taxonomy = {}
        for key in ALL_TAXONOMY_FACETS:
            if key in SINGLE_SELECT_FACETS:
                taxonomy[key] = getattr(obj, key) or ""
            elif key in MULTI_SELECT_FACETS:
                taxonomy[key] = sorted(tags_by_facet.get(key, []))
        return taxonomy


class VideoDetailSerializer(VideoSummarySerializer):
    """Extends the summary with everything needed for the right-hand detail/player pane."""

    segments = SegmentSerializer(many=True, read_only=True)
    transcript = serializers.SerializerMethodField()

    class Meta(VideoSummarySerializer.Meta):
        fields = VideoSummarySerializer.Meta.fields + [
            "s3_bucket",
            "s3_key",
            "recorded_at",
            "caller_state",
            "caller_country",
            "detected_language",
            "assist_detailed",
            "request_detailed",
            "ingestion_error",
            "segments",
            "transcript",
        ]

    def get_transcript(self, obj):
        turns = obj.raw_data.get("speech", {}).get("turns", [])
        return [
            {
                "start_s": turn.get("start_s"),
                "end_s": turn.get("end_s"),
                "speaker_id": turn.get("speaker_id"),
                "text": turn.get("transcript"),
            }
            for turn in turns
        ]
