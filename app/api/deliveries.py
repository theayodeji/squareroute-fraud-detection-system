from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.api.deps import get_db
from app.models.score import Score
from app.schemas.score import DeliveryRiskSummary, ScoreSchema
from app.services.risk_service import RiskService

router = APIRouter()

@router.get("/{delivery_id}", response_model=DeliveryRiskSummary)
async def get_delivery_risk(
    delivery_id: str,
    session: AsyncSession = Depends(get_db)
):
    """
    Get the current risk summary and decision recommendation for a delivery.
    Consumers: Payout job, Refund job, Ops desk.
    """
    summary = await RiskService.get_delivery_risk_summary(session, delivery_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return summary

@router.get("/{delivery_id}/evidence", response_model=ScoreSchema)
async def get_delivery_evidence(
    delivery_id: str,
    session: AsyncSession = Depends(get_db)
):
    """
    Get the full explainable audit trail for a delivery's score, including rule executions.
    """
    stmt = (
        select(Score)
        .options(selectinload(Score.executions))
        .where(Score.entity_type == "delivery")
        .where(Score.entity_id == delivery_id)
        .order_by(Score.computed_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    score = result.scalar_one_or_none()
    
    if not score:
        raise HTTPException(status_code=404, detail="No score found for delivery")
        
    return score
