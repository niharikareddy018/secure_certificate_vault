# Use official Python image to avoid Nixpacks virtualenv/encodings issues
FROM python:3.11-slim

# Ensure Python behaves well in containers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Workdir
WORKDIR /app

# System dependencies often needed for psycopg2, web3, and building wheels
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
      curl \
      ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /app/backend/requirements.txt

# Copy the rest of the app
COPY . /app

# Default port (Railway will inject PORT)
ENV PORT=8000

# Document container port
EXPOSE 8000

# Container healthcheck: rely on /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD sh -c "curl -fsS http://localhost:${PORT:-8000}/health || exit 1"

# Start gunicorn binding to the injected PORT
# Use shell form with double quotes so $PORT expands; default to 8000 if unset
CMD sh -c "gunicorn backend.app:app --bind 0.0.0.0:${PORT:-8000}"
