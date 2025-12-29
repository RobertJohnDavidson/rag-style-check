"""
Test Manager - CRUD operations for test cases and results using SQLAlchemy ORM.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.db import get_async_session
from src.data.models.tests import TestCase
from src.data.models.tests import TestResult


class TestManager:
    """Manager for test case and result database operations using ORM"""
    
    # --- TEST CASE CRUD OPERATIONS ---
    
    async def create_test(
        self,
        label: str,
        text: str,
        expected_violations: List[str],
        generation_method: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new test case"""
        async with get_async_session() as session:
            test_case = TestCase(
                label=label,
                text=text,
                expected_violations=expected_violations,
                generation_method=generation_method,
                notes=notes
            )
            session.add(test_case)
            await session.flush()
            return self._model_to_dict(test_case)
    
    async def get_test(self, test_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a test case by ID"""
        async with get_async_session() as session:
            result = await session.execute(
                select(TestCase).where(TestCase.id == test_id)
            )
            test_case = result.scalar_one_or_none()
            return self._model_to_dict(test_case) if test_case else None
    
    async def list_tests(
        self,
        page: int = 1,
        page_size: int = 20,
        generation_method: Optional[str] = None,
        search: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """List test cases with pagination and optional filters"""
        async with get_async_session() as session:
            # Build query with filters
            query = select(TestCase)
            
            # Apply filters
            if generation_method:
                query = query.where(TestCase.generation_method == generation_method)
            
            if search:
                search_pattern = f"%{search}%"
                query = query.where(
                    or_(
                        TestCase.label.ilike(search_pattern),
                        TestCase.text.ilike(search_pattern),
                        TestCase.notes.ilike(search_pattern)
                    )
                )
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await session.execute(count_query)
            total = count_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(TestCase.created_at.desc())
            query = query.limit(page_size).offset((page - 1) * page_size)
            
            # Execute query
            result = await session.execute(query)
            test_cases = result.scalars().all()
            
            return [self._model_to_dict(tc) for tc in test_cases], total
    
    async def update_test(
        self,
        test_id: UUID,
        label: Optional[str] = None,
        text: Optional[str] = None,
        expected_violations: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a test case"""
        async with get_async_session() as session:
            result = await session.execute(
                select(TestCase).where(TestCase.id == test_id)
            )
            test_case = result.scalar_one_or_none()
            
            if not test_case:
                return None
            
            # Update provided fields
            if label is not None:
                test_case.label = label
            if text is not None:
                test_case.text = text
            if expected_violations is not None:
                test_case.expected_violations = expected_violations
            if notes is not None:
                test_case.notes = notes
            
            test_case.updated_at = datetime.utcnow()
            await session.flush()
            
            return self._model_to_dict(test_case)
    
    async def delete_test(self, test_id: UUID) -> bool:
        """Delete a test case (and cascade to results)"""
        async with get_async_session() as session:
            result = await session.execute(
                select(TestCase).where(TestCase.id == test_id)
            )
            test_case = result.scalar_one_or_none()
            
            if not test_case:
                return False
            
            await session.delete(test_case)
            return True
    
    # --- TEST RESULT OPERATIONS ---
    
    async def save_test_result(
        self,
        test_id: UUID,
        true_positives: int,
        false_positives: int,
        false_negatives: int,
        true_negatives: int,
        precision: Optional[float],
        recall: Optional[float],
        f1_score: Optional[float],
        detected_violations: List[Dict[str, Any]],
        tuning_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save a test execution result"""
        async with get_async_session() as session:
            test_result = TestResult(
                test_id=test_id,
                true_positives=true_positives,
                false_positives=false_positives,
                false_negatives=false_negatives,
                true_negatives=true_negatives,
                precision=precision,
                recall=recall,
                f1_score=f1_score,
                detected_violations=detected_violations,
                tuning_parameters=tuning_parameters
            )
            session.add(test_result)
            await session.flush()
            return self._result_to_dict(test_result)
    
    async def get_test_results(
        self,
        test_id: UUID,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get results for a specific test with pagination"""
        async with get_async_session() as session:
            # Build query
            query = select(TestResult).where(TestResult.test_id == test_id)
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await session.execute(count_query)
            total = count_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(TestResult.executed_at.desc())
            query = query.limit(page_size).offset((page - 1) * page_size)
            
            # Execute query
            result = await session.execute(query)
            test_results = result.scalars().all()
            
            return [self._result_to_dict(tr) for tr in test_results], total
    
    # --- UTILITY METHODS ---
    
    def _model_to_dict(self, test_case: TestCase) -> Dict[str, Any]:
        """Convert TestCase model to dictionary"""
        if test_case is None:
            return None
        
        return {
            "id": test_case.id,
            "label": test_case.label,
            "text": test_case.text,
            "expected_violations": test_case.expected_violations,
            "generation_method": test_case.generation_method,
            "notes": test_case.notes,
            "created_at": test_case.created_at,
            "updated_at": test_case.updated_at
        }
    
    def _result_to_dict(self, test_result: TestResult) -> Dict[str, Any]:
        """Convert TestResult model to dictionary"""
        if test_result is None:
            return None
        
        return {
            "id": test_result.id,
            "test_id": test_result.test_id,
            "true_positives": test_result.true_positives,
            "false_positives": test_result.false_positives,
            "false_negatives": test_result.false_negatives,
            "true_negatives": test_result.true_negatives,
            "precision": test_result.precision,
            "recall": test_result.recall,
            "f1_score": test_result.f1_score,
            "detected_violations": test_result.detected_violations,
            "tuning_parameters": test_result.tuning_parameters,
            "executed_at": test_result.executed_at
        }
