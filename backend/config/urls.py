from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/taxonomy/", include("apps.taxonomy.urls")),
    path("api/videos/", include("apps.videos.urls")),
    path("api/ingestion/", include("apps.ingestion.urls")),
    path("api/search/", include("apps.search.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
