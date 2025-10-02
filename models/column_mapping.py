"""
Column mapping configuration system for user-configurable CSV output.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import json
import re


class DataType(Enum):
    """Supported data types for column mapping validation."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DATE = "date"
    BOOLEAN = "boolean"


class ValidationRule(Enum):
    """Available validation rules for column mappings."""
    REQUIRED = "required"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    PATTERN = "pattern"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    DATE_FORMAT = "date_format"


@dataclass
class ColumnMapping:
    """
    Configuration for mapping system field names to user-defined column names.
    """
    
    system_field_name: str  # Internal field name (e.g., 'hmo_address')
    user_column_name: str   # User-defined column name (e.g., 'Property Address')
    data_type: DataType = DataType.STRING
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    is_required: bool = False
    default_value: Optional[Union[str, int, float]] = None
    
    def __post_init__(self):
        """Validate the column mapping configuration."""
        if not self.system_field_name or not self.user_column_name:
            raise ValueError("Both system_field_name and user_column_name are required")
        
        # Ensure data_type is DataType enum
        if isinstance(self.data_type, str):
            try:
                self.data_type = DataType(self.data_type.lower())
            except ValueError:
                raise ValueError(f"Invalid data type: {self.data_type}")
    
    def validate_value(self, value: Any) -> tuple[bool, str]:
        """
        Validate a value against this column's configuration.
        
        Args:
            value: Value to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            if self.is_required:
                return False, f"Required field '{self.user_column_name}' is empty"
            return True, ""
        
        # Type validation
        try:
            converted_value = self._convert_type(value)
        except (ValueError, TypeError) as e:
            return False, f"Invalid {self.data_type.value} value for '{self.user_column_name}': {str(e)}"
        
        # Apply validation rules
        for rule, rule_value in self.validation_rules.items():
            is_valid, error = self._apply_validation_rule(converted_value, rule, rule_value)
            if not is_valid:
                return False, error
        
        return True, ""
    
    def _convert_type(self, value: Any) -> Any:
        """Convert value to the specified data type."""
        if self.data_type == DataType.STRING:
            return str(value)
        elif self.data_type == DataType.INTEGER:
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return 0
            return int(float(value))  # Handle "5.0" -> 5
        elif self.data_type == DataType.FLOAT:
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return 0.0
            return float(value)
        elif self.data_type == DataType.DATE:
            return str(value)  # Date validation happens in validation rules
        elif self.data_type == DataType.BOOLEAN:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        else:
            return value
    
    def _apply_validation_rule(self, value: Any, rule: str, rule_value: Any) -> tuple[bool, str]:
        """Apply a specific validation rule to a value."""
        try:
            rule_enum = ValidationRule(rule)
        except ValueError:
            return True, ""  # Skip unknown rules
        
        if rule_enum == ValidationRule.REQUIRED:
            if rule_value and (value is None or (isinstance(value, str) and not value.strip())):
                return False, f"'{self.user_column_name}' is required"
        
        elif rule_enum == ValidationRule.MIN_LENGTH:
            if isinstance(value, str) and len(value) < rule_value:
                return False, f"'{self.user_column_name}' must be at least {rule_value} characters"
        
        elif rule_enum == ValidationRule.MAX_LENGTH:
            if isinstance(value, str) and len(value) > rule_value:
                return False, f"'{self.user_column_name}' must be no more than {rule_value} characters"
        
        elif rule_enum == ValidationRule.PATTERN:
            if isinstance(value, str) and not re.match(rule_value, value):
                return False, f"'{self.user_column_name}' does not match required pattern"
        
        elif rule_enum == ValidationRule.MIN_VALUE:
            if isinstance(value, (int, float)) and value < rule_value:
                return False, f"'{self.user_column_name}' must be at least {rule_value}"
        
        elif rule_enum == ValidationRule.MAX_VALUE:
            if isinstance(value, (int, float)) and value > rule_value:
                return False, f"'{self.user_column_name}' must be no more than {rule_value}"
        
        elif rule_enum == ValidationRule.DATE_FORMAT:
            if isinstance(value, str):
                # Simple date format validation
                date_patterns = {
                    'YYYY-MM-DD': r'^\d{4}-\d{2}-\d{2}$',
                    'DD/MM/YYYY': r'^\d{2}/\d{2}/\d{4}$',
                    'MM/DD/YYYY': r'^\d{2}/\d{2}/\d{4}$',
                    'DD-MM-YYYY': r'^\d{2}-\d{2}-\d{4}$'
                }
                
                pattern = date_patterns.get(rule_value, rule_value)
                if not re.match(pattern, value):
                    return False, f"'{self.user_column_name}' must match date format {rule_value}"
        
        return True, ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'system_field_name': self.system_field_name,
            'user_column_name': self.user_column_name,
            'data_type': self.data_type.value,
            'validation_rules': self.validation_rules,
            'description': self.description,
            'is_required': self.is_required,
            'default_value': self.default_value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColumnMapping':
        """Create ColumnMapping from dictionary."""
        return cls(
            system_field_name=data['system_field_name'],
            user_column_name=data['user_column_name'],
            data_type=DataType(data.get('data_type', 'string')),
            validation_rules=data.get('validation_rules', {}),
            description=data.get('description', ''),
            is_required=data.get('is_required', False),
            default_value=data.get('default_value')
        )


class ColumnMappingConfig:
    """
    Manages column mapping configurations with presets and validation.
    """
    
    def __init__(self):
        """Initialize with default mappings."""
        self.mappings: Dict[str, ColumnMapping] = {}
        self.presets: Dict[str, Dict[str, ColumnMapping]] = {}
        self._load_default_presets()
    
    def _load_default_presets(self):
        """Load default column mapping presets."""
        
        # Standard HMO preset
        standard_mappings = {
            'council': ColumnMapping(
                system_field_name='council',
                user_column_name='Council',
                data_type=DataType.STRING,
                description='Local authority/council name',
                is_required=True,
                validation_rules={'min_length': 2}
            ),
            'reference': ColumnMapping(
                system_field_name='reference',
                user_column_name='Reference',
                data_type=DataType.STRING,
                description='HMO license reference number',
                is_required=True,
                validation_rules={'min_length': 3}
            ),
            'hmo_address': ColumnMapping(
                system_field_name='hmo_address',
                user_column_name='HMO Address',
                data_type=DataType.STRING,
                description='Address of the HMO property',
                is_required=True,
                validation_rules={'min_length': 10}
            ),
            'licence_start': ColumnMapping(
                system_field_name='licence_start',
                user_column_name='Licence Start Date',
                data_type=DataType.DATE,
                description='License start date',
                validation_rules={'date_format': 'YYYY-MM-DD'}
            ),
            'licence_expiry': ColumnMapping(
                system_field_name='licence_expiry',
                user_column_name='Licence Expiry Date',
                data_type=DataType.DATE,
                description='License expiry date',
                validation_rules={'date_format': 'YYYY-MM-DD'}
            ),
            'max_occupancy': ColumnMapping(
                system_field_name='max_occupancy',
                user_column_name='Maximum Occupancy',
                data_type=DataType.INTEGER,
                description='Maximum number of occupants allowed',
                validation_rules={'min_value': 1, 'max_value': 100}
            ),
            'hmo_manager_name': ColumnMapping(
                system_field_name='hmo_manager_name',
                user_column_name='Manager Name',
                data_type=DataType.STRING,
                description='Name of the HMO manager'
            ),
            'hmo_manager_address': ColumnMapping(
                system_field_name='hmo_manager_address',
                user_column_name='Manager Address',
                data_type=DataType.STRING,
                description='Address of the HMO manager'
            ),
            'licence_holder_name': ColumnMapping(
                system_field_name='licence_holder_name',
                user_column_name='Licence Holder Name',
                data_type=DataType.STRING,
                description='Name of the license holder'
            ),
            'licence_holder_address': ColumnMapping(
                system_field_name='licence_holder_address',
                user_column_name='Licence Holder Address',
                data_type=DataType.STRING,
                description='Address of the license holder'
            ),
            'number_of_households': ColumnMapping(
                system_field_name='number_of_households',
                user_column_name='Number of Households',
                data_type=DataType.INTEGER,
                description='Number of separate households',
                validation_rules={'min_value': 0, 'max_value': 50}
            ),
            'number_of_shared_kitchens': ColumnMapping(
                system_field_name='number_of_shared_kitchens',
                user_column_name='Shared Kitchens',
                data_type=DataType.INTEGER,
                description='Number of shared kitchen facilities',
                validation_rules={'min_value': 0, 'max_value': 20}
            ),
            'number_of_shared_bathrooms': ColumnMapping(
                system_field_name='number_of_shared_bathrooms',
                user_column_name='Shared Bathrooms',
                data_type=DataType.INTEGER,
                description='Number of shared bathroom facilities',
                validation_rules={'min_value': 0, 'max_value': 20}
            ),
            'number_of_shared_toilets': ColumnMapping(
                system_field_name='number_of_shared_toilets',
                user_column_name='Shared Toilets',
                data_type=DataType.INTEGER,
                description='Number of shared toilet facilities',
                validation_rules={'min_value': 0, 'max_value': 20}
            ),
            'number_of_storeys': ColumnMapping(
                system_field_name='number_of_storeys',
                user_column_name='Number of Storeys',
                data_type=DataType.INTEGER,
                description='Number of floors/storeys in the building',
                validation_rules={'min_value': 1, 'max_value': 20}
            )
        }
        
        self.presets['standard'] = standard_mappings
        
        # Compact preset (fewer columns)
        compact_mappings = {
            'council': standard_mappings['council'],
            'reference': standard_mappings['reference'],
            'hmo_address': standard_mappings['hmo_address'],
            'licence_start': standard_mappings['licence_start'],
            'licence_expiry': standard_mappings['licence_expiry'],
            'max_occupancy': standard_mappings['max_occupancy']
        }
        
        self.presets['compact'] = compact_mappings
        
        # Detailed preset (all fields with additional validation)
        detailed_mappings = dict(standard_mappings)
        # Add stricter validation for detailed preset
        detailed_mappings['hmo_address'].validation_rules.update({'min_length': 15})
        detailed_mappings['hmo_manager_name'].validation_rules.update({'min_length': 2})
        detailed_mappings['licence_holder_name'].validation_rules.update({'min_length': 2})
        
        self.presets['detailed'] = detailed_mappings
        
        # Set default to standard
        self.mappings = dict(standard_mappings)
    
    def load_preset(self, preset_name: str) -> bool:
        """
        Load a predefined column mapping preset.
        
        Args:
            preset_name: Name of the preset to load
            
        Returns:
            bool: True if preset loaded successfully
        """
        if preset_name in self.presets:
            self.mappings = dict(self.presets[preset_name])
            return True
        return False
    
    def get_available_presets(self) -> List[str]:
        """Get list of available preset names."""
        return list(self.presets.keys())
    
    def add_mapping(self, mapping: ColumnMapping) -> bool:
        """
        Add or update a column mapping.
        
        Args:
            mapping: ColumnMapping to add
            
        Returns:
            bool: True if added successfully
        """
        try:
            # Validate the mapping
            is_valid, error = self.validate_mapping(mapping)
            if not is_valid:
                raise ValueError(error)
            
            self.mappings[mapping.system_field_name] = mapping
            return True
        except Exception:
            return False
    
    def remove_mapping(self, system_field_name: str) -> bool:
        """
        Remove a column mapping.
        
        Args:
            system_field_name: System field name to remove
            
        Returns:
            bool: True if removed successfully
        """
        if system_field_name in self.mappings:
            del self.mappings[system_field_name]
            return True
        return False
    
    def get_mapping(self, system_field_name: str) -> Optional[ColumnMapping]:
        """
        Get a specific column mapping.
        
        Args:
            system_field_name: System field name to get
            
        Returns:
            ColumnMapping or None if not found
        """
        return self.mappings.get(system_field_name)
    
    def get_all_mappings(self) -> Dict[str, ColumnMapping]:
        """Get all current column mappings."""
        return dict(self.mappings)
    
    def get_user_column_names(self) -> List[str]:
        """Get list of user-defined column names in order."""
        return [mapping.user_column_name for mapping in self.mappings.values()]
    
    def get_system_field_names(self) -> List[str]:
        """Get list of system field names in order."""
        return list(self.mappings.keys())
    
    def validate_mapping(self, mapping: ColumnMapping) -> tuple[bool, str]:
        """
        Validate a column mapping configuration.
        
        Args:
            mapping: ColumnMapping to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # Check for duplicate user column names
        for existing_field, existing_mapping in self.mappings.items():
            if (existing_field != mapping.system_field_name and 
                existing_mapping.user_column_name == mapping.user_column_name):
                return False, f"Column name '{mapping.user_column_name}' is already used"
        
        # Validate column name format
        if not re.match(r'^[A-Za-z][A-Za-z0-9\s_-]*$', mapping.user_column_name):
            return False, "Column name must start with a letter and contain only letters, numbers, spaces, underscores, and hyphens"
        
        # Validate validation rules
        for rule, value in mapping.validation_rules.items():
            try:
                ValidationRule(rule)
            except ValueError:
                return False, f"Unknown validation rule: {rule}"
        
        return True, ""
    
    def validate_config(self) -> tuple[bool, List[str]]:
        """
        Validate the entire column mapping configuration.
        
        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for duplicate column names
        user_names = [mapping.user_column_name for mapping in self.mappings.values()]
        duplicates = set([name for name in user_names if user_names.count(name) > 1])
        
        for duplicate in duplicates:
            errors.append(f"Duplicate column name: '{duplicate}'")
        
        # Validate each mapping
        for mapping in self.mappings.values():
            is_valid, error = self.validate_mapping(mapping)
            if not is_valid:
                errors.append(error)
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            'mappings': {
                field_name: mapping.to_dict() 
                for field_name, mapping in self.mappings.items()
            }
        }
    
    def from_dict(self, data: Dict[str, Any]) -> bool:
        """
        Load configuration from dictionary.
        
        Args:
            data: Dictionary containing mapping configuration
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            mappings = {}
            for field_name, mapping_data in data.get('mappings', {}).items():
                mappings[field_name] = ColumnMapping.from_dict(mapping_data)
            
            # Validate the configuration
            temp_config = ColumnMappingConfig()
            temp_config.mappings = mappings
            is_valid, errors = temp_config.validate_config()
            
            if is_valid:
                self.mappings = mappings
                return True
            else:
                print(f"Configuration validation errors: {errors}")
                return False
                
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
    
    def save_to_file(self, file_path: str) -> bool:
        """
        Save configuration to JSON file.
        
        Args:
            file_path: Path to save the configuration
            
        Returns:
            bool: True if saved successfully
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def load_from_file(self, file_path: str) -> bool:
        """
        Load configuration from JSON file.
        
        Args:
            file_path: Path to load the configuration from
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return self.from_dict(data)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False