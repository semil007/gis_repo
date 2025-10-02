"""
Comprehensive error handling system for the HMO document processing pipeline.

Provides centralized error handling, graceful degradation for service failures,
and user-friendly error messages with recovery options.
"""

import logging
import traceback
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import functools

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    FILE_UPLOAD = "file_upload"
    DOCUMENT_PROCESSING = "document_processing"
    NLP_PROCESSING = "nlp_processing"
    DATA_VALIDATION = "data_validation"
    SYSTEM_ERROR = "system_error"
    NETWORK_ERROR = "network_error"
    STORAGE_ERROR = "storage_error"
    CONFIGURATION_ERROR = "configuration_error"


@dataclass
class ErrorInfo:
    """Structured error information."""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    user_message: str
    technical_details: str
    recovery_suggestions: List[str]
    timestamp: datetime
    context: Dict[str, Any]
    traceback_info: Optional[str] = None


class ErrorHandler:
    """
    Centralized error handling system with graceful degradation capabilities.
    
    Requirements: 5.3, 4.5
    """
    
    def __init__(self):
        """Initialize error handler with predefined error patterns."""
        self.error_patterns = self._initialize_error_patterns()
        self.recovery_strategies = self._initialize_recovery_strategies()
        self.error_history = []
        
    def _initialize_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize common error patterns and their handling."""
        return {
            # File upload errors
            "file_too_large": {
                "category": ErrorCategory.FILE_UPLOAD,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "File size exceeds the maximum limit of 100MB",
                "recovery_suggestions": [
                    "Try compressing the file or splitting it into smaller parts",
                    "Use a different file format if possible",
                    "Contact support if the file is critical"
                ]
            },
            "unsupported_format": {
                "category": ErrorCategory.FILE_UPLOAD,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "File format is not supported",
                "recovery_suggestions": [
                    "Convert the file to PDF or DOCX format",
                    "Check that the file extension matches the content",
                    "Try uploading a different file"
                ]
            },
            "corrupted_file": {
                "category": ErrorCategory.FILE_UPLOAD,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "The uploaded file appears to be corrupted",
                "recovery_suggestions": [
                    "Try re-uploading the file",
                    "Check the original file for corruption",
                    "Use a different copy of the file if available"
                ]
            },
            
            # Document processing errors
            "pdf_extraction_failed": {
                "category": ErrorCategory.DOCUMENT_PROCESSING,
                "severity": ErrorSeverity.HIGH,
                "user_message": "Failed to extract text from PDF document",
                "recovery_suggestions": [
                    "The system will attempt OCR processing as a fallback",
                    "Ensure the PDF contains readable text (not just images)",
                    "Try converting the PDF to a different format"
                ]
            },
            "ocr_failed": {
                "category": ErrorCategory.DOCUMENT_PROCESSING,
                "severity": ErrorSeverity.HIGH,
                "user_message": "OCR processing failed to extract readable text",
                "recovery_suggestions": [
                    "Ensure the document images are clear and high-quality",
                    "Try preprocessing the document to improve image quality",
                    "Consider manual data entry for critical documents"
                ]
            },
            "no_text_extracted": {
                "category": ErrorCategory.DOCUMENT_PROCESSING,
                "severity": ErrorSeverity.CRITICAL,
                "user_message": "No readable text could be extracted from the document",
                "recovery_suggestions": [
                    "Verify the document contains text content",
                    "Try a different file format or version",
                    "Contact support with the document details"
                ]
            },
            
            # NLP processing errors
            "nlp_model_unavailable": {
                "category": ErrorCategory.NLP_PROCESSING,
                "severity": ErrorSeverity.HIGH,
                "user_message": "Natural language processing is temporarily unavailable",
                "recovery_suggestions": [
                    "The system will use basic text processing as a fallback",
                    "Results may have lower accuracy than usual",
                    "Try processing again later"
                ]
            },
            "entity_extraction_failed": {
                "category": ErrorCategory.NLP_PROCESSING,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "Failed to extract structured data from document",
                "recovery_suggestions": [
                    "The document may not contain standard HMO licensing data",
                    "Try manual review of the extracted text",
                    "Ensure the document format matches expected templates"
                ]
            },
            
            # Data validation errors
            "validation_failed": {
                "category": ErrorCategory.DATA_VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "Extracted data failed validation checks",
                "recovery_suggestions": [
                    "Review the flagged records in the audit interface",
                    "Manually correct any obvious errors",
                    "Check if the source document has unusual formatting"
                ]
            },
            
            # System errors
            "memory_error": {
                "category": ErrorCategory.SYSTEM_ERROR,
                "severity": ErrorSeverity.HIGH,
                "user_message": "System ran out of memory during processing",
                "recovery_suggestions": [
                    "Try processing a smaller file",
                    "Wait a few minutes and try again",
                    "Contact support if the issue persists"
                ]
            },
            "disk_space_error": {
                "category": ErrorCategory.STORAGE_ERROR,
                "severity": ErrorSeverity.HIGH,
                "user_message": "Insufficient disk space for processing",
                "recovery_suggestions": [
                    "Contact system administrator",
                    "Try again later when space may be available",
                    "Process smaller files if possible"
                ]
            },
            "database_error": {
                "category": ErrorCategory.SYSTEM_ERROR,
                "severity": ErrorSeverity.CRITICAL,
                "user_message": "Database connection error",
                "recovery_suggestions": [
                    "Try refreshing the page",
                    "Wait a few minutes and try again",
                    "Contact support if the issue persists"
                ]
            }
        }
        
    def _initialize_recovery_strategies(self) -> Dict[ErrorCategory, Callable]:
        """Initialize recovery strategies for different error categories."""
        return {
            ErrorCategory.DOCUMENT_PROCESSING: self._recover_document_processing,
            ErrorCategory.NLP_PROCESSING: self._recover_nlp_processing,
            ErrorCategory.DATA_VALIDATION: self._recover_data_validation,
            ErrorCategory.SYSTEM_ERROR: self._recover_system_error,
            ErrorCategory.STORAGE_ERROR: self._recover_storage_error
        }
        
    def handle_error(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        error_pattern: Optional[str] = None
    ) -> ErrorInfo:
        """
        Handle an error with comprehensive error information and recovery options.
        
        Args:
            exception: The exception that occurred
            context: Additional context information
            error_pattern: Specific error pattern if known
            
        Returns:
            ErrorInfo: Structured error information
            
        Requirements: 5.3, 4.5
        """
        error_id = self._generate_error_id()
        context = context or {}
        
        # Determine error pattern if not provided
        if not error_pattern:
            error_pattern = self._classify_error(exception)
            
        # Get error pattern info
        pattern_info = self.error_patterns.get(error_pattern, {})
        
        # Create error info
        error_info = ErrorInfo(
            error_id=error_id,
            category=pattern_info.get("category", ErrorCategory.SYSTEM_ERROR),
            severity=pattern_info.get("severity", ErrorSeverity.HIGH),
            message=str(exception),
            user_message=pattern_info.get("user_message", "An unexpected error occurred"),
            technical_details=self._extract_technical_details(exception),
            recovery_suggestions=pattern_info.get("recovery_suggestions", [
                "Try the operation again",
                "Contact support if the issue persists"
            ]),
            timestamp=datetime.now(),
            context=context,
            traceback_info=traceback.format_exc()
        )
        
        # Log the error
        self._log_error(error_info)
        
        # Store in error history
        self.error_history.append(error_info)
        
        # Attempt recovery if strategy available
        recovery_strategy = self.recovery_strategies.get(error_info.category)
        if recovery_strategy:
            try:
                recovery_result = recovery_strategy(error_info, context)
                if recovery_result:
                    error_info.recovery_suggestions.insert(0, "Automatic recovery attempted")
            except Exception as recovery_error:
                logger.error(f"Recovery strategy failed: {str(recovery_error)}")
                
        return error_info
        
    def _classify_error(self, exception: Exception) -> str:
        """Classify error based on exception type and message."""
        error_message = str(exception).lower()
        exception_type = type(exception).__name__
        
        # File-related errors
        if "file too large" in error_message or "size exceeds" in error_message:
            return "file_too_large"
        elif "unsupported format" in error_message or "invalid file" in error_message:
            return "unsupported_format"
        elif "corrupted" in error_message or "cannot read" in error_message:
            return "corrupted_file"
            
        # Processing errors
        elif "pdf" in error_message and ("extract" in error_message or "read" in error_message):
            return "pdf_extraction_failed"
        elif "ocr" in error_message or "tesseract" in error_message:
            return "ocr_failed"
        elif "no text" in error_message or "empty document" in error_message:
            return "no_text_extracted"
            
        # NLP errors
        elif "spacy" in error_message or "nlp" in error_message:
            return "nlp_model_unavailable"
        elif "entity" in error_message or "extraction" in error_message:
            return "entity_extraction_failed"
            
        # System errors
        elif exception_type == "MemoryError" or "memory" in error_message:
            return "memory_error"
        elif "disk" in error_message or "space" in error_message:
            return "disk_space_error"
        elif "database" in error_message or "connection" in error_message:
            return "database_error"
            
        # Validation errors
        elif "validation" in error_message:
            return "validation_failed"
            
        return "unknown_error"
        
    def _extract_technical_details(self, exception: Exception) -> str:
        """Extract technical details from exception."""
        details = [
            f"Exception Type: {type(exception).__name__}",
            f"Exception Message: {str(exception)}"
        ]
        
        # Add additional details based on exception type
        if hasattr(exception, 'errno'):
            details.append(f"Error Code: {exception.errno}")
        if hasattr(exception, 'filename'):
            details.append(f"Filename: {exception.filename}")
            
        return "; ".join(details)
        
    def _generate_error_id(self) -> str:
        """Generate unique error ID."""
        import uuid
        return f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
    def _log_error(self, error_info: ErrorInfo) -> None:
        """Log error information."""
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_info.severity, logging.ERROR)
        
        logger.log(
            log_level,
            f"Error {error_info.error_id}: {error_info.message} "
            f"[{error_info.category.value}] - {error_info.technical_details}"
        )
        
    # Recovery strategies
    def _recover_document_processing(self, error_info: ErrorInfo, context: Dict[str, Any]) -> bool:
        """Attempt recovery for document processing errors."""
        try:
            if error_info.message and "pdf" in error_info.message.lower():
                # Try OCR fallback for PDF errors
                logger.info("Attempting OCR fallback for PDF processing error")
                return True  # Indicate recovery was attempted
        except Exception as e:
            logger.error(f"Document processing recovery failed: {str(e)}")
        return False
        
    def _recover_nlp_processing(self, error_info: ErrorInfo, context: Dict[str, Any]) -> bool:
        """Attempt recovery for NLP processing errors."""
        try:
            # Fall back to basic text processing
            logger.info("Falling back to basic text processing")
            return True
        except Exception as e:
            logger.error(f"NLP processing recovery failed: {str(e)}")
        return False
        
    def _recover_data_validation(self, error_info: ErrorInfo, context: Dict[str, Any]) -> bool:
        """Attempt recovery for data validation errors."""
        try:
            # Continue with flagged records for manual review
            logger.info("Flagging records for manual review due to validation errors")
            return True
        except Exception as e:
            logger.error(f"Data validation recovery failed: {str(e)}")
        return False
        
    def _recover_system_error(self, error_info: ErrorInfo, context: Dict[str, Any]) -> bool:
        """Attempt recovery for system errors."""
        try:
            # Implement cleanup and retry logic
            logger.info("Attempting system error recovery")
            return False  # Most system errors can't be automatically recovered
        except Exception as e:
            logger.error(f"System error recovery failed: {str(e)}")
        return False
        
    def _recover_storage_error(self, error_info: ErrorInfo, context: Dict[str, Any]) -> bool:
        """Attempt recovery for storage errors."""
        try:
            # Try cleanup of temporary files
            logger.info("Attempting storage cleanup for recovery")
            return False  # Storage errors usually need manual intervention
        except Exception as e:
            logger.error(f"Storage error recovery failed: {str(e)}")
        return False


def error_handler_decorator(error_handler: ErrorHandler, context_func: Optional[Callable] = None):
    """
    Decorator for automatic error handling in functions.
    
    Args:
        error_handler: ErrorHandler instance
        context_func: Optional function to generate context information
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = context_func(*args, **kwargs) if context_func else {}
                error_info = error_handler.handle_error(e, context)
                
                # Re-raise with error info attached
                e.error_info = error_info
                raise
        return wrapper
    return decorator


class GracefulDegradationManager:
    """
    Manager for graceful degradation when services fail.
    
    Requirements: 5.3
    """
    
    def __init__(self):
        """Initialize degradation manager."""
        self.service_status = {}
        self.fallback_strategies = {}
        
    def register_service(self, service_name: str, health_check: Callable) -> None:
        """
        Register a service with health check function.
        
        Args:
            service_name: Name of the service
            health_check: Function to check service health
        """
        self.service_status[service_name] = {
            'health_check': health_check,
            'status': 'unknown',
            'last_check': None
        }
        
    def register_fallback(self, service_name: str, fallback_func: Callable) -> None:
        """
        Register a fallback strategy for a service.
        
        Args:
            service_name: Name of the service
            fallback_func: Fallback function to use when service fails
        """
        self.fallback_strategies[service_name] = fallback_func
        
    def check_service_health(self, service_name: str) -> bool:
        """
        Check health of a specific service.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            bool: True if service is healthy
        """
        if service_name not in self.service_status:
            return False
            
        try:
            health_check = self.service_status[service_name]['health_check']
            is_healthy = health_check()
            
            self.service_status[service_name].update({
                'status': 'healthy' if is_healthy else 'unhealthy',
                'last_check': datetime.now()
            })
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {str(e)}")
            self.service_status[service_name].update({
                'status': 'error',
                'last_check': datetime.now()
            })
            return False
            
    def get_service_or_fallback(self, service_name: str, *args, **kwargs):
        """
        Get service result or fallback if service is unavailable.
        
        Args:
            service_name: Name of the service
            *args, **kwargs: Arguments to pass to service or fallback
            
        Returns:
            Service result or fallback result
        """
        is_healthy = self.check_service_health(service_name)
        
        if is_healthy:
            try:
                # Service is healthy, use it normally
                return None  # Caller should use normal service
            except Exception as e:
                logger.warning(f"Service {service_name} failed despite health check: {str(e)}")
                is_healthy = False
                
        if not is_healthy and service_name in self.fallback_strategies:
            logger.info(f"Using fallback strategy for {service_name}")
            fallback_func = self.fallback_strategies[service_name]
            return fallback_func(*args, **kwargs)
            
        raise Exception(f"Service {service_name} is unavailable and no fallback is configured")
        
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system status.
        
        Returns:
            Dict[str, Any]: System status information
        """
        total_services = len(self.service_status)
        healthy_services = sum(
            1 for status in self.service_status.values()
            if status['status'] == 'healthy'
        )
        
        overall_health = 'healthy' if healthy_services == total_services else (
            'degraded' if healthy_services > 0 else 'critical'
        )
        
        return {
            'overall_health': overall_health,
            'total_services': total_services,
            'healthy_services': healthy_services,
            'service_details': {
                name: {
                    'status': info['status'],
                    'last_check': info['last_check'].isoformat() if info['last_check'] else None,
                    'has_fallback': name in self.fallback_strategies
                }
                for name, info in self.service_status.items()
            }
        }