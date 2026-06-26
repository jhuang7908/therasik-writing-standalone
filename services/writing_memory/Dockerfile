# InSynBio Writing-Memory — production image
# Build context: this directory (services/writing_memory)
# Run:   docker build -t insynbio/writing-memory:latest .
#        docker run -p 8100:8100 --env-file .env -v $(pwd)/data:/app/data insynbio/writing-memory:latest

FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps — lxml; Vale (prose lint); Quarto (DOCX/PDF render)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libxml2 libxslt1.1 ca-certificates curl unzip \
    && VALE_VER=3.14.2 \
    && curl -fsSL -o /tmp/vale.zip \
         "https://github.com/errata-ai/vale/releases/download/v${VALE_VER}/vale_${VALE_VER}_Linux_64-bit.tar.gz" \
    && tar -xzf /tmp/vale.zip -C /usr/local/bin vale \
    && rm /tmp/vale.zip \
    && curl -fsSL https://quarto.org/download/latest/quarto-linux-amd64.deb -o /tmp/quarto.deb \
    && apt-get install -y /tmp/quarto.deb \
    && rm /tmp/quarto.deb \
    && rm -rf /var/lib/apt/lists/*

# Python deps first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Application code
COPY . /app/

# Quota DB and embedding index live under /app/data — mount a host volume here
RUN mkdir -p /app/data

EXPOSE 8100

# Healthcheck — fail container if /health stops responding
HEALTHCHECK --interval=30s --timeout=8s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8100/health || exit 1

# Run from project root so module path `services.writing_memory.app` resolves.
# `--proxy-headers` makes uvicorn honor X-Forwarded-For from nginx (required for quota).
CMD ["python", "-m", "uvicorn", "app:app", \
     "--host", "0.0.0.0", "--port", "8100", \
     "--proxy-headers", "--forwarded-allow-ips", "*", \
     "--workers", "1", "--log-level", "info"]
