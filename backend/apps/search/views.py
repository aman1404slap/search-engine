from rest_framework.response import Response
from rest_framework.views import APIView

from apps.search import ranking
from apps.search.serializers import SearchRequestSerializer


class SearchView(APIView):
    def post(self, request):
        req = SearchRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        data = req.validated_data

        results = ranking.hybrid_search(
            query_text=data["query"],
            filters=data["filters"],
            top_k=data["top_k"],
            min_confidence=data["min_confidence"],
        )

        results = self._attach_videos(results, request)

        return Response({"results": results})

    def _attach_videos(self, results, request):
        if not results:
            return results

        from apps.videos.models import Video
        from apps.videos.serializers import VideoSummarySerializer

        video_ids = {r["video_id"] for r in results}
        videos = Video.objects.filter(shot_id__in=video_ids).prefetch_related("tags")
        videos_by_id = {v.shot_id: v for v in videos}

        enriched = []
        for r in results:
            video = videos_by_id.get(r["video_id"])
            if video is None:
                # Video vanished/filtered out at the DB level since the index was built;
                # skip rather than emit a result with no video payload.
                continue
            enriched.append(
                {
                    **r,
                    "video": VideoSummarySerializer(video, context={"request": request}).data,
                }
            )
        return enriched
