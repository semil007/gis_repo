"""
Unit tests for ProcessingSession model and SessionManager.
"""
import unittest
import tempfile
import os
import sqlite3
from datetime import datetime
import sys

# Add the parent directory to the path so we can import models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.processing_session import ProcessingSession, SessionManager
from models.hmo_record import HMORecord


class TestProcessingSession(unittest.TestCase):
    """Test cases for ProcessingSession class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.session = ProcessingSession(
            file_name="test_document.pdf",
            file_size=1024000,
            file_path="/tmp/test_document.pdf"
        )
        
        # Create sample records
        self.sample_records = [
            HMORecord(
                council="Test Council 1",
                reference="HMO001",
                hmo_address="123 Test Street, TC1 1AB",
                max_occupancy=5
            ),
            HMORecord(
                council="Test Council 2",
                reference="HMO002",
                hmo_address="456 Test Road, TC2 2CD",
                max_occupancy=8
            )
        ]
    
    def test_initialization(self):
        """Test ProcessingSession initialization."""
        # Check default values
        self.assertIsNotNone(self.session.session_id)
        self.assertEqual(self.session.file_name, "test_document.pdf")
        self.assertEqual(self.session.file_size, 1024000)
        self.assertEqual(self.session.processing_status, "uploaded")
        self.assertIsInstance(self.session.extracted_records, list)
        self.assertIsInstance(self.session.quality_metrics, dict)
        
        # Check quality metrics initialization
        expected_metrics = [
            'total_records_found', 'records_with_high_confidence',
            'records_flagged_for_review', 'average_confidence_score',
            'field_extraction_rates', 'processing_time_seconds'
        ]
        for metric in expected_metrics:
            self.assertIn(metric, self.session.quality_metrics)
    
    def test_start_processing(self):
        """Test starting processing."""
        self.session.start_processing()
        
        self.assertEqual(self.session.processing_status, "processing")
        self.assertIsNotNone(self.session.processing_start_time)
        self.assertIsInstance(self.session.processing_start_time, datetime)
    
    def test_complete_processing(self):
        """Test completing processing."""
        self.session.start_processing()
        
        # Add some records
        for record in self.sample_records:
            self.session.add_record(record)
        
        self.session.complete_processing()
        
        self.assertEqual(self.session.processing_status, "completed")
        self.assertIsNotNone(self.session.processing_end_time)
        self.assertGreater(self.session.quality_metrics['total_records_found'], 0)
    
    def test_fail_processing(self):
        """Test failing processing."""
        error_message = "Test error occurred"
        self.session.fail_processing(error_message)
        
        self.assertEqual(self.session.processing_status, "failed")
        self.assertIsNotNone(self.session.processing_end_time)
        self.assertIn(error_message, self.session.extraction_errors)
    
    def test_add_record(self):
        """Test adding records to session."""
        initial_count = len(self.session.extracted_records)
        
        self.session.add_record(self.sample_records[0])
        
        self.assertEqual(len(self.session.extracted_records), initial_count + 1)
        self.assertEqual(self.session.total_records, initial_count + 1)
        self.assertEqual(self.session.extracted_records[-1], self.sample_records[0])
    
    def test_add_flagged_record(self):
        """Test adding a record that should be flagged."""
        # Create a record with low confidence
        bad_record = HMORecord(council="", reference="", hmo_address="")
        bad_record.validate_all_fields()  # This should result in low confidence
        
        initial_flagged_count = len(self.session.flagged_records)
        self.session.add_record(bad_record)
        
        # Should be flagged due to low confidence
        self.assertGreater(len(self.session.flagged_records), initial_flagged_count)
    
    def test_calculate_quality_metrics(self):
        """Test quality metrics calculation."""
        # Add records with different confidence levels
        for record in self.sample_records:
            record.validate_all_fields()
            self.session.add_record(record)
        
        # Add a low-confidence record
        bad_record = HMORecord(council="", reference="")
        bad_record.validate_all_fields()
        self.session.add_record(bad_record)
        
        self.session.calculate_quality_metrics()
        
        # Check metrics
        metrics = self.session.quality_metrics
        self.assertEqual(metrics['total_records_found'], 3)
        self.assertGreaterEqual(metrics['records_with_high_confidence'], 0)
        self.assertGreaterEqual(metrics['records_flagged_for_review'], 1)
        self.assertIsInstance(metrics['average_confidence_score'], float)
        self.assertIsInstance(metrics['field_extraction_rates'], dict)
    
    def test_get_flagged_records(self):
        """Test getting flagged records."""
        # Add good and bad records
        good_record = self.sample_records[0]
        good_record.validate_all_fields()
        
        bad_record = HMORecord(council="", reference="")
        bad_record.validate_all_fields()
        
        self.session.add_record(good_record)
        self.session.add_record(bad_record)
        
        flagged_records = self.session.get_flagged_records()
        
        # Should contain at least the bad record
        self.assertGreaterEqual(len(flagged_records), 1)
        
        # All flagged records should have low confidence
        for record in flagged_records:
            self.assertTrue(record.is_flagged_for_review())
    
    def test_update_record(self):
        """Test updating a record in the session."""
        # Add a record
        self.session.add_record(self.sample_records[0])
        
        # Create updated record
        updated_record = HMORecord(
            council="Updated Council",
            reference="UPDATED001",
            hmo_address="Updated Address",
            max_occupancy=10
        )
        
        # Update the record
        self.session.update_record(0, updated_record)
        
        # Check the record was updated
        self.assertEqual(self.session.extracted_records[0].council, "Updated Council")
        self.assertEqual(self.session.extracted_records[0].reference, "UPDATED001")
    
    def test_update_record_invalid_index(self):
        """Test updating record with invalid index."""
        # Should not raise exception
        self.session.update_record(999, self.sample_records[0])
        
        # Should not change anything
        self.assertEqual(len(self.session.extracted_records), 0)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        # Add some data
        for record in self.sample_records:
            self.session.add_record(record)
        
        session_dict = self.session.to_dict()
        
        # Check required fields
        required_fields = [
            'session_id', 'file_name', 'file_size', 'processing_status',
            'total_records', 'quality_metrics', 'extracted_records'
        ]
        
        for field in required_fields:
            self.assertIn(field, session_dict)
        
        # Check data types
        self.assertIsInstance(session_dict['extracted_records'], list)
        self.assertEqual(len(session_dict['extracted_records']), 2)
        
        # Check timestamp serialization
        if session_dict['upload_timestamp']:
            # Should be ISO format string
            datetime.fromisoformat(session_dict['upload_timestamp'])


class TestSessionManager(unittest.TestCase):
    """Test cases for SessionManager class."""
    
    def setUp(self):
        """Set up test fixtures with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.session_manager = SessionManager(self.db_path)
        
        # Create test session
        self.test_session = ProcessingSession(
            file_name="test.pdf",
            file_size=1024,
            file_path="/tmp/test.pdf"
        )
        
        # Add some records
        record1 = HMORecord(
            council="Test Council",
            reference="TEST001",
            hmo_address="123 Test Street"
        )
        record1.validate_all_fields()
        self.test_session.add_record(record1)
    
    def tearDown(self):
        """Clean up temporary database."""
        # Close any open connections
        if hasattr(self, 'session_manager'):
            del self.session_manager
        
        # Try to remove the file, ignore errors on Windows
        try:
            if os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except (PermissionError, OSError):
            # On Windows, the file might still be locked
            pass
    
    def test_init_database(self):
        """Test database initialization."""
        # Check that tables were created
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            
            self.assertIn('processing_sessions', tables)
            self.assertIn('extracted_records', tables)
    
    def test_save_session(self):
        """Test saving a session."""
        success = self.session_manager.save_session(self.test_session)
        self.assertTrue(success)
        
        # Verify session was saved
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT session_id, file_name FROM processing_sessions WHERE session_id = ?",
                (self.test_session.session_id,)
            )
            row = cursor.fetchone()
            
            self.assertIsNotNone(row)
            self.assertEqual(row[0], self.test_session.session_id)
            self.assertEqual(row[1], self.test_session.file_name)
    
    def test_load_session(self):
        """Test loading a session."""
        # Save session first
        self.session_manager.save_session(self.test_session)
        
        # Load session
        loaded_session = self.session_manager.load_session(self.test_session.session_id)
        
        self.assertIsNotNone(loaded_session)
        self.assertEqual(loaded_session.session_id, self.test_session.session_id)
        self.assertEqual(loaded_session.file_name, self.test_session.file_name)
        self.assertEqual(loaded_session.file_size, self.test_session.file_size)
        self.assertEqual(len(loaded_session.extracted_records), 1)
    
    def test_load_nonexistent_session(self):
        """Test loading a session that doesn't exist."""
        loaded_session = self.session_manager.load_session("nonexistent_id")
        self.assertIsNone(loaded_session)
    
    def test_list_sessions(self):
        """Test listing sessions."""
        # Save multiple sessions
        session1 = ProcessingSession(file_name="test1.pdf")
        session2 = ProcessingSession(file_name="test2.pdf")
        session2.processing_status = "completed"
        
        self.session_manager.save_session(session1)
        self.session_manager.save_session(session2)
        
        # List all sessions
        all_sessions = self.session_manager.list_sessions()
        self.assertGreaterEqual(len(all_sessions), 2)
        
        # List by status
        completed_sessions = self.session_manager.list_sessions(status="completed")
        self.assertGreaterEqual(len(completed_sessions), 1)
        
        # Check session data
        session_data = all_sessions[0]
        required_fields = ['session_id', 'file_name', 'processing_status']
        for field in required_fields:
            self.assertIn(field, session_data)
    
    def test_delete_session(self):
        """Test deleting a session."""
        # Save session first
        self.session_manager.save_session(self.test_session)
        
        # Verify it exists
        loaded_session = self.session_manager.load_session(self.test_session.session_id)
        self.assertIsNotNone(loaded_session)
        
        # Delete session
        success = self.session_manager.delete_session(self.test_session.session_id)
        self.assertTrue(success)
        
        # Verify it's gone
        loaded_session = self.session_manager.load_session(self.test_session.session_id)
        self.assertIsNone(loaded_session)
    
    def test_cleanup_old_sessions(self):
        """Test cleaning up old sessions."""
        # Create session with old timestamp
        old_session = ProcessingSession(file_name="old.pdf")
        old_session.upload_timestamp = datetime(2020, 1, 1)
        
        # Save sessions
        self.session_manager.save_session(self.test_session)  # Recent
        self.session_manager.save_session(old_session)        # Old
        
        # Cleanup sessions older than 1 day
        deleted_count = self.session_manager.cleanup_old_sessions(days_old=1)
        
        # Should have deleted the old session
        self.assertGreaterEqual(deleted_count, 1)
        
        # Recent session should still exist
        loaded_session = self.session_manager.load_session(self.test_session.session_id)
        self.assertIsNotNone(loaded_session)
        
        # Old session should be gone
        loaded_old_session = self.session_manager.load_session(old_session.session_id)
        self.assertIsNone(loaded_old_session)


if __name__ == '__main__':
    unittest.main()