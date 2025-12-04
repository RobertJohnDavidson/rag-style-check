"""
Database migration script to create test management tables.
Run this script once to set up test_cases and test_results tables in Cloud SQL.
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

# SQL statements to create tables
CREATE_TEST_CASES_TABLE = """
CREATE TABLE IF NOT EXISTS test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label VARCHAR(255) NOT NULL,
    text TEXT NOT NULL,
    expected_violations JSONB NOT NULL DEFAULT '[]'::jsonb,
    generation_method VARCHAR(50) NOT NULL CHECK (generation_method IN ('manual', 'article', 'synthetic')),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

# Comment documenting expected_violations schema
COMMENT_EXPECTED_VIOLATIONS = """
COMMENT ON COLUMN test_cases.expected_violations IS 
'JSONB array of expected violations. Each object contains: rule (string, required), text (string, required), reason (string, optional), link (string, required - URL to style guide rule)';
"""

CREATE_TEST_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    true_positives INTEGER NOT NULL DEFAULT 0,
    false_positives INTEGER NOT NULL DEFAULT 0,
    false_negatives INTEGER NOT NULL DEFAULT 0,
    true_negatives INTEGER NOT NULL DEFAULT 0,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    detected_violations JSONB NOT NULL DEFAULT '[]'::jsonb,
    tuning_parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

# Indexes for common query patterns
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_test_cases_label ON test_cases(label);",
    "CREATE INDEX IF NOT EXISTS idx_test_cases_generation_method ON test_cases(generation_method);",
    "CREATE INDEX IF NOT EXISTS idx_test_cases_created_at ON test_cases(created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_test_results_test_id ON test_results(test_id);",
    "CREATE INDEX IF NOT EXISTS idx_test_results_executed_at ON test_results(executed_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_test_results_f1_score ON test_results(f1_score DESC);"
]

# Trigger to auto-update updated_at timestamp
CREATE_TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';
"""

DROP_EXISTING_TRIGGER = "DROP TRIGGER IF EXISTS update_test_cases_updated_at ON test_cases;"

CREATE_TRIGGER = """
CREATE TRIGGER update_test_cases_updated_at
    BEFORE UPDATE ON test_cases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""

async def run_migration():
    """Execute the migration to create test management tables"""
    print("🚀 Starting database migration for test management tables...")
    
    # Create connector within the async event loop
    loop = asyncio.get_running_loop()
    connector = Connector(loop=loop)
    
    try:
        # Create async engine
        engine = create_async_engine(
            "postgresql+asyncpg://",
            async_creator=lambda: get_async_conn(connector),
            echo=True  # Show SQL statements being executed
        )
        
        try:
            async with engine.begin() as conn:
                print("\n📝 Creating test_cases table...")
                await conn.execute(sqlalchemy.text(CREATE_TEST_CASES_TABLE))
                print("✅ test_cases table created")
                
                print("\n📝 Adding column comments...")
                await conn.execute(sqlalchemy.text(COMMENT_EXPECTED_VIOLATIONS))
                print("✅ Column documentation added")
                
                print("\n📝 Creating test_results table...")
                await conn.execute(sqlalchemy.text(CREATE_TEST_RESULTS_TABLE))
                print("✅ test_results table created")
                
                print("\n📝 Creating indexes...")
                for index_sql in CREATE_INDEXES:
                    await conn.execute(sqlalchemy.text(index_sql))
                print("✅ Indexes created")
                
                print("\n📝 Creating updated_at trigger...")
                await conn.execute(sqlalchemy.text(CREATE_TRIGGER_FUNCTION))
                await conn.execute(sqlalchemy.text(DROP_EXISTING_TRIGGER))
                await conn.execute(sqlalchemy.text(CREATE_TRIGGER))
                print("✅ Trigger created")
                
            print("\n✨ Migration completed successfully!")
            print("\nCreated tables:")
            print("  • test_cases: Store test definitions with expected violations")
            print("  • test_results: Store test execution results with metrics")
            print("\nCreated indexes for efficient querying on:")
            print("  • label, generation_method, created_at (test_cases)")
            print("  • test_id, executed_at, f1_score (test_results)")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            raise
        finally:
            await engine.dispose()
    finally:
        await connector.close_async()

def main():
    """Entry point for migration script"""
    try:
        asyncio.run(run_migration())
    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
