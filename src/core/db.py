import os
import asyncio
from google.cloud.sql.connector import Connector, IPTypes
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from llama_index.vector_stores.postgres import PGVectorStore
from src.config import settings

def get_ip_type():
    if os.getenv("K_SERVICE"):
        return IPTypes.PRIVATE
    return IPTypes.PUBLIC

async def get_async_conn():
    """
    Callback for asyncpg connection.
    Note: Connector must be initialized in the running loop context if loop is provided,
    or just default if running standard asyncio.
    """
    # Initialize connector lazily to ensure it attaches to the current loop
    loop = asyncio.get_running_loop()
    connector = Connector(loop=loop)
    
    conn = await connector.connect_async(
        f"{settings.PROJECT_ID}:{settings.DB_REGION}:{settings.INSTANCE_NAME}",
        "asyncpg",
        user=settings.DB_USER,
        db=settings.DB_NAME,
        enable_iam_auth=True,
        ip_type=get_ip_type()
    )
    # Note: In a real app, we should probably close the connector when app shuts down.
    # For now, we return the connection.
    return conn

def get_async_engine() -> AsyncEngine:
    """Creates the SQLAlchemy AsyncEngine."""
    return create_async_engine(
        "postgresql+asyncpg://",
        async_creator=get_async_conn,
    )

def init_vector_store(engine: AsyncEngine) -> PGVectorStore:
    """Initializes the PGVectorStore with the given engine."""
    return PGVectorStore(
        async_engine=engine,
        table_name=settings.TABLE_NAME,
        embed_dim=settings.EMBED_DIM,
        hybrid_search=True,
        text_search_config="english",
        hnsw_kwargs={
            "hnsw_m": 24,                
            "hnsw_ef_construction": 512, 
            "hnsw_dist_method": "vector_cosine_ops",
        },
    )
