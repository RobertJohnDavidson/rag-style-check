from src.data.db import get_sync_engine
from sqlalchemy import text

engine = get_sync_engine()
with engine.connect() as conn:
    print(f"StyleRules: {conn.execute(text('SELECT count(*) FROM style_rules')).scalar()}")
    print(f"Triggers: {conn.execute(text('SELECT count(*) FROM rule_triggers')).scalar()}")
    print(f"Vectors: {conn.execute(text('SELECT count(*) FROM data_style_guide')).scalar()}")
