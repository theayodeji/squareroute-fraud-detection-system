from sqlalchemy import select
from datetime import timedelta, datetime, timezone
from app.rules.base import BaseRule, RuleContext, ExecutionResult
from app.models.delivery import Delivery

def utc_now_func():
    return datetime.now(timezone.utc)

class EntityDisputeVelocityRule(BaseRule):
    # This acts as a base class for entity velocity checks
    entity_type = "rider" # overridden in subclasses
    
    async def evaluate(self, context: RuleContext) -> ExecutionResult:
        min_deliveries = self.config.get("min_deliveries", 10)
        min_dispute_rate = self.config.get("min_dispute_rate", 0.15)
        rolling_days = self.config.get("rolling_days", 30)

        if not context.delivery:
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "missing_delivery_context"})
            
        rider_id = context.delivery.rider_id
        consumer_id = context.delivery.consumer_id
        
        target_entity_id = rider_id if self.entity_type == "rider" else consumer_id
        
        cutoff_date = utc_now_func() - timedelta(days=rolling_days)
        
        if self.entity_type == "rider":
            stmt = select(Delivery.status).where(
                Delivery.rider_id == target_entity_id,
                Delivery.created_at >= cutoff_date
            )
        else:
            stmt = select(Delivery.status).where(
                Delivery.consumer_id == target_entity_id,
                Delivery.created_at >= cutoff_date
            )
            
        result = await context.session.execute(stmt)
        statuses = result.scalars().all()
        
        total_deliveries = len(statuses)
        disputes = sum(1 for s in statuses if s == "disputed")
        
        if total_deliveries < min_deliveries:
            return ExecutionResult(self.rule_id, self.rule_version, False, {
                "entity_type": self.entity_type,
                "total_deliveries": total_deliveries,
                "reason": "insufficient_volume"
            })
            
        dispute_rate = disputes / total_deliveries
        fired = dispute_rate >= min_dispute_rate
        
        evidence = {
            "entity_type": self.entity_type,
            "entity_id": target_entity_id,
            "total_deliveries": total_deliveries,
            "disputes": disputes,
            "dispute_rate": round(dispute_rate, 2),
            "threshold_rate": min_dispute_rate,
        }
            
        return ExecutionResult(self.rule_id, self.rule_version, fired, evidence)


class RiderDisputeVelocityRule(EntityDisputeVelocityRule):
    rule_id = "rider_dispute_velocity"
    rule_version = "v1.0"
    entity_type = "rider"

class ConsumerDisputeVelocityRule(EntityDisputeVelocityRule):
    rule_id = "consumer_dispute_velocity"
    rule_version = "v1.0"
    entity_type = "consumer"
