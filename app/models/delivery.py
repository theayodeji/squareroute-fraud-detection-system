from datetime import datetime
from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, utc_now

class Delivery(Base):
    """
    Current state projection. Provides the context layer that rules need to interpret events.
    """
    __tablename__ = "deliveries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    consumer_id: Mapped[str] = mapped_column(String, index=True)
    rider_id: Mapped[str] = mapped_column(String, index=True)
    
    status: Mapped[str] = mapped_column(String, default="created")
    
    target_lat: Mapped[float] = mapped_column(Float)
    target_lng: Mapped[float] = mapped_column(Float)
    geofence_radius_m: Mapped[float] = mapped_column(Float, default=30.0)
    
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
