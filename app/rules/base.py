from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.event import Event
from app.models.delivery import Delivery

@dataclass
class ExecutionResult:
    rule_id: str
    rule_version: str
    fired: bool
    evidence: Dict[str, Any]

@dataclass
class RuleContext:
    session: AsyncSession
    event: Optional[Event] = None
    delivery: Optional[Delivery] = None
    recent_events: List[Event] = field(default_factory=list)

class BaseRule(ABC):
    """Base interface for all deterministic risk rules."""
    rule_id: str
    rule_version: str
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def evaluate(self, context: RuleContext) -> ExecutionResult:
        """Evaluate the rule against the provided context."""
        pass
