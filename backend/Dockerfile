# syntax=docker/dockerfile:1
# The line above pins the BuildKit Dockerfile frontend so `RUN --mount=type=secret`
# below is always supported, regardless of the local daemon's default.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the search models into the image so every container built from
# it (backend, celery -- both use this same Dockerfile) already has them on
# local disk. Without this, each process's first-ever get_model()/
# get_cross_encoder() call hits the network, and a multi-process Celery
# worker's children each do this independently, which is what shows up in
# logs as the "same model downloading" repeatedly after a fresh deploy.
# Defaults must match apps/search/embedding.py + reranker.py's env defaults
# (config/settings.py EMBEDDING_MODEL_NAME / SEARCH_RERANK_MODEL_NAME) --
# overriding those env vars at runtime to a different model falls back to a
# normal on-demand download for that model, same as before this change.
# HF_TOKEN is passed as a BuildKit secret (not an ARG/ENV) so it never gets
# baked into an image layer or shows up in `docker history` -- it's mounted
# read-only for this RUN only, then gone. Both public models below don't
# strictly require it, but without it every build hits the Hub anonymously,
# which is what a "sending unauthenticated request" log line at build time
# means; passing the token (docker-compose.dev.yml wires this secret up from
# the HF_TOKEN in .env) avoids that and raises the anonymous rate limit.
ARG EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
ARG SEARCH_RERANK_MODEL_NAME=cross-encoder/ms-marco-MiniLM-L-6-v2
RUN --mount=type=secret,id=hf_token \
    HF_TOKEN="$(cat /run/secrets/hf_token 2>/dev/null || true)" \
    python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('$EMBEDDING_MODEL_NAME'); CrossEncoder('$SEARCH_RERANK_MODEL_NAME')"

COPY backend/ .
# taxonomy.txt lives at the repo root, not under backend/ -- placed one level
# above the app dir so it lands at REPO_ROOT/taxonomy.txt (settings.py's
# default TAXONOMY_TXT_PATH), matching the checkout's actual layout.
COPY taxonomy.txt /taxonomy.txt

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
