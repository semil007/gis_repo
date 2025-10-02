"""
Integration tests for queue and storage systems.
Tests the interaction between Redis queue management and SQLite session storage.
"""

import pytest
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from services.queue_manager import QueueManager, ProcessingJob, JobStatus
from services.queue_worker import QueueWorker, WorkerPool
from services.session_manager import SessionManager
from services.file_storage import FileStorageManager
from models.hmo_record import HMORecord


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    with patch('redis.Redis') as mock_redis_class:
        mock_client = Mock()
        mock_redis_class.return_value = mock_client
        mock_client.ping.return_value = True
        yield mock_client


@pytest.fixture
def queue_manager(mock_redis):
    """Create QueueManager with mocked Redis"""
    return QueueManager()


@pytest.fixture
def session_manager(temp_db):
    """Create SessionManager with temporary database"""
    return SessionManager(db_path=temp_db)


@pytest.fixture
def file_storage(temp_storage):
    """Create FileStorageManager with temporary directory"""
    return FileStorageManager(
        storage_root=str(temp_storage / "storage"),
        temp_dir=str(temp_storage / "temp"),
        max_storage_gb=0.1,  # 100MB for testing
        cleanup_age_hours=1
    )


class TestQueueStorageIntegration:
    """Test integration between queue and storage systems"""
    
    def test_job_lifecycle_with_session_storage(self, queue_manager, session_manager, mock_redis):
        """Test complete job lifecycle with session persistence"""
        # Mock Redis operations
        mock_redis.hset.return_value = True
        mock_redis.lpush.return_value = 1
        mock_redis.expire.return_value = True
        
        # Create session in storage
        session_id = session_manager.create_session(
            file_name="test_document.pdf",
            file_size=1024000,
            column_mappings={"Council": "council"},
            processing_config={"confidence_threshold": 0.7}
        )
        
        # Enqueue job
        returned_job_id = queue_manager.enqueue_job(
            file_path="/path/to/test_document.pdf",
            session_id=session_id,
            config={"column_mappings": {"Council": "council"}}
        )
        
        assert returned_job_id is not None
        assert len(returned_job_id) == 36  # UUID length
        
        # Verify session exists
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_name FROM processing_sessions WHERE session_id = ?", (session_id,))
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == "test_document.pdf"
        
        # Update session status through processing
        session_manager.update_session_status(session_id, "processing")
        
        # Simulate job completion
        queue_manager.update_job_status(returned_job_id, JobStatus.COMPLETED)
        session_manager.update_session_status(session_id, "completed", quality_score=0.85)
        
        # Verify final state
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT processing_status, quality_score FROM processing_sessions WHERE session_id = ?", (session_id,))
            result = cursor.fetchone()
            assert result[0] == "completed"
            assert result[1] == 0.85
    
    def test_concurrent_job_processing_with_storage(self, queue_manager, session_manager, mock_redis):
        """Test concurrent job processing with session storage"""
        # Create multiple sessions
        session_ids = []
        for i in range(3):
            session_id = session_manager.create_session(
                file_name=f"document_{i}.pdf",
                file_size=1000000 + i * 100000
            )
            session_ids.append(session_id)
        
        # Mock Redis for multiple jobs
        job_ids = [f"job_{i}" for i in range(3)]
        mock_redis.hset.return_value = True
        mock_redis.lpush.return_value = 1
        mock_redis.expire.return_value = True
        
        # Enqueue jobs
        for i, session_id in enumerate(session_ids):
            queue_manager.enqueue_job(
                file_path=f"/path/document_{i}.pdf",
                session_id=session_id
            )
        
        # Simulate concurrent processing
        def process_session(session_id, status):
            session_manager.update_session_status(session_id, status)
        
        threads = []
        for i, session_id in enumerate(session_ids):
            status = "completed" if i % 2 == 0 else "failed"
            thread = threading.Thread(target=process_session, args=(session_id, status))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all sessions were processed
        for i, session_id in enumerate(session_ids):
            with session_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT processing_status FROM processing_sessions WHERE session_id = ?", (session_id,))
                result = cursor.fetchone()
                expected_status = "completed" if i % 2 == 0 else "failed"
                assert result[0] == expected_status
    
    def test_job_failure_handling_with_storage(self, queue_manager, session_manager, mock_redis):
        """Test job failure handling with proper storage updates"""
        # Create session
        session_id = session_manager.create_session("failing_document.pdf", 500000)
        
        # Mock Redis operations
        job_id = "failing_job"
        mock_redis.hset.return_value = True
        mock_redis.lpush.return_value = 1
        mock_redis.expire.return_value = True
        
        # Enqueue job
        queue_manager.enqueue_job("/path/failing_document.pdf", session_id)
        
        # Simulate job failure
        error_message = "Document processing failed: Invalid format"
        queue_manager.update_job_status(job_id, JobStatus.FAILED, error_message)
        session_manager.update_session_status(session_id, "failed")
        
        # Verify failure is recorded
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT processing_status FROM processing_sessions WHERE session_id = ?", (session_id,))
            result = cursor.fetchone()
            assert result[0] == "failed"
    
    def test_file_storage_with_queue_processing(self, queue_manager, file_storage, mock_redis):
        """Test file storage operations during queue processing"""
        # Create test file
        test_content = b'%PDF-1.4\nTest PDF content'
        temp_file = file_storage.temp_dir.parent / "test_input.pdf"
        temp_file.write_bytes(test_content)
        
        # Store uploaded file
        success, message, stored_path = file_storage.store_uploaded_file(
            temp_file,
            "session_123",
            "original_document.pdf"
        )
        
        assert success is True
        assert stored_path is not None
        
        # Mock Redis operations
        mock_redis.hset.return_value = True
        mock_redis.lpush.return_value = 1
        mock_redis.expire.return_value = True
        
        # Enqueue job with stored file path
        job_id = queue_manager.enqueue_job(
            file_path=stored_path,
            session_id="session_123"
        )
        
        # Simulate processing result storage
        result_data = b"council,reference,address\nTest Council,REF123,123 Test St"
        success, message, result_path = file_storage.store_processed_result(
            "session_123",
            result_data,
            "processed_results.csv"
        )
        
        assert success is True
        assert result_path is not None
        
        # Verify files exist
        assert Path(stored_path).exists()
        assert Path(result_path).exists()
    
    def test_storage_cleanup_with_active_jobs(self, queue_manager, session_manager, file_storage, mock_redis):
        """Test storage cleanup while jobs are active"""
        # Create old session and files
        old_session_id = session_manager.create_session("old_document.pdf", 100000)
        
        # Create old temp files
        old_temp_file = file_storage.create_temp_file("old_session", ".tmp")
        old_temp_file.write_text("old temporary data")
        
        # Set old modification time
        import os
        old_time = (datetime.now() - timedelta(hours=2)).timestamp()
        os.utime(old_temp_file, (old_time, old_time))
        
        # Create active session and job
        active_session_id = session_manager.create_session("active_document.pdf", 200000)
        
        # Mock Redis for active job
        mock_redis.hset.return_value = True
        mock_redis.lpush.return_value = 1
        mock_redis.expire.return_value = True
        
        queue_manager.enqueue_job("/path/active_document.pdf", active_session_id)
        
        # Run cleanup
        cleanup_stats = file_storage.cleanup_old_files()
        old_sessions_cleaned = session_manager.cleanup_old_sessions(max_age_days=1)
        
        # Verify cleanup results
        assert cleanup_stats['temp_files'] >= 1
        assert not old_temp_file.exists()
        
        # Active session should remain
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM processing_sessions WHERE session_id = ?", (active_session_id,))
            result = cursor.fetchone()
            assert result is not None


class TestQueueWorkerWithStorage:
    """Test queue worker integration with storage systems"""
    
    def test_worker_with_session_updates(self, queue_manager, session_manager, mock_redis):
        """Test worker updating session status during processing"""
        # Create session
        session_id = session_manager.create_session("worker_test.pdf", 150000)
        
        # Create job
        job = ProcessingJob("worker_job", "/path/worker_test.pdf", session_id)
        
        # Mock Redis operations
        mock_redis.brpop.side_effect = [('queue', 'worker_job'), None]
        mock_redis.hgetall.return_value = {
            'job_id': 'worker_job',
            'file_path': '/path/worker_test.pdf',
            'session_id': session_id,
            'config': '{}',
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'progress': '0',
            'error_message': None,
            'result': None
        }
        mock_redis.hset.return_value = True
        
        # Create processor that updates session
        def processor_with_session_update(job):
            session_manager.update_session_status(job.session_id, "processing")
            
            # Simulate processing
            time.sleep(0.1)
            
            # Update session to completed (skip record storage for this test)
            session_manager.update_session_status(job.session_id, "completed", 0.9)
            
            return {
                'extracted_records': [],
                'quality_metrics': {'accuracy': 0.9}
            }
        
        # Create and run worker
        worker = QueueWorker(queue_manager, processor_with_session_update)
        worker.start()
        time.sleep(0.2)
        worker.stop()
        
        # Verify session was updated
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT processing_status, quality_score FROM processing_sessions WHERE session_id = ?", (session_id,))
            result = cursor.fetchone()
            assert result[0] == "completed"
            assert result[1] == 0.9
    
    def test_worker_pool_with_file_storage(self, queue_manager, file_storage, mock_redis):
        """Test worker pool with file storage operations"""
        # Create test files
        test_files = []
        for i in range(3):
            test_file = file_storage.temp_dir.parent / f"test_{i}.pdf"
            test_file.write_bytes(b'%PDF-1.4\nTest content ' + str(i).encode())
            
            success, _, stored_path = file_storage.store_uploaded_file(
                test_file, f"session_{i}", f"document_{i}.pdf"
            )
            assert success
            test_files.append(stored_path)
        
        # Mock Redis for multiple jobs
        job_data_list = []
        for i in range(3):
            job_data = {
                'job_id': f'pool_job_{i}',
                'file_path': test_files[i],
                'session_id': f'session_{i}',
                'config': '{}',
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'started_at': None,
                'completed_at': None,
                'progress': '0',
                'error_message': None,
                'result': None
            }
            job_data_list.append(job_data)
        
        mock_redis.brpop.side_effect = [
            ('queue', 'pool_job_0'),
            ('queue', 'pool_job_1'),
            ('queue', 'pool_job_2')
        ] + [None] * 10
        
        mock_redis.hgetall.side_effect = job_data_list
        mock_redis.hset.return_value = True
        
        # Create processor that uses file storage
        def processor_with_file_ops(job):
            # Read input file
            file_info = file_storage.get_file_info(job.file_path)
            assert file_info is not None
            
            # Create result file
            result_data = f"Processed: {job.session_id}"
            success, _, result_path = file_storage.create_export_file(
                job.session_id, result_data, "result.csv"
            )
            assert success
            
            return {'result_path': result_path}
        
        # Create and run worker pool
        pool = WorkerPool(queue_manager, processor_with_file_ops, num_workers=2)
        pool.start()
        time.sleep(0.5)
        pool.stop()
        
        # Verify result files were created
        export_dir = file_storage.storage_root / "exports"
        result_files = list(export_dir.glob("*.csv"))
        assert len(result_files) >= 3


class TestStorageSystemResilience:
    """Test storage system resilience and error handling"""
    
    def test_database_connection_recovery(self, temp_db):
        """Test database connection recovery after failure"""
        session_manager = SessionManager(db_path=temp_db)
        
        # Create initial session
        session_id = session_manager.create_session("test.pdf", 100000)
        assert session_id is not None
        
        # Simulate database lock by opening another connection
        import sqlite3
        blocking_conn = sqlite3.connect(temp_db)
        blocking_conn.execute("BEGIN EXCLUSIVE")
        
        try:
            # This should handle the lock gracefully
            with pytest.raises(Exception):
                session_manager.create_session("blocked.pdf", 200000)
        finally:
            blocking_conn.close()
        
        # Should recover and work normally
        recovery_session_id = session_manager.create_session("recovery.pdf", 300000)
        assert recovery_session_id is not None
    
    def test_file_storage_disk_full_simulation(self, file_storage):
        """Test file storage behavior when disk is full"""
        # Set very small quota
        file_storage.max_storage_bytes = 1024  # 1KB
        
        # Try to store large file
        large_content = b'%PDF-1.4\n' + b'x' * 2048  # 2KB
        temp_file = file_storage.temp_dir.parent / "large.pdf"
        temp_file.write_bytes(large_content)
        
        success, message, _ = file_storage.store_uploaded_file(
            temp_file, "session_full", "large.pdf"
        )
        
        assert success is False
        assert "quota exceeded" in message.lower()
    
    def test_concurrent_storage_operations(self, session_manager, file_storage):
        """Test concurrent storage operations"""
        import threading
        
        results = []
        errors = []
        
        def storage_worker(worker_id):
            try:
                # Session operations
                session_id = session_manager.create_session(
                    f"concurrent_{worker_id}.pdf", 100000 + worker_id
                )
                
                # File operations
                temp_file = file_storage.create_temp_file(f"worker_{worker_id}", ".tmp")
                temp_file.write_text(f"Worker {worker_id} data")
                
                # Store result
                result_data = f"Result from worker {worker_id}"
                success, _, _ = file_storage.create_export_file(
                    session_id, result_data, f"worker_{worker_id}.csv"
                )
                
                results.append((worker_id, session_id, success))
                
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Create multiple concurrent workers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=storage_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(results) == 5
        assert len(errors) == 0
        assert all(success for _, _, success in results)
    
    def test_storage_cleanup_under_load(self, session_manager, file_storage):
        """Test storage cleanup while system is under load"""
        # Create many sessions and files
        session_ids = []
        temp_files = []
        
        for i in range(10):
            session_id = session_manager.create_session(f"load_test_{i}.pdf", 50000)
            session_ids.append(session_id)
            
            temp_file = file_storage.create_temp_file(f"load_{i}", ".tmp")
            temp_file.write_text(f"Load test data {i}")
            temp_files.append(temp_file)
        
        # Make some files old
        import os
        old_time = (datetime.now() - timedelta(hours=2)).timestamp()
        for i in range(0, 5):  # First 5 files are old
            os.utime(temp_files[i], (old_time, old_time))
        
        # Run cleanup while creating more files
        def create_more_files():
            for i in range(5):
                new_file = file_storage.create_temp_file(f"during_cleanup_{i}", ".tmp")
                new_file.write_text(f"Created during cleanup {i}")
        
        cleanup_thread = threading.Thread(target=file_storage.cleanup_old_files)
        create_thread = threading.Thread(target=create_more_files)
        
        cleanup_thread.start()
        create_thread.start()
        
        cleanup_thread.join()
        create_thread.join()
        
        # Verify cleanup worked and new files weren't affected
        remaining_files = list(file_storage.temp_dir.glob("*.tmp"))
        assert len(remaining_files) >= 10  # 5 new + 5 not old + 5 created during cleanup


if __name__ == "__main__":
    pytest.main([__file__, "-v"])