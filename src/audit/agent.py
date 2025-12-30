import logging
import time
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
        overall_start = time.perf_counter()
        timings = []
        
        # 1. Retrieval
        logger.info("🔍 Agent: Retrieval...")
        start_r = time.perf_counter()
        retrieved_contexts, retrieval_details = await self.retriever.retrieve(paragraph)
        duration_r = time.perf_counter() - start_r
        timings.append(("Retrieval", duration_r))
        
        steps.append({
            "type": "retrieval",
            "duration_seconds": duration_r,
            "details": retrieval_details
        })
        
        # 2. Reranking
        logger.info("🔍 Agent: Reranking...")
        start_rk = time.perf_counter()
        reranked_contexts, rerank_details = await self.reranker.rerank(retrieved_contexts, paragraph)
        duration_rk = time.perf_counter() - start_rk
        timings.append(("Reranking", duration_rk))
        
        steps.append({
            "type": "reranking",
            "duration_seconds": duration_rk,
            "details": rerank_details
        })
        
        current_contexts = reranked_contexts if reranked_contexts else retrieved_contexts
        
        # Deduplicate contexts by ID
        unique_contexts = {c['id']: c for c in current_contexts}.values()
        contexts = list(unique_contexts)[:self.config.aggregated_rule_limit]
        
        violations = []
        
        # 3. Agent Audit Loop
        for iteration in range(self.config.max_agent_iterations):
            logger.info(f"--- Iteration {iteration + 1}/{self.config.max_agent_iterations} ---")
            start_it = time.perf_counter()
            
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
            
            duration_it = time.perf_counter() - start_it
            timings.append((f"Iteration {iteration + 1}", duration_it))
            
            if not response_obj:
                break
                
            # Log Step
            steps.append({
                "type": "iteration",
                "iteration": iteration,
                "duration_seconds": duration_it,
                "prompt": prompt,
                "response": response_obj.model_dump()
            })
            
            # Collect Violations
            new_violations = response_obj.violations
            formatted = format_violations(new_violations, paragraph, contexts)
            if formatted:
                violations.extend(formatted)
                
            # Additional Context (only if we have more iterations to use it)
            if response_obj.additional_queries and (iteration + 1 < self.config.max_agent_iterations):
                 logger.info(f"🔍 Requesting more context: {response_obj.additional_queries}")
                 start_add = time.perf_counter()
                 new_ctx = await self._fetch_additional_context(response_obj.additional_queries)
                 duration_add = time.perf_counter() - start_add
                 timings.append((f"AddContext It{iteration+1}", duration_add))
                 
                 steps.append({
                     "type": "additional_retrieval",
                     "duration_seconds": duration_add,
                     "queries": response_obj.additional_queries,
                     "results": new_ctx
                 })
                 contexts.extend(new_ctx)
                 # Re-deduplicate
                 unique_contexts = {c['id']: c for c in contexts}.values()
                 contexts = list(unique_contexts)[:self.config.aggregated_rule_limit]
            
            # Stop Conditions
            if response_obj.confident and not response_obj.needs_more_context:
                break

        total_duration = time.perf_counter() - overall_start
        self._print_timing_table(timings, total_duration)
        
        return deduplicate_violations(violations), steps

    def _print_timing_table(self, timings, total):
        print("\n" + "="*40)
        print(f"{'Audit Step':<25} | {'Duration (s)':>10}")
        print("-" * 40)
        for step, duration in timings:
            print(f"{step:<25} | {duration:>10.3f}")
        print("-" * 40)
        print(f"{'Total Time':<25} | {total:>10.3f}")
        print("="*40 + "\n")

    async def _fetch_additional_context(self, queries: List[str]) -> List[Dict]:
        """Fetch more rules for specific queries."""
        all_results = []
        for q in queries:
             # Just use base retrieval for speed on additional queries
             r_ctx, _ = await self.retriever.retrieve(q)
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
            violation_texts = [v.get('text', '') for v in existing_violations[:5]]
            reflection_block = f"PREVIOUS FINDINGS ({len(existing_violations)}): Already flagged: {', '.join(violation_texts)}. Do NOT re-flag these."
        
        system_prompt = PROMPT_AUDIT_SYSTEM
        if self.config.include_thinking:
            system_prompt += "\nExplain your thinking process clearly in the 'thinking' field before listing violations."

        return system_prompt.format(current_date=current_date) + "\n" + PROMPT_AUDIT_USER_TEMPLATE.format(
            paragraph=paragraph,
            context_block=context_block,
            reflection_block=reflection_block
        )
