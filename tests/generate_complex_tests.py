import json
import random
import argparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import chromadb
from spacy.lang.en import English

from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core import Settings, VectorStoreIndex, QueryBundle
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.retrievers import VectorIndexRetriever

# Import reranker if available
try:
    from src.vertex_rerank import VertexAIRerank
except ImportError:
    VertexAIRerank = None

load_dotenv()

# Configuration
PROJECT_NAME = os.getenv("PROJECT_NAME")
REGION = os.getenv("REGION", "us-central1")
MODEL = os.getenv("MODEL", "models/gemini-1.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
DB_PATH = os.getenv("DB_PATH", "./db/chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "cbc_style_guide")

if not PROJECT_NAME:
    raise ValueError("PROJECT_NAME not found in environment variables.")

# Configure embeddings
Settings.embed_model = GoogleGenAIEmbedding(
    model_name=EMBEDDING_MODEL,
    vertexai_config={
        "project": PROJECT_NAME,
        "location": REGION
    }
)

# Configure LLM
Settings.llm = GoogleGenAI(
    model=MODEL,
    vertexai_config={
        "project": PROJECT_NAME,
        "location": REGION
    },
    temperature=0.7
)

# NLP for sentence splitting
nlp = English()
nlp.add_pipe("sentencizer")

# RAG Configuration (matching optimized auditor parameters)
INITIAL_RETRIEVAL_COUNT = 50  # Increased from 20 for better coverage
FINAL_TOP_K = 15              # Increased from 10 for more context
RERANK_SCORE_THRESHOLD = 0.10  # Lowered from 0.25 for better recall
RERANK_TOP_N = 15              # Match FINAL_TOP_K


def fetch_cbc_article_text(url):
    """Scrapes paragraph text from a CBC article URL."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.google.com/',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    try:
        # 2. Pass the headers into the request
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        paragraphs = []
        
        # 3. CBC structure update:
        # They often use 'story' class, but looking for the main <article> tag is safer.
        # If specific classes fail, we fall back to the generic 'story' or 'detailContent'.
        content_div = (
            soup.find('div', class_='story') or 
            soup.find('article') or 
            soup.find('div', class_='sc-content')
        )
        
        if content_div:
            for p in content_div.find_all('p'):
                text = p.get_text().strip()
                # Filtering logic
                if len(text) > 50: 
                    paragraphs.append(text)
        else:
            print("Connection successful, but content container not found. Check HTML classes.")

        return paragraphs

    except requests.exceptions.RequestException as e:
        print(f"Error fetching article: {e}")
        return []

def generate_synthetic_paragraph(topic):
    """Asks LLM to write a clean paragraph on a topic."""
    prompt = f"Write a single, neutral news paragraph about {topic}. It should be around 3-4 sentences long. Do not include any obvious style errors yet."
    return Settings.llm.complete(prompt).text.strip()

def retrieve_relevant_rules(text, retriever, reranker=None, top_k=15):
    """Retrieve relevant style guide rules from vector DB with query expansion and keyword backup."""
    import re
    
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 5]
    
    aggregated = {}
    
    # Query expansion mapping
    def expand_query(query):
        expanded = [query]
        query_lower = query.lower()
        
        if "quotation" in query_lower:
            expanded.extend(["quotes", "quotation marks"])
        if "dash" in query_lower:
            expanded.extend(["em dash", "en dash", "hyphen"])
        if "capital" in query_lower:
            expanded.extend(["uppercase", "lowercase"])
        
        return expanded[:2]  # Limit to 2 variations
    
    # Sentence-based retrieval with query expansion
    for sentence in sentences[:3]:  # Sample first 3 sentences
        queries = expand_query(sentence)
        
        for query in queries:
            nodes = retriever.retrieve(query)
            
            # Apply reranker if available
            if nodes and reranker:
                try:
                    query_bundle = QueryBundle(query_str=query)
                    nodes = reranker.postprocess_nodes(nodes=nodes, query_bundle=query_bundle)
                    # Filter by threshold
                    nodes = [n for n in nodes if getattr(n, 'score', 0) >= RERANK_SCORE_THRESHOLD]
                except Exception:
                    nodes = nodes[:5]
            else:
                nodes = nodes[:5] if nodes else []
            
            for node in nodes:
                term = node.metadata.get('term', 'Unknown Rule')
                key = (term, node.metadata.get('url', ''))
                score = getattr(node, 'score', 0)
                
                if key not in aggregated or score > aggregated[key]['score']:
                    aggregated[key] = {
                        "term": term,
                        "text": node.metadata.get('display_text', node.get_content()),
                        "url": node.metadata.get('url', ''),
                        "score": score
                    }
    
    # Keyword-based backup retrieval if insufficient rules
    if len(aggregated) < 10:
        # Extract capitalized words/phrases as keywords
        keywords = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        unique_keywords = list(dict.fromkeys(keywords))[:5]  # Deduplicate, take top 5
        
        for keyword in unique_keywords:
            nodes = retriever.retrieve(keyword)
            
            if reranker and nodes:
                try:
                    query_bundle = QueryBundle(query_str=keyword)
                    nodes = reranker.postprocess_nodes(nodes=nodes, query_bundle=query_bundle)
                    nodes = [n for n in nodes if getattr(n, 'score', 0) >= RERANK_SCORE_THRESHOLD]
                except Exception:
                    nodes = nodes[:3]
            else:
                nodes = nodes[:3] if nodes else []
            
            for node in nodes:
                term = node.metadata.get('term', 'Unknown Rule')
                key = (term, node.metadata.get('url', ''))
                score = getattr(node, 'score', 0) * 0.8  # Slightly lower priority for keyword matches
                
                if key not in aggregated or score > aggregated[key]['score']:
                    aggregated[key] = {
                        "term": term,
                        "text": node.metadata.get('display_text', node.get_content()),
                        "url": node.metadata.get('url', ''),
                        "score": score
                    }
    
    sorted_rules = sorted(aggregated.values(), key=lambda r: r['score'], reverse=True)
    return sorted_rules[:top_k]


def inject_errors(text, num_errors, retriever=None, reranker=None):
    """Asks LLM to rewrite text with specific errors using RAG-retrieved rules."""
    if num_errors == 0:
        return {"text": text, "expected_violations": []}
    
    # Retrieve relevant rules from vector DB (using optimized top_k)
    retrieved_rules = retrieve_relevant_rules(text, retriever, reranker, top_k=FINAL_TOP_K)
    
    print(f"   Retrieved {len(retrieved_rules)} rules (scores: {[f'{r['score']:.3f}' for r in retrieved_rules[:3]]})")
    
    if not retrieved_rules:
        print("⚠️ No rules retrieved from vector DB")
        return {"text": text, "expected_violations": []}
    
    rules_list = []
    for idx, rule in enumerate(retrieved_rules, 1):
        rules_list.append(
            f"{idx}. **{rule['term']}**\n"
            f"   Guideline: {rule['text']}\n"
            f"   URL: {rule.get('url', 'N/A')}"
        )
    rules_context = "RETRIEVED STYLE GUIDE RULES:\n" + "\n\n".join(rules_list)
    
    prompt = f"""
You are a 'Bad Style' Generator for CBC News style guide violations.

Below are relevant CBC News style guide rules retrieved from the database.

{rules_context}

ORIGINAL PARAGRAPH:
"{text}"

TASK:
1. Select {num_errors} diverse rules from the list above
2. Rewrite the paragraph to violate EXACTLY those {num_errors} rules
3. Make each violation realistic and subtle (how a journalist might naturally err)
4. Keep the rest of the text as close to the original as possible
5. For each violation, identify the EXACT substring that contains the error

Return ONLY a JSON object (no markdown fences, no extra text):

{{
    "text": "The rewritten paragraph with {num_errors} style violations",
    "expected_violations": [
        {{
            "rule": "Exact rule name from the list above",
            "text": "The specific substring/phrase that violates the rule",
            "source_url": "The URL from the rule's metadata above"
        }}
    ]
}}
"""
    
    response = Settings.llm.complete(prompt).text.strip()
    
    # Clean up markdown fences
    if response.startswith("```json"):
        response = response[7:]
    elif response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]
    
    response = response.strip()
    
    try:
        result = json.loads(response)
        # Validate structure
        if not isinstance(result.get('text'), str) or not isinstance(result.get('expected_violations'), list):
            raise ValueError("Invalid JSON structure")
        return result
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse LLM response for error injection: {e}")
        print(f"Response was: {response[:200]}...")
        return {"text": text, "expected_violations": []}

def main():
    parser = argparse.ArgumentParser(description="Generate complex test cases with style violations")
    parser.add_argument("--mode", choices=["synthetic", "real"], default="synthetic",
                       help="Source material: synthetic (LLM-generated) or real (scraped from CBC)")
    parser.add_argument("--count", type=int, default=10, help="Number of test cases to generate")
    parser.add_argument("--output", default="tests/generated_tests_complex.json")
    parser.add_argument("--url", help="CBC Article URL (required if mode is real)")
    parser.add_argument("--min-errors", type=int, default=0, help="Minimum violations per test case")
    parser.add_argument("--max-errors", type=int, default=5, help="Maximum violations per test case")
    
    args = parser.parse_args()
    
    # Initialize ChromaDB retriever
    print("🔌 Connecting to ChromaDB...")
    chroma_client = chromadb.PersistentClient(path=DB_PATH)
    chroma_collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=Settings.embed_model
    )
    
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=INITIAL_RETRIEVAL_COUNT  # Use optimized parameter
    )
    
    # Initialize reranker if available
    reranker = None
    if VertexAIRerank:
        try:
            reranker = VertexAIRerank(
                project_id=PROJECT_NAME,
                location_id=REGION,
                ranking_config="default_ranking_config",
                top_n=RERANK_TOP_N  # Use optimized parameter
            )
            print(f"✓ Reranker initialized (top_n={RERANK_TOP_N}, threshold={RERANK_SCORE_THRESHOLD})")
        except Exception as e:
            print(f"⚠️ Reranker initialization failed: {e}")
    
    test_cases = []
    case_id = 1
    
    if args.mode == "real":
        if not args.url:
            print("Error: --url is required for real mode")
            return
        
        print(f"Fetching article from {args.url}...")
        paragraphs = fetch_cbc_article_text(args.url)
        
        if not paragraphs:
            print("No paragraphs found. Check the URL or article structure.")
            return
            
        print(f"Found {len(paragraphs)} paragraphs.")
        # Randomly select paragraphs to process
        selected_paragraphs = random.sample(paragraphs, min(args.count, len(paragraphs)))
        
        for i, p in enumerate(selected_paragraphs, 1):
            num_errors = random.randint(args.min_errors, args.max_errors)
            print(f"Processing paragraph {i}/{len(selected_paragraphs)} with {num_errors} target violations...")
            
            if num_errors == 0:
                result = {"text": p, "expected_violations": []}
            else:
                result = inject_errors(p, num_errors, retriever, reranker)
            
            result["id"] = f"complex_real_{case_id}"
            case_id += 1
            test_cases.append(result)
            print(f"  ✓ Generated with {len(result['expected_violations'])} violations.")

    else: # Synthetic
        topics = [
            "politics and government policy",
            "technology and innovation", 
            "sports and athletics",
            "health and medical research",
            "environment and climate",
            "business and economy",
            "education and schools",
            "crime and justice",
            "arts and entertainment",
            "science and discovery"
        ]
        
        for i in range(args.count):
            topic = random.choice(topics)
            num_errors = random.randint(args.min_errors, args.max_errors)
            print(f"[{i+1}/{args.count}] Generating paragraph about {topic} with {num_errors} target violations...")
            
            clean_text = generate_synthetic_paragraph(topic)
            
            if num_errors == 0:
                result = {"text": clean_text, "expected_violations": []}
            else:
                result = inject_errors(clean_text, num_errors, retriever, reranker)
            
            result["id"] = f"complex_syn_{case_id}"
            case_id += 1
            test_cases.append(result)
            print(f"  ✓ Generated with {len(result['expected_violations'])} violations.")
            
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(test_cases, f, indent=2, ensure_ascii=False)
    
    # Summary statistics
    total_violations = sum(len(tc['expected_violations']) for tc in test_cases)
    avg_violations = total_violations / len(test_cases) if test_cases else 0
    zero_violation_cases = sum(1 for tc in test_cases if len(tc['expected_violations']) == 0)
    
    print("\n" + "="*50)
    print(f"✓ Saved {len(test_cases)} test cases to {args.output}")
    print(f"  Total violations: {total_violations}")
    print(f"  Average violations per case: {avg_violations:.1f}")
    print(f"  Cases with 0 violations (True Negative tests): {zero_violation_cases}")
    print("="*50)

if __name__ == "__main__":
    main()
