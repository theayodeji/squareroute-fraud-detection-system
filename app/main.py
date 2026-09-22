from fastapi import FastAPI
from app.config import settings
from app.api.events import router as events_router
from app.api.deliveries import router as deliveries_router
from app.api.riders import router as riders_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Event-driven risk engine for delivery fraud detection",
    version="1.0.0"
)

app.include_router(events_router, prefix="/events", tags=["events"])
app.include_router(deliveries_router, prefix="/deliveries", tags=["deliveries"])
app.include_router(riders_router, prefix="/riders", tags=["riders"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
