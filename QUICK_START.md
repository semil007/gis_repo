# HMO Document Processing Pipeline - Quick Start

## 🚀 Quick Start Guide

### 1. Setup and Installation

First, ensure all dependencies are installed and the system is set up:

```bash
# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run setup and initialization
python fix_setup.py
```

### 2. Start the Application

```bash
# Start the web application
python start_app.py
```

Or manually:

```bash
streamlit run app.py
```

### 3. Access the Application

Open your web browser and go to: **http://localhost:8501**

## 📋 How to Use

### Upload and Process Documents

1. **Upload Document**: Click "Browse files" and select a PDF or DOCX file containing HMO licensing data
2. **Configure Options**: 
   - Enable/disable OCR for scanned documents
   - Set confidence threshold for flagging records
3. **Start Processing**: Click "🚀 Start Processing"
4. **Monitor Progress**: Watch the progress bar and status updates
5. **Download Results**: Once complete, download the CSV file with extracted data

### Supported File Formats

- **PDF files** (.pdf) - Including scanned documents with OCR
- **Word documents** (.docx) - Text-based documents

### File Requirements

- Maximum size: 100MB
- Must contain HMO licensing data
- Readable text content (for best results)

## 🔧 Troubleshooting

### Common Issues and Solutions

#### "Processing Error - Unknown Error"

**Cause**: System components may be temporarily unavailable

**Solutions**:
1. **Try Again**: Click "🔄 Try Again" button
2. **Refresh Page**: Refresh your browser and re-upload the file
3. **Check File**: Ensure your file is a valid PDF or DOCX
4. **File Size**: Try a smaller file if yours is very large

#### "Redis Connection Failed" (in logs)

**Cause**: Redis service is not running (this is normal for basic setup)

**Solution**: The system automatically uses fallback processing - no action needed

#### "No Text Extracted"

**Cause**: Document may be image-based or corrupted

**Solutions**:
1. Enable OCR processing option
2. Ensure document contains readable text
3. Try a different file format

### System Status Check

You can check system status by clicking "🔍 Check System Status" in the error interface.

## 🧪 Testing

Test the system with a sample document:

```bash
python test_simple.py
```

This will:
- Create a test document
- Process it through the system
- Generate a CSV output
- Verify all components work

## 📁 Output Files

Processed results are saved in:
- **CSV files**: `sample_outputs/hmo_results_[session_id].csv`
- **Logs**: Console output and error logs
- **Temp files**: `temp/` directory (automatically cleaned)

## 🔄 Fallback Processing

The system includes a robust fallback processor that works even when main components fail:

- **Simple text extraction** for basic document processing
- **Pattern matching** for HMO data identification
- **CSV generation** with extracted records
- **Error recovery** with meaningful messages

## 📞 Support

If you encounter persistent issues:

1. **Check Logs**: Review console output for detailed error messages
2. **Session ID**: Note the session ID from error messages
3. **File Details**: Document the file type, size, and content structure
4. **System Status**: Run the system status check

## 🎯 Expected Results

The system extracts:
- Council/Authority name
- HMO reference number
- Property address
- License dates (start/expiry)
- Maximum occupancy
- Manager/holder names

Results include confidence scores and flagging for manual review when needed.

---

**Note**: This system uses AI/ML techniques for data extraction. Results may require manual review for accuracy, especially for non-standard document formats.