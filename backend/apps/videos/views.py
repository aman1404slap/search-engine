from django.conf import settings
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.videos.constants import ALL_TAXONOMY_FACETS, MULTI_SELECT_FACETS, SINGLE_SELECT_FACETS
from apps.videos.filters import apply_video_filters, normalize_query_params
from apps.videos.models import Video, VideoTag
from apps.videos.serializers import VideoDetailSerializer, VideoSummarySerializer


class VideoListView(generics.ListAPIView):
    queryset = Video.objects.prefetch_related("tags").all()
    serializer_class = VideoSummarySerializer

    def get_queryset(self):
        params = normalize_query_params(self.request.query_params)
        return apply_video_filters(super().get_queryset(), params)


class VideoFacetCountsView(APIView):
    def get(self, request, *args, **kwargs):
        params = normalize_query_params(request.query_params)
        filtered_qs = apply_video_filters(Video.objects.all(), params)

        counts = {}
        for key in ALL_TAXONOMY_FACETS:
            if key in SINGLE_SELECT_FACETS:
                rows = (
                    filtered_qs.exclude(**{key: ""})
                    .values(key)
                    .annotate(count=Count("shot_id"))
                    .order_by()
                )
                counts[key] = {row[key]: row["count"] for row in rows}
            elif key in MULTI_SELECT_FACETS:
                rows = (
                    VideoTag.objects.filter(video__in=filtered_qs, facet=key)
                    .values("value")
                    .annotate(count=Count("video", distinct=True))
                    .order_by()
                )
                counts[key] = {row["value"]: row["count"] for row in rows}

        return Response(counts)


class VideoDetailView(generics.RetrieveAPIView):
    queryset = Video.objects.prefetch_related("tags", "segments")
    serializer_class = VideoDetailSerializer
    lookup_field = "shot_id"
    lookup_url_kwarg = "shot_id"


class VideoPlayUrlView(APIView):
    def get(self, request, shot_id, *args, **kwargs):
        video = get_object_or_404(Video, shot_id=shot_id)

        try:
            from apps.ingestion.s3 import generate_presigned_url

            url = generate_presigned_url(video.s3_bucket, video.s3_key)
        except Exception as exc:
            return Response({"error": str(exc)}, status=502)

        return Response({"url": url, "expires_in": settings.S3_PRESIGNED_URL_EXPIRY_SECONDS})
