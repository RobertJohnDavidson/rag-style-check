import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

from llama_index.core import VectorStoreIndex, QueryBundle
from llama_index.core.retrievers import BaseRetriever, VectorIndexRetriever, QueryFusionRetriever
from llama_index.core.postprocessor import LLMRerank
from llama_index.core.schema import NodeWithScore
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core import PromptTemplate

# Custom Imports
from src.config import settings
from src.core.prompts import (
    PROMPT_QUERY_GEN,
    PROMPT_CLASSIFY_TAGS,
    PROMPT_AUDIT_SYSTEM,
    PROMPT_AUDIT_USER_TEMPLATE,
    STYLE_CATEGORIES
)
from src.core.utils import (
    find_span_indices,
    deduplicate_violations
)
from llama_index.core import Settings as LlamaSettings

# Optional Reranker
try:
    from src.core.reranker import VertexAIRerank
except ImportError:
    print("⚠️ VertexAIRerank class not found. Re-ranking will be skipped.")
    VertexAIRerank = None

logger = logging.getLogger(__name__)

# --- PYDANTIC MODELS FOR STRUCTURED OUTPUT ---

class Violation(BaseModel):
    text: str = Field(description="Exact substring from the paragraph that violates the rule")
    explanation: str = Field(description="Why this violates the rule")
    suggested_fix: str = Field(description="Correction or 'omit'")
    rule_id: str = Field(description="ID of the violated rule (e.g. RULE_123)")
    rule_name: Optional[str] = Field(description="Name of the rule", default=None)
    url: Optional[str] = Field(description="URL of the rule", default=None)

class AuditResult(BaseModel):
    thinking: Optional[str] = Field(description="Chain of thought or reasoning process", default=None)
    violations: List[Violation] = Field(default_factory=list)
    confident: bool = Field(description="True if the agent is certain about findings")
    needs_more_context: bool = Field(description="True if more rules are needed")
    additional_queries: List[str] = Field(default_factory=list, description="Queries to find missing rules")

class AuditorConfig(BaseModel):
    """Configuration for StyleAuditor."""
    model_name: str = settings.DEFAULT_MODEL
    temperature: float = 0.0
    initial_retrieval_count: int = settings.DEFAULT_INITIAL_RETRIEVAL_COUNT
    final_top_k: int = settings.DEFAULT_FINAL_TOP_K
    rerank_score_threshold: float = settings.DEFAULT_RERANK_SCORE_THRESHOLD
    aggregated_rule_limit: int = settings.DEFAULT_AGGREGATED_RULE_LIMIT
    max_agent_iterations: int = settings.DEFAULT_MAX_AGENT_ITERATIONS
    confidence_threshold: float = settings.DEFAULT_CONFIDENCE_THRESHOLD
    max_concurrent_requests: int = settings.DEFAULT_MAX_CONCURRENT_REQUESTS
    use_query_fusion: bool = True
    use_llm_rerank: bool = False
    include_thinking: bool = False

class StyleAuditor:
    """
    Unified Style Auditor.
    
    Refactored to support:
    - Async Execution
    - Dependency Injection (pass LLM/Retriever in)
    - Structured Outputs (Pydantic)
    """
    
    def __init__(
        self,
        retriever: Optional[BaseRetriever] = None,
        index: Optional[VectorStoreIndex] = None,
        config: Optional[AuditorConfig] = None,
    ):
        """
        Initialize the Auditor.
        LLM instances are created on-demand per run based on config.
        """
        self.config = config or AuditorConfig()
        self.index = index
        self.external_retriever = retriever

        # Fixed Rerank LLM (always lite, stable for reranking)
        self.rerank_llm = GoogleGenAI(
            model=settings.RERANK_MODEL,
            temperature=0.0,
            vertexai_config={
                "project": settings.PROJECT_ID,
                "location": settings.LLM_REGION
            }
        )
        #Set this here so the generate text api has access to it
        LlamaSettings.llm = self.rerank_llm  # For any internal use in LlamaIndex
        logger.info(f"🔧 Auditor initialized with Base Model: {self.config.model_name}")
        logger.info(f"🔧 Rerank Model: {settings.RERANK_MODEL}")

    def _get_llm_for_run(self, config: AuditorConfig) -> GoogleGenAI:
        """
        Create LLM instance configured entirely by the run config.
        No caching—always create fresh to ensure config isolation.
        """
        generation_config = {}
        
        if config.include_thinking:
            # Gemini 2.x models use thinking_budget, 3.x+ use thinking_level
            if "2." in config.model_name:
                generation_config["thinking_config"] = {
                    "includeThoughts": True,
                    "thinking_budget": 2000  # Token budget for thinking
                }
            else:  # Gemini 3.x or higher
                generation_config["thinking_config"] = {
                    "includeThoughts": True,
                    "thinking_level": "medium"  # Options: low, medium, high
                }
        
        return GoogleGenAI(
            model=config.model_name,
            temperature=config.temperature,
            vertexai_config={
                "project": settings.PROJECT_ID,
                "location": settings.LLM_REGION,
            }
        )

    def _get_retriever_for_run(self, config: AuditorConfig) -> BaseRetriever:
        """Get retriever configured for the run. Always uses rerank_llm for query fusion."""
        # 1. Base Retriever
        if self.external_retriever:
            base_retriever = self.external_retriever
            if hasattr(base_retriever, "similarity_top_k"):
                base_retriever.similarity_top_k = config.initial_retrieval_count
        elif self.index:
            base_retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=config.initial_retrieval_count,
                vector_store_query_mode="hybrid",
                sparse_top_k=10
            )
        else:
            raise ValueError("No retriever or index available.")

        # 2. Query Fusion (Advanced) - Always use rerank_llm for step efficiency
        if config.use_query_fusion:
            return QueryFusionRetriever(
                [base_retriever],
                llm=self.rerank_llm,
                similarity_top_k=config.initial_retrieval_count,
                num_queries=3,
                mode="reciprocal_rerank",
                use_async=True,
                verbose=True,
                query_gen_prompt=PROMPT_QUERY_GEN
            )
        return base_retriever

    def _get_rerankers_for_run(self, config: AuditorConfig):
        """Get rerankers configured for the run. Always uses rerank_llm for stability."""
        llm_reranker = None
        if config.use_llm_rerank:
            llm_reranker = LLMRerank(
                choice_batch_size=10,
                top_n=config.final_top_k,
                llm=self.rerank_llm
            )

        vertex_reranker = None
        if VertexAIRerank:
            vertex_reranker = VertexAIRerank(
                project_id=settings.PROJECT_ID,
                location_id=settings.LLM_REGION,
                ranking_config="default_ranking_config",
                top_n=config.final_top_k
            )
            
        return llm_reranker, vertex_reranker

    async def check_text(self, text: str, tuning_params: Optional[Any] = None) -> tuple[List[Dict], Dict]:
        """
        Main Async Entry Point.
        Returns a tuple of (violations, log_data).
        """
        # Resolve config for this run
        run_config = self.config
        if tuning_params:
            if hasattr(tuning_params, 'model_dump'):
                overrides = tuning_params.model_dump(exclude_unset=True)
            else:
                overrides = tuning_params
            run_config = self.config.model_copy(update=overrides)

        # Resolve run-scoped tools
        llm = self._get_llm_for_run(run_config)
        retriever = self._get_retriever_for_run(run_config)
        llm_reranker, vertex_reranker = self._get_rerankers_for_run(run_config)

        if not text.strip():
            return [], {}

        paragraphs = self._split_paragraphs(text)
        all_violations = []
        interim_steps = []

        logger.info(f"🔍 Auditing {len(paragraphs)} paragraph(s)...")

        # Process paragraphs concurrently with semaphore
        semaphore = asyncio.Semaphore(run_config.max_concurrent_requests)
        
        async def process_paragraph_with_limit(i: int, paragraph: str):
            async with semaphore:
                print(f"Processing paragraph {i+1}/{len(paragraphs)}")
                return i, paragraph, await self._audit_paragraph_agentic(
                    paragraph, 
                    run_config,
                    llm=llm,
                    retriever=retriever,
                    llm_reranker=llm_reranker,
                    vertex_reranker=vertex_reranker
                )
        
        tasks = [
            process_paragraph_with_limit(i, paragraph)
            for i, paragraph in enumerate(paragraphs)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle errors
        successful_count = 0
        for result in results:
            if isinstance(result, Exception):
                # Log error but continue with other paragraphs
                logger.error(f"Paragraph processing failed: {result}")
                interim_steps.append({
                    "type": "paragraph_error",
                    "error": str(result)
                })
            else:
                i, paragraph, (paragraph_violations, paragraph_steps) = result
                successful_count += 1
                if paragraph_violations:
                    all_violations.extend(paragraph_violations)
                interim_steps.append({
                    "paragraph_index": i,
                    "text": paragraph,
                    "steps": paragraph_steps
                })
        
        # Raise exception if all paragraphs failed
        if successful_count == 0:
            raise RuntimeError(f"All {len(paragraphs)} paragraph(s) failed to process")
        
        final_violations = deduplicate_violations(all_violations)
        
        # Categorize parameters
        llm_params = {
            "temperature": run_config.temperature,
            "max_agent_iterations": run_config.max_agent_iterations,
            "confidence_threshold": run_config.confidence_threshold,
            "include_thinking": run_config.include_thinking
        }
        rag_params = {
            "initial_retrieval_count": run_config.initial_retrieval_count,
            "final_top_k": run_config.final_top_k,
            "rerank_score_threshold": run_config.rerank_score_threshold,
            "aggregated_rule_limit": run_config.aggregated_rule_limit,
            "use_query_fusion": run_config.use_query_fusion,
            "use_llm_rerank": run_config.use_llm_rerank,
        }

        log_data = {
            "model_used": run_config.model_name,
            "llm_parameters": llm_params,
            "rag_parameters": rag_params,
            "interim_steps": interim_steps,
            "final_output": final_violations
        }
        
        return final_violations, log_data

    def _split_paragraphs(self, text: str) -> List[str]:
        if not text:
            return []
        chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
        return chunks if chunks else [text.strip()]

    async def _audit_paragraph_agentic(
        self, 
        paragraph: str, 
        config: AuditorConfig,
        llm: GoogleGenAI,
        retriever: BaseRetriever,
        llm_reranker: Optional[LLMRerank] = None,
        vertex_reranker: Optional[Any] = None
    ) -> tuple[List[Dict], List[Dict]]:
        """
        Agentic audit loop with async execution and structured output.
        Returns (violations, steps).
        """
        steps = []

        # 1. Advanced Retrieval
        logger.info("🔍 Retrieving rules...")
        contexts, retrieval_details = await self._retrieve_advanced_with_details(
            paragraph, 
            config,
            retriever=retriever,
            llm_reranker=llm_reranker,
            vertex_reranker=vertex_reranker
        )
        steps.append({
            "type": "retrieval",
            "details": retrieval_details
        })
        
        # Deduplicate contexts
        unique_contexts = {c['id']: c for c in contexts}.values()
        contexts = list(unique_contexts)[:config.aggregated_rule_limit]
        
        violations = []
        
        # 2. Agent Loop
        for iteration in range(config.max_agent_iterations):
            logger.info(f"--- Iteration {iteration + 1}/{config.max_agent_iterations} ---")
            
            # Build Prompt
            prompt = self._build_prompt(paragraph, contexts, violations, iteration, config)
            
            # Call LLM with Structured Output
            try:
                tmpl = PromptTemplate(prompt)
                response_obj = await llm.astructured_predict(AuditResult, tmpl)
            except Exception as e:
                logger.error(f"Structured predict failed: {e}")
                steps.append({
                    "type": "iteration_error",
                    "iteration": iteration,
                    "error": str(e)
                })
                break

            if not response_obj:
                break
            
            # Capture Iteration
            steps.append({
                "type": "iteration",
                "iteration": iteration,
                "prompt": prompt,
                "response": response_obj.model_dump()
            })
                
            # Process Result
            new_violations = response_obj.violations
            
            # Format and Extend
            formatted_violations = self._format_violations(new_violations, paragraph, contexts)
            if formatted_violations:
                violations.extend(formatted_violations)
            
            # Check Confidence
            if response_obj.confident and not response_obj.needs_more_context:
                logger.info("✅ Agent is confident. Stopping.")
                break
            
            # Handle More Context
            if response_obj.additional_queries:
                logger.info(f"🔍 Requesting more context: {response_obj.additional_queries}")
                new_ctx = await self._collect_additional_contexts(
                    response_obj.additional_queries, 
                    config,
                    retriever=retriever,
                    llm_reranker=llm_reranker,
                    vertex_reranker=vertex_reranker
                )
                steps.append({
                    "type": "additional_retrieval",
                    "queries": response_obj.additional_queries,
                    "results": new_ctx
                })
                contexts.extend(new_ctx)

        return deduplicate_violations(violations), steps

    async def _retrieve_advanced_with_details(
        self, 
        text: str, 
        config: AuditorConfig,
        retriever: BaseRetriever,
        llm_reranker: Optional[LLMRerank] = None,
        vertex_reranker: Optional[Any] = None
    ) -> tuple[List[Dict], Dict]:
        """Async Advanced Retrieval with detailed logging."""
        details = {}
        # 0. Classify Tags (Optional Optimization)
        tags = await self._classify_text_async(text)
        normalized_tags = self._normalize_tags(tags)
        details["tags"] = normalized_tags
        
        tags_str = ", ".join(normalized_tags)
        
        query_text = text
        if normalized_tags:
            logger.info(f"🏷️ Tags: {tags_str}")
            query_text = f"Tags: {tags_str}. Content: {text}"
        
        details["final_query"] = query_text

        # 1. Retrieve
        try:
            nodes = await retriever.aretrieve(query_text)
            details["retrieved_nodes_count"] = len(nodes)
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            details["error"] = str(e)
            return [], details

        # 2. Rerank (LLM)
        if config.use_llm_rerank and llm_reranker and nodes:
             try:
                 query_bundle = QueryBundle(query_str=text) 
                 # Slice to the desired top_n if reranker doesn't handle it
                 if hasattr(llm_reranker, "apostprocess_nodes"):
                    nodes = await llm_reranker.apostprocess_nodes(nodes, query_bundle=query_bundle)
                 else:
                    nodes = llm_reranker.postprocess_nodes(nodes, query_bundle=query_bundle)
                 
                 # Apply final_top_k constraint
                 nodes = nodes[:config.final_top_k]
                 details["llm_reranked_count"] = len(nodes)
             except Exception as e:
                 logger.warning(f"LLM Rerank failed: {e}")
                 details["llm_rerank_error"] = str(e)

        # 3. Rerank (Vertex)
        if vertex_reranker and nodes and not config.use_llm_rerank:
            try:
                query_bundle = QueryBundle(query_str=text)
                nodes = vertex_reranker.postprocess_nodes(nodes, query_bundle=query_bundle)
                # Apply final_top_k constraint
                nodes = nodes[:config.final_top_k]
                details["vertex_reranked_count"] = len(nodes)
            except Exception as e:
                 logger.warning(f"Vertex Rerank failed: {e}")
                 details["vertex_rerank_error"] = str(e)

        results = self._nodes_to_dicts(nodes, source_type="advanced_retrieval")
        details["results"] = results
        return results, details

    async def _classify_text_async(self, text: str) -> List[str]:

        
        prompt_str = PROMPT_CLASSIFY_TAGS.format(
            tags_list_str=", ".join(STYLE_CATEGORIES.split("\n")), 
            text_snippet=text[:1000]
        )
        try:
            resp = await self.rerank_llm.acomplete(prompt_str)
            found = [t.strip() for t in resp.text.split(',')]
            return found
        except Exception:
            return []

    def _normalize_tags(self, tags: List[str]) -> List[str]:
        """Keep only tag titles when constructing query hints."""
        normalized = []
        for tag in tags:
            if not tag:
                continue
            cleaned = tag.replace("*", "").strip()
            base = cleaned.split(":")[0].strip()
            if base:
                normalized.append(base)
        return normalized

    async def _collect_additional_contexts(
        self, 
        queries: List[str], 
        config: AuditorConfig,
        retriever: BaseRetriever,
        llm_reranker: Optional[LLMRerank] = None,
        vertex_reranker: Optional[Any] = None
    ) -> List[Dict]:
        """Collect more rules based on agent queries."""
        # Process queries concurrently with semaphore
        semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        
        async def retrieve_with_limit(q: str):
            async with semaphore:
                return await self._retrieve_advanced_with_details(
                    q, 
                    config,
                    retriever=retriever,
                    llm_reranker=llm_reranker,
                    vertex_reranker=vertex_reranker
                )
        
        tasks = [retrieve_with_limit(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Query retrieval failed: {result}")
            else:
                query_results, _ = result
                all_results.extend(query_results)
        
        return all_results

    def _nodes_to_dicts(self, nodes: List[NodeWithScore], source_type="retrieved") -> List[Dict]:
        out = []
        for node in nodes:
            # Safely access metadata
            meta = node.metadata or {}
            out.append({
                "term": meta.get('term', 'Untitled Rule'),
                "text": meta.get('display_text', node.get_content()),
                "url": meta.get('url', ''),
                "score": node.score or 0.0,
                "source_type": source_type,
                "id": f"RULE_{node.node.node_id[:8]}"
            })
        return out

    def _build_prompt(self, paragraph, contexts, violations, iteration, config: AuditorConfig):
        # Get current date for grounding
        current_date = datetime.now().strftime("%B %d, %Y")
        context_lines = [
            f"{c['id']} | Rule: {c['term']}\nGuideline: {c['text']}" 
            for c in contexts
        ]
        context_block = "\n\n".join(context_lines) if context_lines else "No rules found."
        
        reflection_block = ""
        if iteration > 0 and violations:
             reflection_block = f"PREVIOUS FINDINGS: {len(violations)} violations found so far."

        system_prompt = PROMPT_AUDIT_SYSTEM
        if config.include_thinking:
            system_prompt += "\nExplain your thinking process clearly in the 'thinking' field before listing violations."

        # Return the FORMATTED prompt string
        return system_prompt.format(current_date=current_date) + "\n" + PROMPT_AUDIT_USER_TEMPLATE.format(
            paragraph=paragraph,
            context_block=context_block,
            reflection_block=reflection_block
        )

    def _format_violations(self, pydantic_violations: List[Violation], paragraph: str, contexts: List[Dict]) -> List[Dict]:
        """Convert Pydantic violations to Dicts with indices."""
        formatted = []
        context_map = {c['id']: c for c in contexts}
        
        for v in pydantic_violations:
            start, end = find_span_indices(paragraph, v.text)
            
            # Enrich with source info
            rule_info = context_map.get(v.rule_id, {})
            
            formatted.append({
                "text": v.text,
                "violation": v.explanation,
                "correction": v.suggested_fix,
                "rule_id": v.rule_id,
                "rule_name": v.rule_name or rule_info.get('term'),
                "url": v.url or rule_info.get('url'),
                "paragraph": paragraph,
                "start_index": start,
                "end_index": end
            })
        return formatted
