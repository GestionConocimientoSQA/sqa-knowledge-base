# ============================================================
# SQA KB Backend — Multi-stage Dockerfile para Azure Container Apps
# ============================================================
# Build:
#   docker build -t sqa-kb-backend apps/backend
# Run:
#   docker run -p 8000:8000 --env-file ../../.env sqa-kb-backend
# ============================================================

FROM python:3.12-slim AS builder
WORKDIR /build
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -e .

# ------------------------------------------------------------
FROM python:3.12-slim AS runner
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd -r app --gid 1001 \
 && useradd -r -g app --uid 1001 app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/src ./src

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "sqa_kb.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
