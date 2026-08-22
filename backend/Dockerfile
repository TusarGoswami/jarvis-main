# ==============================================================================
# VOCALIS AI — BACKEND DOCKERFILE (Production AWS / Container Deployment)
# Multi-arch compatible (x86_64, arm64), slim footprint, security-hardened.
# ==============================================================================

FROM python:3.12-slim-bookworm as base

# Prevents Python from writing pyc files to disc and enables unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOST=0.0.0.0 \
    PORT=8005

WORKDIR /app

# Install system runtime dependencies (audio, speech, visual processing, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    libportaudio2 \
    alsa-utils \
    libgl1 \
    libglib2.0-0 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for optimal Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create non-root user and setup permissions for secure execution
RUN groupadd -r vocalis && useradd -r -g vocalis -m -d /home/vocalis vocalis && \
    mkdir -p /home/vocalis/.jarvis /app/workspace /app/logs && \
    chown -R vocalis:vocalis /app /home/vocalis

USER vocalis

# Expose backend application port (default 8005 or dynamic AWS PORT)
EXPOSE 8005

# Container Healthcheck for AWS ECS / ALB / App Runner
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8005}/ || exit 1

# Launch production ASGI server with uvicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8005}"]
