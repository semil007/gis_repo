"""
Unified document processor that combines PDF, DOCX, and OCR processing capabilities.
"""

from pathlib import Path
from typing import Dict, Optional, Union

from loguru import logger

from .base import DocumentProcessor, DocumentType, ProcessingResult, ProcessingStatus
from .pdf_processor import PDFProcessor
from .docx_processor import DOCXProcessor
from .ocr_processor import OCRProcessor


from nlp.nlp_pipeline import NLPPipeline

class UnifiedDocumentProcessor(DocumentProcessor):
    """
    Unified document processor that automatically routes documents to appropriate
    specialized processors based on file type and content analysis.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize unified processor with configuration.
        
        Args:
            config: Configuration dictionary for all processors
        """
        super().__init__(config)
        
        # Initialize specialized processors
        self.pdf_processor = PDFProcessor(config)
        self.docx_processor = DOCXProcessor(config)
        self.ocr_processor = OCRProcessor(config)
        
        # Initialize NLP pipeline
        self.nlp_pipeline = NLPPipeline(
            model_name=self.config.get('SPACY_MODEL', 'en_core_web_sm'),
            require_gpu=self.config.get('NLP_REQUIRE_GPU', False)
        )
        
        logger.info("Unified document processor initialized")
        
    def process_pdf(self, file_path: Union[str, Path]) -> ProcessingResult:
        """
        Process PDF document using specialized PDF processor.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ProcessingResult with extracted data
        """
        return self.pdf_processor.process_pdf(file_path)
        
    def process_docx(self, file_path: Union[str, Path]) -> ProcessingResult:
        """
        Process DOCX document using specialized DOCX processor.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            ProcessingResult with extracted data
        """
        return self.docx_processor.process_docx(file_path)
        
    def process_document_with_fallback(self, file_path: Union[str, Path]) -> ProcessingResult:
        """
        Process document with intelligent fallback strategies.
        
        Args:
            file_path: Path to document file
            
        Returns:
            ProcessingResult with extracted data
        """
        file_path = Path(file_path)
        
        try:
            logger.info(f"Processing document with fallback: {file_path}")
            
            # First attempt: Use standard processing
            result = self.process_document(file_path)
            
            # Check if we need OCR fallback for PDFs
            if (result.status in [ProcessingStatus.FAILED, ProcessingStatus.PARTIAL] and
                self.detect_document_type(file_path) == DocumentType.PDF):
                
                logger.info("Attempting OCR fallback for PDF")
                ocr_result = self._try_ocr_fallback(file_path)
                
                if ocr_result and len(ocr_result.get('text', '')) > len(result.extracted_text):
                    # OCR produced better results
                    result.extracted_text = ocr_result['text']
                    result.ocr_used = True
                    result.processing_metadata.update({
                        'fallback_method': 'ocr',
                        'ocr_confidence': ocr_result.get('overall_confidence', 0)
                    })
                    
                    if result.status == ProcessingStatus.FAILED:
                        result.status = ProcessingStatus.PARTIAL
            
            # NLP processing
            if result.extracted_text:
                nlp_results = self.nlp_pipeline.process_text(result.extracted_text)
                result.extracted_data['entities'] = nlp_results['entities']

            return result
            
        except Exception as e:
            logger.error(f"Document processing with fallback failed: {str(e)}")
            return ProcessingResult(
                extracted_text="",
                extracted_data={},
                confidence_scores={},
                flagged_fields=[],
                processing_metadata={"error": str(e), "file_path": str(file_path)},
                status=ProcessingStatus.FAILED,
                error_messages=[str(e)],
                ocr_used=False
            )
            
    def _try_ocr_fallback(self, file_path: Union[str, Path]) -> Optional[Dict]:
        """
        Try OCR as fallback for failed document processing.
        
        Args:
            file_path: Path to document file
            
        Returns:
            OCR result dictionary or None if failed
        """
        try:
            if self.detect_document_type(file_path) == DocumentType.PDF:
                return self.ocr_processor.process_pdf_with_ocr(file_path)
            else:
                logger.warning(f"OCR fallback not supported for file type: {file_path}")
                return None
                
        except Exception as e:
            logger.error(f"OCR fallback failed: {str(e)}")
            return None
            
    def get_processor_capabilities(self) -> Dict:
        """
        Get capabilities of all available processors.
        
        Returns:
            Dictionary with processor capabilities
        """
        capabilities = {
            "supported_formats": self.get_supported_types(),
            "pdf_processor": {
                "text_extraction": True,
                "table_detection": True,
                "ocr_support": True,
                "multi_page": True
            },
            "docx_processor": {
                "text_extraction": True,
                "table_detection": True,
                "metadata_extraction": True,
                "formatting_preservation": True,
                "headers_footers": True
            },
            "ocr_processor": {
                "image_preprocessing": True,
                "confidence_scoring": True,
                "multi_language": True,
                "orientation_detection": True
            },
            "unified_features": {
                "automatic_routing": True,
                "fallback_processing": True,
                "error_recovery": True,
                "quality_assessment": True
            }
        }
        
        # Check OCR language support
        try:
            capabilities["ocr_processor"]["supported_languages"] = self.ocr_processor.get_supported_languages()
        except Exception:
            capabilities["ocr_processor"]["supported_languages"] = ["eng"]
            
        return capabilities
        
    def validate_processing_environment(self) -> Dict:
        """
        Validate that all processing components are working correctly.
        
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            "overall_status": "unknown",
            "pdf_processor": "unknown",
            "docx_processor": "unknown", 
            "ocr_processor": "unknown",
            "issues": []
        }
        
        try:
            # Test PDF processor
            try:
                # Basic validation - check if PyPDF2 is available
                import PyPDF2
                validation_results["pdf_processor"] = "available"
            except ImportError:
                validation_results["pdf_processor"] = "unavailable"
                validation_results["issues"].append("PyPDF2 not available for PDF processing")
                
            # Test DOCX processor
            try:
                # Basic validation - check if python-docx is available
                import docx
                validation_results["docx_processor"] = "available"
            except ImportError:
                validation_results["docx_processor"] = "unavailable"
                validation_results["issues"].append("python-docx not available for DOCX processing")
                
            # Test OCR processor
            ocr_valid = self.ocr_processor.validate_tesseract_installation()
            validation_results["ocr_processor"] = "available" if ocr_valid else "unavailable"
            if not ocr_valid:
                validation_results["issues"].append("Tesseract OCR not properly installed or configured")
                
            # Determine overall status
            available_processors = sum(1 for status in [
                validation_results["pdf_processor"],
                validation_results["docx_processor"],
                validation_results["ocr_processor"]
            ] if status == "available")
            
            if available_processors == 3:
                validation_results["overall_status"] = "fully_operational"
            elif available_processors >= 2:
                validation_results["overall_status"] = "partially_operational"
            else:
                validation_results["overall_status"] = "limited_functionality"
                
            logger.info(f"Processing environment validation: {validation_results['overall_status']}")
            
        except Exception as e:
            validation_results["overall_status"] = "error"
            validation_results["issues"].append(f"Validation error: {str(e)}")
            logger.error(f"Environment validation failed: {str(e)}")
            
        return validation_results