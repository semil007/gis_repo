"""
Tests for Redis queue management system.
"""

import pytest
import time
import json
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from services.queue_manager import QueueManager, ProcessingJob, JobStatus


class TestProcessingJob:
    """Test ProcessingJob class"""
    
    def test_job_creation(self):
        """Test creating a new processing job"""
        job = ProcessingJob("job123", "/path/to/file.pdf", "session456")
        
        assert job.job_id == "job123"
        assert job.file_path == "/path/to/file.pdf"
        assert job.session_id == "session456"
        assert job.status == JobStatus.PENDING
        assert job.progress == 0
        assert job.config == {}
        assert isinstance(job.created_at, datetime)
    
    def test_job_to_dict(self):
        """Test converting job to dictionary"""
        config = {"column_mappings": {"col1": "field1"}}
        job = ProcessingJob("job123", "/path/to/file.pdf", "session456", config)
        
        job_dict = job.to_dict()
        
        assert job_dict['job_id'] == "job123"
        assert job_dict['file_path'] == "/path/to/file.pdf"
        assert job_dict['session_id'] == "session456"
        assert job_dict['config'] == config
        assert job_dict['status'] == JobStatus.PENDING.value
        assert 'created_at' in job_dict
    
    def test_job_from_dict(self):
        """Test creating job from dictionary"""
        job_data = {
            'job_id': 'job123',
            'file_path': '/path/to/file.pdf',
            'session_id': 'session456',
            'config': {'test': 'value'},
            'status': 'processing',
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'progress': 50,
            'error_message': None,
            'result': None
        }
        
        job = ProcessingJob.from_dict(job_data)
        
        assert job.job_id == 'job123'
        assert job.status == JobStatus.PROCESSING
        assert job.progress == 50
        assert job.config == {'test': 'value'}


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    with patch('redis.Redis') as mock_redis_class:
        mock_client = Mock()
        mock_redis_class.return_value = mock_client
        
        # Mock successful ping
        mock_client.ping.return_value = True
        
        yield mock_client


@pytest.fixture
def queue_manager(mock_redis):
    """Create QueueManager instance with mocked Redis"""
    return QueueManager()


class TestQueueManager:
    """Test QueueManager class"""
    
    def test_queue_manager_initialization(self, mock_redis):
        """Test QueueManager initialization"""
        qm = QueueManager(redis_host='localhost', redis_port=6379)
        
        mock_redis.ping.assert_called_once()
        assert qm.queue_name == 'document_processing'
        assert qm.job_prefix == 'document_processing:job:'
    
    def test_enqueue_job(self, queue_manager, mock_redis):
        """Test enqueuing a job"""
        # Mock Redis operations
        mock_redis.hset.return_value = True
        mock_redis.lpush.return_value = 1
        mock_redis.expire.return_value = True
        
        job_id = queue_manager.enqueue_job(
            "/path/to/file.pdf", 
            "session123", 
            {"test": "config"}
        )
        
        assert job_id is not None
        mock_redis.hset.assert_called_once()
        mock_redis.lpush.assert_called_once_with('document_processing', job_id)
        mock_redis.expire.assert_called_once()
    
    def test_dequeue_job(self, queue_manager, mock_redis):
        """Test dequeuing a job"""
        # Mock Redis brpop returning a job
        job_id = "test_job_123"
        mock_redis.brpop.return_value = ('document_processing', job_id)
        
        # Mock hgetall for job data
        job_data = {
            'job_id': job_id,
            'file_path': '/path/to/file.pdf',
            'session_id': 'session123',
            'config': '{}',
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'progress': '0',
            'error_message': None,
            'result': None
        }
        mock_redis.hgetall.return_value = job_data
        
        job = queue_manager.dequeue_job(timeout=5)
        
        assert job is not None
        assert job.job_id == job_id
        mock_redis.brpop.assert_called_once_with('document_processing', timeout=5)
    
    def test_dequeue_job_timeout(self, queue_manager, mock_redis):
        """Test dequeue timeout"""
        mock_redis.brpop.return_value = None
        
        job = queue_manager.dequeue_job(timeout=1)
        
        assert job is None
    
    def test_get_job(self, queue_manager, mock_redis):
        """Test getting job by ID"""
        job_id = "test_job_123"
        job_data = {
            'job_id': job_id,
            'file_path': '/path/to/file.pdf',
            'session_id': 'session123',
            'config': '{"test": "value"}',
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'progress': '0',
            'error_message': None,
            'result': None
        }
        mock_redis.hgetall.return_value = job_data
        
        job = queue_manager.get_job(job_id)
        
        assert job is not None
        assert job.job_id == job_id
        assert job.config == {"test": "value"}
        mock_redis.hgetall.assert_called_once_with(f'document_processing:job:{job_id}')
    
    def test_get_nonexistent_job(self, queue_manager, mock_redis):
        """Test getting non-existent job"""
        mock_redis.hgetall.return_value = {}
        
        job = queue_manager.get_job("nonexistent")
        
        assert job is None
    
    def test_update_job_status(self, queue_manager, mock_redis):
        """Test updating job status"""
        mock_redis.hset.return_value = True
        
        success = queue_manager.update_job_status("job123", JobStatus.PROCESSING)
        
        assert success is True
        mock_redis.hset.assert_called_once()
        
        # Check the call arguments
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == 'document_processing:job:job123'
        assert 'status' in call_args[1]['mapping']
        assert call_args[1]['mapping']['status'] == 'processing'
    
    def test_update_job_progress(self, queue_manager, mock_redis):
        """Test updating job progress"""
        mock_redis.hset.return_value = True
        
        success = queue_manager.update_job_progress("job123", 75, "Processing data")
        
        assert success is True
        mock_redis.hset.assert_called_once()
        
        call_args = mock_redis.hset.call_args
        assert call_args[1]['mapping']['progress'] == 75
        assert call_args[1]['mapping']['progress_message'] == "Processing data"
    
    def test_set_job_result(self, queue_manager, mock_redis):
        """Test setting job result"""
        mock_redis.hset.return_value = True
        
        result = {"records": [{"field1": "value1"}]}
        success = queue_manager.set_job_result("job123", result)
        
        assert success is True
        mock_redis.hset.assert_called_once_with(
            'document_processing:job:job123',
            'result',
            json.dumps(result)
        )
    
    def test_get_queue_length(self, queue_manager, mock_redis):
        """Test getting queue length"""
        mock_redis.llen.return_value = 5
        
        length = queue_manager.get_queue_length()
        
        assert length == 5
        mock_redis.llen.assert_called_once_with('document_processing')
    
    def test_cancel_job(self, queue_manager, mock_redis):
        """Test canceling a pending job"""
        # Mock job data for pending job
        job_data = {
            'job_id': 'job123',
            'file_path': '/path/to/file.pdf',
            'session_id': 'session123',
            'config': '{}',
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'progress': '0',
            'error_message': None,
            'result': None
        }
        mock_redis.hgetall.return_value = job_data
        mock_redis.lrem.return_value = 1
        mock_redis.hset.return_value = True
        
        success = queue_manager.cancel_job("job123")
        
        assert success is True
        mock_redis.lrem.assert_called_once_with('document_processing', 0, 'job123')
    
    def test_cleanup_old_jobs(self, queue_manager, mock_redis):
        """Test cleaning up old jobs"""
        # Mock scan_iter to return some job keys
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        mock_redis.scan_iter.return_value = [
            'document_processing:job:old_job1',
            'document_processing:job:old_job2'
        ]
        
        # Mock job data with old timestamps
        mock_redis.hgetall.side_effect = [
            {'created_at': old_time},
            {'created_at': old_time}
        ]
        mock_redis.delete.return_value = True
        
        cleaned_count = queue_manager.cleanup_old_jobs(max_age_hours=24)
        
        assert cleaned_count == 2
        assert mock_redis.delete.call_count == 2
    
    def test_get_queue_stats(self, queue_manager, mock_redis):
        """Test getting queue statistics"""
        mock_redis.llen.return_value = 3
        mock_redis.scan_iter.return_value = [
            'document_processing:job:job1',
            'document_processing:job:job2'
        ]
        mock_redis.hgetall.side_effect = [
            {'status': 'pending'},
            {'status': 'completed'}
        ]
        
        stats = queue_manager.get_queue_stats()
        
        assert stats['queue_length'] == 3
        assert stats['total_jobs'] == 2
        assert stats['status_counts']['pending'] == 1
        assert stats['status_counts']['completed'] == 1


if __name__ == "__main__":
    pytest.main([__file__])