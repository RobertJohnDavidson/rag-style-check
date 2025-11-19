import os
import chromadb
import json
from dotenv import load_dotenv
from spacy.lang.en import English  # Lightweight SpaCy

from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.retrievers import VectorIndexRetriever

# Using Google GenAI for Embeddings (as per your snippet)
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# Using Vertex AI for the LLM (matches your project/region config)
from llama_index.llms.google_genai import GoogleGenAI

load_dotenv()

# --- CONFIGURATION ---
DB_PATH = os.getenv("DB_PATH")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
MODEL = os.getenv("MODEL")
PROJECT_NAME = os.getenv("PROJECT_NAME")
REGION = os.getenv("REGION")
CONFIDENCE_THRESHOLD = 0.48 

if not PROJECT_NAME:
    raise ValueError("PROJECT_NAME not found in environment variables.")

# 1. Configure Embeddings (Your specific Vertex setup)
Settings.embed_model = GoogleGenAIEmbedding(
    model_name=EMBEDDING_MODEL,
    vertexai_config={
        "project": PROJECT_NAME,
        "location": REGION
    }
)

# 2. Configure LLM (The Auditor)
# We use Vertex here to match your embedding auth method
Settings.llm = GoogleGenAI(
    model=MODEL,
    vertexai_config={
        "project": PROJECT_NAME,
        "location": REGION
    },
    temperature=0.1
)

# 3. Load Lightweight Spacy (No model download needed)
try:
    nlp = English()
    nlp.add_pipe("sentencizer")
except Exception as e:
    print(f"Error initializing Spacy: {e}")
    exit()

class StyleAuditor:
    def __init__(self, top_k=3, confidence_threshold=CONFIDENCE_THRESHOLD):
        if not os.path.exists(DB_PATH):
            raise FileNotFoundError("Database not found. Run ingest.py first.")

        # print("Loading Style Guide Database...")
        db = chromadb.PersistentClient(path=DB_PATH)
        chroma_collection = db.get_or_create_collection(COLLECTION_NAME)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

        self.confidence_threshold = confidence_threshold
        self.top_k = top_k
        
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            embed_model=Settings.embed_model
        )
        
        self.retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=top_k 
        )

    def check_text(self, text):
        """
        Audits a text block and returns a list of violations.
        Returns: List[Dict]
        """
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if len(sent.text) > 5]
        
        all_violations = []

        for sentence in sentences:
            violation = self._audit_sentence(sentence)
            if violation:
                all_violations.append(violation)
        
        return all_violations

    def _audit_sentence(self, sentence):
        # 1. Retrieve Rules
        nodes = self.retriever.retrieve(sentence)
        
        # 2. Filter by Confidence
        relevant_nodes = [n for n in nodes if n.score > self.confidence_threshold]

        if not relevant_nodes:
            return None

        # 3. Construct Context
        context_block = ""
        citations = {}
        
        for i, node in enumerate(relevant_nodes):
            term = node.metadata['term']
            rule_text = node.metadata.get('display_text', node.get_content())
            url = node.metadata.get('url', 'No URL')
            
            context_block += f"RULE #{i+1} ({term}):\n{rule_text}\n\n"
            citations[f"RULE #{i+1}"] = url

        # 4. The Structured Prompt (Forces JSON)
        prompt = f"""
        You are an expert Copy Editor for CBC News.
        Check the User Sentence against the Rules.

        USER SENTENCE: "{sentence}"

        RULES:
        {context_block}

        TASK:
        Return a JSON object with the results.
        If the sentence is correct or the rules don't apply, return "status": "PASS".
        If there is a violation, return "status": "FAIL" and fill the other fields.

        JSON SCHEMA:
        {{
            "status": "PASS" | "FAIL",
            "violation_explanation": "Why it is wrong (or null)",
            "correction": "Corrected sentence (or null)",
            "cited_rule_id": "RULE #1" (or null)
        }}

        Do not include markdown formatting (```json). Just the raw JSON string.
        """

        # 5. Generate and Parse
        try:
            response_text = Settings.llm.complete(prompt).text.strip()
            
            # Cleanup markdown if the LLM adds it
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "")

            result = json.loads(response_text)

            if result.get("status") == "FAIL":
                # Attach metadata and URL
                rule_id = result.get("cited_rule_id", "RULE #1")
                citation_url = citations.get(rule_id, "")
                
                return {
                    "sentence": sentence,
                    "violation": result.get("violation_explanation"),
                    "correction": result.get("correction"),
                    "source_url": citation_url,
                    "rule_context": rule_id
                }
            
            return None # PASS

        except Exception as e:
            print(f"Error parsing LLM response for '{sentence}': {e}")
            return None

if __name__ == "__main__":
    auditor = StyleAuditor()
    
    test_text = "The government needs to do more for Aboriginal housing. I watched the live stream."
    
    print(f"Analyzing: {test_text}\n")
    results = auditor.check_text(test_text)
    
    print(json.dumps(results, indent=2))