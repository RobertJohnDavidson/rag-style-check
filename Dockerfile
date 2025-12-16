# Multi-stage build for CBC News Style Checker

# Stage 1: Build frontend using Bun
FROM oven/bun:latest AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json ./

RUN bun install

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN bun run build

# Stage 2: Python backend
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy Python configuration and source
COPY pyproject.toml ./
COPY src/ ./src/

# Install Python dependencies and the package itself
# This uses pyproject.toml (requires src/ to be present for setuptools)
RUN pip install --no-cache-dir .

# Download spacy model
# Spacy removed
# RUN python -m spacy download en_core_web_sm

# Copy runner script
COPY run_server.py ./

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Expose port (Cloud Run will set PORT env var, default to 8080)
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the server
CMD ["python", "run_server.py", "--production"]