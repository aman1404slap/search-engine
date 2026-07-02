from rest_framework import serializers

from .models import Upload


class UploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upload
        fields = [
            "id",
            "file_name",
            "status",
            "total_records",
            "processed_records",
            "failed_records",
            "error_message",
            "created_at",
        ]
