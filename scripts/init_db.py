import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.data.db import get_sync_engine
from src.data.models import Base, TestCase, TestResult, AuditLog, StyleRule, RuleTrigger, RulePattern

def init_db():
    engine = get_sync_engine()
    print("🚀 Initializing database tables...")
    try:
        Base.metadata.create_all(engine)
        print("✅ Database tables created/updated successfully.")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")

if __name__ == "__main__":
    init_db()
