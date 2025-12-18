"""
Database migration script to create audit_logs table.
"""

import os
import asyncio
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

# --- CONFIGURATION ---
PROJECT_ID = os.getenv("PROJECT_NAME")
REGION = os.getenv("DB_REGION", "us-central1")
INSTANCE_NAME = os.getenv("INSTANCE_NAME")
DB_USER = os.getenv("DB_USER")
DB_NAME = os.getenv("DB_NAME", "postgres")

def get_ip_type():
    """Determine IP type based on environment (private for Cloud Run, public otherwise)"""
    if os.getenv("K_SERVICE"):
        return IPTypes.PRIVATE
    return IPTypes.PUBLIC

async def get_async_conn(connector):
    """Create async database connection using Cloud SQL connector"""
    return await connector.connect_async(
        f"{PROJECT_ID}:{REGION}:{INSTANCE_NAME}",
        "asyncpg",
        user=DB_USER,
        db=DB_NAME,
        enable_iam_auth=True,
        ip_type=get_ip_type()
    )

CREATE_AUDIT_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID REFERENCES test_cases(id) ON DELETE SET NULL,
    input_text TEXT NOT NULL,
    model_used TEXT NOT NULL,
    llm_parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    rag_parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    interim_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    final_output JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_test_id ON audit_logs(test_id);",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);"
]

async def run_migration():
    """Execute the migration to create audit_logs table"""
    print("🚀 Starting database migration for audit_logs table...")
    
    loop = asyncio.get_running_loop()
    connector = Connector(loop=loop)
    
    try:
        engine = create_async_engine(
            "postgresql+asyncpg://",
            async_creator=lambda: get_async_conn(connector),
            echo=True
        )
        
        try:
            async with engine.begin() as conn:
                print("\n📝 Creating audit_logs table...")
                await conn.execute(sqlalchemy.text(CREATE_AUDIT_LOGS_TABLE))
                print("✅ audit_logs table created")
                
                print("\n📝 Creating indexes...")
                for index_sql in CREATE_INDEXES:
                    await conn.execute(sqlalchemy.text(index_sql))
                print("✅ Indexes created")
                
            print("\n✨ Migration completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            raise
        finally:
            await engine.dispose()
    finally:
        await connector.close_async()

def main():
    try:
        asyncio.run(run_migration())
    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
