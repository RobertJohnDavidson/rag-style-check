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
import ahocorasick
from src.audit.tag_matcher import TagMatcher
from sqlalchemy import select
from src.data.db import get_async_session
from src.data.models import StyleRule, RuleTrigger, RulePattern
import re

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
        tag_matcher: Optional[TagMatcher] = None
    ):
        self.config = config or AuditorConfig()
        self.index = index
        self.tag_matcher = tag_matcher
        
    async def check_text(self, text: str, tuning_params: Optional[Any] = None) -> Tuple[List[Dict], Dict]:
        """
        Main entry point for auditing an article.
        Gather rules from multiple sources (Vector, Triggers, Patterns) in parallel,
        deduplicate, and perform a single AI audit.
        """
        # 1. Resolve Config
        run_config = self.config
        if tuning_params:
            if hasattr(tuning_params, 'model_dump'):
                overrides = tuning_params.model_dump(exclude_unset=True)
            else:
                overrides = tuning_params
            run_config = self.config.model_copy(update=overrides)

        if not text.strip():
            return [], {}

        session_start = time.perf_counter()
        llm = self._create_llm(run_config)
        
        # 2. Parallel Rule Gathering
        gathering_tasks = []
        source_names = []

        if run_config.enable_vector_search:
            gathering_tasks.append(self._fetch_vectors(text, run_config, llm))
            source_names.append("vector")
        
        if run_config.enable_triggers:
            gathering_tasks.append(self._fetch_triggers(text))
            source_names.append("triggers")
            
        if run_config.enable_patterns:
            gathering_tasks.append(self._fetch_patterns(text))
            source_names.append("patterns")

        logger.info(f"🔍 Gathering rules from: {', '.join(source_names)}...")
        gathering_results = await asyncio.gather(*gathering_tasks, return_exceptions=True)
        
        all_rules = []
        gathering_details = {}
        
        for name, res in zip(source_names, gathering_results):
            if isinstance(res, Exception):
                logger.error(f"Rule gathering failed for source {name}: {res}")
                gathering_details[name] = {"error": str(res), "count": 0}
            else:
                rules, details = res
                all_rules.extend(rules)
                gathering_details[name] = {**details, "count": len(rules)}

        # 3. Deduplication
        unique_rules_map = {r['id']: r for r in all_rules if 'id' in r}
        deduped_rules_list = list(unique_rules_map.values())
        logger.info(f"📦 Total unique rules collected: {len(deduped_rules_list)}")

        # 4. Aggregated Audit
        logger.info("🔍 Global AI Audit Phase...")
        agent = StyleAgent(run_config, llm)
        
        audit_start = time.perf_counter()
        violations, audit_steps, iter_timings = await agent.audit_full_article(text, deduped_rules_list)
        audit_duration = time.perf_counter() - audit_start
        session_duration = time.perf_counter() - session_start
        
        # 5. Summary and Payload
        self._print_session_summary(
            gathering_details,
            deduped_rules_list,
            iter_timings,
            session_duration,
            run_config.include_thinking
        )

        log_data = self._build_log_data(run_config, gathering_details, audit_steps, violations)
        log_data["overall_duration_seconds"] = session_duration
        log_data["audit_phase_duration_seconds"] = audit_duration
        log_data["unique_rules_count"] = len(deduped_rules_list)
        log_data["thinking_enabled"] = run_config.include_thinking
        
        return violations, log_data

    async def _fetch_vectors(self, text: str, config: AuditorConfig, llm: Any) -> Tuple[List[Dict], Dict]:
        """Existing logic for paragraph-based vector retrieval."""
        start = time.perf_counter()
        paragraphs = split_paragraphs(text)
        
        if config.use_query_fusion:
             retriever = AdvancedRetrieverModule(self.index, config, llm)
        else:
             retriever = SimpleRetrieverModule(self.index, config)
        reranker = CompositeRerankerModule(config, llm)
        
        semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        
        async def retrieve_for_para(i: int, p: str):
            async with semaphore:
                rules, r_details = await retriever.retrieve(p)
                reranked, rk_details = await reranker.rerank(rules, p)
                return reranked

        tasks = [retrieve_for_para(i, p) for i, p in enumerate(paragraphs)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_rules = []
        for res in results:
            if not isinstance(res, Exception):
                all_rules.extend(res)
        
        duration = time.perf_counter() - start
        return all_rules, {"duration_seconds": duration, "paragraphs_count": len(paragraphs)}

    async def _fetch_triggers(self, text: str) -> Tuple[List[Dict], Dict]:
        """Fetches rules whose triggers exist in the text using Aho-Corasick."""
        start = time.perf_counter()
        
        if not self.tag_matcher:
            return [], {"duration_seconds": time.perf_counter() - start, "error": "TagMatcher not initialized"}

        # Use TagMatcher to find rule IDs efficiently
        found_rule_ids = self.tag_matcher.find_matches(text)
        
        if not found_rule_ids:
             return [], {"duration_seconds": time.perf_counter() - start}

        async with get_async_session() as session:
            rule_stmt = select(StyleRule).where(StyleRule.id.in_(found_rule_ids))
            rule_results = await session.execute(rule_stmt)
            rules = rule_results.scalars().all()
            
            rule_dicts = [
                {
                    "id": r.id,
                    "term": r.term,
                    "text": r.definition, 
                    "url": r.url,
                    "tags": r.tags
                }
                for r in rules
            ]
            
        duration = time.perf_counter() - start
        return rule_dicts, {"duration_seconds": duration}

    async def _fetch_patterns(self, text: str) -> Tuple[List[Dict], Dict]:
        """Fetches rules whose regex patterns match the text."""
        start = time.perf_counter()
        
        async with get_async_session() as session:
            # Fetch all patterns first (assuming the list of rules isn't astronomical)
            # Alternatively, we could do this on ingest, but here we can be more dynamic.
            pattern_stmt = select(RulePattern)
            pattern_results = await session.execute(pattern_stmt)
            patterns = pattern_results.scalars().all()
            
            matched_rule_ids = set()
            for p in patterns:
                try:
                    if re.search(p.pattern_regex, text, re.IGNORECASE):
                        matched_rule_ids.add(p.rule_id)
                except re.error as e:
                    logger.warning(f"Invalid regex {p.pattern_regex}: {e}")
            
            if not matched_rule_ids:
                return [], {"duration_seconds": time.perf_counter() - start}
                
            rule_stmt = select(StyleRule).where(StyleRule.id.in_(matched_rule_ids))
            rule_results = await session.execute(rule_stmt)
            rules = rule_results.scalars().all()
            
            rule_dicts = [
                {
                    "id": r.id,
                    "term": r.term,
                    "text": r.definition,
                    "url": r.url,
                    "tags": r.tags
                }
                for r in rules
            ]
            
        duration = time.perf_counter() - start
        return rule_dicts, {"duration_seconds": duration}

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

    def _build_log_data(self, config, gathering_details, audit_steps, violations):
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
            "gathering_details": gathering_details,
            "interim_steps": audit_steps,
            "final_output": violations
        }

    def _print_session_summary(self, gathering_details, rules_list, audit_timings, total_duration, thinking_on):
        thinking_status = "ON" if thinking_on else "OFF"
        
        print("\n" + "#" * 50)
        print(f"{'AUDIT TIMING BREAKDOWN':^50}")
        print("#" * 50)
        
        print(f"{'CONFIGURATION':<35}")
        print("-" * 50)
        print(f"{'  Thinking Mode':<35} | {thinking_status}")
        print("-" * 50)
        
        print(f"{'GATHERING PHASE':<35}")
        print("-" * 50)
        for source, info in gathering_details.items():
            duration = info.get("duration_seconds", 0)
            count = info.get("count", 0)
            print(f"{'  ' + source.capitalize():<35} | {count:>3} rules | {duration:>7.3f}s")
        print(f"{'  Total Unique Rules':<35} | {len(rules_list):>10}")
        print("-" * 50)
        
        print(f"{'AUDIT PHASE':<35}")
        print("-" * 50)
        for step, duration in audit_timings:
            print(f"{'  ' + step:<35} | {duration:>10.3f}s")
        print("-" * 50)
        
        print(f"{'TOTAL SESSION TIME':<35} | {total_duration:>10.3f}s")
        print("#" * 50 + "\n")
