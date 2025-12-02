# Multi-stage build for CBC News Style Checker

# Stage 1: Build frontend using Bun
FROM oven/bun:latest AS frontend-builder

WORKDIR /app/frontend


COPY frontend/package.json ./
COPY frontend/bun.lockb ./
COPY frontend/src ./

RUN bun install

# Copy frontend source
COPY frontend/ ./

# Build frontend with Bun
RUN bun run build

# Stage 2: Python backend
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download spacy model
RUN python -m spacy download en_core_web_sm

# Copy backend source
COPY src/ ./src/
COPY run_server.py ./

# Copy ChromaDB database
COPY db/ ./db/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Expose ports
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Run the server
CMD ["python", "run_server.py", "--production", "--host", "0.0.0.0", "--port", "8000"]
