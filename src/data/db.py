import os
import asyncio
from contextlib import asynccontextmanager
from google.cloud.sql.connector import Connector, IPTypes
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from llama_index.vector_stores.postgres import PGVectorStore
from src.config import settings

def get_ip_type():
    if os.getenv("K_SERVICE"):
        return IPTypes.PRIVATE
    return IPTypes.PUBLIC

def get_sync_engine() -> Engine:
    """Creates the SQLAlchemy Engine (Sync)."""
    conn = Connector()
    
    def get_sync_conn():
        return conn.connect(
            f"{settings.PROJECT_ID}:{settings.DB_REGION}:{settings.INSTANCE_NAME}",
            "pg8000",
            user=settings.DB_USER,
            db=settings.DB_NAME,
            enable_iam_auth=True,
            ip_type=get_ip_type()
        )
    
    return create_engine(
        "postgresql+pg8000://",
        creator=get_sync_conn,
    )

def get_async_engine() -> AsyncEngine:
    """Creates the SQLAlchemy AsyncEngine with connectors bound to the running event loop."""
    
    async def get_async_conn():
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
        return conn
    
    return create_async_engine(
        "postgresql+asyncpg://",
        async_creator=get_async_conn,
    )

# Create async session factory
async_engine = get_async_engine()
AsyncSessionFactory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@asynccontextmanager
async def get_async_session():
    """Async context manager for database sessions."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

def init_vector_store(engine: Engine, async_engine: AsyncEngine) -> PGVectorStore:
    """Initializes the PGVectorStore with the given engine."""
    return PGVectorStore(
        engine=engine,
        async_engine=async_engine,
        table_name=settings.TABLE_NAME,
        embed_dim=settings.EMBED_DIM,
        hybrid_search=True,
        perform_setup=False,
        text_search_config="english",
        # hnsw_kwargs=settings.HNSW_KWARGS, # Avoid passing this if not setting up, as it can cause issues if already exists
    )


def init_vector_store_for_ingest(engine: Engine, async_engine: AsyncEngine) -> PGVectorStore:
    """Return a vector store configured for ingestion that builds the schema."""
    return PGVectorStore(
        engine=engine,
        async_engine=async_engine,
        table_name=settings.TABLE_NAME,
        embed_dim=settings.EMBED_DIM,
        perform_setup=True,
        hybrid_search=True,
        text_search_config="english",
        hnsw_kwargs=settings.HNSW_KWARGS,
    )


def setup_tsvector_column(engine: Engine, table_name: str | None = None) -> None:
    """Ensure the tsvector column, index, and trigger exist on the vectors table."""
    resolved_table = table_name or settings.TABLE_NAME
    normalized_name = resolved_table.lower()
    statements = [
        f"""ALTER TABLE {normalized_name} ADD COLUMN IF NOT EXISTS text_search_tsv tsvector;""",
        f"""CREATE INDEX IF NOT EXISTS idx_{normalized_name}_tsv ON {normalized_name} USING GIN (text_search_tsv);""",
        f"""CREATE OR REPLACE FUNCTION {normalized_name}_tsv_trigger()
RETURNS trigger AS $$
BEGIN
  new.text_search_tsv := to_tsvector('english', coalesce(new.text, ''));
  return new;
END;
$$ LANGUAGE plpgsql;""",
        f"""DROP TRIGGER IF EXISTS tsvectorupdate ON {normalized_name};""",
        f"""CREATE TRIGGER tsvectorupdate
BEFORE INSERT OR UPDATE ON {normalized_name}
FOR EACH ROW EXECUTE PROCEDURE {normalized_name}_tsv_trigger();""",
    ]
    with engine.connect() as conn:
        for statement in statements:
            conn.execute(text(statement))
        conn.commit()
