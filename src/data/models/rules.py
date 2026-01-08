from typing import List, Optional
from sqlalchemy import String, Text, ARRAY, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class StyleRule(Base):
    """Master record for a style guide rule."""
    __tablename__ = 'style_rules'
    __table_args__ = {'extend_existing': True}

    # Deterministic ID: hash(term + url)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    term: Mapped[str] = mapped_column(String, nullable=False)
    definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    rule_type: Mapped[str] = mapped_column(String, nullable=False)  # atomic_check, complex_policy
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=[])

    # Relationships
    triggers: Mapped[List["RuleTrigger"]] = relationship(
        "src.data.models.rules.RuleTrigger", back_populates="rule", cascade="all, delete-orphan"
    )
    patterns: Mapped[List["RulePattern"]] = relationship(
        "src.data.models.rules.RulePattern", back_populates="rule", cascade="all, delete-orphan"
    )

class RuleTrigger(Base):
    """Trigger words for O(1) hashmap lookup."""
    __tablename__ = 'rule_triggers'
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trigger_text: Mapped[str] = mapped_column(String, index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(ForeignKey('style_rules.id', ondelete='CASCADE'), nullable=False)

    rule: Mapped["StyleRule"] = relationship("src.data.models.rules.StyleRule", back_populates="triggers")

class RulePattern(Base):
    """Regex patterns for structural violations."""
    __tablename__ = 'rule_patterns'
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pattern_regex: Mapped[str] = mapped_column(String, nullable=False)
    rule_id: Mapped[str] = mapped_column(ForeignKey('style_rules.id', ondelete='CASCADE'), nullable=False)

    rule: Mapped["StyleRule"] = relationship("src.data.models.rules.StyleRule", back_populates="patterns")
