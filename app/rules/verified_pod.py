from sqlalchemy import select
from app.rules.base import BaseRule, RuleContext, ExecutionResult
from app.models.event import Event
from app.core.geo import haversine_distance

class VerifiedPODRule(BaseRule):
    rule_id = "dna_against_verified_pod"
    rule_version = "v1.0"

    async def evaluate(self, context: RuleContext) -> ExecutionResult:
        max_pod_distance_m = self.config.get("max_pod_distance_m", 30.0)
        
        # Rule only applies to claim_filed of type did_not_arrive
        if not context.event or context.event.event_type != "claim_filed":
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "not_claim_filed"})
            
        claim_type = context.event.payload.get("claim_type")
        if claim_type != "did_not_arrive":
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "not_dna_claim"})
            
        delivery = context.delivery
        if not delivery:
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "missing_delivery_context"})

        # Fetch the delivery_completed event for this delivery
        stmt = (
            select(Event)
            .where(Event.delivery_id == delivery.id)
            .where(Event.event_type == "delivery_completed")
            .order_by(Event.occurred_at.desc())
            .limit(1)
        )
        result = await context.session.execute(stmt)
        completion_event = result.scalar_one_or_none()

        if not completion_event:
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "no_completion_event"})

        pod_data = completion_event.payload.get("proof_of_delivery", {})
        if not pod_data:
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "no_pod_data"})
            
        is_verified = pod_data.get("is_verified_by_upstream", False)
        pod_lat = pod_data.get("pod_lat")
        pod_lng = pod_data.get("pod_lng")
        pod_type = pod_data.get("pod_type", "unknown")
        
        if not is_verified:
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "pod_not_verified"})
            
        if pod_lat is None or pod_lng is None:
            # If signature-based and verified by device proximity to door, we might allow it
            # But let's assume we strictly need geo-coordinates of the POD
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "missing_pod_coordinates"})

        pod_distance = haversine_distance(pod_lat, pod_lng, delivery.target_lat, delivery.target_lng)
        
        fired = pod_distance <= max_pod_distance_m
        
        evidence = {
            "claim_type": claim_type,
            "pod_type": pod_type,
            "pod_distance_to_target_m": round(pod_distance, 2),
            "verified": is_verified,
            "contradiction": fired
        }
            
        return ExecutionResult(self.rule_id, self.rule_version, fired, evidence)
