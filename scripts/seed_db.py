import asyncio
import logging
from app.core.database import engine, async_session_maker
from app.models.base import Base
# Import all models to ensure they are registered with Base
from app.models import * 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seeder")

DEFAULT_RULESET_CONFIG = {
    "rules": {
        "gps_jump_speed": {
            "enabled": True,
            "weight": 75,
            "threshold_kmh": 120.0
        },
        "geofence_loiter_completion": {
            "enabled": True,
            "weight": 70,
            "door_radius_m": 30.0,
            "outer_radius_m": 200.0,
            "min_dwell_time_sec": 300.0
        },
        "dna_against_verified_pod": {
            "enabled": True,
            "weight": 85,
            "max_pod_distance_m": 30.0
        },
        "pair_dispute_velocity": {
            "enabled": True,
            "weight": 90,
            "min_deliveries": 3,
            "min_dispute_rate": 0.5,
            "rolling_days": 30
        },
        "rider_dispute_velocity": {
            "enabled": True,
            "weight": 60,
            "min_deliveries": 10,
            "min_dispute_rate": 0.15,
            "rolling_days": 30
        },
        "consumer_dispute_velocity": {
            "enabled": True,
            "weight": 60,
            "min_deliveries": 5,
            "min_dispute_rate": 0.20,
            "rolling_days": 30
        }
    }
}

async def seed():
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    logger.info("Seeding default ruleset...")
    async with async_session_maker() as session:
        # Check if exists
        from sqlalchemy import select
        stmt = select(RuleSet).where(RuleSet.version == "v1.0")
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            rs = RuleSet(
                version="v1.0",
                name="Baseline Risk Rules",
                config=DEFAULT_RULESET_CONFIG,
                is_active=True
            )
            session.add(rs)
            await session.commit()
            logger.info("Inserted v1.0 RuleSet")
        else:
            logger.info("RuleSet v1.0 already exists")

if __name__ == "__main__":
    asyncio.run(seed())
