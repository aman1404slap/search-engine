# Video Search POC

Django + DRF backend, a small React (Vite) SPA, SQLite, local Redis, and a
self-hosted sentence-embedding model. Upload a JSONL of ego-assist video
records, they're matched to S3, thumbnailed, embedded, and become browsable +
natural-language searchable with confidence-scored timestamp spans.

See `SEARCH_ARCHITECTURE_BLUEPRINT.md` for the original backend-only design
this POC extends with a UI, SQLite/Redis-for-local-dev, and a taxonomy admin.

## Prerequisites

- Python 3.12+ (a `.venv` is already set up at the repo root)
- Node 20+ / npm
- `redis-server`, `ffmpeg`/`ffprobe` on PATH
- AWS credentials that can read `s3://ssai-staging-us-east-2/Be-My-Eyes/`.
  boto3 uses the standard credential chain — either a profile in
  `~/.aws/credentials` or `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/
  `AWS_SESSION_TOKEN` exported in the terminal you run the server/worker
  from. No AWS config lives in this repo.

## One-time setup

```bash
# Python deps (venv already created at repo root)
source .venv/bin/activate
pip install -r backend/requirements.txt

# Frontend deps
cd frontend && npm install && cd ..

# Env config (defaults are already sensible for local dev)
cp .env.example .env
```

## Running it

Four processes, each in its own terminal (all from the repo root unless noted):

```bash
# 1. Redis (cache + Celery broker)
redis-server --daemonize yes   # or just `redis-server` in a foreground terminal

# 2. Django API
source .venv/bin/activate
cd backend
python manage.py migrate
python manage.py seed_taxonomy        # idempotent, seeds taxonomy.txt into the DB
python manage.py runserver 0.0.0.0:8000

# 3. Celery worker (background thumbnail/embedding pipeline)
source .venv/bin/activate
cd backend
celery -A config worker --loglevel=info

# 4. Frontend
cd frontend
npm run dev
```

Open **http://localhost:5173**.

For quick local testing without a Celery worker running, set
`CELERY_TASK_ALWAYS_EAGER=true` in `.env` — uploads then process
synchronously inside the request/response cycle instead of being queued.

## Loading the 200-video dataset

The repo already includes the real dataset at
`video-audit_runs_ego_full_bemyeyes_20260418_semantic_v2_ego_assist.jsonl`.
Load it either through the UI's "Upload JSONL" button, or from the CLI
(useful the first time, since it doesn't need Celery running):

```bash
cd backend
python manage.py ingest_jsonl ../video-audit_runs_ego_full_bemyeyes_20260418_semantic_v2_ego_assist.jsonl
```

This upserts `Video`/`VideoTag`/`Segment` rows for every line, then
synchronously fetches each video's presigned S3 URL, extracts a thumbnail
with ffmpeg, and computes sentence-embeddings for every segment — so the
grid, filters, and natural-language search all work immediately without a
running worker. Re-running it is safe (upsert by `shot_id`). Pass
`--skip-media` to load metadata only (fast) and defer thumbnails/embeddings
to a Celery worker later.

Uploading additional JSONL files later (through the UI or the same command)
adds/updates videos the same way — the taxonomy is shared and static, videos
accumulate.

## How a video is found

- **Metadata**: parsed from each JSONL line's `request_case`/`assist`/`events`.
- **S3 key**: derived from `provenance.source` (e.g.
  `/mnt/experiments/Be-My-Eyes/Sample_Data/Phone/_all-clips-001/4748416.mp4`)
  by stripping the `/mnt/experiments/` prefix, giving the key relative to the
  `ssai-staging-us-east-2` bucket root. Playback uses a short-lived presigned
  URL fetched on demand — no video files are stored locally, only thumbnails.
- **Search**: a local `all-MiniLM-L6-v2` sentence-transformer embeds every
  event-level segment at ingest time; a query is embedded the same way and
  fused with a BM25 keyword score (`apps/search/ranking.py`) inside the
  facet filters currently active. Matching segments are merged into
  contiguous spans and returned with a confidence score, rendered as the
  colored timeline under the player.

## Project layout

```
backend/            Django project (config/ + apps/{taxonomy,videos,ingestion,search})
frontend/            React (Vite) SPA
taxonomy.txt          static taxonomy definition, seeded via manage.py seed_taxonomy
*.jsonl               the 200-video dataset
SEARCH_ARCHITECTURE_BLUEPRINT.md   original backend-only design doc
```

## Known limitations (POC scope)

- ~half the dataset (the "Meta" smart-glasses source) has empty capture
  metadata (`duration`, caller location, etc.) — the UI falls back to the
  actual media duration read from the video element in that case.
- No auth — everything is open on localhost, as expected for a local POC.
- Embeddings run on CPU by default (fast enough at this scale); install a
  CUDA build of `torch` if you want `sentence-transformers` to use the GPU.
