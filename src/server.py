"""
FastAPI server for CBC News Style Checker.

Provides REST API endpoints for:
- Text auditing with the style checker
- Test case management
- Model configuration
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import os
from datetime import datetime
from pathlib import Path

from src.audit import StyleAuditor

# Initialize FastAPI app
app = FastAPI(
    title="CBC News Style Checker API",
    description="RAG-based style auditing for CBC News content",
    version="1.0.0"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize auditor (singleton)
auditor: Optional[StyleAuditor] = None


def get_auditor() -> StyleAuditor:
    """Dependency to get or create the auditor instance."""
    global auditor
    if auditor is None:
        auditor = StyleAuditor()
    return auditor


# Request/Response Models
class AuditRequest(BaseModel):
    text: str = Field(..., description="Text to audit for style violations")
    model: Optional[str] = Field(None, description="Optional model override")


class Violation(BaseModel):
    text: str = Field(..., description="The text snippet that violates the rule")
    rule: str = Field(..., description="The rule name or guideline violated")
    reason: str = Field(..., description="Explanation of why this is a violation")
    source_url: Optional[str] = Field(None, description="URL to the style guide section")


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


# API Key validation (simple implementation)
API_KEY = os.getenv("API_KEY", "dev-key-change-in-production")


def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key for protected endpoints."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


# Endpoints

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "CBC News Style Checker",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.post("/audit", response_model=AuditResponse)
async def audit_text(
    request: AuditRequest,
    auditor: StyleAuditor = Depends(get_auditor)
):
    """
    Audit text for CBC News style violations.
    
    Returns a list of violations with explanations and source URLs.
    """
    try:
        start_time = datetime.now()
        
        # Run the auditor
        violations = auditor.check_text(request.text)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Format response
        formatted_violations = [
            Violation(
                text=v.get("text", ""),
                rule=v.get("rule", "Unknown"),
                reason=v.get("reason", ""),
                source_url=v.get("source_url", None)
            )
            for v in violations
        ]
        
        return AuditResponse(
            violations=formatted_violations,
            metadata={
                "processing_time_seconds": processing_time,
                "model": request.model or os.getenv("MODEL", "gemini-2.5-flash"),
                "violation_count": len(formatted_violations)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


@app.get("/models", response_model=List[ModelInfo])
async def list_models():
    """
    List available LLM models for auditing.
    """
    models = [
        ModelInfo(
            name="gemini-2.5-flash",
            description="Fast, cost-effective model for production use",
            available=True
        ),
        ModelInfo(
            name="gemini-1.5-pro",
            description="More capable model for complex cases",
            available=True
        ),
        ModelInfo(
            name="gemini-1.5-flash",
            description="Previous generation fast model",
            available=True
        )
    ]
    return models


@app.post("/tests", status_code=201)
async def create_test_suite(
    request: TestSuiteRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Create a new test suite by saving test cases to a JSON file.
    
    Protected endpoint - requires API key.
    """
    try:
        # Generate filename with timestamp
        suite_name = request.suite_name or "custom_suite"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/{suite_name}_{timestamp}.json"
        
        # Ensure tests directory exists
        Path("tests").mkdir(exist_ok=True)
        
        # Convert to dict format
        test_data = [tc.dict() for tc in request.test_cases]
        
        # Save to file
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        
        return {
            "message": "Test suite created successfully",
            "filename": filename,
            "test_count": len(test_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create test suite: {str(e)}")


@app.post("/tests/run")
async def run_test_suite(
    file_path: str,
    api_key: str = Depends(verify_api_key),
    auditor: StyleAuditor = Depends(get_auditor)
):
    """
    Execute a test suite and return confusion matrix results.
    
    Protected endpoint - requires API key.
    """
    try:
        # Load test cases
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Test file not found: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            test_cases = json.load(f)
        
        # Run tests
        results = {
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "true_negatives": 0,
            "test_details": []
        }
        
        from difflib import SequenceMatcher
        
        def is_text_match(text1: str, text2: str, threshold: float = 0.8) -> bool:
            """Check if two text snippets match using fuzzy comparison."""
            if text1 in text2 or text2 in text1:
                return True
            ratio = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
            return ratio >= threshold
        
        for test_case in test_cases:
            text = test_case["text"]
            expected = test_case.get("expected_violations", [])
            
            # Run auditor
            actual = auditor.check_text(text)
            
            # Match violations
            matched_expected = set()
            matched_actual = set()
            
            for i, exp_v in enumerate(expected):
                for j, act_v in enumerate(actual):
                    if j not in matched_actual and is_text_match(exp_v.get("text", ""), act_v.get("text", "")):
                        matched_expected.add(i)
                        matched_actual.add(j)
                        results["true_positives"] += 1
                        break
            
            # False negatives: expected but not found
            results["false_negatives"] += len(expected) - len(matched_expected)
            
            # False positives: found but not expected
            results["false_positives"] += len(actual) - len(matched_actual)
            
            # True negatives: no violations expected or found
            if len(expected) == 0 and len(actual) == 0:
                results["true_negatives"] += 1
            
            results["test_details"].append({
                "id": test_case.get("id", "unknown"),
                "expected_count": len(expected),
                "actual_count": len(actual),
                "true_positives": len(matched_expected),
                "false_negatives": len(expected) - len(matched_expected),
                "false_positives": len(actual) - len(matched_actual)
            })
        
        # Calculate metrics
        tp = results["true_positives"]
        fp = results["false_positives"]
        fn = results["false_negatives"]
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        results["metrics"] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1, 3)
        }
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Detailed health check including auditor status."""
    try:
        aud = get_auditor()
        return {
            "status": "healthy",
            "auditor_initialized": aud is not None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
