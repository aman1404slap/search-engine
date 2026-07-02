from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Upload
from .serializers import UploadSerializer
from .tasks import process_upload


class UploadCreateView(APIView):
    """POST /api/ingestion/upload/ -- multipart upload of a JSONL file."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "no file provided (expected multipart field 'file')"}, status=status.HTTP_400_BAD_REQUEST)

        upload = Upload(file_name=file_obj.name, file=file_obj)
        upload.save()

        total_records = _count_lines(upload)
        upload.total_records = total_records
        upload.save(update_fields=["total_records", "updated_at"])

        process_upload.delay(upload.id)

        return Response(
            {
                "upload_id": upload.id,
                "status": upload.status,
                "total_records": upload.total_records,
            },
            status=status.HTTP_201_CREATED,
        )


def _count_lines(upload: Upload) -> int:
    """Cheaply count non-blank lines in the uploaded file without fully parsing it."""
    try:
        count = 0
        upload.file.open("rb")
        try:
            for raw_line in upload.file:
                line = raw_line.decode("utf-8").strip() if isinstance(raw_line, bytes) else raw_line.strip()
                if line:
                    count += 1
        finally:
            upload.file.close()
        return count
    except Exception:
        return 0


class UploadListView(generics.ListAPIView):
    """GET /api/ingestion/uploads/ -- recent uploads, newest first."""

    queryset = Upload.objects.all()
    serializer_class = UploadSerializer


class UploadDetailView(generics.RetrieveAPIView):
    """GET /api/ingestion/uploads/<int:pk>/ -- single upload's status (for polling)."""

    queryset = Upload.objects.all()
    serializer_class = UploadSerializer
