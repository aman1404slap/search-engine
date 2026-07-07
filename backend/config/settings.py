"""
Django settings for the Video Search POC.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

load_dotenv(REPO_ROOT / ".env")

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-3*3!61p$3bynv=j9yq644xyhp060yiyw_*qx*%x&6$6_hvf-8j",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "apps.taxonomy",
    "apps.videos",
    "apps.ingestion",
    "apps.search",
    "apps.accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "video_search"),
        "USER": os.environ.get("POSTGRES_USER", "video_search"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "video_search"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# CORS (Vite dev server runs on a different port than Django) + CSRF
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

# Without this, cross-port POSTs from the dev SPA (localhost:5173 -> :8000),
# including the login POST itself, fail CSRF's Origin check regardless of
# CORS config -- Django checks Origin against CSRF_TRUSTED_ORIGINS whenever
# it doesn't match request.get_host().
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "apps.videos.pagination.StandardPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

# ---------------------------------------------------------------------------
# Redis: cache + Celery broker/result backend
# ---------------------------------------------------------------------------
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
# Run tasks synchronously (in-process) when no Celery worker is available yet.
# Flip to False once `celery -A config worker` is running.
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"

# ---------------------------------------------------------------------------
# S3 video source
# ---------------------------------------------------------------------------
# boto3 picks up AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN
# from the environment automatically (the temp creds the user exports in their
# terminal before running `manage.py runserver` / the Celery worker).
AWS_S3_REGION = os.environ.get("AWS_S3_REGION", "us-east-2")
AWS_S3_DEFAULT_BUCKET = os.environ.get("AWS_S3_DEFAULT_BUCKET", "ssai-staging-us-east-2")
# provenance.source paths look like "/mnt/experiments/Be-My-Eyes/...mp4" — this
# prefix is stripped to derive the S3 key relative to the bucket root.
S3_SOURCE_LOCAL_MOUNT_PREFIX = os.environ.get("S3_SOURCE_LOCAL_MOUNT_PREFIX", "/mnt/experiments/")
S3_PRESIGNED_URL_EXPIRY_SECONDS = int(os.environ.get("S3_PRESIGNED_URL_EXPIRY_SECONDS", "3600"))

# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "384"))
SEARCH_DENSE_WEIGHT = float(os.environ.get("SEARCH_DENSE_WEIGHT", "0.6"))
SEARCH_KEYWORD_WEIGHT = float(os.environ.get("SEARCH_KEYWORD_WEIGHT", "0.4"))
SEARCH_SPAN_MERGE_GAP_SECONDS = float(os.environ.get("SEARCH_SPAN_MERGE_GAP_SECONDS", "2.0"))

# Compound queries ("walking in rain") are split into concept clauses and
# combined via min() instead of one blended vector, so a segment strong on
# only one clause doesn't score as if it matched the whole query.
SEARCH_DECOMPOSE_QUERY = os.environ.get("SEARCH_DECOMPOSE_QUERY", "true").lower() == "true"

# Cross-encoder reranking of the top-N stage-1 results, run *before* grouping
# spans by video so that (almost) every span which could end up in a returned
# video's best-match slot gets a real cross-encoder score -- otherwise the
# reranked (cross-encoder sigmoid) and un-reranked (min-max fusion) results
# share one "confidence" field on two incomparable scales. Only ever runs on
# a shortlist (see apps/search/reranker.py) so it's independent of corpus
# size; disable entirely with SEARCH_RERANK_ENABLED=false.
SEARCH_RERANK_ENABLED = os.environ.get("SEARCH_RERANK_ENABLED", "true").lower() == "true"
SEARCH_RERANK_MODEL_NAME = os.environ.get(
    "SEARCH_RERANK_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
SEARCH_RERANK_POOL_SIZE = int(os.environ.get("SEARCH_RERANK_POOL_SIZE", "120"))

# Path to the static taxonomy definition used by `manage.py seed_taxonomy`.
TAXONOMY_TXT_PATH = Path(os.environ.get("TAXONOMY_TXT_PATH", REPO_ROOT / "taxonomy.txt"))
