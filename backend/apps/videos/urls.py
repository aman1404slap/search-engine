from django.urls import path

from apps.videos.views import (
    VideoDetailView,
    VideoFacetCountsView,
    VideoListView,
    VideoPlayUrlView,
)

urlpatterns = [
    path("", VideoListView.as_view(), name="video-list"),
    path("facets/", VideoFacetCountsView.as_view(), name="video-facets"),  # MUST come before the shot_id pattern below
    path("<str:shot_id>/", VideoDetailView.as_view(), name="video-detail"),
    path("<str:shot_id>/play-url/", VideoPlayUrlView.as_view(), name="video-play-url"),
]
