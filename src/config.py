import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel
from llama_index.core import Settings as LlamaSettings
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from google.genai.types import EmbedContentConfig

load_dotenv()

class AppSettings(BaseModel):
    # Google Cloud
    PROJECT_ID: str = os.getenv("PROJECT_NAME", "")
    LLM_REGION: str = os.getenv("LLM_REGION", "us-central1")
    EMBED_REGION: str = os.getenv("EMBED_REGION", "us-central1")

    # Database
    INSTANCE_NAME: Optional[str] = os.getenv("INSTANCE_NAME")
    DB_USER: Optional[str] = os.getenv("DB_USER")
    DB_NAME: str = os.getenv("DB_NAME", "postgres")
    DB_REGION: str = os.getenv("DB_REGION", "us-central1")
    TABLE_NAME: str = "rag_vectors"  # Name passed to PGVectorStore
    ACTUAL_TABLE_NAME: str = "data_rag_vectors"  # Actual name in database (PGVectorStore adds 'data_' prefix)
    
    # Model Config
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
    EMBED_DIM: int = 768
    DEFAULT_MODEL: str = os.getenv("MODEL", "gemini-2.5-flash")
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "gemini-2.5-flash-lite")
    # HNSW Index creation parameters (used during table setup)
    HNSW_INDEX_KWARGS: dict = {
        "hnsw_m": 24,
        "hnsw_ef_construction": 512,
        "hnsw_dist_method": "vector_cosine_ops",
    }
    
    # HNSW Query parameters (used during vector search)
    HNSW_QUERY_KWARGS: dict = {
        "hnsw_ef_search": 100,
    }
    
    # Combined for PGVectorStore initialization (needs both)
    @property
    def HNSW_KWARGS(self) -> dict:
        return {**self.HNSW_INDEX_KWARGS, **self.HNSW_QUERY_KWARGS}
    
    # Tuning Defaults
    DEFAULT_INITIAL_RETRIEVAL_COUNT: int = 75
    DEFAULT_FINAL_TOP_K: int = 15
    DEFAULT_RERANK_SCORE_THRESHOLD: float = 0.10
    DEFAULT_AGGREGATED_RULE_LIMIT: int = 40
    DEFAULT_MAX_AGENT_ITERATIONS: int = 1

    DEFAULT_LLM_TEMPERATURE: float = 0.0
    DEFAULT_MAX_CONCURRENT_REQUESTS: int = 15
    def validate_env(self):
        if not self.PROJECT_ID:
            raise ValueError("PROJECT_NAME not found in environment variables.")

# Global Settings Instance
settings = AppSettings()

def init_settings():
    """Initialize global LlamaIndex settings."""
    settings.validate_env()
    
    # Configure Embeddings (Global default)
    LlamaSettings.embed_model = GoogleGenAIEmbedding(
        model_name=settings.EMBEDDING_MODEL,
        vertexai_config={
            "project": settings.PROJECT_ID,
            "location": settings.EMBED_REGION
        },
        embedding_config=EmbedContentConfig(
            output_dimensionality=settings.EMBED_DIM 
        )
    )
