"""Celery tasks for the ingestion pipeline: JSONL parse -> thumbnail -> embeddings."""

import json
import logging

from celery import shared_task
from django.conf import settings

from apps.videos.models import Video

from . import media, s3
from .models import Upload
from .parser import ingest_record

logger = logging.getLogger(__name__)

SAVE_EVERY = 10


@shared_task
def process_upload(upload_id):
    """Parse an Upload's JSONL file line by line, ingesting each record.

    Bad lines are skipped (logged + counted as failures) rather than aborting the
    whole upload. Successfully-ingested videos are handed off to the media/embedding
    pipeline via process_video_media.delay().
    """
    try:
        upload = Upload.objects.get(id=upload_id)
    except Upload.DoesNotExist:
        logger.error("process_upload: Upload %s does not exist", upload_id)
        return

    ingested_shot_ids = []
    total = 0
    processed = 0
    failed = 0

    try:
        upload.file.open("rb")
    except Exception as exc:
        logger.error("process_upload: could not open file for Upload %s: %s", upload_id, exc)
        upload.status = "failed"
        upload.error_message = f"could not open uploaded file: {exc}"
        upload.save(update_fields=["status", "error_message", "updated_at"])
        return

    try:
        with upload.file:
            for raw_line in upload.file:
                line = raw_line.decode("utf-8").strip() if isinstance(raw_line, bytes) else raw_line.strip()
                if not line:
                    continue
                total += 1
                try:
                    record = json.loads(line)
                    video = ingest_record(record, upload=upload)
                    ingested_shot_ids.append(video.shot_id)
                    processed += 1
                except Exception as exc:
                    failed += 1
                    logger.error("process_upload: failed to ingest line %s of upload %s: %s", total, upload_id, exc)

                if total % SAVE_EVERY == 0:
                    upload.total_records = total
                    upload.processed_records = processed
                    upload.failed_records = failed
                    upload.save(update_fields=["total_records", "processed_records", "failed_records", "updated_at"])
    except Exception as exc:
        logger.error("process_upload: fatal error reading upload %s: %s", upload_id, exc)
        upload.status = "failed"
        upload.error_message = f"fatal error while reading file: {exc}"
        upload.total_records = total
        upload.processed_records = processed
        upload.failed_records = failed
        upload.save(update_fields=["status", "error_message", "total_records", "processed_records", "failed_records", "updated_at"])
        for shot_id in ingested_shot_ids:
            process_video_media.delay(shot_id)
        return

    upload.total_records = total
    upload.processed_records = processed
    upload.failed_records = failed
    if total == 0:
        upload.status = "failed"
        upload.error_message = upload.error_message or "no records found in uploaded file"
    elif failed == 0:
        upload.status = "completed"
    elif processed == 0:
        upload.status = "failed"
        upload.error_message = upload.error_message or "all records failed to ingest"
    else:
        upload.status = "completed_with_errors"
    upload.save()

    for shot_id in ingested_shot_ids:
        process_video_media.delay(shot_id)


@shared_task
def process_video_media(shot_id):
    """Generate a thumbnail for a video (best-effort) and chain to embeddings."""
    try:
        video = Video.objects.get(shot_id=shot_id)
    except Video.DoesNotExist:
        logger.error("process_video_media: Video %s does not exist", shot_id)
        return

    video.ingestion_status = "processing"
    video.save(update_fields=["ingestion_status", "updated_at"])

    try:
        presigned_url = s3.generate_presigned_url(video.s3_bucket, video.s3_key)
        output_path = str(settings.MEDIA_ROOT / "thumbnails" / f"{shot_id}.jpg")
        ok = media.generate_thumbnail(presigned_url, output_path)
        if ok:
            video.thumbnail = f"thumbnails/{shot_id}.jpg"
        else:
            note = "thumbnail: generation failed"
            video.ingestion_error = f"{video.ingestion_error}\n{note}".strip() if video.ingestion_error else note
    except Exception as exc:
        note = f"thumbnail: {exc}"
        logger.error("process_video_media: %s for shot_id %s", note, shot_id)
        video.ingestion_error = f"{video.ingestion_error}\n{note}".strip() if video.ingestion_error else note
    finally:
        video.save()
        compute_embeddings.delay(shot_id)


@shared_task
def compute_embeddings(shot_id):
    """Embed all segments for a video and bump the search index version."""
    video = Video.objects.get(shot_id=shot_id)
    segments = list(video.segments.all())

    try:
        if segments:
            from apps.search.embedding import embed_texts

            vectors = embed_texts([seg.text for seg in segments])
            for seg, vec in zip(segments, vectors):
                seg.embedding = vec
                seg.save(update_fields=["embedding"])

        from apps.search.index import bump_version

        bump_version()

        video.ingestion_status = "ready"
        video.save(update_fields=["ingestion_status", "updated_at"])
    except Exception as exc:
        note = f"embeddings: {exc}"
        logger.error("compute_embeddings: %s for shot_id %s", note, shot_id)
        video.ingestion_status = "failed"
        video.ingestion_error = f"{video.ingestion_error}\n{note}".strip() if video.ingestion_error else note
        video.save(update_fields=["ingestion_status", "ingestion_error", "updated_at"])
        raise
