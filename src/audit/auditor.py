import asyncio
import logging
import time
from typing import List, Optional, Any, Dict
from llama_index.core import VectorStoreIndex, Settings as LlamaSettings
from llama_index.core.retrievers import BaseRetriever
from llama_index.llms.google_genai import GoogleGenAI
from src.audit.models import AuditorConfig
from src.config import settings
from src.utils import deduplicate_violations, split_paragraphs
# from src.audit.helpers import split_paragraphs # Wait, split_paragraphs I'll verify if strict or generic.
# Actually I'll put split_paragraphs into src/utils.py as well.
from src.audit.retrievers import AdvancedRetrieverModule, SimpleRetrieverModule
from src.audit.rerankers import CompositeRerankerModule
from src.audit.agent import StyleAgent

logger = logging.getLogger(__name__)

class StyleAuditor:
    """
    Orchestrator for the Style Audit process.
    - Manages configuration.
    - Initializes components (Agent, Retriever, Reranker).
    - Dispatch parallel jobs for paragraphs.
    """
    
    def __init__(
        self,
        index: Optional[VectorStoreIndex] = None,
        config: Optional[AuditorConfig] = None,
    ):
        self.config = config or AuditorConfig()
        self.index = index
        
        # Shared or default resources can be init here if strictly global
        pass

    async def check_text(self, text: str, tuning_params: Optional[Any] = None) -> tuple[List[Dict], Dict]:
        """
        Main Async Entry Point.
        Returns a tuple of (violations, log_data).
        """
        # 1. Resolve Config for this Run
        run_config = self.config
        if tuning_params:
            if hasattr(tuning_params, 'model_dump'):
                overrides = tuning_params.model_dump(exclude_unset=True)
            else:
                overrides = tuning_params
            run_config = self.config.model_copy(update=overrides)

        # 2. Setup Resources for this Run (Per-Request Isolation)
        # LLM
        llm = self._create_llm(run_config)
        
        # Retriever
        if run_config.use_query_fusion:
             # Advanced pipeline with query generation
             retriever_module = AdvancedRetrieverModule(self.index, run_config, llm)
        else:
             # Simple direct retrieval
             retriever_module = SimpleRetrieverModule(self.index, run_config)
             
        # Reranker
        reranker_module = CompositeRerankerModule(run_config, llm)
        
        # Agent Factory
        def create_agent():
            return StyleAgent(run_config, llm, retriever_module, reranker_module)

        if not text.strip():
            return [], {}

        # 3. Execution (Parallel)
        paragraphs = split_paragraphs(text)
        all_violations = []
        interim_steps = []
        
        session_start = time.perf_counter()
        logger.info(f"🔍 Auditing {len(paragraphs)} paragraph(s)...")
        semaphore = asyncio.Semaphore(run_config.max_concurrent_requests)
        
        async def process_paragraph(i: int, paragraph: str):
            async with semaphore:
                agent = create_agent()
                return i, paragraph, await agent.audit_paragraph(paragraph)

        tasks = [process_paragraph(i, p) for i, p in enumerate(paragraphs)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 4. Aggregation
        successful_count = 0
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Paragraph processing failed: {result}")
                interim_steps.append({
                    "type": "paragraph_error",
                    "error": str(result)
                })
            else:
                i, paragraph, (p_violations, p_steps) = result
                successful_count += 1
                if p_violations:
                    all_violations.extend(p_violations)
                interim_steps.append({
                    "paragraph_index": i,
                    "text": paragraph,
                    "steps": p_steps
                })

        session_duration = time.perf_counter() - session_start
        
        if successful_count > 0:
            self._print_session_summary(successful_count, len(paragraphs), session_duration)

        if successful_count == 0:
            logger.error("All paragraphs failed.")

        final_violations = deduplicate_violations(all_violations)
        
        # 5. Logging Payload
        log_data = self._build_log_data(run_config, interim_steps, final_violations)
        log_data["overall_duration_seconds"] = session_duration
        
        return final_violations, log_data

    def _print_session_summary(self, successful, total, duration):
        print("\n" + "#" * 40)
        print("         AUDIT SESSION SUMMARY")
        print("#" * 40)
        print(f"Paragraphs Processed : {successful}/{total}")
        print(f"Total Session Time   : {duration:>10.3f}s")
        if successful > 0:
            print(f"Average Per Para     : {duration/successful:>10.3f}s")
        print("#" * 40 + "\n")

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

    def _build_log_data(self, config, steps, violations):
        return {
            "model_used": config.model_name,
            "llm_parameters": {
                "temperature": config.temperature,
                "max_agent_iterations": config.max_agent_iterations
            },
            "rag_parameters": {
                "initial_retrieval_count": config.initial_retrieval_count,
                 "use_query_fusion": config.use_query_fusion
            },
            "interim_steps": steps,
            "final_output": violations
        }
