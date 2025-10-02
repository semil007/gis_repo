"""
Unit tests for document processors including PDF, DOCX, and OCR components.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from PIL import Image

from processors.base import (
    DocumentProcessor, DocumentType, ProcessingStatus, ProcessingResult,
    DocumentProcessingError, UnsupportedDocumentError, FileAccessError
)
from processors.pdf_processor import PDFProcessor, PDFProcessingError
from processors.docx_processor import DOCXProcessor, DOCXProcessingError
from processors.ocr_processor import OCRProcessor, OCRProcessingError


class TestDocumentProcessor(unittest.TestCase):
    """Test cases for base DocumentProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {"log_level": "ERROR"}  # Suppress logs during testing
        
    def test_detect_document_type_pdf(self):
        """Test PDF document type detection."""
        # Create a concrete implementation for testing
        class TestProcessor(DocumentProcessor):
            def process_pdf(self, file_path): pass
            def process_docx(self, file_path): pass
            
        processor = TestProcessor(self.config)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
        try:
            doc_type = processor.detect_document_type(tmp_path)
            self.assertEqual(doc_type, DocumentType.PDF)
        finally:
            tmp_path.unlink()
            
    def test_detect_document_type_docx(self):
        """Test DOCX document type detection."""
        class TestProcessor(DocumentProcessor):
            def process_pdf(self, file_path): pass
            def process_docx(self, file_path): pass
            
        processor = TestProcessor(self.config)
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
        try:
            doc_type = processor.detect_document_type(tmp_path)
            self.assertEqual(doc_type, DocumentType.DOCX)
        finally:
            tmp_path.unlink()
            
    def test_detect_document_type_unknown(self):
        """Test unknown document type detection."""
        class TestProcessor(DocumentProcessor):
            def process_pdf(self, file_path): pass
            def process_docx(self, file_path): pass
            
        processor = TestProcessor(self.config)
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
        try:
            doc_type = processor.detect_document_type(tmp_path)
            self.assertEqual(doc_type, DocumentType.UNKNOWN)
        finally:
            tmp_path.unlink()
            
    def test_validate_file_nonexistent(self):
        """Test file validation with non-existent file."""
        class TestProcessor(DocumentProcessor):
            def process_pdf(self, file_path): pass
            def process_docx(self, file_path): pass
            
        processor = TestProcessor(self.config)
        
        with self.assertRaises(FileAccessError):
            processor.validate_file("nonexistent_file.pdf")
            
    def test_validate_file_too_large(self):
        """Test file validation with oversized file."""
        class TestProcessor(DocumentProcessor):
            def process_pdf(self, file_path): pass
            def process_docx(self, file_path): pass
            
        config = {"max_file_size": 100}  # 100 bytes limit
        processor = TestProcessor(config)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b'x' * 200)  # Write 200 bytes
            tmp_path = Path(tmp_file.name)
            
        try:
            with self.assertRaises(FileAccessError):
                processor.validate_file(tmp_path)
        finally:
            tmp_path.unlink()
            
    def test_get_supported_types(self):
        """Test getting supported document types."""
        class TestProcessor(DocumentProcessor):
            def process_pdf(self, file_path): pass
            def process_docx(self, file_path): pass
            
        processor = TestProcessor(self.config)
        supported_types = processor.get_supported_types()
        
        self.assertIn('.pdf', supported_types)
        self.assertIn('.docx', supported_types)
        
    def test_get_processing_stats(self):
        """Test processing statistics generation."""
        class TestProcessor(DocumentProcessor):
            def process_pdf(self, file_path): pass
            def process_docx(self, file_path): pass
            
        processor = TestProcessor(self.config)
        
        result = ProcessingResult(
            extracted_text="Sample text content",
            extracted_data={"field1": "value1", "field2": "value2"},
            confidence_scores={"field1": 0.8, "field2": 0.9},
            flagged_fields=["field1"],
            processing_metadata={},
            status=ProcessingStatus.COMPLETED,
            error_messages=[],
            page_count=2,
            tables_found=1,
            ocr_used=True
        )
        
        stats = processor.get_processing_stats(result)
        
        self.assertEqual(stats["status"], "completed")
        self.assertEqual(stats["text_length"], len("Sample text content"))
        self.assertEqual(stats["fields_extracted"], 2)
        self.assertEqual(stats["flagged_fields"], 1)
        self.assertEqual(stats["page_count"], 2)
        self.assertEqual(stats["tables_found"], 1)
        self.assertTrue(stats["ocr_used"])
        self.assertEqual(stats["average_confidence"], 0.85)


class TestPDFProcessor(unittest.TestCase):
    """Test cases for PDFProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {"log_level": "ERROR"}
        self.processor = PDFProcessor(self.config)
        
    def test_should_use_ocr_empty_text(self):
        """Test OCR decision with empty text."""
        self.assertTrue(self.processor._should_use_ocr(""))
        
    def test_should_use_ocr_short_text(self):
        """Test OCR decision with short text."""
        self.assertTrue(self.processor._should_use_ocr("abc"))
        
    def test_should_use_ocr_low_alphanumeric_ratio(self):
        """Test OCR decision with low alphanumeric ratio."""
        text = "!!!!!@@@@@#####$$$$$%%%%%"  # No alphanumeric characters
        self.assertTrue(self.processor._should_use_ocr(text))
        
    def test_should_use_ocr_good_text(self):
        """Test OCR decision with good quality text."""
        text = "This is a good quality text with proper alphanumeric content and sufficient length."
        self.assertFalse(self.processor._should_use_ocr(text))
        
    def test_extract_basic_data_references(self):
        """Test basic data extraction for references."""
        text = "Reference: ABC123 License: DEF456/2023"
        data = self.processor._extract_basic_data(text)
        
        self.assertIn("potential_references", data)
        references = data["potential_references"]
        self.assertIn("ABC123", references)
        self.assertIn("DEF456/2023", references)
        
    def test_extract_basic_data_addresses(self):
        """Test basic data extraction for addresses."""
        text = "Property located at 123 Main Street, London"
        data = self.processor._extract_basic_data(text)
        
        self.assertIn("potential_addresses", data)
        addresses = data["potential_addresses"]
        self.assertTrue(any("123 Main Street" in addr for addr in addresses))
        
    def test_extract_basic_data_dates(self):
        """Test basic data extraction for dates."""
        text = "Valid from 01/01/2023 to 31 Dec 2024"
        data = self.processor._extract_basic_data(text)
        
        self.assertIn("potential_dates", data)
        dates = data["potential_dates"]
        self.assertIn("01/01/2023", dates)
        
    def test_extract_basic_data_numbers(self):
        """Test basic data extraction for numbers."""
        text = "Maximum occupancy: 6 persons"
        data = self.processor._extract_basic_data(text)
        
        self.assertIn("potential_numbers", data)
        numbers = data["potential_numbers"]
        self.assertIn(6, numbers)
        
    def test_calculate_confidence_scores(self):
        """Test confidence score calculation."""
        extracted_data = {
            "potential_references": ["ABC123", "DEF456"],
            "potential_addresses": ["123 Main St"]
        }
        text = "Sample text content"
        
        scores = self.processor._calculate_confidence_scores(extracted_data, text, False)
        
        self.assertIn("potential_references", scores)
        self.assertIn("potential_addresses", scores)
        self.assertTrue(0 <= scores["potential_references"] <= 1)
        self.assertTrue(0 <= scores["potential_addresses"] <= 1)
        
    @patch('processors.pdf_processor.PyPDF2.PdfReader')
    def test_process_pdf_success(self, mock_pdf_reader):
        """Test successful PDF processing."""
        # Mock PDF reader
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample PDF content with reference ABC123"
        
        mock_reader_instance = Mock()
        mock_reader_instance.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_instance
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
        try:
            result = self.processor.process_pdf(tmp_path)
            
            self.assertEqual(result.status, ProcessingStatus.COMPLETED)
            self.assertIn("Sample PDF content", result.extracted_text)
            self.assertIn("potential_references", result.extracted_data)
            
        finally:
            tmp_path.unlink()
            
    def test_process_docx_not_supported(self):
        """Test that DOCX processing is not supported by PDFProcessor."""
        result = self.processor.process_docx("test.docx")
        
        self.assertEqual(result.status, ProcessingStatus.FAILED)
        self.assertIn("DOCX processing not supported", result.error_messages[0])


class TestDOCXProcessor(unittest.TestCase):
    """Test cases for DOCXProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {"log_level": "ERROR"}
        self.processor = DOCXProcessor(self.config)
        
    def test_looks_like_header_positive_cases(self):
        """Test header detection with positive cases."""
        # Test cases that should be detected as headers
        test_cases = [
            ["Name", "Address", "Date"],
            ["REFERENCE", "LICENCE", "EXPIRY"],
            ["Property:", "Manager:", "Contact:"],
            ["ID", "Type", "Status"]
        ]
        
        for row_data in test_cases:
            with self.subTest(row_data=row_data):
                self.assertTrue(self.processor._looks_like_header(row_data))
                
    def test_looks_like_header_negative_cases(self):
        """Test header detection with negative cases."""
        # Test cases that should NOT be detected as headers
        test_cases = [
            ["123 Main Street", "John Smith", "01/01/2023"],
            ["some random text", "more random text", "even more text"],
            ["", "", ""],
            []
        ]
        
        for row_data in test_cases:
            with self.subTest(row_data=row_data):
                self.assertFalse(self.processor._looks_like_header(row_data))
                
    @patch('processors.docx_processor.Document')
    def test_extract_metadata(self, mock_document_class):
        """Test metadata extraction from DOCX."""
        # Mock document and core properties
        mock_core_props = Mock()
        mock_core_props.title = "Test Document"
        mock_core_props.author = "Test Author"
        mock_core_props.subject = "Test Subject"
        mock_core_props.created = None
        mock_core_props.modified = None
        mock_core_props.last_modified_by = None
        
        mock_doc = Mock()
        mock_doc.core_properties = mock_core_props
        mock_doc.paragraphs = []
        mock_doc.tables = []
        
        metadata = self.processor._extract_metadata(mock_doc)
        
        self.assertEqual(metadata["title"], "Test Document")
        self.assertEqual(metadata["author"], "Test Author")
        self.assertEqual(metadata["subject"], "Test Subject")
        self.assertEqual(metadata["paragraph_count"], 0)
        self.assertEqual(metadata["table_count"], 0)
        
    @patch('processors.docx_processor.Document')
    def test_extract_text_content(self, mock_document_class):
        """Test text content extraction from DOCX."""
        # Mock paragraphs
        mock_para1 = Mock()
        mock_para1.text = "This is paragraph 1"
        mock_para1.style.name = "Normal"
        mock_para1.runs = []
        
        mock_para2 = Mock()
        mock_para2.text = "This is a heading"
        mock_para2.style.name = "Heading 1"
        mock_para2.runs = []
        
        mock_doc = Mock()
        mock_doc.paragraphs = [mock_para1, mock_para2]
        
        content = self.processor._extract_text_content(mock_doc)
        
        self.assertIn("This is paragraph 1", content["full_text"])
        self.assertIn("This is a heading", content["full_text"])
        self.assertEqual(len(content["paragraphs"]), 2)
        self.assertEqual(len(content["headings"]), 1)
        self.assertEqual(content["headings"][0]["text"], "This is a heading")
        
    def test_calculate_confidence_scores(self):
        """Test confidence score calculation for DOCX."""
        extracted_data = {
            "metadata": {"title": "Test"},
            "tables": [{"table_id": 0}],
            "potential_references": ["ABC123"]
        }
        text = "Sample DOCX content"
        
        scores = self.processor._calculate_confidence_scores(extracted_data, text)
        
        self.assertIn("metadata", scores)
        self.assertIn("tables", scores)
        self.assertIn("potential_references", scores)
        
        # DOCX should have high confidence for metadata and tables
        self.assertGreater(scores["metadata"], 0.9)
        self.assertGreater(scores["tables"], 0.9)
        
    def test_process_pdf_not_supported(self):
        """Test that PDF processing is not supported by DOCXProcessor."""
        result = self.processor.process_pdf("test.pdf")
        
        self.assertEqual(result.status, ProcessingStatus.FAILED)
        self.assertIn("PDF processing not supported", result.error_messages[0])


class TestOCRProcessor(unittest.TestCase):
    """Test cases for OCRProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {"log_level": "ERROR"}
        self.processor = OCRProcessor(self.config)
        
    def test_setup_tesseract_config(self):
        """Test Tesseract configuration setup."""
        self.processor.setup_tesseract_config()
        
        self.assertIn("--psm", self.processor.tesseract_config)
        self.assertIn("--oem", self.processor.tesseract_config)
        self.assertIn("tessedit_char_whitelist", self.processor.tesseract_config)
        
    def test_preprocess_image_disabled(self):
        """Test image preprocessing when disabled."""
        self.processor.preprocessing_enabled = False
        
        # Create a test image
        test_image = Image.new('RGB', (100, 100), color='white')
        
        result = self.processor.preprocess_image(test_image)
        
        # Should return the same image when preprocessing is disabled
        self.assertEqual(result.size, test_image.size)
        
    @patch('processors.ocr_processor.cv2')
    def test_preprocess_image_enabled(self, mock_cv2):
        """Test image preprocessing when enabled."""
        self.processor.preprocessing_enabled = True
        
        # Mock OpenCV operations
        mock_cv2.cvtColor.return_value = Mock()
        mock_cv2.fastNlMeansDenoising.return_value = Mock()
        mock_cv2.adaptiveThreshold.return_value = Mock()
        
        # Create a test image
        test_image = Image.new('RGB', (100, 100), color='white')
        
        # This should not raise an exception
        result = self.processor.preprocess_image(test_image)
        self.assertIsInstance(result, Image.Image)
        
    @patch('processors.ocr_processor.pytesseract.image_to_data')
    def test_extract_text_with_confidence(self, mock_image_to_data):
        """Test text extraction with confidence scoring."""
        # Mock OCR data
        mock_image_to_data.return_value = {
            'text': ['', 'Hello', 'World', ''],
            'conf': [0, 85, 90, 0],
            'left': [0, 10, 50, 0],
            'top': [0, 10, 10, 0],
            'width': [0, 30, 35, 0],
            'height': [0, 20, 20, 0]
        }
        
        test_image = Image.new('RGB', (100, 100), color='white')
        
        text, confidence_data = self.processor.extract_text_with_confidence(test_image)
        
        self.assertIn("Hello", text)
        self.assertIn("World", text)
        self.assertGreater(confidence_data['overall_confidence'], 0)
        self.assertEqual(confidence_data['word_count'], 2)
        
    def test_process_image_with_path(self):
        """Test processing image from file path."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            # Create a simple test image
            test_image = Image.new('RGB', (100, 50), color='white')
            test_image.save(tmp_file.name)
            tmp_path = Path(tmp_file.name)
            
        try:
            with patch('processors.ocr_processor.pytesseract.image_to_data') as mock_ocr:
                mock_ocr.return_value = {
                    'text': ['Test'],
                    'conf': [80],
                    'left': [0], 'top': [0], 'width': [50], 'height': [20]
                }
                
                result = self.processor.process_image(tmp_path)
                
                self.assertIn('text', result)
                self.assertIn('confidence_data', result)
                
        finally:
            tmp_path.unlink()
            
    @patch('processors.ocr_processor.pytesseract.image_to_osd')
    def test_detect_orientation(self, mock_image_to_osd):
        """Test document orientation detection."""
        mock_image_to_osd.return_value = {
            'rotate': 90,
            'orientation_conf': 8.5,
            'script': 'Latin',
            'script_conf': 9.2
        }
        
        test_image = Image.new('RGB', (100, 100), color='white')
        
        orientation_info = self.processor.detect_orientation(test_image)
        
        self.assertEqual(orientation_info['rotate'], 90)
        self.assertEqual(orientation_info['orientation_confidence'], 8.5)
        self.assertEqual(orientation_info['script'], 'Latin')
        
    @patch('processors.ocr_processor.pytesseract.get_languages')
    def test_get_supported_languages(self, mock_get_languages):
        """Test getting supported OCR languages."""
        mock_get_languages.return_value = ['eng', 'fra', 'deu']
        
        languages = self.processor.get_supported_languages()
        
        self.assertIn('eng', languages)
        self.assertIn('fra', languages)
        self.assertIn('deu', languages)
        
    @patch('processors.ocr_processor.pytesseract.image_to_string')
    def test_validate_tesseract_installation(self, mock_image_to_string):
        """Test Tesseract installation validation."""
        mock_image_to_string.return_value = "test"
        
        is_valid = self.processor.validate_tesseract_installation()
        
        self.assertTrue(is_valid)
        
    @patch('processors.ocr_processor.pytesseract.image_to_string')
    def test_validate_tesseract_installation_failure(self, mock_image_to_string):
        """Test Tesseract installation validation failure."""
        mock_image_to_string.side_effect = Exception("Tesseract not found")
        
        is_valid = self.processor.validate_tesseract_installation()
        
        self.assertFalse(is_valid)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)