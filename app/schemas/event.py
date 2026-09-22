from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, Optional

class EventPayload(BaseModel):
    # This captures arbitrary JSON data related to the event
    model_config = {"extra": "allow"}

class EventCreate(BaseModel):
    delivery_id: str = Field(..., description="The ID of the delivery")
    rider_id: str = Field(..., description="The ID of the rider")
    event_type: str = Field(..., description="Type of event (e.g., location_ping, delivery_completed, claim_filed)")
    
    lat: Optional[float] = Field(None, description="Latitude at time of event")
    lng: Optional[float] = Field(None, description="Longitude at time of event")
    
    delivery_status: Optional[str] = Field(None, description="Status of the delivery at this moment")
    
    occurred_at: datetime = Field(..., description="Timestamp when the event actually occurred")
    source: str = Field("api", description="Source of the event (rider_app, customer_app, webhook)")
    
    payload: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")

class EventResponse(BaseModel):
    event_id: str
    delivery_id: str
    status: str = "enqueued"
