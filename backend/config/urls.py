import re

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponseForbidden
from django.urls import include, path, re_path
from django.views.static import serve as static_serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/taxonomy/", include("apps.taxonomy.urls")),
    path("api/videos/", include("apps.videos.urls")),
    path("api/ingestion/", include("apps.ingestion.urls")),
    path("api/search/", include("apps.search.urls")),
]


def auth_required_media(request, *args, **kwargs):
    """Media (thumbnails) served the same way in dev and prod (gunicorn has
    no DEBUG-only auto-serving) -- gated behind login rather than
    django.contrib.auth's login_required, which would 302 to a nonexistent
    /accounts/login/ instead of a clean 403 for an <img> tag."""
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
    return static_serve(request, *args, **kwargs)


urlpatterns += [
    re_path(
        r"^%s(?P<path>.*)$" % re.escape(settings.MEDIA_URL.lstrip("/")),
        auth_required_media,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
