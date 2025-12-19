import os
import json
import glob
from pathlib import Path
from sqlalchemy import text
from google.cloud import storage
from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.core.ingestion import IngestionPipeline, IngestionCache
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.kvstore import SimpleKVStore
from llama_index.core.schema import TextNode
from src.config import settings, init_settings
from src.core.db import (
    get_sync_engine,
    get_async_engine,
    init_vector_store_for_ingest,
)

# Load environment variables
load_dotenv()
init_settings()

JSON_DATA_DIR = os.getenv("JSON_DATA_DIR")

# Inline Constants
RULE_TAGS = [
    "Capitalization", "Punctuation", "Spelling", "Grammar", "Numbers",
    "Dates & Time", "Geography", "Titles & Ranks", "Abbreviations",
    "Formatting", "Usage & Diction", "Proper Names", "Bias & Sensitivity"
]


def create_node_from_entry(entry):
    """ Transforms a raw JSON entry into a Semantic Vector Node. """
    term = entry.get("term", "Unknown Rule")
    definition = entry.get("definition", "")
    constraints = entry.get("negative_constraints", []) or []
    url = entry.get("url", "")
    context = entry.get("context_tag", "General")
    entry_type = entry.get("type", "term")
    is_spelling = entry.get("is_spelling_only", False)
    # Get tags, defaulting to empty list if missing
    tags = entry.get("tags", [])
    
    # Validate tags against known list (optional, but good for data hygiene)
    valid_tags = [t for t in tags if t in RULE_TAGS]
    tags_str = ", ".join(valid_tags)

    if entry_type == "term":
        search_text = (
            f"Rule: {term}. Context: {context}. Definition: {definition}. "
            f"Negative Triggers: {' '.join(constraints)}."
        )
        if valid_tags:
            search_text += f" Tags: {tags_str}."
            
        if is_spelling:
            search_text += f" Strict spelling rule for {term}."
    else:
        search_text = (
            f"Policy Context: {term}. Category: {context}. Guideline: {definition}"
        )
        if valid_tags:
            search_text += f" Tags: {tags_str}."

    display_text = f"**Rule:** {term}\n**Guideline:** {definition}"
    if valid_tags:
        display_text += f"\n**Tags:** {tags_str}"
        
    if constraints:
        display_text += f"\n**⛔ AVOID:** {', '.join(constraints)}"

    node = TextNode(
        text=search_text,
        metadata={
            "term": term, 
            "url": url, 
            "context": context, 
            "display_text": display_text,
            "tags": valid_tags # Store as list in metadata
        }
    )
    node.excluded_embed_metadata_keys = ["term", "url", "context", "display_text", "tags"]
    node.excluded_llm_metadata_keys = ["context"] 
    return node

def load_nodes_from_gcs(gcs_path):
    """ Loads JSON files from a Google Cloud Storage bucket. """
    nodes = []
    path_parts = gcs_path[5:].split("/", 1)
    bucket_name = path_parts[0]
    prefix = path_parts[1] if len(path_parts) > 1 else ""
    
    print(f"☁️  Connecting to GCS Bucket: {bucket_name}, Prefix: {prefix}")
    try:
        storage_client = storage.Client(
            project=os.getenv("PROJECT_NAME")
        )
        bucket = storage_client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        file_count = 0
        total_entries = 0
        for blob in blobs:
            if blob.name.endswith(".json"):
                try:
                    content = blob.download_as_text()
                    data = json.loads(content)
                    entries = data if isinstance(data, list) else [data]
                    for entry in entries:
                        nodes.append(create_node_from_entry(entry))
                    file_count += 1
                    total_entries += len(entries)
                    if file_count <= 5:  # Show first 5 files for debugging
                        print(f"  📄 {blob.name}: {len(entries)} entries")
                except Exception as e:
                    print(f"❌ Error processing {blob.name}: {e}")
        print(f"📂 Processed {file_count} JSON files with {total_entries} total entries → {len(nodes)} nodes")
    except Exception as e:
        print(f"❌ Error accessing GCS: {e}")
    return nodes

def load_nodes(directory):
    if directory.startswith("gs://"):
        return load_nodes_from_gcs(directory)

    nodes = []
    files = glob.glob(os.path.join(directory, "*.json"))
    print(f"📂 Found {len(files)} JSON files. Parsing...")

    total_entries = 0
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                entries = data if isinstance(data, list) else [data]
                for entry in entries:
                    nodes.append(create_node_from_entry(entry))
                total_entries += len(entries)
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")
    
    print(f"📊 Loaded {total_entries} entries → {len(nodes)} nodes from {len(files)} files")
    return nodes

def clear_vector_store(engine):
    with engine.connect() as conn:
        # We use TRUNCATE instead of DELETE because it is faster 
        # and resets the internal identity counters.
        print(f"🧹 Clearing table {settings.ACTUAL_TABLE_NAME}...")
        conn.execute(text(f"TRUNCATE TABLE {settings.ACTUAL_TABLE_NAME}"))
        conn.commit()
        print("✅ Table cleared.")



def main():
    # Enable verbose logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('llama_index').setLevel(logging.DEBUG)
    
    # 1. Load Data
    nodes = load_nodes(JSON_DATA_DIR)
    print(f"✅ Processed {len(nodes)} nodes.")

    print(f"🔌 Connecting to Cloud SQL...")

    # 2. Create Engines & Vector Store
    engine = get_sync_engine()
    async_engine = get_async_engine()
    clear_vector_store(engine)
    vector_store = init_vector_store_for_ingest(engine, async_engine)

    # --- NEW CACHING LOGIC STARTS HERE ---
    
    # Define a local path to save the cache file
    cache_path = "./ingestion_cache.json"
    
    print("💾 Loading Ingestion Cache...")
    try:
        # Try to load existing cache from disk
        cached_hashes = SimpleKVStore.from_persist_path(cache_path)
        print("✅ Found existing cache file.")
    except FileNotFoundError:
        # Create a new one if it doesn't exist
        cached_hashes = SimpleKVStore()
        print("⚠️ No cache file found. Creating new cache.")

    # Create the Ingestion Pipeline WITHOUT vector_store
    # We'll manually add nodes to the vector store after embedding
    pipeline = IngestionPipeline(
        transformations=[Settings.embed_model],  # Uses the embed model from your init_settings()
        cache=IngestionCache(cache=cached_hashes),
        docstore=SimpleDocumentStore(),  # Optional: tracks doc metadata
    )

    print("🚀 Running Ingestion Pipeline with Cache...")
    print(f"📊 Input: {len(nodes)} nodes")
    # This will check the cache first. If a node hash matches, it skips embedding.
    # It only calculates embeddings for NEW or CHANGED nodes.
    output_nodes = pipeline.run(nodes=nodes, show_progress=True)
    print(f"📊 Output: {len(output_nodes)} nodes processed with embeddings")

    # Save the cache to disk so it persists for the next run
    cached_hashes.persist(cache_path)
    print(f"💾 Cache saved to {cache_path}")

    # --- NEW CACHING LOGIC ENDS HERE ---
    
    # Now use VectorStoreIndex to insert the embedded nodes
    # This properly triggers table creation and insertion
    print("💾 Writing embedded nodes to database...")
    from llama_index.core import StorageContext, VectorStoreIndex
    
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Create index from the embedded nodes - this will insert them into the vector store
    index = VectorStoreIndex(
        output_nodes,
        storage_context=storage_context,
        show_progress=False  # Already embedded, so this should be fast
    )
    
    print(f"✅ Created index with {len(output_nodes)} nodes")

    # Debug: Check row count after ingestion
    from sqlalchemy import select, func, text
    from sqlalchemy.schema import Table, MetaData
    try:
        with engine.connect() as conn:
            # Use SQLAlchemy to query count
            metadata = MetaData()
            table = Table(settings.ACTUAL_TABLE_NAME, metadata, autoload_with=engine)
            count_query = select(func.count()).select_from(table)
            result = conn.execute(count_query)
            count = result.scalar()
            print(f"✅ Database contains {count} vectors")
    except Exception as e:
        print(f"⚠️  Could not verify database: {e}")
    
    print(f"✅ Pipeline finished. Processed {len(nodes)} nodes (including cached).")
    print("🎉 Ingestion Complete.")
    
if __name__ == "__main__":
    main()