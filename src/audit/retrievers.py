from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Tuple
import logging
import json
import asyncio
import time
from llama_index.core import VectorStoreIndex, QueryBundle
from llama_index.core.retrievers import BaseRetriever, VectorIndexRetriever, QueryFusionRetriever
from llama_index.core.schema import NodeWithScore
from llama_index.llms.google_genai import GoogleGenAI
from src.audit.models import AuditorConfig
from src.audit.helpers import nodes_to_dicts
from src.audit.prompts import (
    PROMPT_QUERY_GEN, 
    PROMPT_CLASSIFY_TAGS, 
    STYLE_CATEGORY_LIST,
    PROMPT_IDENTIFY_AND_GENERATE_QUERIES
)
from src.config import settings

logger = logging.getLogger(__name__)

class BaseRetrieverModule(ABC):
    """Abstract base class for retrieval modules."""
    
    def __init__(self, index: VectorStoreIndex, config: AuditorConfig):
        self.index = index
        self.config = config
        
    @abstractmethod
    async def retrieve(self, query: str) -> Tuple[List[Dict], Dict]:
        """
        Execute retrieval.
        Returns:
            - List of rule dicts
            - Dict of details (logs/metadata)
        """
        pass

class SimpleRetrieverModule(BaseRetrieverModule):
    """Basic retrieval using the Vector Store directly."""
    
    async def retrieve(self, query: str) -> Tuple[List[Dict], Dict]:
        details = {}
        retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=self.config.initial_retrieval_count,
            vector_store_query_mode="hybrid",
            sparse_top_k=self.config.sparse_top_k
        )
        try:
            nodes = await retriever.aretrieve(query)
            details["retrieved_nodes_count"] = len(nodes)
            return nodes_to_dicts(nodes, source_type="simple_retrieval"), details
        except Exception as e:
            logger.error(f"Simple retrieval failed: {e}")
            details["error"] = str(e)
            return [], details

class AdvancedRetrieverModule(BaseRetrieverModule):
    """
    Advanced retrieval with:
    1. Tag Classification (optional)
    2. Query Fusion (optional)
    """
    
    def __init__(self, index: VectorStoreIndex, config: AuditorConfig, llm: GoogleGenAI):
        super().__init__(index, config)
        self.llm = llm # Used for classification and query fusion
        
    async def retrieve(self, query: str) -> Tuple[List[Dict], Dict]:
        details = {}
        
        # 1. Tag Classification
        start_classify = time.perf_counter()
        tags = await self._classify_text_async(query)
        details["classify_duration"] = time.perf_counter() - start_classify
        
        normalized_tags = self._normalize_tags(tags)
        details["tags"] = normalized_tags
        
        tags_str = ", ".join(normalized_tags)
        final_query = query
        if normalized_tags:
            logger.info(f"🏷️ Tags: {tags_str}")
            final_query = f"Tags: {tags_str}. Content: {query}"
        
        details["final_query"] = final_query
        
        # 2. Configure Base Retriever
        base_retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=self.config.initial_retrieval_count,
            vector_store_query_mode="hybrid",
            sparse_top_k=self.config.sparse_top_k
        )
        
        # 3. Apply Fusion if enabled
        if self.config.use_query_fusion:
            logger.info("🔥 Using Term-Based Query Fusion (Single LLM Call)")
            try:
                # Single LLM call to identify terms AND generate queries
                start_gen = time.perf_counter()
                term_queries = await self._identify_and_generate_queries(query)
                details["query_gen_duration"] = time.perf_counter() - start_gen
                
                if not term_queries:
                    logger.warning("⚠️ No terms/queries generated, falling back to base query.")
                    start_fallback = time.perf_counter()
                    nodes = await base_retriever.aretrieve(final_query)
                    details["db_retrieval_duration"] = time.perf_counter() - start_fallback
                    details["retrieved_nodes_count"] = len(nodes)
                    return nodes_to_dicts(nodes, source_type="advanced_retrieval_fallback"), details

                # Extract all queries
                all_queries = []
                identified_terms = []
                for item in term_queries:
                    identified_terms.append(item.get("term", ""))
                    all_queries.extend(item.get("queries", []))
                
                details["identified_terms"] = identified_terms
                details["generated_queries"] = all_queries
                logger.info(f"🚀 Running {len(all_queries)} queries in parallel...")

                # Run all queries in parallel
                start_retrieval = time.perf_counter()
                query_tasks = [base_retriever.aretrieve(q) for q in all_queries]
                results = await asyncio.gather(*query_tasks)
                details["db_retrieval_duration"] = time.perf_counter() - start_retrieval
                
                query_to_results = {q: list(r) for q, r in zip(all_queries, results)}

                # Apply reciprocal rank fusion
                start_rf = time.perf_counter()
                fused_nodes = self._reciprocal_rank_fusion(query_to_results)
                details["fusion_duration"] = time.perf_counter() - start_rf
                
                details["retrieved_nodes_count"] = len(fused_nodes)
                return nodes_to_dicts(fused_nodes, source_type="term_fusion"), details

            except Exception as e:
                logger.error(f"Term-based fusion failed: {e}", exc_info=True)
                details["fusion_error"] = str(e)
                # Fallback to simple retrieval
                nodes = await base_retriever.aretrieve(final_query)
                return nodes_to_dicts(nodes, source_type="advanced_retrieval_fallback"), details
        
        # Default behavior: No fusion
        try:
            start_retrieval = time.perf_counter()
            nodes = await base_retriever.aretrieve(final_query)
            details["db_retrieval_duration"] = time.perf_counter() - start_retrieval
            details["retrieved_nodes_count"] = len(nodes)
            return nodes_to_dicts(nodes, source_type="advanced_retrieval"), details
        except Exception as e:
            logger.error(f"Advanced retrieval failed: {e}")
            details["error"] = str(e)
            return [], details

    async def _identify_and_generate_queries(self, text: str) -> List[Dict]:
        """Single LLM call to identify terms AND generate queries for each."""
        prompt = PROMPT_IDENTIFY_AND_GENERATE_QUERIES.format(
            max_terms=self.config.max_violation_terms,
            num_queries=self.config.num_fusion_queries,
            text=text[:2000]
        )
        try:
            resp = await self.llm.acomplete(prompt)
            # Clean response
            clean_text = resp.text.strip().strip("`").strip()
            if clean_text.startswith("json"):
                clean_text = clean_text[4:].strip()
            
            result = json.loads(clean_text)
            terms = result.get("terms", [])
            
            # Validate and limit
            validated = []
            for item in terms[:self.config.max_violation_terms]:
                if isinstance(item, dict) and "term" in item and "queries" in item:
                    validated.append({
                        "term": str(item["term"]),
                        "queries": [str(q) for q in item["queries"][:self.config.num_fusion_queries]]
                    })
            return validated
        except Exception as e:
            logger.warning(f"Failed to identify and generate queries: {e}")
            return []

    def _reciprocal_rank_fusion(self, results: Dict[str, List[NodeWithScore]], k: float = 60.0) -> List[NodeWithScore]:
        """Apply RRF to combine results from multiple queries."""
        fused_scores = {}
        hash_to_node = {}
        
        for query, nodes in results.items():
            # Sort individual result set by score
            sorted_nodes = sorted(nodes, key=lambda x: x.score or 0.0, reverse=True)
            for rank, node in enumerate(sorted_nodes):
                node_hash = node.node.hash
                hash_to_node[node_hash] = node
                if node_hash not in fused_scores:
                    fused_scores[node_hash] = 0.0
                fused_scores[node_hash] += 1.0 / (rank + k)
        
        # Sort combined results by fused score
        sorted_hashes = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Result combined nodes
        reranked_nodes: List[NodeWithScore] = []
        for node_hash, score in sorted_hashes:
            node_with_score = hash_to_node[node_hash]
            node_with_score.score = score
            reranked_nodes.append(node_with_score)
            
        return reranked_nodes

    async def _classify_text_async(self, text: str) -> List[str]:
        prompt_str = PROMPT_CLASSIFY_TAGS.format(
            tags_list_str=", ".join(STYLE_CATEGORY_LIST), 
            text_snippet=text[:1000]
        )
        try:
            resp = await self.llm.acomplete(prompt_str)
            found = [t.strip() for t in resp.text.split(',')]
            return found
        except Exception:
            return []

    def _normalize_tags(self, tags: List[str]) -> List[str]:
        normalized = []
        for tag in tags:
            if not tag:
                continue
            cleaned = tag.replace("*", "").strip()
            base = cleaned.split(":")[0].strip()
            if base:
                normalized.append(base)
        return normalized
