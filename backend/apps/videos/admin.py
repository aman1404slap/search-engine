from django.contrib import admin

from apps.videos.models import Segment, Video, VideoTag


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ["shot_id", "request", "ingestion_status", "duration_sec", "source_label", "created_at"]
    list_filter = ["ingestion_status", "request", "setting", "outcome"]
    search_fields = ["shot_id", "assist_brief", "request_brief"]


@admin.register(VideoTag)
class VideoTagAdmin(admin.ModelAdmin):
    list_display = ["video", "facet", "value"]
    list_filter = ["facet"]
    search_fields = ["video__shot_id", "value"]


@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ["segment_id", "video", "granularity", "start_s", "end_s", "confidence"]
    list_filter = ["granularity"]
    search_fields = ["segment_id", "video__shot_id", "text"]
