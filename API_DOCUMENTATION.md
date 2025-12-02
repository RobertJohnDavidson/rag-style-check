# CBC News Style Checker API Documentation

## Overview

A FastAPI-based REST API for auditing text against CBC News style guidelines using RAG (Retrieval-Augmented Generation). The system retrieves relevant style rules from a ChromaDB vector database and uses Google's Gemini LLM to identify violations.

## Architecture

```
┌─────────────┐
│   Client    │
│  (Frontend) │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────────────────────────┐
│      FastAPI Server (Port 8000)     │
│  ┌───────────────────────────────┐  │
│  │  API Endpoints (/audit, etc)  │  │
│  └───────────┬───────────────────┘  │
│              │                       │
│  ┌───────────▼───────────────────┐  │
│  │   StyleAuditor (Singleton)    │  │
│  │  - RAG retrieval              │  │
│  │  - Agentic refinement         │  │
│  │  - LLM analysis               │  │
│  └───────────┬───────────────────┘  │
└──────────────┼───────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌─────────┐         ┌──────────┐
│ChromaDB │         │ Google   │
│Vector DB│         │ Gemini   │
│(Rules)  │         │ LLM      │
└─────────┘         └──────────┘
```

## Getting Started

### Installation

```bash
# Install dependencies
pip install fastapi "uvicorn[standard]" pydantic

# Or use requirements.txt
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
# Google Cloud Configuration
PROJECT_NAME=your-gcp-project-id
REGION=us-central1

# Model Configuration
MODEL=models/gemini-2.5-flash
EMBEDDING_MODEL=models/text-embedding-004

# Database
DB_PATH=./db/chroma_db
COLLECTION_NAME=cbc_style_guide

# API Security (change in production!)
API_KEY=dev-key-change-in-production
```

### Starting the Server

```bash
# Development mode (auto-reload on code changes)
python run_server.py

# Production mode (no auto-reload)
python run_server.py --production

# Custom port
python run_server.py --port 3000

# Custom host and port
python run_server.py --host 127.0.0.1 --port 8080
```

### Interactive API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### 1. Health Check

```http
GET /
```

**Response:**
```json
{
  "service": "CBC News Style Checker",
  "status": "healthy",
  "version": "1.0.0"
}
```

---

### 2. Audit Text

```http
POST /audit
Content-Type: application/json
```

**Request Body:**
```json
{
  "text": "The Cabinet met yesterday to discuss the Alberta government's new policy.",
  "model": "models/gemini-2.5-flash"  // Optional
}
```

**Response:**
```json
{
  "violations": [
    {
      "text": "Cabinet",
      "rule": "Cabinet",
      "reason": "Should be lowercase 'cabinet' when referring to the federal or provincial cabinet in general.",
      "source_url": "https://www.cbc.ca/newsinteractives/style/cabinet"
    },
    {
      "text": "Alberta government",
      "rule": "Government",
      "reason": "Should be 'Alberta Government' with capital G when referring to the specific governing body.",
      "source_url": "https://www.cbc.ca/newsinteractives/style/government"
    }
  ],
  "metadata": {
    "processing_time_seconds": 2.45,
    "model": "models/gemini-2.5-flash",
    "violation_count": 2
  }
}
```

**How it works:**
1. Splits text into paragraphs
2. For each paragraph, extracts sentences
3. Retrieves relevant style rules from ChromaDB using sentence embeddings
4. Applies keyword-based backup retrieval if < 10 rules found
5. Performs agentic analysis with up to 3 refinement iterations
6. Deduplicates violations across paragraphs
7. Returns violations with explanations and source URLs

---

### 3. List Available Models

```http
GET /models
```

**Response:**
```json
[
  {
    "name": "gemini-2.5-flash",
    "description": "Fast, cost-effective model for production use",
    "available": true
  },
  {
    "name": "gemini-1.5-pro",
    "description": "More capable model for complex cases",
    "available": true
  },
  {
    "name": "gemini-1.5-flash",
    "description": "Previous generation fast model",
    "available": true
  }
]
```

---

### 4. Create Test Suite (Protected)

```http
POST /tests
Content-Type: application/json
X-API-Key: your-api-key-here
```

**Request Body:**
```json
{
  "suite_name": "december_2024_tests",
  "test_cases": [
    {
      "id": "test_001",
      "text": "The Cabinet announced new measures today.",
      "expected_violations": [
        {
          "rule": "Cabinet",
          "text": "Cabinet",
          "source_url": "https://www.cbc.ca/newsinteractives/style/cabinet"
        }
      ]
    }
  ]
}
```

**Response:**
```json
{
  "message": "Test suite created successfully",
  "filename": "tests/december_2024_tests_20251201_143022.json",
  "test_count": 1
}
```

**Authentication:**
- Requires `X-API-Key` header
- Default key (dev): `dev-key-change-in-production`
- Configure via `API_KEY` environment variable

---

### 5. Run Test Suite (Protected)

```http
POST /tests/run
Content-Type: application/json
X-API-Key: your-api-key-here
```

**Request Body:**
```json
{
  "file_path": "tests/generated_tests_complex.json"
}
```

**Response:**
```json
{
  "true_positives": 12,
  "false_positives": 0,
  "false_negatives": 6,
  "true_negatives": 2,
  "metrics": {
    "precision": 1.0,
    "recall": 0.667,
    "f1_score": 0.8
  },
  "test_details": [
    {
      "id": "complex_real_1",
      "expected_count": 5,
      "actual_count": 3,
      "true_positives": 3,
      "false_negatives": 2,
      "false_positives": 0
    }
  ]
}
```

**Metrics Explained:**
- **True Positive (TP)**: Correctly identified violation
- **False Positive (FP)**: Incorrectly flagged non-violation
- **False Negative (FN)**: Missed actual violation
- **True Negative (TN)**: Correctly ignored clean text
- **Precision**: TP / (TP + FP) - How many flagged violations were correct
- **Recall**: TP / (TP + FN) - How many actual violations were found
- **F1 Score**: Harmonic mean of precision and recall

---

### 6. Detailed Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "auditor_initialized": true,
  "timestamp": "2025-12-01T14:30:45.123456"
}
```

---

## Request/Response Schemas

### Violation Schema
```python
{
  "text": str,          # The violating text snippet
  "rule": str,          # Rule name from style guide
  "reason": str,        # Why this violates the rule
  "source_url": str?    # Optional URL to style guide section
}
```

### AuditRequest Schema
```python
{
  "text": str,          # Text to audit (required)
  "model": str?         # Optional model override
}
```

### TestCase Schema
```python
{
  "id": str,                      # Unique test identifier
  "text": str,                    # Text to audit
  "expected_violations": [        # Expected violations list
    {
      "rule": str,
      "text": str,
      "source_url": str?
    }
  ]
}
```

---

## CORS Configuration

The server is configured to allow all origins for development:

```python
allow_origins=["*"]  # Configure this for production!
```

**Production recommendation:**
```python
allow_origins=[
    "https://yourdomain.com",
    "https://app.yourdomain.com"
]
```

---

## Error Handling

### Standard Error Response
```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

| Code | Meaning | Cause |
|------|---------|-------|
| 200 | Success | Request completed successfully |
| 201 | Created | Test suite created successfully |
| 403 | Forbidden | Invalid or missing API key |
| 404 | Not Found | Test file doesn't exist |
| 500 | Internal Server Error | Auditor failure, LLM timeout, etc. |

---

## Performance Considerations

### Auditor Initialization
- The `StyleAuditor` is initialized as a **singleton**
- First request may be slow (~5-10s) due to:
  - ChromaDB connection
  - Vector index loading
  - Reranker initialization
- Subsequent requests are much faster (~1-3s)

### Request Processing Time
Typical `/audit` endpoint timing:
- Simple paragraph (1-2 sentences): 1-2 seconds
- Complex paragraph (5+ sentences): 2-4 seconds
- Multiple paragraphs: 3-6 seconds

Factors affecting speed:
- Number of paragraphs
- Number of sentences per paragraph
- Agentic iteration count (1-3 iterations)
- LLM response time

### Optimization Tips
1. **Batch processing**: For multiple texts, consider implementing a batch endpoint
2. **Caching**: Add Redis for repeated identical requests
3. **Async processing**: For UI responsiveness, use background tasks with job IDs
4. **Model selection**: `gemini-2.5-flash` is fastest, `gemini-1.5-pro` is most accurate

---

## Security

### API Key Authentication

Protected endpoints require authentication:
```bash
curl -X POST http://localhost:8000/tests \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{"test_cases": [...]}'
```

### Production Checklist
- [ ] Change `API_KEY` environment variable
- [ ] Configure CORS origins whitelist
- [ ] Enable HTTPS/TLS
- [ ] Add rate limiting (e.g., `slowapi`)
- [ ] Implement user authentication/authorization
- [ ] Add request logging and monitoring
- [ ] Set up proper error tracking (Sentry, etc.)

---

## Development

### Project Structure
```
src/
├── api/
│   ├── server.py      # FastAPI app and endpoints
│   └── schemas.py     # Pydantic models
├── core/
│   ├── auditor.py     # Main StyleAuditor class
│   └── reranker.py    # VertexAI reranker
└── data/
    └── ingest.py      # ChromaDB ingestion
```

### Adding New Endpoints

1. Define schema in `src/api/schemas.py`:
```python
class MyRequest(BaseModel):
    field: str = Field(..., description="Description")
```

2. Add endpoint in `src/api/server.py`:
```python
@app.post("/my-endpoint")
async def my_endpoint(
    request: MyRequest,
    auditor: StyleAuditor = Depends(get_auditor)
):
    # Implementation
    return {"result": "success"}
```

3. Document in this file!

### Running Tests
```bash
# Test auditor directly
python tests/run_tests.py --file tests/generated_tests_complex.json

# Test API endpoints
curl http://localhost:8000/audit \
  -H "Content-Type: application/json" \
  -d '{"text": "The Cabinet met today."}'
```

---

## Deployment

### Docker (Recommended)

Create `Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "run_server.py", "--production", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t cbc-style-checker .
docker run -p 8000:8000 --env-file .env cbc-style-checker
```

### Cloud Run / App Engine
```bash
# Deploy to Google Cloud Run
gcloud run deploy cbc-style-checker \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### Traditional Server
```bash
# Use gunicorn for production
pip install gunicorn
gunicorn src.api.server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'src'"
**Solution:** Run from project root:
```bash
cd /path/to/newslabs-rag-style-checker
python run_server.py
```

### Issue: "PROJECT_NAME not found in environment variables"
**Solution:** Create `.env` file with required variables (see Configuration section)

### Issue: ChromaDB connection fails
**Solution:** Verify `DB_PATH` exists and contains `chroma.sqlite3`:
```bash
ls -la ./db/chroma_db/
```

### Issue: Slow first request
**Solution:** This is normal! Auditor initializes on first request. Consider pre-warming:
```python
# Add to server.py startup
@app.on_event("startup")
async def startup_event():
    get_auditor()  # Pre-initialize
```

### Issue: "VertexAIRerank class not found"
**Solution:** Reranker is optional. If needed, ensure `google-cloud-discoveryengine` is installed:
```bash
pip install google-cloud-discoveryengine
```

---

## Examples

### Python Client
```python
import requests

response = requests.post(
    "http://localhost:8000/audit",
    json={"text": "The Cabinet announced new measures."}
)

violations = response.json()["violations"]
for v in violations:
    print(f"❌ {v['text']}: {v['reason']}")
```

### JavaScript/TypeScript Client
```typescript
const response = await fetch('http://localhost:8000/audit', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: "The Cabinet announced new measures."
  })
});

const { violations } = await response.json();
violations.forEach(v => {
  console.log(`❌ ${v.text}: ${v.reason}`);
});
```

### cURL
```bash
curl -X POST http://localhost:8000/audit \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The Cabinet announced new measures today."
  }' | jq '.violations'
```

---

## Support

- **Issues**: Report bugs via GitHub Issues
- **Documentation**: See project README and inline code comments
- **Style Guide**: https://www.cbc.ca/newsinteractives/style

---

## License

Internal CBC News Labs project.
