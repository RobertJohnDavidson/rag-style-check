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
from contextlib import asynccontextmanager
import json
import os
from datetime import datetime
from pathlib import Path
from uuid import UUID
import nest_asyncio
nest_asyncio.apply()

# Import Core Components
from src.config import settings, init_settings
from src.core.db import get_async_engine, get_sync_engine, init_vector_store
from src.core.auditor import StyleAuditor
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
    ModelInfo as TestModelInfo,
    GenerateTestsRequest
)

from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core import Settings as LlamaSettings
from sqlalchemy.ext.asyncio import AsyncEngine

# Global State
auditor: Optional[StyleAuditor] = None
test_manager: Optional[TestManager] = None
db_engine: Optional[AsyncEngine] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Initializes DB connection, LLM settings, and the Auditor.
    """
    global auditor, test_manager, db_engine
    sync_db_engine = None
    
    print("🚀 Starting up Style Checker API...")
    
    # 1. Initialize Settings (Env, Embeddings)
    try:
        init_settings()
        print("✅ Settings initialized.")
    except Exception as e:
        print(f"❌ Settings initialization failed: {e}")
        # We might want to exit here in strict mode, but let's continue for now
    
    # 2. Database Connection
    try:
        db_engine = get_async_engine()
        sync_db_engine = get_sync_engine()
        # Test connection?
        async with db_engine.connect() as conn:
             print("✅ Database connection established.")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
    
    # 3. Vector Store & Index
    if db_engine and sync_db_engine:
        try:
            vector_store = init_vector_store(sync_db_engine, db_engine)
            # But the Auditor needs an index or retriever.
            # Let's create the Index wrapper.
            from llama_index.core import VectorStoreIndex
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=LlamaSettings.embed_model
            )
            print("✅ Vector Store Index ready.")
        except Exception as e:
            print(f"❌ Vector Store init failed: {e}")
            index = None
    else:
        index = None

    # 4. LLM
    llm = GoogleGenAI(
        model=settings.DEFAULT_MODEL,
        vertexai_config={
            "project": settings.PROJECT_ID,
            "location": settings.REGION
        },
        temperature=0.1
    )
    LlamaSettings.llm = llm

    # 5. Initialize Auditor
    if index:
        auditor = StyleAuditor(
            llm=llm,
            index=index
        )
        print("✅ StyleAuditor initialized.")
    else:
        print("⚠️ Auditor running without Vector Store (retrieval will fail).")

    # 6. Initialize Test Manager
    try:
        test_manager = TestManager()
        # Inject dependencies if TestManager needs them
        # (Assuming TestManager handles its own DB/logic for now, or needs update)
        print("✅ TestManager initialized.")
    except Exception as e:
        print(f"❌ TestManager init failed: {e}")

    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    if db_engine:
        await db_engine.dispose()
    if sync_db_engine:
        sync_db_engine.dispose()

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="CBC News Style Checker API",
    description="RAG-based style auditing for CBC News content",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
frontend_build_path = Path(__file__).parent.parent.parent / "frontend" / "build"
if frontend_build_path.exists():
    app.mount("/assets", StaticFiles(directory=frontend_build_path / "_app" / "immutable"), name="assets")

# Dependencies
def get_auditor_instance() -> StyleAuditor:
    if auditor is None:
        raise HTTPException(status_code=503, detail="Auditor not initialized")
    return auditor

def get_test_manager_instance() -> TestManager:
    if test_manager is None:
        raise HTTPException(status_code=503, detail="TestManager not initialized")
    return test_manager

# Endpoints
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "cbc-style-checker", 
        "timestamp": datetime.now().isoformat(),
        "auditor_ready": auditor is not None,
        "db_ready": db_engine is not None
    }

@app.get("/")
async def root():
    return {
        "service": "CBC News Style Checker",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.post("/audit", response_model=AuditResponse)
async def audit_text(
    request: AuditRequest,
    auditor_svc: StyleAuditor = Depends(get_auditor_instance)
):
    """
    Audit text for CBC News style violations.
    """
    try:
        start_time = datetime.now()
        
        # Run the auditor (Async call)
        # Note: request.text might be empty
        violations_dicts = await auditor_svc.check_text(request.text)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Format response
        formatted_violations = [
            Violation(
                text=v.get("text", ""),
                rule=v.get("rule_name", "Unknown"),
                reason=v.get("violation", ""),
                source_url=v.get("source_url", None)
            )
            for v in violations_dicts
        ]
        
        return AuditResponse(
            violations=formatted_violations,
            metadata={
                "processing_time_seconds": processing_time,
                "model": request.model or settings.DEFAULT_MODEL,
                "violation_count": len(formatted_violations)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")

@app.get("/models", response_model=List[ModelInfo])
async def list_models():
    models = [
        ModelInfo(
            name="gemini-2.0-flash-exp",
            description="Fastest model",
            available=True
        ),
        ModelInfo(
            name="gemini-1.5-pro",
            description="More capable model",
            available=True
        )
    ]
    return models

# --- TEST MANAGEMENT ENDPOINTS ---
# NOTE: TestManager logic might need refactor to share the same DB engine/Auditor
# For now keeping it mostly as is but injecting dependencies where possible.

@app.post("/api/tests", response_model=TestRecord, status_code=201)
async def create_test(
    test: TestInput,
    manager: TestManager = Depends(get_test_manager_instance)
):
    try:
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
    manager: TestManager = Depends(get_test_manager_instance)
):
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

@app.post("/api/generate-tests", response_model=List[TestRecord])
async def generate_tests(
    request: GenerateTestsRequest,
    auditor_svc: StyleAuditor = Depends(get_auditor_instance),
    manager: TestManager = Depends(get_test_manager_instance)
):
    """
    Generate synthetic tests or tests from articles.
    Returns the list of created and saved test records.
    """
    try:
        # Dependencies from Auditor service
        # Ensure we have the base retriever for retrieval tasks
        if not hasattr(auditor_svc, 'base_retriever') or not auditor_svc.base_retriever:
             raise HTTPException(status_code=500, detail="Auditor service not initialized with a retriever.")
             
        retriever = auditor_svc.base_retriever
        pass_reranker = getattr(auditor_svc, 'vertex_reranker', None)
        
        generated_data = []
        
        if request.method == "synthetic":
            count = request.count or 3
            # Call generator
            generated_data = await test_generator.generate_synthetic_tests(
                count=count,
                retriever=retriever,
                reranker=pass_reranker
            )
            
        elif request.method == "article":
            if not request.url:
                raise HTTPException(status_code=400, detail="URL is required for article generation")
            
            # Call generator
            result = await test_generator.generate_test_from_article(
                url=request.url,
                retriever=retriever,
                reranker=pass_reranker
            )
            generated_data = [result]
            
        else:
             raise HTTPException(status_code=400, detail="Invalid generation method")
        
        # Save generated tests to DB
        saved_records = []
        for data in generated_data:
            test_dict = await manager.create_test(
                label=data["label"],
                text=data["text"],
                expected_violations=data["expected_violations"],
                generation_method=f"auto-{request.method}",
                notes=f"Auto-generated on {datetime.now().isoformat()}"
            )
            saved_records.append(TestRecord(**test_dict))
            
        return saved_records

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate tests: {str(e)}")


@app.get("/api/tests/{test_id}", response_model=TestRecord)
async def get_test(
    test_id: UUID,
    manager: TestManager = Depends(get_test_manager_instance)
):
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
    manager: TestManager = Depends(get_test_manager_instance)
):
    try:
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
    manager: TestManager = Depends(get_test_manager_instance)
):
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
    manager: TestManager = Depends(get_test_manager_instance),
    auditor_svc: StyleAuditor = Depends(get_auditor_instance)
):
    """
    Run a test case using the Global Auditor service.
    Note: Dynamic tuning overrides on the global auditor are tricky concurrently.
    For this version, we will use the global auditor with its defined settings, 
    IGNORING tuning_params unless we instantiate a temporary one (expensive).
    
    Future TODO: Pass parameters to `check_text`.
    """
    try:
        test_dict = await manager.get_test(test_id)
        if not test_dict:
            raise HTTPException(status_code=404, detail="Test not found")
        
        test_record = TestRecord(**test_dict)
        
        # Run audit
        start_time = datetime.now()
        # Use main auditor
        detected = await auditor_svc.check_text(test_record.text)
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Convert to DetectedViolation
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
        
        # Calculate metrics
        # Simple exact match for now (can be improved)
        tp = 0
        fp = 0
        fn = 0
        
        expected_rules = set(v['link'] for v in test_record.expected_violations if v.get('link'))
        detected_rules = set(v.source_url for v in detected_violations if v.source_url)
        
        tp = len(expected_rules.intersection(detected_rules))
        fp = len(detected_rules - expected_rules)
        fn = len(expected_rules - detected_rules)
        
        tn = 0 # Not applicable for this type of test really
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        metrics = TestMetrics(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            true_negatives=tn,
            precision=precision,
            recall=recall,
            f1_score=f1
        )
        
        return TestRunResult(
            test_record=test_record,
            metrics=metrics,
            detected_violations=detected_violations,
            tuning_parameters=tuning_params.model_dump() if tuning_params else {},
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
    manager: TestManager = Depends(get_test_manager_instance)
):
    try:
        results, total = await manager.get_test_results(test_id=test_id, page=page, page_size=page_size)
        from src.api.test_schemas import TestResult
        return TestResultListResponse(
            results=[TestResult(**r) for r in results],
            total=total, page=page, page_size=page_size,
            has_more=(page * page_size) < total
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")

@app.get("/api/models", response_model=ModelListResponse)
async def list_available_models_api():
    models = [
        TestModelInfo(name="models/gemini-1.5-flash", display_name="Gemini 1.5 Flash", description="Fast", supports_thinking=False),
        TestModelInfo(name="models/gemini-1.5-pro", display_name="Gemini 1.5 Pro", description="Capable", supports_thinking=False)
    ]
    return ModelListResponse(models=models)

@app.get("/api/tuning-defaults", response_model=TuningParameters)
async def get_tuning_defaults():
    # Helper to return current settings as tuning defaults
    return TuningParameters()

# Serve frontend (catch-all)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if frontend_build_path.exists():
        file_path = frontend_build_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        index_path = frontend_build_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Frontend not built.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True, loop="asyncio")

