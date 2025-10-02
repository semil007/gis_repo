"""
Unit tests for HMORecord data model.
"""
import unittest
from datetime import datetime
import sys
import os

# Add the parent directory to the path so we can import models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.hmo_record import HMORecord


class TestHMORecord(unittest.TestCase):
    """Test cases for HMORecord class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_record = HMORecord(
            council="Test Borough Council",
            reference="HMO123456",
            hmo_address="123 Test Street, Test City, TC1 2AB",
            licence_start="2023-01-01",
            licence_expiry="2024-01-01",
            max_occupancy=6,
            hmo_manager_name="John Smith",
            hmo_manager_address="456 Manager Road, Test City, TC2 3CD",
            licence_holder_name="Jane Doe",
            licence_holder_address="789 Holder Avenue, Test City, TC3 4EF",
            number_of_households=3,
            number_of_shared_kitchens=1,
            number_of_shared_bathrooms=2,
            number_of_shared_toilets=2,
            number_of_storeys=3
        )
    
    def test_initialization(self):
        """Test HMORecord initialization."""
        record = HMORecord()
        
        # Check default values
        self.assertEqual(record.council, "")
        self.assertEqual(record.reference, "")
        self.assertEqual(record.max_occupancy, 0)
        self.assertIsInstance(record.confidence_scores, dict)
        self.assertIsInstance(record.validation_errors, list)
        
        # Check confidence scores are initialized
        field_names = HMORecord.get_field_names()
        for field_name in field_names:
            self.assertIn(field_name, record.confidence_scores)
            self.assertEqual(record.confidence_scores[field_name], 0.0)
    
    def test_get_field_names(self):
        """Test get_field_names class method."""
        field_names = HMORecord.get_field_names()
        
        expected_fields = [
            'council', 'reference', 'hmo_address', 'licence_start', 'licence_expiry',
            'max_occupancy', 'hmo_manager_name', 'hmo_manager_address',
            'licence_holder_name', 'licence_holder_address', 'number_of_households',
            'number_of_shared_kitchens', 'number_of_shared_bathrooms',
            'number_of_shared_toilets', 'number_of_storeys'
        ]
        
        self.assertEqual(len(field_names), len(expected_fields))
        for field in expected_fields:
            self.assertIn(field, field_names)
    
    def test_validate_council(self):
        """Test council field validation."""
        # Valid council names
        self.sample_record.council = "Test Borough Council"
        confidence = self.sample_record.validate_council()
        self.assertGreater(confidence, 0.8)
        
        self.sample_record.council = "Manchester City Council"
        confidence = self.sample_record.validate_council()
        self.assertGreater(confidence, 0.8)
        
        # Council without keywords but reasonable length
        self.sample_record.council = "Test Authority"
        confidence = self.sample_record.validate_council()
        self.assertGreater(confidence, 0.6)
        
        # Short council name
        self.sample_record.council = "TC"
        confidence = self.sample_record.validate_council()
        self.assertLess(confidence, 0.5)
        
        # Empty council
        self.sample_record.council = ""
        confidence = self.sample_record.validate_council()
        self.assertEqual(confidence, 0.0)
    
    def test_validate_reference(self):
        """Test reference field validation."""
        # Valid reference patterns
        test_cases = [
            ("HMO123", 0.9),
            ("LIC456789", 0.9),
            ("2023/001", 0.8),
            ("23-HMO-001", 0.8),
            ("123456", 0.7),
            ("ABC123DEF", 0.5),
            ("", 0.0),
            ("AB", 0.3)
        ]
        
        for reference, expected_min_confidence in test_cases:
            with self.subTest(reference=reference):
                self.sample_record.reference = reference
                confidence = self.sample_record.validate_reference()
                if expected_min_confidence == 0.0:
                    self.assertEqual(confidence, 0.0)
                else:
                    self.assertGreaterEqual(confidence, expected_min_confidence - 0.1)
    
    def test_validate_address(self):
        """Test address field validation."""
        # Valid UK address with postcode
        address = "123 Test Street, Test City, TC1 2AB"
        confidence = self.sample_record.validate_address(address)
        self.assertGreater(confidence, 0.8)
        
        # Address with street indicator but no postcode
        address = "456 Main Road, Test City"
        confidence = self.sample_record.validate_address(address)
        self.assertGreater(confidence, 0.6)
        
        # Short address
        address = "123 Test"
        confidence = self.sample_record.validate_address(address)
        self.assertLess(confidence, 0.5)
        
        # Empty address
        confidence = self.sample_record.validate_address("")
        self.assertEqual(confidence, 0.0)
    
    def test_validate_date(self):
        """Test date field validation."""
        # Valid date formats
        test_cases = [
            ("2023-01-01", 0.9),  # ISO format
            ("01/01/2023", 0.7),  # DD/MM/YYYY
            ("01-01-2023", 0.7),  # DD-MM-YYYY
            ("1/1/2023", 0.7),    # D/M/YYYY
            ("2023", 0.3),        # Year only
            ("invalid", 0.1),     # Invalid
            ("", 0.0)             # Empty
        ]
        
        for date_str, expected_min_confidence in test_cases:
            with self.subTest(date=date_str):
                confidence = self.sample_record.validate_date(date_str)
                if expected_min_confidence == 0.0:
                    self.assertEqual(confidence, 0.0)
                else:
                    self.assertGreaterEqual(confidence, expected_min_confidence - 0.1)
    
    def test_validate_numeric_field(self):
        """Test numeric field validation."""
        # Test max_occupancy
        confidence = self.sample_record.validate_numeric_field(6, 'max_occupancy')
        self.assertGreater(confidence, 0.8)
        
        confidence = self.sample_record.validate_numeric_field(0, 'max_occupancy')
        self.assertLess(confidence, 0.3)
        
        confidence = self.sample_record.validate_numeric_field(-1, 'max_occupancy')
        self.assertEqual(confidence, 0.0)
        
        # Test number_of_storeys
        confidence = self.sample_record.validate_numeric_field(3, 'number_of_storeys')
        self.assertGreater(confidence, 0.8)
        
        confidence = self.sample_record.validate_numeric_field(0, 'number_of_storeys')
        self.assertLess(confidence, 0.3)
        
        # Test shared facilities (zero might be valid)
        confidence = self.sample_record.validate_numeric_field(0, 'number_of_shared_kitchens')
        self.assertGreater(confidence, 0.5)
    
    def test_validate_name_field(self):
        """Test name field validation."""
        # Valid names
        test_cases = [
            ("John Smith", 0.8),
            ("Mary Jane Watson", 0.8),
            ("O'Connor", 0.6),
            ("Smith-Jones", 0.6),
            ("John", 0.6),
            ("J", 0.1),
            ("", 0.0),
            ("John123", 0.4)
        ]
        
        for name, expected_min_confidence in test_cases:
            with self.subTest(name=name):
                confidence = self.sample_record.validate_name_field(name)
                if expected_min_confidence == 0.0:
                    self.assertEqual(confidence, 0.0)
                else:
                    self.assertGreaterEqual(confidence, expected_min_confidence - 0.1)
    
    def test_validate_all_fields(self):
        """Test validation of all fields."""
        confidence_scores = self.sample_record.validate_all_fields()
        
        # Check that all fields have confidence scores
        field_names = HMORecord.get_field_names()
        for field_name in field_names:
            self.assertIn(field_name, confidence_scores)
            self.assertIsInstance(confidence_scores[field_name], float)
            self.assertGreaterEqual(confidence_scores[field_name], 0.0)
            self.assertLessEqual(confidence_scores[field_name], 1.0)
        
        # Check that sample record has high confidence
        overall_confidence = self.sample_record.get_overall_confidence()
        self.assertGreater(overall_confidence, 0.7)
    
    def test_get_overall_confidence(self):
        """Test overall confidence calculation."""
        # Test with empty record
        empty_record = HMORecord()
        empty_record.validate_all_fields()
        confidence = empty_record.get_overall_confidence()
        self.assertLess(confidence, 0.3)
        
        # Test with good record
        self.sample_record.validate_all_fields()
        confidence = self.sample_record.get_overall_confidence()
        self.assertGreater(confidence, 0.7)
    
    def test_is_flagged_for_review(self):
        """Test flagging logic for manual review."""
        # Good record should not be flagged
        self.sample_record.validate_all_fields()
        self.assertFalse(self.sample_record.is_flagged_for_review())
        
        # Record with validation errors should be flagged
        bad_record = HMORecord(council="", reference="")
        bad_record.validate_all_fields()
        self.assertTrue(bad_record.is_flagged_for_review())
        
        # Test custom threshold
        self.assertFalse(self.sample_record.is_flagged_for_review(threshold=0.5))
        self.assertTrue(bad_record.is_flagged_for_review(threshold=0.9))
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        record_dict = self.sample_record.to_dict()
        
        # Check all fields are present
        field_names = HMORecord.get_field_names()
        for field_name in field_names:
            self.assertIn(field_name, record_dict)
        
        # Check metadata fields
        self.assertIn('confidence_scores', record_dict)
        self.assertIn('validation_errors', record_dict)
        
        # Check values
        self.assertEqual(record_dict['council'], self.sample_record.council)
        self.assertEqual(record_dict['reference'], self.sample_record.reference)
        self.assertEqual(record_dict['max_occupancy'], self.sample_record.max_occupancy)
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        # Create record and convert to dict
        original_dict = self.sample_record.to_dict()
        
        # Create new record from dict
        new_record = HMORecord.from_dict(original_dict)
        
        # Check all fields match
        field_names = HMORecord.get_field_names()
        for field_name in field_names:
            original_value = getattr(self.sample_record, field_name)
            new_value = getattr(new_record, field_name)
            self.assertEqual(original_value, new_value)
        
        # Check metadata
        self.assertEqual(new_record.confidence_scores, self.sample_record.confidence_scores)
        self.assertEqual(new_record.validation_errors, self.sample_record.validation_errors)
    
    def test_from_dict_partial_data(self):
        """Test creation from dictionary with partial data."""
        partial_data = {
            'council': 'Test Council',
            'reference': 'TEST123',
            'hmo_address': '123 Test Street'
        }
        
        record = HMORecord.from_dict(partial_data)
        
        # Check specified fields
        self.assertEqual(record.council, 'Test Council')
        self.assertEqual(record.reference, 'TEST123')
        self.assertEqual(record.hmo_address, '123 Test Street')
        
        # Check default values for unspecified fields
        self.assertEqual(record.max_occupancy, 0)
        self.assertEqual(record.hmo_manager_name, "")
        
        # Check confidence scores are initialized
        self.assertIsInstance(record.confidence_scores, dict)
        self.assertGreater(len(record.confidence_scores), 0)


if __name__ == '__main__':
    unittest.main()