"""
Confidence scoring system for HMO data extraction.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import statistics
import logging

logger = logging.getLogger(__name__)


class FieldType(Enum):
    """Enumeration of HMO field types for confidence calculation."""
    COUNCIL = "council"
    REFERENCE = "reference"
    ADDRESS = "hmo_address"
    DATE = "date"
    PERSON_NAME = "person_name"
    NUMERIC = "numeric"
    TEXT = "text"


@dataclass
class ConfidenceFactors:
    """Factors that contribute to confidence scoring."""
    pattern_match_score: float = 0.0
    context_score: float = 0.0
    format_validation_score: float = 0.0
    length_score: float = 0.0
    consistency_score: float = 0.0
    extraction_method_score: float = 0.0
    
    def overall_score(self) -> float:
        """Calculate weighted overall confidence score."""
        weights = {
            'pattern_match': 0.25,
            'context': 0.20,
            'format_validation': 0.20,
            'length': 0.10,
            'consistency': 0.15,
            'extraction_method': 0.10
        }
        
        total = (
            self.pattern_match_score * weights['pattern_match'] +
            self.context_score * weights['context'] +
            self.format_validation_score * weights['format_validation'] +
            self.length_score * weights['length'] +
            self.consistency_score * weights['consistency'] +
            self.extraction_method_score * weights['extraction_method']
        )
        
        return min(max(total, 0.0), 1.0)


@dataclass
class ExtractionResult:
    """Result of field extraction with confidence metrics."""
    field_name: str
    extracted_value: str
    normalized_value: str
    confidence_score: float
    confidence_factors: ConfidenceFactors
    extraction_method: str
    source_text: str = ""
    position: Tuple[int, int] = (0, 0)


class ConfidenceCalculator:
    """
    Calculate confidence scores for extracted HMO data using multiple factors.
    
    Implements field-specific confidence thresholds and ensemble scoring
    combining multiple extraction methods.
    """
    
    def __init__(self):
        # Field-specific confidence thresholds
        self.field_thresholds = {
            FieldType.COUNCIL: 0.75,
            FieldType.REFERENCE: 0.80,
            FieldType.ADDRESS: 0.70,
            FieldType.DATE: 0.85,
            FieldType.PERSON_NAME: 0.65,
            FieldType.NUMERIC: 0.80,
            FieldType.TEXT: 0.60
        }
        
        # Pattern confidence scores for different field types
        self.pattern_scores = {
            FieldType.REFERENCE: {
                r'^[A-Z]{2,4}\/\d{4,8}$': 0.95,
                r'^HMO\/\d{4,8}$': 0.90,
                r'^[A-Z]{1,3}\d{4,8}$': 0.85,
                r'^\d{6,8}$': 0.75
            },
            FieldType.DATE: {
                r'^\d{4}-\d{2}-\d{2}$': 0.95,
                r'^\d{1,2}\/\d{1,2}\/\d{4}$': 0.85,
                r'^\d{1,2}-\d{1,2}-\d{4}$': 0.85,
            },
            FieldType.ADDRESS: {
                r'\d+\s+[A-Za-z\s]+(?:Street|Road|Avenue|Lane|Drive|Close|Way|Place)': 0.90,
                r'[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}': 0.85,  # UK postcode
            }
        }
        
        # Context keywords that boost confidence
        self.context_keywords = {
            FieldType.COUNCIL: ['council', 'borough', 'district', 'authority'],
            FieldType.REFERENCE: ['reference', 'ref', 'licence', 'license', 'number', 'no'],
            FieldType.ADDRESS: ['address', 'property', 'premises', 'location'],
            FieldType.DATE: ['date', 'from', 'to', 'expires', 'expiry', 'start', 'end'],
            FieldType.PERSON_NAME: ['name', 'manager', 'holder', 'owner', 'contact'],
            FieldType.NUMERIC: ['occupancy', 'maximum', 'max', 'number', 'households', 'rooms']
        }
    
    def calculate_field_confidence(
        self, 
        field_name: str, 
        extracted_value: str,
        normalized_value: str = "",
        context: str = "",
        extraction_method: str = "unknown",
        source_text: str = "",
        position: Tuple[int, int] = (0, 0)
    ) -> ExtractionResult:
        """
        Calculate confidence score for a single extracted field.
        
        Args:
            field_name: Name of the HMO field
            extracted_value: Raw extracted value
            normalized_value: Normalized/cleaned value
            context: Surrounding text context
            extraction_method: Method used for extraction
            source_text: Original source text
            position: Position in source text (start, end)
            
        Returns:
            ExtractionResult with confidence metrics
        """
        field_type = self._get_field_type(field_name)
        
        # Calculate individual confidence factors
        factors = ConfidenceFactors()
        
        # Pattern matching score
        factors.pattern_match_score = self._calculate_pattern_score(
            field_type, normalized_value or extracted_value
        )
        
        # Context score
        factors.context_score = self._calculate_context_score(field_type, context)
        
        # Format validation score
        factors.format_validation_score = self._calculate_format_score(
            field_type, normalized_value or extracted_value
        )
        
        # Length score
        factors.length_score = self._calculate_length_score(
            field_type, extracted_value
        )
        
        # Extraction method score
        factors.extraction_method_score = self._calculate_method_score(extraction_method)
        
        # Overall confidence
        confidence = factors.overall_score()
        
        return ExtractionResult(
            field_name=field_name,
            extracted_value=extracted_value,
            normalized_value=normalized_value or extracted_value,
            confidence_score=confidence,
            confidence_factors=factors,
            extraction_method=extraction_method,
            source_text=source_text,
            position=position
        )
    
    def calculate_ensemble_confidence(
        self, 
        extraction_results: List[ExtractionResult]
    ) -> ExtractionResult:
        """
        Calculate ensemble confidence from multiple extraction methods.
        
        Args:
            extraction_results: List of results from different methods
            
        Returns:
            Best result with ensemble confidence score
        """
        if not extraction_results:
            raise ValueError("No extraction results provided")
        
        if len(extraction_results) == 1:
            return extraction_results[0]
        
        # Calculate ensemble score based on agreement and individual confidences
        best_result = max(extraction_results, key=lambda x: x.confidence_score)
        
        # Check for agreement between methods
        values = [result.normalized_value for result in extraction_results]
        unique_values = set(values)
        
        # Boost confidence if multiple methods agree
        if len(unique_values) == 1:
            # All methods agree
            agreement_boost = 0.1
        elif len(unique_values) <= len(values) / 2:
            # Majority agreement
            agreement_boost = 0.05
        else:
            # No clear agreement
            agreement_boost = -0.05
        
        # Calculate weighted average of confidences
        weights = [result.confidence_score for result in extraction_results]
        total_weight = sum(weights)
        
        if total_weight > 0:
            weighted_confidence = sum(
                result.confidence_score * (result.confidence_score / total_weight)
                for result in extraction_results
            )
        else:
            weighted_confidence = best_result.confidence_score
        
        # Apply agreement boost
        ensemble_confidence = min(weighted_confidence + agreement_boost, 1.0)
        
        # Update the best result with ensemble confidence
        best_result.confidence_score = ensemble_confidence
        best_result.extraction_method = f"ensemble({len(extraction_results)})"
        
        return best_result
    
    def is_above_threshold(self, field_name: str, confidence_score: float) -> bool:
        """
        Check if confidence score is above the threshold for the field type.
        
        Args:
            field_name: Name of the field
            confidence_score: Confidence score to check
            
        Returns:
            True if above threshold
        """
        field_type = self._get_field_type(field_name)
        threshold = self.field_thresholds.get(field_type, 0.7)
        return confidence_score >= threshold
    
    def flag_low_confidence_fields(
        self, 
        extraction_results: List[ExtractionResult],
        custom_threshold: Optional[float] = None
    ) -> List[str]:
        """
        Identify fields that should be flagged for manual review.
        
        Args:
            extraction_results: List of extraction results
            custom_threshold: Optional custom threshold (overrides field-specific)
            
        Returns:
            List of field names that should be flagged
        """
        flagged_fields = []
        
        for result in extraction_results:
            if custom_threshold is not None:
                threshold = custom_threshold
            else:
                field_type = self._get_field_type(result.field_name)
                threshold = self.field_thresholds.get(field_type, 0.7)
            
            if result.confidence_score < threshold:
                flagged_fields.append(result.field_name)
        
        return flagged_fields
    
    def generate_confidence_report(
        self, 
        extraction_results: List[ExtractionResult]
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive confidence report.
        
        Args:
            extraction_results: List of extraction results
            
        Returns:
            Dictionary containing confidence statistics and analysis
        """
        if not extraction_results:
            return {"error": "No extraction results provided"}
        
        confidences = [result.confidence_score for result in extraction_results]
        
        report = {
            "overall_statistics": {
                "total_fields": len(extraction_results),
                "mean_confidence": statistics.mean(confidences),
                "median_confidence": statistics.median(confidences),
                "min_confidence": min(confidences),
                "max_confidence": max(confidences),
                "std_deviation": statistics.stdev(confidences) if len(confidences) > 1 else 0.0
            },
            "field_analysis": {},
            "flagged_fields": self.flag_low_confidence_fields(extraction_results),
            "recommendations": []
        }
        
        # Per-field analysis
        for result in extraction_results:
            field_type = self._get_field_type(result.field_name)
            threshold = self.field_thresholds.get(field_type, 0.7)
            
            report["field_analysis"][result.field_name] = {
                "confidence_score": result.confidence_score,
                "threshold": threshold,
                "above_threshold": result.confidence_score >= threshold,
                "extraction_method": result.extraction_method,
                "confidence_factors": {
                    "pattern_match": result.confidence_factors.pattern_match_score,
                    "context": result.confidence_factors.context_score,
                    "format_validation": result.confidence_factors.format_validation_score,
                    "length": result.confidence_factors.length_score,
                    "consistency": result.confidence_factors.consistency_score,
                    "extraction_method": result.confidence_factors.extraction_method_score
                }
            }
        
        # Generate recommendations
        low_confidence_count = len(report["flagged_fields"])
        total_fields = len(extraction_results)
        
        if low_confidence_count == 0:
            report["recommendations"].append("All fields meet confidence thresholds. No manual review required.")
        elif low_confidence_count / total_fields > 0.5:
            report["recommendations"].append("More than 50% of fields flagged. Consider reviewing source document quality.")
        else:
            report["recommendations"].append(f"{low_confidence_count} fields flagged for manual review.")
        
        if report["overall_statistics"]["mean_confidence"] < 0.7:
            report["recommendations"].append("Overall confidence is low. Consider using additional extraction methods.")
        
        return report
    
    def _get_field_type(self, field_name: str) -> FieldType:
        """Map field name to field type."""
        field_mapping = {
            'council': FieldType.COUNCIL,
            'reference': FieldType.REFERENCE,
            'hmo_address': FieldType.ADDRESS,
            'licence_start': FieldType.DATE,
            'licence_expiry': FieldType.DATE,
            'max_occupancy': FieldType.NUMERIC,
            'hmo_manager_name': FieldType.PERSON_NAME,
            'hmo_manager_address': FieldType.ADDRESS,
            'licence_holder_name': FieldType.PERSON_NAME,
            'licence_holder_address': FieldType.ADDRESS,
            'number_of_households': FieldType.NUMERIC,
            'number_of_shared_kitchens': FieldType.NUMERIC,
            'number_of_shared_bathrooms': FieldType.NUMERIC,
            'number_of_shared_toilets': FieldType.NUMERIC,
            'number_of_storeys': FieldType.NUMERIC
        }
        
        return field_mapping.get(field_name, FieldType.TEXT)
    
    def _calculate_pattern_score(self, field_type: FieldType, value: str) -> float:
        """Calculate pattern matching confidence score."""
        if not value:
            return 0.0
        
        patterns = self.pattern_scores.get(field_type, {})
        
        for pattern, score in patterns.items():
            if re.match(pattern, value, re.IGNORECASE):
                return score
        
        # Default scores based on field type
        if field_type == FieldType.NUMERIC and value.isdigit():
            return 0.8
        elif field_type == FieldType.TEXT and len(value) > 2:
            return 0.6
        
        return 0.4
    
    def _calculate_context_score(self, field_type: FieldType, context: str) -> float:
        """Calculate context-based confidence score."""
        if not context:
            return 0.5  # Neutral score when no context
        
        context_lower = context.lower()
        keywords = self.context_keywords.get(field_type, [])
        
        matches = sum(1 for keyword in keywords if keyword in context_lower)
        
        if matches == 0:
            return 0.3
        elif matches == 1:
            return 0.7
        else:
            return 0.9
    
    def _calculate_format_score(self, field_type: FieldType, value: str) -> float:
        """Calculate format validation confidence score."""
        if not value:
            return 0.0
        
        if field_type == FieldType.DATE:
            # Check if it's a valid date format
            date_patterns = [
                r'^\d{4}-\d{2}-\d{2}$',
                r'^\d{1,2}\/\d{1,2}\/\d{4}$',
                r'^\d{1,2}-\d{1,2}-\d{4}$'
            ]
            for pattern in date_patterns:
                if re.match(pattern, value):
                    return 0.9
            return 0.3
        
        elif field_type == FieldType.NUMERIC:
            if value.isdigit():
                return 0.9
            elif re.match(r'^\d+\.\d+$', value):
                return 0.8
            return 0.2
        
        elif field_type == FieldType.PERSON_NAME:
            # Check for proper name format
            if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+', value):
                return 0.8
            return 0.5
        
        elif field_type == FieldType.ADDRESS:
            # Check for address-like format
            if re.search(r'\d+', value) and len(value) > 10:
                return 0.8
            return 0.5
        
        return 0.6  # Default for other types
    
    def _calculate_length_score(self, field_type: FieldType, value: str) -> float:
        """Calculate length-based confidence score."""
        if not value:
            return 0.0
        
        length = len(value.strip())
        
        # Field-specific length expectations
        if field_type == FieldType.REFERENCE:
            if 6 <= length <= 15:
                return 0.9
            elif 4 <= length <= 20:
                return 0.7
            else:
                return 0.4
        
        elif field_type == FieldType.PERSON_NAME:
            if 5 <= length <= 50:
                return 0.8
            elif 3 <= length <= 80:
                return 0.6
            else:
                return 0.3
        
        elif field_type == FieldType.ADDRESS:
            if 15 <= length <= 100:
                return 0.8
            elif 10 <= length <= 150:
                return 0.6
            else:
                return 0.4
        
        elif field_type == FieldType.NUMERIC:
            if 1 <= length <= 5:
                return 0.9
            else:
                return 0.5
        
        # General length check
        if length < 2:
            return 0.2
        elif length > 200:
            return 0.3
        else:
            return 0.7
    
    def _calculate_method_score(self, extraction_method: str) -> float:
        """Calculate confidence score based on extraction method."""
        method_scores = {
            'spacy_ner': 0.8,
            'regex_pattern': 0.9,
            'table_extraction': 0.85,
            'ocr': 0.6,
            'manual_pattern': 0.75,
            'ensemble': 0.9,
            'unknown': 0.5
        }
        
        return method_scores.get(extraction_method.lower(), 0.5)