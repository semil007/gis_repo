"""
Unit tests for ColumnMapping configuration system.
"""
import unittest
import tempfile
import os
import json
import sys

# Add the parent directory to the path so we can import models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.column_mapping import ColumnMapping, ColumnMappingConfig, DataType, ValidationRule


class TestColumnMapping(unittest.TestCase):
    """Test cases for ColumnMapping class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mapping = ColumnMapping(
            system_field_name="hmo_address",
            user_column_name="Property Address",
            data_type=DataType.STRING,
            description="Address of the HMO property",
            is_required=True,
            validation_rules={"min_length": 10}
        )
    
    def test_initialization(self):
        """Test ColumnMapping initialization."""
        self.assertEqual(self.mapping.system_field_name, "hmo_address")
        self.assertEqual(self.mapping.user_column_name, "Property Address")
        self.assertEqual(self.mapping.data_type, DataType.STRING)
        self.assertTrue(self.mapping.is_required)
        self.assertEqual(self.mapping.validation_rules["min_length"], 10)
    
    def test_initialization_with_string_data_type(self):
        """Test initialization with string data type."""
        mapping = ColumnMapping(
            system_field_name="test_field",
            user_column_name="Test Field",
            data_type="integer"
        )
        self.assertEqual(mapping.data_type, DataType.INTEGER)
    
    def test_initialization_invalid_data_type(self):
        """Test initialization with invalid data type."""
        with self.assertRaises(ValueError):
            ColumnMapping(
                system_field_name="test_field",
                user_column_name="Test Field",
                data_type="invalid_type"
            )
    
    def test_initialization_missing_required_fields(self):
        """Test initialization with missing required fields."""
        with self.assertRaises(ValueError):
            ColumnMapping(system_field_name="", user_column_name="Test")
        
        with self.assertRaises(ValueError):
            ColumnMapping(system_field_name="test", user_column_name="")
    
    def test_validate_string_value(self):
        """Test string value validation."""
        # Valid string
        is_valid, error = self.mapping.validate_value("123 Test Street, Test City")
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        
        # String too short
        is_valid, error = self.mapping.validate_value("Short")
        self.assertFalse(is_valid)
        self.assertIn("at least", error.lower())
        
        # Empty required field
        is_valid, error = self.mapping.validate_value("")
        self.assertFalse(is_valid)
        self.assertIn("required", error.lower())
    
    def test_validate_integer_value(self):
        """Test integer value validation."""
        int_mapping = ColumnMapping(
            system_field_name="max_occupancy",
            user_column_name="Max Occupancy",
            data_type=DataType.INTEGER,
            validation_rules={"min_value": 1, "max_value": 50}
        )
        
        # Valid integer
        is_valid, error = int_mapping.validate_value(5)
        self.assertTrue(is_valid)
        
        # Valid string integer
        is_valid, error = int_mapping.validate_value("10")
        self.assertTrue(is_valid)
        
        # Below minimum
        is_valid, error = int_mapping.validate_value(0)
        self.assertFalse(is_valid)
        self.assertIn("at least", error.lower())
        
        # Above maximum
        is_valid, error = int_mapping.validate_value(100)
        self.assertFalse(is_valid)
        self.assertIn("no more than", error.lower())
        
        # Invalid integer
        is_valid, error = int_mapping.validate_value("not_a_number")
        self.assertFalse(is_valid)
        self.assertIn("invalid", error.lower())
    
    def test_validate_date_value(self):
        """Test date value validation."""
        date_mapping = ColumnMapping(
            system_field_name="licence_start",
            user_column_name="Start Date",
            data_type=DataType.DATE,
            validation_rules={"date_format": "YYYY-MM-DD"}
        )
        
        # Valid date format
        is_valid, error = date_mapping.validate_value("2023-01-01")
        self.assertTrue(is_valid)
        
        # Invalid date format
        is_valid, error = date_mapping.validate_value("01/01/2023")
        self.assertFalse(is_valid)
        self.assertIn("date format", error.lower())
    
    def test_validate_pattern_rule(self):
        """Test pattern validation rule."""
        pattern_mapping = ColumnMapping(
            system_field_name="reference",
            user_column_name="Reference",
            data_type=DataType.STRING,
            validation_rules={"pattern": r"^HMO\d+$"}
        )
        
        # Valid pattern
        is_valid, error = pattern_mapping.validate_value("HMO123")
        self.assertTrue(is_valid)
        
        # Invalid pattern
        is_valid, error = pattern_mapping.validate_value("ABC123")
        self.assertFalse(is_valid)
        self.assertIn("pattern", error.lower())
    
    def test_convert_type(self):
        """Test type conversion."""
        # String conversion
        result = self.mapping._convert_type(123)
        self.assertEqual(result, "123")
        self.assertIsInstance(result, str)
        
        # Integer conversion
        int_mapping = ColumnMapping("test", "Test", DataType.INTEGER)
        result = int_mapping._convert_type("5.0")
        self.assertEqual(result, 5)
        self.assertIsInstance(result, int)
        
        # Float conversion
        float_mapping = ColumnMapping("test", "Test", DataType.FLOAT)
        result = float_mapping._convert_type("5.5")
        self.assertEqual(result, 5.5)
        self.assertIsInstance(result, float)
        
        # Boolean conversion
        bool_mapping = ColumnMapping("test", "Test", DataType.BOOLEAN)
        self.assertTrue(bool_mapping._convert_type("true"))
        self.assertTrue(bool_mapping._convert_type("1"))
        self.assertTrue(bool_mapping._convert_type("yes"))
        self.assertFalse(bool_mapping._convert_type("false"))
        self.assertFalse(bool_mapping._convert_type("0"))
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        mapping_dict = self.mapping.to_dict()
        
        expected_keys = [
            'system_field_name', 'user_column_name', 'data_type',
            'validation_rules', 'description', 'is_required', 'default_value'
        ]
        
        for key in expected_keys:
            self.assertIn(key, mapping_dict)
        
        self.assertEqual(mapping_dict['system_field_name'], "hmo_address")
        self.assertEqual(mapping_dict['user_column_name'], "Property Address")
        self.assertEqual(mapping_dict['data_type'], "string")
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        mapping_dict = {
            'system_field_name': 'test_field',
            'user_column_name': 'Test Field',
            'data_type': 'integer',
            'validation_rules': {'min_value': 1},
            'description': 'Test description',
            'is_required': True,
            'default_value': 0
        }
        
        mapping = ColumnMapping.from_dict(mapping_dict)
        
        self.assertEqual(mapping.system_field_name, 'test_field')
        self.assertEqual(mapping.user_column_name, 'Test Field')
        self.assertEqual(mapping.data_type, DataType.INTEGER)
        self.assertEqual(mapping.validation_rules['min_value'], 1)
        self.assertTrue(mapping.is_required)


class TestColumnMappingConfig(unittest.TestCase):
    """Test cases for ColumnMappingConfig class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ColumnMappingConfig()
    
    def test_initialization(self):
        """Test ColumnMappingConfig initialization."""
        # Should have default mappings loaded
        self.assertGreater(len(self.config.mappings), 0)
        
        # Should have presets
        presets = self.config.get_available_presets()
        self.assertIn('standard', presets)
        self.assertIn('compact', presets)
        self.assertIn('detailed', presets)
    
    def test_load_preset(self):
        """Test loading presets."""
        # Load compact preset
        success = self.config.load_preset('compact')
        self.assertTrue(success)
        
        # Should have fewer mappings than standard
        compact_count = len(self.config.mappings)
        
        # Load standard preset
        self.config.load_preset('standard')
        standard_count = len(self.config.mappings)
        
        self.assertGreater(standard_count, compact_count)
        
        # Try invalid preset
        success = self.config.load_preset('invalid_preset')
        self.assertFalse(success)
    
    def test_add_mapping(self):
        """Test adding column mappings."""
        new_mapping = ColumnMapping(
            system_field_name="new_field",
            user_column_name="New Field",
            data_type=DataType.STRING
        )
        
        initial_count = len(self.config.mappings)
        success = self.config.add_mapping(new_mapping)
        
        self.assertTrue(success)
        self.assertEqual(len(self.config.mappings), initial_count + 1)
        self.assertIn("new_field", self.config.mappings)
    
    def test_add_duplicate_column_name(self):
        """Test adding mapping with duplicate column name."""
        # Get existing mapping
        existing_mapping = list(self.config.mappings.values())[0]
        
        # Try to add mapping with same user column name
        duplicate_mapping = ColumnMapping(
            system_field_name="different_field",
            user_column_name=existing_mapping.user_column_name,
            data_type=DataType.STRING
        )
        
        success = self.config.add_mapping(duplicate_mapping)
        self.assertFalse(success)
    
    def test_remove_mapping(self):
        """Test removing column mappings."""
        # Get a field to remove
        field_to_remove = list(self.config.mappings.keys())[0]
        initial_count = len(self.config.mappings)
        
        success = self.config.remove_mapping(field_to_remove)
        
        self.assertTrue(success)
        self.assertEqual(len(self.config.mappings), initial_count - 1)
        self.assertNotIn(field_to_remove, self.config.mappings)
        
        # Try to remove non-existent field
        success = self.config.remove_mapping("non_existent_field")
        self.assertFalse(success)
    
    def test_get_mapping(self):
        """Test getting specific mappings."""
        # Get existing mapping
        field_name = list(self.config.mappings.keys())[0]
        mapping = self.config.get_mapping(field_name)
        
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.system_field_name, field_name)
        
        # Try non-existent mapping
        mapping = self.config.get_mapping("non_existent_field")
        self.assertIsNone(mapping)
    
    def test_get_column_names(self):
        """Test getting column names."""
        user_names = self.config.get_user_column_names()
        system_names = self.config.get_system_field_names()
        
        self.assertIsInstance(user_names, list)
        self.assertIsInstance(system_names, list)
        self.assertEqual(len(user_names), len(system_names))
        self.assertGreater(len(user_names), 0)
    
    def test_validate_mapping(self):
        """Test mapping validation."""
        # Valid mapping
        valid_mapping = ColumnMapping(
            system_field_name="test_field",
            user_column_name="Test Field",
            data_type=DataType.STRING
        )
        
        is_valid, error = self.config.validate_mapping(valid_mapping)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        
        # Invalid column name (starts with number)
        invalid_mapping = ColumnMapping(
            system_field_name="test_field2",
            user_column_name="123 Invalid Name",
            data_type=DataType.STRING
        )
        
        is_valid, error = self.config.validate_mapping(invalid_mapping)
        self.assertFalse(is_valid)
        self.assertIn("letter", error.lower())
    
    def test_validate_config(self):
        """Test configuration validation."""
        # Valid config should pass
        is_valid, errors = self.config.validate_config()
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Add duplicate column name
        duplicate_mapping = ColumnMapping(
            system_field_name="new_field",
            user_column_name=list(self.config.mappings.values())[0].user_column_name,
            data_type=DataType.STRING
        )
        
        # Manually add to bypass validation
        self.config.mappings["new_field"] = duplicate_mapping
        
        is_valid, errors = self.config.validate_config()
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
    
    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        # Convert to dict
        config_dict = self.config.to_dict()
        
        self.assertIn('mappings', config_dict)
        self.assertIsInstance(config_dict['mappings'], dict)
        
        # Create new config from dict
        new_config = ColumnMappingConfig()
        success = new_config.from_dict(config_dict)
        
        self.assertTrue(success)
        self.assertEqual(len(new_config.mappings), len(self.config.mappings))
        
        # Check that mappings match
        for field_name, mapping in self.config.mappings.items():
            new_mapping = new_config.get_mapping(field_name)
            self.assertIsNotNone(new_mapping)
            self.assertEqual(new_mapping.user_column_name, mapping.user_column_name)
    
    def test_save_and_load_file(self):
        """Test saving and loading configuration files."""
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_file.close()
        
        try:
            # Save configuration
            success = self.config.save_to_file(temp_file.name)
            self.assertTrue(success)
            
            # Verify file exists and has content
            self.assertTrue(os.path.exists(temp_file.name))
            
            with open(temp_file.name, 'r') as f:
                data = json.load(f)
                self.assertIn('mappings', data)
            
            # Load configuration into new instance
            new_config = ColumnMappingConfig()
            success = new_config.load_from_file(temp_file.name)
            
            self.assertTrue(success)
            self.assertEqual(len(new_config.mappings), len(self.config.mappings))
            
        finally:
            # Clean up
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    def test_load_invalid_file(self):
        """Test loading from invalid file."""
        # Try to load non-existent file
        success = self.config.load_from_file("non_existent_file.json")
        self.assertFalse(success)
        
        # Create file with invalid JSON
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_file.write("invalid json content")
        temp_file.close()
        
        try:
            success = self.config.load_from_file(temp_file.name)
            self.assertFalse(success)
        finally:
            os.unlink(temp_file.name)


if __name__ == '__main__':
    unittest.main()