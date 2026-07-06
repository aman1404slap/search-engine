from rest_framework import serializers

from .models import Upload


class UploadSerializer(serializers.ModelSerializer):
    pipeline_status = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    videos_ready = serializers.SerializerMethodField()
    videos_processing = serializers.SerializerMethodField()
    videos_failed_media = serializers.SerializerMethodField()

    class Meta:
        model = Upload
        fields = [
            "id",
            "file_name",
            "status",
            "pipeline_status",
            "is_active",
            "total_records",
            "processed_records",
            "failed_records",
            "videos_ready",
            "videos_processing",
            "videos_failed_media",
            "error_message",
            "created_at",
        ]

    def get_videos_ready(self, obj):
        return obj.video_pipeline_counts()["ready"]

    def get_videos_processing(self, obj):
        counts = obj.video_pipeline_counts()
        return counts["pending"] + counts["processing"]

    def get_videos_failed_media(self, obj):
        return obj.video_pipeline_counts()["failed"]
