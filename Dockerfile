# AbEngineCore — Self-contained production image
# No external AI agent dependency. All computation is local and deterministic.
#
# Build (CPU-only):
#   docker build -t abenginecore:v4.9.1 .
#
# Build (GPU):
#   docker build --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cu121 \
#                -t abenginecore:v4.9.1-gpu .
#
# Run:
#   docker run -p 8000:8000 -v abenginecore_jobs:/app/.job_storage abenginecore:v4.9.1
#   Then open http://localhost:8000 in a browser.

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    KMP_DUPLICATE_LIB_OK=TRUE

WORKDIR /app

# System libs needed by BioPython (C extensions) and reportlab
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libatlas-base-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# ── 1. Install Python dependencies ──────────────────────────────────────────
COPY requirements.txt requirements-api.txt ./

# Allow caller to override torch wheel index for GPU builds
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
RUN pip install --upgrade pip && \
    pip install torch --index-url ${TORCH_INDEX} && \
    pip install -r requirements.txt -r requirements-api.txt

# ── 2. Copy application code and data ───────────────────────────────────────
COPY api     ./api
COPY core    ./core
COPY config  ./config
COPY pipeline ./pipeline
COPY scripts ./scripts
COPY data    ./data

# ── 3. Pre-download ML model weights at build time ──────────────────────────
# This bakes model weights into the image so runtime has zero external calls.
# IgFold weights (~200 MB) and ImmuneBuilder weights (~300 MB) are cached here.
RUN python -c "from igfold import IgFoldRunner; IgFoldRunner()" || true
RUN python -c "from immunebuilder import ABodyBuilder2; ABodyBuilder2()" || true
RUN python -c "import ablang2; ablang2.pretrained()" || true

# ── 4. Metadata ─────────────────────────────────────────────────────────────
ARG ABENGINECORE_GIT_SHA=
ENV ABENGINECORE_GIT_SHA=${ABENGINECORE_GIT_SHA} \
    ABENGINECORE_VERSION=4.9.1

EXPOSE 8000

# Persist job storage and any uploaded PDB files across container restarts
VOLUME ["/app/.job_storage", "/app/api/.data"]

# ── 5. Health check ─────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
