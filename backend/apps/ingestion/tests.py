from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.videos.models import Video

from .models import Upload


def make_video(shot_id, upload, ingestion_status):
    return Video.objects.create(
        shot_id=shot_id,
        source_local_path=f"/rec/{shot_id}.mp4",
        raw_data={},
        uploaded_from=upload,
        ingestion_status=ingestion_status,
    )


class UploadPipelineStatusTests(APITestCase):
    """Upload.pipeline_status/is_active must reflect BOTH the JSONL parse step
    (`status`) and the per-video thumbnail/embedding pipeline it queues -- not
    just the parse step, since videos keep processing after parsing finishes."""

    def test_still_parsing_is_active(self):
        upload = Upload.objects.create(file_name="a.jsonl", status="processing", total_records=2)
        self.assertEqual(upload.pipeline_status, "parsing")
        self.assertTrue(upload.is_active)

    def test_parse_failed_with_nothing_ingested_is_terminal(self):
        upload = Upload.objects.create(file_name="a.jsonl", status="failed", total_records=0)
        self.assertEqual(upload.pipeline_status, "failed")
        self.assertFalse(upload.is_active)

    def test_parsed_but_videos_still_processing_media_is_active(self):
        upload = Upload.objects.create(
            file_name="a.jsonl", status="completed", total_records=2, processed_records=2
        )
        make_video("s1", upload, "ready")
        make_video("s2", upload, "processing")
        self.assertEqual(upload.pipeline_status, "processing_media")
        self.assertTrue(upload.is_active)

    def test_all_videos_ready_is_completed_and_inactive(self):
        upload = Upload.objects.create(
            file_name="a.jsonl", status="completed", total_records=2, processed_records=2
        )
        make_video("s1", upload, "ready")
        make_video("s2", upload, "ready")
        self.assertEqual(upload.pipeline_status, "completed")
        self.assertFalse(upload.is_active)

    def test_video_media_failure_downgrades_to_completed_with_errors(self):
        upload = Upload.objects.create(
            file_name="a.jsonl", status="completed", total_records=2, processed_records=2
        )
        make_video("s1", upload, "ready")
        make_video("s2", upload, "failed")
        self.assertEqual(upload.pipeline_status, "completed_with_errors")
        self.assertFalse(upload.is_active)

    def test_parse_level_errors_stay_completed_with_errors_once_media_settles(self):
        upload = Upload.objects.create(
            file_name="a.jsonl",
            status="completed_with_errors",
            total_records=2,
            processed_records=1,
            failed_records=1,
        )
        make_video("s1", upload, "ready")
        self.assertEqual(upload.pipeline_status, "completed_with_errors")
        self.assertFalse(upload.is_active)


class UploadGatingViewTests(APITestCase):
    """A new upload must be rejected while the most recent one is still active
    across the whole pipeline, and allowed again once it settles."""

    def setUp(self):
        user = get_user_model().objects.create_user(username="u", password="pw")
        self.client.force_authenticate(user=user)

    def _file(self, content=b'{"provenance": {"source": "/x.mp4"}}\n'):
        return SimpleUploadedFile("data.jsonl", content, content_type="application/octet-stream")

    def test_upload_rejected_while_previous_still_parsing(self):
        Upload.objects.create(file_name="prev.jsonl", status="processing", total_records=1)
        res = self.client.post("/api/ingestion/upload/", {"file": self._file()}, format="multipart")
        self.assertEqual(res.status_code, 409)

    def test_upload_rejected_while_previous_videos_still_processing_media(self):
        prev = Upload.objects.create(
            file_name="prev.jsonl", status="completed", total_records=1, processed_records=1
        )
        make_video("s1", prev, "processing")
        res = self.client.post("/api/ingestion/upload/", {"file": self._file()}, format="multipart")
        self.assertEqual(res.status_code, 409)

    def test_upload_allowed_once_previous_upload_fully_settled(self):
        prev = Upload.objects.create(
            file_name="prev.jsonl", status="completed", total_records=1, processed_records=1
        )
        make_video("s1", prev, "ready")
        res = self.client.post("/api/ingestion/upload/", {"file": self._file()}, format="multipart")
        self.assertEqual(res.status_code, 201)

    def test_upload_allowed_when_no_prior_uploads_exist(self):
        res = self.client.post("/api/ingestion/upload/", {"file": self._file()}, format="multipart")
        self.assertEqual(res.status_code, 201)
