import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Text, ForeignKey, func, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class AuditLog(Base):
    """ORM model for audit_logs table."""
    __tablename__ = 'audit_logs'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    test_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('test_cases.id', ondelete='SET NULL'),
        nullable=True
    )
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(Text, nullable=False)
    llm_parameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    rag_parameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    interim_steps: Mapped[list] = mapped_column(JSONB, nullable=False)
    final_output: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
