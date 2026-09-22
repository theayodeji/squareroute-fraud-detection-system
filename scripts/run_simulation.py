import asyncio
import logging
from datetime import datetime, timezone, timedelta
from app.core.database import async_session_maker
from app.schemas.event import EventCreate
from app.services.event_service import EventService
from app.worker.consumer import process_job
from app.services.risk_service import RiskService

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("simulation")

def now():
    return datetime.now(timezone.utc)

async def simulate_event(event_data: EventCreate):
    async with async_session_maker() as session:
        event = await EventService.ingest_event(session, event_data)
        await session.commit()
        # Instead of waiting for queue broker, process it synchronously for the simulation
        await process_job({"event_id": str(event.id)})

async def print_risk_report(delivery_id: str, scenario_name: str):
    async with async_session_maker() as session:
        summary = await RiskService.get_delivery_risk_summary(session, delivery_id)
        print(f"\n{'='*50}")
        print(f"SCENARIO: {scenario_name}")
        print(f"{'='*50}")
        if summary and summary.latest_score:
            print(f"DELIVERY ID   : {summary.delivery_id}")
            print(f"SCORE         : {summary.latest_score.score} / 100")
            print(f"BAND          : {summary.latest_score.band}")
            print(f"RECOMMENDATION: {summary.recommendation}")
            print("EVIDENCE:")
            for ex in summary.latest_score.executions:
                fired = "FIRED" if ex.fired else "PASSED"
                print(f"  - [{fired}] {ex.rule_id} -> {ex.evidence}")
        else:
            print("No score generated.")
        print("="*50 + "\n")

async def run_scenarios():
    from scripts.seed_db import seed
    from scripts.simulation_data import generate_scenarios
    await seed()
    
    t0 = now()
    scenarios = generate_scenarios(t0)
    
    # Run the core 4 event-driven scenarios
    for title, data in scenarios.items():
        for event in data["events"]:
            await simulate_event(event)
        await print_risk_report(data["id"], title)

    # ---------------------------------------------------------
    # SCENARIO E: High-Risk Rider (Individual Velocity)
    # ---------------------------------------------------------
    target_lat, target_lng = 40.7128, -74.0060
    del_e_base = "del_rider_risk"
    rider_e = "rider_bad_apple"
    
    async with async_session_maker() as session:
        from app.models.delivery import Delivery
        for i in range(10):
            status = "disputed" if i < 2 else "completed" # 20% dispute rate
            deliv = Delivery(
                id=f"{del_e_base}_{i}",
                consumer_id=f"cust_rand_{i}", # different customers!
                rider_id=rider_e,
                status=status,
                target_lat=target_lat,
                target_lng=target_lng,
                created_at=t0 - timedelta(days=2)
            )
            session.add(deliv)
        await session.commit()
    
    await simulate_event(EventCreate(
        delivery_id=f"{del_e_base}_current", rider_id=rider_e, event_type="delivery_created",
        occurred_at=t0, payload={"target_lat": target_lat, "target_lng": target_lng}
    ))
    await print_risk_report(f"{del_e_base}_current", "E. High-Risk Rider (Should be HIGH risk on dispatch)")

    # ---------------------------------------------------------
    # SCENARIO F: High-Risk Consumer (Individual Velocity)
    # ---------------------------------------------------------
    del_f_base = "del_cust_risk"
    consumer_f = "cust_scammer"
    
    async with async_session_maker() as session:
        for i in range(5):
            status = "disputed" if i < 2 else "completed" # 40% dispute rate
            deliv = Delivery(
                id=f"{del_f_base}_{i}",
                consumer_id=consumer_f,
                rider_id=f"rider_rand_{i}", # different riders!
                status=status,
                target_lat=target_lat,
                target_lng=target_lng,
                created_at=t0 - timedelta(days=2)
            )
            session.add(deliv)
        await session.commit()
    
    await simulate_event(EventCreate(
        delivery_id=f"{del_f_base}_current", rider_id="rider_99", event_type="delivery_created",
        occurred_at=t0, payload={"target_lat": target_lat, "target_lng": target_lng, "consumer_id": consumer_f}
    ))
    await print_risk_report(f"{del_f_base}_current", "F. High-Risk Consumer (Should be HIGH risk on dispatch)")

if __name__ == "__main__":
    asyncio.run(run_scenarios())
