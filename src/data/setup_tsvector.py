"""
Setup tsvector column for full-text search on the vectors table.

Run this once after creating the table with ingest.py:
    python -m src.data.setup_tsvector
"""

from dotenv import load_dotenv
from sqlalchemy import text

from src.config import settings, init_settings
from src.core.db import get_sync_engine, setup_tsvector_column

load_dotenv()
init_settings()


def main():
    print("🔧 Setting up full-text search for pgvector table...")
    print(f"📊 Table: {settings.ACTUAL_TABLE_NAME}")
    
    engine = get_sync_engine()
    
    # Verify table exists
    print("🔍 Verifying table exists...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {settings.ACTUAL_TABLE_NAME}"))
            count = result.scalar()
            print(f"✅ Table exists with {count} rows")
    except Exception as e:
        print(f"❌ Table not found: {e}")
        print("💡 Run 'python -m src.data.ingest' first to create the table")
        return
    
    # Setup tsvector column, index, and trigger
    print("🔧 Adding tsvector column, GIN index, and auto-update trigger...")
    try:
        setup_tsvector_column(engine, table_name=settings.ACTUAL_TABLE_NAME)
        print("✅ Full-text search configured successfully!")
        print("📝 The trigger will automatically update tsvector on insert/update")
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        raise


if __name__ == "__main__":
    main()
