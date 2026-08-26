# =============================================================================
# Spresy — Self-contained Docker image
# Builds the React frontend, then serves it alongside the FastAPI backend.
# Usage:
#   docker build -t spresy .
#   docker run -p 9000:9000 --env-file backend/.env spresy
# =============================================================================

# ---- Stage 1: Build the frontend ----
FROM node:20-slim AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts

COPY frontend/ ./
RUN npm run build


# ---- Stage 2: Python backend + built frontend ----
FROM python:3.12-slim

# System deps for lxml, psycopg2-binary, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend from Stage 1
COPY --from=frontend-build /build/frontend/dist ./frontend/dist

# Create output directory for CSV exports
RUN mkdir -p /app/backend/output

# Environment: tell the backend to serve the built frontend
ENV SERVE_FRONTEND=true
ENV OUTPUT_DIR=/app/backend/output
ENV PYTHONUNBUFFERED=1

EXPOSE 9000

# Run from the backend directory so relative paths (like .env, spresy.db) work
WORKDIR /app/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
