"""
Test Manager - CRUD operations for test cases and results in PostgreSQL.
"""

import os
import json
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text as sql_text

load_dotenv()

# --- CONFIGURATION ---
PROJECT_ID = os.getenv("PROJECT_NAME")
REGION = os.getenv("DB_REGION", "us-central1")
INSTANCE_NAME = os.getenv("INSTANCE_NAME")
DB_USER = os.getenv("DB_USER")
DB_NAME = os.getenv("DB_NAME", "postgres")

def get_ip_type():
    """Determine IP type based on environment"""
    if os.getenv("K_SERVICE"):
        return IPTypes.PRIVATE
    return IPTypes.PUBLIC

async def get_async_conn():
    """Create async database connection"""
    # Create a new Connector with explicit loop to avoid event loop conflicts
    import asyncio
    loop = asyncio.get_running_loop()
    connector = Connector(loop=loop)
    conn = await connector.connect_async(
        f"{PROJECT_ID}:{REGION}:{INSTANCE_NAME}",
        "asyncpg",
        user=DB_USER,
        db=DB_NAME,
        enable_iam_auth=True,
        ip_type=get_ip_type()
    )
    return conn

# Create async engine (singleton pattern)
_engine = None

def get_engine():
    """Get or create the async database engine"""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            "postgresql+asyncpg://",
            async_creator=get_async_conn,
            pool_size=5,
            max_overflow=10
        )
    return _engine


class TestManager:
    """Manager for test case and result database operations"""
    
    def __init__(self):
        self.engine = get_engine()
    
    # --- TEST CASE CRUD OPERATIONS ---
    
    async def create_test(
        self,
        label: str,
        text: str,
        expected_violations: List[Dict[str, Any]],
        generation_method: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new test case"""
        query = sql_text("""
            INSERT INTO test_cases (label, text, expected_violations, generation_method, notes)
            VALUES (:label, :text, :expected_violations, :generation_method, :notes)
            RETURNING id, label, text, expected_violations, generation_method, notes, created_at, updated_at
        """)
        
        async with self.engine.begin() as conn:
            result = await conn.execute(
                query,
                {
                    "label": label,
                    "text": text,
                    "expected_violations": json.dumps(expected_violations),
                    "generation_method": generation_method,
                    "notes": notes
                }
            )
            row = result.fetchone()
            return self._row_to_test_dict(row)
    
    async def get_test(self, test_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a test case by ID"""
        query = sql_text("""
            SELECT id, label, text, expected_violations, generation_method, notes, created_at, updated_at
            FROM test_cases
            WHERE id = :test_id
        """)
        
        async with self.engine.connect() as conn:
            result = await conn.execute(query, {"test_id": str(test_id)})
            row = result.fetchone()
            return self._row_to_test_dict(row) if row else None
    
    async def list_tests(
        self,
        page: int = 1,
        page_size: int = 20,
        generation_method: Optional[str] = None,
        search: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """List test cases with pagination and optional filters"""
        offset = (page - 1) * page_size
        
        # Build WHERE clause
        where_clauses = []
        params = {"page_size": page_size, "offset": offset}
        
        if generation_method:
            where_clauses.append("generation_method = :generation_method")
            params["generation_method"] = generation_method
        
        if search:
            where_clauses.append("(label ILIKE :search OR text ILIKE :search OR notes ILIKE :search)")
            params["search"] = f"%{search}%"
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Get total count
        count_query = sql_text(f"SELECT COUNT(*) FROM test_cases {where_sql}")
        
        # Get paginated results
        list_query = sql_text(f"""
            SELECT id, label, text, expected_violations, generation_method, notes, created_at, updated_at
            FROM test_cases
            {where_sql}
            ORDER BY created_at DESC
            LIMIT :page_size OFFSET :offset
        """)
        
        async with self.engine.connect() as conn:
            # Get count
            count_result = await conn.execute(count_query, params)
            total = count_result.scalar()
            
            # Get tests
            result = await conn.execute(list_query, params)
            tests = [self._row_to_test_dict(row) for row in result.fetchall()]
            
            return tests, total
    
    async def update_test(
        self,
        test_id: UUID,
        label: Optional[str] = None,
        text: Optional[str] = None,
        expected_violations: Optional[List[Dict[str, Any]]] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a test case"""
        updates = []
        params = {"test_id": str(test_id)}
        
        if label is not None:
            updates.append("label = :label")
            params["label"] = label
        
        if text is not None:
            updates.append("text = :text")
            params["text"] = text
        
        if expected_violations is not None:
            updates.append("expected_violations = :expected_violations")
            params["expected_violations"] = json.dumps(expected_violations)
        
        if notes is not None:
            updates.append("notes = :notes")
            params["notes"] = notes
        
        if not updates:
            return await self.get_test(test_id)
        
        query = sql_text(f"""
            UPDATE test_cases
            SET {', '.join(updates)}
            WHERE id = :test_id
            RETURNING id, label, text, expected_violations, generation_method, notes, created_at, updated_at
        """)
        
        async with self.engine.begin() as conn:
            result = await conn.execute(query, params)
            row = result.fetchone()
            return self._row_to_test_dict(row) if row else None
    
    async def delete_test(self, test_id: UUID) -> bool:
        """Delete a test case (and cascade to results)"""
        query = sql_text("DELETE FROM test_cases WHERE id = :test_id")
        
        async with self.engine.begin() as conn:
            result = await conn.execute(query, {"test_id": str(test_id)})
            return result.rowcount > 0
    
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
        query = sql_text("""
            INSERT INTO test_results (
                test_id, true_positives, false_positives, false_negatives, true_negatives,
                precision, recall, f1_score, detected_violations, tuning_parameters
            )
            VALUES (
                :test_id, :true_positives, :false_positives, :false_negatives, :true_negatives,
                :precision, :recall, :f1_score, :detected_violations, :tuning_parameters
            )
            RETURNING id, test_id, true_positives, false_positives, false_negatives, true_negatives,
                      precision, recall, f1_score, detected_violations, tuning_parameters, executed_at
        """)
        
        async with self.engine.begin() as conn:
            result = await conn.execute(
                query,
                {
                    "test_id": str(test_id),
                    "true_positives": true_positives,
                    "false_positives": false_positives,
                    "false_negatives": false_negatives,
                    "true_negatives": true_negatives,
                    "precision": precision,
                    "recall": recall,
                    "f1_score": f1_score,
                    "detected_violations": json.dumps(detected_violations),
                    "tuning_parameters": json.dumps(tuning_parameters)
                }
            )
            row = result.fetchone()
            return self._row_to_result_dict(row)
    
    async def get_test_results(
        self,
        test_id: UUID,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get results for a specific test with pagination"""
        offset = (page - 1) * page_size
        
        count_query = sql_text("SELECT COUNT(*) FROM test_results WHERE test_id = :test_id")
        
        list_query = sql_text("""
            SELECT id, test_id, true_positives, false_positives, false_negatives, true_negatives,
                   precision, recall, f1_score, detected_violations, tuning_parameters, executed_at
            FROM test_results
            WHERE test_id = :test_id
            ORDER BY executed_at DESC
            LIMIT :page_size OFFSET :offset
        """)
        
        async with self.engine.connect() as conn:
            # Get count
            count_result = await conn.execute(count_query, {"test_id": str(test_id)})
            total = count_result.scalar()
            
            # Get results
            result = await conn.execute(
                list_query,
                {"test_id": str(test_id), "page_size": page_size, "offset": offset}
            )
            results = [self._row_to_result_dict(row) for row in result.fetchall()]
            
            return results, total
    
    # --- UTILITY METHODS ---
    
    def _row_to_test_dict(self, row) -> Dict[str, Any]:
        """Convert database row to test case dictionary"""
        if row is None:
            return None
        
        return {
            "id": row[0],
            "label": row[1],
            "text": row[2],
            "expected_violations": row[3] if isinstance(row[3], list) else json.loads(row[3]),
            "generation_method": row[4],
            "notes": row[5],
            "created_at": row[6],
            "updated_at": row[7]
        }
    
    def _row_to_result_dict(self, row) -> Dict[str, Any]:
        """Convert database row to test result dictionary"""
        if row is None:
            return None
        
        return {
            "id": row[0],
            "test_id": row[1],
            "true_positives": row[2],
            "false_positives": row[3],
            "false_negatives": row[4],
            "true_negatives": row[5],
            "precision": row[6],
            "recall": row[7],
            "f1_score": row[8],
            "detected_violations": row[9] if isinstance(row[9], list) else json.loads(row[9]),
            "tuning_parameters": row[10] if isinstance(row[10], dict) else json.loads(row[10]),
            "executed_at": row[11]
        }
    
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
