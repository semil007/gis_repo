# HMO Document Processing Pipeline - User Manual

## Table of Contents
1. [Getting Started](#getting-started)
2. [Web Interface Overview](#web-interface-overview)
3. [Document Upload](#document-upload)
4. [Configuration](#configuration)
5. [Processing and Results](#processing-and-results)
6. [Audit and Review](#audit-and-review)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

## Getting Started

### Accessing the Application

1. **Open your web browser** (Chrome, Firefox, Safari, or Edge)
2. **Navigate to the application URL:**
   - Local installation: `http://localhost:8501`
   - Server installation: `http://your-server-ip:8501`
3. **Wait for the application to load** (may take a few seconds on first visit)

### System Requirements for Users

- **Browser**: Modern web browser with JavaScript enabled
- **Internet Connection**: Required for initial loading
- **File Size**: Maximum 100MB per document
- **File Formats**: PDF and DOCX files only

## Web Interface Overview

### Main Navigation

The application consists of several main sections:

1. **📄 Document Upload** - Upload and process files
2. **⚙️ Configuration** - Set up column mappings
3. **📊 Results** - View and download processed data
4. **🔍 Audit** - Review flagged records manually

### Interface Layout

```
┌─────────────────────────────────────────────────┐
│ HMO Document Processing Pipeline                │
├─────────────────────────────────────────────────┤
│ [Upload] [Config] [Results] [Audit]             │
├─────────────────────────────────────────────────┤
│                                                 │
│           Main Content Area                     │
│                                                 │
├─────────────────────────────────────────────────┤
│ Status Messages and Progress                    │
└─────────────────────────────────────────────────┘
```

## Document Upload

### Supported File Types

- **PDF Files** (.pdf)
  - Text-based PDFs (preferred)
  - Scanned PDFs (processed with OCR)
  - Multi-page documents
  - Password-protected files (not supported)

- **DOCX Files** (.docx)
  - Microsoft Word documents
  - Documents with tables
  - Documents with embedded images

### Upload Process

#### Method 1: Drag and Drop

1. **Navigate to the Upload section**
2. **Drag your file** from your computer's file explorer
3. **Drop it onto the upload area** (highlighted in blue when hovering)
4. **Wait for upload confirmation**

#### Method 2: File Browser

1. **Click "Browse files" button**
2. **Select your file** from the file dialog
3. **Click "Open"** to upload

### Upload Validation

The system automatically validates uploaded files:

✅ **Valid Files:**
- PDF files under 100MB
- DOCX files under 100MB
- Files containing readable text

❌ **Invalid Files:**
- Files over 100MB
- Unsupported formats (JPG, PNG, TXT, etc.)
- Corrupted or password-protected files
- Empty files

### Upload Status Indicators

- 🔄 **Uploading...** - File transfer in progress
- ✅ **Upload Complete** - File ready for processing
- ❌ **Upload Failed** - Check file format and size
- ⚠️ **File Too Large** - Reduce file size or split document

## Configuration

### Column Mapping Setup

Before processing, you can configure how data fields are mapped to CSV columns.

#### Default Column Mappings

The system includes these default columns:

| System Field | Description | Example |
|--------------|-------------|---------|
| council | Local authority name | "Birmingham City Council" |
| reference | License reference number | "HMO/2023/001234" |
| hmo_address | Property address | "123 Main St, Birmingham B1 1AA" |
| licence_start | License start date | "2023-01-15" |
| licence_expiry | License expiry date | "2026-01-14" |
| max_occupancy | Maximum number of occupants | "6" |
| hmo_manager_name | Property manager name | "John Smith" |
| hmo_manager_address | Manager address | "456 Oak Ave, Birmingham B2 2BB" |
| licence_holder_name | License holder name | "ABC Property Ltd" |
| licence_holder_address | Holder address | "789 Pine St, Birmingham B3 3CC" |
| number_of_households | Number of separate households | "3" |
| number_of_shared_kitchens | Shared kitchen count | "2" |
| number_of_shared_bathrooms | Shared bathroom count | "3" |
| number_of_shared_toilets | Shared toilet count | "4" |
| number_of_storeys | Number of floors | "3" |

#### Custom Column Names

1. **Navigate to Configuration section**
2. **Select "Custom Column Mapping"**
3. **Enter your preferred column names:**
   ```
   System Field → Your Column Name
   council → "Local Authority"
   reference → "Licence Number"
   hmo_address → "Property Address"
   ```
4. **Click "Save Configuration"**

#### Preset Configurations

Choose from common configurations:
- **Standard HMO Format** - Default mapping
- **Council Format A** - Common council document format
- **Council Format B** - Alternative council format
- **Minimal Fields** - Essential fields only

### Processing Options

#### Confidence Threshold

Set the minimum confidence level for automatic acceptance:
- **High (85%)** - Only very confident extractions
- **Medium (70%)** - Balanced approach (recommended)
- **Low (50%)** - Accept more uncertain extractions

#### OCR Settings

For scanned documents:
- **Language**: English (default)
- **Quality**: Standard/High (affects processing time)
- **Preprocessing**: Auto-enhance images

## Processing and Results

### Starting Processing

1. **Upload your document(s)**
2. **Configure column mappings** (optional)
3. **Click "Start Processing"**
4. **Monitor progress** in the status area

### Processing Status

#### Status Indicators

- 🔄 **Queued** - Waiting to start processing
- 📄 **Reading Document** - Extracting text content
- 🧠 **Analyzing Content** - NLP and entity extraction
- ✅ **Processing Complete** - Ready for download
- ❌ **Processing Failed** - Check error message

#### Progress Information

The system shows:
- **Current step** in the processing pipeline
- **Estimated time remaining**
- **Number of records found**
- **Quality score** (percentage of high-confidence extractions)

### Viewing Results

#### Results Summary

After processing, you'll see:
- **Total records extracted**
- **High confidence records** (automatically accepted)
- **Flagged records** (requiring manual review)
- **Overall quality score**

#### Preview Data

- **Table view** of extracted data
- **Confidence scores** for each field
- **Flagged records** highlighted in yellow/red
- **Missing data** shown as empty cells

### Downloading Results

#### Download Options

1. **Download All Data** - Complete CSV with all records
2. **Download Verified Only** - High-confidence records only
3. **Download After Review** - Available after audit completion

#### File Naming

Downloaded files are automatically named:
- Format: `processed_YYYYMMDD_HHMMSS.csv`
- Example: `processed_20231215_143022.csv`

## Audit and Review

### When Manual Review is Needed

Records are flagged for review when:
- **Low confidence scores** (below threshold)
- **Missing critical fields** (address, reference number)
- **Inconsistent data formats** (invalid dates, addresses)
- **Conflicting information** within the document

### Audit Interface

#### Accessing Audit Mode

1. **Click "Audit" tab** after processing
2. **View flagged records** in the review queue
3. **Select a record** to start editing

#### Record Review Process

For each flagged record:

1. **Review extracted data** in the form fields
2. **Check confidence scores** (shown as colored bars)
3. **Verify against source document** (displayed alongside)
4. **Edit incorrect fields** as needed
5. **Mark as "Reviewed"** when complete

#### Editing Fields

- **Text fields**: Click to edit directly
- **Dates**: Use date picker or enter YYYY-MM-DD format
- **Numbers**: Enter numeric values only
- **Addresses**: Verify format and completeness

#### Confidence Indicators

- 🟢 **Green (85%+)**: High confidence, likely correct
- 🟡 **Yellow (70-84%)**: Medium confidence, check carefully
- 🔴 **Red (<70%)**: Low confidence, verify against document

### Batch Review Actions

- **Accept All High Confidence** - Auto-approve records above threshold
- **Flag All Low Confidence** - Mark uncertain records for review
- **Export Current State** - Download partially reviewed data

### Review Status Tracking

- ✅ **Reviewed** - Manually verified and approved
- 🔄 **In Progress** - Currently being reviewed
- ⏳ **Pending** - Waiting for review
- ❌ **Rejected** - Marked as invalid/unusable

## Troubleshooting

### Common Upload Issues

#### "File format not supported"
- **Solution**: Ensure file is PDF or DOCX format
- **Check**: File extension is .pdf or .docx (not .doc, .txt, etc.)

#### "File too large"
- **Solution**: Reduce file size or split large documents
- **Tip**: Use PDF compression tools or save DOCX in compatibility mode

#### "Upload failed"
- **Check**: Internet connection is stable
- **Try**: Refresh page and upload again
- **Alternative**: Use different browser

### Processing Issues

#### "No data found"
- **Cause**: Document may be image-based or poorly formatted
- **Solution**: Try OCR processing or check document quality
- **Tip**: Ensure document contains actual HMO licensing data

#### "Processing timeout"
- **Cause**: Very large file or server overload
- **Solution**: Try smaller files or wait and retry
- **Contact**: Administrator if problem persists

#### "Low quality results"
- **Cause**: Poor document quality or unusual format
- **Solution**: Use manual review to correct extractions
- **Tip**: Provide higher quality source documents when possible

### Interface Issues

#### Page won't load
- **Check**: URL is correct (http://localhost:8501)
- **Try**: Refresh browser or clear cache
- **Verify**: Application is running (check with administrator)

#### Buttons not working
- **Solution**: Enable JavaScript in browser
- **Try**: Different browser (Chrome, Firefox recommended)
- **Check**: No browser extensions blocking functionality

#### Slow performance
- **Cause**: Large files or limited system resources
- **Solution**: Process smaller files or wait for completion
- **Tip**: Close other browser tabs to free memory

## Best Practices

### Document Preparation

#### For Best Results:
- **Use text-based PDFs** when possible (not scanned images)
- **Ensure good image quality** for scanned documents
- **Keep file sizes reasonable** (under 50MB preferred)
- **Use standard document formats** (avoid unusual layouts)

#### Document Quality Tips:
- **High resolution scans** (300 DPI minimum)
- **Good contrast** between text and background
- **Straight orientation** (not rotated or skewed)
- **Clear, readable fonts** in source documents

### Processing Workflow

#### Recommended Steps:
1. **Start with a test document** to verify configuration
2. **Review column mappings** before bulk processing
3. **Process documents in batches** rather than all at once
4. **Review flagged records promptly** while document is fresh
5. **Keep source documents** until review is complete

#### Efficiency Tips:
- **Use consistent document formats** when possible
- **Set appropriate confidence thresholds** for your use case
- **Train team members** on the audit interface
- **Establish review workflows** for quality assurance

### Data Quality

#### Ensuring Accuracy:
- **Always review flagged records** before final export
- **Spot-check high-confidence extractions** periodically
- **Maintain consistent data formats** across documents
- **Document any manual corrections** for future reference

#### Quality Metrics:
- **Aim for 90%+ overall confidence** in final dataset
- **Review 100% of flagged records** before export
- **Validate critical fields** (addresses, dates, references)
- **Check for completeness** in required fields

### Security and Privacy

#### Data Handling:
- **Upload only authorized documents**
- **Download results promptly** and securely store
- **Clear browser cache** after sensitive processing
- **Use secure networks** for document upload/download

#### File Management:
- **Delete temporary files** after processing
- **Secure storage** of source documents
- **Regular backups** of processed data
- **Access control** for sensitive information

---

## Support and Contact

For additional help:
- **Check application logs** for error details
- **Review troubleshooting section** in main README
- **Contact system administrator** for technical issues
- **Report bugs** through the issue tracking system

**Version**: 1.0.0  
**Last Updated**: December 2024