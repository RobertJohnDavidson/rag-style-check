import os
import json
import chromadb
from dotenv import load_dotenv
from spacy.lang.en import English 

from llama_index.core import VectorStoreIndex, Settings, QueryBundle
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.retrievers import VectorIndexRetriever

# Embeddings & LLM
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI

# Import Common Rules
from src.prompts import COMMON_RULES

# --- IMPORT CUSTOM RERANKER ---
try:
    from src.vertex_rerank import VertexAIRerank
except ImportError:
    print("⚠️ VertexAIRerank class not found. Re-ranking will be skipped.")
    VertexAIRerank = None

load_dotenv()

# --- CONFIGURATION ---
DB_PATH = os.getenv("DB_PATH", "./db/chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "cbc_style_guide")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
MODEL = os.getenv("MODEL", "models/gemini-1.5-flash")
PROJECT_NAME = os.getenv("PROJECT_NAME")
REGION = os.getenv("REGION", "us-central1")

# Tuning
INITIAL_RETRIEVAL_COUNT = 20 
FINAL_TOP_K = 5             
RERANK_SCORE_THRESHOLD = 0.25

if not PROJECT_NAME:
    raise ValueError("PROJECT_NAME not found in environment variables.")

# 1. Configure Embeddings
Settings.embed_model = GoogleGenAIEmbedding(
    model_name=EMBEDDING_MODEL,
    vertexai_config={
        "project": PROJECT_NAME,
        "location": REGION
    }
)

# 2. Configure LLM
Settings.llm = GoogleGenAI(
    model=MODEL,
    vertexai_config={
        "project": PROJECT_NAME,
        "location": REGION
    },
    temperature=0.1
)

# 3. Load NLP
try:
    nlp = English()
    nlp.add_pipe("sentencizer")
except Exception as e:
    print(f"Error initializing Spacy: {e}")
    exit()

class StyleAuditor:
    def __init__(self, top_k=3, confidence_threshold=0.48):
        if not os.path.exists(DB_PATH):
            raise FileNotFoundError("Database not found. Run ingest.py first.")

        # Database
        db = chromadb.PersistentClient(path=DB_PATH)
        chroma_collection = db.get_or_create_collection(COLLECTION_NAME)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

        index = VectorStoreIndex.from_vector_store(
            vector_store,
            embed_model=Settings.embed_model
        )
        
        # A. Retriever (Wide Net)
        self.retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=INITIAL_RETRIEVAL_COUNT 
        )

        # B. Reranker (Initialize if available)
        self.reranker = None
        if VertexAIRerank:
            try:
                self.reranker = VertexAIRerank(
                    project_id=PROJECT_NAME,
                    location_id="global", 
                    ranking_config="default_ranking_config",
                    top_n=FINAL_TOP_K
                )
                print("✅ Vertex AI Re-ranker initialized.")
            except Exception as e:
                print(f"⚠️ Failed to init Reranker: {e}")

    def check_text(self, text):
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if len(sent.text) > 5]
        all_violations = []

        print(f"\n🔍 Auditing {len(sentences)} sentences...")

        for sentence in sentences:
            violation = self._audit_sentence(sentence)
            if violation:
                all_violations.append(violation)
        
        return all_violations

    def _audit_sentence(self, sentence):
        # 1. Retrieve (Vector Search)
        nodes = self.retriever.retrieve(sentence)
        
        # 2. Rerank (Semantic Ranking)
        if nodes and self.reranker:
            try:
                query_bundle = QueryBundle(query_str=sentence)
                nodes = self.reranker.postprocess_nodes(
                    nodes=nodes, 
                    query_bundle=query_bundle
                )
            except Exception as e:
                print(f"Rerank failed (fallback to vector): {e}")
                nodes = nodes[:FINAL_TOP_K]
        elif nodes:
            # Fallback if no reranker loaded
            nodes = nodes[:FINAL_TOP_K]

        # 3. Filter
        valid_nodes = [n for n in nodes if n.score > RERANK_SCORE_THRESHOLD] if nodes else []
        
        # 4. Context Construction
        context_block = ""
        citations = {}
        rule_names = {} 
        
        # Add Retrieved Rules
        for i, node in enumerate(valid_nodes):
            term = node.metadata['term']
            rule_text = node.metadata.get('display_text', node.get_content())
            url = node.metadata.get('url', 'No URL')
            
            rule_id = f"RETRIEVED_RULE_#{i+1}"
            context_block += f"{rule_id} ({term}):\n{rule_text}\n\n"
            citations[rule_id] = url
            rule_names[rule_id] = term

        # 5. LLM Judge
        # We now include COMMON_RULES in the prompt regardless of retrieval success
        prompt = f"""
        You are an expert Copy Editor for CBC News.
        Check the User Sentence against the Rules.

        USER SENTENCE: "{sentence}"

        --- SOURCE A: COMMON HIGH-PRIORITY RULES ---
        {COMMON_RULES}

        --- SOURCE B: SPECIFIC RETRIEVED GUIDELINES ---
        {context_block if context_block else "No specific guidelines found in database."}

        TASK:
        Return a JSON object.
        1. Check against Source A first.
        2. If no violation found, check against Source B.
        If correct or rules don't apply: "status": "PASS".
        If violation: "status": "FAIL".

        JSON SCHEMA:
        {{
            "status": "PASS" | "FAIL",
            "violation_explanation": "Why it is wrong",
            "correction": "Corrected sentence",
            "cited_rule_id": "Name of the rule from Source A (e.g. 'CAPITALIZATION') or ID from Source B (e.g. 'RETRIEVED_RULE_#1')"
        }}
        
        Return ONLY raw JSON. No markdown blocks.
        """

        try:
            response_text = Settings.llm.complete(prompt).text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "")

            result = json.loads(response_text)

            if result.get("status") == "FAIL":
                rule_id = result.get("cited_rule_id", "Unknown")
                
                # Determine source URL
                source_url = citations.get(rule_id, "Common Style Rule (No specific URL)")
                rule_name = rule_names.get(rule_id, rule_id)

                return {
                    "sentence": sentence,
                    "violation": result.get("violation_explanation"),
                    "correction": result.get("correction"),
                    "source_url": source_url,
                    "rule_name": rule_name,
                    "rule_context": rule_id
                }
            return None 

        except Exception as e:
            print(f"Error parsing LLM: {e}")
            return None

if __name__ == "__main__":
    auditor = StyleAuditor()
    test_text = "The government needs to do more for Aboriginal housing."
    print(json.dumps(auditor.check_text(test_text), indent=2))