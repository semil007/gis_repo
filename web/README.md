# Web Interface Components

This directory contains the Streamlit-based web interface for the HMO Document Processing Pipeline.

## Components

### Core Application
- **`streamlit_app.py`** - Main Streamlit application class with session management
- **`app.py`** - Application entry point that integrates all components

### Upload and Validation
- **`file_uploader.py`** - File upload component with drag-and-drop functionality
- **`upload_validator.py`** - Comprehensive file validation with security checks
- **`progress_tracker.py`** - Progress tracking and status updates during processing

### Configuration and Results
- **`configuration_interface.py`** - Column mapping and validation rule configuration
- **`results_interface.py`** - Results display, data preview, and CSV download functionality

### Testing
- **`../tests/test_web_interface.py`** - Integration tests for all web components

## Features

### File Upload
- Drag-and-drop file upload interface
- Support for PDF and DOCX files up to 100MB
- Real-time file validation with detailed feedback
- Security checks including file signature validation
- Upload progress tracking with detailed status updates

### Configuration Management
- Customizable column mappings for CSV output
- Configurable validation rules and confidence thresholds
- Preset configurations for common use cases
- Import/export configuration functionality
- Real-time validation of configuration settings

### Results and Download
- Interactive data preview with filtering and sorting
- Quality metrics and confidence score analysis
- Flagged records identification for manual review
- Multiple download formats (CSV, complete package)
- Detailed quality reports and recommendations

### Progress Tracking
- Real-time processing progress with stage-by-stage updates
- Estimated completion times and elapsed time tracking
- Visual progress indicators and status messages
- Error handling with recovery options

## Usage

### Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Start the Streamlit application
streamlit run app.py
```

### Navigation

The application provides a multi-page interface:

1. **Upload & Process** - Upload documents and start processing
2. **Configuration** - Customize column mappings and validation rules
3. **Results** - View extracted data and download CSV files
4. **Manual Review** - Review and correct flagged records (implemented in task 7)

### Configuration Options

#### Column Mappings
- Customize output column names for all extracted fields
- Use preset configurations or create custom mappings
- Validate mappings to prevent duplicates and conflicts

#### Validation Rules
- Set confidence thresholds for quality assessment
- Configure required fields for record validation
- Enable/disable strict validation for dates and addresses

### File Requirements

#### Supported Formats
- PDF files (.pdf) - including scanned documents with OCR
- Microsoft Word documents (.docx)

#### File Constraints
- Maximum file size: 100MB
- Must contain readable text content
- Should include HMO licensing information

#### Expected Content
- Council/authority information
- License reference numbers
- Property addresses
- Manager and holder details
- Occupancy information
- License dates and terms

## Architecture

### Component Structure

```
web/
├── streamlit_app.py      # Main application logic
├── file_uploader.py      # Upload handling
├── upload_validator.py   # File validation
├── configuration_interface.py  # Settings management
├── results_interface.py  # Results display
├── progress_tracker.py   # Progress tracking
└── app.py               # Application entry point
```

### Session Management

The application uses Streamlit's session state to maintain:
- Upload status and file information
- Processing progress and results
- Configuration settings
- User preferences and navigation state

### Error Handling

Comprehensive error handling includes:
- File validation errors with specific guidance
- Processing errors with retry mechanisms
- Configuration validation with detailed feedback
- Network and system error recovery

## Testing

### Running Tests

```bash
# Run all web interface tests
python -m pytest tests/test_web_interface.py -v

# Run specific test classes
python -m pytest tests/test_web_interface.py::TestFileUploader -v
```

### Test Coverage

The test suite covers:
- File upload and validation workflows
- Configuration interface functionality
- Results processing and download generation
- Error handling and edge cases
- Integration between components

### Mock Data

Tests use mock data and fixtures to simulate:
- Various file types and sizes
- Processing results with different confidence levels
- Configuration scenarios
- Error conditions

## Dependencies

### Required Packages
- `streamlit>=1.28.0` - Web framework
- `pandas>=2.1.0` - Data manipulation
- `PyPDF2>=3.0.1` - PDF processing
- `python-docx>=1.1.0` - DOCX processing

### Optional Packages
- `python-magic` - Enhanced MIME type detection
- `pytest>=7.4.0` - Testing framework

## Performance Considerations

### File Processing
- Large files (>50MB) may take longer to process
- OCR processing adds significant time for scanned documents
- Progress tracking provides real-time feedback

### Memory Usage
- Files are processed in chunks to prevent memory issues
- Temporary files are cleaned up automatically
- Session data is managed efficiently

### Concurrent Users
- Each user session is isolated
- Processing queue prevents resource conflicts
- Graceful degradation under load

## Security Features

### File Validation
- File signature verification
- MIME type checking
- Size limit enforcement
- Content analysis for safety

### Data Handling
- Temporary file cleanup
- Session isolation
- No persistent storage of sensitive data
- Secure download links with expiration

## Customization

### Styling
- Streamlit theming support
- Custom CSS for enhanced UI
- Responsive design for different screen sizes

### Configuration
- Environment-based settings
- Configurable processing parameters
- Extensible validation rules

### Integration
- API endpoints for programmatic access
- Webhook support for notifications
- Export capabilities for external systems