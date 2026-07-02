from django.db import models

UPLOAD_STATUS_CHOICES = [
    ("processing", "Processing"),
    ("completed", "Completed"),
    ("completed_with_errors", "Completed with errors"),
    ("failed", "Failed"),
]


class Upload(models.Model):
    """One JSONL file uploaded through the UI (or loaded via the CLI)."""

    file_name = models.CharField(max_length=300)
    file = models.FileField(upload_to="uploads/")
    status = models.CharField(max_length=30, choices=UPLOAD_STATUS_CHOICES, default="processing")
    total_records = models.IntegerField(default=0)
    processed_records = models.IntegerField(default=0)
    failed_records = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Upload({self.file_name}, {self.status})"
