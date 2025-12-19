"""
Pydantic schemas for test management API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


# --- Input Schemas (Request Bodies) ---

class ExpectedViolation(BaseModel):
    """Expected violation in a test case"""
    rule: str = Field(..., description="The rule name that should be detected")
    text: str = Field(..., description="The text snippet that violates the rule")
    reason: Optional[str] = Field(None, description="Why this is a violation")
    link: str = Field(..., description="URL link to the style guide rule")


class TestInput(BaseModel):
    """Schema for creating a new test case"""
    label: str = Field(..., min_length=1, max_length=255, description="Test case label/name")
    text: str = Field(..., min_length=1, description="Text content to audit")
    expected_violations: List[ExpectedViolation] = Field(
        default_factory=list,
        description="List of violations expected to be detected"
    )
    generation_method: str = Field(
        ...,
        pattern="^(manual|article|synthetic)$",
        description="How the test was created: manual, article, or synthetic"
    )
    notes: Optional[str] = Field(None, description="Additional notes about this test case")


class TuningParameters(BaseModel):
    """Configurable parameters for running tests"""
    model_name: str = Field(
        default="gemini-2.5-flash",
        description="LLM model to use for auditing"
    )
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="LLM temperature (0.0-2.0)"
    )
    initial_retrieval_count: int = Field(
        default=75,
        ge=10,
        le=200,
        description="Number of rules to retrieve initially"
    )
    final_top_k: int = Field(
        default=25,
        ge=5,
        le=100,
        description="Number of top rules after reranking"
    )
    rerank_score_threshold: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Minimum rerank score to include a rule"
    )
    aggregated_rule_limit: int = Field(
        default=40,
        ge=10,
        le=100,
        description="Maximum number of unique rules to use"
    )
    min_sentence_length: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Minimum sentence length in words"
    )
    max_agent_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum agent thinking cycles"
    )
    confidence_threshold: float = Field(
        default=10.0,
        ge=0.0,
        le=100.0,
        description="Minimum confidence score for violations"
    )
    include_thinking: bool = Field(
        default=False,
        description="Include LLM thinking process in the output"
    )


class TestUpdateInput(BaseModel):
    """Schema for updating an existing test case"""
    label: Optional[str] = Field(None, min_length=1, max_length=255)
    text: Optional[str] = Field(None, min_length=1)
    expected_violations: Optional[List[ExpectedViolation]] = None
    notes: Optional[str] = None


class GenerateTestsRequest(BaseModel):
    """Request to generate test cases"""
    method: str = Field(..., pattern="^(synthetic|article)$", description="Type of generation")
    count: Optional[int] = Field(3, ge=1, le=10, description="Number of synthetic tests to generate")
    url: Optional[str] = Field(None, description="URL of CBC article to parse (required for article type)")
    topic: Optional[str] = Field(None, description="Topic for synthetic generation (optional)")


# --- Output Schemas (Response Bodies) ---

class TestRecord(BaseModel):
    """Complete test case record from database"""
    id: UUID
    label: str
    text: str
    expected_violations: List[Dict[str, Any]]
    generation_method: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DetectedViolation(BaseModel):
    """Violation detected by the auditor"""
    text: str
    rule: str
    reason: str
    confidence: Optional[float] = None
    source_url: Optional[str] = None


class TestMetrics(BaseModel):
    """Test execution metrics"""
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]


class TestResult(BaseModel):
    """Test execution result record from database"""
    id: UUID
    test_id: UUID
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]
    detected_violations: List[Dict[str, Any]]
    tuning_parameters: Dict[str, Any]
    executed_at: datetime

    class Config:
        from_attributes = True


class TestRunResult(BaseModel):
    """Detailed result from running a test"""
    test_record: TestRecord
    metrics: TestMetrics
    detected_violations: List[DetectedViolation]
    tuning_parameters: Dict[str, Any]
    execution_time_seconds: float


class TestListResponse(BaseModel):
    """Paginated list of test cases"""
    tests: List[TestRecord]
    total: int
    page: int
    page_size: int
    has_more: bool


class TestResultListResponse(BaseModel):
    """Paginated list of test results for a specific test"""
    results: List[TestResult]
    total: int
    page: int
    page_size: int
    has_more: bool


class ModelInfo(BaseModel):
    """Information about available LLM models"""
    name: str
    display_name: str
    description: str
    supports_thinking: bool = False


class ModelListResponse(BaseModel):
    """List of available models"""
    models: List[ModelInfo]
