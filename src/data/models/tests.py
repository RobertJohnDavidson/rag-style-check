import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Text, ARRAY, ForeignKey, Numeric, func, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class TestCase(Base):
    """ORM model for test_cases table."""
    __tablename__ = 'test_cases'
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_violations: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generation_method: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship to test results
    test_results: Mapped[List["TestResult"]] = relationship(
        "src.data.models.tests.TestResult",
        back_populates="test_case",
        cascade="all, delete-orphan"
    )


class TestResult(Base):
    """ORM model for test_results table."""
    __tablename__ = 'test_results'
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    test_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('test_cases.id', ondelete='CASCADE'),
        nullable=False
    )
    true_positives: Mapped[int] = mapped_column(default=0)
    false_positives: Mapped[int] = mapped_column(default=0)
    false_negatives: Mapped[int] = mapped_column(default=0)
    true_negatives: Mapped[int] = mapped_column(default=0)
    precision: Mapped[float] = mapped_column(Numeric(5, 4))
    recall: Mapped[float] = mapped_column(Numeric(5, 4))
    f1_score: Mapped[float] = mapped_column(Numeric(5, 4))
    detected_violations: Mapped[list] = mapped_column(JSONB, nullable=False)
    tuning_parameters: Mapped[dict] = mapped_column(JSONB, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationship to test case
    test_case: Mapped["TestCase"] = relationship(
        "src.data.models.tests.TestCase",
        back_populates="test_results"
    )
