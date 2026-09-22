from typing import Any, Dict
from sqlalchemy import String, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class RuleSet(Base):
    """
    Versioned rule configurations and thresholds.
    """
    __tablename__ = "rule_sets"

    version: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
