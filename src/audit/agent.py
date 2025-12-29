import logging
from datetime import datetime
from typing import List, Dict, Tuple
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core import PromptTemplate

from src.audit.models import AuditorConfig, AuditResult, Violation
from src.audit.retrievers import BaseRetrieverModule
from src.audit.rerankers import BaseRerankerModule
from src.audit.prompts import PROMPT_AUDIT_SYSTEM, PROMPT_AUDIT_USER_TEMPLATE
from src.utils import deduplicate_violations
from src.audit.helpers import format_violations

logger = logging.getLogger(__name__)

class StyleAgent:
    """
    Performs the audit on a single paragraph.
    Follows strictly the linear flow:
    Retrieve -> Rerank -> Audit Loop (with optional re-retrieval)
    """
    
    def __init__(
        self, 
        config: AuditorConfig, 
        llm: GoogleGenAI,
        retriever: BaseRetrieverModule,
        reranker: BaseRerankerModule
    ):
        self.config = config
        self.llm = llm
        self.retriever = retriever
        self.reranker = reranker

    async def audit_paragraph(self, paragraph: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Execute the audit process for one paragraph.
        Returns:
            - List of Violated Dicts
            - List of Step Dicts (for logging)
        """
        steps = []
        
        # 1. Retrieval
        logger.info("🔍 Agent: Simple Retrieval...")
        retrieved_contexts, retrieval_details = await self.retriever.retrieve(paragraph)
        steps.append({
            "type": "retrieval",
            "details": retrieval_details
        })
        
        # 2. Reranking
        logger.info("🔍 Agent: Reranking...")
        reranked_contexts, rerank_details = await self.reranker.rerank(retrieved_contexts, paragraph)
        steps.append({
            "type": "reranking",
            "details": rerank_details
        })
        
        # Use reranked contexts; fallback to retrieved if empty? 
        # Usually reranker returns subset.
        current_contexts = reranked_contexts if reranked_contexts else retrieved_contexts
        
        # Deduplicate contexts by ID
        unique_contexts = {c['id']: c for c in current_contexts}.values()
        contexts = list(unique_contexts)[:self.config.aggregated_rule_limit]
        
        violations = []
        
        # 3. Agent Audit Loop
        for iteration in range(self.config.max_agent_iterations):
            logger.info(f"--- Iteration {iteration + 1}/{self.config.max_agent_iterations} ---")
            
            # Build Prompt
            prompt = self._build_prompt(paragraph, contexts, violations, iteration)
            
            # Predict
            try:
                tmpl = PromptTemplate(prompt)
                response_obj = await self.llm.astructured_predict(AuditResult, tmpl)
            except Exception as e:
                logger.error(f"Agent iteration failed: {e}")
                steps.append({
                    "type": "iteration_error",
                    "iteration": iteration,
                    "error": str(e)
                })
                break
            
            if not response_obj:
                break
                
            # Log Step
            steps.append({
                "type": "iteration",
                "iteration": iteration,
                "prompt": prompt,
                "response": response_obj.model_dump()
            })
            
            # Collect Violations
            new_violations = response_obj.violations
            formatted = format_violations(new_violations, paragraph, contexts)
            if formatted:
                violations.extend(formatted)
                
            # Stop Conditions
            if response_obj.confident and not response_obj.needs_more_context:
                break
                
            # Additional Context
            if response_obj.additional_queries:
                 logger.info(f"🔍 Requesting more context: {response_obj.additional_queries}")
                 new_ctx = await self._fetch_additional_context(response_obj.additional_queries)
                 steps.append({
                     "type": "additional_retrieval",
                     "queries": response_obj.additional_queries,
                     "results": new_ctx
                 })
                 contexts.extend(new_ctx)
                 # Re-deduplicate
                 unique_contexts = {c['id']: c for c in contexts}.values()
                 contexts = list(unique_contexts)[:self.config.aggregated_rule_limit]

        return deduplicate_violations(violations), steps

    async def _fetch_additional_context(self, queries: List[str]) -> List[Dict]:
        """Fetch more rules for specific queries."""
        all_results = []
        for q in queries:
             # Just use base retrieval for speed on additional queries, 
             # or reuse the full pipeline? 
             # Let's reuse the full pipeline for consistency.
             r_ctx, _ = await self.retriever.retrieve(q)
             # Optional: Rerank these too? Maybe overkill for specific queries.
             # Let's skip rerank for additional specific queries to trust the vector store match.
             all_results.extend(r_ctx)
        return all_results

    def _build_prompt(self, paragraph, contexts, existing_violations, iteration):
        current_date = datetime.now().strftime("%B %d, %Y")
        
        context_lines = [
            f"{c['id']} | Rule: {c['term']}\nGuideline: {c['text']}" 
            for c in contexts
        ]
        context_block = "\n\n".join(context_lines) if context_lines else "No rules found."
        
        reflection_block = ""
        if iteration > 0 and existing_violations:
             reflection_block = f"PREVIOUS FINDINGS: {len(existing_violations)} violations found so far."

        system_prompt = PROMPT_AUDIT_SYSTEM
        if self.config.include_thinking:
            system_prompt += "\nExplain your thinking process clearly in the 'thinking' field before listing violations."

        return system_prompt.format(current_date=current_date) + "\n" + PROMPT_AUDIT_USER_TEMPLATE.format(
            paragraph=paragraph,
            context_block=context_block,
            reflection_block=reflection_block
        )
