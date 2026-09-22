from sqlalchemy import select, func, or_
from datetime import timedelta
from app.rules.base import BaseRule, RuleContext, ExecutionResult
from app.models.delivery import Delivery
from datetime import datetime, timezone

def utc_now_func():
    return datetime.now(timezone.utc)

class PairDisputeVelocityRule(BaseRule):
    rule_id = "pair_dispute_velocity"
    rule_version = "v1.0"

    async def evaluate(self, context: RuleContext) -> ExecutionResult:
        min_deliveries = self.config.get("min_deliveries", 3)
        min_dispute_rate = self.config.get("min_dispute_rate", 0.5)
        rolling_days = self.config.get("rolling_days", 30)
        
        # We need a rider and consumer to form a pair.
        if not context.delivery:
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "missing_delivery_context"})
            
        rider_id = context.delivery.rider_id
        consumer_id = context.delivery.consumer_id
        
        cutoff_date = utc_now_func() - timedelta(days=rolling_days)
        
        # Count total deliveries and disputed deliveries for this pair in the window
        stmt = (
            select(
                func.count(Delivery.id).label("total_deliveries"),
                func.sum(
                    # using postgres cast/case or simple count of disputed
                    # Assuming status='disputed' means disputed
                ).label("disputes")
            )
            .where(Delivery.rider_id == rider_id)
            .where(Delivery.consumer_id == consumer_id)
            .where(Delivery.created_at >= cutoff_date)
        )
        
        # Actually a better query for counting conditionally in sqlalchemy async:
        # select count(id) filter (where status='disputed')
        stmt = select(Delivery.status).where(
            Delivery.rider_id == rider_id,
            Delivery.consumer_id == consumer_id,
            Delivery.created_at >= cutoff_date
        )
        
        result = await context.session.execute(stmt)
        statuses = result.scalars().all()
        
        total_deliveries = len(statuses)
        disputes = sum(1 for s in statuses if s == "disputed")
        
        if total_deliveries < min_deliveries:
            return ExecutionResult(self.rule_id, self.rule_version, False, {
                "total_deliveries": total_deliveries,
                "reason": "insufficient_volume"
            })
            
        dispute_rate = disputes / total_deliveries
        fired = dispute_rate >= min_dispute_rate
        
        evidence = {
            "total_deliveries": total_deliveries,
            "disputes": disputes,
            "dispute_rate": round(dispute_rate, 2),
            "threshold_rate": min_dispute_rate,
            "pair": f"{rider_id}:{consumer_id}"
        }
            
        return ExecutionResult(self.rule_id, self.rule_version, fired, evidence)
