import pytest
from datetime import datetime, timedelta, timezone
from app.models.delivery import Delivery
from app.models.event import Event
from app.rules.base import RuleContext
from app.rules.entity_velocity import RiderDisputeVelocityRule, ConsumerDisputeVelocityRule
from app.rules.gps_jump import GPSJumpSpeedRule
from app.rules.geofence_loiter import GeofenceLoiterRule
from app.rules.verified_pod import VerifiedPODRule
from app.rules.pair_velocity import PairDisputeVelocityRule

def now():
    return datetime.now(timezone.utc)

@pytest.mark.asyncio
async def test_gps_jump_speed_rule(db_session):
    rule = GPSJumpSpeedRule(config={"threshold_kmh": 120.0})
    
    deliv = Delivery(id="del_gps", rider_id="r1", consumer_id="c1", status="in_flight", target_lat=0.0, target_lng=0.0)
    db_session.add(deliv)
    
    # Event 1: Valid ping
    t1 = now() - timedelta(seconds=10)
    e1 = Event(delivery_id="del_gps", rider_id="r1", event_type="location_ping", lat=40.7128, lng=-74.0060, occurred_at=t1)
    
    # Event 2: Impossible jump (e.g., 20km away in 10 seconds = 7200 km/h)
    e2 = Event(delivery_id="del_gps", rider_id="r1", event_type="location_ping", lat=40.9000, lng=-74.2000, occurred_at=now())
    
    db_session.add_all([e1, e2])
    await db_session.commit()
    
    context = RuleContext(session=db_session, event=e2, delivery=deliv)
    res = await rule.evaluate(context)
    
    assert res.fired is True
    assert res.evidence["speed_kmh"] > 120.0

@pytest.mark.asyncio
async def test_geofence_loiter_rule(db_session):
    rule = GeofenceLoiterRule(config={
        "door_radius_m": 30.0,
        "outer_radius_m": 200.0,
        "min_dwell_time_sec": 300.0
    })
    
    target_lat, target_lng = 40.7128, -74.0060
    deliv = Delivery(id="del_ghost", target_lat=target_lat, target_lng=target_lng, rider_id="r1", consumer_id="c1")
    db_session.add(deliv)
    
    t0 = now()
    # Ping 1: 150m away (enters outer radius)
    e1 = Event(delivery_id="del_ghost", rider_id="r1", event_type="location_ping", lat=40.7128 + 0.00135, lng=-74.0060, occurred_at=t0 - timedelta(minutes=6))
    
    # Ping 2: Still 150m away, 6 minutes later
    e2 = Event(delivery_id="del_ghost", rider_id="r1", event_type="location_ping", lat=40.7128 + 0.00135, lng=-74.0060, occurred_at=t0)
    
    # Event 3: Delivery completed
    e3 = Event(delivery_id="del_ghost", rider_id="r1", event_type="delivery_completed", occurred_at=t0 + timedelta(seconds=1))
    
    db_session.add_all([e1, e2, e3])
    await db_session.commit()
    
    context = RuleContext(session=db_session, event=e3, delivery=deliv)
    res = await rule.evaluate(context)
    
    assert res.fired is True
    assert res.evidence["dwell_time_seconds"] >= 300.0
    assert res.evidence["min_distance_to_door_m"] > 30.0

@pytest.mark.asyncio
async def test_verified_pod_rule(db_session):
    rule = VerifiedPODRule(config={"max_pod_distance_m": 30.0})
    
    target_lat, target_lng = 40.7128, -74.0060
    deliv = Delivery(id="del_pod", target_lat=target_lat, target_lng=target_lng, rider_id="r1", consumer_id="c1")
    db_session.add(deliv)
    
    # Event 1: Valid completion exactly at target
    e1 = Event(
        delivery_id="del_pod", rider_id="r1", event_type="delivery_completed",
        payload={"proof_of_delivery": {"is_verified_by_upstream": True, "pod_type": "photo", "pod_lat": target_lat, "pod_lng": target_lng}},
        occurred_at=now() - timedelta(minutes=30)
    )
    
    # Event 2: DNA Claim
    e2 = Event(delivery_id="del_pod", rider_id="r1", event_type="claim_filed", payload={"claim_type": "did_not_arrive"}, occurred_at=now())
    
    db_session.add_all([e1, e2])
    await db_session.commit()
    
    context = RuleContext(session=db_session, event=e2, delivery=deliv)
    res = await rule.evaluate(context)
    
    assert res.fired is True
    assert res.evidence["contradiction"] is True

@pytest.mark.asyncio
async def test_pair_dispute_velocity_rule(db_session):
    rule = PairDisputeVelocityRule(config={
        "min_deliveries": 3,
        "min_dispute_rate": 0.50,
        "rolling_days": 30
    })
    
    rider_id, consumer_id = "r_pair", "c_pair"
    # Create 4 deliveries, 2 disputed = 50% rate
    for i in range(4):
        status = "disputed" if i < 2 else "completed"
        deliv = Delivery(id=f"del_pair_{i}", rider_id=rider_id, consumer_id=consumer_id, status=status, created_at=now(), target_lat=0.0, target_lng=0.0)
        db_session.add(deliv)
        
    await db_session.commit()
    context = RuleContext(session=db_session, delivery=deliv)
    res = await rule.evaluate(context)
    
    assert res.fired is True
    assert res.evidence["dispute_rate"] == 0.50
    # Setup configuration
    rule = RiderDisputeVelocityRule(config={
        "min_deliveries": 10,
        "min_dispute_rate": 0.15,
        "rolling_days": 30
    })
    
    # Create 10 deliveries for rider_1 (2 disputed = 20% rate)
    rider_id = "rider_1"
    for i in range(10):
        status = "disputed" if i < 2 else "completed"
        deliv = Delivery(
            id=f"del_{i}",
            consumer_id=f"cust_{i}",
            rider_id=rider_id,
            status=status,
            target_lat=0.0,
            target_lng=0.0,
            created_at=now() - timedelta(days=5)
        )
        db_session.add(deliv)
    
    await db_session.commit()
    
    # Create context from one of the deliveries
    context = RuleContext(session=db_session, delivery=deliv)
    
    result = await rule.evaluate(context)
    
    assert result.fired is True
    assert result.evidence["dispute_rate"] == 0.20
    assert result.evidence["total_deliveries"] == 10

@pytest.mark.asyncio
async def test_consumer_dispute_velocity_fires(db_session):
    rule = ConsumerDisputeVelocityRule(config={
        "min_deliveries": 5,
        "min_dispute_rate": 0.20,
        "rolling_days": 30
    })
    
    consumer_id = "cust_bad"
    # Create 5 deliveries (1 disputed = 20% rate)
    for i in range(5):
        status = "disputed" if i == 0 else "completed"
        deliv = Delivery(
            id=f"del_c_{i}",
            consumer_id=consumer_id,
            rider_id=f"rider_{i}",
            status=status,
            target_lat=0.0,
            target_lng=0.0,
            created_at=now() - timedelta(days=2)
        )
        db_session.add(deliv)
        
    await db_session.commit()
    
    context = RuleContext(session=db_session, delivery=deliv)
    result = await rule.evaluate(context)
    
    assert result.fired is True
    assert result.evidence["dispute_rate"] == 0.20
    assert result.evidence["total_deliveries"] == 5

@pytest.mark.asyncio
async def test_rider_dispute_velocity_ignores_old_data(db_session):
    rule = RiderDisputeVelocityRule(config={
        "min_deliveries": 2,
        "min_dispute_rate": 0.50,
        "rolling_days": 30
    })
    
    rider_id = "rider_old"
    # Create 2 disputed deliveries 40 days ago (outside rolling window)
    for i in range(2):
        deliv = Delivery(
            id=f"del_old_{i}",
            consumer_id=f"cust_old_{i}",
            rider_id=rider_id,
            status="disputed",
            target_lat=0.0,
            target_lng=0.0,
            created_at=now() - timedelta(days=40)
        )
        db_session.add(deliv)
        
    await db_session.commit()
    
    context = RuleContext(session=db_session, delivery=deliv)
    result = await rule.evaluate(context)
    
    # Fails because 0 recent deliveries
    assert result.fired is False
    assert result.evidence["reason"] == "insufficient_volume"
    assert result.evidence["total_deliveries"] == 0
