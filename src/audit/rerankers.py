from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Tuple
import logging
from llama_index.core import QueryBundle
from llama_index.core.postprocessor import LLMRerank
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.llms.google_genai import GoogleGenAI
from src.audit.models import AuditorConfig
# from src.rag.reranker import VertexAIRerank
from src.config import settings
from src.audit.helpers import nodes_to_dicts
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from google.cloud import discoveryengine_v1beta as discoveryengine

logger = logging.getLogger(__name__)

class VertexAIRerank(BaseNodePostprocessor):
    """
    Custom wrapper for Google Vertex AI (Discovery Engine) Semantic Ranker.
    """
    project_id: str = Field(description="Google Cloud Project ID")
    location_id: str = Field(default="global", description="Location for the ranking service")
    ranking_config: str = Field(default="default_ranking_config", description="Ranking config name")
    model: str = Field(default="semantic-ranker-default@latest", description="Model to use for ranking")
    top_n: int = Field(default=3, description="Number of nodes to return")
    
    _client: Any = PrivateAttr()

    def __init__(
        self, 
        project_id: str, 
        location_id: str = "global", 
        ranking_config: str = "default_ranking_config", 
        model: str = "semantic-ranker-default@latest",
        top_n: int = 3,
    ):
        super().__init__(
            project_id=project_id,
            location_id=location_id,
            ranking_config=ranking_config,
            model=model,
            top_n=top_n
        )
        try:
            self._client = discoveryengine.RankServiceClient()
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI RankServiceClient: {e}")
            raise

    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        if not nodes:
            return []
        
        if query_bundle is None:
            raise ValueError("Query bundle is required for reranking.")

        # 1. Prepare the request for Google
        records = []
        for node in nodes:
            # We use the 'display_text' metadata if available, else content
            # Google's ranker works best with the actual text you want to check
            content = node.node.metadata.get('display_text', node.node.get_content())
            records.append(
                discoveryengine.RankingRecord(
                    id=node.node.node_id,
                    content=content,
                )
            )

        # Construct the full resource name for the ranking config
        # Format: projects/{project}/locations/{location}/rankingConfigs/{ranking_config}
        ranking_config_path = self._client.ranking_config_path(
            project=self.project_id,
            location=self.location_id,
            ranking_config=self.ranking_config
        )

        # 2. Call the API
        try:
            request = discoveryengine.RankRequest(
                ranking_config=ranking_config_path,
                model=self.model,
                top_n=self.top_n,
                query=query_bundle.query_str,
                records=records,
            )
            response = self._client.rank(request=request)
        except Exception as e:
            logger.warning(f"Vertex Rerank API Error: {e}. Returning original nodes.")
            # Fallback: return top_n from original list without re-ordering
            return nodes[:self.top_n]

        # 3. Map results back to LlamaIndex Nodes
        id_to_node = {n.node.node_id: n for n in nodes}
        reranked_nodes = []

        for record in response.records:
            if record.id in id_to_node:
                node = id_to_node[record.id]
                # Update score with Google's semantic score
                # Ensure we handle cases where score might be None
                node.score = float(record.score) if record.score is not None else 0.0
                reranked_nodes.append(node)

        return reranked_nodes

class BaseRerankerModule(ABC):
    """Abstract base class for reranking modules."""
    
    def __init__(self, config: AuditorConfig, llm: GoogleGenAI = None):
        self.config = config
        self.llm = llm # Only needed for LLM reranker
        
    @abstractmethod
    async def rerank(self, nodes_data: List[Dict], query: str) -> Tuple[List[Dict], Dict]:
        """
        Execute reranking.
        Input: List of Dicts (previously retrieved results).
        Output: Reranked List of Dicts, Details Dict.
        """
        pass
    
    def _dicts_to_nodes(self, data: List[Dict]) -> List[NodeWithScore]:
        """Helper to convert dicts back to nodes for LlamaIndex processors."""
        nodes = []
        for d in data:
            # Reconstruct node
            node = TextNode(
                text=d['text'],
                metadata={
                    "term": d.get('term'),
                    "url": d.get('url'),
                    "id": d.get('id')
                }
            )
            # Assign score if present
            nodes.append(NodeWithScore(node=node, score=d.get('score', 0.0)))
        return nodes

class CompositeRerankerModule(BaseRerankerModule):
    """
    Applies configured rerankers in sequence (LLM then Vertex, or vice vera).
    For now, matches original logic:
    1. LLM Rerank (if enabled)
    2. Vertex Rerank (if enabled & LLM not used, or chained?) 
    Original code logic was: 
        - If LLM Rerank: do it.
        - If Vertex Rerank AND NOT LLM Rerank: do it.
    We will preserve this logic but encapsulate it.
    """
    
    async def rerank(self, nodes_data: List[Dict], query: str) -> Tuple[List[Dict], Dict]:
        details = {}
        if not nodes_data:
            return [], {}
            
        nodes = self._dicts_to_nodes(nodes_data)
        query_bundle = QueryBundle(query_str=query)
        
        # 1. LLM Rerank
        if self.config.use_llm_rerank and self.llm:
            try:
                reranker = LLMRerank(
                    choice_batch_size=10,
                    top_n=self.config.final_top_k,
                    llm=self.llm
                )
                # LLMRerank supports async postprocess
                results = await reranker.apostprocess_nodes(nodes, query_bundle=query_bundle)
                nodes = results[:self.config.final_top_k]
                details["llm_reranked_count"] = len(nodes)
            except Exception as e:
                logger.warning(f"LLM Rerank failed: {e}")
                details["llm_rerank_error"] = str(e)

        # 2. Vertex Rerank (Only if LLM didn't already run)
        elif self.config.use_vertex_rerank and not self.config.use_llm_rerank:
             try:
                vertex_reranker = VertexAIRerank(
                    project_id=settings.PROJECT_ID,
                    location_id=settings.LLM_REGION,
                    ranking_config="default_ranking_config",
                    top_n=self.config.final_top_k
                )
                # Vertex AI rerank might be sync in the custom class, check usage
                # Original code used .postprocess_nodes (sync)
                results = vertex_reranker.postprocess_nodes(nodes, query_bundle=query_bundle)
                nodes = results[:self.config.final_top_k]
                details["vertex_reranked_count"] = len(nodes)
             except Exception as e:
                 logger.warning(f"Vertex Rerank failed: {e}")
                 details["vertex_rerank_error"] = str(e)
        
        # Filter by score threshold
        filtered_nodes = [
            n for n in nodes 
            if (n.score or 0.0) >= self.config.rerank_score_threshold
        ]
        
        details["final_count"] = len(filtered_nodes)
        
        return nodes_to_dicts(filtered_nodes, source_type="reranked"), details
