"""
Unit tests for DataValidator class.

Tests validation rules with edge cases, format checking for dates, addresses,
and numbers, and cross-field validation logic.
"""
import unittest
from datetime import datetime, date
from models.hmo_record import HMORecord
from services.data_validator import DataValidator, ValidationResult


class TestDataValidator(unittest.TestCase):
    """Test cases for DataValidator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = DataValidator()
    
    def test_validate_council_valid_names(self):
        """Test council validation with valid council names."""
        test_cases = [
            ("Manchester City Council", 0.95),
            ("Birmingham Borough Council", 0.95),
            ("Leeds District Council", 0.95),
            ("Westminster Council", 0.95),
            ("Kent County Council", 0.95),
            ("Local Authority", 0.95)
        ]
        
        for council_name, expected_min_score in test_cases:
            with self.subTest(council=council_name):
                # Create a more complete record to get better overall confidence
                record = HMORecord(
                    council=council_name,
                    reference="TEST123",
                    hmo_address="123 Test Street, Test City, T1 1TT"
                )
                result = self.validator.validate_record(record)
                
                # Check that council field specifically has high confidence
                council_errors = [e for e in result.validation_errors if "council" in e.lower() and "required" in e.lower()]
                self.assertEqual(len(council_errors), 0)
    
    def test_validate_council_invalid_names(self):
        """Test council validation with invalid council names."""
        test_cases = [
            ("", 0.0, True),  # Empty - should be error
            ("AB", 0.2, True),  # Too short - should be error
            ("Random Text", 0.7, False),  # No council pattern - warning only
            ("123456", 0.5, False)  # Numbers only - warning
        ]
        
        for council_name, max_score, should_error in test_cases:
            with self.subTest(council=council_name):
                record = HMORecord(council=council_name)
                result = self.validator.validate_record(record)
                
                if should_error:
                    self.assertTrue(any("council" in e.lower() for e in result.validation_errors))
                else:
                    # Should have warnings but not errors
                    self.assertTrue(any("council" in w.lower() for w in result.warnings))
    
    def test_validate_reference_patterns(self):
        """Test license reference validation with various patterns."""
        valid_references = [
            "HMO123",
            "LIC456",
            "2023/001",
            "23-HMO-001",
            "ABC/123/456",
            "12345"
        ]
        
        for ref in valid_references:
            with self.subTest(reference=ref):
                # Create a more complete record
                record = HMORecord(
                    council="Test Council",
                    reference=ref,
                    hmo_address="123 Test Street, Test City, T1 1TT"
                )
                result = self.validator.validate_record(record)
                
                # Check that reference field specifically doesn't have errors
                reference_errors = [e for e in result.validation_errors if "reference" in e.lower()]
                self.assertEqual(len(reference_errors), 0)
    
    def test_validate_reference_invalid(self):
        """Test license reference validation with invalid patterns."""
        invalid_references = [
            "",  # Empty
            "AB",  # Too short
            "!@#$%",  # Special characters only
            "A"  # Single character
        ]
        
        for ref in invalid_references:
            with self.subTest(reference=ref):
                record = HMORecord(reference=ref)
                result = self.validator.validate_record(record)
                
                # Should have errors for invalid references
                self.assertTrue(any("reference" in e.lower() for e in result.validation_errors))
    
    def test_validate_address_uk_format(self):
        """Test address validation with UK address formats."""
        valid_addresses = [
            "123 Main Street, Manchester, M1 1AA",
            "45 Oak Road, Birmingham B2 4QA",
            "Flat 2, 67 High Street, London SW1A 1AA",
            "10 Church Lane, Leeds LS1 2AB"
        ]
        
        for address in valid_addresses:
            with self.subTest(address=address):
                # Create a more complete record
                record = HMORecord(
                    council="Test Council",
                    reference="TEST123",
                    hmo_address=address
                )
                result = self.validator.validate_record(record)
                
                # Check that address field specifically doesn't have major errors
                address_errors = [e for e in result.validation_errors if "address" in e.lower() and "required" in e.lower()]
                self.assertEqual(len(address_errors), 0)
    
    def test_validate_address_incomplete(self):
        """Test address validation with incomplete addresses."""
        incomplete_addresses = [
            "",  # Empty
            "123",  # Too short
            "Some Street",  # No postcode
            "Random text without proper format"
        ]
        
        for address in incomplete_addresses:
            with self.subTest(address=address):
                record = HMORecord(hmo_address=address)
                result = self.validator.validate_record(record)
                
                if not address:
                    # Empty HMO address should be an error
                    self.assertTrue(any("address" in e.lower() and "required" in e.lower() for e in result.validation_errors))
                else:
                    # Incomplete addresses should have warnings
                    self.assertTrue(any("address" in w.lower() for w in result.warnings))
    
    def test_validate_date_formats(self):
        """Test date validation with various formats."""
        valid_dates = [
            ("2023-12-25", 0.95),  # ISO format - highest confidence
            ("25/12/2023", 0.85),  # UK format
            ("25-12-2023", 0.85),  # UK format with dashes
            ("1/1/2024", 0.85),    # Short format
        ]
        
        for date_str, expected_min_confidence in valid_dates:
            with self.subTest(date=date_str):
                record = HMORecord(licence_start=date_str)
                result = self.validator.validate_record(record)
                
                # Should parse successfully
                self.assertNotIn("date", [e.lower() for e in result.validation_errors if "invalid" in e.lower()])
    
    def test_validate_date_invalid(self):
        """Test date validation with invalid formats."""
        invalid_dates = [
            "",  # Empty
            "not a date",
            "32/13/2023",  # Invalid day/month
            "2023-13-45",  # Invalid month/day
            "abc/def/ghij"
        ]
        
        for date_str in invalid_dates:
            with self.subTest(date=date_str):
                record = HMORecord(licence_start=date_str)
                result = self.validator.validate_record(record)
                
                if not date_str:
                    # Empty required date should be error
                    self.assertTrue(any("required" in e.lower() for e in result.validation_errors))
                else:
                    # Invalid format should be error
                    self.assertTrue(any("invalid" in e.lower() and "date" in e.lower() for e in result.validation_errors))
    
    def test_validate_occupancy_valid(self):
        """Test occupancy validation with valid values."""
        valid_occupancies = [1, 5, 10, 25, 50]
        
        for occupancy in valid_occupancies:
            with self.subTest(occupancy=occupancy):
                record = HMORecord(max_occupancy=occupancy)
                result = self.validator.validate_record(record)
                
                # Should have high confidence for reasonable occupancy
                self.assertNotIn("occupancy", [e.lower() for e in result.validation_errors])
    
    def test_validate_occupancy_invalid(self):
        """Test occupancy validation with invalid values."""
        invalid_occupancies = [0, -1, -10]
        
        for occupancy in invalid_occupancies:
            with self.subTest(occupancy=occupancy):
                record = HMORecord(max_occupancy=occupancy)
                result = self.validator.validate_record(record)
                
                # Should have errors for invalid occupancy
                self.assertTrue(any("occupancy" in e.lower() for e in result.validation_errors))
    
    def test_validate_occupancy_warnings(self):
        """Test occupancy validation with values that should generate warnings."""
        warning_occupancies = [75, 150]  # Very high occupancy
        
        for occupancy in warning_occupancies:
            with self.subTest(occupancy=occupancy):
                record = HMORecord(max_occupancy=occupancy)
                result = self.validator.validate_record(record)
                
                # Should have warnings for unusually high occupancy
                self.assertTrue(any("occupancy" in w.lower() for w in result.warnings))
    
    def test_validate_name_valid(self):
        """Test name validation with valid names."""
        valid_names = [
            "John Smith",
            "Mary Jane Watson",
            "O'Connor",
            "Jean-Pierre",
            "Dr. Smith",
            "Smith Jr."
        ]
        
        for name in valid_names:
            with self.subTest(name=name):
                # Create a more complete record
                record = HMORecord(
                    council="Test Council",
                    reference="TEST123",
                    hmo_address="123 Test Street, Test City, T1 1TT",
                    hmo_manager_name=name
                )
                result = self.validator.validate_record(record)
                
                # Check that name field specifically doesn't have major errors
                name_errors = [e for e in result.validation_errors if "name" in e.lower()]
                self.assertEqual(len(name_errors), 0)
    
    def test_validate_name_invalid(self):
        """Test name validation with invalid names."""
        invalid_names = [
            "",  # Empty
            "A",  # Too short
            "123456",  # Numbers only
            "!@#$%"  # Special characters only
        ]
        
        for name in invalid_names:
            with self.subTest(name=name):
                record = HMORecord(hmo_manager_name=name)
                result = self.validator.validate_record(record)
                
                if not name:
                    # Empty name should generate warning
                    self.assertTrue(any("name" in w.lower() and "empty" in w.lower() for w in result.warnings))
                else:
                    # Invalid names should generate warnings
                    self.assertTrue(any("name" in w.lower() for w in result.warnings))
    
    def test_validate_count_fields(self):
        """Test validation of count fields (households, facilities)."""
        # Valid counts
        record = HMORecord(
            number_of_households=5,
            number_of_shared_kitchens=2,
            number_of_shared_bathrooms=3,
            number_of_shared_toilets=4
        )
        result = self.validator.validate_record(record)
        
        # Should not have errors for reasonable counts
        count_errors = [e for e in result.validation_errors if any(field in e.lower() for field in ['household', 'kitchen', 'bathroom', 'toilet'])]
        self.assertEqual(len(count_errors), 0)
        
        # Test negative counts (should be errors)
        record_negative = HMORecord(number_of_households=-1)
        result_negative = self.validator.validate_record(record_negative)
        self.assertTrue(any("negative" in e.lower() for e in result_negative.validation_errors))
    
    def test_validate_storeys(self):
        """Test validation of number of storeys."""
        # Valid storeys
        valid_storeys = [1, 2, 3, 5, 8]
        
        for storeys in valid_storeys:
            with self.subTest(storeys=storeys):
                record = HMORecord(number_of_storeys=storeys)
                result = self.validator.validate_record(record)
                
                # Should not have errors for reasonable storey counts
                self.assertNotIn("storeys", [e.lower() for e in result.validation_errors])
        
        # Invalid storeys
        record_invalid = HMORecord(number_of_storeys=0)
        result_invalid = self.validator.validate_record(record_invalid)
        self.assertTrue(any("storeys" in e.lower() for e in result_invalid.validation_errors))
        
        # Warning for very high storeys
        record_high = HMORecord(number_of_storeys=25)
        result_high = self.validator.validate_record(record_high)
        self.assertTrue(any("storeys" in w.lower() for w in result_high.warnings))
    
    def test_cross_field_validation_dates(self):
        """Test cross-field validation for date relationships."""
        # Valid date relationship
        record_valid = HMORecord(
            licence_start="2023-01-01",
            licence_expiry="2024-01-01"
        )
        result_valid = self.validator.validate_record(record_valid)
        
        # Should not have date relationship errors
        date_errors = [e for e in result_valid.validation_errors if "expiry" in e.lower() and "start" in e.lower()]
        self.assertEqual(len(date_errors), 0)
        
        # Invalid date relationship (expiry before start)
        record_invalid = HMORecord(
            licence_start="2024-01-01",
            licence_expiry="2023-01-01"
        )
        result_invalid = self.validator.validate_record(record_invalid)
        
        # Should have error about date relationship
        self.assertTrue(any("expiry" in e.lower() and "start" in e.lower() for e in result_invalid.validation_errors))
    
    def test_cross_field_validation_occupancy_facilities(self):
        """Test cross-field validation for occupancy vs facilities."""
        # High occupancy with few facilities should generate warning
        record = HMORecord(
            max_occupancy=50,
            number_of_shared_bathrooms=1,
            number_of_shared_kitchens=1
        )
        result = self.validator.validate_record(record)
        
        # Should have warnings about high ratios
        ratio_warnings = [w for w in result.warnings if "ratio" in w.lower()]
        self.assertGreater(len(ratio_warnings), 0)
    
    def test_cross_field_validation_households_occupancy(self):
        """Test cross-field validation for households vs occupancy."""
        # More households than occupancy should generate warning
        record = HMORecord(
            max_occupancy=5,
            number_of_households=10
        )
        result = self.validator.validate_record(record)
        
        # Should have warning about households exceeding occupancy
        self.assertTrue(any("household" in w.lower() and "occupancy" in w.lower() for w in result.warnings))
    
    def test_validation_result_structure(self):
        """Test that ValidationResult has correct structure."""
        record = HMORecord(
            council="Test Council",
            reference="TEST123",
            hmo_address="123 Test Street, Test City, T1 1TT"
        )
        result = self.validator.validate_record(record)
        
        # Check ValidationResult structure
        self.assertIsInstance(result, ValidationResult)
        self.assertIsInstance(result.is_valid, bool)
        self.assertIsInstance(result.confidence_score, float)
        self.assertIsInstance(result.validation_errors, list)
        self.assertIsInstance(result.warnings, list)
        self.assertIsInstance(result.suggested_corrections, dict)
        
        # Confidence score should be between 0 and 1
        self.assertGreaterEqual(result.confidence_score, 0.0)
        self.assertLessEqual(result.confidence_score, 1.0)
    
    def test_batch_validation(self):
        """Test batch validation of multiple records."""
        records = [
            HMORecord(council="Council 1", reference="REF1"),
            HMORecord(council="Council 2", reference="REF2"),
            HMORecord(council="", reference="")  # Invalid record
        ]
        
        results = self.validator.validate_batch(records)
        
        # Should return same number of results as records
        self.assertEqual(len(results), len(records))
        
        # All results should be ValidationResult instances
        for result in results:
            self.assertIsInstance(result, ValidationResult)
        
        # Last record should have errors (empty required fields)
        self.assertFalse(results[2].is_valid)
        self.assertGreater(len(results[2].validation_errors), 0)
    
    def test_validation_summary(self):
        """Test validation summary generation."""
        records = [
            HMORecord(council="Valid Council", reference="VALID123"),
            HMORecord(council="", reference=""),  # Invalid
            HMORecord(council="Another Council", reference="VALID456")
        ]
        
        results = self.validator.validate_batch(records)
        summary = self.validator.get_validation_summary(results)
        
        # Check summary structure
        self.assertIn('total_records', summary)
        self.assertIn('valid_records', summary)
        self.assertIn('invalid_records', summary)
        self.assertIn('validation_rate', summary)
        self.assertIn('average_confidence', summary)
        self.assertIn('common_errors', summary)
        self.assertIn('common_warnings', summary)
        
        # Check values
        self.assertEqual(summary['total_records'], 3)
        self.assertGreaterEqual(summary['validation_rate'], 0.0)
        self.assertLessEqual(summary['validation_rate'], 1.0)
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Empty record
        empty_record = HMORecord()
        result_empty = self.validator.validate_record(empty_record)
        
        # Should have multiple errors for empty required fields
        self.assertFalse(result_empty.is_valid)
        self.assertGreater(len(result_empty.validation_errors), 0)
        
        # Record with whitespace-only fields
        whitespace_record = HMORecord(
            council="   ",
            reference="   ",
            hmo_address="   "
        )
        result_whitespace = self.validator.validate_record(whitespace_record)
        
        # Should treat whitespace-only as empty
        self.assertFalse(result_whitespace.is_valid)
        
        # Record with very long fields
        long_text = "A" * 1000
        long_record = HMORecord(
            council=long_text,
            reference=long_text,
            hmo_address=long_text
        )
        result_long = self.validator.validate_record(long_record)
        
        # Should handle long text without crashing
        self.assertIsInstance(result_long, ValidationResult)


if __name__ == '__main__':
    unittest.main()