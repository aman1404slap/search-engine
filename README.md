# Video Search POC

Django + DRF backend, a small React (Vite) SPA, Postgres, Redis, and a
self-hosted sentence-embedding model, all behind a login. Upload a JSONL of
ego-assist video records, they're matched to S3, thumbnailed, embedded, and
become browsable + natural-language searchable with confidence-scored
timestamp spans.

See `SEARCH_ARCHITECTURE_BLUEPRINT.md` for the original backend-only design
this POC extends with a UI, Postgres/Redis-in-Docker, auth, and a taxonomy
admin.

## Prerequisites

- Docker + Docker Compose v2 (`docker compose version` must work)
- AWS credentials that can read `s3://ssai-staging-us-east-2/Be-My-Eyes/`.
  boto3 uses the standard credential chain; export temporary
  `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_SESSION_TOKEN` in the same
  terminal you run `docker compose up` from and they're passed through into
  the `backend`/`celery` containers. No AWS config lives in this repo.

## One-time setup

```bash
cp .env.example .env   # defaults are already sensible for local dev
```

## Running it locally

```bash
docker compose -f docker-compose.dev.yml up --build
```

This starts five containers: `db` (Postgres), `redis`, `backend` (Django,
auto-runs migrations + taxonomy seeding + superadmin bootstrap on every
start), `celery` (the thumbnail/embedding worker), and `frontend` (Vite dev
server). Source in `backend/` and `frontend/` is bind-mounted, so code edits
take effect immediately — Django's autoreload and Vite's HMR both work as
normal. The first `up` is slower (image build + `npm install`); later ones
reuse the cache and are fast unless `requirements.txt`/`package.json`
changed.

Open **http://localhost:5173** and log in (see below).

Postgres data persists across restarts locally (named volume) — only the
deployed environment wipes it on every deploy.

## Logging in / creating users

The backend bootstraps one superadmin on every startup, from
`DJANGO_SUPERUSER_USERNAME`/`DJANGO_SUPERUSER_PASSWORD` in `.env` (defaults:
`admin` / `change-me` locally — change these).

To create additional accounts:
1. Go to **http://localhost:8000/admin/** and log in with the superadmin
   credentials.
2. **Users → Add user**, set a username/password. Leave "Staff status"
   unchecked unless that person also needs `/admin/` access.
3. That user can now log into the app itself at **http://localhost:5173**
   with the same credentials.

The whole site (every API endpoint, thumbnails, the app itself) requires
being logged in.

## Loading the 200-video dataset

The repo already includes the real dataset at
`video-audit_runs_ego_full_bemyeyes_20260418_semantic_v2_ego_assist.jsonl`.
Once you're logged in, load it either through the UI's "Upload JSONL"
button, or from the CLI:

```bash
docker compose -f docker-compose.dev.yml exec backend \
  python manage.py ingest_jsonl /host/video-audit_runs_ego_full_bemyeyes_20260418_semantic_v2_ego_assist.jsonl
```

(`/host` is the repo root, read-only-mounted into the `backend` container
specifically so this command can reach dataset files that live outside
`backend/` — see `docker-compose.dev.yml`.)

This upserts `Video`/`VideoTag`/`Segment` rows for every line, then
synchronously fetches each video's presigned S3 URL, extracts a thumbnail
with ffmpeg, and computes sentence-embeddings for every segment — so the
grid, filters, and natural-language search all work immediately without
waiting on the Celery worker. Re-running it is safe (upsert by `shot_id`).
Pass `--skip-media` to load metadata only (fast) and defer thumbnails/
embeddings to the `celery` container.

**In the deployed environment, this must be repeated after every deploy** —
Postgres is intentionally wiped on each deploy (see Deployment below), so
re-upload the dataset via the UI once the new deploy is up.

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

## Deployment

CircleCI (`.circleci/config.yml`) builds and deploys on every push to
`main`:
1. **`test-backend`** — Django checks + tests against Postgres/Redis
   service containers.
2. **`build-and-push`** — builds `backend/Dockerfile` and
   `frontend/Dockerfile`, pushes both to ECR tagged with the commit SHA and
   `latest`.
3. **`deploy`** — copies `docker-compose.prod.yml` to the EC2 host over
   `scp`, then SSHes in and runs `docker compose down && pull && up -d`.

The deployed stack is a single EC2 instance running five containers via
`docker-compose.prod.yml`: `frontend` (nginx serving the built SPA and
reverse-proxying `/api`, `/admin`, `/static`, `/media` to `backend` —
same-origin, so no CORS/cookie complications), `backend` (gunicorn),
`celery`, `db` (Postgres), `redis`. Currently plain HTTP, no TLS.

**Postgres has no persistent volume in prod on purpose** — every deploy
starts from an empty database (migrations + taxonomy seeding + superadmin
bootstrap run fresh each time). This also means any extra users created via
`/admin` are wiped along with the video data on each deploy; re-create them
if needed. The JSONL dataset must be re-uploaded via the UI after each
deploy.

Secrets (DB password, `DJANGO_SECRET_KEY`, superadmin password, AWS creds)
live only in a hand-created `.env` file on the EC2 host itself (see
`.env.prod.example` for the template) — CircleCI never sees them. CircleCI
only needs, in a context named `video-search-aws`: AWS credentials that can
push to ECR (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/
`AWS_DEFAULT_REGION`), `ECR_REGISTRY` (your ECR account's registry
hostname), `SSH_HOST`, `SSH_USER`, plus an SSH deploy key added via
CircleCI's project **SSH Keys** settings (its fingerprint goes into
`.circleci/config.yml`'s `deploy` job).

### One-time AWS setup (do this once, by hand, before the first deploy)

1. Launch an EC2 instance (Ubuntu; something with enough headroom to run
   Postgres/Redis alongside the embedding/reranker models in memory —
   `t3.large` or bigger). Security group: allow port 22 (SSH, restrict to
   your IP) and port 80 (HTTP, open).
2. Install Docker Engine + the Compose v2 plugin (`docker compose version`
   must work — the compose files use `depends_on: condition:
   service_healthy`, which needs v2).
3. Add the CircleCI deploy key's public half to the instance's
   `~/.ssh/authorized_keys`.
4. `mkdir ~/video-search` on the instance; copy `.env.prod.example` there
   as `.env` and fill in real values. Prefer attaching an IAM instance role
   with S3 read access over static AWS keys if convenient.
5. `aws ecr create-repository --repository-name video-search-backend` and
   same for `video-search-frontend`.
6. In CircleCI, create a context named `video-search-aws` with the env vars
   listed above, and add the SSH deploy key under project settings.

## Project layout

```
backend/                     Django project (config/ + apps/{accounts,taxonomy,videos,ingestion,search})
frontend/                    React (Vite) SPA
docker-compose.dev.yml       local dev: bind-mounted source, live reload
docker-compose.prod.yml      deployment: pre-built images from ECR
.circleci/config.yml         test -> build & push images -> deploy
taxonomy.txt                 static taxonomy definition, seeded via manage.py seed_taxonomy
*.jsonl                      the 200-video dataset
SEARCH_ARCHITECTURE_BLUEPRINT.md   original backend-only design doc
```

## Known limitations (POC scope)

- ~half the dataset (the "Meta" smart-glasses source) has empty capture
  metadata (`duration`, caller location, etc.) — the UI falls back to the
  actual media duration read from the video element in that case.
- Plain HTTP in the deployed environment — no TLS yet.
- Postgres is wiped on every deploy — this is intentional for the POC, not
  a bug (see Deployment).
- Embeddings run on CPU by default (fast enough at this scale); install a
  CUDA build of `torch` if you want `sentence-transformers` to use the GPU.
