# ==============================================================================
# VOCALIS AI — BACKEND DOCKERFILE (Fast & Optimized Production Build)
# ==============================================================================

FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOST=0.0.0.0 \
    PORT=8005

WORKDIR /app

# Install only essential lightweight runtime packages (no heavy compiler toolchains)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    libportaudio2 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install pre-built binary Python wheels (fast, no compilation needed)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy backend source code
COPY . .

# Setup non-root user and persistent folders
RUN groupadd -r vocalis && useradd -r -g vocalis -m -d /home/vocalis vocalis && \
    mkdir -p /home/vocalis/.jarvis /app/workspace /app/logs && \
    chown -R vocalis:vocalis /app /home/vocalis

USER vocalis

EXPOSE 8005

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8005}/ || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8005}"]
