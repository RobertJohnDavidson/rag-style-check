import os
import json
import glob
import hashlib
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session
from google.cloud import storage
from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.core.ingestion import IngestionPipeline, IngestionCache
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.kvstore import SimpleKVStore
from llama_index.core.schema import TextNode

from src.config import settings, init_settings
from src.data.db import (
    get_sync_engine,
    get_async_engine,
    init_vector_store_for_ingest,
)
from src.data.models import StyleRule, RuleTrigger, RulePattern

# Load environment variables
load_dotenv()
init_settings()

JSON_DATA_DIR = os.getenv("JSON_DATA_DIR")

def create_id(term, url, definition):
    """Creates a deterministic ID for a rule based on term, url, and definition."""
    # definition might be None, so use empty string fallback for hasing
    def_str = definition or ""
    return hashlib.md5(f"{term}:{url}:{def_str}".encode()).hexdigest()

def create_ingest_objects(entry):
    """
    Transforms a raw JSON entry into:
    1. A Vector Node (LlamaIndex)
    2. A StyleRule ORM object
    3. A list of RuleTrigger ORM objects
    4. A list of RulePattern ORM objects
    """
    term = entry.get("term", "Unknown Rule")
    definition = entry.get("definition") 
    url = entry.get("url", "")
    rule_type = entry.get("rule_type")
    tags = entry.get("tags", [])
    triggers_text = entry.get("triggers", []) 
    patterns_text = entry.get("detection_patterns", []) 

    rule_id = create_id(term, url, definition)

    # 1. Vector Node (Only Embed Term + Definition)
    search_text = f"{term} {definition}"
    
    node = TextNode(
        id_=rule_id,
        text=search_text,
        metadata={
            "term": term,
            "definition": definition,
            "url": url,
            "rule_type": rule_type,
            "tags": tags,
            "rule_id": rule_id
        }
    )
    # Exclude everything but text from embedding
    node.excluded_embed_metadata_keys = ["term", "definition", "url", "rule_type", "tags", "rule_id"]

    # 2. StyleRule
    rule = StyleRule(
        id=rule_id,
        term=term,
        definition=definition,
        url=url,
        rule_type=rule_type,
        tags=tags
    )

    # 3. RuleTrigger
    triggers = [RuleTrigger(trigger_text=t, rule_id=rule_id) for t in triggers_text]

    # 4. RulePattern
    patterns = [RulePattern(pattern_regex=p, rule_id=rule_id) for p in patterns_text]

    return node, rule, triggers, patterns

def load_all_data(directory):
    """Loads all JSON files and converts them to ingest objects."""
    all_nodes = []
    all_rules = []
    all_triggers = []
    all_patterns = []

    seen_ids = set()

    def process_entry(data):
        if isinstance(data, list):
            for item in data:
                process_entry(item)
        elif isinstance(data, dict):
            if not data.get("term") and not data.get("rule_type"):
                return # Skip empty or invalid entries
            try:
                n, r, t, p = create_ingest_objects(data)
                
                # Deduplication check
                if r.id in seen_ids:
                    return
                seen_ids.add(r.id)

                all_nodes.append(n)
                all_rules.append(r)
                all_triggers.extend(t)
                all_patterns.extend(p)
            except Exception as e:
                print(f"⚠️  Skipping malformed entry: {e}")
        else:
            print(f"⚠️  Found unexpected data type: {type(data)}")

    if directory.startswith("gs://"):
        storage_client = storage.Client(project=settings.PROJECT_ID)
        path_parts = directory[5:].split("/", 1)
        bucket = storage_client.bucket(path_parts[0])
        prefix = path_parts[1] if len(path_parts) > 1 else ""
        blobs = bucket.list_blobs(prefix=prefix)
        files = [blob.name for blob in blobs if blob.name.endswith(".json")]
        
        for blob_name in files:
            try:
                content = bucket.blob(blob_name).download_as_text()
                data = json.loads(content)
                process_entry(data)
            except Exception as e:
                print(f"❌ Error processing blob {blob_name}: {e}")
    else:
        files = glob.glob(os.path.join(directory, "*.json"))
        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    process_entry(data)
            except Exception as e:
                print(f"❌ Error processing file {filepath}: {e}")

    return all_nodes, all_rules, all_triggers, all_patterns

def clear_sql_tables(engine):
    """Truncates the structured SQL tables."""
    tables = ["rule_triggers", "rule_patterns", "style_rules"]
    with engine.connect() as conn:
        for table in tables:
            print(f"🧹 Truncating {table}...")
            conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        conn.commit()

def main():
    # 1. Load Data from JSON
    print(f"📂 Loading data from {JSON_DATA_DIR}...")
    nodes, rules, triggers, patterns = load_all_data(JSON_DATA_DIR)
    print(f"✅ Loaded {len(nodes)} rules, {len(triggers)} triggers, {len(patterns)} patterns.")

    # 2. Setup Engines
    engine = get_sync_engine()
    async_engine = get_async_engine()

    # 3. Clear existing SQL data
    clear_sql_tables(engine)

    # 4. Ingest Vectors with LlamaIndex
    # Note: LlamaIndex will handle data_style_guide creation/truncation if drop/setup are coordinated
    vector_store = init_vector_store_for_ingest(engine, async_engine)
    
    cache_path = "./ingestion_cache.json"
    try:
        cached_hashes = SimpleKVStore.from_persist_path(cache_path)
    except FileNotFoundError:
        cached_hashes = SimpleKVStore()

    pipeline = IngestionPipeline(
        transformations=[Settings.embed_model],
        cache=IngestionCache(cache=cached_hashes),
        docstore=SimpleDocumentStore(),
    )

    print("🚀 Running Vector Ingestion Pipeline...")
    output_nodes = pipeline.run(nodes=nodes, show_progress=True)
    cached_hashes.persist(cache_path)

    print("💾 Writing vectors to database...")
    from llama_index.core import StorageContext, VectorStoreIndex
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    VectorStoreIndex(output_nodes, storage_context=storage_context)

    # 5. Bulk Insert SQL Objects
    # 5. Bulk Insert SQL Objects
    print("💾 Writing structured rules to database...")
    from sqlalchemy.orm import Session
    
    BATCH_SIZE = 1000
    
    with Session(engine) as session:
        # Insert Style Rules
        print(f"  ↳ Inserting {len(rules)} style rules in batches of {BATCH_SIZE}...")
        for i in range(0, len(rules), BATCH_SIZE):
            batch = rules[i : i + BATCH_SIZE]
            session.add_all(batch)
            session.commit() # Commit each batch to free resources and avoid locks
            print(f"    - Committed rules batch {(i // BATCH_SIZE) + 1}/{(len(rules) // BATCH_SIZE) + 1}")

        # Insert Triggers
        print(f"  ↳ Inserting {len(triggers)} triggers in batches of {BATCH_SIZE}...")
        for i in range(0, len(triggers), BATCH_SIZE):
            batch = triggers[i : i + BATCH_SIZE]
            session.add_all(batch)
            session.commit()
            print(f"    - Committed triggers batch {(i // BATCH_SIZE) + 1}/{(len(triggers) // BATCH_SIZE) + 1}")

        # Insert Patterns
        print(f"  ↳ Inserting {len(patterns)} patterns in batches of {BATCH_SIZE}...")
        for i in range(0, len(patterns), BATCH_SIZE):
            batch = patterns[i : i + BATCH_SIZE]
            session.add_all(batch)
            session.commit()
            print(f"    - Committed patterns batch {(i // BATCH_SIZE) + 1}/{(len(patterns) // BATCH_SIZE) + 1}")

    print(f"✅ Ingestion Complete. {len(output_nodes)} vectors and {len(rules)} SQL rules stored.")

if __name__ == "__main__":
    main()