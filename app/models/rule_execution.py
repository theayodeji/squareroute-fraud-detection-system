from app.models.score import Score
import uuid
from typing import Any, Dict
from sqlalchemy import String, Boolean, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class RuleExecution(Base):
    """
    Explainable evidence per score.
    """
    __tablename__ = "rule_executions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    score_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scores.id", ondelete="CASCADE"), index=True)
    
    rule_id: Mapped[str] = mapped_column(String)
    rule_version: Mapped[str] = mapped_column(String)
    
    fired: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    score: Mapped["Score"] = relationship("Score", back_populates="executions")
