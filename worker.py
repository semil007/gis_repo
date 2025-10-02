#!/usr/bin/env python3
"""
Worker entry point for document processing queue.
Starts queue workers to process documents in the background.
"""

import sys
import os
import time
import signal
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.queue_manager import QueueManager
from services.queue_worker import QueueWorker
from services.integration_manager import IntegrationManager
from loguru import logger

# Configure logging
logger.add(
    "logs/worker.log",
    rotation="100 MB",
    retention="30 days",
    level="INFO"
)


def process_job(job):
    """
    Process a document processing job.
    
    Args:
        job: ProcessingJob instance
        
    Returns:
        Dict with processing results
    """
    try:
        logger.info(f"Processing job {job.job_id} for session {job.session_id}")
        
        # Initialize integration manager
        integration_manager = IntegrationManager()
        
        # Process document
        import asyncio
        result = asyncio.run(
            integration_manager.processing_pipeline.process_document_async(
                file_path=job.file_path,
                session_id=job.session_id,
                options=job.config
            )
        )
        
        logger.info(f"Job {job.job_id} completed successfully")
        
        return {
            'status': 'completed',
            'result': result,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Job {job.job_id} failed: {str(e)}")
        
        return {
            'status': 'failed',
            'result': None,
            'error': str(e)
        }


def main():
    """Main worker entry point."""
    logger.info("Starting document processing worker...")
    
    try:
        # Initialize queue manager
        queue_manager = QueueManager()
        logger.info("Connected to Redis queue")
        
        # Get worker concurrency from environment
        worker_count = int(os.getenv('WORKER_CONCURRENCY', '2'))
        logger.info(f"Starting {worker_count} worker(s)")
        
        # Create workers
        workers = []
        for i in range(worker_count):
            worker = QueueWorker(
                queue_manager=queue_manager,
                processor_func=process_job,
                worker_id=f"worker_{i+1}"
            )
            workers.append(worker)
            
        # Start all workers
        for worker in workers:
            worker.start()
            logger.info(f"Started {worker.worker_id}")
            
        logger.info("All workers started successfully")
        logger.info("Press Ctrl+C to stop workers")
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
                
                # Check if any worker has stopped
                for worker in workers:
                    if not worker.running and worker.thread and not worker.thread.is_alive():
                        logger.warning(f"{worker.worker_id} has stopped, restarting...")
                        worker.start()
                        
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            
    except Exception as e:
        logger.error(f"Worker startup failed: {str(e)}")
        sys.exit(1)
        
    finally:
        # Stop all workers
        logger.info("Stopping workers...")
        for worker in workers:
            worker.stop()
            
        logger.info("All workers stopped")


if __name__ == "__main__":
    main()
