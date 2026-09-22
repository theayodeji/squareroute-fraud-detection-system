from sqlalchemy import select
from app.rules.base import BaseRule, RuleContext, ExecutionResult
from app.models.event import Event
from app.core.geo import haversine_distance, calculate_speed_kmh

class GPSJumpSpeedRule(BaseRule):
    rule_id = "gps_jump_speed"
    rule_version = "v1.0"

    async def evaluate(self, context: RuleContext) -> ExecutionResult:
        threshold_kmh = self.config.get("threshold_kmh", 120.0)
        
        # Rule only applies to location pings
        if not context.event or context.event.event_type != "location_ping":
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "not_location_ping"})
            
        current_ping = context.event
        if current_ping.lat is None or current_ping.lng is None:
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "missing_coordinates"})

        # Fetch the immediately preceding location ping for this delivery
        stmt = (
            select(Event)
            .where(Event.delivery_id == current_ping.delivery_id)
            .where(Event.event_type == "location_ping")
            .where(Event.occurred_at < current_ping.occurred_at)
            .order_by(Event.occurred_at.desc())
            .limit(1)
        )
        result = await context.session.execute(stmt)
        prev_ping = result.scalar_one_or_none()

        if not prev_ping or prev_ping.lat is None or prev_ping.lng is None:
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "insufficient_history"})

        distance_m = haversine_distance(prev_ping.lat, prev_ping.lng, current_ping.lat, current_ping.lng)
        time_delta_sec = (current_ping.occurred_at - prev_ping.occurred_at).total_seconds()
        
        speed_kmh = calculate_speed_kmh(distance_m, time_delta_sec)
        
        fired = speed_kmh > threshold_kmh
        
        evidence = {
            "distance_meters": round(distance_m, 2),
            "elapsed_seconds": round(time_delta_sec, 2),
            "speed_kmh": round(speed_kmh, 2),
            "threshold_kmh": threshold_kmh
        }
        
        return ExecutionResult(self.rule_id, self.rule_version, fired, evidence)
