from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Tuple
import logging
from llama_index.core import VectorStoreIndex, QueryBundle
from llama_index.core.retrievers import BaseRetriever, VectorIndexRetriever, QueryFusionRetriever
from llama_index.llms.google_genai import GoogleGenAI
from src.audit.models import AuditorConfig
from src.audit.helpers import nodes_to_dicts
from src.audit.prompts import PROMPT_QUERY_GEN, PROMPT_CLASSIFY_TAGS, STYLE_CATEGORIES
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
            sparse_top_k=10
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
        tags = await self._classify_text_async(query)
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
            sparse_top_k=10
        )
        
        # 3. Apply Fusion if enabled
        active_retriever = base_retriever
        if self.config.use_query_fusion:
            active_retriever = QueryFusionRetriever(
                [base_retriever],
                llm=self.llm,
                similarity_top_k=self.config.initial_retrieval_count,
                num_queries=3,
                mode="reciprocal_rerank",
                use_async=True,
                verbose=True,
                query_gen_prompt=PROMPT_QUERY_GEN
            )
            
        try:
            nodes = await active_retriever.aretrieve(final_query)
            details["retrieved_nodes_count"] = len(nodes)
            return nodes_to_dicts(nodes, source_type="advanced_retrieval"), details
        except Exception as e:
            logger.error(f"Advanced retrieval failed: {e}")
            details["error"] = str(e)
            return [], details

    async def _classify_text_async(self, text: str) -> List[str]:
        prompt_str = PROMPT_CLASSIFY_TAGS.format(
            tags_list_str=", ".join(STYLE_CATEGORIES.split("\n")), 
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
