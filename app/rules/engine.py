from typing import List, Dict, Any, Tuple
from app.models.rule_set import RuleSet
from app.rules.base import BaseRule, RuleContext, ExecutionResult
from app.rules.gps_jump import GPSJumpSpeedRule
from app.rules.geofence_loiter import GeofenceLoiterRule
from app.rules.verified_pod import VerifiedPODRule
from app.rules.pair_velocity import PairDisputeVelocityRule
from app.rules.entity_velocity import RiderDisputeVelocityRule, ConsumerDisputeVelocityRule

# Registry of available rule classes
RULE_REGISTRY = {
    GPSJumpSpeedRule.rule_id: GPSJumpSpeedRule,
    GeofenceLoiterRule.rule_id: GeofenceLoiterRule,
    VerifiedPODRule.rule_id: VerifiedPODRule,
    PairDisputeVelocityRule.rule_id: PairDisputeVelocityRule,
    RiderDisputeVelocityRule.rule_id: RiderDisputeVelocityRule,
    ConsumerDisputeVelocityRule.rule_id: ConsumerDisputeVelocityRule
}

def determine_band(score: int) -> str:
    """Map a 0-100 score to its risk band."""
    if score <= 29:
        return "LOW"
    elif score <= 59:
        return "ELEVATED"
    elif score <= 84:
        return "HIGH"
    return "CRITICAL"

class RuleEngine:
    def __init__(self, rule_set: RuleSet):
        self.rule_set = rule_set
        self.rules: List[BaseRule] = []
        self.config = rule_set.config
        
        # Instantiate active rules based on the ruleset config
        rule_configs = self.config.get("rules", {})
        for r_id, r_conf in rule_configs.items():
            if r_conf.get("enabled", False) and r_id in RULE_REGISTRY:
                rule_class = RULE_REGISTRY[r_id]
                self.rules.append(rule_class(config=r_conf))
                
    async def evaluate_all(self, context: RuleContext) -> Tuple[int, str, List[ExecutionResult]]:
        """
        Evaluate all active rules in the set and aggregate the score.
        Returns: (final_score, band, executions)
        """
        executions = []
        total_score = 0
        
        for rule in self.rules:
            result = await rule.evaluate(context)
            executions.append(result)
            
            if result.fired:
                # Add the weight assigned to this rule in the ruleset config
                weight = rule.config.get("weight", 0)
                total_score += weight
                
        # Normalize score to 0-100
        total_score = min(max(total_score, 0), 100)
        band = determine_band(total_score)
        
        return total_score, band, executions
