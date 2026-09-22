import uuid
from datetime import datetime
from typing import Any, Dict
from sqlalchemy import String, Float, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, utc_now

class Event(Base):
    """
    Append-only facts. Represents what happened in the physical world or system.
    """
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[str] = mapped_column(String, index=True)
    rider_id: Mapped[str] = mapped_column(String, index=True)
    
    event_type: Mapped[str] = mapped_column(String, index=True) # e.g. location_ping, delivery_completed, claim_filed
    
    # Location coordinates at the time of the event
    lat: Mapped[float | None] = mapped_column(Float, index=True, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, index=True, nullable=True)
    
    delivery_status: Mapped[str | None] = mapped_column(String, nullable=True)
    
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    source: Mapped[str] = mapped_column(String, default="api")
    schema_version: Mapped[str] = mapped_column(String, default="1.0")
    
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
