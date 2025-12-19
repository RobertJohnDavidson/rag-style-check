"""
Pydantic schemas for API request/response models.
"""
from src.api.test_schemas import TuningParameters

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class AuditRequest(BaseModel):
    text: str = Field(..., description="Text to audit for style violations")
    model: Optional[str] = Field(None, description="Optional model override")
    test_id: Optional[str] = Field(None, description="Optional ID of the test case if this is a test run")
    tuning_parameters: Optional[TuningParameters] = Field(None, description="Optional overrides for auditor & RAG settings")


class Violation(BaseModel):
    text: str = Field(..., description="The text snippet that violates the rule")
    rule: str = Field(..., description="The rule name or guideline violated")
    reason: str = Field(..., description="Explanation of why this is a violation")
    url: Optional[str] = Field(None, description="URL to the style guide section")


class AuditResponse(BaseModel):
    violations: List[Violation]
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (processing time, model used, etc.)"
    )


class TestCase(BaseModel):
    id: str
    text: str
    expected_violations: List[Dict[str, str]]


class TestSuiteRequest(BaseModel):
    test_cases: List[TestCase]
    suite_name: Optional[str] = Field(None, description="Name for the test suite")


class ModelInfo(BaseModel):
    name: str
    description: str
    available: bool


class GenerateTextResponse(BaseModel):
    text: str
