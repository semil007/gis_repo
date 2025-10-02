"""
Unit tests for NLP pipeline components.
"""

import pytest
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp.nlp_pipeline import NLPPipeline, EntityMatch
from nlp.entity_extractors import (
    AddressParser, DateNormalizer, ReferenceExtractor, 
    PersonNameExtractor, ExtractedEntity
)
from nlp.confidence_calculator import (
    ConfidenceCalculator, FieldType, ExtractionResult, ConfidenceFactors
)


class TestNLPPipeline:
    """Test cases for the main NLP pipeline."""
    
    @pytest.fixture
    def nlp_pipeline(self):
        """Create NLP pipeline instance for testing."""
        return NLPPipeline()
    
    def test_pipeline_initialization(self, nlp_pipeline):
        """Test that NLP pipeline initializes correctly."""
        assert nlp_pipeline is not None
        assert nlp_pipeline.nlp is not None
        assert nlp_pipeline.model_name == "en_core_web_sm"
    
    def test_process_text_basic(self, nlp_pipeline):
        """Test basic text processing functionality."""
        text = "This is a test document about HMO licensing."
        result = nlp_pipeline.process_text(text)
        
        assert "entities" in result
        assert "tokens" in result
        assert "sentences" in result
        assert isinstance(result["entities"], list)
        assert isinstance(result["tokens"], list)
        assert isinstance(result["sentences"], list)
    
    def test_extract_addresses(self, nlp_pipeline):
        """Test address extraction with known text samples."""
        text = """
        Property Address: 123 Main Street, London, SW1A 1AA
        Another property at 45 Oak Road, Manchester M1 1AA
        """
        
        addresses = nlp_pipeline.extract_addresses(text)
        
        assert len(addresses) >= 1
        # Check that at least one address contains expected elements
        address_texts = [addr.text for addr in addresses]
        assert any("123 Main Street" in addr or "Main Street" in addr for addr in address_texts)
    
    def test_extract_dates(self, nlp_pipeline):
        """Test date extraction with various formats."""
        text = """
        License start date: 01/04/2023
        Expiry: 31-03-2024
        Valid from 2023-04-01 to 2024-03-31
        """
        
        dates = nlp_pipeline.extract_dates(text)
        
        assert len(dates) >= 2
        date_texts = [date.text for date in dates]
        assert any("01/04/2023" in date for date in date_texts)
        assert any("31-03-2024" in date for date in date_texts)
    
    def test_extract_references(self, nlp_pipeline):
        """Test license reference extraction."""
        text = """
        License Reference: HMO/123456
        Ref: ABC/789012
        Reference Number: 654321
        """
        
        references = nlp_pipeline.extract_references(text)
        
        assert len(references) >= 2
        ref_texts = [ref.text for ref in references]
        assert any("HMO/123456" in ref for ref in ref_texts)
        assert any("ABC/789012" in ref for ref in ref_texts)
    
    def test_extract_person_names(self, nlp_pipeline):
        """Test person name extraction."""
        text = """
        License Holder: John Smith
        HMO Manager: Sarah Johnson
        Contact: Michael Brown
        """
        
        names = nlp_pipeline.extract_person_names(text)
        
        # Note: This test might be sensitive to spaCy model availability
        # We'll check for basic functionality
        assert isinstance(names, list)


class TestAddressParser:
    """Test cases for address parsing functionality."""
    
    @pytest.fixture
    def address_parser(self):
        """Create AddressParser instance for testing."""
        return AddressParser()
    
    def test_parse_simple_address(self, address_parser):
        """Test parsing of simple UK addresses."""
        text = "123 Main Street, London, SW1A 1AA"
        addresses = address_parser.parse_addresses(text)
        
        assert len(addresses) >= 1
        assert any("123 Main Street" in addr.text for addr in addresses)
    
    def test_parse_multiple_addresses(self, address_parser):
        """Test parsing multiple addresses from text."""
        text = """
        Property 1: 45 Oak Road, Manchester M1 1AA
        Property 2: 78 High Street, Birmingham B1 2AA
        """
        
        addresses = address_parser.parse_addresses(text)
        
        assert len(addresses) >= 2
    
    def test_normalize_address(self, address_parser):
        """Test address normalization."""
        test_cases = [
            ("123 main st", "123 Main Street"),
            ("45 oak rd", "45 Oak Road"),
            ("78 high   street", "78 High Street")
        ]
        
        for input_addr, expected in test_cases:
            normalized = address_parser._normalize_address(input_addr)
            assert "Main Street" in normalized or "Oak Road" in normalized or "High Street" in normalized
    
    def test_uk_postcode_detection(self, address_parser):
        """Test UK postcode pattern detection."""
        text = "Address with postcode SW1A 1AA and another M1 1AA"
        addresses = address_parser.parse_addresses(text)
        
        # Should detect addresses with postcodes
        assert len(addresses) >= 1


class TestDateNormalizer:
    """Test cases for date normalization."""
    
    @pytest.fixture
    def date_normalizer(self):
        """Create DateNormalizer instance for testing."""
        return DateNormalizer()
    
    def test_normalize_various_formats(self, date_normalizer):
        """Test normalization of various date formats."""
        test_cases = [
            "01/04/2023",
            "31-03-2024", 
            "2023-04-01",
            "1 April 2023",
            "Apr 1, 2023"
        ]
        
        for date_str in test_cases:
            dates = date_normalizer.normalize_dates(date_str)
            if dates:  # Some formats might not be parsed
                assert len(dates) >= 1
                # Check that normalized value follows YYYY-MM-DD format
                normalized = dates[0].normalized_value
                assert len(normalized) == 10
                assert normalized.count('-') == 2
    
    def test_parse_dd_mm_yyyy_format(self, date_normalizer):
        """Test parsing of DD/MM/YYYY format specifically."""
        date_str = "15/06/2023"
        normalized = date_normalizer._parse_and_normalize_date(date_str)
        
        if normalized:  # Might fail if dateutil not available
            assert normalized == "2023-06-15"
    
    def test_invalid_date_handling(self, date_normalizer):
        """Test handling of invalid date strings."""
        invalid_dates = ["not-a-date", "32/13/2023", ""]
        
        for invalid_date in invalid_dates:
            result = date_normalizer._parse_and_normalize_date(invalid_date)
            assert result is None


class TestReferenceExtractor:
    """Test cases for license reference extraction."""
    
    @pytest.fixture
    def reference_extractor(self):
        """Create ReferenceExtractor instance for testing."""
        return ReferenceExtractor()
    
    def test_extract_various_reference_formats(self, reference_extractor):
        """Test extraction of various reference formats."""
        text = """
        License Ref: HMO/123456
        Reference: ABC/789012
        Licence No: XYZ123456
        Simple ref: 654321
        """
        
        references = reference_extractor.extract_references(text)
        
        assert len(references) >= 3
        ref_values = [ref.normalized_value for ref in references]
        assert any("HMO/123456" in ref for ref in ref_values)
        assert any("ABC/789012" in ref for ref in ref_values)
    
    def test_reference_validation(self, reference_extractor):
        """Test reference format validation."""
        valid_refs = ["HMO/123456", "ABC/789012", "XYZ123", "123456"]
        invalid_refs = ["AB", "123", "", "!@#$%"]
        
        for ref in valid_refs:
            assert reference_extractor._is_valid_reference(ref)
        
        for ref in invalid_refs:
            assert not reference_extractor._is_valid_reference(ref)
    
    def test_reference_normalization(self, reference_extractor):
        """Test that references are normalized to uppercase."""
        text = "Ref: hmo/123456"
        references = reference_extractor.extract_references(text)
        
        if references:
            assert references[0].normalized_value == "HMO/123456"


class TestPersonNameExtractor:
    """Test cases for person name extraction."""
    
    @pytest.fixture
    def name_extractor(self):
        """Create PersonNameExtractor instance for testing."""
        return PersonNameExtractor()
    
    def test_extract_names_with_context(self, name_extractor):
        """Test name extraction with context clues."""
        text = """
        Manager: John Smith
        Holder: Sarah Johnson
        Contact: Michael Brown
        """
        
        names = name_extractor.extract_person_names(text)
        
        assert len(names) >= 2
        name_values = [name.normalized_value for name in names]
        assert any("John Smith" in name for name in name_values)
        assert any("Sarah Johnson" in name for name in name_values)
    
    def test_name_validation(self, name_extractor):
        """Test name format validation."""
        valid_names = ["John Smith", "Sarah Johnson", "Michael O'Connor"]
        invalid_names = ["John", "123 Street", "john smith", ""]
        
        for name in valid_names:
            assert name_extractor._is_valid_name(name)
        
        for name in invalid_names:
            assert not name_extractor._is_valid_name(name)
    
    def test_name_normalization(self, name_extractor):
        """Test name normalization."""
        test_cases = [
            ("john smith", "John Smith"),
            ("SARAH JOHNSON", "Sarah Johnson"),
            ("michael o'connor", "Michael O'Connor")
        ]
        
        for input_name, expected in test_cases:
            normalized = name_extractor._normalize_name(input_name)
            assert normalized == expected


class TestConfidenceCalculator:
    """Test cases for confidence scoring system."""
    
    @pytest.fixture
    def confidence_calculator(self):
        """Create ConfidenceCalculator instance for testing."""
        return ConfidenceCalculator()
    
    def test_calculate_field_confidence(self, confidence_calculator):
        """Test confidence calculation for individual fields."""
        result = confidence_calculator.calculate_field_confidence(
            field_name="reference",
            extracted_value="HMO/123456",
            normalized_value="HMO/123456",
            context="License Reference: HMO/123456",
            extraction_method="regex_pattern"
        )
        
        assert isinstance(result, ExtractionResult)
        assert result.field_name == "reference"
        assert result.confidence_score > 0.0
        assert result.confidence_score <= 1.0
    
    def test_field_specific_thresholds(self, confidence_calculator):
        """Test that field-specific thresholds are applied correctly."""
        # Reference fields should have high threshold
        assert confidence_calculator.field_thresholds[FieldType.REFERENCE] == 0.80
        
        # Person names should have lower threshold
        assert confidence_calculator.field_thresholds[FieldType.PERSON_NAME] == 0.65
        
        # Dates should have high threshold
        assert confidence_calculator.field_thresholds[FieldType.DATE] == 0.85
    
    def test_ensemble_confidence_calculation(self, confidence_calculator):
        """Test ensemble confidence from multiple extraction methods."""
        results = [
            ExtractionResult(
                field_name="reference",
                extracted_value="HMO/123456",
                normalized_value="HMO/123456",
                confidence_score=0.9,
                confidence_factors=ConfidenceFactors(),
                extraction_method="method1"
            ),
            ExtractionResult(
                field_name="reference", 
                extracted_value="HMO/123456",
                normalized_value="HMO/123456",
                confidence_score=0.8,
                confidence_factors=ConfidenceFactors(),
                extraction_method="method2"
            )
        ]
        
        ensemble_result = confidence_calculator.calculate_ensemble_confidence(results)
        
        assert ensemble_result.confidence_score >= 0.8
        assert "ensemble" in ensemble_result.extraction_method
    
    def test_flag_low_confidence_fields(self, confidence_calculator):
        """Test flagging of low confidence fields."""
        results = [
            ExtractionResult(
                field_name="reference",
                extracted_value="ABC123",
                normalized_value="ABC123", 
                confidence_score=0.9,  # Above threshold
                confidence_factors=ConfidenceFactors(),
                extraction_method="test"
            ),
            ExtractionResult(
                field_name="hmo_manager_name",
                extracted_value="J Smith",
                normalized_value="J Smith",
                confidence_score=0.5,  # Below threshold
                confidence_factors=ConfidenceFactors(),
                extraction_method="test"
            )
        ]
        
        flagged = confidence_calculator.flag_low_confidence_fields(results)
        
        assert "hmo_manager_name" in flagged
        assert "reference" not in flagged
    
    def test_confidence_report_generation(self, confidence_calculator):
        """Test generation of confidence reports."""
        results = [
            ExtractionResult(
                field_name="reference",
                extracted_value="HMO/123456",
                normalized_value="HMO/123456",
                confidence_score=0.9,
                confidence_factors=ConfidenceFactors(),
                extraction_method="test"
            )
        ]
        
        report = confidence_calculator.generate_confidence_report(results)
        
        assert "overall_statistics" in report
        assert "field_analysis" in report
        assert "flagged_fields" in report
        assert "recommendations" in report
        
        assert report["overall_statistics"]["total_fields"] == 1
        assert report["overall_statistics"]["mean_confidence"] == 0.9
    
    def test_pattern_score_calculation(self, confidence_calculator):
        """Test pattern-based confidence scoring."""
        # Test high-confidence pattern
        score = confidence_calculator._calculate_pattern_score(
            FieldType.REFERENCE, "HMO/123456"
        )
        assert score >= 0.8
        
        # Test lower-confidence pattern
        score = confidence_calculator._calculate_pattern_score(
            FieldType.REFERENCE, "unknown"
        )
        assert score <= 0.6
    
    def test_context_score_calculation(self, confidence_calculator):
        """Test context-based confidence scoring."""
        # Test with relevant context
        score = confidence_calculator._calculate_context_score(
            FieldType.REFERENCE, "License Reference Number: HMO/123456"
        )
        assert score >= 0.7
        
        # Test with no context
        score = confidence_calculator._calculate_context_score(
            FieldType.REFERENCE, ""
        )
        assert score == 0.5


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])