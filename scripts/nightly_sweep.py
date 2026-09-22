import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, distinct
from sqlalchemy.orm import selectinload

from app.core.database import async_session_maker
from app.models.delivery import Delivery
from app.models.score import Score
from app.models.rule_execution import RuleExecution
from app.models.rule_set import RuleSet
from app.rules.base import RuleContext
from app.rules.entity_velocity import RiderDisputeVelocityRule, ConsumerDisputeVelocityRule
from app.rules.pair_velocity import PairDisputeVelocityRule
from app.rules.engine import RuleEngine, determine_band

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nightly_sweep")

async def run_sweep():
    logger.info("Starting nightly dispute velocity sweep...")
    t0 = datetime.now(timezone.utc)
    cutoff = t0 - timedelta(days=30)
    
    async with async_session_maker() as session:
        # 1. Fetch active Ruleset to get thresholds
        res = await session.execute(select(RuleSet).where(RuleSet.is_active == True))
        active_ruleset = res.scalars().first()
        if not active_ruleset:
            logger.error("No active ruleset found. Aborting.")
            return
            
        config = active_ruleset.config
        
        # Instantiate rules with config
        rule_configs = config.get("rules", {})
        rider_conf = rule_configs.get("rider_dispute_velocity", {})
        consumer_conf = rule_configs.get("consumer_dispute_velocity", {})
        
        rider_rule = RiderDisputeVelocityRule(config=rider_conf)
        consumer_rule = ConsumerDisputeVelocityRule(config=consumer_conf)

        # 2. Find all riders active in the last 30 days
        rider_res = await session.execute(
            select(distinct(Delivery.rider_id)).where(Delivery.created_at >= cutoff)
        )
        active_riders = rider_res.scalars().all()
        
        for rider_id in active_riders:
            if not rider_id: continue
            
            # Create a mock delivery context to satisfy the rule signature
            mock_delivery = Delivery(rider_id=rider_id)
            context = RuleContext(session=session, delivery=mock_delivery)
            
            # Evaluate
            result = await rider_rule.evaluate(context)
            if result.fired:
                logger.warning(f"Rider {rider_id} flagged for high dispute velocity! Rate: {result.evidence.get('dispute_rate')}")
                
                score_val = rider_conf.get("weight", 60)
                band = determine_band(score_val)
                
                score_record = Score(
                    entity_type="rider",
                    entity_id=rider_id,
                    score=score_val,
                    band=band,
                    ruleset_version=active_ruleset.version
                )
                session.add(score_record)
                
                execution = RuleExecution(
                    rule_id=result.rule_id,
                    rule_version="1.0",
                    fired=result.fired,
                    evidence=result.evidence,
                    score=score_record
                )
                session.add(execution)
        
        # 3. Find all consumers active in the last 30 days
        consumer_res = await session.execute(
            select(distinct(Delivery.consumer_id)).where(Delivery.created_at >= cutoff)
        )
        active_consumers = consumer_res.scalars().all()
        
        for consumer_id in active_consumers:
            if not consumer_id: continue
            
            mock_delivery = Delivery(consumer_id=consumer_id)
            context = RuleContext(session=session, delivery=mock_delivery)
            
            result = await consumer_rule.evaluate(context)
            if result.fired:
                logger.warning(f"Consumer {consumer_id} flagged for high dispute velocity! Rate: {result.evidence.get('dispute_rate')}")
                
                score_val = consumer_conf.get("weight", 60)
                band = determine_band(score_val)
                
                score_record = Score(
                    entity_type="consumer",
                    entity_id=consumer_id,
                    score=score_val,
                    band=band,
                    ruleset_version=active_ruleset.version
                )
                session.add(score_record)
                
                execution = RuleExecution(
                    rule_id=result.rule_id,
                    rule_version="1.0",
                    fired=result.fired,
                    evidence=result.evidence,
                    score=score_record
                )
                session.add(execution)
                
        # Commit all new global scores
        await session.commit()
        logger.info("Nightly sweep complete. Scores committed to database.")

if __name__ == "__main__":
    asyncio.run(run_sweep())
