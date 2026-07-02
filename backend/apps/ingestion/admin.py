from django.contrib import admin

from .models import Upload


@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "file_name",
        "status",
        "total_records",
        "processed_records",
        "failed_records",
        "created_at",
    ]
    list_filter = ["status"]
    readonly_fields = [
        "file_name",
        "file",
        "status",
        "total_records",
        "processed_records",
        "failed_records",
        "error_message",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]
