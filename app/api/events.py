from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.schemas.event import EventCreate, EventResponse
from app.services.event_service import EventService

router = APIRouter()

@router.post("/", response_model=EventResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(
    event_data: EventCreate,
    session: AsyncSession = Depends(get_db)
):
    """
    Ingest a delivery lifecycle event.
    Returns 202 Accepted immediately after writing the raw event and enqueueing the job.
    """
    event = await EventService.ingest_event(session, event_data)
    await session.commit()
    
    return EventResponse(
        event_id=str(event.id),
        delivery_id=event.delivery_id,
        status="enqueued"
    )
