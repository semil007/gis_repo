"""
Base document processor class providing abstract interface and common functionality
for document processing engines.
"""

import logging
import mimetypes
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

from loguru import logger


class DocumentType(Enum):
    """Supported document types for processing."""
    PDF = "pdf"
    DOCX = "docx"
    UNKNOWN = "unknown"


class ProcessingStatus(Enum):
    """Processing status indicators."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class ProcessingResult:
    """Result container for document processing operations."""
    extracted_text: str
    extracted_data: Dict
    confidence_scores: Dict[str, float]
    flagged_fields: List[str]
    processing_metadata: Dict
    status: ProcessingStatus
    error_messages: List[str]
    page_count: Optional[int] = None
    tables_found: Optional[int] = None
    ocr_used: bool = False


class DocumentProcessingError(Exception):
    """Base exception for document processing errors."""
    pass


class UnsupportedDocumentError(DocumentProcessingError):
    """Raised when document type is not supported."""
    pass


class FileAccessError(DocumentProcessingError):
    """Raised when file cannot be accessed or read."""
    pass


class ProcessingTimeoutError(DocumentProcessingError):
    """Raised when processing exceeds timeout limits."""
    pass


class DocumentProcessor(ABC):
    """
    Abstract base class for document processors.
    
    Provides common functionality for file type detection, error handling,
    and logging framework for all document processing implementations.
    """
    
    # Supported MIME types for each document type
    SUPPORTED_MIME_TYPES = {
        DocumentType.PDF: [
            "application/pdf",
            "application/x-pdf"
        ],
        DocumentType.DOCX: [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-word.document.macroEnabled.12"
        ]
    }
    
    # File extensions mapping
    SUPPORTED_EXTENSIONS = {
        ".pdf": DocumentType.PDF,
        ".docx": DocumentType.DOCX
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the document processor.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for the processor."""
        log_level = self.config.get("log_level", "INFO")
        logger.remove()  # Remove default handler
        logger.add(
            sink=lambda msg: print(msg, end=""),
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>"
        )
        
    def detect_document_type(self, file_path: Union[str, Path]) -> DocumentType:
        """
        Detect document type based on file extension and MIME type.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            DocumentType enum value
            
        Raises:
            FileAccessError: If file cannot be accessed
            UnsupportedDocumentError: If document type is not supported
        """
        file_path = Path(file_path)
        
        # Check if file exists and is accessible
        if not file_path.exists():
            raise FileAccessError(f"File not found: {file_path}")
            
        if not file_path.is_file():
            raise FileAccessError(f"Path is not a file: {file_path}")
            
        # Check file extension first
        extension = file_path.suffix.lower()
        if extension in self.SUPPORTED_EXTENSIONS:
            doc_type = self.SUPPORTED_EXTENSIONS[extension]
            logger.info(f"Detected document type {doc_type.value} from extension: {extension}")
            return doc_type
            
        # Fallback to MIME type detection
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            for doc_type, mime_types in self.SUPPORTED_MIME_TYPES.items():
                if mime_type in mime_types:
                    logger.info(f"Detected document type {doc_type.value} from MIME type: {mime_type}")
                    return doc_type
                    
        logger.warning(f"Unknown document type for file: {file_path}")
        return DocumentType.UNKNOWN
        
    def validate_file(self, file_path: Union[str, Path]) -> bool:
        """
        Validate file for processing.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            True if file is valid for processing
            
        Raises:
            FileAccessError: If file validation fails
        """
        file_path = Path(file_path)
        
        # Check file size limits (default 100MB)
        max_size = self.config.get("max_file_size", 100 * 1024 * 1024)
        file_size = file_path.stat().st_size
        
        if file_size > max_size:
            raise FileAccessError(
                f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)"
            )
            
        # Check if document type is supported
        doc_type = self.detect_document_type(file_path)
        if doc_type == DocumentType.UNKNOWN:
            raise UnsupportedDocumentError(f"Unsupported document type: {file_path}")
            
        logger.info(f"File validation passed for: {file_path}")
        return True
        
    def route_processing(self, file_path: Union[str, Path]) -> ProcessingResult:
        """
        Route document to appropriate processor based on type.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            ProcessingResult with extracted data
            
        Raises:
            UnsupportedDocumentError: If document type is not supported
        """
        try:
            # Validate file first
            self.validate_file(file_path)
            
            # Detect document type and route to appropriate processor
            doc_type = self.detect_document_type(file_path)
            
            logger.info(f"Starting processing for {doc_type.value} document: {file_path}")
            
            if doc_type == DocumentType.PDF:
                return self.process_pdf(file_path)
            elif doc_type == DocumentType.DOCX:
                return self.process_docx(file_path)
            else:
                raise UnsupportedDocumentError(f"No processor available for document type: {doc_type}")
                
        except Exception as e:
            logger.error(f"Processing failed for {file_path}: {str(e)}")
            return ProcessingResult(
                extracted_text="",
                extracted_data={},
                confidence_scores={},
                flagged_fields=[],
                processing_metadata={"error": str(e)},
                status=ProcessingStatus.FAILED,
                error_messages=[str(e)]
            )
            
    @abstractmethod
    def process_pdf(self, file_path: Union[str, Path]) -> ProcessingResult:
        """
        Process PDF document.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ProcessingResult with extracted data
        """
        pass
        
    @abstractmethod
    def process_docx(self, file_path: Union[str, Path]) -> ProcessingResult:
        """
        Process DOCX document.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            ProcessingResult with extracted data
        """
        pass
        
    def process_document(self, file_path: Union[str, Path]) -> ProcessingResult:
        """
        Main entry point for document processing.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            ProcessingResult with extracted data and metadata
        """
        try:
            logger.info(f"Processing document: {file_path}")
            result = self.route_processing(file_path)
            
            if result.status == ProcessingStatus.COMPLETED:
                logger.info(f"Successfully processed document: {file_path}")
            else:
                logger.warning(f"Processing completed with issues: {file_path}")
                
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error processing document {file_path}: {str(e)}")
            return ProcessingResult(
                extracted_text="",
                extracted_data={},
                confidence_scores={},
                flagged_fields=[],
                processing_metadata={"error": str(e), "file_path": str(file_path)},
                status=ProcessingStatus.FAILED,
                error_messages=[str(e)]
            )
            
    def get_supported_types(self) -> List[str]:
        """
        Get list of supported document types.
        
        Returns:
            List of supported file extensions
        """
        return list(self.SUPPORTED_EXTENSIONS.keys())
        
    def get_processing_stats(self, result: ProcessingResult) -> Dict:
        """
        Generate processing statistics from result.
        
        Args:
            result: ProcessingResult to analyze
            
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            "status": result.status.value,
            "text_length": len(result.extracted_text),
            "fields_extracted": len(result.extracted_data),
            "flagged_fields": len(result.flagged_fields),
            "error_count": len(result.error_messages),
            "ocr_used": result.ocr_used
        }
        
        if result.page_count is not None:
            stats["page_count"] = result.page_count
            
        if result.tables_found is not None:
            stats["tables_found"] = result.tables_found
            
        # Calculate average confidence score
        if result.confidence_scores:
            avg_confidence = sum(result.confidence_scores.values()) / len(result.confidence_scores)
            stats["average_confidence"] = round(avg_confidence, 3)
        else:
            stats["average_confidence"] = 0.0
            
        return stats