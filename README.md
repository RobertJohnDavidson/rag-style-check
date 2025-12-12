# Style Guide Auditor (RAG Pipeline)

This project is a RAG-based system that audits text against the CBC News style guide. It uses semantic search (Google Gemini Embeddings) to retrieve relevant style rules and an LLM to verify violations.

## Features

*   **RAG Pipeline**: Vector database with semantic search for style guide rules
*   **Agentic Auditor**: Multi-iteration refinement with self-reflection
*   **REST API**: FastAPI backend for text auditing
*   **Modern Frontend**: SvelteKit 5 UI with Tailwind CSS
*   **Docker Support**: Containerized deployment with Docker Compose

## Quick Start with Docker

### Production Deployment

```bash
# Build and run
docker compose up -d

# Check logs
docker compose logs -f backend

# Access the API
curl http://localhost:8000/health
```

### Development Mode

```bash
# Run with frontend dev server
docker compose --profile dev up -d
```

See [DOCKER.md](DOCKER.md) for detailed Docker deployment instructions.

## Local Development

### Prerequisites

*   Python 3.10+
*   Node.js 20+
*   Google API Key (for Gemini)

### Backend Setup

1.  **Install dependencies**:
    ```bash
    pip install -e .
    ```

2.  **Create `.env` file**:
    ```ini
    PROJECT_NAME=cbc-style-checker
    ```

3.  **Run the API server**:
    ```bash
    python run_server.py
    ```

### Frontend Setup

```bash
cd frontend
# Install dependencies with bun (or use npm/yarn if you prefer)
bun install
# Run dev server
bun run dev -- --host 0.0.0.0
```

## Usage

## Usage

### API Endpoints

**Audit Text:**
```bash
curl -X POST http://localhost:8000/audit \
  -H "Content-Type: application/json" \
  -d '{"text": "The government announced a new policy today."}'
```

**Health Check:**
```bash
curl http://localhost:8000/health
```

**API Documentation:**
Visit `http://localhost:8000/docs` for interactive API documentation.

### Programmatic Usage

```python
from src.core.auditor import StyleAuditor

auditor = StyleAuditor()
violations = auditor.check_text("The government needs to do more for Aboriginal housing.")

for v in violations:
    print(f"Rule: {v['rule_name']}")
    print(f"Issue: {v['violation']}")
    print(f"Text: {v['text']}")
```

### Run Tests

```bash
# Run all tests
.venv/bin/python tests/run_tests.py --file tests/generated_tests_complex.json

# Run first 10 tests
.venv/bin/python tests/run_tests.py --file tests/generated_tests_complex.json --limit 10
```

## Architecture

- **Backend**: FastAPI + LlamaIndex + ChromaDB + Google Gemini
- **Frontend**: SvelteKit 5 + Tailwind CSS
- **Database**: ChromaDB (vector store for style guide rules)
- **LLM**: Google Gemini 2.5-flash for rule verification
- **Embeddings**: Google text-embedding-004

## Project Structure

```
.
├── src/
│   ├── api/          # FastAPI server
│   ├── core/         # Auditor logic
│   ├── data/         # Ingestion scripts
│   └── legacy/       # Old implementations
├── frontend/         # SvelteKit UI
├── tests/            # Test suite
├── db/               # ChromaDB database
├── Dockerfile        # Container image
├── docker-compose.yml # Orchestration
└── run_server.py     # Server entry point
```
