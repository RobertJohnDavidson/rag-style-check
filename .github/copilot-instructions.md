# CBC News Style Checker - AI Agent Instructions

## Project Overview

A RAG-based system that audits news text against CBC News style guidelines using:

- **Vector retrieval**: Google Gemini embeddings + PostgreSQL with pgvector (HNSW index)
- **Agentic auditor**: Multi-iteration refinement with structured LLM outputs (Pydantic models)
- **FastAPI backend**: Async endpoints for auditing, test management, and tuning
- **SvelteKit 5 frontend**: Modern UI with Tailwind CSS and Bun package manager

## Architecture

```
FastAPI Server (src/api/server.py)
  ├─ StyleAuditor (src/core/auditor.py) - RAG + agentic refinement
  │   ├─ VectorStoreIndex (LlamaIndex) - semantic search
  │   ├─ Query Fusion - multi-query retrieval
  │   └─ LLM Reranking - filter and score rules
  ├─ TestManager (src/core/test_manager.py) - CRUD for test cases/results
  └─ PostgreSQL (src/core/db.py) - vectors + SQLAlchemy ORM models
```

### Key Data Flow

1. **Ingestion** ([src/data/ingest.py](../src/data/ingest.py)): JSON style rules → TextNodes → PostgreSQL vectors
2. **Auditing** ([src/core/auditor.py](../src/core/auditor.py)): User text → semantic retrieval → LLM reasoning → violations
3. **Agentic Loop**: Initial audit → self-reflection → additional queries → refinement (max iterations: 3)

## Development Patterns

### Database Models (SQLAlchemy ORM)

All models use SQLAlchemy 2.0 style with type annotations:

```python
# See src/core/models/tests.py
class TestCase(Base):
    __tablename__ = 'test_cases'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    expected_violations: Mapped[dict] = mapped_column(JSONB, nullable=False)
    test_results: Mapped[List["TestResult"]] = relationship(...)
```

- Use `Mapped[T]` for all columns
- JSONB for flexible data (violations, tuning params)
- Relationships use `relationship()` with back_populates

### API Schemas (Pydantic v2)

FastAPI uses Pydantic models for request/response validation:

```python
# See src/api/schemas.py and src/api/test_schemas.py
class AuditRequest(BaseModel):
    text: str
    config: Optional[AuditorConfig] = None
```

**Important**: Keep separate schemas for API vs core logic to avoid circular imports.

### Async Patterns

- All API endpoints are `async def`
- Database operations use `AsyncSession` via `get_async_session()` context manager
- StyleAuditor runs async: `await auditor.check_text_async(text)`

```python
async with get_async_session() as session:
    result = await session.execute(select(TestCase).where(...))
    test_case = result.scalar_one_or_none()
```

### Configuration

Settings live in [src/config.py](../src/config.py) as a Pydantic model:

- Environment variables loaded via `python-dotenv`
- Tuning defaults: `DEFAULT_INITIAL_RETRIEVAL_COUNT`, `DEFAULT_FINAL_TOP_K`, etc.
- HNSW parameters for vector search efficiency

**Critical**: Always call `init_settings()` before using `settings` to initialize embeddings.

### Prompts & Structured Outputs

Prompts in [src/core/prompts.py](../src/core/prompts.py) use Pydantic for structured LLM responses:

```python
class AuditResult(BaseModel):
    violations: List[Violation]
    confident: bool
    needs_more_context: bool  # Triggers agentic refinement
    additional_queries: List[str]
```

LLM generates JSON matching this schema, enabling programmatic decision-making.

## Development Workflow

### Local Development

```bash
# Backend
pip install -e .
python run_server.py  # Auto-reload enabled by default

# Frontend (use bun, not npm)
cd frontend
bun install
bun run dev -- --host 0.0.0.0
```

### Docker Development

```bash
# Backend only
docker compose up -d

# Backend + Frontend dev server
docker compose --profile dev up -d

# Or use Makefile shortcuts
make dev        # Run with hot reload
make dev-build  # Force rebuild (when deps change)
make down       # Stop all containers
```

### Database Migrations

Uses Alembic (though not actively used in current state):

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Testing Framework

Test cases stored in PostgreSQL (`test_cases` table):

- **Generation**: `/api/generate-tests` - LLM creates test cases with expected violations
- **Execution**: `/api/tests/{test_id}/run` - Run auditor, calculate metrics (precision/recall/F1)
- **Tuning**: Compare results across different `AuditorConfig` parameters

See [src/core/test_manager.py](../src/core/test_manager.py) for CRUD operations.

## Critical Gotchas

### 1. PGVectorStore Table Naming

PGVectorStore adds `data_` prefix to table names:

```python
TABLE_NAME = "rag_vectors"          # What you pass to PGVectorStore
ACTUAL_TABLE_NAME = "data_rag_vectors"  # Actual table in PostgreSQL
```

### 2. Embeddings Initialization

**Must** call `init_settings()` before creating auditor/ingestion pipeline:

```python
from src.config import init_settings
init_settings()  # Sets LlamaSettings.embed_model globally
```

### 3. Async Context Managers

Database sessions are async context managers - don't forget `async with`:

```python
# Correct
async with get_async_session() as session:
    result = await session.execute(...)
    await session.commit()  # Auto-commit on exit

# Wrong - will leak connections
session = get_async_session()
```

### 4. Frontend Uses Bun

Don't use npm/pnpm - this project uses `bun` for frontend:

```bash
bun install  # Not npm install
bun run dev
```

### 5. Rule Matching Logic

The auditor applies rules LITERALLY based on guideline text. When modifying prompts in [src/core/prompts.py](../src/core/prompts.py), maintain the instruction to avoid over-generalization (see `PROMPT_AUDIT_SYSTEM`).

## Common Tasks

### Adding a New API Endpoint

1. Define Pydantic schema in [src/api/schemas.py](../src/api/schemas.py) or [src/api/test_schemas.py](../src/api/test_schemas.py)
2. Add route in [src/api/server.py](../src/api/server.py) with `@app.post()` / `@app.get()`
3. Use dependency injection for auditor: `auditor: StyleAuditor = Depends(get_auditor)`

### Tuning Retrieval Parameters

Adjust these in [src/config.py](../src/config.py):

- `DEFAULT_INITIAL_RETRIEVAL_COUNT`: Initial semantic search results
- `DEFAULT_FINAL_TOP_K`: Final rules after reranking
- `DEFAULT_RERANK_SCORE_THRESHOLD`: Min relevance score (0-1)

Or pass custom `AuditorConfig` via API request.

### Modifying Style Rules

1. Edit JSON files (location: `JSON_DATA_DIR` env var)
2. Run ingestion: `python -m src.data.ingest`
3. Rules become searchable vectors in PostgreSQL

## External Dependencies

- **Google Gemini API**: Embeddings (`text-embedding-004`) and LLM (`gemini-2.5-flash`)
- **PostgreSQL**: Vector storage with pgvector extension (HNSW indexing)
- **LlamaIndex**: Abstracts retrieval/reranking logic
- **ChromaDB**: Old vector store (replaced by PostgreSQL, but imports remain)

## File Organization

- `src/api/`: FastAPI server and schemas
- `src/core/`: Business logic (auditor, test manager, DB)
- `src/core/models/`: SQLAlchemy ORM models
- `src/data/`: Ingestion scripts
- `frontend/src/lib/components/tuning/`: Svelte components for test UI
- `alembic/`: Database migrations (not actively used)
