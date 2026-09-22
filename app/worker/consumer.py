import asyncio
import logging
from typing import Dict, Any
from app.core.queue import queue_broker
from app.core.database import async_session_maker
from app.services.risk_service import RiskService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

async def process_job(payload: Dict[str, Any]):
    """Job processor callback."""
    event_id = payload.get("event_id")
    if not event_id:
        logger.error("Job payload missing event_id")
        return
        
    logger.info(f"Worker processing event_id: {event_id}")
    
    async with async_session_maker() as session:
        try:
            score = await RiskService.evaluate_event(session, event_id)
            if score:
                logger.info(f"Score generated for {score.entity_type} {score.entity_id}: {score.score} ({score.band})")
            else:
                logger.warning(f"Could not evaluate event {event_id}")
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to process event {event_id}: {e}", exc_info=True)
            raise # Let the queue broker handle retries if applicable

async def run_worker():
    """Main entrypoint for the worker process."""
    logger.info("Starting Risk Engine Queue Worker...")
    
    # Start the worker
    worker_task = await queue_broker.start_worker(process_job)
    
    # Keep the process alive
    try:
        # BullMQ Worker has a wait mechanism, memory queue task is a standard asyncio Task
        if hasattr(worker_task, "wait"):
            # Await the BullMQ worker
            pass
        
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Worker shutting down...")
    finally:
        await queue_broker.close()

if __name__ == "__main__":
    asyncio.run(run_worker())
