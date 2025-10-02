"""
Queue worker for processing document processing jobs.
Handles job execution and status updates.
"""

import time
import signal
import threading
from typing import Callable, Optional, Dict, Any
from loguru import logger

from .queue_manager import QueueManager, JobStatus, ProcessingJob


class QueueWorker:
    """Worker process for handling document processing jobs"""
    
    def __init__(self, queue_manager: QueueManager, 
                 processor_func: Callable[[ProcessingJob], Dict[str, Any]],
                 worker_id: str = None):
        self.queue_manager = queue_manager
        self.processor_func = processor_func
        self.worker_id = worker_id or f"worker_{int(time.time())}"
        self.running = False
        self.current_job = None
        self.thread = None
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Worker {self.worker_id} received shutdown signal")
        self.stop()
    
    def start(self, daemon: bool = True):
        """Start the worker in a separate thread"""
        if self.running:
            logger.warning(f"Worker {self.worker_id} is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_worker, daemon=daemon)
        self.thread.start()
        logger.info(f"Started worker {self.worker_id}")
    
    def stop(self):
        """Stop the worker gracefully"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=30)
        logger.info(f"Stopped worker {self.worker_id}")
    
    def _run_worker(self):
        """Main worker loop"""
        logger.info(f"Worker {self.worker_id} started processing")
        
        while self.running:
            try:
                # Get next job from queue
                job = self.queue_manager.dequeue_job(timeout=5)
                
                if job is None:
                    continue
                
                self.current_job = job
                logger.info(f"Worker {self.worker_id} processing job {job.job_id}")
                
                # Update job status to processing
                self.queue_manager.update_job_status(job.job_id, JobStatus.PROCESSING)
                
                try:
                    # Process the job
                    result = self.processor_func(job)
                    
                    # Store result and mark as completed
                    self.queue_manager.set_job_result(job.job_id, result)
                    self.queue_manager.update_job_status(job.job_id, JobStatus.COMPLETED)
                    
                    logger.info(f"Worker {self.worker_id} completed job {job.job_id}")
                
                except Exception as e:
                    # Handle processing errors
                    error_msg = f"Processing failed: {str(e)}"
                    logger.error(f"Worker {self.worker_id} job {job.job_id} failed: {error_msg}")
                    
                    self.queue_manager.update_job_status(
                        job.job_id, JobStatus.FAILED, error_msg
                    )
                
                finally:
                    self.current_job = None
            
            except Exception as e:
                logger.error(f"Worker {self.worker_id} encountered error: {e}")
                time.sleep(1)  # Brief pause before retrying
        
        logger.info(f"Worker {self.worker_id} stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get worker status information"""
        return {
            'worker_id': self.worker_id,
            'running': self.running,
            'current_job': self.current_job.job_id if self.current_job else None,
            'thread_alive': self.thread.is_alive() if self.thread else False
        }


class WorkerPool:
    """Manages multiple queue workers"""
    
    def __init__(self, queue_manager: QueueManager, 
                 processor_func: Callable[[ProcessingJob], Dict[str, Any]],
                 num_workers: int = 2):
        self.queue_manager = queue_manager
        self.processor_func = processor_func
        self.num_workers = num_workers
        self.workers = []
        self.running = False
    
    def start(self):
        """Start all workers in the pool"""
        if self.running:
            logger.warning("Worker pool is already running")
            return
        
        self.running = True
        
        for i in range(self.num_workers):
            worker = QueueWorker(
                self.queue_manager,
                self.processor_func,
                f"worker_{i+1}"
            )
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Started worker pool with {self.num_workers} workers")
    
    def stop(self):
        """Stop all workers in the pool"""
        self.running = False
        
        for worker in self.workers:
            worker.stop()
        
        self.workers.clear()
        logger.info("Stopped worker pool")
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get status of all workers in the pool"""
        return {
            'num_workers': len(self.workers),
            'running': self.running,
            'workers': [worker.get_status() for worker in self.workers]
        }
    
    def scale_workers(self, new_count: int):
        """Scale the number of workers up or down"""
        current_count = len(self.workers)
        
        if new_count > current_count:
            # Add workers
            for i in range(current_count, new_count):
                worker = QueueWorker(
                    self.queue_manager,
                    self.processor_func,
                    f"worker_{i+1}"
                )
                if self.running:
                    worker.start()
                self.workers.append(worker)
            
            logger.info(f"Scaled up to {new_count} workers")
        
        elif new_count < current_count:
            # Remove workers
            workers_to_remove = self.workers[new_count:]
            self.workers = self.workers[:new_count]
            
            for worker in workers_to_remove:
                worker.stop()
            
            logger.info(f"Scaled down to {new_count} workers")
        
        self.num_workers = new_count


def create_document_processor_func(unified_processor):
    """Create a processor function for document processing jobs"""
    
    def process_document_job(job: ProcessingJob) -> Dict[str, Any]:
        """Process a document processing job"""
        try:
            # Update progress
            queue_manager = QueueManager()  # This should be passed in properly
            queue_manager.update_job_progress(job.job_id, 10, "Starting document processing")
            
            # Process the document
            result = unified_processor.process_document(
                job.file_path,
                job.config.get('column_mappings', {}),
                progress_callback=lambda p, msg: queue_manager.update_job_progress(job.job_id, p, msg)
            )
            
            queue_manager.update_job_progress(job.job_id, 100, "Processing completed")
            
            return {
                'extracted_records': result.get('records', []),
                'quality_metrics': result.get('quality_metrics', {}),
                'flagged_records': result.get('flagged_records', []),
                'processing_metadata': result.get('metadata', {})
            }
        
        except Exception as e:
            logger.error(f"Document processing failed for job {job.job_id}: {e}")
            raise
    
    return process_document_job