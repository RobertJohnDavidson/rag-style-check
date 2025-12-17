from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Test_Results(Base):
    __tablename__ = 'test_results'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    test_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('test_cases.id'), nullable=False, ondelete='CASCADE')
    true_positives: Mapped[int] = mapped_column(default=0)
    false_positives: Mapped[int] = mapped_column(default=0)
    false_negatives: Mapped[int] = mapped_column(default=0)
    true_negatives: Mapped[int] = mapped_column(default=0)
    precision: Mapped[float] = mapped_column()
    recall: Mapped[float] = mapped_column()
    f1_score: Mapped[float] = mapped_column()
    detected_violations: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list
    )
    tuning_parameters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    executed_at: Mapped[datetime] = mapped_column(default=datetime.now)