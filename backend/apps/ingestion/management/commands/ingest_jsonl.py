import json

from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.parser import ingest_record
from apps.ingestion.tasks import process_video_media


class Command(BaseCommand):
    help = "Synchronously ingest a JSONL file of video records (no Celery, no Upload row)."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Path to the JSONL file to ingest")
        parser.add_argument(
            "--skip-media",
            action="store_true",
            help="Skip thumbnail generation and embedding computation (metadata-only, fast).",
        )

    def handle(self, *args, **options):
        path = options["path"]
        skip_media = options["skip_media"]

        try:
            f = open(path, "r", encoding="utf-8")
        except OSError as exc:
            raise CommandError(f"could not open {path}: {exc}")

        total = 0
        processed = 0
        failed = 0
        ingested_shot_ids = []

        with f:
            for line_number, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                total += 1
                try:
                    record = json.loads(line)
                    video = ingest_record(record, upload=None)
                    ingested_shot_ids.append(video.shot_id)
                    processed += 1
                except Exception as exc:
                    failed += 1
                    self.stderr.write(self.style.WARNING(f"line {line_number}: failed to ingest ({exc})"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Ingested {processed}/{total} records ({failed} failed) from {path}"
            )
        )

        if skip_media:
            self.stdout.write("Skipping media/embedding pipeline (--skip-media).")
            return

        for shot_id in ingested_shot_ids:
            self.stdout.write(f"Processing media/embeddings for {shot_id}...")
            try:
                process_video_media(shot_id)
            except Exception as exc:
                self.stderr.write(self.style.WARNING(f"{shot_id}: media/embedding pipeline error ({exc})"))

        self.stdout.write(self.style.SUCCESS("Done."))
