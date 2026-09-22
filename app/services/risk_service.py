import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.event import Event
from app.models.delivery import Delivery
from app.models.score import Score
from app.models.rule_execution import RuleExecution
from app.models.rule_set import RuleSet
from app.rules.engine import RuleEngine
from app.rules.base import RuleContext
from app.schemas.score import DeliveryRiskSummary, ScoreSchema, RuleExecutionSchema

class RiskService:
    @staticmethod
    async def evaluate_event(session: AsyncSession, event_id: str) -> Score | None:
        """
        Evaluate an event using the active RuleSet and persist the Score.
        """
        # Fetch Event
        stmt = select(Event).where(Event.id == uuid.UUID(event_id))
        result = await session.execute(stmt)
        event = result.scalar_one_or_none()
        if not event:
            return None
            
        # Fetch Delivery projection
        stmt_del = select(Delivery).where(Delivery.id == event.delivery_id)
        res_del = await session.execute(stmt_del)
        delivery = res_del.scalar_one_or_none()
        
        # Fetch Active RuleSet
        # For simplicity, getting the first active ruleset
        stmt_rs = select(RuleSet).where(RuleSet.is_active == True).limit(1)
        res_rs = await session.execute(stmt_rs)
        rule_set = res_rs.scalar_one_or_none()
        
        if not rule_set:
            # Fallback to an empty ruleset if none in DB for some reason
            rule_set = RuleSet(version="default-fallback", config={"rules": {}})
            
        # Initialize Engine and Context
        engine = RuleEngine(rule_set)
        context = RuleContext(session=session, event=event, delivery=delivery)
        
        # Evaluate
        total_score, band, executions = await engine.evaluate_all(context)
        
        # We only generate scores for certain trigger events, or we score every event.
        # Based on rules, if none fired, score is 0.
        # Entity-scoped: typically we score the Delivery for these event types,
        # unless it's a scheduled pair rule. We'll default to delivery entity.
        entity_type = "delivery"
        entity_id = event.delivery_id
        
        # Create Score
        score_record = Score(
            entity_type=entity_type,
            entity_id=entity_id,
            score=total_score,
            band=band,
            ruleset_version=rule_set.version
        )
        session.add(score_record)
        await session.flush() # get score ID
        
        # Create Executions
        for exec_res in executions:
            execution_record = RuleExecution(
                score_id=score_record.id,
                rule_id=exec_res.rule_id,
                rule_version=exec_res.rule_version,
                fired=exec_res.fired,
                evidence=exec_res.evidence
            )
            session.add(execution_record)
            
        return score_record

    @staticmethod
    async def get_delivery_risk_summary(session: AsyncSession, delivery_id: str) -> DeliveryRiskSummary | None:
        """Fetch the latest score and summary for a delivery."""
        # Get delivery
        stmt = select(Delivery).where(Delivery.id == delivery_id)
        result = await session.execute(stmt)
        delivery = result.scalar_one_or_none()
        if not delivery:
            return None
            
        # Get latest score for delivery
        from sqlalchemy.orm import selectinload
        stmt_score = (
            select(Score)
            .options(selectinload(Score.executions))
            .where(Score.entity_type == "delivery")
            .where(Score.entity_id == delivery_id)
            .order_by(Score.computed_at.desc())
            .limit(1)
        )
        score_res = await session.execute(stmt_score)
        latest_score = score_res.scalar_one_or_none()
        
        score_schema = None
        recommendation = "PROCEED"
        
        if latest_score:
            score_schema = ScoreSchema.model_validate(latest_score)
            
            # Map band to decision recommendation
            if latest_score.band == "CRITICAL":
                recommendation = "BLOCK_AND_ESCALATE"
            elif latest_score.band == "HIGH":
                recommendation = "HOLD_PAYOUT_OR_DENY_REFUND"
            elif latest_score.band == "ELEVATED":
                recommendation = "MONITOR"
                
        return DeliveryRiskSummary(
            delivery_id=delivery.id,
            rider_id=delivery.rider_id,
            status=delivery.status,
            latest_score=score_schema,
            recommendation=recommendation
        )
