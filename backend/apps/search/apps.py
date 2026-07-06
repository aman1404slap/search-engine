import os
import sys

from django.apps import AppConfig


class SearchConfig(AppConfig):
    name = "apps.search"

    def ready(self):
        if not _is_long_running_server_process():
            return

        from django.conf import settings

        from . import embedding

        embedding.get_model()

        if settings.SEARCH_RERANK_ENABLED:
            from . import reranker

            reranker.get_cross_encoder()


def _is_long_running_server_process() -> bool:
    """AppConfig.ready() fires for every manage.py command, not just the
    server -- eager-loading the embedding/rerank models there would also
    slow down migrate/collectstatic/seed_taxonomy/etc. Only preload for the
    processes that actually serve requests or run tasks and stay warm:
    gunicorn, Celery workers, and `runserver`'s actual serving process (its
    autoreloader first runs a watcher parent that never serves anything --
    RUN_MAIN is only set in the reloaded child)."""
    argv0 = sys.argv[0] if sys.argv else ""
    if "gunicorn" in argv0 or "celery" in argv0:
        return True
    if len(sys.argv) > 1 and sys.argv[1] == "runserver":
        return os.environ.get("RUN_MAIN") == "true"
    return False
