"""
FastAPI server for CBC News Style Checker.

Provides REST API endpoints for:
- Text auditing with the style checker
- Test case management
- Model configuration
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional, Dict, Any, List
import json
import os
from datetime import datetime
from pathlib import Path

from src.core.auditor import StyleAuditor
from src.core.auditor_configurable import ConfigurableStyleAuditor
from src.core.test_manager import TestManager
from src.core import test_generator
from src.api.schemas import (
    AuditRequest,
    AuditResponse,
    Violation,
    TestCase,
    TestSuiteRequest,
    ModelInfo
)
from src.api.test_schemas import (
    TestInput,
    TestRecord,
    TuningParameters,
    TestRunResult,
    TestMetrics,
    DetectedViolation,
    TestListResponse,
    TestResultListResponse,
    TestUpdateInput,
    ModelListResponse,
    ModelInfo as TestModelInfo
)
from uuid import UUID

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

# Mount static files for frontend (if built)
frontend_build_path = Path(__file__).parent.parent.parent / "frontend" / "build"
if frontend_build_path.exists():
    app.mount("/assets", StaticFiles(directory=frontend_build_path / "_app" / "immutable"), name="assets")

# Initialize auditor and test manager (singletons)
auditor: Optional[StyleAuditor] = None
test_manager: Optional[TestManager] = None


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "cbc-style-checker", "timestamp": datetime.now().isoformat()}

def get_auditor() -> StyleAuditor:
    """Dependency to get or create the auditor instance."""
    global auditor
    if auditor is None:
        auditor = StyleAuditor()
    return auditor


def get_test_manager() -> TestManager:
    """Dependency to get or create the test manager instance."""
    global test_manager
    if test_manager is None:
        test_manager = TestManager()
    return test_manager


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
        violations = await auditor.check_text_async(request.text)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Format response - map auditor fields to API schema
        formatted_violations = [
            Violation(
                text=v.get("text", ""),
                rule=v.get("rule_name", "Unknown"),
                reason=v.get("violation", ""),
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


# --- TEST MANAGEMENT ENDPOINTS ---

@app.post("/api/tests", response_model=TestRecord, status_code=201)
async def create_test(
    test: TestInput,
    manager: TestManager = Depends(get_test_manager)
):
    """Create a new test case."""
    try:
        # Convert expected_violations to dict format
        expected_violations = [v.model_dump() for v in test.expected_violations]
        
        test_dict = await manager.create_test(
            label=test.label,
            text=test.text,
            expected_violations=expected_violations,
            generation_method=test.generation_method,
            notes=test.notes
        )
        
        return TestRecord(**test_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create test: {str(e)}")


@app.get("/api/tests", response_model=TestListResponse)
async def list_tests(
    page: int = 1,
    page_size: int = 20,
    generation_method: Optional[str] = None,
    search: Optional[str] = None,
    manager: TestManager = Depends(get_test_manager)
):
    """List test cases with pagination and filtering."""
    try:
        tests, total = await manager.list_tests(
            page=page,
            page_size=page_size,
            generation_method=generation_method,
            search=search
        )
        
        return TestListResponse(
            tests=[TestRecord(**t) for t in tests],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tests: {str(e)}")


@app.get("/api/tests/{test_id}", response_model=TestRecord)
async def get_test(
    test_id: UUID,
    manager: TestManager = Depends(get_test_manager)
):
    """Get a specific test case by ID."""
    try:
        test_dict = await manager.get_test(test_id)
        if not test_dict:
            raise HTTPException(status_code=404, detail="Test not found")
        return TestRecord(**test_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get test: {str(e)}")


@app.patch("/api/tests/{test_id}", response_model=TestRecord)
async def update_test(
    test_id: UUID,
    update: TestUpdateInput,
    manager: TestManager = Depends(get_test_manager)
):
    """Update a test case."""
    try:
        # Convert expected_violations if provided
        expected_violations = None
        if update.expected_violations is not None:
            expected_violations = [v.model_dump() for v in update.expected_violations]
        
        test_dict = await manager.update_test(
            test_id=test_id,
            label=update.label,
            text=update.text,
            expected_violations=expected_violations,
            notes=update.notes
        )
        
        if not test_dict:
            raise HTTPException(status_code=404, detail="Test not found")
        
        return TestRecord(**test_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update test: {str(e)}")


@app.delete("/api/tests/{test_id}", status_code=204)
async def delete_test(
    test_id: UUID,
    manager: TestManager = Depends(get_test_manager)
):
    """Delete a test case."""
    try:
        deleted = await manager.delete_test(test_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Test not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete test: {str(e)}")


@app.post("/api/tests/{test_id}/run", response_model=TestRunResult)
async def run_test(
    test_id: UUID,
    tuning_params: Optional[TuningParameters] = None,
    manager: TestManager = Depends(get_test_manager)
):
    """
    Run a test case with optional parameter overrides.
    Returns metrics and detected violations.
    """
    try:
        # Get test case
        test_dict = await manager.get_test(test_id)
        if not test_dict:
            raise HTTPException(status_code=404, detail="Test not found")
        
        test_record = TestRecord(**test_dict)
        
        # Create configurable auditor with parameters
        if tuning_params:
            auditor_instance = ConfigurableStyleAuditor(
                model_name=tuning_params.model_name,
                temperature=tuning_params.temperature,
                initial_retrieval_count=tuning_params.initial_retrieval_count,
                final_top_k=tuning_params.final_top_k,
                rerank_score_threshold=tuning_params.rerank_score_threshold,
                aggregated_rule_limit=tuning_params.aggregated_rule_limit,
                min_sentence_length=tuning_params.min_sentence_length,
                max_agent_iterations=tuning_params.max_agent_iterations,
                confidence_threshold=tuning_params.confidence_threshold
            )
            params_dict = tuning_params.model_dump()
        else:
            # Use defaults
            auditor_instance = ConfigurableStyleAuditor()
            params_dict = TuningParameters().model_dump()
        
        # Run audit
        start_time = datetime.now()
        detected = await auditor_instance.check_text_async(test_record.text)
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Convert to DetectedViolation format
        detected_violations = [
            DetectedViolation(
                text=v.get("text", ""),
                rule=v.get("rule_name", "Unknown"),
                reason=v.get("violation", ""),
                confidence=None,
                source_url=v.get("source_url")
            )
            for v in detected
        ]
        
        # Calculate metrics (fuzzy matching)
        from difflib import SequenceMatcher
        
        def is_text_match(text1: str, text2: str, threshold: float = 0.8) -> bool:
            if text1 in text2 or text2 in text1:
                return True
            ratio = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
            return ratio >= threshold
        
        expected = test_record.expected_violations
        matched_expected = set()
        matched_detected = set()
        
        for i, exp_v in enumerate(expected):
            for j, det_v in enumerate(detected_violations):
                if j not in matched_detected and is_text_match(exp_v.get("text", ""), det_v.text):
                    matched_expected.add(i)
                    matched_detected.add(j)
                    break
        
        tp = len(matched_expected)
        fp = len(detected_violations) - len(matched_detected)
        fn = len(expected) - len(matched_expected)
        tn = 1 if len(expected) == 0 and len(detected_violations) == 0 else 0
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else None
        recall = tp / (tp + fn) if (tp + fn) > 0 else None
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision and recall and (precision + recall) > 0) else None
        
        metrics = TestMetrics(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            true_negatives=tn,
            precision=precision,
            recall=recall,
            f1_score=f1_score
        )
        
        # Save result to database
        await manager.save_test_result(
            test_id=test_id,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            true_negatives=tn,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            detected_violations=[v.model_dump() for v in detected_violations],
            tuning_parameters=params_dict
        )
        
        return TestRunResult(
            test_record=test_record,
            metrics=metrics,
            detected_violations=detected_violations,
            tuning_parameters=params_dict,
            execution_time_seconds=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run test: {str(e)}")


@app.get("/api/tests/{test_id}/results", response_model=TestResultListResponse)
async def get_test_results(
    test_id: UUID,
    page: int = 1,
    page_size: int = 10,
    manager: TestManager = Depends(get_test_manager)
):
    """Get execution results for a specific test."""
    try:
        results, total = await manager.get_test_results(
            test_id=test_id,
            page=page,
            page_size=page_size
        )
        
        from src.api.test_schemas import TestResult
        
        return TestResultListResponse(
            results=[TestResult(**r) for r in results],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")


@app.get("/api/models", response_model=ModelListResponse)
async def list_available_models():
    """List available LLM models for test execution."""
    models = [
        TestModelInfo(
            name="models/gemini-1.5-flash",
            display_name="Gemini 1.5 Flash",
            description="Fast, cost-effective model",
            supports_thinking=False
        ),
        TestModelInfo(
            name="models/gemini-1.5-pro",
            display_name="Gemini 1.5 Pro",
            description="More capable model for complex cases",
            supports_thinking=False
        ),
        TestModelInfo(
            name="models/gemini-2.0-flash-thinking-exp",
            display_name="Gemini 2.0 Flash Thinking",
            description="Experimental model with extended reasoning",
            supports_thinking=True
        ),
    ]
    
    return ModelListResponse(models=models)


@app.get("/api/tuning-defaults", response_model=TuningParameters)
async def get_tuning_defaults():
    """Get default tuning parameter values."""
    return TuningParameters()


@app.post("/api/generate-tests")
async def generate_tests(
    article_url: Optional[str] = None,
    count: int = 1,
    method: str = "synthetic"
):
    """
    Generate test cases from CBC articles or synthetically.
    
    - article_url: URL of CBC article (for article method)
    - count: Number of tests to generate (for synthetic method)
    - method: 'article' or 'synthetic'
    """
    try:
        # Get auditor instance to access retriever
        auditor = get_auditor()
        
        if method == "article":
            if not article_url:
                raise HTTPException(status_code=400, detail="article_url required for article method")
            
            if not article_url.startswith("https://www.cbc.ca"):
                raise HTTPException(status_code=400, detail="Must be a valid CBC article URL")
            
            # Generate single test from article
            test = await test_generator.generate_test_from_article(
                article_url,
                auditor.retriever,
                auditor.reranker
            )
            
            return {"tests": [test]}
        
        elif method == "synthetic":
            # Generate multiple synthetic tests
            tests = await test_generator.generate_synthetic_tests(
                count,
                auditor.retriever,
                auditor.reranker
            )
            
            return {"tests": tests}
        
        else:
            raise HTTPException(status_code=400, detail="method must be 'article' or 'synthetic'")
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test generation failed: {str(e)}")


# --- END TEST MANAGEMENT ENDPOINTS ---


# Serve frontend (catch-all route for SPA)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve the built frontend SPA."""
    if frontend_build_path.exists():
        # Try to serve the specific file
        file_path = frontend_build_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for SPA routing
        index_path = frontend_build_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Frontend not built. Run 'npm run build' in frontend/")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

