from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

class RuleExecutionSchema(BaseModel):
    rule_id: str
    rule_version: str
    fired: bool
    evidence: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)

class ScoreSchema(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: str
    score: int
    band: str
    ruleset_version: str
    computed_at: datetime
    
    executions: Optional[List[RuleExecutionSchema]] = None

    model_config = ConfigDict(from_attributes=True)

class DeliveryRiskSummary(BaseModel):
    delivery_id: str
    rider_id: str
    status: str
    latest_score: Optional[ScoreSchema]
    recommendation: str # e.g. "PROCEED", "HOLD_PAYOUT"
