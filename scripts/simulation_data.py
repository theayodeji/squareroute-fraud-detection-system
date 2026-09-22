from datetime import timedelta
from app.schemas.event import EventCreate

def generate_scenarios(t0):
    target_lat, target_lng = 40.7128, -74.0060
    
    # ---------------------------------------------------------
    # SCENARIO A: Legitimate Delivery
    # ---------------------------------------------------------
    del_a, rider_a = "del_legit_001", "rider_1"
    scenario_a = [
        EventCreate(delivery_id=del_a, rider_id=rider_a, event_type="delivery_created", occurred_at=t0, payload={"target_lat": target_lat, "target_lng": target_lng}),
        EventCreate(delivery_id=del_a, rider_id=rider_a, event_type="location_ping", lat=40.7200, lng=-74.0000, occurred_at=t0 + timedelta(minutes=5)),
        EventCreate(delivery_id=del_a, rider_id=rider_a, event_type="location_ping", lat=40.7129, lng=-74.0061, occurred_at=t0 + timedelta(minutes=10)),
        EventCreate(delivery_id=del_a, rider_id=rider_a, event_type="delivery_completed", occurred_at=t0 + timedelta(minutes=11))
    ]

    # ---------------------------------------------------------
    # SCENARIO B: GPS Teleportation
    # ---------------------------------------------------------
    del_b, rider_b = "del_teleport_002", "rider_2"
    scenario_b = [
        EventCreate(delivery_id=del_b, rider_id=rider_b, event_type="delivery_created", occurred_at=t0, payload={"target_lat": target_lat, "target_lng": target_lng}),
        EventCreate(delivery_id=del_b, rider_id=rider_b, event_type="location_ping", lat=40.7100, lng=-74.0100, occurred_at=t0 + timedelta(minutes=5)),
        EventCreate(delivery_id=del_b, rider_id=rider_b, event_type="location_ping", lat=40.9000, lng=-74.2000, occurred_at=t0 + timedelta(minutes=5, seconds=5))
    ]

    # ---------------------------------------------------------
    # SCENARIO C: Ghost Delivery (Geofence Loiter)
    # ---------------------------------------------------------
    del_c, rider_c = "del_ghost_003", "rider_3"
    lat_150m = target_lat + 0.00135
    scenario_c = [
        EventCreate(delivery_id=del_c, rider_id=rider_c, event_type="delivery_created", occurred_at=t0, payload={"target_lat": target_lat, "target_lng": target_lng}),
        EventCreate(delivery_id=del_c, rider_id=rider_c, event_type="location_ping", lat=lat_150m, lng=-74.0060, occurred_at=t0 + timedelta(minutes=5)),
        EventCreate(delivery_id=del_c, rider_id=rider_c, event_type="location_ping", lat=lat_150m, lng=-74.0061, occurred_at=t0 + timedelta(minutes=11)),
        EventCreate(delivery_id=del_c, rider_id=rider_c, event_type="delivery_completed", occurred_at=t0 + timedelta(minutes=11, seconds=10))
    ]

    # ---------------------------------------------------------
    # SCENARIO D: False DNA Claim
    # ---------------------------------------------------------
    del_d, rider_d = "del_dna_004", "rider_4"
    scenario_d = [
        EventCreate(delivery_id=del_d, rider_id=rider_d, event_type="delivery_created", occurred_at=t0, payload={"target_lat": target_lat, "target_lng": target_lng}),
        EventCreate(delivery_id=del_d, rider_id=rider_d, event_type="delivery_completed", occurred_at=t0 + timedelta(minutes=15), payload={"proof_of_delivery": {"is_verified_by_upstream": True, "pod_type": "photo", "pod_lat": target_lat, "pod_lng": target_lng}}),
        EventCreate(delivery_id=del_d, rider_id=rider_d, event_type="claim_filed", occurred_at=t0 + timedelta(minutes=45), payload={"claim_type": "did_not_arrive"})
    ]

    return {
        "A. Legitimate Delivery (Should be LOW risk)": {"id": del_a, "events": scenario_a},
        "B. GPS Teleportation (Should be HIGH risk in-flight)": {"id": del_b, "events": scenario_b},
        "C. Ghost Delivery Loiter (Should be HIGH risk on payout)": {"id": del_c, "events": scenario_c},
        "D. False DNA Claim (Should be CRITICAL risk on refund)": {"id": del_d, "events": scenario_d}
    }
