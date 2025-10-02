"""
Tests for SQLite session management system.
"""

import pytest
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path

from services.session_manager import SessionManager
from models.hmo_record import HMORecord
from models.processing_session import ProcessingSession


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def session_manager(temp_db):
    """Create SessionManager instance with temporary database"""
    return SessionManager(db_path=temp_db)


@pytest.fixture
def sample_hmo_record():
    """Create sample HMO record for testing"""
    record = HMORecord()
    record.council = "Test Council"
    record.reference = "HMO123"
    record.hmo_address = "123 Test Street, Test City"
    record.licence_start = "2024-01-01"
    record.licence_expiry = "2025-01-01"
    record.max_occupancy = 5
    record.confidence_scores = {
        "council": 0.95,
        "reference": 0.90,
        "hmo_address": 0.85
    }
    return record


class TestSessionManager:
    """Test SessionManager class"""
    
    def test_database_initialization(self, session_manager):
        """Test database initialization creates required tables"""
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('processing_sessions', 'extracted_records', 'column_mappings')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'processing_sessions' in tables
            assert 'extracted_records' in tables
            assert 'column_mappings' in tables
    
    def test_create_session(self, session_manager):
        """Test creating a new processing session"""
        column_mappings = {"Council": "council", "Reference": "reference"}
        processing_config = {"confidence_threshold": 0.7}
        
        session_id = session_manager.create_session(
            file_name="test_file.pdf",
            file_size=1024000,
            column_mappings=column_mappings,
            processing_config=processing_config
        )
        
        assert session_id is not None
        assert len(session_id) == 36  # UUID length
        
        # Verify session was stored
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_name, file_size, column_mappings, processing_config 
                FROM processing_sessions WHERE session_id = ?
            """, (session_id,))
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == "test_file.pdf"
            assert result[1] == 1024000
            
            import json
            stored_mappings = json.loads(result[2]) if result[2] else {}
            stored_config = json.loads(result[3]) if result[3] else {}
            assert stored_mappings == column_mappings
            assert stored_config == processing_config
    
    def test_get_nonexistent_session(self, session_manager):
        """Test getting non-existent session returns None"""
        session = session_manager.get_session("nonexistent-id")
        assert session is None
    
    def test_update_session_status(self, session_manager):
        """Test updating session status"""
        session_id = session_manager.create_session("test.pdf", 1000)
        
        success = session_manager.update_session_status(
            session_id, 
            "completed", 
            quality_score=0.85
        )
        
        assert success is True
        
        # Verify update
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT processing_status, quality_score 
                FROM processing_sessions WHERE session_id = ?
            """, (session_id,))
            result = cursor.fetchone()
            assert result[0] == "completed"
            assert result[1] == 0.85
    
    def test_update_session_metrics(self, session_manager):
        """Test updating session record metrics"""
        session_id = session_manager.create_session("test.pdf", 1000)
        
        success = session_manager.update_session_metrics(
            session_id, 
            total_records=10, 
            flagged_records=2
        )
        
        assert success is True
        
        # Verify update
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT total_records, flagged_records 
                FROM processing_sessions WHERE session_id = ?
            """, (session_id,))
            result = cursor.fetchone()
            assert result[0] == 10
            assert result[1] == 2
    
    def test_store_extracted_records(self, session_manager, sample_hmo_record):
        """Test storing extracted records"""
        session_id = session_manager.create_session("test.pdf", 1000)
        
        # Create multiple records
        records = [sample_hmo_record]
        for i in range(2):
            record = HMORecord()
            record.council = f"Council {i}"
            record.reference = f"REF{i}"
            record.confidence_scores = {"council": 0.8, "reference": 0.9}
            records.append(record)
        
        success = session_manager.store_extracted_records(session_id, records)
        assert success is True
        
        # Verify records were stored
        stored_records = session_manager.get_session_records(session_id)
        assert len(stored_records) == 3
        assert stored_records[0].council == "Test Council"
    
    def test_get_session_records_flagged_only(self, session_manager):
        """Test getting only flagged records"""
        session_id = session_manager.create_session("test.pdf", 1000)
        
        # Create records with different flag status
        records = []
        for i in range(3):
            record = HMORecord()
            record.council = f"Council {i}"
            record.confidence_scores = {"council": 0.5 if i == 1 else 0.9}  # Middle one flagged
            records.append(record)
        
        session_manager.store_extracted_records(session_id, records)
        
        # Get all records
        all_records = session_manager.get_session_records(session_id)
        assert len(all_records) == 3
        
        # Get flagged records only
        flagged_records = session_manager.get_session_records(session_id, flagged_only=True)
        assert len(flagged_records) == 1
        assert flagged_records[0].council == "Council 1"
    
    def test_update_record(self, session_manager, sample_hmo_record):
        """Test updating an extracted record"""
        session_id = session_manager.create_session("test.pdf", 1000)
        session_manager.store_extracted_records(session_id, [sample_hmo_record])
        
        # Get record ID from database
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT record_id FROM extracted_records WHERE session_id = ?", (session_id,))
            record_id = cursor.fetchone()[0]
        
        # Update record
        updated_data = {"council": "Updated Council", "max_occupancy": 10}
        success = session_manager.update_record(
            record_id, 
            updated_data, 
            reviewer_notes="Manual correction"
        )
        
        assert success is True
        
        # Verify update
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT record_data, review_status, reviewer_notes 
                FROM extracted_records WHERE record_id = ?
            """, (record_id,))
            row = cursor.fetchone()
            
            record_data = json.loads(row[0])
            assert record_data['council'] == "Updated Council"
            assert record_data['max_occupancy'] == 10
            assert row[1] == 'reviewed'
            assert row[2] == "Manual correction"
    
    def test_get_sessions_by_status(self, session_manager):
        """Test getting sessions by status"""
        # Create sessions with different statuses
        session1 = session_manager.create_session("file1.pdf", 1000)
        session2 = session_manager.create_session("file2.pdf", 2000)
        session3 = session_manager.create_session("file3.pdf", 3000)
        
        session_manager.update_session_status(session1, "completed")
        session_manager.update_session_status(session2, "failed")
        # session3 remains "pending"
        
        # Test getting completed sessions
        completed_sessions = session_manager.get_sessions_by_status("completed")
        assert len(completed_sessions) == 1
        # Check session data directly since we don't have from_dict method
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM processing_sessions WHERE processing_status = 'completed'")
            result = cursor.fetchone()
            assert result[0] == session1
        
        # Test getting pending sessions
        pending_sessions = session_manager.get_sessions_by_status("pending")
        assert len(pending_sessions) == 1
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM processing_sessions WHERE processing_status = 'pending'")
            result = cursor.fetchone()
            assert result[0] == session3
    
    def test_cleanup_old_sessions(self, session_manager):
        """Test cleaning up old sessions"""
        # Create sessions
        session1 = session_manager.create_session("old_file.pdf", 1000)
        session2 = session_manager.create_session("new_file.pdf", 2000)
        
        # Manually update one session to be old
        old_date = (datetime.now() - timedelta(days=35)).isoformat()
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE processing_sessions 
                SET created_at = ? 
                WHERE session_id = ?
            """, (old_date, session1))
            conn.commit()
        
        # Cleanup sessions older than 30 days
        cleaned_count = session_manager.cleanup_old_sessions(max_age_days=30)
        
        assert cleaned_count == 1
        
        # Verify old session is gone, new session remains
        with session_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM processing_sessions WHERE session_id = ?", (session1,))
            assert cursor.fetchone() is None
            
            cursor.execute("SELECT session_id FROM processing_sessions WHERE session_id = ?", (session2,))
            assert cursor.fetchone() is not None
    
    def test_get_database_stats(self, session_manager, sample_hmo_record):
        """Test getting database statistics"""
        # Create test data
        session1 = session_manager.create_session("file1.pdf", 1000)
        session2 = session_manager.create_session("file2.pdf", 2000)
        
        session_manager.update_session_status(session1, "completed")
        session_manager.update_session_status(session2, "failed")
        
        # Add some records
        records = [sample_hmo_record]
        flagged_record = HMORecord()
        flagged_record.council = "Flagged Council"
        flagged_record.confidence_scores = {"council": 0.3}  # Low confidence = flagged
        records.append(flagged_record)
        
        session_manager.store_extracted_records(session1, records)
        
        # Get stats
        stats = session_manager.get_database_stats()
        
        assert stats['session_counts']['completed'] == 1
        assert stats['session_counts']['failed'] == 1
        assert stats['total_records'] == 2
        assert stats['flagged_records'] == 1
        assert 'database_size_bytes' in stats
        assert 'database_path' in stats
    
    def test_connection_error_handling(self, temp_db):
        """Test database connection error handling"""
        # Create session manager with invalid path
        invalid_path = "/invalid/path/database.db"
        
        with pytest.raises(Exception):
            SessionManager(db_path=invalid_path)
    
    def test_concurrent_access(self, session_manager):
        """Test concurrent database access"""
        import threading
        import time
        
        results = []
        
        def create_session_worker(worker_id):
            try:
                session_id = session_manager.create_session(f"file_{worker_id}.pdf", 1000)
                results.append(session_id)
            except Exception as e:
                results.append(f"Error: {e}")
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_session_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(results) == 5
        assert all(isinstance(result, str) and len(result) == 36 for result in results)
        assert len(set(results)) == 5  # All unique session IDs


if __name__ == "__main__":
    pytest.main([__file__])