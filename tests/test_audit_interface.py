"""
Tests for audit interface components.
Tests record editing, validation, audit workflow, and export functionality.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import json

# Import components to test
from web.audit_interface import AuditInterface
from web.record_editor import RecordEditor
from web.audit_tracker import AuditTracker
from services.audit_manager import AuditManager, FlaggedRecord, ReviewStatus, AuditAction
from models.hmo_record import HMORecord
from models.processing_session import SessionManager


class TestAuditInterface:
    """Test cases for AuditInterface component."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        yield temp_file.name
        try:
            os.unlink(temp_file.name)
        except (PermissionError, FileNotFoundError):
            pass  # Ignore cleanup errors on Windows
        
    @pytest.fixture
    def audit_manager(self, temp_db):
        """Create AuditManager instance for testing."""
        return AuditManager(db_path=temp_db)
        
    @pytest.fixture
    def session_manager(self, temp_db):
        """Create SessionManager instance for testing."""
        session_db = temp_db.replace('.db', '_sessions.db')
        return SessionManager(db_path=session_db)
        
    @pytest.fixture
    def sample_hmo_record(self):
        """Create sample HMO record for testing."""
        record = HMORecord(
            council="Test Council",
            reference="HMO/2024/001",
            hmo_address="123 Test Street, Test City, TC1 2AB",
            licence_start="2024-01-01",
            licence_expiry="2025-01-01",
            max_occupancy=5,
            hmo_manager_name="John Smith",
            hmo_manager_address="456 Manager Street, Test City, TC2 3CD",
            licence_holder_name="Jane Doe",
            licence_holder_address="789 Holder Avenue, Test City, TC3 4EF",
            number_of_households=3,
            number_of_shared_kitchens=1,
            number_of_shared_bathrooms=2,
            number_of_shared_toilets=2,
            number_of_storeys=2
        )
        
        # Set confidence scores
        record.confidence_scores = {
            'council': 0.95,
            'reference': 0.88,
            'hmo_address': 0.92,
            'licence_start': 0.85,
            'licence_expiry': 0.87,
            'max_occupancy': 0.90,
            'hmo_manager_name': 0.45,  # Low confidence to trigger flagging
            'hmo_manager_address': 0.72,
            'licence_holder_name': 0.75,
            'licence_holder_address': 0.68,
            'number_of_households': 0.80,
            'number_of_shared_kitchens': 0.85,
            'number_of_shared_bathrooms': 0.88,
            'number_of_shared_toilets': 0.86,
            'number_of_storeys': 0.92
        }
        
        return record
        
    @pytest.fixture
    def flagged_record(self, audit_manager, sample_hmo_record):
        """Create flagged record for testing."""
        session_id = "test_session_123"
        record_id = audit_manager.flag_record(
            sample_hmo_record,
            session_id,
            "Low confidence in manager name field",
            "system"
        )
        
        return audit_manager.flagged_records[record_id]
        
    @pytest.fixture
    def audit_interface(self, audit_manager, session_manager):
        """Create AuditInterface instance for testing."""
        interface = AuditInterface()
        interface.audit_manager = audit_manager
        interface.session_manager = session_manager
        return interface
        
    def test_audit_interface_initialization(self, audit_interface):
        """Test audit interface initialization."""
        assert audit_interface.audit_manager is not None
        assert audit_interface.session_manager is not None
        assert audit_interface.record_editor is not None
        assert audit_interface.audit_tracker is not None
        
    def test_get_sessions_with_flagged_records(self, audit_interface, flagged_record):
        """Test getting sessions with flagged records."""
        # Mock session manager to return test session
        audit_interface.session_manager.list_sessions = Mock(return_value=[
            {
                'session_id': 'test_session_123',
                'file_name': 'test_file.pdf',
                'upload_timestamp': datetime.now().isoformat(),
                'processing_status': 'completed'
            }
        ])
        
        sessions = audit_interface._get_sessions_with_flagged_records()
        
        assert len(sessions) == 1
        assert sessions[0]['session_id'] == 'test_session_123'
        assert sessions[0]['flagged_count'] == 1
        
    def test_calculate_status_metrics(self, audit_interface, audit_manager, sample_hmo_record):
        """Test status metrics calculation."""
        # Create multiple flagged records with different statuses
        session_id = "test_session_metrics"
        
        # Create records with different statuses
        record1_id = audit_manager.flag_record(sample_hmo_record, session_id, "Test reason 1")
        record2_id = audit_manager.flag_record(sample_hmo_record, session_id, "Test reason 2")
        record3_id = audit_manager.flag_record(sample_hmo_record, session_id, "Test reason 3")
        
        # Update statuses
        audit_manager.approve_record(record1_id, "test_reviewer", "Approved")
        audit_manager.reject_record(record2_id, "test_reviewer", "Rejected")
        # record3 remains pending
        
        flagged_records = audit_manager.get_flagged_records(session_id=session_id)
        status_metrics = audit_interface.audit_tracker._calculate_status_metrics(flagged_records)
        
        assert status_metrics['approved'] == 1
        assert status_metrics['rejected'] == 1
        assert status_metrics['pending'] == 1
        
    @patch('streamlit.info')
    @patch('streamlit.button')
    def test_render_no_flagged_records(self, mock_button, mock_info, audit_interface):
        """Test rendering when no flagged records exist."""
        mock_button.return_value = False
        
        audit_interface._render_no_flagged_records()
        
        mock_info.assert_called_once()
        mock_button.assert_called_once()


class TestRecordEditor:
    """Test cases for RecordEditor component."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        yield temp_file.name
        try:
            os.unlink(temp_file.name)
        except (PermissionError, FileNotFoundError):
            pass  # Ignore cleanup errors on Windows
        
    @pytest.fixture
    def audit_manager(self, temp_db):
        """Create AuditManager instance for testing."""
        return AuditManager(db_path=temp_db)
        
    @pytest.fixture
    def record_editor(self, audit_manager):
        """Create RecordEditor instance for testing."""
        return RecordEditor(audit_manager)
        
    @pytest.fixture
    def sample_record(self):
        """Create sample HMO record for testing."""
        return HMORecord(
            council="Test Council",
            reference="HMO/2024/001",
            hmo_address="123 Test Street",
            licence_start="2024-01-01",
            licence_expiry="2025-01-01",
            max_occupancy=5,
            hmo_manager_name="John Smith"
        )
        
    def test_record_editor_initialization(self, record_editor, audit_manager):
        """Test record editor initialization."""
        assert record_editor.audit_manager == audit_manager
        assert record_editor.data_validator is not None
        
    def test_initialize_edit_data(self, record_editor, sample_record):
        """Test initialization of edit data from HMO record."""
        edit_data = record_editor._initialize_edit_data(sample_record)
        
        assert edit_data['council'] == "Test Council"
        assert edit_data['reference'] == "HMO/2024/001"
        assert edit_data['hmo_address'] == "123 Test Street"
        assert edit_data['max_occupancy'] == 5
        
    def test_validate_field_council(self, record_editor, sample_record):
        """Test field validation for council field."""
        # Test valid council
        result = record_editor._validate_field('council', 'Test Council', sample_record)
        
        assert result['confidence'] > 0.5
        assert result['status'] in ['excellent', 'good', 'warning', 'error']
        assert 'is_changed' in result
        
        # Test empty council
        result = record_editor._validate_field('council', '', sample_record)
        
        assert result['confidence'] == 0.0
        assert result['status'] == 'error'
        
    def test_validate_field_reference(self, record_editor, sample_record):
        """Test field validation for reference field."""
        # Test valid reference
        result = record_editor._validate_field('reference', 'HMO/2024/001', sample_record)
        
        assert result['confidence'] > 0.5  # Adjusted expectation
        assert result['status'] in ['excellent', 'good', 'warning']
        
        # Test invalid reference
        result = record_editor._validate_field('reference', 'invalid', sample_record)
        
        assert result['confidence'] < 0.8
        
    def test_validate_field_numeric(self, record_editor, sample_record):
        """Test field validation for numeric fields."""
        # Test valid occupancy
        result = record_editor._validate_field('max_occupancy', 5, sample_record)
        
        assert result['confidence'] > 0.8
        assert result['status'] in ['excellent', 'good']
        
        # Test invalid occupancy (negative)
        result = record_editor._validate_field('max_occupancy', -1, sample_record)
        
        assert result['confidence'] == 0.0
        assert result['status'] == 'error'
        
    def test_parse_date_string(self, record_editor):
        """Test date string parsing."""
        # Test valid ISO date
        date_obj = record_editor._parse_date_string('2024-01-01')
        assert date_obj is not None
        assert date_obj.year == 2024
        assert date_obj.month == 1
        assert date_obj.day == 1
        
        # Test valid UK date format
        date_obj = record_editor._parse_date_string('01/01/2024')
        assert date_obj is not None
        
        # Test invalid date
        date_obj = record_editor._parse_date_string('invalid-date')
        assert date_obj is None
        
        # Test empty date
        date_obj = record_editor._parse_date_string('')
        assert date_obj is None


class TestAuditTracker:
    """Test cases for AuditTracker component."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        yield temp_file.name
        try:
            os.unlink(temp_file.name)
        except (PermissionError, FileNotFoundError):
            pass  # Ignore cleanup errors on Windows
        
    @pytest.fixture
    def audit_manager(self, temp_db):
        """Create AuditManager instance for testing."""
        return AuditManager(db_path=temp_db)
        
    @pytest.fixture
    def session_manager(self, temp_db):
        """Create SessionManager instance for testing."""
        session_db = temp_db.replace('.db', '_sessions.db')
        return SessionManager(db_path=session_db)
        
    @pytest.fixture
    def audit_tracker(self, audit_manager, session_manager):
        """Create AuditTracker instance for testing."""
        return AuditTracker(audit_manager, session_manager)
        
    @pytest.fixture
    def sample_flagged_records(self, audit_manager):
        """Create sample flagged records for testing."""
        session_id = "test_session_tracker"
        records = []
        
        for i in range(3):
            record = HMORecord(
                council=f"Council {i}",
                reference=f"HMO/2024/00{i}",
                hmo_address=f"Address {i}"
            )
            
            record_id = audit_manager.flag_record(
                record, 
                session_id, 
                f"Test reason {i}",
                "system"
            )
            
            records.append(audit_manager.flagged_records[record_id])
            
        # Set different statuses
        audit_manager.approve_record(records[0].record_id, "reviewer1", "Approved")
        audit_manager.reject_record(records[1].record_id, "reviewer1", "Rejected")
        # records[2] remains pending
        
        return records
        
    def test_audit_tracker_initialization(self, audit_tracker, audit_manager, session_manager):
        """Test audit tracker initialization."""
        assert audit_tracker.audit_manager == audit_manager
        assert audit_tracker.session_manager == session_manager
        
    def test_calculate_status_metrics(self, audit_tracker, sample_flagged_records):
        """Test status metrics calculation."""
        status_metrics = audit_tracker._calculate_status_metrics(sample_flagged_records)
        
        assert status_metrics['approved'] == 1
        assert status_metrics['rejected'] == 1
        assert status_metrics['pending'] == 1
        
    def test_get_sessions_with_completed_audits(self, audit_tracker, sample_flagged_records):
        """Test getting sessions with completed audits."""
        # Mock session manager
        audit_tracker.session_manager.list_sessions = Mock(return_value=[
            {
                'session_id': 'test_session_tracker',
                'file_name': 'test_file.pdf',
                'processing_status': 'completed'
            }
        ])
        
        sessions = audit_tracker._get_sessions_with_completed_audits()
        
        assert len(sessions) == 1
        assert sessions[0]['session_id'] == 'test_session_tracker'
        assert sessions[0]['completed_audits'] == 2  # approved + rejected
        
    def test_prepare_export_data(self, audit_tracker, audit_manager, sample_flagged_records):
        """Test export data preparation."""
        session_id = "test_session_tracker"
        
        # Mock export_audited_data
        mock_data = [
            {
                'council': 'Council 0',
                'reference': 'HMO/2024/000',
                'hmo_address': 'Address 0',
                'confidence_scores': {'council': 0.9, 'reference': 0.8},
                '_audit_metadata': {
                    'record_id': 'test_record_1',
                    'flag_reason': 'Test reason',
                    'review_status': 'approved',
                    'reviewer': 'reviewer1',
                    'corrections_made': 1
                }
            }
        ]
        
        audit_tracker.audit_manager.export_audited_data = Mock(return_value=mock_data)
        
        # Test with all options enabled
        export_data = audit_tracker._prepare_export_data(
            session_id, 
            include_rejected=True,
            include_metadata=True,
            include_confidence=True
        )
        
        assert len(export_data) == 1
        assert 'council' in export_data[0]
        assert 'council_confidence' in export_data[0]
        assert 'audit_record_id' in export_data[0]
        
        # Test with minimal options
        export_data = audit_tracker._prepare_export_data(
            session_id,
            include_rejected=False,
            include_metadata=False,
            include_confidence=False
        )
        
        assert len(export_data) == 1
        assert 'council' in export_data[0]
        assert 'council_confidence' not in export_data[0]
        assert 'audit_record_id' not in export_data[0]
        
    def test_calculate_efficiency_metrics(self, audit_tracker):
        """Test efficiency metrics calculation."""
        metrics = audit_tracker._calculate_efficiency_metrics("test_session")
        
        assert 'records_per_hour' in metrics
        assert 'corrections_per_record' in metrics
        assert 'first_pass_approval_rate' in metrics
        assert 'quality_metrics' in metrics


class TestAuditWorkflow:
    """Integration tests for complete audit workflow."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        yield temp_file.name
        try:
            os.unlink(temp_file.name)
        except (PermissionError, FileNotFoundError):
            pass  # Ignore cleanup errors on Windows
        
    @pytest.fixture
    def audit_manager(self, temp_db):
        """Create AuditManager instance for testing."""
        return AuditManager(db_path=temp_db)
        
    def test_complete_audit_workflow(self, audit_manager):
        """Test complete audit workflow from flagging to export."""
        session_id = "workflow_test_session"
        
        # Step 1: Create and flag a record
        record = HMORecord(
            council="Workflow Council",
            reference="WF/2024/001",
            hmo_address="123 Workflow Street",
            max_occupancy=5
        )
        
        record.confidence_scores = {
            'council': 0.95,
            'reference': 0.45,  # Low confidence
            'hmo_address': 0.88,
            'max_occupancy': 0.90
        }
        
        record_id = audit_manager.flag_record(
            record,
            session_id,
            "Low confidence in reference field",
            "system"
        )
        
        # Verify record is flagged
        flagged_record = audit_manager.flagged_records[record_id]
        assert flagged_record.review_status == ReviewStatus.PENDING
        
        # Step 2: Assign reviewer
        success = audit_manager.assign_reviewer(record_id, "test_reviewer")
        assert success
        assert flagged_record.review_status == ReviewStatus.IN_REVIEW
        assert flagged_record.assigned_reviewer == "test_reviewer"
        
        # Step 3: Make corrections
        updates = {
            'reference': 'WF/2024/001-CORRECTED'
        }
        
        success = audit_manager.update_record(
            record_id,
            updates,
            "test_reviewer",
            "Corrected reference format"
        )
        assert success
        
        # Verify record was updated
        updated_record = flagged_record.hmo_record
        assert updated_record.reference == 'WF/2024/001-CORRECTED'
        
        # Step 4: Approve record
        success = audit_manager.approve_record(
            record_id,
            "test_reviewer",
            "Record looks good after corrections"
        )
        assert success
        assert flagged_record.review_status == ReviewStatus.APPROVED
        
        # Step 5: Verify audit trail
        audit_trail = audit_manager.get_audit_trail(record_id)
        
        # Should have: flagged, reviewed (assigned), corrected, approved
        assert len(audit_trail) >= 4
        
        actions = [entry.action for entry in audit_trail]
        assert AuditAction.FLAGGED in actions
        assert AuditAction.REVIEWED in actions
        assert AuditAction.CORRECTED in actions
        assert AuditAction.APPROVED in actions
        
        # Step 6: Export audited data
        exported_data = audit_manager.export_audited_data(session_id)
        
        assert len(exported_data) == 1
        assert exported_data[0]['reference'] == 'WF/2024/001-CORRECTED'
        assert exported_data[0]['_audit_metadata']['review_status'] == 'approved'
        
    def test_audit_statistics_generation(self, audit_manager):
        """Test audit statistics and reporting."""
        session_id = "stats_test_session"
        
        # Create multiple records with different outcomes
        records_data = [
            ("Council A", "REF001", ReviewStatus.APPROVED),
            ("Council B", "REF002", ReviewStatus.APPROVED),
            ("Council C", "REF003", ReviewStatus.REJECTED),
            ("Council D", "REF004", ReviewStatus.PENDING)
        ]
        
        record_ids = []
        
        for council, ref, final_status in records_data:
            record = HMORecord(council=council, reference=ref)
            record_id = audit_manager.flag_record(record, session_id, "Test flagging")
            record_ids.append(record_id)
            
            # Set final status
            if final_status == ReviewStatus.APPROVED:
                audit_manager.approve_record(record_id, "reviewer", "Approved")
            elif final_status == ReviewStatus.REJECTED:
                audit_manager.reject_record(record_id, "reviewer", "Rejected")
                
        # Generate audit summary
        summary = audit_manager.get_session_audit_summary(session_id)
        
        assert summary['total_flagged'] == 4
        assert summary['status_breakdown']['approved'] == 2
        assert summary['status_breakdown']['rejected'] == 1
        assert summary['status_breakdown']['pending'] == 1
        assert summary['completion_rate'] >= 0.5  # At least 2 out of 4 completed
        
        # Generate full audit report
        report = audit_manager.generate_audit_report(session_id)
        
        assert report['summary']['total_flagged_records'] == 4
        assert report['summary']['completion_rate'] == 0.75


class TestAuditValidation:
    """Test cases for audit validation and error handling."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        yield temp_file.name
        try:
            os.unlink(temp_file.name)
        except (PermissionError, FileNotFoundError):
            pass  # Ignore cleanup errors on Windows
        
    @pytest.fixture
    def audit_manager(self, temp_db):
        """Create AuditManager instance for testing."""
        return AuditManager(db_path=temp_db)
        
    def test_invalid_record_operations(self, audit_manager):
        """Test operations on non-existent records."""
        # Test operations on non-existent record
        assert not audit_manager.assign_reviewer("nonexistent", "reviewer")
        assert not audit_manager.update_record("nonexistent", {}, "reviewer")
        assert not audit_manager.approve_record("nonexistent", "reviewer")
        assert not audit_manager.reject_record("nonexistent", "reviewer", "reason")
        
    def test_validation_error_handling(self, audit_manager):
        """Test handling of validation errors."""
        # Create record with validation issues
        record = HMORecord(
            council="",  # Empty council should cause validation error
            reference="invalid-ref",
            max_occupancy=-1  # Negative occupancy should cause validation error
        )
        
        # Validate the record
        record.validate_all_fields()
        
        # Should have validation errors
        assert len(record.validation_errors) > 0
        
        # Flag the record
        record_id = audit_manager.flag_record(
            record,
            "validation_test_session",
            "Multiple validation errors",
            "system"
        )
        
        # Verify record was flagged
        flagged_record = audit_manager.flagged_records[record_id]
        assert flagged_record.hmo_record.validation_errors
        
    def test_export_with_no_data(self, audit_manager):
        """Test export functionality with no data."""
        # Try to export from non-existent session
        exported_data = audit_manager.export_audited_data("nonexistent_session")
        assert exported_data == []
        
        # Try to generate report for non-existent session
        report = audit_manager.generate_audit_report("nonexistent_session")
        assert 'message' in report
        
    def test_concurrent_record_updates(self, audit_manager):
        """Test handling of concurrent record updates."""
        session_id = "concurrent_test_session"
        
        # Create and flag a record
        record = HMORecord(council="Test Council", reference="TEST001")
        record_id = audit_manager.flag_record(record, session_id, "Test")
        
        # Simulate concurrent updates
        updates1 = {'council': 'Updated Council 1'}
        updates2 = {'reference': 'UPDATED-REF-2'}
        
        # Both updates should succeed
        success1 = audit_manager.update_record(record_id, updates1, "reviewer1")
        success2 = audit_manager.update_record(record_id, updates2, "reviewer2")
        
        assert success1
        assert success2
        
        # Final record should have both updates
        final_record = audit_manager.flagged_records[record_id].hmo_record
        assert final_record.council == 'Updated Council 1'
        assert final_record.reference == 'UPDATED-REF-2'


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])