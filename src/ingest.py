import os
import json
import glob
import chromadb
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.schema import TextNode
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---


EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
JSON_DATA_DIR = os.getenv("JSON_DATA_DIR")
DB_PATH = os.getenv("DB_PATH")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
PROJECT_NAME = os.getenv("PROJECT_NAME")
REGION = os.getenv("REGION")

Settings.embed_model = GoogleGenAIEmbedding(
    model_name=EMBEDDING_MODEL,
    embed_batch_size=100, # Batching for API efficiency
    vertexai_config={
        "project": PROJECT_NAME,
        "location": REGION
    }
)

def create_node_from_entry(entry):
    """
    Transforms a raw JSON entry into a Semantic Vector Node.
    """
    # 1. Extract Data
    term = entry.get("term", "Unknown Rule")
    definition = entry.get("definition", "")
    constraints = entry.get("negative_constraints", []) or []
    url = entry.get("url", "")
    context = entry.get("context_tag", "General")
    entry_type = entry.get("type", "term")
    is_spelling = entry.get("is_spelling_only", False)

    # 2. Construct the "Search Text" (The Vector Content)
    # This is the text the AI compares against the user's draft.
    # We explicitly include negative constraints to "trap" common errors.
    if entry_type == "term":
        search_text = (
            f"Rule: {term}. "
            f"Context: {context}. "
            f"Definition: {definition}. "
            f"Negative Triggers: {' '.join(constraints)}." 
        )
        if is_spelling:
            search_text += f" Strict spelling rule for {term}."
    else:
        # For Policies/Overviews
        search_text = (
            f"Policy Context: {term}. "
            f"Category: {context}. "
            f"Guideline: {definition}"
        )

    # 3. Construct Metadata (The Display Content)
    # This is what the LLM reads to explain the rule to the user.
    display_text = f"**Rule:** {term}\n**Guideline:** {definition}"
    if constraints:
        display_text += f"\n**⛔ AVOID:** {', '.join(constraints)}"

    # 4. Create Node
    node = TextNode(
        text=search_text,
        metadata={
            "term": term,
            "url": url,
            "context": context,
            "display_text": display_text 
        }
    )

    # CRITICAL: Metadata Exclusion
    # We exclude these fields from the embedding to prevent the URL or display text
    # from diluting the vector's semantic meaning.
    node.excluded_embed_metadata_keys = ["term", "url", "context", "display_text"]
    node.excluded_llm_metadata_keys = ["context"] 

    return node

def load_nodes(directory):
    nodes = []
    files = glob.glob(os.path.join(directory, "*.json"))
    print(f"📂 Found {len(files)} JSON files. Parsing...")

    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle both single objects and lists of objects
                entries = data if isinstance(data, list) else [data]
                for entry in entries:
                    nodes.append(create_node_from_entry(entry))
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")
    
    return nodes

def main():
    # 1. Prepare Data
    if not os.path.exists(JSON_DATA_DIR):
        print(f"❌ Directory not found: {JSON_DATA_DIR}")
        return
    
    nodes = load_nodes(JSON_DATA_DIR)
    print(f"✅ Processed {len(nodes)} nodes.")

    # 2. Setup Database
    print(f"🔌 Connecting to ChromaDB at {DB_PATH}...")
    db = chromadb.PersistentClient(path=DB_PATH)
    chroma_collection = db.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 3. Ingest
    print("🚀 Generating embeddings and indexing...")
    VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        show_progress=True
    )
    print("🎉 Ingestion Complete.")

if __name__ == "__main__":
    main()