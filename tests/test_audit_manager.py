"""
Unit tests for AuditManager class.

Tests audit workflow management, record tracking, and audit trail functionality.
"""
import unittest
import tempfile
import os
from datetime import datetime
from models.hmo_record import HMORecord
from services.audit_manager import AuditManager, ReviewStatus, AuditAction, FlaggedRecord, AuditRecord


class TestAuditManager(unittest.TestCase):
    """Test cases for AuditManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.audit_manager = AuditManager(db_path=self.temp_db.name)
        
        # Create sample records for testing
        self.sample_record = HMORecord(
            council="Test Council",
            reference="TEST123",
            hmo_address="123 Test Street, Test City, T1 1TT",
            licence_start="2023-01-01",
            licence_expiry="2024-01-01",
            max_occupancy=10
        )
        
        self.sample_record.confidence_scores = {
            'council': 0.9,
            'reference': 0.8,
            'hmo_address': 0.7,
            'licence_start': 0.85,
            'licence_expiry': 0.85,
            'max_occupancy': 0.9
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Close any database connections
        if hasattr(self, 'audit_manager'):
            del self.audit_manager
        
        # Remove temporary database
        try:
            if os.path.exists(self.temp_db.name):
                os.unlink(self.temp_db.name)
        except PermissionError:
            # On Windows, sometimes the file is still locked
            pass
    
    def test_flag_record(self):
        """Test flagging a record for manual review."""
        session_id = "test_session_001"
        reason = "Low confidence in address field"
        
        record_id = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id=session_id,
            reason=reason,
            reviewer="system"
        )
        
        # Should return a valid record ID
        self.assertIsInstance(record_id, str)
        self.assertGreater(len(record_id), 0)
        
        # Record should be in flagged records
        self.assertIn(record_id, self.audit_manager.flagged_records)
        
        flagged_record = self.audit_manager.flagged_records[record_id]
        self.assertEqual(flagged_record.session_id, session_id)
        self.assertEqual(flagged_record.flag_reason, reason)
        self.assertEqual(flagged_record.review_status, ReviewStatus.PENDING)
        
        # Should have audit trail entry
        self.assertEqual(len(flagged_record.audit_trail), 1)
        audit_entry = flagged_record.audit_trail[0]
        self.assertEqual(audit_entry.action, AuditAction.FLAGGED)
        self.assertEqual(audit_entry.reviewer, "system")
    
    def test_assign_reviewer(self):
        """Test assigning a reviewer to a flagged record."""
        # First flag a record
        record_id = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id="test_session",
            reason="Test flagging"
        )
        
        # Assign reviewer
        reviewer = "john.doe"
        success = self.audit_manager.assign_reviewer(record_id, reviewer)
        
        self.assertTrue(success)
        
        flagged_record = self.audit_manager.flagged_records[record_id]
        self.assertEqual(flagged_record.assigned_reviewer, reviewer)
        self.assertEqual(flagged_record.review_status, ReviewStatus.IN_REVIEW)
        self.assertIsNotNone(flagged_record.review_started)
        
        # Should have additional audit trail entry
        self.assertEqual(len(flagged_record.audit_trail), 2)
        review_entry = flagged_record.audit_trail[1]
        self.assertEqual(review_entry.action, AuditAction.REVIEWED)
        self.assertEqual(review_entry.reviewer, reviewer)
    
    def test_assign_reviewer_invalid_record(self):
        """Test assigning reviewer to non-existent record."""
        success = self.audit_manager.assign_reviewer("invalid_id", "reviewer")
        self.assertFalse(success)
    
    def test_update_record(self):
        """Test updating a flagged record with corrections."""
        # Flag a record first
        record_id = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id="test_session",
            reason="Test flagging"
        )
        
        # Update the record
        updates = {
            'council': 'Updated Council Name',
            'max_occupancy': 15
        }
        reviewer = "jane.smith"
        comments = "Corrected council name and occupancy"
        
        success = self.audit_manager.update_record(record_id, updates, reviewer, comments)
        
        self.assertTrue(success)
        
        # Check that record was updated
        flagged_record = self.audit_manager.flagged_records[record_id]
        self.assertEqual(flagged_record.hmo_record.council, 'Updated Council Name')
        self.assertEqual(flagged_record.hmo_record.max_occupancy, 15)
        
        # Should have correction audit trail entry
        correction_entries = [a for a in flagged_record.audit_trail if a.action == AuditAction.CORRECTED]
        self.assertEqual(len(correction_entries), 1)
        
        correction_entry = correction_entries[0]
        self.assertEqual(correction_entry.reviewer, reviewer)
        self.assertEqual(correction_entry.comments, comments)
        self.assertIsNotNone(correction_entry.original_data)
        self.assertIsNotNone(correction_entry.modified_data)
    
    def test_update_record_invalid_record(self):
        """Test updating non-existent record."""
        success = self.audit_manager.update_record("invalid_id", {}, "reviewer")
        self.assertFalse(success)
    
    def test_approve_record(self):
        """Test approving a reviewed record."""
        # Flag and assign a record
        record_id = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id="test_session",
            reason="Test flagging"
        )
        self.audit_manager.assign_reviewer(record_id, "reviewer")
        
        # Approve the record
        reviewer = "supervisor"
        comments = "Record looks good after review"
        
        success = self.audit_manager.approve_record(record_id, reviewer, comments)
        
        self.assertTrue(success)
        
        flagged_record = self.audit_manager.flagged_records[record_id]
        self.assertEqual(flagged_record.review_status, ReviewStatus.APPROVED)
        self.assertIsNotNone(flagged_record.review_completed)
        
        # Should have approval audit trail entry
        approval_entries = [a for a in flagged_record.audit_trail if a.action == AuditAction.APPROVED]
        self.assertEqual(len(approval_entries), 1)
        
        approval_entry = approval_entries[0]
        self.assertEqual(approval_entry.reviewer, reviewer)
        self.assertEqual(approval_entry.comments, comments)
    
    def test_reject_record(self):
        """Test rejecting a reviewed record."""
        # Flag and assign a record
        record_id = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id="test_session",
            reason="Test flagging"
        )
        self.audit_manager.assign_reviewer(record_id, "reviewer")
        
        # Reject the record
        reviewer = "supervisor"
        reason = "Data quality too poor to use"
        
        success = self.audit_manager.reject_record(record_id, reviewer, reason)
        
        self.assertTrue(success)
        
        flagged_record = self.audit_manager.flagged_records[record_id]
        self.assertEqual(flagged_record.review_status, ReviewStatus.REJECTED)
        self.assertIsNotNone(flagged_record.review_completed)
        
        # Should have rejection audit trail entry
        rejection_entries = [a for a in flagged_record.audit_trail if a.action == AuditAction.REJECTED]
        self.assertEqual(len(rejection_entries), 1)
        
        rejection_entry = rejection_entries[0]
        self.assertEqual(rejection_entry.reviewer, reviewer)
        self.assertEqual(rejection_entry.comments, reason)
    
    def test_add_comment(self):
        """Test adding comments to a flagged record."""
        # Flag a record
        record_id = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id="test_session",
            reason="Test flagging"
        )
        
        # Add comment
        reviewer = "reviewer"
        comment = "This record needs additional verification"
        
        success = self.audit_manager.add_comment(record_id, reviewer, comment)
        
        self.assertTrue(success)
        
        # Should have comment audit trail entry
        flagged_record = self.audit_manager.flagged_records[record_id]
        comment_entries = [a for a in flagged_record.audit_trail if a.action == AuditAction.COMMENT_ADDED]
        self.assertEqual(len(comment_entries), 1)
        
        comment_entry = comment_entries[0]
        self.assertEqual(comment_entry.reviewer, reviewer)
        self.assertEqual(comment_entry.comments, comment)
    
    def test_get_flagged_records_no_filter(self):
        """Test getting all flagged records without filters."""
        # Flag multiple records
        record_ids = []
        for i in range(3):
            record_id = self.audit_manager.flag_record(
                record=self.sample_record,
                session_id=f"session_{i}",
                reason=f"Reason {i}"
            )
            record_ids.append(record_id)
        
        # Get all flagged records
        flagged_records = self.audit_manager.get_flagged_records()
        
        self.assertEqual(len(flagged_records), 3)
        
        # Check that all records are returned
        returned_ids = [record.record_id for record in flagged_records]
        for record_id in record_ids:
            self.assertIn(record_id, returned_ids)
    
    def test_get_flagged_records_with_filters(self):
        """Test getting flagged records with various filters."""
        # Flag records with different sessions and reviewers
        record_id_1 = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id="session_A",
            reason="Reason A"
        )
        
        record_id_2 = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id="session_B",
            reason="Reason B"
        )
        
        # Assign different reviewers
        self.audit_manager.assign_reviewer(record_id_1, "reviewer_1")
        self.audit_manager.assign_reviewer(record_id_2, "reviewer_2")
        
        # Test session filter
        session_a_records = self.audit_manager.get_flagged_records(session_id="session_A")
        self.assertEqual(len(session_a_records), 1)
        self.assertEqual(session_a_records[0].record_id, record_id_1)
        
        # Test status filter
        in_review_records = self.audit_manager.get_flagged_records(status=ReviewStatus.IN_REVIEW)
        self.assertEqual(len(in_review_records), 2)  # Both assigned records
        
        # Test reviewer filter
        reviewer_1_records = self.audit_manager.get_flagged_records(reviewer="reviewer_1")
        self.assertEqual(len(reviewer_1_records), 1)
        self.assertEqual(reviewer_1_records[0].record_id, record_id_1)
    
    def test_get_audit_trail(self):
        """Test getting complete audit trail for a record."""
        # Flag a record and perform various actions
        record_id = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id="test_session",
            reason="Test flagging"
        )
        
        self.audit_manager.assign_reviewer(record_id, "reviewer")
        self.audit_manager.add_comment(record_id, "reviewer", "Initial comment")
        self.audit_manager.update_record(record_id, {'council': 'Updated Council'}, "reviewer")
        self.audit_manager.approve_record(record_id, "supervisor", "Approved")
        
        # Get audit trail
        audit_trail = self.audit_manager.get_audit_trail(record_id)
        
        # Should have all actions in chronological order
        self.assertEqual(len(audit_trail), 5)  # Flag, assign, comment, update, approve
        
        expected_actions = [
            AuditAction.FLAGGED,
            AuditAction.REVIEWED,
            AuditAction.COMMENT_ADDED,
            AuditAction.CORRECTED,
            AuditAction.APPROVED
        ]
        
        actual_actions = [entry.action for entry in audit_trail]
        self.assertEqual(actual_actions, expected_actions)
        
        # Should be in chronological order
        timestamps = [entry.timestamp for entry in audit_trail]
        self.assertEqual(timestamps, sorted(timestamps))
    
    def test_get_session_audit_summary(self):
        """Test getting audit summary for a processing session."""
        session_id = "test_session_summary"
        
        # Flag multiple records with different outcomes
        record_id_1 = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id=session_id,
            reason="Reason 1"
        )
        
        record_id_2 = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id=session_id,
            reason="Reason 2"
        )
        
        # Process records differently
        self.audit_manager.assign_reviewer(record_id_1, "reviewer")
        self.audit_manager.approve_record(record_id_1, "reviewer", "Approved")
        
        self.audit_manager.assign_reviewer(record_id_2, "reviewer")
        self.audit_manager.update_record(record_id_2, {'council': 'Updated'}, "reviewer")
        
        # Get summary
        summary = self.audit_manager.get_session_audit_summary(session_id)
        
        # Check summary structure and values
        self.assertEqual(summary['session_id'], session_id)
        self.assertEqual(summary['total_flagged'], 2)
        self.assertIn('status_breakdown', summary)
        self.assertIn('total_corrections_made', summary)
        self.assertIn('completion_rate', summary)
        
        # Check status breakdown
        status_breakdown = summary['status_breakdown']
        self.assertEqual(status_breakdown['approved'], 1)
        self.assertEqual(status_breakdown['in_review'], 1)
        
        # Check corrections count
        self.assertEqual(summary['total_corrections_made'], 1)  # One update made
    
    def test_export_audited_data(self):
        """Test exporting audited data for a session."""
        session_id = "export_test_session"
        
        # Flag and process records
        record_id_1 = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id=session_id,
            reason="Test export"
        )
        
        record_id_2 = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id=session_id,
            reason="Test export 2"
        )
        
        # Approve one, reject another
        self.audit_manager.assign_reviewer(record_id_1, "reviewer")
        self.audit_manager.approve_record(record_id_1, "reviewer", "Good")
        
        self.audit_manager.assign_reviewer(record_id_2, "reviewer")
        self.audit_manager.reject_record(record_id_2, "reviewer", "Poor quality")
        
        # Export approved only
        exported_data = self.audit_manager.export_audited_data(session_id, include_rejected=False)
        
        self.assertEqual(len(exported_data), 1)  # Only approved record
        
        exported_record = exported_data[0]
        self.assertIn('_audit_metadata', exported_record)
        
        audit_metadata = exported_record['_audit_metadata']
        self.assertEqual(audit_metadata['record_id'], record_id_1)
        self.assertEqual(audit_metadata['review_status'], 'approved')
        
        # Export including rejected
        exported_data_all = self.audit_manager.export_audited_data(session_id, include_rejected=True)
        
        self.assertEqual(len(exported_data_all), 2)  # Both records
    
    def test_generate_audit_report(self):
        """Test generating comprehensive audit report."""
        session_id = "report_test_session"
        
        # Create various audit scenarios
        record_id_1 = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id=session_id,
            reason="Low confidence"
        )
        
        record_id_2 = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id=session_id,
            reason="Missing data"
        )
        
        # Process records
        self.audit_manager.assign_reviewer(record_id_1, "reviewer_1")
        self.audit_manager.update_record(record_id_1, {'council': 'Corrected'}, "reviewer_1")
        self.audit_manager.approve_record(record_id_1, "reviewer_1", "Fixed")
        
        self.audit_manager.assign_reviewer(record_id_2, "reviewer_2")
        
        # Generate report
        report = self.audit_manager.generate_audit_report(session_id)
        
        # Check report structure
        self.assertIn('report_generated', report)
        self.assertIn('session_id', report)
        self.assertIn('summary', report)
        self.assertIn('reviewer_performance', report)
        self.assertIn('flag_analysis', report)
        self.assertIn('correction_analysis', report)
        
        # Check summary
        summary = report['summary']
        self.assertEqual(summary['total_flagged_records'], 2)
        self.assertIn('status_breakdown', summary)
        self.assertIn('completion_rate', summary)
        
        # Check reviewer performance
        reviewer_perf = report['reviewer_performance']
        self.assertIn('reviewer_1', reviewer_perf)
        self.assertEqual(reviewer_perf['reviewer_1']['assigned'], 1)
        self.assertEqual(reviewer_perf['reviewer_1']['completed'], 1)
        self.assertEqual(reviewer_perf['reviewer_1']['approved'], 1)
        
        # Check flag analysis
        flag_analysis = report['flag_analysis']
        self.assertIn('most_common_reasons', flag_analysis)
        
        # Check correction analysis
        correction_analysis = report['correction_analysis']
        self.assertEqual(correction_analysis['total_corrections'], 1)
        self.assertEqual(correction_analysis['records_with_corrections'], 1)
    
    def test_database_persistence(self):
        """Test that data persists across AuditManager instances."""
        session_id = "persistence_test"
        
        # Flag a record
        record_id = self.audit_manager.flag_record(
            record=self.sample_record,
            session_id=session_id,
            reason="Persistence test"
        )
        
        # Create new AuditManager instance with same database
        new_audit_manager = AuditManager(db_path=self.temp_db.name)
        
        # Should load the flagged record
        self.assertIn(record_id, new_audit_manager.flagged_records)
        
        flagged_record = new_audit_manager.flagged_records[record_id]
        self.assertEqual(flagged_record.session_id, session_id)
        self.assertEqual(flagged_record.flag_reason, "Persistence test")
        self.assertEqual(len(flagged_record.audit_trail), 1)
    
    def test_empty_session_summary(self):
        """Test audit summary for session with no flagged records."""
        summary = self.audit_manager.get_session_audit_summary("nonexistent_session")
        self.assertEqual(summary, {})
    
    def test_invalid_operations(self):
        """Test various invalid operations."""
        # Test operations on non-existent record
        invalid_id = "nonexistent_record"
        
        self.assertFalse(self.audit_manager.assign_reviewer(invalid_id, "reviewer"))
        self.assertFalse(self.audit_manager.update_record(invalid_id, {}, "reviewer"))
        self.assertFalse(self.audit_manager.approve_record(invalid_id, "reviewer"))
        self.assertFalse(self.audit_manager.reject_record(invalid_id, "reviewer", "reason"))
        self.assertFalse(self.audit_manager.add_comment(invalid_id, "reviewer", "comment"))
        
        # Get audit trail for non-existent record should return empty list
        audit_trail = self.audit_manager.get_audit_trail(invalid_id)
        self.assertEqual(audit_trail, [])


if __name__ == '__main__':
    unittest.main()