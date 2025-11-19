# Style Guide Auditor (RAG Pipeline)

This project is a Python-based Retrieval-Augmented Generation (RAG) system designed to audit text against a specific style guide. It ingests style guide rules from JSON files, stores them in a ChromaDB vector database, and uses a semantic search (powered by Google Gemini Embeddings) to flag potential violations in user text.

## Features

*   **Ingestion Pipeline**: Parses JSON style guide data and creates optimized vector embeddings.
*   **Semantic Search**: Uses Google's `text-embedding-004` model to find relevant rules even if the wording isn't exact.
*   **Auditor Interface**: A Python class (`StyleAuditor`) that splits text into sentences, checks them against the database, and uses an LLM to verify violations.
*   **Portable Module**: Structured as a Python package for easy integration.

## Prerequisites

*   Python 3.10+
*   Google Cloud Project with Vertex AI API enabled.
*   Application Default Credentials (ADC) configured or a Service Account.

## Installation

1.  **Clone the repository** (if applicable).

2.  **Install the package in editable mode**:
    This installs dependencies and links the `src` directory to your environment.
    ```bash
    pip install -e .
    ```

3.  **Environment Configuration**:
    Create a `.env` file in the root directory based on `.env.example`:
    ```ini
    PROJECT_NAME=your-project-name
    EMBEDDING_MODEL=gemini-embedding-001
    MODEL=gemini-2.5-flash
    REGION=us-central1
    JSON_DATA_DIR = "./data" 
    DB_PATH = "./db/your-db"
    COLLECTION_NAME = "your-collection"
    ```

## Usage

### 1. Ingest Data
Before you can audit text, you must build the vector database. This script reads JSON files from the `data/` directory.

```bash
python src/ingest.py
```

### 2. Run the Auditor
You can run the auditor interactively or import it into your own scripts.

**Interactive Mode:**
```bash
python src/audit.py
```

**Programmatic Usage:**
```python
from src import StyleAuditor

auditor = StyleAuditor()
results = auditor.check_text("The government needs to do more for Aboriginal housing.")

for violation in results:
    print(f"Violation: {violation['violation']}")
    print(f"Correction: {violation['correction']}")
    print(f"Source: {violation['source_url']}")
```

### 3. Run Tests
To evaluate the system against a set of test cases:

```bash
python tests/run_tests.py
```

## Project Structure

*   `src/`: Source code for the package.
    *   `ingest.py`: Script to parse data and build the vector store.
    *   `audit.py`: Core logic for the `StyleAuditor` class.
*   `data/`: Directory containing the source JSON style guide files.
*   `tests/`: Test scripts and data.
*   `chroma_db/`: (Generated) The persistent vector database.
