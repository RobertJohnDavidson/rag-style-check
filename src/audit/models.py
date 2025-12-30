from pydantic import BaseModel, Field
from typing import List, Optional
from src.config import settings

class Violation(BaseModel):
    text: str = Field(description="Exact substring from the paragraph that violates the rule")
    explanation: str = Field(description="Why this violates the rule")
    suggested_fix: str = Field(description="Correction or 'omit'")
    rule_id: str = Field(description="ID of the violated rule (e.g. RULE_123)")
    rule_name: Optional[str] = Field(description="Name of the rule", default=None)
    url: Optional[str] = Field(description="URL of the rule", default=None)

class AuditResult(BaseModel):
    thinking: Optional[str] = Field(description="Chain of thought or reasoning process", default=None)
    violations: List[Violation] = Field(default_factory=list)
    confident: bool = Field(description="True if the agent is certain about findings")
    needs_more_context: bool = Field(description="True if more rules are needed")
    additional_queries: List[str] = Field(default_factory=list, description="Queries to find missing rules")

class AuditorConfig(BaseModel):
    """Configuration for StyleAuditor."""
    model_name: str = settings.DEFAULT_MODEL
    temperature: float = 0.0
    initial_retrieval_count: int = settings.DEFAULT_INITIAL_RETRIEVAL_COUNT
    final_top_k: int = settings.DEFAULT_FINAL_TOP_K
    rerank_score_threshold: float = settings.DEFAULT_RERANK_SCORE_THRESHOLD
    aggregated_rule_limit: int = settings.DEFAULT_AGGREGATED_RULE_LIMIT
    max_agent_iterations: int = settings.DEFAULT_MAX_AGENT_ITERATIONS
    max_concurrent_requests: int = settings.DEFAULT_MAX_CONCURRENT_REQUESTS
    use_query_fusion: bool = True
    use_llm_rerank: bool = False
    use_vertex_rerank: bool = True
    include_thinking: bool = False
    sparse_top_k: int = 10
    num_fusion_queries: int = 3
    max_violation_terms: int = 5
