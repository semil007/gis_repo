"""
Quality assessment framework for HMO data extraction.

Provides extraction metrics, automated flagging for low-confidence records,
and generates quality reports with statistics.
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import statistics
from models.hmo_record import HMORecord
from services.data_validator import ValidationResult


class QualityLevel(Enum):
    """Quality levels for extracted data."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class FieldQualityMetrics:
    """Quality metrics for individual fields."""
    field_name: str
    total_records: int
    populated_records: int
    average_confidence: float
    min_confidence: float
    max_confidence: float
    validation_errors: int
    warnings: int
    quality_level: QualityLevel
    
    @property
    def population_rate(self) -> float:
        """Calculate field population rate."""
        return self.populated_records / self.total_records if self.total_records > 0 else 0.0


@dataclass
class ExtractionQualityReport:
    """Comprehensive quality report for extraction results."""
    session_id: str
    timestamp: datetime
    total_records: int
    valid_records: int
    flagged_records: int
    overall_confidence: float
    quality_level: QualityLevel
    field_metrics: Dict[str, FieldQualityMetrics]
    error_summary: Dict[str, int]
    warning_summary: Dict[str, int]
    recommendations: List[str]
    processing_metadata: Dict[str, Any] = field(default_factory=dict)


class QualityAssessment:
    """
    Quality assessment framework for HMO data extraction.
    
    Implements extraction metrics, automated flagging for low-confidence records,
    and generates comprehensive quality reports with statistics.
    """
    
    def __init__(self, confidence_threshold: float = 0.7, critical_threshold: float = 0.5):
        """
        Initialize quality assessment framework.
        
        Args:
            confidence_threshold: Threshold below which records are flagged
            critical_threshold: Threshold below which records are marked critical
        """
        self.confidence_threshold = confidence_threshold
        self.critical_threshold = critical_threshold
        
        # Define critical fields that must have good quality
        self.critical_fields = ['council', 'reference', 'hmo_address']
        self.important_fields = ['licence_start', 'licence_expiry', 'max_occupancy']
        self.optional_fields = [
            'hmo_manager_name', 'hmo_manager_address', 'licence_holder_name',
            'licence_holder_address', 'number_of_households', 'number_of_shared_kitchens',
            'number_of_shared_bathrooms', 'number_of_shared_toilets', 'number_of_storeys'
        ]
    
    def assess_extraction_quality(
        self, 
        records: List[HMORecord], 
        validation_results: List[ValidationResult],
        session_id: str = None
    ) -> ExtractionQualityReport:
        """
        Assess overall quality of extracted data.
        
        Args:
            records: List of extracted HMO records
            validation_results: List of validation results for each record
            session_id: Optional session identifier
            
        Returns:
            ExtractionQualityReport: Comprehensive quality assessment
        """
        if len(records) != len(validation_results):
            raise ValueError("Number of records must match number of validation results")
        
        session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Calculate field-level metrics
        field_metrics = self._calculate_field_metrics(records, validation_results)
        
        # Calculate overall metrics
        total_records = len(records)
        valid_records = sum(1 for result in validation_results if result.is_valid)
        flagged_records = self._count_flagged_records(records, validation_results)
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(validation_results)
        
        # Determine overall quality level
        quality_level = self._determine_quality_level(overall_confidence, valid_records, total_records)
        
        # Aggregate errors and warnings
        error_summary = self._aggregate_errors(validation_results)
        warning_summary = self._aggregate_warnings(validation_results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(field_metrics, error_summary, warning_summary)
        
        return ExtractionQualityReport(
            session_id=session_id,
            timestamp=datetime.now(),
            total_records=total_records,
            valid_records=valid_records,
            flagged_records=flagged_records,
            overall_confidence=overall_confidence,
            quality_level=quality_level,
            field_metrics=field_metrics,
            error_summary=error_summary,
            warning_summary=warning_summary,
            recommendations=recommendations
        )
    
    def flag_low_confidence_records(
        self, 
        records: List[HMORecord], 
        validation_results: List[ValidationResult]
    ) -> List[Tuple[int, HMORecord, str]]:
        """
        Identify records that should be flagged for manual review.
        
        Args:
            records: List of HMO records
            validation_results: List of validation results
            
        Returns:
            List[Tuple[int, HMORecord, str]]: List of (index, record, reason) tuples
        """
        flagged = []
        
        for i, (record, result) in enumerate(zip(records, validation_results)):
            flag_reasons = []
            
            # Check overall confidence
            if result.confidence_score < self.confidence_threshold:
                flag_reasons.append(f"Low overall confidence ({result.confidence_score:.2f})")
            
            # Check for validation errors
            if result.validation_errors:
                flag_reasons.append(f"Validation errors ({len(result.validation_errors)})")
            
            # Check critical fields
            for field in self.critical_fields:
                field_confidence = record.confidence_scores.get(field, 0.0)
                if field_confidence < self.critical_threshold:
                    flag_reasons.append(f"Critical field '{field}' low confidence ({field_confidence:.2f})")
            
            # Check for empty critical fields
            for field in self.critical_fields:
                field_value = getattr(record, field, "")
                if not field_value or not str(field_value).strip():
                    flag_reasons.append(f"Critical field '{field}' is empty")
            
            if flag_reasons:
                reason = "; ".join(flag_reasons)
                flagged.append((i, record, reason))
        
        return flagged
    
    def generate_quality_metrics(self, records: List[HMORecord]) -> Dict[str, Any]:
        """
        Generate detailed quality metrics for a set of records.
        
        Args:
            records: List of HMO records
            
        Returns:
            Dict[str, Any]: Detailed quality metrics
        """
        if not records:
            return {}
        
        metrics = {
            'total_records': len(records),
            'field_statistics': {},
            'confidence_distribution': {},
            'completeness_analysis': {}
        }
        
        # Analyze each field
        all_fields = HMORecord.get_field_names()
        
        for field in all_fields:
            field_values = []
            field_confidences = []
            populated_count = 0
            
            for record in records:
                value = getattr(record, field, "")
                confidence = record.confidence_scores.get(field, 0.0)
                
                field_confidences.append(confidence)
                
                if value and str(value).strip():
                    populated_count += 1
                    field_values.append(value)
            
            metrics['field_statistics'][field] = {
                'populated_count': populated_count,
                'population_rate': populated_count / len(records),
                'average_confidence': statistics.mean(field_confidences) if field_confidences else 0.0,
                'min_confidence': min(field_confidences) if field_confidences else 0.0,
                'max_confidence': max(field_confidences) if field_confidences else 0.0,
                'confidence_std': statistics.stdev(field_confidences) if len(field_confidences) > 1 else 0.0
            }
        
        # Overall confidence distribution
        all_confidences = []
        for record in records:
            overall_conf = record.get_overall_confidence()
            all_confidences.append(overall_conf)
        
        if all_confidences:
            metrics['confidence_distribution'] = {
                'mean': statistics.mean(all_confidences),
                'median': statistics.median(all_confidences),
                'std': statistics.stdev(all_confidences) if len(all_confidences) > 1 else 0.0,
                'min': min(all_confidences),
                'max': max(all_confidences),
                'quartiles': self._calculate_quartiles(all_confidences)
            }
        
        # Completeness analysis
        metrics['completeness_analysis'] = self._analyze_completeness(records)
        
        return metrics
    
    def _calculate_field_metrics(
        self, 
        records: List[HMORecord], 
        validation_results: List[ValidationResult]
    ) -> Dict[str, FieldQualityMetrics]:
        """Calculate quality metrics for each field."""
        field_metrics = {}
        all_fields = HMORecord.get_field_names()
        
        for field in all_fields:
            confidences = []
            populated_count = 0
            error_count = 0
            warning_count = 0
            
            for record, result in zip(records, validation_results):
                # Get field value and confidence
                value = getattr(record, field, "")
                confidence = record.confidence_scores.get(field, 0.0)
                confidences.append(confidence)
                
                if value and str(value).strip():
                    populated_count += 1
                
                # Count field-specific errors and warnings
                field_errors = [e for e in result.validation_errors if field.replace('_', ' ') in e.lower()]
                field_warnings = [w for w in result.warnings if field.replace('_', ' ') in w.lower()]
                error_count += len(field_errors)
                warning_count += len(field_warnings)
            
            # Calculate metrics
            avg_confidence = statistics.mean(confidences) if confidences else 0.0
            min_confidence = min(confidences) if confidences else 0.0
            max_confidence = max(confidences) if confidences else 0.0
            
            # Determine quality level for this field
            population_rate = populated_count / len(records) if len(records) > 0 else 0.0
            quality_level = self._determine_field_quality_level(
                field, avg_confidence, population_rate, error_count
            )
            
            field_metrics[field] = FieldQualityMetrics(
                field_name=field,
                total_records=len(records),
                populated_records=populated_count,
                average_confidence=avg_confidence,
                min_confidence=min_confidence,
                max_confidence=max_confidence,
                validation_errors=error_count,
                warnings=warning_count,
                quality_level=quality_level
            )
        
        return field_metrics
    
    def _count_flagged_records(
        self, 
        records: List[HMORecord], 
        validation_results: List[ValidationResult]
    ) -> int:
        """Count records that should be flagged for review."""
        flagged = self.flag_low_confidence_records(records, validation_results)
        return len(flagged)
    
    def _calculate_overall_confidence(self, validation_results: List[ValidationResult]) -> float:
        """Calculate overall confidence across all records."""
        if not validation_results:
            return 0.0
        
        confidences = [result.confidence_score for result in validation_results]
        return statistics.mean(confidences)
    
    def _determine_quality_level(
        self, 
        overall_confidence: float, 
        valid_records: int, 
        total_records: int
    ) -> QualityLevel:
        """Determine overall quality level based on metrics."""
        validation_rate = valid_records / total_records if total_records > 0 else 0.0
        
        if overall_confidence >= 0.9 and validation_rate >= 0.95:
            return QualityLevel.EXCELLENT
        elif overall_confidence >= 0.8 and validation_rate >= 0.85:
            return QualityLevel.GOOD
        elif overall_confidence >= 0.7 and validation_rate >= 0.70:
            return QualityLevel.ACCEPTABLE
        elif overall_confidence >= 0.5 and validation_rate >= 0.50:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL
    
    def _determine_field_quality_level(
        self, 
        field: str, 
        avg_confidence: float, 
        population_rate: float, 
        error_count: int
    ) -> QualityLevel:
        """Determine quality level for individual field."""
        # Adjust thresholds based on field importance
        if field in self.critical_fields:
            conf_excellent, conf_good, conf_acceptable = 0.9, 0.8, 0.7
            pop_excellent, pop_good, pop_acceptable = 0.95, 0.85, 0.70
        elif field in self.important_fields:
            conf_excellent, conf_good, conf_acceptable = 0.85, 0.75, 0.65
            pop_excellent, pop_good, pop_acceptable = 0.90, 0.80, 0.65
        else:
            conf_excellent, conf_good, conf_acceptable = 0.80, 0.70, 0.60
            pop_excellent, pop_good, pop_acceptable = 0.85, 0.70, 0.50
        
        if error_count > 0:
            # Presence of errors lowers quality
            if avg_confidence >= conf_good and population_rate >= pop_good:
                return QualityLevel.ACCEPTABLE
            elif avg_confidence >= conf_acceptable and population_rate >= pop_acceptable:
                return QualityLevel.POOR
            else:
                return QualityLevel.CRITICAL
        
        if avg_confidence >= conf_excellent and population_rate >= pop_excellent:
            return QualityLevel.EXCELLENT
        elif avg_confidence >= conf_good and population_rate >= pop_good:
            return QualityLevel.GOOD
        elif avg_confidence >= conf_acceptable and population_rate >= pop_acceptable:
            return QualityLevel.ACCEPTABLE
        elif avg_confidence >= 0.5 and population_rate >= 0.3:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL
    
    def _aggregate_errors(self, validation_results: List[ValidationResult]) -> Dict[str, int]:
        """Aggregate validation errors across all results."""
        error_counts = {}
        
        for result in validation_results:
            for error in result.validation_errors:
                error_counts[error] = error_counts.get(error, 0) + 1
        
        return dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _aggregate_warnings(self, validation_results: List[ValidationResult]) -> Dict[str, int]:
        """Aggregate warnings across all results."""
        warning_counts = {}
        
        for result in validation_results:
            for warning in result.warnings:
                warning_counts[warning] = warning_counts.get(warning, 0) + 1
        
        return dict(sorted(warning_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _generate_recommendations(
        self, 
        field_metrics: Dict[str, FieldQualityMetrics],
        error_summary: Dict[str, int],
        warning_summary: Dict[str, int]
    ) -> List[str]:
        """Generate actionable recommendations based on quality assessment."""
        recommendations = []
        
        # Check critical fields
        for field in self.critical_fields:
            if field in field_metrics:
                metrics = field_metrics[field]
                if metrics.quality_level in [QualityLevel.POOR, QualityLevel.CRITICAL]:
                    recommendations.append(
                        f"Critical field '{field}' has {metrics.quality_level.value} quality. "
                        f"Consider improving extraction methods or manual review."
                    )
                elif metrics.population_rate < 0.8:
                    recommendations.append(
                        f"Critical field '{field}' is only populated in {metrics.population_rate:.1%} of records. "
                        f"Review document parsing for this field."
                    )
        
        # Check for common errors
        if error_summary:
            top_error = list(error_summary.keys())[0]
            error_count = error_summary[top_error]
            recommendations.append(
                f"Most common error: '{top_error}' ({error_count} occurrences). "
                f"Focus on resolving this issue first."
            )
        
        # Check overall data completeness
        critical_completeness = []
        for field in self.critical_fields:
            if field in field_metrics:
                critical_completeness.append(field_metrics[field].population_rate)
        
        if critical_completeness and statistics.mean(critical_completeness) < 0.7:
            recommendations.append(
                "Low completeness in critical fields. Consider improving document preprocessing "
                "or using alternative extraction methods."
            )
        
        # Check confidence distribution
        low_confidence_fields = [
            field for field, metrics in field_metrics.items()
            if metrics.average_confidence < 0.6
        ]
        
        if len(low_confidence_fields) > 5:
            recommendations.append(
                f"{len(low_confidence_fields)} fields have low confidence scores. "
                f"Consider retraining extraction models or improving validation rules."
            )
        
        return recommendations
    
    def _analyze_completeness(self, records: List[HMORecord]) -> Dict[str, Any]:
        """Analyze data completeness patterns."""
        if not records:
            return {}
        
        all_fields = HMORecord.get_field_names()
        completeness = {}
        
        # Calculate completeness by field category
        critical_completeness = []
        important_completeness = []
        optional_completeness = []
        
        for field in all_fields:
            populated = sum(1 for record in records 
                          if getattr(record, field, "") and str(getattr(record, field, "")).strip())
            rate = populated / len(records)
            
            if field in self.critical_fields:
                critical_completeness.append(rate)
            elif field in self.important_fields:
                important_completeness.append(rate)
            else:
                optional_completeness.append(rate)
        
        completeness['critical_fields_avg'] = statistics.mean(critical_completeness) if critical_completeness else 0.0
        completeness['important_fields_avg'] = statistics.mean(important_completeness) if important_completeness else 0.0
        completeness['optional_fields_avg'] = statistics.mean(optional_completeness) if optional_completeness else 0.0
        
        # Find records with high/low completeness
        record_completeness = []
        for record in records:
            populated_fields = sum(1 for field in all_fields 
                                 if getattr(record, field, "") and str(getattr(record, field, "")).strip())
            record_completeness.append(populated_fields / len(all_fields))
        
        completeness['record_completeness'] = {
            'mean': statistics.mean(record_completeness),
            'min': min(record_completeness),
            'max': max(record_completeness),
            'std': statistics.stdev(record_completeness) if len(record_completeness) > 1 else 0.0
        }
        
        return completeness
    
    def _calculate_quartiles(self, values: List[float]) -> Dict[str, float]:
        """Calculate quartiles for a list of values."""
        if not values:
            return {}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            'q1': sorted_values[n // 4] if n >= 4 else sorted_values[0],
            'q2': statistics.median(sorted_values),
            'q3': sorted_values[3 * n // 4] if n >= 4 else sorted_values[-1]
        }
    
    def export_quality_report(self, report: ExtractionQualityReport, format: str = 'dict') -> Any:
        """
        Export quality report in specified format.
        
        Args:
            report: Quality report to export
            format: Export format ('dict', 'json', 'summary')
            
        Returns:
            Exported report in specified format
        """
        if format == 'dict':
            return {
                'session_id': report.session_id,
                'timestamp': report.timestamp.isoformat(),
                'summary': {
                    'total_records': report.total_records,
                    'valid_records': report.valid_records,
                    'flagged_records': report.flagged_records,
                    'validation_rate': report.valid_records / report.total_records if report.total_records > 0 else 0,
                    'overall_confidence': report.overall_confidence,
                    'quality_level': report.quality_level.value
                },
                'field_metrics': {
                    field: {
                        'population_rate': metrics.population_rate,
                        'average_confidence': metrics.average_confidence,
                        'quality_level': metrics.quality_level.value,
                        'validation_errors': metrics.validation_errors,
                        'warnings': metrics.warnings
                    }
                    for field, metrics in report.field_metrics.items()
                },
                'top_errors': list(report.error_summary.items())[:5],
                'top_warnings': list(report.warning_summary.items())[:5],
                'recommendations': report.recommendations
            }
        
        elif format == 'summary':
            return {
                'quality_level': report.quality_level.value,
                'overall_confidence': f"{report.overall_confidence:.2%}",
                'validation_rate': f"{report.valid_records / report.total_records:.2%}" if report.total_records > 0 else "0%",
                'flagged_for_review': report.flagged_records,
                'key_recommendations': report.recommendations[:3]
            }
        
        else:
            raise ValueError(f"Unsupported export format: {format}")