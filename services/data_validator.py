"""
Data validation service for HMO records.

Provides comprehensive validation rules, format checking, and cross-field validation
for extracted HMO licensing data.
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
import re
from dataclasses import dataclass
from models.hmo_record import HMORecord


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    confidence_score: float
    validation_errors: List[str]
    warnings: List[str]
    suggested_corrections: Dict[str, Any]


class DataValidator:
    """
    Comprehensive data validator for HMO records.
    
    Provides field-specific validation rules, format checking for dates, addresses,
    and numbers, and implements cross-field validation logic.
    """
    
    def __init__(self):
        """Initialize validator with validation rules and patterns."""
        self.date_formats = [
            '%Y-%m-%d',      # ISO format (preferred)
            '%d/%m/%Y',      # UK format
            '%d-%m-%Y',      # UK format with dashes
            '%d/%m/%y',      # Short year UK format
            '%d-%m-%y',      # Short year UK format with dashes
            '%Y/%m/%d',      # Alternative ISO
            '%m/%d/%Y',      # US format (less common in UK)
        ]
        
        # UK postcode regex pattern
        self.uk_postcode_pattern = re.compile(
            r'^[A-Z]{1,2}[0-9R][0-9A-Z]?\s?[0-9][A-Z]{2}$',
            re.IGNORECASE
        )
        
        # Common UK council name patterns
        self.council_patterns = [
            r'.*council.*',
            r'.*borough.*',
            r'.*city.*',
            r'.*district.*',
            r'.*county.*',
            r'.*authority.*'
        ]
        
        # Street name indicators
        self.street_indicators = [
            'street', 'road', 'avenue', 'lane', 'drive', 'close', 'way', 'place',
            'crescent', 'gardens', 'park', 'square', 'terrace', 'grove', 'court',
            'mews', 'walk', 'rise', 'hill', 'view', 'green', 'common'
        ]
        
        # License reference patterns
        self.license_patterns = [
            r'^[A-Z]{2,5}\d+$',                    # Letters + numbers (HMO123)
            r'^\d{2,4}[/-]\w+[/-]?\d*$',          # Year/code/number
            r'^[A-Z]+[/-]\d+[/-]?\d*$',           # Code/number format
            r'^\d{3,}$',                          # Pure numbers
            r'^[A-Z0-9/-]{3,}$'                   # Mixed alphanumeric
        ]
    
    def validate_record(self, record: HMORecord) -> ValidationResult:
        """
        Validate a complete HMO record.
        
        Args:
            record: HMORecord to validate
            
        Returns:
            ValidationResult: Comprehensive validation result
        """
        errors = []
        warnings = []
        suggestions = {}
        field_scores = {}
        
        # Validate individual fields
        field_scores['council'] = self._validate_council(record.council, errors, warnings, suggestions)
        field_scores['reference'] = self._validate_reference(record.reference, errors, warnings, suggestions)
        field_scores['hmo_address'] = self._validate_address(record.hmo_address, 'hmo_address', errors, warnings, suggestions)
        field_scores['licence_start'] = self._validate_date(record.licence_start, 'licence_start', errors, warnings, suggestions)
        field_scores['licence_expiry'] = self._validate_date(record.licence_expiry, 'licence_expiry', errors, warnings, suggestions)
        field_scores['max_occupancy'] = self._validate_occupancy(record.max_occupancy, errors, warnings, suggestions)
        field_scores['hmo_manager_name'] = self._validate_name(record.hmo_manager_name, 'hmo_manager_name', errors, warnings, suggestions)
        field_scores['hmo_manager_address'] = self._validate_address(record.hmo_manager_address, 'hmo_manager_address', errors, warnings, suggestions)
        field_scores['licence_holder_name'] = self._validate_name(record.licence_holder_name, 'licence_holder_name', errors, warnings, suggestions)
        field_scores['licence_holder_address'] = self._validate_address(record.licence_holder_address, 'licence_holder_address', errors, warnings, suggestions)
        field_scores['number_of_households'] = self._validate_count(record.number_of_households, 'number_of_households', errors, warnings, suggestions)
        field_scores['number_of_shared_kitchens'] = self._validate_count(record.number_of_shared_kitchens, 'number_of_shared_kitchens', errors, warnings, suggestions)
        field_scores['number_of_shared_bathrooms'] = self._validate_count(record.number_of_shared_bathrooms, 'number_of_shared_bathrooms', errors, warnings, suggestions)
        field_scores['number_of_shared_toilets'] = self._validate_count(record.number_of_shared_toilets, 'number_of_shared_toilets', errors, warnings, suggestions)
        field_scores['number_of_storeys'] = self._validate_storeys(record.number_of_storeys, errors, warnings, suggestions)
        
        # Perform cross-field validation
        self._validate_cross_fields(record, errors, warnings, suggestions)
        
        # Calculate overall confidence score
        confidence_score = self._calculate_overall_confidence(field_scores)
        
        # Determine if record is valid (no critical errors)
        critical_errors = [error for error in errors if 'critical' in error.lower() or 'required' in error.lower()]
        is_valid = len(critical_errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            confidence_score=confidence_score,
            validation_errors=errors,
            warnings=warnings,
            suggested_corrections=suggestions
        )
    
    def _validate_council(self, council: str, errors: List[str], warnings: List[str], suggestions: Dict[str, Any]) -> float:
        """Validate council field."""
        if not council or not council.strip():
            errors.append("Council field is required")
            return 0.0
        
        council_clean = council.strip()
        
        if len(council_clean) < 3:
            errors.append("Council name is too short")
            return 0.2
        
        # Check for council-like patterns
        council_lower = council_clean.lower()
        has_council_pattern = any(re.match(pattern, council_lower) for pattern in self.council_patterns)
        
        if has_council_pattern:
            return 0.95
        elif len(council_clean) >= 5:
            warnings.append("Council name doesn't match typical patterns")
            return 0.7
        else:
            warnings.append("Council name may be incomplete")
            return 0.5
    
    def _validate_reference(self, reference: str, errors: List[str], warnings: List[str], suggestions: Dict[str, Any]) -> float:
        """Validate license reference field."""
        if not reference or not reference.strip():
            errors.append("License reference is required")
            return 0.0
        
        ref_clean = reference.strip().upper()
        
        # Check against known patterns
        for pattern in self.license_patterns:
            if re.match(pattern, ref_clean):
                return 0.9
        
        # Check for reasonable alphanumeric content
        if re.match(r'^[A-Z0-9/-]{3,}$', ref_clean):
            warnings.append("License reference format is unusual")
            return 0.6
        
        errors.append("License reference format is invalid")
        suggestions['reference'] = "Should contain letters and/or numbers (e.g., HMO123, 2023/001)"
        return 0.3
    
    def _validate_address(self, address: str, field_name: str, errors: List[str], warnings: List[str], suggestions: Dict[str, Any]) -> float:
        """Validate address fields."""
        if not address or not address.strip():
            if field_name == 'hmo_address':
                errors.append("HMO address is required")
                return 0.0
            else:
                warnings.append(f"{field_name} is empty")
                return 0.0
        
        address_clean = address.strip()
        
        if len(address_clean) < 10:
            warnings.append(f"{field_name} appears incomplete")
            return 0.3
        
        confidence = 0.5
        
        # Check for UK postcode
        postcode_match = self.uk_postcode_pattern.search(address_clean)
        if postcode_match:
            confidence += 0.3
        else:
            warnings.append(f"{field_name} missing valid UK postcode")
        
        # Check for street indicators
        address_lower = address_clean.lower()
        has_street = any(indicator in address_lower for indicator in self.street_indicators)
        if has_street:
            confidence += 0.15
        
        # Check for house number
        if re.match(r'^\d+', address_clean):
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _validate_date(self, date_str: str, field_name: str, errors: List[str], warnings: List[str], suggestions: Dict[str, Any]) -> float:
        """Validate date fields."""
        if not date_str or not date_str.strip():
            if field_name in ['licence_start', 'licence_expiry']:
                errors.append(f"{field_name} is required")
                return 0.0
            return 0.0
        
        date_clean = date_str.strip()
        
        # Try to parse with different formats
        parsed_date = None
        format_used = None
        
        for date_format in self.date_formats:
            try:
                parsed_date = datetime.strptime(date_clean, date_format).date()
                format_used = date_format
                break
            except ValueError:
                continue
        
        if not parsed_date:
            errors.append(f"{field_name} has invalid date format")
            suggestions[field_name] = "Use format YYYY-MM-DD or DD/MM/YYYY"
            return 0.2
        
        # Check date reasonableness
        current_date = date.today()
        
        if field_name == 'licence_start':
            # Start date shouldn't be too far in the future
            if parsed_date > current_date.replace(year=current_date.year + 2):
                warnings.append("License start date is far in the future")
                return 0.6
        
        elif field_name == 'licence_expiry':
            # Expiry date shouldn't be in the distant past
            if parsed_date < current_date.replace(year=current_date.year - 10):
                warnings.append("License expiry date is very old")
                return 0.5
        
        # Higher confidence for ISO format
        if format_used == '%Y-%m-%d':
            return 0.95
        else:
            return 0.85
    
    def _validate_occupancy(self, occupancy: int, errors: List[str], warnings: List[str], suggestions: Dict[str, Any]) -> float:
        """Validate maximum occupancy field."""
        if occupancy <= 0:
            errors.append("Maximum occupancy must be greater than 0")
            return 0.0
        
        if occupancy > 100:
            warnings.append("Maximum occupancy is unusually high")
            return 0.6
        
        if occupancy > 50:
            warnings.append("Maximum occupancy is high for typical HMO")
            return 0.7
        
        return 0.9
    
    def _validate_name(self, name: str, field_name: str, errors: List[str], warnings: List[str], suggestions: Dict[str, Any]) -> float:
        """Validate name fields."""
        if not name or not name.strip():
            warnings.append(f"{field_name} is empty")
            return 0.0
        
        name_clean = name.strip()
        
        if len(name_clean) < 2:
            warnings.append(f"{field_name} is too short")
            return 0.2
        
        # Check for reasonable name pattern
        if re.match(r"^[A-Za-z\s\-'\.]+$", name_clean):
            parts = name_clean.split()
            if len(parts) >= 2:
                return 0.9
            else:
                warnings.append(f"{field_name} may be incomplete (single name)")
                return 0.7
        
        # Contains some letters but also other characters
        if re.search(r'[A-Za-z]', name_clean):
            warnings.append(f"{field_name} contains unusual characters")
            return 0.5
        
        warnings.append(f"{field_name} doesn't appear to be a valid name")
        return 0.2
    
    def _validate_count(self, count: int, field_name: str, errors: List[str], warnings: List[str], suggestions: Dict[str, Any]) -> float:
        """Validate count fields (households, facilities)."""
        if count < 0:
            errors.append(f"{field_name} cannot be negative")
            return 0.0
        
        if count == 0:
            # Zero might be valid for shared facilities
            return 0.6
        
        if count > 50:
            warnings.append(f"{field_name} is unusually high")
            return 0.6
        
        return 0.9
    
    def _validate_storeys(self, storeys: int, errors: List[str], warnings: List[str], suggestions: Dict[str, Any]) -> float:
        """Validate number of storeys."""
        if storeys <= 0:
            errors.append("Number of storeys must be greater than 0")
            return 0.0
        
        if storeys > 20:
            warnings.append("Number of storeys is unusually high for HMO")
            return 0.5
        
        if storeys > 10:
            warnings.append("Number of storeys is high for typical HMO")
            return 0.7
        
        return 0.9
    
    def _validate_cross_fields(self, record: HMORecord, errors: List[str], warnings: List[str], suggestions: Dict[str, Any]) -> None:
        """Perform cross-field validation."""
        # Validate date relationships
        if record.licence_start and record.licence_expiry:
            try:
                start_date = self._parse_date_flexible(record.licence_start)
                expiry_date = self._parse_date_flexible(record.licence_expiry)
                
                if start_date and expiry_date:
                    if expiry_date <= start_date:
                        errors.append("License expiry date must be after start date")
                    
                    # Check for reasonable license duration
                    duration_years = (expiry_date - start_date).days / 365.25
                    if duration_years > 10:
                        warnings.append("License duration is unusually long")
                    elif duration_years < 0.5:
                        warnings.append("License duration is very short")
            
            except Exception:
                pass  # Date parsing already handled in individual validation
        
        # Validate occupancy vs facilities relationship
        if record.max_occupancy > 0:
            if record.number_of_shared_bathrooms > 0:
                ratio = record.max_occupancy / record.number_of_shared_bathrooms
                if ratio > 10:
                    warnings.append("High occupancy to bathroom ratio")
            
            if record.number_of_shared_kitchens > 0:
                ratio = record.max_occupancy / record.number_of_shared_kitchens
                if ratio > 15:
                    warnings.append("High occupancy to kitchen ratio")
        
        # Validate households vs occupancy
        if record.number_of_households > 0 and record.max_occupancy > 0:
            if record.number_of_households > record.max_occupancy:
                warnings.append("Number of households exceeds maximum occupancy")
    
    def _parse_date_flexible(self, date_str: str) -> Optional[date]:
        """Parse date string using multiple formats."""
        if not date_str:
            return None
        
        for date_format in self.date_formats:
            try:
                return datetime.strptime(date_str.strip(), date_format).date()
            except ValueError:
                continue
        
        return None
    
    def _calculate_overall_confidence(self, field_scores: Dict[str, float]) -> float:
        """Calculate overall confidence score with weighted fields."""
        if not field_scores:
            return 0.0
        
        # Define field weights
        weights = {
            'council': 3.0,
            'reference': 3.0,
            'hmo_address': 3.0,
            'licence_start': 2.0,
            'licence_expiry': 2.0,
            'max_occupancy': 2.0,
            'hmo_manager_name': 1.5,
            'hmo_manager_address': 1.5,
            'licence_holder_name': 1.5,
            'licence_holder_address': 1.5,
            'number_of_households': 1.0,
            'number_of_shared_kitchens': 1.0,
            'number_of_shared_bathrooms': 1.0,
            'number_of_shared_toilets': 1.0,
            'number_of_storeys': 1.0
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for field, score in field_scores.items():
            weight = weights.get(field, 1.0)
            total_score += score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def validate_batch(self, records: List[HMORecord]) -> List[ValidationResult]:
        """
        Validate a batch of records.
        
        Args:
            records: List of HMORecord instances to validate
            
        Returns:
            List[ValidationResult]: Validation results for each record
        """
        return [self.validate_record(record) for record in records]
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """
        Generate summary statistics for validation results.
        
        Args:
            results: List of validation results
            
        Returns:
            Dict[str, Any]: Summary statistics
        """
        if not results:
            return {}
        
        total_records = len(results)
        valid_records = sum(1 for r in results if r.is_valid)
        avg_confidence = sum(r.confidence_score for r in results) / total_records
        
        # Count error types
        error_counts = {}
        warning_counts = {}
        
        for result in results:
            for error in result.validation_errors:
                error_counts[error] = error_counts.get(error, 0) + 1
            for warning in result.warnings:
                warning_counts[warning] = warning_counts.get(warning, 0) + 1
        
        return {
            'total_records': total_records,
            'valid_records': valid_records,
            'invalid_records': total_records - valid_records,
            'validation_rate': valid_records / total_records,
            'average_confidence': avg_confidence,
            'common_errors': sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'common_warnings': sorted(warning_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }