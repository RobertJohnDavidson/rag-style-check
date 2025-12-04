"""
Configurable Style Auditor - Injectable tuning parameters for test execution.
This is a modified version of auditor.py that accepts runtime parameters.
"""

import os
import json
import asyncio
from dotenv import load_dotenv
from spacy.lang.en import English 

from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine
from llama_index.vector_stores.postgres import PGVectorStore
from google.genai.types import EmbedContentConfig

from llama_index.core import VectorStoreIndex, Settings, QueryBundle
from llama_index.core.retrievers import VectorIndexRetriever

from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI

try:
    from src.core.reranker import VertexAIRerank
except ImportError:
    print("⚠️ VertexAIRerank class not found. Re-ranking will be skipped.")
    VertexAIRerank = None

load_dotenv()

# --- FIXED CONFIGURATION (From Environment) ---
PROJECT_ID = os.getenv("PROJECT_NAME")
REGION = os.getenv("REGION", "us-central1")
INSTANCE_NAME = os.getenv("INSTANCE_NAME")
DB_USER = os.getenv("DB_USER")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_REGION = os.getenv("DB_REGION", REGION)
TABLE_NAME = "rag_vectors"

# Model Config - EMBEDDING PARAMETERS ARE FIXED
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
EMBED_DIM = 768  # Must match DB schema
PROJECT_NAME = os.getenv("PROJECT_NAME")

if not PROJECT_NAME:
    raise ValueError("PROJECT_NAME not found in environment variables.")

# --- DATABASE CONNECTION LOGIC ---
_sync_connector = None

def get_ip_type():
    if os.getenv("K_SERVICE"):
        return IPTypes.PRIVATE
    return IPTypes.PUBLIC

def get_sync_conn():
    # Sync connections can use a cached connector since they don't use event loops
    global _sync_connector
    if _sync_connector is None:
        _sync_connector = Connector()
    return _sync_connector.connect(
        f"{PROJECT_ID}:{DB_REGION}:{INSTANCE_NAME}",
        "pg8000",
        user=DB_USER,
        db=DB_NAME,
        enable_iam_auth=True,
        ip_type=get_ip_type()
    )

async def get_async_conn():
    # Create a new Connector with explicit loop to avoid event loop conflicts
    import asyncio
    loop = asyncio.get_running_loop()
    connector = Connector(loop=loop)
    conn = await connector.connect_async(
        f"{PROJECT_ID}:{REGION}:{INSTANCE_NAME}",
        "asyncpg",
        user=DB_USER,
        db=DB_NAME,
        enable_iam_auth=True,
        ip_type=get_ip_type()
    )
    return conn


class ConfigurableStyleAuditor:
    """
    Style auditor with configurable tuning parameters.
    Embedding model and dimensions are fixed (must match DB schema).
    """
    
    def __init__(
        self,
        model_name: str = "models/gemini-1.5-flash",
        temperature: float = 0.1,
        initial_retrieval_count: int = 75,
        final_top_k: int = 25,
        rerank_score_threshold: float = 0.10,
        aggregated_rule_limit: int = 40,
        min_sentence_length: int = 5,
        max_agent_iterations: int = 3,
        confidence_threshold: float = 10.0
    ):
        """
        Initialize configurable auditor with custom parameters.
        
        Args:
            model_name: LLM model to use (e.g., "models/gemini-1.5-flash", "models/gemini-2.0-flash-thinking-exp")
            temperature: LLM temperature (0.0-2.0)
            initial_retrieval_count: Number of rules to retrieve initially (10-200)
            final_top_k: Number of top rules after reranking (5-100)
            rerank_score_threshold: Minimum rerank score to include a rule (0.0-1.0)
            aggregated_rule_limit: Maximum number of unique rules to use (10-100)
            min_sentence_length: Minimum sentence length in words (1-50)
            max_agent_iterations: Maximum agent thinking cycles (1-10)
            confidence_threshold: Minimum confidence score for violations (0.0-100.0)
        """
        # Validate parameters
        self._validate_parameters(
            model_name, temperature, initial_retrieval_count, final_top_k,
            rerank_score_threshold, aggregated_rule_limit, min_sentence_length,
            max_agent_iterations, confidence_threshold
        )
        
        # Store configurable parameters
        self.model_name = model_name
        self.temperature = temperature
        self.initial_retrieval_count = initial_retrieval_count
        self.final_top_k = final_top_k
        self.rerank_score_threshold = rerank_score_threshold
        self.aggregated_rule_limit = aggregated_rule_limit
        self.min_sentence_length = min_sentence_length
        self.max_agent_iterations = max_agent_iterations
        self.confidence_threshold = confidence_threshold
        
        print(f"🔧 Configurable Auditor initialized with:")
        print(f"   Model: {model_name}")
        print(f"   Temperature: {temperature}")
        print(f"   Retrieval: {initial_retrieval_count} → Rerank: {final_top_k}")
        print(f"   Rerank threshold: {rerank_score_threshold}")
        print(f"   Rule limit: {aggregated_rule_limit}")
        print(f"   Min sentence length: {min_sentence_length}")
        print(f"   Max iterations: {max_agent_iterations}")
        print(f"   Confidence threshold: {confidence_threshold}")
        
        # Configure embeddings (FIXED - from environment)
        Settings.embed_model = GoogleGenAIEmbedding(
            model_name=EMBEDDING_MODEL,
            vertexai_config={
                "project": PROJECT_NAME,
                "location": REGION
            },
            embedding_config=EmbedContentConfig(
                output_dimensionality=EMBED_DIM
            )
        )
        
        # Configure LLM (CONFIGURABLE)
        Settings.llm = GoogleGenAI(
            model=model_name,
            vertexai_config={
                "project": PROJECT_NAME,
                "location": REGION
            },
            temperature=temperature
        )
        
        # Load NLP
        self.nlp = English()
        self.nlp.add_pipe("sentencizer")
        
        # Initialize database connection
        print(f"🔌 Connecting to Cloud SQL Instance: {INSTANCE_NAME}...")
        
        self.engine = sqlalchemy.create_engine(
            "postgresql+pg8000://",
            creator=get_sync_conn,
        )

        self.async_engine = create_async_engine(
            "postgresql+asyncpg://",
            async_creator=get_async_conn,
        )

        self.vector_store = PGVectorStore(
            engine=self.engine,
            async_engine=self.async_engine,
            table_name=TABLE_NAME,
            embed_dim=EMBED_DIM,
            hybrid_search=True,
            text_search_config="english",
            hnsw_kwargs={
                "hnsw_m": 24,
                "hnsw_ef_construction": 512,
                "hnsw_dist_method": "vector_cosine_ops",
            },
        )

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            embed_model=Settings.embed_model
        )
        
        self.retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=self.initial_retrieval_count,
            vector_store_query_mode="hybrid",
            sparse_top_k=10
        )

        if VertexAIRerank:
            self.reranker = VertexAIRerank(
                project_id=PROJECT_NAME,
                location_id=REGION,
                ranking_config="default_ranking_config",
                top_n=self.final_top_k
            )
        else:
            self.reranker = None
            
        print("✅ Connected to Cloud SQL Vector Store.")
    
    def _validate_parameters(
        self, model_name, temperature, initial_retrieval_count, final_top_k,
        rerank_score_threshold, aggregated_rule_limit, min_sentence_length,
        max_agent_iterations, confidence_threshold
    ):
        """Validate parameter ranges"""
        if not isinstance(model_name, str) or not model_name:
            raise ValueError("model_name must be a non-empty string")
        
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        
        if not 10 <= initial_retrieval_count <= 200:
            raise ValueError("initial_retrieval_count must be between 10 and 200")
        
        if not 5 <= final_top_k <= 100:
            raise ValueError("final_top_k must be between 5 and 100")
        
        if not 0.0 <= rerank_score_threshold <= 1.0:
            raise ValueError("rerank_score_threshold must be between 0.0 and 1.0")
        
        if not 10 <= aggregated_rule_limit <= 100:
            raise ValueError("aggregated_rule_limit must be between 10 and 100")
        
        if not 1 <= min_sentence_length <= 50:
            raise ValueError("min_sentence_length must be between 1 and 50")
        
        if not 1 <= max_agent_iterations <= 10:
            raise ValueError("max_agent_iterations must be between 1 and 10")
        
        if not 0.0 <= confidence_threshold <= 100.0:
            raise ValueError("confidence_threshold must be between 0.0 and 100.0")

    async def check_text_async(self, text):
        """Async wrapper for check_text to work with FastAPI."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.check_text, text)

    def check_text(self, text):
        """Main entry point for auditing text"""
        paragraphs = self._split_paragraphs(text)
        all_violations = []

        print(f"\n🔍 Auditing {len(paragraphs)} paragraph(s)...")

        for paragraph in paragraphs:
            paragraph_violations = self._audit_paragraph_agentic(paragraph)
            if paragraph_violations:
                all_violations.extend(paragraph_violations)
        
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
        doc = self.nlp(paragraph)
        sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > self.min_sentence_length]
        
        contexts = self._collect_rule_contexts(sentences)
        violations = []
        
        print(f"\n{'='*60}")
        print(f"🤖 AGENTIC AUDIT - Starting analysis")
        print(f"{'='*60}")
        
        for iteration in range(self.max_agent_iterations):
            print(f"\n--- Iteration {iteration + 1}/{self.max_agent_iterations} ---")
            
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
            
            if isinstance(result, dict):
                new_violations = result.get("violations", [])
                needs_more_context = result.get("needs_more_context", False)
                is_confident = result.get("confident", True)
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
            
            if new_violations:
                violations = self._format_violations(new_violations, paragraph, contexts)
                print(f"   - Formatted {len(violations)} violations")
            
            if is_confident and not needs_more_context:
                if len(contexts) < 10:
                    print(f"⚠️  Agent claims confidence but only {len(contexts)} rules available. Requesting more context.")
                    is_confident = False
                    needs_more_context = True
                    import re
                    keywords = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', paragraph)
                    additional_queries = list(set(keywords))[:3]
                else:
                    print(f"\n✅ Agent is confident. Stopping at iteration {iteration + 1}.")
                    break
            
            if iteration == self.max_agent_iterations - 1:
                print(f"\n⏱️  Max iterations reached. Stopping.")
                break
            
            if additional_queries:
                print(f"\n🔍 Agent requesting more context...")
                print(f"   Queries: {additional_queries}")
                additional_contexts = self._collect_additional_contexts(additional_queries)
                print(f"   - Retrieved {len(additional_contexts)} additional rules:")
                for ctx in additional_contexts[:3]:
                    print(f"     • {ctx['term']} (score: {ctx['score']:.3f})")
                contexts.extend(additional_contexts)
        
        deduplicated = self._deduplicate_violations(violations)
        print(f"\n🔧 Deduplication: {len(violations)} → {len(deduplicated)} violations")
        print(f"{'='*60}\n")
        
        return deduplicated

    def _collect_additional_contexts(self, queries):
        """Retrieve additional rule contexts based on agent's questions."""
        aggregated = {}
        
        for query in queries:
            expanded_queries = [query]
            
            if "quotation" in query.lower():
                expanded_queries.extend(["quotes", "quotation marks", "quote marks"])
            if "dash" in query.lower():
                expanded_queries.extend(["em dash", "en dash", "hyphen"])
            if "capitalization" in query.lower() or "capital" in query.lower():
                expanded_queries.extend(["uppercase", "lowercase", "title case"])
            
            for q in expanded_queries:
                nodes = self.retriever.retrieve(q)
                
                if nodes and self.reranker:
                    try:
                        query_bundle = QueryBundle(query_str=query)
                        nodes = self.reranker.postprocess_nodes(nodes=nodes, query_bundle=query_bundle)
                    except Exception:
                        nodes = nodes[:self.final_top_k]
                else:
                    nodes = nodes[:self.final_top_k] if nodes else []
                
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
        limited = sorted_rules[:10]
        
        for idx, rule in enumerate(limited, start=100):
            rule["id"] = f"ADDITIONAL_RULE_#{idx}"
        
        return limited
    
    def _collect_rule_contexts(self, sentences):
        aggregated = {}

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
        
        if len(aggregated) < 10:
            import re
            paragraph_text = " ".join(sentences)
            keywords = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', paragraph_text)
            keywords = list(set(keywords))
            
            for keyword in keywords:
                nodes = self._retrieve_nodes(keyword)
                for node in nodes:
                    term = node.metadata.get('term', 'Untitled Rule')
                    key = (term, node.metadata.get('url', ''))
                    score = getattr(node, 'score', 0) * 0.8
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
        limited = sorted_rules[:self.aggregated_rule_limit]

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
                nodes = nodes[:self.final_top_k]
        elif nodes:
            nodes = nodes[:self.final_top_k]

        return self._filter_nodes(nodes)

    def _filter_nodes(self, nodes):
        if not nodes:
            return []
        return [node for node in nodes if getattr(node, 'score', 0) >= self.rerank_score_threshold]

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
        
        reflection_block = ""
        if iteration > 0 and current_violations:
            violations_summary = "\n".join([f"- {v.get('text', 'N/A')}: {v.get('violation', 'N/A')}" for v in current_violations[:5]])
            reflection_block = f"""
        --- PREVIOUS ANALYSIS (Iteration {iteration}) ---
        You previously found these violations:
        {violations_summary}
        
        Review your previous findings. Are there duplicates? Did you miss anything? Do you need more context?
        """
        
        prompt = f"""
        You are an expert Copy Editor for CBC News with agentic capabilities.
        Review the entire paragraph below and flag every rule violation you can find.

        USER PARAGRAPH:
        "{paragraph}"

        --- RETRIEVED RULES (reference by rule_id) ---
        {context_block}
        {reflection_block}

        CRITICAL INSTRUCTIONS:
        1. Apply rules LITERALLY based on the guideline text, not rule interpretations
           - Read the full guideline text carefully
           - Only flag violations that explicitly match the guideline
           - If the text already matches the guideline requirement, DO NOT flag it
           
           EXAMPLE: If rule says "Use 'Alberta Government' (capitalized)" and text says "Alberta Government", this is CORRECT - do NOT flag it
           EXAMPLE: If rule says "Use 'oilsands'" and text says "tarsands", this IS a violation
           ABBREVIATION RULES: Only flag abbreviations if the guideline says they are WRONG or FORBIDDEN
           - If rule says "can be abbreviated as X", just seeing the full form is NOT a violation
           - Only flag if abbreviation is required but not used, OR if wrong abbreviation is used
        
        2. Do NOT over-generalize or extrapolate
           - Rules about specific terms apply only to those exact terms
           - Do NOT invent additional cases
           - Never assume an abbreviation rule applies to every instance of a word
        
        3. Verify each violation:
           - Is the text in the paragraph exactly what the guideline says to change?
           - Would fixing it actually improve compliance with the rule?
           - If the text is already correct per the guideline, skip it
        
        4. Avoid reporting duplicates (same violation at different locations)
        
        5. Set "confident": true only if:
           - You have reviewed all retrieved rules thoroughly
           - You are certain about each violation
           - You would not benefit from additional context
           Set "confident": false if unsure or if retrieved rules seem incomplete
        
        6. If needs_more_context=true, provide specific queries
           - Use exact terms from the text (e.g., "quotation marks", "prime minister")
           - Make queries SPECIFIC and SHORT
           - Examples: "em dash usage", "premier capitalization", "acronym punctuation"

        JSON SCHEMA:
        {{
            "violations": [
                {{
                    "text": "Exact substring from the user paragraph that violates the rule",
                    "explanation": "Why the snippet breaks the rule (reference the guideline)",
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
            text_normalized = self._normalize_text(v.get('text', ''))
            key = (text_normalized, v.get('start_index'), v.get('end_index'), v.get('paragraph', ''))
            
            if key not in seen and text_normalized:
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
