"""
Integration tests for the Streamlit web interface components.
Tests complete upload-to-download workflow and error handling.
"""

import pytest
import streamlit as st
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json
from io import BytesIO, StringIO
import pandas as pd

# Import web interface components
try:
    from web.streamlit_app import StreamlitApp
    from web.file_uploader import FileUploader, UploadProgressTracker
    from web.upload_validator import UploadValidator, VisualFeedback
    from web.configuration_interface import ConfigurationInterface
    from web.results_interface import ResultsInterface, ResultsDownloader
    from web.progress_tracker import ProgressTracker, ProcessingStage
except ImportError as e:
    # Handle missing dependencies gracefully for testing
    print(f"Warning: Some imports failed: {e}")
    StreamlitApp = None


class TestStreamlitApp:
    """Test cases for the main Streamlit application."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = StreamlitApp()
        
    @patch('streamlit.session_state', {})
    def test_initialize_session_state(self):
        """Test session state initialization."""
        self.app.initialize_session_state()
        
        assert 'session_id' in st.session_state
        assert 'processing_status' in st.session_state
        assert 'uploaded_file' in st.session_state
        assert 'processing_results' in st.session_state
        assert 'column_mappings' in st.session_state
        
        assert st.session_state.processing_status == 'idle'
        assert st.session_state.uploaded_file is None
        assert st.session_state.processing_results is None
        
    def test_get_default_column_mappings(self):
        """Test default column mappings generation."""
        mappings = self.app.get_default_column_mappings()
        
        assert isinstance(mappings, dict)
        assert 'council' in mappings
        assert 'reference' in mappings
        assert 'hmo_address' in mappings
        assert len(mappings) >= 10  # Should have all required fields
        
    @patch('streamlit.session_state', {'session_id': 'test123', 'processing_status': 'idle'})
    @patch('streamlit.rerun')
    def test_reset_session(self, mock_rerun):
        """Test session reset functionality."""
        # Set some session state
        st.session_state.uploaded_file = Mock()
        st.session_state.processing_results = {'test': 'data'}
        
        self.app.reset_session()
        
        assert st.session_state.processing_status == 'idle'
        assert st.session_state.uploaded_file is None
        assert st.session_state.processing_results is None
        
    def test_validate_uploaded_file(self):
        """Test file validation logic."""
        # Create mock file objects
        valid_pdf = Mock()
        valid_pdf.name = "test.pdf"
        valid_pdf.size = 1024 * 1024  # 1MB
        
        large_file = Mock()
        large_file.name = "large.pdf"
        large_file.size = 200 * 1024 * 1024  # 200MB
        
        invalid_format = Mock()
        invalid_format.name = "test.txt"
        invalid_format.size = 1024
        
        # Test valid file
        assert self.app.validate_uploaded_file(valid_pdf) == True
        
        # Test large file
        with patch('streamlit.error') as mock_error:
            assert self.app.validate_uploaded_file(large_file) == False
            mock_error.assert_called()
            
        # Test invalid format
        with patch('streamlit.error') as mock_error:
            assert self.app.validate_uploaded_file(invalid_format) == False
            mock_error.assert_called()
            
    def test_mock_processing_results(self):
        """Test mock processing results generation."""
        results = self.app.mock_processing_results()
        
        assert isinstance(results, dict)
        assert 'records' in results
        assert 'avg_confidence' in results
        assert 'flagged_records' in results
        assert 'processing_time' in results
        
        assert isinstance(results['records'], list)
        assert len(results['records']) > 0
        assert isinstance(results['avg_confidence'], float)


class TestFileUploader:
    """Test cases for file upload functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.uploader = FileUploader()
        
    def test_initialization(self):
        """Test FileUploader initialization."""
        assert self.uploader.max_file_size_mb == 100
        assert self.uploader.max_file_size_bytes == 100 * 1024 * 1024
        assert '.pdf' in self.uploader.supported_formats
        assert '.docx' in self.uploader.supported_formats
        
    def test_validate_file_success(self):
        """Test successful file validation."""
        # Create mock uploaded file
        mock_file = Mock()
        mock_file.name = "test_document.pdf"
        mock_file.size = 5 * 1024 * 1024  # 5MB
        
        result = self.uploader.validate_file(mock_file)
        
        assert result['is_valid'] == True
        assert len(result['errors']) == 0
        assert 'file_info' in result
        assert result['file_info']['name'] == "test_document.pdf"
        
    def test_validate_file_too_large(self):
        """Test validation of oversized file."""
        mock_file = Mock()
        mock_file.name = "large_document.pdf"
        mock_file.size = 150 * 1024 * 1024  # 150MB
        
        result = self.uploader.validate_file(mock_file)
        
        assert result['is_valid'] == False
        assert len(result['errors']) > 0
        assert any("exceeds maximum" in error for error in result['errors'])
        
    def test_validate_file_invalid_format(self):
        """Test validation of invalid file format."""
        mock_file = Mock()
        mock_file.name = "document.txt"
        mock_file.size = 1024
        
        result = self.uploader.validate_file(mock_file)
        
        assert result['is_valid'] == False
        assert len(result['errors']) > 0
        assert any("Unsupported file format" in error for error in result['errors'])
        
    def test_validate_file_none(self):
        """Test validation with no file."""
        result = self.uploader.validate_file(None)
        
        assert result['is_valid'] == False
        assert "No file uploaded" in result['errors']
        
    def test_get_supported_extensions(self):
        """Test supported extensions list."""
        extensions = self.uploader.get_supported_extensions()
        
        assert 'pdf' in extensions
        assert 'docx' in extensions
        assert len(extensions) == 2
        
    @patch('tempfile.gettempdir')
    @patch('os.makedirs')
    def test_save_uploaded_file(self, mock_makedirs, mock_tempdir):
        """Test file saving functionality."""
        mock_tempdir.return_value = "/tmp"
        
        # Create mock file
        mock_file = Mock()
        mock_file.name = "test.pdf"
        mock_file.getbuffer.return_value = b"test content"
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = Mock()
            
            result = self.uploader.save_uploaded_file(mock_file, "session123")
            
            assert result is not None
            assert "session123" in result
            assert result.endswith(".pdf")


class TestUploadValidator:
    """Test cases for upload validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = UploadValidator()
        
    def test_initialization(self):
        """Test UploadValidator initialization."""
        assert self.validator.max_file_size_mb == 100
        assert len(self.validator.supported_extensions) == 2
        assert len(self.validator.supported_mime_types) > 0
        
    def test_extract_file_info(self):
        """Test file information extraction."""
        mock_file = Mock()
        mock_file.name = "test_document.pdf"
        mock_file.size = 1024
        mock_file.getvalue.return_value = b"test content"
        
        file_info = self.validator._extract_file_info(mock_file)
        
        assert file_info['name'] == "test_document.pdf"
        assert file_info['size'] == 1024
        assert file_info['extension'] == '.pdf'
        assert 'hash' in file_info
        assert 'upload_time' in file_info
        
    def test_validate_file_size(self):
        """Test file size validation."""
        # Test normal size
        result = self.validator._validate_file_size(10 * 1024 * 1024)  # 10MB
        assert len(result['errors']) == 0
        
        # Test large size (warning)
        result = self.validator._validate_file_size(90 * 1024 * 1024)  # 90MB
        assert len(result['warnings']) > 0
        
        # Test oversized
        result = self.validator._validate_file_size(150 * 1024 * 1024)  # 150MB
        assert len(result['errors']) > 0
        
        # Test very small
        result = self.validator._validate_file_size(500)  # 500 bytes
        assert len(result['warnings']) > 0
        
    def test_validate_file_signature_pdf(self):
        """Test PDF file signature validation."""
        mock_file = Mock()
        mock_file.getvalue.return_value = b'%PDF-1.4\n...'
        
        result = self.validator._validate_file_signature(mock_file, '.pdf')
        
        assert result['signature_valid'] == True
        assert result['detected_format'] == 'PDF'
        
    def test_validate_file_signature_docx(self):
        """Test DOCX file signature validation."""
        mock_file = Mock()
        mock_file.getvalue.return_value = b'PK\x03\x04...'
        
        result = self.validator._validate_file_signature(mock_file, '.docx')
        
        assert result['signature_valid'] == True
        assert 'ZIP-based' in result['detected_format']


class TestConfigurationInterface:
    """Test cases for configuration interface."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config_interface = ConfigurationInterface()
        
    def test_initialization(self):
        """Test ConfigurationInterface initialization."""
        assert len(self.config_interface.default_system_fields) > 10
        assert 'council' in self.config_interface.default_system_fields
        assert 'reference' in self.config_interface.default_system_fields
        assert len(self.config_interface.presets) >= 3
        
    def test_get_default_mappings(self):
        """Test default mappings generation."""
        mappings = self.config_interface._get_default_mappings()
        
        assert isinstance(mappings, dict)
        assert 'council' in mappings
        assert mappings['council'] == 'Council'
        assert len(mappings) == len(self.config_interface.default_system_fields)
        
    def test_get_field_description(self):
        """Test field description retrieval."""
        desc = self.config_interface._get_field_description('council')
        assert isinstance(desc, str)
        assert len(desc) > 0
        
        # Test unknown field
        desc = self.config_interface._get_field_description('unknown_field')
        assert desc == 'System field'
        
    def test_format_default_column_name(self):
        """Test column name formatting."""
        formatted = self.config_interface._format_default_column_name('hmo_address')
        assert formatted == 'Hmo Address'
        
        formatted = self.config_interface._format_default_column_name('number_of_storeys')
        assert formatted == 'Number Of Storeys'
        
    def test_validate_configuration(self):
        """Test configuration validation."""
        # Set up valid configuration
        with patch('streamlit.session_state', {
            'config_column_mappings': {'council': 'Council', 'reference': 'Reference'},
            'config_validation_rules': {
                'high_confidence_threshold': 0.8,
                'medium_confidence_threshold': 0.6,
                'flag_threshold': 0.4
            }
        }):
            result = self.config_interface.validate_configuration()
            assert result['is_valid'] == True
            
        # Test invalid thresholds
        with patch('streamlit.session_state', {
            'config_column_mappings': {'council': 'Council'},
            'config_validation_rules': {
                'high_confidence_threshold': 0.5,
                'medium_confidence_threshold': 0.7,
                'flag_threshold': 0.9
            }
        }):
            result = self.config_interface.validate_configuration()
            assert result['is_valid'] == False
            assert len(result['errors']) > 0


class TestResultsInterface:
    """Test cases for results interface."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.results_interface = ResultsInterface()
        self.sample_results = {
            'records': [
                {
                    'council': 'Test Council',
                    'reference': 'HMO/2024/001',
                    'hmo_address': '123 Test St',
                    'confidence_scores': {'council': 0.9, 'reference': 0.8}
                },
                {
                    'council': 'Test Council 2',
                    'reference': 'HMO/2024/002',
                    'hmo_address': '456 Test Ave',
                    'confidence_scores': {'council': 0.7, 'reference': 0.6}
                }
            ],
            'average_confidence': 0.75,
            'flagged_records': ['record_2'],
            'processing_time': 12.5
        }
        
    def test_generate_csv_data(self):
        """Test CSV data generation."""
        csv_data = self.results_interface._generate_csv_data(
            self.sample_results['records'], 
            include_confidence=False, 
            flagged_only=False
        )
        
        assert isinstance(csv_data, str)
        assert len(csv_data) > 0
        assert 'council' in csv_data
        assert 'Test Council' in csv_data
        
        # Test with confidence scores
        csv_with_conf = self.results_interface._generate_csv_data(
            self.sample_results['records'],
            include_confidence=True,
            flagged_only=False
        )
        
        assert 'council_confidence' in csv_with_conf
        
    def test_generate_filename(self):
        """Test filename generation."""
        with patch('streamlit.session_state', {'session_id': 'test123'}):
            filename = self.results_interface._generate_filename('csv')
            
            assert filename.endswith('.csv')
            assert 'hmo_data' in filename
            assert 'test123'[:8] in filename
            
    def test_apply_preview_filters(self):
        """Test preview filtering functionality."""
        df = pd.DataFrame(self.sample_results['records'])
        
        # Test confidence filter
        filtered_df = self.results_interface._apply_preview_filters(
            df, min_confidence=0.8, max_records=10, selected_columns=['council', 'reference']
        )
        
        assert len(filtered_df.columns) >= 2
        assert 'council' in filtered_df.columns
        
    def test_generate_quality_report(self):
        """Test quality report generation."""
        report_json = self.results_interface._generate_quality_report(
            self.sample_results['records']
        )
        
        report = json.loads(report_json)
        
        assert 'summary' in report
        assert 'field_analysis' in report
        assert 'confidence_distribution' in report
        assert report['summary']['total_records'] == 2


class TestProgressTracker:
    """Test cases for progress tracking functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.progress_tracker = ProgressTracker()
        
    def test_initialization(self):
        """Test ProgressTracker initialization."""
        assert len(self.progress_tracker.stages) > 5
        assert self.progress_tracker.current_stage_index == 0
        
    def test_start_processing(self):
        """Test processing start."""
        self.progress_tracker.start_processing()
        
        assert self.progress_tracker.start_time is not None
        assert self.progress_tracker.stage_start_time is not None
        
    def test_update_stage(self):
        """Test stage update functionality."""
        # Mock Streamlit components
        with patch('streamlit.progress'), \
             patch('streamlit.markdown'), \
             patch('streamlit.columns'):
            
            self.progress_tracker.update_stage(
                ProcessingStage.TEXT_EXTRACTION, 
                progress_within_stage=0.5
            )
            
            # Should update current stage index
            expected_index = next(
                i for i, s in enumerate(self.progress_tracker.stages) 
                if s['id'] == ProcessingStage.TEXT_EXTRACTION
            )
            assert self.progress_tracker.current_stage_index == expected_index


class TestIntegrationWorkflow:
    """Integration tests for complete workflow."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.app = StreamlitApp()
        self.uploader = FileUploader()
        self.validator = UploadValidator()
        self.config_interface = ConfigurationInterface()
        self.results_interface = ResultsInterface()
        
    @patch('streamlit.session_state', {})
    def test_complete_upload_workflow(self):
        """Test complete upload to processing workflow."""
        # Initialize session
        self.app.initialize_session_state()
        
        # Create mock file
        mock_file = Mock()
        mock_file.name = "test_hmo_document.pdf"
        mock_file.size = 5 * 1024 * 1024  # 5MB
        mock_file.getvalue.return_value = b"mock pdf content"
        
        # Validate file
        validation_result = self.uploader.validate_file(mock_file)
        assert validation_result['is_valid'] == True
        
        # Validate with comprehensive validator
        comprehensive_result = self.validator.validate_comprehensive(mock_file)
        # Should pass basic validation even without actual PDF content
        assert isinstance(comprehensive_result, dict)
        assert 'is_valid' in comprehensive_result
        
    def test_configuration_to_results_workflow(self):
        """Test configuration to results workflow."""
        # Set up configuration
        with patch('streamlit.session_state', {
            'config_column_mappings': {'council': 'Local Authority'},
            'config_validation_rules': {'flag_threshold': 0.4}
        }):
            config = self.config_interface._get_current_configuration()
            assert 'column_mappings' in config
            
            # Generate mock results
            mock_results = {
                'records': [
                    {
                        'council': 'Test Council',
                        'reference': 'HMO/001',
                        'confidence_scores': {'council': 0.9}
                    }
                ],
                'average_confidence': 0.9,
                'flagged_records': [],
                'processing_time': 10.0
            }
            
            # Test results interface
            csv_data = self.results_interface._generate_csv_data(
                mock_results['records'], False, False
            )
            assert len(csv_data) > 0
            assert 'council' in csv_data
            
    def test_error_handling_workflow(self):
        """Test error handling throughout the workflow."""
        # Test file validation errors
        invalid_file = Mock()
        invalid_file.name = "test.txt"
        invalid_file.size = 1024
        
        validation_result = self.uploader.validate_file(invalid_file)
        assert validation_result['is_valid'] == False
        assert len(validation_result['errors']) > 0
        
        # Test configuration validation errors
        with patch('streamlit.session_state', {
            'config_column_mappings': {'council': 'Council', 'reference': 'Council'},  # Duplicate
            'config_validation_rules': {'high_confidence_threshold': 0.5, 'flag_threshold': 0.9}  # Invalid order
        }):
            config_validation = self.config_interface.validate_configuration()
            assert config_validation['is_valid'] == False
            
    def test_empty_results_handling(self):
        """Test handling of empty or invalid results."""
        # Test empty records
        empty_results = {
            'records': [],
            'average_confidence': 0,
            'flagged_records': [],
            'processing_time': 0
        }
        
        csv_data = self.results_interface._generate_csv_data(
            empty_results['records'], False, False
        )
        assert csv_data == ""
        
        # Test None results
        csv_data = self.results_interface._generate_csv_data(None, False, False)
        assert csv_data == ""


# Pytest fixtures for common test data
@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing."""
    mock_file = Mock()
    mock_file.name = "sample_hmo.pdf"
    mock_file.size = 2 * 1024 * 1024  # 2MB
    mock_file.getvalue.return_value = b"%PDF-1.4\nSample PDF content"
    return mock_file


@pytest.fixture
def sample_docx_file():
    """Create a sample DOCX file for testing."""
    mock_file = Mock()
    mock_file.name = "sample_hmo.docx"
    mock_file.size = 1 * 1024 * 1024  # 1MB
    mock_file.getvalue.return_value = b"PK\x03\x04Sample DOCX content"
    return mock_file


@pytest.fixture
def sample_processing_results():
    """Create sample processing results for testing."""
    return {
        'records': [
            {
                'council': 'Test Council',
                'reference': 'HMO/2024/001',
                'hmo_address': '123 Test Street, Test City, TC1 2AB',
                'licence_start': '2024-01-01',
                'licence_expiry': '2025-01-01',
                'max_occupancy': 5,
                'confidence_scores': {
                    'council': 0.95,
                    'reference': 0.88,
                    'hmo_address': 0.92,
                    'licence_start': 0.85,
                    'licence_expiry': 0.87
                }
            },
            {
                'council': 'Another Council',
                'reference': 'HMO/2024/002',
                'hmo_address': '456 Another Street, Test City, TC2 3CD',
                'licence_start': '2024-02-01',
                'licence_expiry': '2025-02-01',
                'max_occupancy': 3,
                'confidence_scores': {
                    'council': 0.78,
                    'reference': 0.65,
                    'hmo_address': 0.72,
                    'licence_start': 0.55,
                    'licence_expiry': 0.60
                }
            }
        ],
        'average_confidence': 0.75,
        'flagged_records': ['record_2'],
        'processing_time': 15.2,
        'quality_metrics': {
            'high_confidence_count': 1,
            'medium_confidence_count': 1,
            'low_confidence_count': 0
        }
    }


# Integration test using fixtures
def test_complete_workflow_with_fixtures(sample_pdf_file, sample_processing_results):
    """Test complete workflow using fixtures."""
    uploader = FileUploader()
    results_interface = ResultsInterface()
    
    # Test file validation
    validation_result = uploader.validate_file(sample_pdf_file)
    assert validation_result['is_valid'] == True
    
    # Test results processing
    csv_data = results_interface._generate_csv_data(
        sample_processing_results['records'], 
        include_confidence=True, 
        flagged_only=False
    )
    
    assert len(csv_data) > 0
    assert 'Test Council' in csv_data
    assert 'confidence' in csv_data


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])