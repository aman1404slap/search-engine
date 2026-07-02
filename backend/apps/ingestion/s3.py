"""S3 helpers: local-mount-path -> S3 key resolution and presigned URL generation."""

import logging

import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


def resolve_s3_key(source_local_path: str) -> str:
    """Convert a local mount path (as seen in provenance.source) into an S3 key.

    Example:
        "/mnt/experiments/Be-My-Eyes/Sample_Data/Phone/_all-clips-001/4748416.mp4"
        -> "Be-My-Eyes/Sample_Data/Phone/_all-clips-001/4748416.mp4"
    """
    if not source_local_path:
        return ""

    prefix = settings.S3_SOURCE_LOCAL_MOUNT_PREFIX
    if prefix and source_local_path.startswith(prefix):
        return source_local_path[len(prefix):]

    logger.warning(
        "resolve_s3_key: prefix %r not found in source_local_path %r; "
        "falling back to stripping a leading slash",
        prefix,
        source_local_path,
    )
    return source_local_path.lstrip("/")


def get_default_bucket() -> str:
    """Return the default S3 bucket name for video sources."""
    return settings.AWS_S3_DEFAULT_BUCKET


def generate_presigned_url(bucket: str, key: str, expires_in: int | None = None) -> str:
    """Generate a presigned GET URL for the given bucket/key.

    Deliberately creates a brand-new boto3.Session() (not boto3.client(), which
    implicitly reuses a process-wide cached default session) so credentials are
    re-read from disk/env on every call. The user's AWS credentials are
    temporary and get rotated externally while this long-running dev server
    keeps running -- a cached session would keep signing with a stale,
    expired credential (S3 returns 403, not an auth error, when that happens)
    until the process was restarted.

    Any boto3/botocore exceptions (including missing credentials) are allowed to
    propagate -- the caller is responsible for catching them so failures (e.g.
    missing AWS creds) surface clearly instead of being silently swallowed here.
    """
    if expires_in is None:
        expires_in = settings.S3_PRESIGNED_URL_EXPIRY_SECONDS

    session = boto3.Session()
    client = session.client("s3", region_name=settings.AWS_S3_REGION)
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )
