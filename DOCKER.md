# Docker Deployment Guide

## Quick Start

### Production Build (Backend Only)

```bash
# Build and run
docker compose up -d

# View logs
docker compose logs -f backend

# Stop
docker compose down
```

The API will be available at `http://localhost:8000`

### Development Mode (Backend + Frontend)

```bash
# Run with frontend dev server
docker compose --profile dev up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_api_key_here
PROJECT_NAME=cbc-style-checker
```

## Building the Image

```bash
# Build the image
docker build -t cbc-style-checker .

# Run the container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/db:/app/db \
  -e GOOGLE_API_KEY=your_key \
  --name style-checker \
  cbc-style-checker
```

## Health Check

```bash
curl http://localhost:8000/health
```

## Volume Mounts

- `./db:/app/db` - ChromaDB database persistence
- `./.env:/app/.env:ro` - Environment variables (read-only)

## Troubleshooting

### Check container logs
```bash
docker compose logs backend
```

### Access container shell
```bash
docker compose exec backend bash
```

### Rebuild after code changes
```bash
docker compose build --no-cache
docker compose up -d
```

## Production Deployment

For production deployment to cloud platforms:

### Google Cloud Run

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/style-checker

# Deploy
gcloud run deploy style-checker \
  --image gcr.io/PROJECT_ID/style-checker \
  --platform managed \
  --region us-central1 \
  --set-env-vars GOOGLE_API_KEY=your_key
```

### AWS ECS / Azure Container Apps

Update the `docker-compose.yml` or create platform-specific configuration files as needed.
