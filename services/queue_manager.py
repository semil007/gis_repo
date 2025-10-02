"""
Redis-based queue management system for document processing pipeline.
Handles job queuing, worker management, and status tracking.
"""

import json
import uuid
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from urllib.parse import urlparse
import redis
from loguru import logger


class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingJob:
    """Represents a document processing job"""
    
    def __init__(self, job_id: str, file_path: str, session_id: str, 
                 config: Dict[str, Any] = None):
        self.job_id = job_id
        self.file_path = file_path
        self.session_id = session_id
        self.config = config or {}
        self.status = JobStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.progress = 0
        self.error_message = None
        self.result = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for Redis storage"""
        return {
            'job_id': self.job_id,
            'file_path': self.file_path,
            'session_id': self.session_id,
            'config': self.config,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress': self.progress,
            'error_message': self.error_message,
            'result': self.result
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingJob':
        """Create job from dictionary"""
        job = cls(
            job_id=data['job_id'],
            file_path=data['file_path'],
            session_id=data['session_id'],
            config=data.get('config', {})
        )
        job.status = JobStatus(data['status'])
        job.created_at = datetime.fromisoformat(data['created_at'])
        job.started_at = datetime.fromisoformat(data['started_at']) if data['started_at'] else None
        job.completed_at = datetime.fromisoformat(data['completed_at']) if data['completed_at'] else None
        job.progress = data.get('progress', 0)
        job.error_message = data.get('error_message')
        job.result = data.get('result')
        return job


class QueueManager:
    """Redis-based queue manager for processing jobs"""
    
    def __init__(self, redis_url: str = None, queue_name: str = 'document_processing'):
        """
        Initialize Queue Manager with Redis connection.
        
        Args:
            redis_url: Redis connection URL (e.g., redis://host:port/db)
                      If None, reads from REDIS_URL environment variable
            queue_name: Name of the processing queue
        """
        # Get Redis configuration from environment or parameters
        redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        redis_password = os.getenv('REDIS_PASSWORD', '')
        
        # Parse Redis URL
        try:
            parsed = urlparse(redis_url)
            redis_host = parsed.hostname or 'localhost'
            redis_port = parsed.port or 6379
            redis_db = int(parsed.path.lstrip('/')) if parsed.path else 0
            
            # Create Redis client with password if provided
            redis_kwargs = {
                'host': redis_host,
                'port': redis_port,
                'db': redis_db,
                'decode_responses': True,
                'socket_connect_timeout': 5,
                'socket_timeout': 5
            }
            
            # Add password if provided
            if redis_password:
                redis_kwargs['password'] = redis_password
                
            self.redis_client = redis.Redis(**redis_kwargs)
            
        except Exception as e:
            logger.error(f"Failed to parse Redis URL: {e}")
            raise ValueError(f"Invalid Redis URL: {redis_url}")
            
        self.queue_name = queue_name
        self.job_prefix = f"{queue_name}:job:"
        self.status_prefix = f"{queue_name}:status:"
        self.progress_prefix = f"{queue_name}:progress:"
        
        # Test Redis connection
        try:
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {redis_host}:{redis_port} (DB: {redis_db})")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis at {redis_host}:{redis_port}: {e}")
            logger.error("Please check your Redis configuration in .env file")
            raise
        except redis.AuthenticationError as e:
            logger.error(f"Redis authentication failed: {e}")
            logger.error("Please check REDIS_PASSWORD in .env file")
            raise
    
    def enqueue_job(self, file_path: str, session_id: str, 
                   config: Dict[str, Any] = None) -> str:
        """Add a new job to the processing queue"""
        job_id = str(uuid.uuid4())
        job = ProcessingJob(job_id, file_path, session_id, config)
        
        # Store job data
        job_key = f"{self.job_prefix}{job_id}"
        self.redis_client.hset(job_key, mapping=job.to_dict())
        
        # Add to processing queue
        self.redis_client.lpush(self.queue_name, job_id)
        
        # Set job expiration (24 hours)
        self.redis_client.expire(job_key, 86400)
        
        logger.info(f"Enqueued job {job_id} for file {file_path}")
        return job_id
    
    def dequeue_job(self, timeout: int = 10) -> Optional[ProcessingJob]:
        """Get the next job from the queue (blocking)"""
        try:
            result = self.redis_client.brpop(self.queue_name, timeout=timeout)
            if result:
                _, job_id = result
                return self.get_job(job_id)
            return None
        except redis.RedisError as e:
            logger.error(f"Error dequeuing job: {e}")
            return None
    
    def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Retrieve job details by ID"""
        job_key = f"{self.job_prefix}{job_id}"
        job_data = self.redis_client.hgetall(job_key)
        
        if not job_data:
            return None
        
        # Convert string values back to appropriate types
        if 'config' in job_data and job_data['config']:
            job_data['config'] = json.loads(job_data['config']) if isinstance(job_data['config'], str) else job_data['config']
        
        return ProcessingJob.from_dict(job_data)
    
    def update_job_status(self, job_id: str, status: JobStatus, 
                         error_message: str = None) -> bool:
        """Update job status"""
        job_key = f"{self.job_prefix}{job_id}"
        
        updates = {'status': status.value}
        
        if status == JobStatus.PROCESSING:
            updates['started_at'] = datetime.now().isoformat()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            updates['completed_at'] = datetime.now().isoformat()
        
        if error_message:
            updates['error_message'] = error_message
        
        try:
            self.redis_client.hset(job_key, mapping=updates)
            logger.info(f"Updated job {job_id} status to {status.value}")
            return True
        except redis.RedisError as e:
            logger.error(f"Error updating job status: {e}")
            return False
    
    def update_job_progress(self, job_id: str, progress: int, 
                           message: str = None) -> bool:
        """Update job progress (0-100)"""
        job_key = f"{self.job_prefix}{job_id}"
        
        updates = {'progress': min(100, max(0, progress))}
        if message:
            updates['progress_message'] = message
        
        try:
            self.redis_client.hset(job_key, mapping=updates)
            return True
        except redis.RedisError as e:
            logger.error(f"Error updating job progress: {e}")
            return False
    
    def set_job_result(self, job_id: str, result: Dict[str, Any]) -> bool:
        """Set job result data"""
        job_key = f"{self.job_prefix}{job_id}"
        
        try:
            self.redis_client.hset(job_key, 'result', json.dumps(result))
            return True
        except redis.RedisError as e:
            logger.error(f"Error setting job result: {e}")
            return False
    
    def get_queue_length(self) -> int:
        """Get number of jobs in queue"""
        return self.redis_client.llen(self.queue_name)
    
    def get_jobs_by_session(self, session_id: str) -> List[ProcessingJob]:
        """Get all jobs for a specific session"""
        jobs = []
        
        # Scan for job keys
        for key in self.redis_client.scan_iter(match=f"{self.job_prefix}*"):
            job_data = self.redis_client.hgetall(key)
            if job_data.get('session_id') == session_id:
                if 'config' in job_data and job_data['config']:
                    job_data['config'] = json.loads(job_data['config']) if isinstance(job_data['config'], str) else job_data['config']
                jobs.append(ProcessingJob.from_dict(job_data))
        
        return sorted(jobs, key=lambda x: x.created_at)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        job = self.get_job(job_id)
        if not job:
            return False
        
        if job.status == JobStatus.PENDING:
            # Remove from queue
            self.redis_client.lrem(self.queue_name, 0, job_id)
            # Update status
            return self.update_job_status(job_id, JobStatus.CANCELLED)
        
        return False
    
    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up jobs older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        for key in self.redis_client.scan_iter(match=f"{self.job_prefix}*"):
            job_data = self.redis_client.hgetall(key)
            if job_data.get('created_at'):
                created_at = datetime.fromisoformat(job_data['created_at'])
                if created_at < cutoff_time:
                    self.redis_client.delete(key)
                    cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} old jobs")
        return cleaned_count
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        stats = {
            'queue_length': self.get_queue_length(),
            'total_jobs': 0,
            'status_counts': {status.value: 0 for status in JobStatus}
        }
        
        # Count jobs by status
        for key in self.redis_client.scan_iter(match=f"{self.job_prefix}*"):
            job_data = self.redis_client.hgetall(key)
            if job_data.get('status'):
                stats['total_jobs'] += 1
                stats['status_counts'][job_data['status']] += 1
        
        return stats