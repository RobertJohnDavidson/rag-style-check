#!/bin/bash
# scripts/run_docker_local.sh

# This script runs the Docker container locally, injecting your
# local Google Application Default Credentials (ADC).
# This mimics the Service Account environment of Cloud Run.

set -e

# 1. Locate ADC file
ADC_FILE="${HOME}/.config/gcloud/application_default_credentials.json"

if [ ! -f "$ADC_FILE" ]; then
    echo "❌ Error: Application Default Credentials not found at $ADC_FILE"
    echo "👉 Please run: gcloud auth application-default login"
    exit 1
fi

echo "✅ Found ADC: $ADC_FILE"

# 2. Run Docker Compose
# We use -f to specify the file (standard)
# We use -v to mount the ADC file to a specific location
# We use -e to tell Google libraries where to find it

echo "🚀 Starting CBC Style Checker (Local)..."
echo "   - Mounting ADC to /app/config/adc.json"
echo "   - Setting GOOGLE_APPLICATION_CREDENTIALS"

# We can't easily add volumes/envs to 'docker-compose up' via CLI flags in the same way as 'docker run'.
# Instead, we will generate a temporary override file or use environment variables if the compose file supported them.
# But since we want to keep the compose file clean, let's use a temporary override file.

cat > docker-compose.override.yml <<EOF
services:
  backend:
    volumes:
      - ${ADC_FILE}:/app/config/adc.json:ro
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/config/adc.json
EOF

# Trap to clean up the override file on exit
trap 'rm -f docker-compose.override.yml' EXIT

# Run compose
docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build "$@"
