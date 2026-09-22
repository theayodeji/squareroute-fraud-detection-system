from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.api.deps import get_db
from app.models.score import Score
from app.models.delivery import Delivery

router = APIRouter()

@router.get("/{rider_id}/risk")
async def get_rider_risk_profile(
    rider_id: str,
    session: AsyncSession = Depends(get_db)
):
    """
    Get aggregated risk profile for a rider across multiple deliveries.
    """
    # Just a basic aggregation query for now
    stmt = (
        select(Score.band, func.count(Score.id))
        .join(Delivery, Score.entity_id == Delivery.id)
        .where(Delivery.rider_id == rider_id)
        .group_by(Score.band)
    )
    result = await session.execute(stmt)
    bands = dict(result.all())
    
    return {
        "rider_id": rider_id,
        "historical_bands": bands,
        "is_flagged": bands.get("HIGH", 0) > 0 or bands.get("CRITICAL", 0) > 0
    }
