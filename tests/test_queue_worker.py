"""
Tests for queue worker system.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock

from services.queue_worker import QueueWorker, WorkerPool, create_document_processor_func
from services.queue_manager import QueueManager, ProcessingJob, JobStatus


@pytest.fixture
def mock_queue_manager():
    """Mock QueueManager for testing"""
    mock_qm = Mock(spec=QueueManager)
    return mock_qm


@pytest.fixture
def mock_processor_func():
    """Mock processor function for testing"""
    def mock_processor(job):
        # Simulate processing time
        time.sleep(0.1)
        return {
            'extracted_records': [{'field1': 'value1'}],
            'quality_metrics': {'accuracy': 0.95},
            'flagged_records': [],
            'processing_metadata': {'processing_time': 0.1}
        }
    
    return mock_processor


@pytest.fixture
def sample_job():
    """Create sample processing job"""
    return ProcessingJob(
        job_id="test_job_123",
        file_path="/path/to/test.pdf",
        session_id="session_456",
        config={"test": "config"}
    )


class TestQueueWorker:
    """Test QueueWorker class"""
    
    def test_worker_initialization(self, mock_queue_manager, mock_processor_func):
        """Test worker initialization"""
        worker = QueueWorker(mock_queue_manager, mock_processor_func, "test_worker")
        
        assert worker.queue_manager == mock_queue_manager
        assert worker.processor_func == mock_processor_func
        assert worker.worker_id == "test_worker"
        assert worker.running is False
        assert worker.current_job is None
    
    def test_worker_start_stop(self, mock_queue_manager, mock_processor_func):
        """Test starting and stopping worker"""
        worker = QueueWorker(mock_queue_manager, mock_processor_func)
        
        # Start worker
        worker.start()
        assert worker.running is True
        assert worker.thread is not None
        assert worker.thread.is_alive()
        
        # Stop worker
        worker.stop()
        assert worker.running is False
    
    def test_worker_process_job(self, mock_queue_manager, mock_processor_func, sample_job):
        """Test worker processing a job"""
        # Mock queue manager methods
        mock_queue_manager.dequeue_job.side_effect = [sample_job, None]  # Return job once, then None
        mock_queue_manager.update_job_status.return_value = True
        mock_queue_manager.set_job_result.return_value = True
        
        worker = QueueWorker(mock_queue_manager, mock_processor_func)
        
        # Start worker and let it process one job
        worker.start()
        time.sleep(0.2)  # Give worker time to process
        worker.stop()
        
        # Verify job processing calls
        mock_queue_manager.update_job_status.assert_any_call(sample_job.job_id, JobStatus.PROCESSING)
        mock_queue_manager.set_job_result.assert_called_once()
        mock_queue_manager.update_job_status.assert_any_call(sample_job.job_id, JobStatus.COMPLETED)
    
    def test_worker_handle_processing_error(self, mock_queue_manager, sample_job):
        """Test worker handling processing errors"""
        # Create processor that raises exception
        def error_processor(job):
            raise ValueError("Processing failed")
        
        mock_queue_manager.dequeue_job.side_effect = [sample_job, None]
        mock_queue_manager.update_job_status.return_value = True
        
        worker = QueueWorker(mock_queue_manager, error_processor)
        
        # Start worker and let it process
        worker.start()
        time.sleep(0.2)
        worker.stop()
        
        # Verify error handling
        mock_queue_manager.update_job_status.assert_any_call(sample_job.job_id, JobStatus.PROCESSING)
        mock_queue_manager.update_job_status.assert_any_call(
            sample_job.job_id, JobStatus.FAILED, "Processing failed: Processing failed"
        )
    
    def test_worker_timeout_handling(self, mock_queue_manager, mock_processor_func):
        """Test worker handling queue timeout"""
        # Mock dequeue to return None (timeout)
        mock_queue_manager.dequeue_job.return_value = None
        
        worker = QueueWorker(mock_queue_manager, mock_processor_func)
        
        # Start worker briefly
        worker.start()
        time.sleep(0.1)
        worker.stop()
        
        # Should handle timeout gracefully
        assert not worker.running
    
    def test_worker_get_status(self, mock_queue_manager, mock_processor_func, sample_job):
        """Test getting worker status"""
        worker = QueueWorker(mock_queue_manager, mock_processor_func, "status_test_worker")
        
        # Test initial status
        status = worker.get_status()
        assert status['worker_id'] == "status_test_worker"
        assert status['running'] is False
        assert status['current_job'] is None
        assert status['thread_alive'] is False
        
        # Start worker and test running status
        worker.start()
        status = worker.get_status()
        assert status['running'] is True
        assert status['thread_alive'] is True
        
        worker.stop()


class TestWorkerPool:
    """Test WorkerPool class"""
    
    def test_pool_initialization(self, mock_queue_manager, mock_processor_func):
        """Test worker pool initialization"""
        pool = WorkerPool(mock_queue_manager, mock_processor_func, num_workers=3)
        
        assert pool.queue_manager == mock_queue_manager
        assert pool.processor_func == mock_processor_func
        assert pool.num_workers == 3
        assert len(pool.workers) == 0
        assert pool.running is False
    
    def test_pool_start_stop(self, mock_queue_manager, mock_processor_func):
        """Test starting and stopping worker pool"""
        pool = WorkerPool(mock_queue_manager, mock_processor_func, num_workers=2)
        
        # Start pool
        pool.start()
        assert pool.running is True
        assert len(pool.workers) == 2
        assert all(worker.running for worker in pool.workers)
        
        # Stop pool
        pool.stop()
        assert pool.running is False
        assert len(pool.workers) == 0
    
    def test_pool_get_status(self, mock_queue_manager, mock_processor_func):
        """Test getting pool status"""
        pool = WorkerPool(mock_queue_manager, mock_processor_func, num_workers=2)
        
        # Test initial status
        status = pool.get_pool_status()
        assert status['num_workers'] == 0
        assert status['running'] is False
        assert len(status['workers']) == 0
        
        # Start pool and test running status
        pool.start()
        status = pool.get_pool_status()
        assert status['num_workers'] == 2
        assert status['running'] is True
        assert len(status['workers']) == 2
        
        pool.stop()
    
    def test_pool_scale_up(self, mock_queue_manager, mock_processor_func):
        """Test scaling worker pool up"""
        pool = WorkerPool(mock_queue_manager, mock_processor_func, num_workers=2)
        pool.start()
        
        initial_count = len(pool.workers)
        
        # Scale up
        pool.scale_workers(4)
        
        assert len(pool.workers) == 4
        assert pool.num_workers == 4
        assert all(worker.running for worker in pool.workers)
        
        pool.stop()
    
    def test_pool_scale_down(self, mock_queue_manager, mock_processor_func):
        """Test scaling worker pool down"""
        pool = WorkerPool(mock_queue_manager, mock_processor_func, num_workers=4)
        pool.start()
        
        # Scale down
        pool.scale_workers(2)
        
        assert len(pool.workers) == 2
        assert pool.num_workers == 2
        assert all(worker.running for worker in pool.workers)
        
        pool.stop()
    
    def test_pool_concurrent_processing(self, mock_queue_manager, mock_processor_func):
        """Test concurrent job processing with multiple workers"""
        jobs = [
            ProcessingJob(f"job_{i}", f"/path/file_{i}.pdf", f"session_{i}")
            for i in range(5)
        ]
        
        # Mock queue manager to return jobs
        mock_queue_manager.dequeue_job.side_effect = jobs + [None] * 10  # Jobs then timeouts
        mock_queue_manager.update_job_status.return_value = True
        mock_queue_manager.set_job_result.return_value = True
        
        pool = WorkerPool(mock_queue_manager, mock_processor_func, num_workers=3)
        
        # Start pool and let it process jobs
        pool.start()
        time.sleep(0.5)  # Give time for processing
        pool.stop()
        
        # Verify all jobs were processed
        assert mock_queue_manager.set_job_result.call_count == 5


class TestDocumentProcessorFunc:
    """Test document processor function creation"""
    
    def test_create_processor_func(self):
        """Test creating document processor function"""
        mock_unified_processor = Mock()
        mock_unified_processor.process_document.return_value = {
            'records': [{'field1': 'value1'}],
            'quality_metrics': {'accuracy': 0.95},
            'flagged_records': [],
            'metadata': {'processing_time': 0.1}
        }
        
        processor_func = create_document_processor_func(mock_unified_processor)
        
        # Test the created function
        job = ProcessingJob("job123", "/path/file.pdf", "session456", {"test": "config"})
        
        with patch('services.queue_worker.QueueManager') as mock_qm_class:
            mock_qm = Mock()
            mock_qm_class.return_value = mock_qm
            mock_qm.update_job_progress.return_value = True
            
            result = processor_func(job)
            
            # Verify processor was called correctly
            mock_unified_processor.process_document.assert_called_once_with(
                job.file_path,
                job.config.get('column_mappings', {}),
                progress_callback=mock_qm.update_job_progress
            )
            
            # Verify result format
            assert 'extracted_records' in result
            assert 'quality_metrics' in result
            assert 'flagged_records' in result
            assert 'processing_metadata' in result
    
    def test_processor_func_error_handling(self):
        """Test processor function error handling"""
        mock_unified_processor = Mock()
        mock_unified_processor.process_document.side_effect = Exception("Processing error")
        
        processor_func = create_document_processor_func(mock_unified_processor)
        job = ProcessingJob("job123", "/path/file.pdf", "session456")
        
        with patch('services.queue_worker.QueueManager'):
            with pytest.raises(Exception) as exc_info:
                processor_func(job)
            
            assert "Processing error" in str(exc_info.value)


class TestWorkerIntegration:
    """Integration tests for worker system"""
    
    def test_end_to_end_processing(self):
        """Test end-to-end job processing"""
        # Create real queue manager with mock Redis
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            # Mock Redis operations for job flow
            job_data = {
                'job_id': 'test_job',
                'file_path': '/path/test.pdf',
                'session_id': 'session123',
                'config': '{}',
                'status': 'pending',
                'created_at': '2024-01-01T00:00:00',
                'started_at': None,
                'completed_at': None,
                'progress': '0',
                'error_message': None,
                'result': None
            }
            
            mock_redis.brpop.side_effect = [('queue', 'test_job'), None]
            mock_redis.hgetall.return_value = job_data
            mock_redis.hset.return_value = True
            mock_redis.lpush.return_value = 1
            mock_redis.expire.return_value = True
            
            queue_manager = QueueManager()
            
            # Create processor function
            def test_processor(job):
                return {'result': 'success'}
            
            # Create and start worker
            worker = QueueWorker(queue_manager, test_processor)
            worker.start()
            
            # Let worker process
            time.sleep(0.2)
            worker.stop()
            
            # Verify Redis calls were made
            assert mock_redis.brpop.called
            assert mock_redis.hset.called
    
    def test_worker_resilience(self, mock_queue_manager):
        """Test worker resilience to errors"""
        error_count = 0
        
        def flaky_processor(job):
            nonlocal error_count
            error_count += 1
            if error_count <= 2:
                raise Exception(f"Error {error_count}")
            return {'result': 'success'}
        
        # Mock jobs with some errors
        jobs = [
            ProcessingJob("job1", "/path/file1.pdf", "session1"),
            ProcessingJob("job2", "/path/file2.pdf", "session2"),
            ProcessingJob("job3", "/path/file3.pdf", "session3"),
            None  # End processing
        ]
        
        mock_queue_manager.dequeue_job.side_effect = jobs
        mock_queue_manager.update_job_status.return_value = True
        mock_queue_manager.set_job_result.return_value = True
        
        worker = QueueWorker(mock_queue_manager, flaky_processor)
        
        # Start worker and let it process
        worker.start()
        time.sleep(0.3)
        worker.stop()
        
        # Worker should have handled errors and continued processing
        assert mock_queue_manager.update_job_status.call_count >= 6  # 3 jobs * 2 status updates each


if __name__ == "__main__":
    pytest.main([__file__])