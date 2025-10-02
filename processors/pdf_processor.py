"""
PDF document processor implementation using PyPDF2, tabula-py, and Tesseract OCR.
"""

import io
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
import PyPDF2
from loguru import logger
from PIL import Image
import pytesseract

try:
    import tabula
except ImportError:
    tabula = None
    logger.warning("tabula-py not available, table detection will be limited")

try:
    import camelot
except ImportError:
    camelot = None
    logger.warning("camelot-py not available, advanced table detection will be limited")

from .base import DocumentProcessor, ProcessingResult, ProcessingStatus, DocumentProcessingError


class PDFProcessingError(DocumentProcessingError):
    """PDF-specific processing error."""
    pass


class PDFProcessor(DocumentProcessor):
    """
    PDF document processor using PyPDF2 for text extraction,
    tabula-py/camelot for table detection, and Tesseract for OCR.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize PDF processor with configuration.
        
        Args:
            config: Configuration dictionary with processing options
        """
        super().__init__(config)
        
        # PDF-specific configuration
        self.ocr_threshold = self.config.get("ocr_threshold", 0.1)  # Minimum text ratio to skip OCR
        self.table_detection_method = self.config.get("table_detection", "tabula")  # tabula or camelot
        self.ocr_language = self.config.get("ocr_language", "eng")
        self.max_pages = self.config.get("max_pages", 100)
        
        # Tesseract configuration
        self.tesseract_config = self.config.get("tesseract_config", "--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?@#$%^&*()_+-=[]{}|;:'\",.<>?/`~ ")
        
    def process_pdf(self, file_path: Union[str, Path]) -> ProcessingResult:
        """
        Process PDF document with text extraction, table detection, and OCR.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ProcessingResult with extracted data
        """
        file_path = Path(file_path)
        
        try:
            logger.info(f"Starting PDF processing: {file_path}")
            
            # Initialize result containers
            extracted_text = ""
            extracted_data = {}
            confidence_scores = {}
            flagged_fields = []
            error_messages = []
            processing_metadata = {
                "file_path": str(file_path),
                "processor": "PDFProcessor"
            }
            
            # Open and analyze PDF
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)
                
                if page_count > self.max_pages:
                    logger.warning(f"PDF has {page_count} pages, limiting to {self.max_pages}")
                    page_count = self.max_pages
                
                processing_metadata["page_count"] = page_count
                
                # Extract text from all pages
                text_pages = []
                for page_num in range(page_count):
                    try:
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        text_pages.append(page_text)
                        logger.debug(f"Extracted text from page {page_num + 1}: {len(page_text)} characters")
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num + 1}: {str(e)}")
                        error_messages.append(f"Page {page_num + 1} text extraction failed: {str(e)}")
                        text_pages.append("")
                
                extracted_text = "\n\n".join(text_pages)
                
            # Check if OCR is needed (low text content)
            ocr_used = False
            if self._should_use_ocr(extracted_text):
                logger.info("Low text content detected, attempting OCR")
                ocr_text = self._perform_ocr(file_path)
                if ocr_text and len(ocr_text) > len(extracted_text):
                    extracted_text = ocr_text
                    ocr_used = True
                    processing_metadata["ocr_method"] = "tesseract"
                
            # Detect and extract tables
            tables_data = self._extract_tables(file_path)
            if tables_data:
                processing_metadata["tables_found"] = len(tables_data)
                extracted_data["tables"] = tables_data
                
            # Basic data extraction from text
            basic_data = self._extract_basic_data(extracted_text)
            extracted_data.update(basic_data)
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(extracted_data, extracted_text, ocr_used)
            
            # Flag low confidence fields
            confidence_threshold = self.config.get("confidence_threshold", 0.7)
            flagged_fields = [
                field for field, score in confidence_scores.items() 
                if score < confidence_threshold
            ]
            
            # Determine processing status
            if error_messages:
                status = ProcessingStatus.PARTIAL if extracted_text else ProcessingStatus.FAILED
            else:
                status = ProcessingStatus.COMPLETED
                
            logger.info(f"PDF processing completed: {len(extracted_text)} chars, {len(extracted_data)} fields")
            
            return ProcessingResult(
                extracted_text=extracted_text,
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                flagged_fields=flagged_fields,
                processing_metadata=processing_metadata,
                status=status,
                error_messages=error_messages,
                page_count=page_count,
                tables_found=len(tables_data) if tables_data else 0,
                ocr_used=ocr_used
            )
            
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
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
            
    def _should_use_ocr(self, text: str) -> bool:
        """
        Determine if OCR should be used based on text content.
        
        Args:
            text: Extracted text content
            
        Returns:
            True if OCR should be performed
        """
        if not text or len(text.strip()) < 100:
            return True
            
        # Calculate ratio of alphanumeric characters
        alphanumeric_chars = sum(1 for c in text if c.isalnum())
        total_chars = len(text)
        
        if total_chars == 0:
            return True
            
        ratio = alphanumeric_chars / total_chars
        return ratio < self.ocr_threshold
        
    def _perform_ocr(self, file_path: Union[str, Path]) -> str:
        """
        Perform OCR on PDF using Tesseract.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            OCR extracted text
        """
        try:
            # Convert PDF to images and perform OCR
            # Note: This is a simplified implementation
            # In production, you might want to use pdf2image for better conversion
            
            logger.info(f"Performing OCR on PDF: {file_path}")
            
            # For now, we'll use a basic approach
            # In a full implementation, you'd convert PDF pages to images first
            ocr_text = ""
            
            # This is a placeholder - actual implementation would need pdf2image
            logger.warning("OCR implementation requires pdf2image library for full functionality")
            
            return ocr_text
            
        except Exception as e:
            logger.error(f"OCR processing failed: {str(e)}")
            return ""
            
    def _extract_tables(self, file_path: Union[str, Path]) -> List[Dict]:
        """
        Extract tables from PDF using tabula-py or camelot.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of table data dictionaries
        """
        tables_data = []
        
        try:
            if self.table_detection_method == "tabula" and tabula:
                tables_data.extend(self._extract_tables_tabula(file_path))
            elif self.table_detection_method == "camelot" and camelot:
                tables_data.extend(self._extract_tables_camelot(file_path))
            else:
                logger.warning("No table detection library available")
                
        except Exception as e:
            logger.error(f"Table extraction failed: {str(e)}")
            
        return tables_data
        
    def _extract_tables_tabula(self, file_path: Union[str, Path]) -> List[Dict]:
        """Extract tables using tabula-py."""
        tables_data = []
        
        try:
            # Extract tables from all pages
            tables = tabula.read_pdf(str(file_path), pages='all', multiple_tables=True)
            
            for i, table in enumerate(tables):
                if not table.empty:
                    table_dict = {
                        "table_id": i,
                        "data": table.to_dict('records'),
                        "columns": table.columns.tolist(),
                        "shape": table.shape,
                        "extraction_method": "tabula"
                    }
                    tables_data.append(table_dict)
                    logger.debug(f"Extracted table {i} with shape {table.shape}")
                    
        except Exception as e:
            logger.error(f"Tabula table extraction failed: {str(e)}")
            
        return tables_data
        
    def _extract_tables_camelot(self, file_path: Union[str, Path]) -> List[Dict]:
        """Extract tables using camelot-py."""
        tables_data = []
        
        try:
            # Extract tables using camelot
            tables = camelot.read_pdf(str(file_path), pages='all')
            
            for i, table in enumerate(tables):
                table_dict = {
                    "table_id": i,
                    "data": table.df.to_dict('records'),
                    "columns": table.df.columns.tolist(),
                    "shape": table.df.shape,
                    "accuracy": table.accuracy,
                    "extraction_method": "camelot"
                }
                tables_data.append(table_dict)
                logger.debug(f"Extracted table {i} with accuracy {table.accuracy}")
                
        except Exception as e:
            logger.error(f"Camelot table extraction failed: {str(e)}")
            
        return tables_data
        
    def _extract_basic_data(self, text: str) -> Dict:
        """
        Extract basic HMO data patterns from text.
        
        Args:
            text: Extracted text content
            
        Returns:
            Dictionary with extracted data fields
        """
        data = {}
        
        try:
            # Extract potential reference numbers
            ref_patterns = [
                r'(?:ref|reference|licence|license)[\s:]+([A-Z0-9\-/]+)',
                r'([A-Z]{2,}\d{4,})',  # Pattern like ABC1234
                r'(\d{4,}/[A-Z0-9]+)'  # Pattern like 2023/ABC123
            ]
            
            references = []
            for pattern in ref_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                references.extend(matches)
                
            if references:
                data["potential_references"] = list(set(references))
                
            # Extract potential addresses (basic pattern)
            address_pattern = r'(\d+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr|Close|Cl|Way|Place|Pl)[^,\n]*(?:,\s*[A-Za-z\s]+)*)'
            addresses = re.findall(address_pattern, text, re.IGNORECASE)
            if addresses:
                data["potential_addresses"] = addresses[:10]  # Limit to first 10
                
            # Extract potential dates
            date_patterns = [
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',
                r'(\d{4}-\d{2}-\d{2})'
            ]
            
            dates = []
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                dates.extend(matches)
                
            if dates:
                data["potential_dates"] = list(set(dates))
                
            # Extract potential numbers (occupancy, etc.)
            number_patterns = [
                r'(?:occupancy|capacity|persons?)[\s:]+(\d+)',
                r'(?:max|maximum)[\s:]+(\d+)',
                r'(\d+)\s+(?:persons?|people|occupants?)'
            ]
            
            numbers = []
            for pattern in number_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                numbers.extend(matches)
                
            if numbers:
                data["potential_numbers"] = [int(n) for n in numbers if n.isdigit()]
                
        except Exception as e:
            logger.error(f"Basic data extraction failed: {str(e)}")
            
        return data
        
    def _calculate_confidence_scores(self, extracted_data: Dict, text: str, ocr_used: bool) -> Dict[str, float]:
        """
        Calculate confidence scores for extracted data.
        
        Args:
            extracted_data: Extracted data dictionary
            text: Source text
            ocr_used: Whether OCR was used
            
        Returns:
            Dictionary with confidence scores for each field
        """
        confidence_scores = {}
        
        try:
            # Base confidence reduction for OCR
            base_confidence = 0.8 if not ocr_used else 0.6
            
            # Text quality indicators
            text_length = len(text)
            text_quality = min(1.0, text_length / 1000)  # Normalize by expected length
            
            for field, value in extracted_data.items():
                if field == "tables":
                    # Table confidence based on structure
                    if value and len(value) > 0:
                        avg_accuracy = sum(t.get("accuracy", 0.8) for t in value) / len(value)
                        confidence_scores[field] = min(0.95, avg_accuracy * base_confidence)
                    else:
                        confidence_scores[field] = 0.0
                        
                elif field.startswith("potential_"):
                    # Pattern-based extraction confidence
                    if isinstance(value, list) and value:
                        # More matches generally indicate higher confidence
                        match_confidence = min(0.9, len(value) * 0.2 + 0.3)
                        confidence_scores[field] = match_confidence * base_confidence * text_quality
                    else:
                        confidence_scores[field] = 0.0
                else:
                    # Default confidence for other fields
                    confidence_scores[field] = base_confidence * text_quality
                    
        except Exception as e:
            logger.error(f"Confidence calculation failed: {str(e)}")
            
        return confidence_scores
        
    def process_docx(self, file_path: Union[str, Path]) -> ProcessingResult:
        """
        DOCX processing not implemented in PDF processor.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            ProcessingResult indicating unsupported operation
        """
        return ProcessingResult(
            extracted_text="",
            extracted_data={},
            confidence_scores={},
            flagged_fields=[],
            processing_metadata={"error": "DOCX processing not supported by PDFProcessor"},
            status=ProcessingStatus.FAILED,
            error_messages=["DOCX processing not supported by PDFProcessor"],
            ocr_used=False
        )