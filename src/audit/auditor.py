import asyncio
import logging
import time
from typing import List, Optional, Any, Dict, Tuple
from llama_index.core import VectorStoreIndex, Settings as LlamaSettings
from llama_index.llms.google_genai import GoogleGenAI
from src.audit.models import AuditorConfig
from src.config import settings
from src.utils import deduplicate_violations, split_paragraphs
from src.audit.retrievers import AdvancedRetrieverModule, SimpleRetrieverModule
from src.audit.rerankers import CompositeRerankerModule
from src.audit.agent import StyleAgent

logger = logging.getLogger(__name__)

class StyleAuditor:
    """
    Orchestrator for the Style Audit process.
    New Two-Stage Architecture:
    1. Parallel Retrieval (per paragraph)
    2. Aggregated Audit (full article)
    """
    
    def __init__(
        self,
        index: Optional[VectorStoreIndex] = None,
        config: Optional[AuditorConfig] = None,
    ):
        self.config = config or AuditorConfig()
        self.index = index
        
    async def check_text(self, text: str, tuning_params: Optional[Any] = None) -> Tuple[List[Dict], Dict]:
        """
        Main entry point for auditing an article.
        """
        # 1. Resolve Config
        run_config = self.config
        if tuning_params:
            if hasattr(tuning_params, 'model_dump'):
                overrides = tuning_params.model_dump(exclude_unset=True)
            else:
                overrides = tuning_params
            run_config = self.config.model_copy(update=overrides)

        # 2. Setup Resources
        llm = self._create_llm(run_config)
        
        if run_config.use_query_fusion:
             retriever_module = AdvancedRetrieverModule(self.index, run_config, llm)
        else:
             retriever_module = SimpleRetrieverModule(self.index, run_config)
             
        reranker_module = CompositeRerankerModule(run_config, llm)
        agent = StyleAgent(run_config, llm, retriever_module, reranker_module)

        if not text.strip():
            return [], {}

        session_start = time.perf_counter()
        paragraphs = split_paragraphs(text)
        logger.info(f"🔍 Stage 1: Parallel Retrieval for {len(paragraphs)} paragraph(s)...")

        # --- STAGE 1: Parallel Retrieval & Reranking ---
        semaphore = asyncio.Semaphore(run_config.max_concurrent_requests)
        
        async def retrieve_for_para(i: int, p: str):
            async with semaphore:
                # We time each retrieval specifically
                start = time.perf_counter()
                rules, r_details = await retriever_module.retrieve(p)
                reranked, rk_details = await reranker_module.rerank(rules, p)
                duration = time.perf_counter() - start
                return i, p, reranked, {
                    "duration_seconds": duration,
                    "retrieval": r_details,
                    "rerank": rk_details
                }

        retrieval_tasks = [retrieve_for_para(i, p) for i, p in enumerate(paragraphs)]
        retrieval_results = await asyncio.gather(*retrieval_tasks, return_exceptions=True)
        
        all_rules = []
        retrieval_steps = []
        retrieval_durations = []
        successful_retrievals = 0

        for res in retrieval_results:
            if isinstance(res, Exception):
                logger.error(f"Retrieval failed for paragraph: {res}")
                retrieval_steps.append({"type": "retrieval_error", "error": str(res)})
            else:
                i, p, p_rules, p_info = res
                successful_retrievals += 1
                all_rules.extend(p_rules)
                retrieval_durations.append(p_info["duration_seconds"])
                retrieval_steps.append({
                    "paragraph_index": i,
                    "text": p[:100] + "...",
                    **p_info
                })

        # --- STAGE 2: Aggregated Audit ---
        logger.info("🔍 Stage 2: Aggregated Full-Article Audit...")
        
        # Deduplicate rules by ID
        unique_rules = {r['id']: r for r in all_rules if 'id' in r}.values()
        deduped_rules_list = list(unique_rules)
        logger.info(f"📦 Total unique rules collected: {len(deduped_rules_list)}")

        audit_start = time.perf_counter()
        violations, audit_steps, iter_timings = await agent.audit_full_article(text, deduped_rules_list)
        audit_duration = time.perf_counter() - audit_start

        session_duration = time.perf_counter() - session_start
        
        if successful_retrievals > 0:
            self._print_session_summary(
                successful_retrievals, 
                len(paragraphs), 
                retrieval_durations,
                iter_timings,
                session_duration,
                run_config.include_thinking
            )

        # 5. Build Final Payload
        log_data = self._build_log_data(run_config, retrieval_steps, audit_steps, violations)
        log_data["overall_duration_seconds"] = session_duration
        log_data["audit_phase_duration_seconds"] = audit_duration
        log_data["unique_rules_count"] = len(deduped_rules_list)
        log_data["thinking_enabled"] = run_config.include_thinking
        
        return violations, log_data

    def _create_llm(self, config: AuditorConfig) -> GoogleGenAI:
        """Create a configured LLM instance."""
        generation_config = {}
        if config.include_thinking:
            if "2." in config.model_name:
                generation_config["thinking_config"] = {"includeThoughts": True, "thinking_budget": 2000}
            else:
                generation_config["thinking_config"] = {"includeThoughts": True, "thinking_level": "medium"}
                
        return GoogleGenAI(
            model=config.model_name,
            temperature=config.temperature,
            vertexai_config={
                "project": settings.PROJECT_ID,
                "location": settings.LLM_REGION,
            },
        )

    def _build_log_data(self, config, retrieval_steps, audit_steps, violations):
        return {
            "model_used": config.model_name,
            "llm_parameters": {
                "temperature": config.temperature,
                "max_agent_iterations": config.max_agent_iterations
            },
            "rag_parameters": {
                "initial_retrieval_count": config.initial_retrieval_count,
                "use_query_fusion": config.use_query_fusion,
                "max_violation_terms": getattr(config, 'max_violation_terms', 5)
            },
            "interim_steps": retrieval_steps + audit_steps,
            "final_output": violations
        }

    def _print_session_summary(self, successful, total, r_durations, audit_timings, total_duration, thinking_on):
        max_r = max(r_durations) if r_durations else 0
        avg_r = sum(r_durations) / len(r_durations) if r_durations else 0
        thinking_status = "ON" if thinking_on else "OFF"
        
        print("\n" + "#" * 50)
        print(f"{'AUDIT TIMING BREAKDOWN':^50}")
        print("#" * 50)
        
        print(f"{'CONFIGURATION':<35}")
        print("-" * 50)
        print(f"{'  Thinking Mode':<35} | {thinking_status}")
        print("-" * 50)
        
        print(f"{'STAGE 1: PARALLEL RETRIEVAL':<35}")
        print("-" * 50)
        print(f"{'  Paragraphs Processed':<35} | {successful}/{total}")
        print(f"{'  Max Para Duration':<35} | {max_r:>10.3f}s")
        print(f"{'  Avg Para Duration':<35} | {avg_r:>10.3f}s")
        print("-" * 50)
        
        print(f"{'STAGE 2: GLOBAL AUDIT':<35}")
        print("-" * 50)
        for step, duration in audit_timings:
            print(f"{'  ' + step:<35} | {duration:>10.3f}s")
        print("-" * 50)
        
        print(f"{'TOTAL SESSION TIME':<35} | {total_duration:>10.3f}s")
        print("#" * 50 + "\n")
