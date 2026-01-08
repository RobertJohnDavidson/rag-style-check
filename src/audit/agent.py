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
    Performs the style audit. 
    Supports both per-paragraph auditing and full-article auditing with pre-fetched rules.
    """
    
    def __init__(
        self, 
        config: AuditorConfig, 
        llm: GoogleGenAI,
        retriever: BaseRetrieverModule = None,
        reranker: BaseRerankerModule = None
    ):
        self.config = config
        self.llm = llm
        self.retriever = retriever
        self.reranker = reranker

    async def audit_full_article(self, text: str, rules: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Tuple[str, float]]]:
        """
        Executes the audit phase against the full article text using pre-fetched rules.
        Does NOT perform retrieval.
        Returns (violations, steps, timings)
        """
        logger.info("🔍 Agent: Starting Full-Article Audit Loop...")
        violations, steps, timings = await self._run_audit_loop(text, rules)
        
        # We no longer print the internal table here to allow StyleAuditor to manage consolidated output
        return deduplicate_violations(violations), steps, timings

    async def _run_audit_loop(self, text: str, contexts: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Tuple[str, float]]]:
        """
        Shared internal audit loop for both paragraph and full-article auditing.
        """
        steps = []
        timings = []
        violations = []
        
        # Deduplicate contexts by ID and limit
        unique_contexts = {c['id']: c for c in contexts}.values()
        current_contexts = list(unique_contexts)[:self.config.aggregated_rule_limit]
        
        for iteration in range(self.config.max_agent_iterations):
            logger.info(f"--- Iteration {iteration + 1}/{self.config.max_agent_iterations} ---")
            start_it = time.perf_counter()
            
            # Build Prompt
            prompt = self._build_prompt(text, current_contexts, violations, iteration)
            
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
            formatted = format_violations(new_violations, text, current_contexts)
            if formatted:
                violations.extend(formatted)
                
            # Additional Context (only if we have more iterations to use it)
            if response_obj.additional_queries and (iteration + 1 < self.config.max_agent_iterations) and self.retriever:
                 logger.info(f"🔍 Requesting more context (agentic): {response_obj.additional_queries}")
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
                 current_contexts.extend(new_ctx)
                 # Re-deduplicate
                 unique_contexts = {c['id']: c for c in current_contexts}.values()
                 current_contexts = list(unique_contexts)[:self.config.aggregated_rule_limit]
            
            # Stop Conditions
            if response_obj.confident and not response_obj.needs_more_context:
                break
                
        return violations, steps, timings

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
        if not self.retriever:
            return []
            
        all_results = []
        for q in queries:
             # Just use base retrieval for speed on additional queries
             r_ctx, _ = await self.retriever.retrieve(q)
             all_results.extend(r_ctx)
        return all_results

    def _build_prompt(self, text, contexts, existing_violations, iteration):
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
            paragraph=text,
            context_block=context_block,
            reflection_block=reflection_block
        )
