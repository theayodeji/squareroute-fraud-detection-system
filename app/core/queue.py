import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Callable, Awaitable
from app.config import settings

logger = logging.getLogger(__name__)

class BaseQueueBroker(ABC):
    @abstractmethod
    async def enqueue(self, job_name: str, payload: Dict[str, Any]) -> str:
        """Enqueue a job and return its ID."""
        pass

    @abstractmethod
    async def start_worker(self, processor: Callable[[Dict[str, Any]], Awaitable[None]]) -> Any:
        """Start a worker that processes jobs using the provided callback."""
        pass

    @abstractmethod
    async def close(self):
        """Clean up connections."""
        pass


class AsyncMemoryBroker(BaseQueueBroker):
    """Zero-dependency in-memory queue for testing and local dev without Redis."""
    def __init__(self):
        self.queue = asyncio.Queue()
        self.job_counter = 0
        self._worker_task = None

    async def enqueue(self, job_name: str, payload: Dict[str, Any]) -> str:
        self.job_counter += 1
        job_id = f"mem-job-{self.job_counter}"
        await self.queue.put({"id": job_id, "name": job_name, "data": payload})
        logger.info(f"Enqueued {job_name} ({job_id}) in memory broker")
        return job_id

    async def start_worker(self, processor: Callable[[Dict[str, Any]], Awaitable[None]]):
        async def worker_loop():
            logger.info("Memory queue worker started")
            while True:
                job = await self.queue.get()
                try:
                    logger.info(f"Processing memory job {job['id']}")
                    await processor(job["data"])
                except Exception as e:
                    logger.error(f"Error processing job {job['id']}: {e}")
                finally:
                    self.queue.task_done()
                    
        self._worker_task = asyncio.create_task(worker_loop())
        return self._worker_task

    async def close(self):
        if self._worker_task:
            self._worker_task.cancel()


class BullMQRedisBroker(BaseQueueBroker):
    """BullMQ backed by Redis for production use."""
    def __init__(self, redis_url: str, queue_name: str):
        from bullmq import Queue
        import redis.asyncio as redis
        
        self.queue_name = queue_name
        self.redis_conn = redis.from_url(redis_url)
        self.queue = Queue(self.queue_name, {"connection": self.redis_conn})
        self.worker = None

    async def enqueue(self, job_name: str, payload: Dict[str, Any]) -> str:
        job = await self.queue.add(job_name, payload)
        logger.info(f"Enqueued {job_name} ({job.id}) in BullMQ")
        return job.id

    async def start_worker(self, processor: Callable[[Dict[str, Any]], Awaitable[None]]):
        from bullmq import Worker
        
        async def process_job(job, token):
            await processor(job.data)
            
        self.worker = Worker(self.queue_name, process_job, {"connection": self.redis_conn})
        logger.info(f"BullMQ worker started for queue: {self.queue_name}")
        return self.worker

    async def close(self):
        if self.worker:
            await self.worker.close()
        await self.queue.close()


# Global queue instance singleton
def get_queue() -> BaseQueueBroker:
    if settings.REDIS_URL:
        return BullMQRedisBroker(settings.REDIS_URL, settings.QUEUE_NAME)
    return AsyncMemoryBroker()

queue_broker = get_queue()
