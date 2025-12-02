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
INITIAL_RETRIEVAL_COUNT = 50  # Increased from 20 for better initial recall
FINAL_TOP_K = 15              # Increased from 10 to give more context
RERAN_SCORE_THRESHOLD = 0.10  # Lowered from 0.15 to be even less strict
AGGREGATED_RULE_LIMIT = 25    # Increased from 20 for more comprehensive coverage
MIN_SENTENCE_LENGTH = 5
MAX_AGENT_ITERATIONS = 3  # Max thinking cycles for agent refinement
INCLUDE_COMMON_RULES = False

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
nlp = English()
nlp.add_pipe("sentencizer")

class StyleAuditor:
    def __init__(self):
        print("Connecting to ChromaDB...")
        self.chroma_client = chromadb.PersistentClient(path=DB_PATH)
        self.chroma_collection = self.chroma_client.get_or_create_collection(name=COLLECTION_NAME)
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            embed_model=Settings.embed_model
        )
        
        self.retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=INITIAL_RETRIEVAL_COUNT
        )

        if VertexAIRerank:
            self.reranker = VertexAIRerank(
                project_id=PROJECT_NAME,
                location_id=REGION,
                ranking_config="default_ranking_config",
                top_n=FINAL_TOP_K
            )
        else:
            self.reranker = None

    def check_text(self, text):
        paragraphs = self._split_paragraphs(text)
        all_violations = []

        print(f"\n🔍 Auditing {len(paragraphs)} paragraph(s)...")

        for paragraph in paragraphs:
            paragraph_violations = self._audit_paragraph_agentic(paragraph)
            if paragraph_violations:
                all_violations.extend(paragraph_violations)
        
        # Final deduplication pass across all paragraphs
        return self._deduplicate_violations(all_violations)

    def _split_paragraphs(self, text):
        if not text:
            return []
        chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
        if chunks:
            return chunks
        stripped = text.strip()
        return [stripped] if stripped else []

    def _audit_paragraph_agentic(self, paragraph):
        """Agentic audit with iterative refinement and self-reflection."""
        doc = nlp(paragraph)
        sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > MIN_SENTENCE_LENGTH]
        
        # Initial retrieval
        contexts = self._collect_rule_contexts(sentences)
        violations = []
        
        print(f"\n{'='*60}")
        print(f"🤖 AGENTIC AUDIT - Starting analysis")
        print(f"{'='*60}")
        
        for iteration in range(MAX_AGENT_ITERATIONS):
            print(f"\n--- Iteration {iteration + 1}/{MAX_AGENT_ITERATIONS} ---")
            
            # Ask agent to audit with current context
            prompt = self._build_paragraph_prompt(paragraph, contexts, violations, iteration)
            
            print(f"📤 Sending prompt to LLM...")
            if iteration == 0:
                print(f"   Context rules: {len(contexts)}")
            
            try:
                response_text = Settings.llm.complete(prompt).text.strip()
                print(f"\n📥 LLM Response:")
                print(f"{'-'*60}")
                print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
                print(f"{'-'*60}")
                
                response_text = self._strip_json_code_fence(response_text)
                result = json.loads(response_text) if response_text else {}
            except Exception as e:
                print(f"❌ Error calling LLM (iteration {iteration + 1}): {e}")
                break
            
            # Parse response
            if isinstance(result, dict):
                new_violations = result.get("violations", [])
                needs_more_context = result.get("needs_more_context", False)
                is_confident = result.get("confident", True)  # Default to confident
                additional_queries = result.get("additional_queries", [])
                
                print(f"\n✅ Agent response parsed:")
                print(f"   - Found {len(new_violations)} violations")
                print(f"   - Confident: {is_confident}")
                print(f"   - Needs more context: {needs_more_context}")
                if additional_queries:
                    print(f"   - Additional queries: {additional_queries}")
            else:
                new_violations = result if isinstance(result, list) else []
                needs_more_context = False
                is_confident = True
                additional_queries = []
            
            # Update violations
            if new_violations:
                violations = self._format_violations(new_violations, paragraph, contexts)
                print(f"   - Formatted {len(violations)} violations")
            
            # If agent is confident, stop early
            # BUT: Don't trust confidence if we have very few rules
            if is_confident and not needs_more_context:
                if len(contexts) < 10:
                    print(f"⚠️  Agent claims confidence but only {len(contexts)} rules available. Requesting more context.")
                    is_confident = False
                    needs_more_context = True
                    # Generate queries based on paragraph content
                    import re
                    paragraph_text = paragraph
                    keywords = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', paragraph_text)
                    additional_queries = list(set(keywords))[:3]
                else:
                    print(f"\n✅ Agent is confident. Stopping at iteration {iteration + 1}.")
                    break
            
            # If max iterations reached, stop
            if iteration == MAX_AGENT_ITERATIONS - 1:
                print(f"\n⏱️  Max iterations reached. Stopping.")
                break
            
            # Retrieve additional context based on agent's questions
            if additional_queries:
                print(f"\n🔍 Agent requesting more context...")
                print(f"   Queries: {additional_queries}")
                additional_contexts = self._collect_additional_contexts(additional_queries)
                print(f"   - Retrieved {len(additional_contexts)} additional rules:")
                for ctx in additional_contexts[:3]:
                    print(f"     • {ctx['term']} (score: {ctx['score']:.3f})")
                contexts.extend(additional_contexts)
        
        # Deduplicate violations within this paragraph
        deduplicated = self._deduplicate_violations(violations)
        print(f"\n🔧 Deduplication: {len(violations)} → {len(deduplicated)} violations")
        print(f"{'='*60}\n")
        
        return deduplicated
    
    def _audit_paragraph(self, paragraph):
        """Legacy method for backwards compatibility."""
        return self._audit_paragraph_agentic(paragraph)

    def _collect_additional_contexts(self, queries):
        """Retrieve additional rule contexts based on agent's questions."""
        aggregated = {}
        
        for query in queries[:3]:  # Limit to 3 additional queries
            # Expand query with synonyms/variations for better matching
            expanded_queries = [query]
            
            # Add variations for better semantic matching
            if "quotation" in query.lower():
                expanded_queries.extend(["quotes", "quotation marks", "quote marks"])
            if "dash" in query.lower():
                expanded_queries.extend(["em dash", "en dash", "hyphen"])
            if "capitalization" in query.lower() or "capital" in query.lower():
                expanded_queries.extend(["uppercase", "lowercase", "title case"])
            
            # Retrieve with all query variations
            for q in expanded_queries[:2]:  # Limit to avoid explosion
                nodes = self.retriever.retrieve(q)
                
                if nodes and self.reranker:
                    try:
                        query_bundle = QueryBundle(query_str=query)  # Use original query for reranking
                        nodes = self.reranker.postprocess_nodes(nodes=nodes, query_bundle=query_bundle)
                    except Exception:
                        nodes = nodes[:FINAL_TOP_K]
                else:
                    nodes = nodes[:FINAL_TOP_K] if nodes else []
                
                for node in self._filter_nodes(nodes):
                    term = node.metadata.get('term', 'Untitled Rule')
                    key = (term, node.metadata.get('url', ''))
                    score = getattr(node, 'score', 0)
                    current = aggregated.get(key)
                    if not current or score > current['score']:
                        aggregated[key] = {
                            "term": term,
                            "text": node.metadata.get('display_text', node.get_content()),
                            "url": node.metadata.get('url', ''),
                            "score": score,
                            "source_type": "additional_retrieval",
                            "query_used": q
                        }
        
        sorted_rules = sorted(aggregated.values(), key=lambda r: r['score'], reverse=True)
        limited = sorted_rules[:10]  # Increased from 5
        
        for idx, rule in enumerate(limited, start=100):  # Start IDs at 100 to differentiate
            rule["id"] = f"ADDITIONAL_RULE_#{idx}"
        
        return limited
    
    def _collect_rule_contexts(self, sentences):
        aggregated = {}

        # Retrieve based on full sentences
        for sentence in sentences:
            nodes = self._retrieve_nodes(sentence)
            for node in nodes:
                term = node.metadata.get('term', 'Untitled Rule')
                key = (term, node.metadata.get('url', ''))
                score = getattr(node, 'score', 0)
                current = aggregated.get(key)
                if not current or score > current['score']:
                    aggregated[key] = {
                        "term": term,
                        "text": node.metadata.get('display_text', node.get_content()),
                        "url": node.metadata.get('url', ''),
                        "score": score,
                        "source_type": "retrieved"
                    }

            if len(aggregated) >= AGGREGATED_RULE_LIMIT:
                break
        
        # If we didn't get enough rules, try keyword-based retrieval
        if len(aggregated) < 10:
            # Extract important words from the paragraph
            import re
            paragraph_text = " ".join(sentences)
            # Find capitalized words, proper nouns, and important terms
            keywords = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', paragraph_text)
            keywords = list(set(keywords))[:5]  # Unique, limit to 5
            
            for keyword in keywords:
                nodes = self._retrieve_nodes(keyword)
                for node in nodes[:3]:  # Limit per keyword
                    term = node.metadata.get('term', 'Untitled Rule')
                    key = (term, node.metadata.get('url', ''))
                    score = getattr(node, 'score', 0) * 0.8  # Slightly lower priority
                    current = aggregated.get(key)
                    if not current or score > current['score']:
                        aggregated[key] = {
                            "term": term,
                            "text": node.metadata.get('display_text', node.get_content()),
                            "url": node.metadata.get('url', ''),
                            "score": score,
                            "source_type": "keyword_retrieval"
                        }

        sorted_rules = sorted(aggregated.values(), key=lambda r: r['score'], reverse=True)
        limited = sorted_rules[:AGGREGATED_RULE_LIMIT]

        for idx, rule in enumerate(limited, start=1):
            rule["id"] = f"RETRIEVED_RULE_#{idx}"

        return limited

    def _retrieve_nodes(self, sentence):
        nodes = self.retriever.retrieve(sentence)

        if nodes and self.reranker:
            try:
                query_bundle = QueryBundle(query_str=sentence)
                nodes = self.reranker.postprocess_nodes(nodes=nodes, query_bundle=query_bundle)
            except Exception as e:
                print(f"Rerank failed (fallback to vector): {e}")
                nodes = nodes[:FINAL_TOP_K]
        elif nodes:
            nodes = nodes[:FINAL_TOP_K]

        return self._filter_nodes(nodes)

    def _filter_nodes(self, nodes):
        if not nodes:
            return []
        return [node for node in nodes if getattr(node, 'score', 0) >= RERAN_SCORE_THRESHOLD]

    def _build_paragraph_prompt(self, paragraph, contexts, current_violations=None, iteration=0):
        if contexts:
            context_lines = []
            for entry in contexts:
                context_lines.append(
                    f"{entry['id']} | Rule: {entry['term']}\nURL: {entry['url'] or 'Unknown'}\nGuideline: {entry['text']}"
                )
            context_block = "\n\n".join(context_lines)
        else:
            context_block = "No specific rules were retrieved from the database for this text."
        
        # Add reflection context if this is a refinement iteration
        reflection_block = ""
        if iteration > 0 and current_violations:
            violations_summary = "\n".join([f"- {v.get('text', 'N/A')}: {v.get('violation', 'N/A')}" for v in current_violations[:5]])
            reflection_block = f"""
        --- PREVIOUS ANALYSIS (Iteration {iteration}) ---
        You previously found these violations:
        {violations_summary}
        
        Review your previous findings. Are there duplicates? Did you miss anything? Do you need more context?
        """

        # # Conditionally add common rules
        # common_rules_block = ""
        # if INCLUDE_COMMON_RULES:
        #     common_rules_block = f"""
        # --- COMMON CBC RULES (reference as COMMON_RULE:<Title>) ---
        # {COMMON_RULES}
        # """
        
        prompt = f"""
        You are an expert Copy Editor for CBC News with agentic capabilities.
        Review the entire paragraph below and flag every rule violation you can find.

        USER PARAGRAPH:
        "{paragraph}"

        --- RETRIEVED RULES (reference by rule_id) ---
        {context_block}
        {reflection_block}

        CRITICAL INSTRUCTIONS:
        1. Apply rules based on the guideline text, not just the rule name
           - Read the full guideline carefully to understand when the rule applies
           - Look for examples and context in the guideline text
           - If a rule says "West Coast" should be capitalized, apply it ONLY to "West Coast", not "B.C. coast" or similar terms
        
        2. Do NOT over-generalize or extrapolate beyond what the rule explicitly states
           - Rules about specific terms apply only to those exact terms
           - Do NOT infer additional cases unless the guideline explicitly mentions them
        
        3. Identify violations based ONLY on the retrieved rules above
           - Do NOT invent or reference rules that aren't in the retrieved list
        
        4. Avoid reporting the same violation twice (check for duplicates)
        
        5. Set "confident": true if your analysis is complete and accurate
           - Set "confident": false and "needs_more_context": true if you need additional rules
        
        6. If needs_more_context=true, provide specific queries in "additional_queries"
           - Make queries SPECIFIC: use exact terms from the text (e.g., "quotation marks", "prime minister capitalization")
           - Do NOT prefix with "CBC style guide for" - just the specific topic
           - Examples: "em dash usage", "premier title capitalization", "acronym punctuation"

        JSON SCHEMA:
        {{
            "violations": [
                {{
                    "text": "Exact substring from the user paragraph that violates the rule",
                    "explanation": "Why the snippet breaks the rule",
                    "suggested_fix": "How to fix it",
                    "rule_id": "RETRIEVED_RULE_#X (use the ID from the list above)",
                    "rule_name": "Human-readable rule title",
                    "source_url": "Rule URL if known, otherwise empty string"
                }}
            ],
            "confident": true,
            "needs_more_context": false,
            "additional_queries": []
        }}

        Return ONLY raw JSON. No markdown.
        """

        return prompt

    def _strip_json_code_fence(self, text):
        if not text:
            return text
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.replace("```json", "", 1)
        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```", "", 1)
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    def _format_violations(self, raw_results, paragraph, contexts):
        context_lookup = {entry['id']: entry for entry in contexts}
        formatted = []

        for violation in raw_results:
            text_span = (violation.get('text') or violation.get('sentence') or '').strip()
            if not text_span:
                continue

            start_idx, end_idx = self._find_span_indices(paragraph, text_span)

            rule_id = violation.get('rule_id', '')
            rule_name = violation.get('rule_name')
            source_url = violation.get('source_url', '')

            if rule_id in context_lookup:
                meta = context_lookup[rule_id]
                rule_name = rule_name or meta.get('term')
                source_url = source_url or meta.get('url', '')

            formatted.append({
                "sentence": text_span,
                "text": text_span,
                "paragraph": paragraph,
                "violation": violation.get('explanation') or violation.get('violation') or '',
                "correction": violation.get('suggested_fix') or violation.get('correction') or '',
                "source_url": source_url,
                "rule_name": rule_name or rule_id,
                "rule_id": rule_id,
                "start_index": start_idx,
                "end_index": end_idx
            })

        return formatted

    def _deduplicate_violations(self, violations):
        """Remove duplicate violations based on text span and location."""
        seen = set()
        deduplicated = []
        
        for v in violations:
            # Create unique key based on normalized text and span indices
            text_normalized = self._normalize_text(v.get('text', ''))
            key = (text_normalized, v.get('start_index'), v.get('end_index'), v.get('paragraph', ''))
            
            if key not in seen and text_normalized:  # Skip empty violations
                seen.add(key)
                deduplicated.append(v)
        
        return deduplicated
    
    def _normalize_text(self, text):
        """Normalize text for comparison."""
        if not text:
            return ""
        return "".join(c.lower() for c in text if c.isalnum() or c.isspace()).strip()
    
    def _find_span_indices(self, paragraph, snippet):
        if not snippet:
            return None, None

        idx = paragraph.find(snippet)
        if idx == -1:
            lower_idx = paragraph.lower().find(snippet.lower())
            if lower_idx == -1:
                return None, None
            return lower_idx, lower_idx + len(snippet)

        return idx, idx + len(snippet)

if __name__ == "__main__":
    auditor = StyleAuditor()
    test_text = "The government needs to do more for Aboriginal housing."
    print(json.dumps(auditor.check_text(test_text), indent=2))