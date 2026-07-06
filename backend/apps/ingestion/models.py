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

    def video_pipeline_counts(self):
        """Ingestion-status tally of every video this upload produced, cached per instance."""
        if not hasattr(self, "_video_pipeline_counts"):
            counts = {"pending": 0, "processing": 0, "ready": 0, "failed": 0}
            for ingestion_status in self.videos.values_list("ingestion_status", flat=True):
                counts[ingestion_status] = counts.get(ingestion_status, 0) + 1
            self._video_pipeline_counts = counts
        return self._video_pipeline_counts

    @property
    def pipeline_status(self):
        """Status across both JSONL parsing (`status`) and the per-video media/embedding
        pipeline that parsing hands off to -- this is what "done" should mean for gating
        new uploads, not just `status` on its own."""
        if self.status == "processing":
            return "parsing"
        if self.status == "failed" and self.processed_records == 0:
            return "failed"

        counts = self.video_pipeline_counts()
        if counts["pending"] or counts["processing"]:
            return "processing_media"
        if self.status == "completed_with_errors" or counts["failed"]:
            return "completed_with_errors"
        return self.status

    @property
    def is_active(self):
        """True while this upload still blocks a new upload from starting."""
        return self.pipeline_status in ("parsing", "processing_media")
