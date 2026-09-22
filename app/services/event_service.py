from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.event import Event
from app.models.delivery import Delivery
from app.schemas.event import EventCreate
from app.core.queue import queue_broker

class EventService:
    @staticmethod
    async def ingest_event(session: AsyncSession, event_data: EventCreate) -> Event:
        """
        Persists the raw event and updates the Delivery projection.
        Returns the saved Event.
        """
        # 1. Persist the raw append-only event
        event = Event(
            delivery_id=event_data.delivery_id,
            rider_id=event_data.rider_id,
            event_type=event_data.event_type,
            lat=event_data.lat,
            lng=event_data.lng,
            delivery_status=event_data.delivery_status,
            occurred_at=event_data.occurred_at,
            source=event_data.source,
            payload=event_data.payload
        )
        session.add(event)
        
        # 2. Update Delivery state projection
        stmt = select(Delivery).where(Delivery.id == event_data.delivery_id)
        result = await session.execute(stmt)
        delivery = result.scalar_one_or_none()
        
        if event_data.event_type == "delivery_created":
            if not delivery:
                delivery = Delivery(
                    id=event_data.delivery_id,
                    consumer_id=event_data.payload.get("consumer_id", "unknown"),
                    rider_id=event_data.rider_id,
                    status="created",
                    target_lat=event_data.payload.get("target_lat", 0.0),
                    target_lng=event_data.payload.get("target_lng", 0.0),
                    geofence_radius_m=event_data.payload.get("geofence_radius_m", 30.0)
                )
                session.add(delivery)
        elif delivery:
            # Update projection based on event
            if event_data.delivery_status:
                delivery.status = event_data.delivery_status
            if event_data.event_type == "delivery_completed":
                delivery.completed_at = event_data.occurred_at
                delivery.status = "completed"
                
        # Flush to get the event.id
        await session.flush()
        
        # 3. Enqueue job for background async processing
        await queue_broker.enqueue(
            job_name="process_risk_event",
            payload={"event_id": str(event.id)}
        )
        
        return event
