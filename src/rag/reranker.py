import logging
from typing import List, Optional, Any
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle
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