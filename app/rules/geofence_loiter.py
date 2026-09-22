from sqlalchemy import select
from app.rules.base import BaseRule, RuleContext, ExecutionResult
from app.models.event import Event
from app.core.geo import haversine_distance

class GeofenceLoiterRule(BaseRule):
    rule_id = "geofence_loiter_completion"
    rule_version = "v1.0"

    async def evaluate(self, context: RuleContext) -> ExecutionResult:
        door_radius_m = self.config.get("door_radius_m", 30.0)
        outer_radius_m = self.config.get("outer_radius_m", 200.0)
        min_dwell_time_sec = self.config.get("min_dwell_time_sec", 300.0)
        
        # Rule only applies to delivery_completed
        if not context.event or context.event.event_type != "delivery_completed":
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "not_delivery_completed"})
            
        delivery = context.delivery
        if not delivery:
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "missing_delivery_context"})

        # Fetch all location pings for this delivery
        stmt = (
            select(Event)
            .where(Event.delivery_id == delivery.id)
            .where(Event.event_type == "location_ping")
            .order_by(Event.occurred_at.asc())
        )
        result = await context.session.execute(stmt)
        pings = result.scalars().all()

        if not pings:
            return ExecutionResult(self.rule_id, self.rule_version, False, {"reason": "no_location_history"})

        min_distance_to_door = float("inf")
        first_time_in_outer_zone = None
        last_time_in_outer_zone = None
        
        for ping in pings:
            if ping.lat is None or ping.lng is None:
                continue
                
            dist = haversine_distance(ping.lat, ping.lng, delivery.target_lat, delivery.target_lng)
            min_distance_to_door = min(min_distance_to_door, dist)
            
            if dist <= outer_radius_m:
                if first_time_in_outer_zone is None:
                    first_time_in_outer_zone = ping.occurred_at
                last_time_in_outer_zone = ping.occurred_at
        
        # If they never entered the outer radius, they didn't loiter there (they might just have dropped it far away, different issue)
        if first_time_in_outer_zone is None or last_time_in_outer_zone is None:
            return ExecutionResult(self.rule_id, self.rule_version, False, {
                "min_distance_to_door_m": round(min_distance_to_door, 2),
                "reason": "never_entered_outer_zone"
            })
            
        dwell_time_seconds = (last_time_in_outer_zone - first_time_in_outer_zone).total_seconds()
        
        # Did they loiter inside outer zone but never approached the door?
        fired = (min_distance_to_door > door_radius_m) and (dwell_time_seconds >= min_dwell_time_sec)

        evidence = {
            "min_distance_to_door_m": round(min_distance_to_door, 2),
            "dwell_time_seconds": round(dwell_time_seconds, 2),
            "door_threshold_m": door_radius_m,
            "outer_threshold_m": outer_radius_m
        }
        if fired:
            evidence["reason"] = "ghost_delivery_loitering"
            
        return ExecutionResult(self.rule_id, self.rule_version, fired, evidence)
