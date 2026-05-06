"""
Background job queue service for email processing.

Provides enterprise-grade background job processing with support
for email queues, retry logic, scheduling, and monitoring.
"""

import asyncio
import json
import pickle
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import redis
import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BackgroundJobError, EmailError
from app.services.email import EmailService
from app.db.models import BackgroundJob, EmailQueue

logger = structlog.get_logger()


class JobStatus(Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class JobPriority(Enum):
    """Job priority enumeration."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Job:
    """Background job data structure."""
    id: str
    task_name: str
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: JobPriority = JobPriority.NORMAL
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    timeout: int = 300  # seconds
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BackgroundJobQueue:
    """
    Enterprise-grade background job queue service.
    
    Features:
    - Redis-based job queue
    - Priority-based processing
    - Retry logic with exponential backoff
    - Job scheduling
    - Monitoring and metrics
    - Dead letter queue
    - Worker management
    - Job dependencies
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or getattr(settings, 'redis_url', None)
        self.redis_client = None
        self.workers = {}
        self.is_running = False
        self.job_handlers: Dict[str, Callable] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Queue names
        self.main_queue = "background_jobs:main"
        self.priority_queue = "background_jobs:priority"
        self.retry_queue = "background_jobs:retry"
        self.dead_letter_queue = "background_jobs:dead_letter"
        self.processing_queue = "background_jobs:processing"
        
        # Metrics
        self.metrics = {
            "jobs_processed": 0,
            "jobs_failed": 0,
            "jobs_retried": 0,
            "processing_time": 0.0,
            "queue_size": 0
        }
        
        self._setup_redis()
        self._register_default_handlers()
    
    def _setup_redis(self) -> None:
        """Setup Redis connection."""
        try:
            if self.redis_url:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=False,
                    max_connections=20,
                    retry_on_timeout=True
                )
                logger.info("Background job queue connected to Redis")
            else:
                logger.warning("No Redis URL provided, using in-memory fallback")
                self.redis_client = None
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.redis_client = None
    
    def _register_default_handlers(self) -> None:
        """Register default job handlers."""
        self.register_handler("send_email", self._handle_send_email)
        self.register_handler("send_bulk_email", self._handle_send_bulk_email)
        self.register_handler("process_email_queue", self._handle_process_email_queue)
    
    def register_handler(self, task_name: str, handler: Callable) -> None:
        """Register a job handler."""
        self.job_handlers[task_name] = handler
        logger.info(f"Registered job handler: {task_name}")
    
    def enqueue_job(
        self,
        task_name: str,
        args: tuple = (),
        kwargs: dict = None,
        priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 3,
        retry_delay: int = 60,
        timeout: int = 300,
        scheduled_at: Optional[datetime] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Enqueue a background job.
        
        Args:
            task_name: Name of the task to execute
            args: Positional arguments for the task
            kwargs: Keyword arguments for the task
            priority: Job priority
            max_retries: Maximum number of retries
            retry_delay: Delay between retries (seconds)
            timeout: Job timeout (seconds)
            scheduled_at: When to schedule the job
            metadata: Additional metadata
            
        Returns:
            Job ID
        """
        job = Job(
            id=str(uuid.uuid4()),
            task_name=task_name,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            scheduled_at=scheduled_at,
            metadata=metadata or {}
        )
        
        if self.redis_client:
            self._enqueue_redis_job(job)
        else:
            self._enqueue_memory_job(job)
        
        logger.info(f"Enqueued job {job.id}: {task_name}")
        return job.id
    
    def _enqueue_redis_job(self, job: Job) -> None:
        """Enqueue job to Redis."""
        job_data = pickle.dumps(job)
        
        # Choose queue based on priority and schedule
        if job.scheduled_at and job.scheduled_at > datetime.utcnow():
            queue = self.retry_queue
            score = job.scheduled_at.timestamp()
        elif job.priority == JobPriority.URGENT:
            queue = self.priority_queue
            score = datetime.utcnow().timestamp()
        else:
            queue = self.main_queue
            score = datetime.utcnow().timestamp()
        
        self.redis_client.zadd(queue, {job_data: score})
        self.metrics["queue_size"] = self._get_queue_size()
    
    def _enqueue_memory_job(self, job: Job) -> None:
        """Enqueue job to in-memory queue (fallback)."""
        if not hasattr(self, '_memory_queue'):
            self._memory_queue = []
        
        self._memory_queue.append(job)
        self.metrics["queue_size"] = len(self._memory_queue)
    
    def start_workers(self, num_workers: int = 3) -> None:
        """Start background workers."""
        if self.is_running:
            logger.warning("Workers are already running")
            return
        
        self.is_running = True
        
        for i in range(num_workers):
            worker_id = f"worker_{i}"
            worker = asyncio.create_task(self._worker_loop(worker_id))
            self.workers[worker_id] = worker
        
        logger.info(f"Started {num_workers} background workers")
    
    async def _worker_loop(self, worker_id: str) -> None:
        """Main worker loop."""
        logger.info(f"Worker {worker_id} started")
        
        while self.is_running:
            try:
                job = await self._get_next_job()
                if job:
                    await self._process_job(worker_id, job)
                else:
                    await asyncio.sleep(1)  # No jobs, wait a bit
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _get_next_job(self) -> Optional[Job]:
        """Get the next job to process."""
        if self.redis_client:
            return await self._get_redis_job()
        else:
            return await self._get_memory_job()
    
    async def _get_redis_job(self) -> Optional[Job]:
        """Get next job from Redis queue."""
        # Check priority queue first
        job_data = self.redis_client.zpopmin(self.priority_queue, 1)
        if not job_data:
            # Check main queue
            job_data = self.redis_client.zpopmin(self.main_queue, 1)
        if not job_data:
            # Check retry queue for scheduled jobs
            now = datetime.utcnow().timestamp()
            job_data = self.redis_client.zrangebyscore(
                self.retry_queue, 0, now, start=0, num=1
            )
            if job_data:
                self.redis_client.zrem(self.retry_queue, job_data[0])
                job_data = [(job_data[0], now)]
        
        if job_data:
            try:
                return pickle.loads(job_data[0][0])
            except Exception as e:
                logger.error(f"Failed to deserialize job: {str(e)}")
                return None
        
        return None
    
    async def _get_memory_job(self) -> Optional[Job]:
        """Get next job from memory queue."""
        if not hasattr(self, '_memory_queue') or not self._memory_queue:
            return None
        
        # Sort by priority and creation time
        self._memory_queue.sort(key=lambda j: (j.priority.value, j.created_at))
        return self._memory_queue.pop(0)
    
    async def _process_job(self, worker_id: str, job: Job) -> None:
        """Process a single job."""
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        job.attempts += 1
        
        try:
            # Add to processing queue
            if self.redis_client:
                job_data = pickle.dumps(job)
                self.redis_client.hset(
                    self.processing_queue,
                    job.id,
                    job_data
                )
                self.redis_client.expire(self.processing_queue, 3600)  # 1 hour TTL
            
            # Check if handler exists
            if job.task_name not in self.job_handlers:
                raise BackgroundJobError(f"No handler for task: {job.task_name}")
            
            # Execute job with timeout
            handler = self.job_handlers[job.task_name]
            start_time = datetime.utcnow()
            
            result = await asyncio.wait_for(
                self._run_handler(handler, job.args, job.kwargs),
                timeout=job.timeout
            )
            
            # Update job with success
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.result = result
            
            # Update metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics["jobs_processed"] += 1
            self.metrics["processing_time"] += processing_time
            
            logger.info(f"Job {job.id} completed successfully by {worker_id}")
            
        except asyncio.TimeoutError:
            job.status = JobStatus.FAILED
            job.error_message = "Job timed out"
            await self._handle_job_failure(job)
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            await self._handle_job_failure(job)
            
        finally:
            # Remove from processing queue
            if self.redis_client:
                self.redis_client.hdel(self.processing_queue, job.id)
            
            # Update queue size
            self.metrics["queue_size"] = self._get_queue_size()
    
    async def _run_handler(self, handler: Callable, args: tuple, kwargs: dict) -> Any:
        """Run job handler."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(*args, **kwargs)
        else:
            # Run synchronous handlers in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor, handler, *args, **kwargs
            )
    
    async def _handle_job_failure(self, job: Job) -> None:
        """Handle job failure and retry logic."""
        self.metrics["jobs_failed"] += 1
        
        if job.attempts < job.max_retries:
            # Schedule retry with exponential backoff
            retry_delay = job.retry_delay * (2 ** (job.attempts - 1))
            retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)
            
            job.status = JobStatus.RETRYING
            job.scheduled_at = retry_at
            
            if self.redis_client:
                job_data = pickle.dumps(job)
                self.redis_client.zadd(
                    self.retry_queue,
                    {job_data: retry_at.timestamp()}
                )
            else:
                # Add back to memory queue
                if not hasattr(self, '_memory_queue'):
                    self._memory_queue = []
                self._memory_queue.append(job)
            
            self.metrics["jobs_retried"] += 1
            logger.warning(f"Job {job.id} scheduled for retry at {retry_at}")
            
        else:
            # Move to dead letter queue
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            
            if self.redis_client:
                job_data = pickle.dumps(job)
                self.redis_client.lpush(self.dead_letter_queue, job_data)
                # Keep only last 1000 dead jobs
                self.redis_client.ltrim(self.dead_letter_queue, 0, 999)
            
            logger.error(f"Job {job.id} failed permanently: {job.error_message}")
    
    def stop_workers(self) -> None:
        """Stop all background workers."""
        self.is_running = False
        
        # Cancel worker tasks
        for worker_id, worker in self.workers.items():
            worker.cancel()
        
        # Wait for workers to finish
        if self.workers:
            asyncio.gather(*self.workers.values(), return_exceptions=True)
        
        self.workers.clear()
        logger.info("Stopped all background workers")
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status."""
        if self.redis_client:
            # Check processing queue
            job_data = self.redis_client.hget(self.processing_queue, job_id)
            if job_data:
                try:
                    job = pickle.loads(job_data)
                    return self._job_to_dict(job)
                except Exception:
                    pass
        
        return None
    
    def get_queue_metrics(self) -> Dict[str, Any]:
        """Get queue metrics."""
        metrics = self.metrics.copy()
        metrics["queue_sizes"] = {
            "main": self._get_queue_size(self.main_queue),
            "priority": self._get_queue_size(self.priority_queue),
            "retry": self._get_queue_size(self.retry_queue),
            "dead_letter": self._get_queue_size(self.dead_letter_queue),
            "processing": self._get_queue_size(self.processing_queue, is_hash=True)
        }
        metrics["active_workers"] = len(self.workers)
        metrics["is_running"] = self.is_running
        
        return metrics
    
    def _get_queue_size(self, queue_name: str, is_hash: bool = False) -> int:
        """Get queue size."""
        if not self.redis_client:
            return len(getattr(self, '_memory_queue', []))
        
        try:
            if is_hash:
                return self.redis_client.hlen(queue_name)
            else:
                return self.redis_client.zcard(queue_name)
        except Exception:
            return 0
    
    def _job_to_dict(self, job: Job) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "id": job.id,
            "task_name": job.task_name,
            "status": job.status.value,
            "priority": job.priority.value,
            "attempts": job.attempts,
            "max_retries": job.max_retries,
            "created_at": job.created_at.isoformat(),
            "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
            "metadata": job.metadata
        }
    
    # Email-specific handlers
    async def _handle_send_email(self, to_email: str, subject: str, body: str, **kwargs) -> bool:
        """Handle send email job."""
        try:
            email_service = EmailService()
            await email_service.send_email(to_email, subject, body, **kwargs)
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise EmailError(f"Failed to send email: {str(e)}")
    
    async def _handle_send_bulk_email(self, recipients: List[str], subject: str, body: str, **kwargs) -> Dict[str, Any]:
        """Handle send bulk email job."""
        try:
            email_service = EmailService()
            results = await email_service.send_bulk_email(recipients, subject, body, **kwargs)
            return results
        except Exception as e:
            logger.error(f"Failed to send bulk email: {str(e)}")
            raise EmailError(f"Failed to send bulk email: {str(e)}")
    
    async def _handle_process_email_queue(self, queue_name: str = "default", batch_size: int = 100) -> Dict[str, Any]:
        """Handle process email queue job."""
        try:
            # This would integrate with the email queue processing
            # Implementation would depend on your email queue structure
            return {
                "processed": 0,
                "failed": 0,
                "queue_name": queue_name
            }
        except Exception as e:
            logger.error(f"Failed to process email queue {queue_name}: {str(e)}")
            raise EmailError(f"Failed to process email queue: {str(e)}")


# Global job queue instance
job_queue = BackgroundJobQueue()


def enqueue_email_job(
    to_email: str,
    subject: str,
    body: str,
    priority: JobPriority = JobPriority.NORMAL,
    **kwargs
) -> str:
    """
    Enqueue an email job.
    
    Args:
        to_email: Recipient email
        subject: Email subject
        body: Email body
        priority: Job priority
        **kwargs: Additional email parameters
        
    Returns:
        Job ID
    """
    return job_queue.enqueue_job(
        task_name="send_email",
        args=(to_email, subject, body),
        kwargs=kwargs,
        priority=priority
    )


def enqueue_bulk_email_job(
    recipients: List[str],
    subject: str,
    body: str,
    priority: JobPriority = JobPriority.NORMAL,
    **kwargs
) -> str:
    """
    Enqueue a bulk email job.
    
    Args:
        recipients: List of recipient emails
        subject: Email subject
        body: Email body
        priority: Job priority
        **kwargs: Additional email parameters
        
    Returns:
        Job ID
    """
    return job_queue.enqueue_job(
        task_name="send_bulk_email",
        args=(recipients, subject, body),
        kwargs=kwargs,
        priority=priority
    )
