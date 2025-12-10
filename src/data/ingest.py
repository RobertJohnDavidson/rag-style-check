import os
import json
import glob
import asyncio 
import pickle
import hashlib
from pathlib import Path
from google.cloud import storage
from google.cloud.sql.connector import Connector, IPTypes
from google.genai.types import EmbedContentConfig
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine 
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.schema import TextNode
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# Load environment variables
load_dotenv()

# --- CONFIGURATION (INLINED) ---
PROJECT_ID = os.getenv("PROJECT_NAME")
REGION = os.getenv("DB_REGION")
INSTANCE_NAME = os.getenv("INSTANCE_NAME")
DB_NAME = "postgres"
DB_USER = os.getenv("DB_USER")
TABLE_NAME = "rag_vectors"
JSON_DATA_DIR = os.getenv("JSON_DATA_DIR")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
EMBED_DIM = 768
CACHE_DIR = os.getenv("EMBEDDING_CACHE_DIR", "./cache/embeddings")

# Inline Constants
RULE_TAGS = [
    "Capitalization", "Punctuation", "Spelling", "Grammar", "Numbers",
    "Dates & Time", "Geography", "Titles & Ranks", "Abbreviations",
    "Formatting", "Usage & Diction", "Proper Names", "Bias & Sensitivity"
]

# --- GLOBAL CONNECTOR ---
connector = Connector()

Settings.embed_model = GoogleGenAIEmbedding(
    model_name=EMBEDDING_MODEL,
    embed_batch_size=10,
    vertexai_config={"project": PROJECT_ID, "location": REGION},
    embedding_config=EmbedContentConfig(
        output_dimensionality=EMBED_DIM  # 768
    )
)

def get_ip_type():
    if os.getenv("K_SERVICE"):
        return IPTypes.PRIVATE
    return IPTypes.PUBLIC

# 1. Synchronous Connection Function
def get_sync_conn():
    return connector.connect(
        f"{PROJECT_ID}:{REGION}:{INSTANCE_NAME}",
        "pg8000",
        user=DB_USER,
        db=DB_NAME,
        enable_iam_auth=True,
        ip_type=get_ip_type()
    )

# 2. Asynchronous Connection Function
async def get_async_conn():
    return await connector.connect_async(
        f"{PROJECT_ID}:{REGION}:{INSTANCE_NAME}",
        "asyncpg",
        user=DB_USER,
        db=DB_NAME,
        enable_iam_auth=True,
        ip_type=get_ip_type()
    )


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
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        count = 0
        for blob in blobs:
            if blob.name.endswith(".json"):
                try:
                    content = blob.download_as_text()
                    data = json.loads(content)
                    entries = data if isinstance(data, list) else [data]
                    for entry in entries:
                        nodes.append(create_node_from_entry(entry))
                    count += 1
                except Exception as e:
                    print(f"❌ Error processing {blob.name}: {e}")
        print(f"📂 Found and processed {count} JSON files from GCS.")
    except Exception as e:
        print(f"❌ Error accessing GCS: {e}")
    return nodes

def load_nodes(directory):
    if directory.startswith("gs://"):
        return load_nodes_from_gcs(directory)

    nodes = []
    files = glob.glob(os.path.join(directory, "*.json"))
    print(f"📂 Found {len(files)} JSON files. Parsing...")

    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                entries = data if isinstance(data, list) else [data]
                for entry in entries:
                    nodes.append(create_node_from_entry(entry))
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")
    return nodes


def get_cache_key(nodes):
    """Generate a cache key based on node contents and embedding model."""
    content_hash = hashlib.sha256()
    for node in nodes:
        content_hash.update(node.text.encode('utf-8'))
        content_hash.update(str(node.metadata).encode('utf-8'))
    content_hash.update(EMBEDDING_MODEL.encode('utf-8'))
    return content_hash.hexdigest()


def load_cached_nodes(cache_key):

    """Load nodes with embeddings from cache if available."""
    cache_path = Path(CACHE_DIR) / f"{cache_key}.pkl"
    if cache_path.exists():
        print(f"📦 Loading cached embeddings from {cache_path}")
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"⚠️  Cache load failed: {e}. Will re-embed.")
    return None


def save_cached_nodes(cache_key, nodes):
    """Save nodes with embeddings to cache."""
    cache_path = Path(CACHE_DIR) / f"{cache_key}.pkl"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"💾 Saving embeddings to cache: {cache_path}")
    try:
        with open(cache_path, 'wb') as f:
            pickle.dump(nodes, f)
        print(f"✅ Cache saved successfully")
    except Exception as e:
        print(f"⚠️  Cache save failed: {e}")


def main():
    # 1. Load Data
    nodes = load_nodes(JSON_DATA_DIR)
    print(f"✅ Processed {len(nodes)} nodes.")

    # 2. Check cache for embeddings
    cache_key = get_cache_key(nodes)
    cached_nodes = load_cached_nodes(cache_key)
    
    if cached_nodes:
        print(f"🎯 Using {len(cached_nodes)} cached nodes with embeddings")
        nodes = cached_nodes
    else:
        print(f"🔄 Will generate embeddings (cache miss or invalid)")

    print(f"🔌 Connecting to Cloud SQL...")

    # 3. Create Engines & Vector Store
    # Sync Engine (for table creation and standard queries)
    engine = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=get_sync_conn,
    )

    # Async Engine (for high-speed async ingestion used by LlamaIndex)
    async_engine = create_async_engine(
        "postgresql+asyncpg://",
        async_creator=get_async_conn,
    )

    # Initialize PGVectorStore with BOTH engines
    vector_store = PGVectorStore(
        engine=engine,
        async_engine=async_engine, 
        table_name=TABLE_NAME,
        embed_dim=EMBED_DIM,
        hnsw_kwargs={
            "hnsw_m": 24,                
            "hnsw_ef_construction": 512, 
            "hnsw_dist_method": "vector_cosine_ops",
        },
    )
    
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 4. Ingest (this triggers embedding if not cached)
    print("🚀 Indexing...")
    index = VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        show_progress=True
    )
    
    # 5. Save embeddings to cache after successful embedding
    if not cached_nodes:
        # Nodes now have embeddings after indexing
        save_cached_nodes(cache_key, list(index.docstore.docs.values()))
    
    print("🎉 Ingestion Complete.")
    
    # Cleanup (Optional but good practice)
    # connector.close() # Can't easily close global in main, but script exit handles it.

if __name__ == "__main__":
    main()