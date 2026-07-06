FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
# taxonomy.txt lives at the repo root, not under backend/ -- placed one level
# above the app dir so it lands at REPO_ROOT/taxonomy.txt (settings.py's
# default TAXONOMY_TXT_PATH), matching the checkout's actual layout.
COPY taxonomy.txt /taxonomy.txt

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
