import chromadb
from spacy.lang.en import English  # Lightweight SpaCy
import os
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.retrievers import VectorIndexRetriever

load_dotenv()

DB_PATH = os.getenv("DB_PATH")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
PROJECT_NAME = os.getenv("PROJECT_NAME")
REGION = os.getenv("REGION")
Settings.embed_model = GoogleGenAIEmbedding(
    model_name=EMBEDDING_MODEL,
    vertexai_config={
        "project": PROJECT_NAME,
        "location": REGION
    }
)


# 3. Load Lightweight Spacy (No model download needed)
try:
    nlp = English()
    nlp.add_pipe("sentencizer")
except Exception as e:
    print(f"Error initializing Spacy: {e}")
    exit()

# --- THE RETRIEVER ---
db = chromadb.PersistentClient(path=DB_PATH)
chroma_collection = db.get_or_create_collection(COLLECTION_NAME)
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
index = VectorStoreIndex.from_vector_store(vector_store, embed_model=Settings.embed_model)

# Get top 3 matches
retriever = VectorIndexRetriever(index=index, similarity_top_k=3)

# --- TEST CASES ---
test_sentences = [
    "The government needs to do more for Aboriginal housing.",  # Should hit 'Aboriginal' rule
    "I watched the live stream yesterday.",                    # Should hit 'Livestream' rule
    "He bought some kleenex.",                                 # Should hit 'Trade Names'
    "The department of defence issued a statement."            # Should hit 'Department' capitalization
]

print(f"🔎 TESTING RETRIEVAL ONLY (No LLM Judgment)\n")

for text in test_sentences:
    print(f"📝 INPUT: '{text}'")
    results = retriever.retrieve(text)
    
    found = False
    for node in results:
        # We only care about high-confidence matches
        if node.score > 0.45:
            print(f"   ✅ HIT: {node.metadata['term']}")
            print(f"      Score: {node.score:.4f}")
            print(f"      Context Tag: {node.metadata['context']}")
            found = True
    
    if not found:
        print("   ❌ MISS: No relevant rules found (Score too low).")
    print("-" * 40)