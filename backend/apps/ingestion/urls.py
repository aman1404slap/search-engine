from django.urls import path

from . import views

urlpatterns = [
    path("upload/", views.UploadCreateView.as_view(), name="ingestion-upload"),
    path("uploads/", views.UploadListView.as_view(), name="ingestion-upload-list"),
    path("uploads/<int:pk>/", views.UploadDetailView.as_view(), name="ingestion-upload-detail"),
]
