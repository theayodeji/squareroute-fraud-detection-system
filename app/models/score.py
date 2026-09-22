import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, utc_now

class Score(Base):
    """
    Entity-scoped risk assessments.
    """
    __tablename__ = "scores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    entity_type: Mapped[str] = mapped_column(String, index=True) # 'delivery', 'rider', 'pair'
    entity_id: Mapped[str] = mapped_column(String, index=True)
    
    score: Mapped[int] = mapped_column(Integer)
    band: Mapped[str] = mapped_column(String) # 'LOW', 'ELEVATED', 'HIGH', 'CRITICAL'
    ruleset_version: Mapped[str] = mapped_column(String)
    
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Relationship to executions
    executions: Mapped[list["RuleExecution"]] = relationship(
        "RuleExecution", back_populates="score", cascade="all, delete-orphan"
    )
