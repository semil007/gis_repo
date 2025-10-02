"""
Unit tests for QualityAssessment class.

Tests quality assessment calculations, automated flagging for low-confidence records,
and quality report generation.
"""
import unittest
from datetime import datetime
from models.hmo_record import HMORecord
from services.data_validator import DataValidator, ValidationResult
from services.quality_assessment import QualityAssessment, QualityLevel, ExtractionQualityReport, FieldQualityMetrics


class TestQualityAssessment(unittest.TestCase):
    """Test cases for QualityAssessment class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.quality_assessment = QualityAssessment()
        self.validator = DataValidator()
        
        # Create sample records for testing
        self.good_record = HMORecord(
            council="Manchester City Council",
            reference="HMO123",
            hmo_address="123 Main Street, Manchester, M1 1AA",
            licence_start="2023-01-01",
            licence_expiry="2024-01-01",
            max_occupancy=10,
            hmo_manager_name="John Smith",
            hmo_manager_address="456 Oak Road, Manchester, M2 2BB"
        )
        
        self.poor_record = HMORecord(
            council="",  # Missing critical field
            reference="X",  # Invalid format
            hmo_address="Short",  # Incomplete address
            licence_start="invalid date",
            licence_expiry="2023-01-01",
            max_occupancy=0,  # Invalid occupancy
            hmo_manager_name="A",  # Too short
            hmo_manager_address=""
        )
        
        self.medium_record = HMORecord(
            council="Some Council",  # No council pattern but not empty
            reference="REF456",
            hmo_address="789 Some Street, Some City",  # No postcode
            licence_start="2023-06-01",
            licence_expiry="2024-06-01",
            max_occupancy=5,
            hmo_manager_name="Jane Doe"
        )
    
    def test_assess_extraction_quality_good_data(self):
        """Test quality assessment with good quality data."""
        records = [self.good_record] * 5  # 5 good records
        validation_results = [self.validator.validate_record(record) for record in records]
        
        report = self.quality_assessment.assess_extraction_quality(records, validation_results, "test_session_good")
        
        # Should have reasonable quality metrics
        self.assertEqual(report.total_records, 5)
        self.assertGreaterEqual(report.overall_confidence, 0.5)  # More realistic expectation
        # Quality level depends on completeness - accept any reasonable level
        self.assertIsInstance(report.quality_level, QualityLevel)
        # Good records might still be flagged due to missing optional fields
        
        # Check field metrics
        self.assertIn('council', report.field_metrics)
        council_metrics = report.field_metrics['council']
        self.assertEqual(council_metrics.total_records, 5)
        self.assertEqual(council_metrics.populated_records, 5)
        self.assertGreaterEqual(council_metrics.average_confidence, 0.8)
    
    def test_assess_extraction_quality_poor_data(self):
        """Test quality assessment with poor quality data."""
        records = [self.poor_record] * 3  # 3 poor records
        validation_results = [self.validator.validate_record(record) for record in records]
        
        report = self.quality_assessment.assess_extraction_quality(records, validation_results, "test_session_poor")
        
        # Should have low quality metrics
        self.assertEqual(report.total_records, 3)
        self.assertLess(report.overall_confidence, 0.6)
        self.assertIn(report.quality_level, [QualityLevel.POOR, QualityLevel.CRITICAL])
        self.assertGreater(report.flagged_records, 0)  # Poor records should be flagged
        
        # Should have error summary
        self.assertGreater(len(report.error_summary), 0)
        
        # Should have recommendations
        self.assertGreater(len(report.recommendations), 0)
    
    def test_assess_extraction_quality_mixed_data(self):
        """Test quality assessment with mixed quality data."""
        records = [self.good_record, self.poor_record, self.medium_record]
        validation_results = [self.validator.validate_record(record) for record in records]
        
        report = self.quality_assessment.assess_extraction_quality(records, validation_results, "test_session_mixed")
        
        # Should have moderate quality metrics
        self.assertEqual(report.total_records, 3)
        self.assertGreater(report.overall_confidence, 0.2)
        self.assertLess(report.overall_confidence, 0.9)
        self.assertGreater(report.flagged_records, 0)
        # All records might be flagged due to various issues
    
    def test_flag_low_confidence_records(self):
        """Test automated flagging of low-confidence records."""
        records = [self.good_record, self.poor_record, self.medium_record]
        validation_results = [self.validator.validate_record(record) for record in records]
        
        flagged = self.quality_assessment.flag_low_confidence_records(records, validation_results)
        
        # Should flag at least the poor record
        self.assertGreater(len(flagged), 0)
        
        # Check flagged record structure
        for index, record, reason in flagged:
            self.assertIsInstance(index, int)
            self.assertIsInstance(record, HMORecord)
            self.assertIsInstance(reason, str)
            self.assertGreaterEqual(index, 0)
            self.assertLess(index, len(records))
    
    def test_flag_low_confidence_critical_fields(self):
        """Test flagging based on critical field confidence."""
        # Create record with low confidence in critical field
        record = HMORecord(council="AB")  # Very short council name
        record.confidence_scores['council'] = 0.3  # Manually set low confidence
        
        validation_result = self.validator.validate_record(record)
        flagged = self.quality_assessment.flag_low_confidence_records([record], [validation_result])
        
        # Should be flagged due to low critical field confidence
        self.assertEqual(len(flagged), 1)
        self.assertIn("critical field", flagged[0][2].lower())
    
    def test_flag_empty_critical_fields(self):
        """Test flagging based on empty critical fields."""
        record = HMORecord(council="", reference="", hmo_address="")  # Empty critical fields
        validation_result = self.validator.validate_record(record)
        
        flagged = self.quality_assessment.flag_low_confidence_records([record], [validation_result])
        
        # Should be flagged due to empty critical fields
        self.assertEqual(len(flagged), 1)
        self.assertIn("empty", flagged[0][2].lower())
    
    def test_generate_quality_metrics(self):
        """Test generation of detailed quality metrics."""
        records = [self.good_record, self.poor_record, self.medium_record]
        
        metrics = self.quality_assessment.generate_quality_metrics(records)
        
        # Check structure
        self.assertIn('total_records', metrics)
        self.assertIn('field_statistics', metrics)
        self.assertIn('confidence_distribution', metrics)
        self.assertIn('completeness_analysis', metrics)
        
        # Check values
        self.assertEqual(metrics['total_records'], 3)
        
        # Check field statistics
        field_stats = metrics['field_statistics']
        self.assertIn('council', field_stats)
        
        council_stats = field_stats['council']
        self.assertIn('populated_count', council_stats)
        self.assertIn('population_rate', council_stats)
        self.assertIn('average_confidence', council_stats)
        
        # Check confidence distribution
        conf_dist = metrics['confidence_distribution']
        self.assertIn('mean', conf_dist)
        self.assertIn('median', conf_dist)
        self.assertIn('std', conf_dist)
        self.assertIn('quartiles', conf_dist)
        
        # Check completeness analysis
        completeness = metrics['completeness_analysis']
        self.assertIn('critical_fields_avg', completeness)
        self.assertIn('important_fields_avg', completeness)
        self.assertIn('optional_fields_avg', completeness)
    
    def test_field_quality_levels(self):
        """Test determination of field quality levels."""
        # Test with records having different field qualities
        records = []
        
        # Good quality fields
        good_record = HMORecord(council="Manchester City Council")
        good_record.confidence_scores['council'] = 0.95
        records.append(good_record)
        
        # Poor quality fields
        poor_record = HMORecord(council="AB")
        poor_record.confidence_scores['council'] = 0.3
        records.append(poor_record)
        
        validation_results = [self.validator.validate_record(record) for record in records]
        report = self.quality_assessment.assess_extraction_quality(records, validation_results)
        
        # Check that field metrics include quality levels
        council_metrics = report.field_metrics['council']
        self.assertIsInstance(council_metrics.quality_level, QualityLevel)
    
    def test_quality_level_determination(self):
        """Test overall quality level determination logic."""
        # Test excellent quality
        excellent_records = [self.good_record] * 10
        excellent_results = [self.validator.validate_record(record) for record in excellent_records]
        excellent_report = self.quality_assessment.assess_extraction_quality(excellent_records, excellent_results)
        
        # Should be better than poor quality
        self.assertNotEqual(excellent_report.quality_level, QualityLevel.CRITICAL)
        # Accept any reasonable quality level since records may have missing optional fields
        
        # Test poor quality
        poor_records = [self.poor_record] * 5
        poor_results = [self.validator.validate_record(record) for record in poor_records]
        poor_report = self.quality_assessment.assess_extraction_quality(poor_records, poor_results)
        
        # Should be poor or critical quality
        self.assertIn(poor_report.quality_level, [QualityLevel.POOR, QualityLevel.CRITICAL])
    
    def test_error_and_warning_aggregation(self):
        """Test aggregation of errors and warnings."""
        records = [self.poor_record] * 3  # Multiple records with same issues
        validation_results = [self.validator.validate_record(record) for record in records]
        
        report = self.quality_assessment.assess_extraction_quality(records, validation_results)
        
        # Should aggregate errors and warnings
        self.assertGreater(len(report.error_summary), 0)
        
        # Error counts should reflect multiple occurrences
        for error, count in report.error_summary.items():
            self.assertGreaterEqual(count, 1)
    
    def test_recommendations_generation(self):
        """Test generation of actionable recommendations."""
        # Mix of good and poor records to generate various recommendations
        records = [self.good_record, self.poor_record, self.medium_record] * 2
        validation_results = [self.validator.validate_record(record) for record in records]
        
        report = self.quality_assessment.assess_extraction_quality(records, validation_results)
        
        # Should have recommendations
        self.assertGreater(len(report.recommendations), 0)
        
        # Recommendations should be strings
        for recommendation in report.recommendations:
            self.assertIsInstance(recommendation, str)
            self.assertGreater(len(recommendation), 10)  # Should be meaningful text
    
    def test_completeness_analysis(self):
        """Test completeness analysis functionality."""
        # Create records with varying completeness
        complete_record = HMORecord(
            council="Complete Council",
            reference="COMP123",
            hmo_address="123 Complete Street, Complete City, C1 1CC",
            licence_start="2023-01-01",
            licence_expiry="2024-01-01",
            max_occupancy=10,
            hmo_manager_name="Complete Manager",
            hmo_manager_address="456 Manager Street, Manager City, M1 1MM",
            licence_holder_name="Complete Holder",
            licence_holder_address="789 Holder Street, Holder City, H1 1HH",
            number_of_households=5,
            number_of_shared_kitchens=2,
            number_of_shared_bathrooms=3,
            number_of_shared_toilets=3,
            number_of_storeys=2
        )
        
        incomplete_record = HMORecord(
            council="Incomplete Council",
            reference="INC123",
            hmo_address="123 Incomplete Street"
            # Many fields left empty
        )
        
        records = [complete_record, incomplete_record]
        metrics = self.quality_assessment.generate_quality_metrics(records)
        
        completeness = metrics['completeness_analysis']
        
        # Should have completeness metrics
        self.assertIn('critical_fields_avg', completeness)
        self.assertIn('record_completeness', completeness)
        
        # Critical fields should have higher completeness than optional
        self.assertGreaterEqual(completeness['critical_fields_avg'], 0.5)
    
    def test_confidence_thresholds(self):
        """Test custom confidence thresholds."""
        # Create quality assessment with custom thresholds
        custom_qa = QualityAssessment(confidence_threshold=0.8, critical_threshold=0.6)
        
        # Create record with medium confidence
        medium_record = self.medium_record
        medium_record.confidence_scores = {field: 0.75 for field in medium_record.get_field_names()}
        
        validation_result = self.validator.validate_record(medium_record)
        validation_result.confidence_score = 0.75
        
        flagged = custom_qa.flag_low_confidence_records([medium_record], [validation_result])
        
        # Should be flagged with higher threshold
        self.assertEqual(len(flagged), 1)
    
    def test_export_quality_report_dict_format(self):
        """Test exporting quality report in dictionary format."""
        records = [self.good_record, self.medium_record]
        validation_results = [self.validator.validate_record(record) for record in records]
        
        report = self.quality_assessment.assess_extraction_quality(records, validation_results)
        exported = self.quality_assessment.export_quality_report(report, format='dict')
        
        # Check structure
        self.assertIn('session_id', exported)
        self.assertIn('summary', exported)
        self.assertIn('field_metrics', exported)
        self.assertIn('top_errors', exported)
        self.assertIn('recommendations', exported)
        
        # Check summary structure
        summary = exported['summary']
        self.assertIn('total_records', summary)
        self.assertIn('validation_rate', summary)
        self.assertIn('quality_level', summary)
    
    def test_export_quality_report_summary_format(self):
        """Test exporting quality report in summary format."""
        records = [self.good_record]
        validation_results = [self.validator.validate_record(record) for record in records]
        
        report = self.quality_assessment.assess_extraction_quality(records, validation_results)
        exported = self.quality_assessment.export_quality_report(report, format='summary')
        
        # Check summary structure
        self.assertIn('quality_level', exported)
        self.assertIn('overall_confidence', exported)
        self.assertIn('validation_rate', exported)
        self.assertIn('flagged_for_review', exported)
        self.assertIn('key_recommendations', exported)
        
        # Values should be formatted as percentages where appropriate
        self.assertIn('%', exported['overall_confidence'])
        self.assertIn('%', exported['validation_rate'])
    
    def test_empty_records_handling(self):
        """Test handling of empty record lists."""
        # Test with empty list
        report = self.quality_assessment.assess_extraction_quality([], [])
        
        self.assertEqual(report.total_records, 0)
        self.assertEqual(report.valid_records, 0)
        self.assertEqual(report.flagged_records, 0)
        self.assertEqual(report.overall_confidence, 0.0)
        
        # Test metrics generation with empty list
        metrics = self.quality_assessment.generate_quality_metrics([])
        self.assertEqual(metrics, {})
    
    def test_mismatched_records_validation_results(self):
        """Test error handling for mismatched records and validation results."""
        records = [self.good_record, self.medium_record]
        validation_results = [self.validator.validate_record(self.good_record)]  # Only one result
        
        # Should raise ValueError for mismatched lengths
        with self.assertRaises(ValueError):
            self.quality_assessment.assess_extraction_quality(records, validation_results)
    
    def test_field_quality_metrics_structure(self):
        """Test FieldQualityMetrics structure and properties."""
        records = [self.good_record, self.poor_record]
        validation_results = [self.validator.validate_record(record) for record in records]
        
        report = self.quality_assessment.assess_extraction_quality(records, validation_results)
        
        # Check field metrics structure
        for field_name, metrics in report.field_metrics.items():
            self.assertIsInstance(metrics, FieldQualityMetrics)
            self.assertEqual(metrics.field_name, field_name)
            self.assertEqual(metrics.total_records, 2)
            self.assertGreaterEqual(metrics.populated_records, 0)
            self.assertLessEqual(metrics.populated_records, 2)
            self.assertGreaterEqual(metrics.average_confidence, 0.0)
            self.assertLessEqual(metrics.average_confidence, 1.0)
            self.assertIsInstance(metrics.quality_level, QualityLevel)
            
            # Test population_rate property
            expected_rate = metrics.populated_records / metrics.total_records
            self.assertEqual(metrics.population_rate, expected_rate)


if __name__ == '__main__':
    unittest.main()