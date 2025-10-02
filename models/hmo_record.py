"""
HMO Record data model with validation and confidence scoring.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import re


@dataclass
class HMORecord:
    """
    Data model for HMO (Houses in Multiple Occupation) licensing records.
    
    Supports configurable field mappings and includes validation methods
    for each field type with confidence scoring.
    """
    
    # Core HMO fields as defined in requirements
    council: str = ""
    reference: str = ""
    hmo_address: str = ""
    licence_start: str = ""
    licence_expiry: str = ""
    max_occupancy: int = 0
    hmo_manager_name: str = ""
    hmo_manager_address: str = ""
    licence_holder_name: str = ""
    licence_holder_address: str = ""
    number_of_households: int = 0
    number_of_shared_kitchens: int = 0
    number_of_shared_bathrooms: int = 0
    number_of_shared_toilets: int = 0
    number_of_storeys: int = 0
    
    # Confidence scoring and metadata
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize confidence scores for all fields."""
        if not self.confidence_scores:
            self.confidence_scores = {field_name: 0.0 for field_name in self.get_field_names()}
    
    @classmethod
    def get_field_names(cls) -> List[str]:
        """Get list of all HMO data field names."""
        return [
            'council', 'reference', 'hmo_address', 'licence_start', 'licence_expiry',
            'max_occupancy', 'hmo_manager_name', 'hmo_manager_address',
            'licence_holder_name', 'licence_holder_address', 'number_of_households',
            'number_of_shared_kitchens', 'number_of_shared_bathrooms',
            'number_of_shared_toilets', 'number_of_storeys'
        ]
    
    def validate_council(self) -> float:
        """
        Validate council field.
        
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        if not self.council or not self.council.strip():
            self.validation_errors.append("Council field is empty")
            return 0.0
        
        # Basic validation - should be a reasonable council name
        council_clean = self.council.strip()
        if len(council_clean) < 3:
            self.validation_errors.append("Council name too short")
            return 0.3
        
        # Higher confidence if contains common council keywords
        council_keywords = ['council', 'borough', 'city', 'district', 'county']
        if any(keyword in council_clean.lower() for keyword in council_keywords):
            return 0.9
        
        return 0.7
    
    def validate_reference(self) -> float:
        """
        Validate reference field (license reference number).
        
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        if not self.reference or not self.reference.strip():
            self.validation_errors.append("Reference field is empty")
            return 0.0
        
        ref_clean = self.reference.strip()
        
        # Check for common reference patterns
        # Pattern 1: Letters followed by numbers (e.g., HMO123, LIC456)
        if re.match(r'^[A-Z]{2,5}\d+$', ref_clean.upper()):
            return 0.95
        
        # Pattern 2: Numbers with separators (e.g., 2023/001, 23-HMO-001)
        if re.match(r'^\d{2,4}[/-]\w+[/-]?\d*$', ref_clean):
            return 0.9
        
        # Pattern 3: Pure numbers
        if re.match(r'^\d{3,}$', ref_clean):
            return 0.8
        
        # Has some alphanumeric content
        if re.match(r'^[A-Z0-9/-]{3,}$', ref_clean.upper()):
            return 0.6
        
        return 0.4
    
    def validate_address(self, address_field: str) -> float:
        """
        Validate address fields (hmo_address, manager_address, holder_address).
        
        Args:
            address_field: The address string to validate
            
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        if not address_field or not address_field.strip():
            return 0.0
        
        address_clean = address_field.strip()
        
        # Very short addresses are likely incomplete
        if len(address_clean) < 10:
            return 0.3
        
        confidence = 0.5  # Base confidence
        
        # Check for UK postcode pattern
        uk_postcode_pattern = r'[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}'
        if re.search(uk_postcode_pattern, address_clean.upper()):
            confidence += 0.3
        
        # Check for street indicators
        street_indicators = ['street', 'road', 'avenue', 'lane', 'drive', 'close', 'way', 'place']
        if any(indicator in address_clean.lower() for indicator in street_indicators):
            confidence += 0.15
        
        # Check for house number
        if re.match(r'^\d+', address_clean.strip()):
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def validate_date(self, date_field: str) -> float:
        """
        Validate date fields (licence_start, licence_expiry).
        
        Args:
            date_field: The date string to validate
            
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        if not date_field or not date_field.strip():
            return 0.0
        
        date_clean = date_field.strip()
        
        # Try to parse various date formats
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD (preferred)
            r'^\d{2}/\d{2}/\d{4}$',  # DD/MM/YYYY
            r'^\d{2}-\d{2}-\d{4}$',  # DD-MM-YYYY
            r'^\d{1,2}/\d{1,2}/\d{4}$',  # D/M/YYYY or DD/M/YYYY
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, date_clean):
                # Higher confidence for ISO format
                if pattern == date_patterns[0]:
                    return 0.95
                return 0.8
        
        # Check for partial dates or text dates
        if re.search(r'\d{4}', date_clean):  # Contains a year
            return 0.4
        
        return 0.1
    
    def validate_numeric_field(self, value: int, field_name: str) -> float:
        """
        Validate numeric fields (occupancy, households, facilities, storeys).
        
        Args:
            value: The numeric value to validate
            field_name: Name of the field for context
            
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        # Negative values are invalid
        if value < 0:
            self.validation_errors.append(f"{field_name} cannot be negative")
            return 0.0
        
        # Zero might be valid for some fields but suspicious for others
        if value == 0:
            if field_name in ['max_occupancy', 'number_of_storeys']:
                self.validation_errors.append(f"{field_name} should not be zero")
                return 0.2
            return 0.6  # Zero might be valid for shared facilities
        
        # Reasonable ranges for different fields
        if field_name == 'max_occupancy':
            if 1 <= value <= 50:
                return 0.9
            elif value > 50:
                return 0.6  # Possible but unusual
        
        elif field_name == 'number_of_storeys':
            if 1 <= value <= 10:
                return 0.9
            elif value > 10:
                return 0.5  # Very tall buildings are unusual for HMOs
        
        elif field_name in ['number_of_households', 'number_of_shared_kitchens', 
                           'number_of_shared_bathrooms', 'number_of_shared_toilets']:
            if 1 <= value <= 20:
                return 0.9
            elif value > 20:
                return 0.6
        
        return 0.7  # Default for reasonable positive values
    
    def validate_name_field(self, name_field: str) -> float:
        """
        Validate name fields (manager_name, holder_name).
        
        Args:
            name_field: The name string to validate
            
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        if not name_field or not name_field.strip():
            return 0.0
        
        name_clean = name_field.strip()
        
        # Very short names are suspicious
        if len(name_clean) < 2:
            return 0.2
        
        # Check for reasonable name patterns
        # Should contain letters and possibly spaces, hyphens, apostrophes
        if re.match(r"^[A-Za-z\s\-'\.]+$", name_clean):
            # Check for at least two parts (first and last name)
            parts = name_clean.split()
            if len(parts) >= 2:
                return 0.9
            else:
                return 0.7  # Single name might be valid
        
        # Contains some letters but also other characters
        if re.search(r'[A-Za-z]', name_clean):
            return 0.5
        
        return 0.2
    
    def validate_all_fields(self) -> Dict[str, float]:
        """
        Validate all fields and update confidence scores.
        
        Returns:
            Dict[str, float]: Updated confidence scores for all fields
        """
        self.validation_errors.clear()
        
        # Validate each field type
        self.confidence_scores['council'] = self.validate_council()
        self.confidence_scores['reference'] = self.validate_reference()
        self.confidence_scores['hmo_address'] = self.validate_address(self.hmo_address)
        self.confidence_scores['licence_start'] = self.validate_date(self.licence_start)
        self.confidence_scores['licence_expiry'] = self.validate_date(self.licence_expiry)
        self.confidence_scores['hmo_manager_name'] = self.validate_name_field(self.hmo_manager_name)
        self.confidence_scores['hmo_manager_address'] = self.validate_address(self.hmo_manager_address)
        self.confidence_scores['licence_holder_name'] = self.validate_name_field(self.licence_holder_name)
        self.confidence_scores['licence_holder_address'] = self.validate_address(self.licence_holder_address)
        
        # Validate numeric fields
        self.confidence_scores['max_occupancy'] = self.validate_numeric_field(self.max_occupancy, 'max_occupancy')
        self.confidence_scores['number_of_households'] = self.validate_numeric_field(self.number_of_households, 'number_of_households')
        self.confidence_scores['number_of_shared_kitchens'] = self.validate_numeric_field(self.number_of_shared_kitchens, 'number_of_shared_kitchens')
        self.confidence_scores['number_of_shared_bathrooms'] = self.validate_numeric_field(self.number_of_shared_bathrooms, 'number_of_shared_bathrooms')
        self.confidence_scores['number_of_shared_toilets'] = self.validate_numeric_field(self.number_of_shared_toilets, 'number_of_shared_toilets')
        self.confidence_scores['number_of_storeys'] = self.validate_numeric_field(self.number_of_storeys, 'number_of_storeys')
        
        return self.confidence_scores
    
    def get_overall_confidence(self) -> float:
        """
        Calculate overall confidence score for the record.
        
        Returns:
            float: Overall confidence score (0.0 to 1.0)
        """
        if not self.confidence_scores:
            return 0.0
        
        # Weight critical fields more heavily
        critical_fields = ['council', 'reference', 'hmo_address']
        important_fields = ['licence_start', 'licence_expiry', 'max_occupancy']
        
        total_score = 0.0
        total_weight = 0.0
        
        for field, score in self.confidence_scores.items():
            if field in critical_fields:
                weight = 3.0
            elif field in important_fields:
                weight = 2.0
            else:
                weight = 1.0
            
            total_score += score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def is_flagged_for_review(self, threshold: float = 0.7) -> bool:
        """
        Check if record should be flagged for manual review.
        
        Args:
            threshold: Confidence threshold below which records are flagged
            
        Returns:
            bool: True if record should be flagged for review
        """
        overall_confidence = self.get_overall_confidence()
        return overall_confidence < threshold or len(self.validation_errors) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert record to dictionary format.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the record
        """
        return {
            'council': self.council,
            'reference': self.reference,
            'hmo_address': self.hmo_address,
            'licence_start': self.licence_start,
            'licence_expiry': self.licence_expiry,
            'max_occupancy': self.max_occupancy,
            'hmo_manager_name': self.hmo_manager_name,
            'hmo_manager_address': self.hmo_manager_address,
            'licence_holder_name': self.licence_holder_name,
            'licence_holder_address': self.licence_holder_address,
            'number_of_households': self.number_of_households,
            'number_of_shared_kitchens': self.number_of_shared_kitchens,
            'number_of_shared_bathrooms': self.number_of_shared_bathrooms,
            'number_of_shared_toilets': self.number_of_shared_toilets,
            'number_of_storeys': self.number_of_storeys,
            'confidence_scores': self.confidence_scores,
            'validation_errors': self.validation_errors
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HMORecord':
        """
        Create HMORecord from dictionary data.
        
        Args:
            data: Dictionary containing record data
            
        Returns:
            HMORecord: New HMORecord instance
        """
        # Make a copy to avoid modifying the original data
        data_copy = dict(data)
        
        # Extract confidence scores and validation errors if present
        confidence_scores = data_copy.pop('confidence_scores', {})
        validation_errors = data_copy.pop('validation_errors', [])
        extraction_metadata = data_copy.pop('extraction_metadata', {})
        
        # Create record with remaining data
        record = cls(**{k: v for k, v in data_copy.items() if k in cls.get_field_names()})
        
        # Set metadata (this will trigger __post_init__ which initializes confidence_scores)
        if confidence_scores:
            record.confidence_scores = confidence_scores
        record.validation_errors = validation_errors
        record.extraction_metadata = extraction_metadata
        
        return record