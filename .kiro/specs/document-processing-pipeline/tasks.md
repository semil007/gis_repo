# Implementation Plan

- [x] 1. Set up project structure and core dependencies





  - Create directory structure for models, services, processors, and web components
  - Set up requirements.txt with all necessary Python packages (streamlit, fastapi, spacy, tesseract, etc.)
  - Create Docker configuration for Ubuntu deployment
  - Set up Git repository structure with deployment scripts
  - _Requirements: 8.1, 9.1, 9.2_

- [x] 2. Implement core data models and validation





  - [x] 2.1 Create HMORecord dataclass with all required fields


    - Define HMORecord with configurable field mappings
    - Implement validation methods for each field type
    - Add confidence scoring attributes
    - _Requirements: 3.1, 3.2, 7.1_


  - [x] 2.2 Implement ProcessingSession model

    - Create session management for tracking upload and processing state
    - Add metadata tracking for quality metrics
    - Implement session persistence with SQLite
    - _Requirements: 5.1, 7.4_

  - [x] 2.3 Create ColumnMapping configuration system


    - Implement user-configurable column name mappings
    - Add validation for column mapping configurations
    - Create default mapping presets
    - _Requirements: 3.1, 3.2_

  - [x] 2.4 Write unit tests for data models


    - Test HMORecord validation with various input types
    - Test session management and persistence
    - Test column mapping validation
    - _Requirements: 3.1, 3.2, 7.1_

- [x] 3. Build document processing engine





  - [x] 3.1 Implement base DocumentProcessor class


    - Create abstract base class for document processing
    - Implement file type detection and routing
    - Add error handling and logging framework
    - _Requirements: 2.1, 5.3, 6.1_

  - [x] 3.2 Create PDF processing component


    - Implement PDFProcessor using PyPDF2 for text extraction
    - Add table detection using tabula-py or camelot
    - Integrate Tesseract OCR for scanned PDFs
    - Handle multi-page documents and page layout analysis
    - _Requirements: 2.1, 2.3, 6.1, 6.2_

  - [x] 3.3 Create DOCX processing component


    - Implement DOCXProcessor using python-docx
    - Extract text content while preserving structure
    - Handle embedded tables and formatting
    - Process document metadata and properties
    - _Requirements: 2.1, 2.3, 6.3_

  - [x] 3.4 Implement OCR processing pipeline


    - Set up Tesseract OCR with optimal configuration
    - Add image preprocessing for better OCR accuracy
    - Implement confidence scoring for OCR results
    - Handle multiple languages and document orientations
    - _Requirements: 6.1, 7.1_

  - [x] 3.5 Write unit tests for document processors


    - Test PDF text extraction with sample files
    - Test DOCX processing with various document formats
    - Test OCR accuracy with scanned documents
    - Test error handling for corrupted files
    - _Requirements: 2.1, 6.1_

- [x] 4. Develop NLP and entity extraction pipeline





  - [x] 4.1 Set up spaCy NLP pipeline


    - Configure spaCy with appropriate language model
    - Implement custom entity recognition for HMO-specific terms
    - Add pattern matching for addresses, dates, and references
    - _Requirements: 2.2, 6.4, 6.5_

  - [x] 4.2 Create specialized entity extractors


    - Implement AddressParser for UK address formats
    - Create DateNormalizer for various date formats
    - Build ReferenceExtractor for license numbers and codes
    - Add PersonNameExtractor for manager and holder names
    - _Requirements: 2.5, 6.4_

  - [x] 4.3 Implement confidence scoring system


    - Create ConfidenceCalculator using multiple factors
    - Implement field-specific confidence thresholds
    - Add ensemble scoring combining multiple extraction methods
    - _Requirements: 7.1, 7.2_

  - [x] 4.4 Write unit tests for NLP components


    - Test entity extraction with known text samples
    - Test address parsing with various UK formats
    - Test date normalization with edge cases
    - Test confidence scoring accuracy
    - _Requirements: 2.2, 6.4, 7.1_

- [x] 5. Build data validation and quality assurance system





  - [x] 5.1 Implement DataValidator class


    - Create field-specific validation rules
    - Add format checking for dates, addresses, and numbers
    - Implement cross-field validation logic
    - _Requirements: 7.3, 7.4_

  - [x] 5.2 Create quality assessment framework


    - Implement QualityAssessment for extraction metrics
    - Add automated flagging for low-confidence records
    - Generate quality reports with statistics
    - _Requirements: 7.2, 7.4_

  - [x] 5.3 Build audit management system


    - Create AuditManager for tracking flagged records
    - Implement review workflow and status tracking
    - Add audit trail for manual corrections
    - _Requirements: 10.1, 10.4_

  - [x] 5.4 Write unit tests for validation system


    - Test validation rules with edge cases
    - Test quality assessment calculations
    - Test audit workflow management
    - _Requirements: 7.1, 7.4_

- [x] 6. Create web interface with Streamlit





  - [x] 6.1 Build main application interface


    - Create StreamlitApp with clean, intuitive layout
    - Implement file upload with drag-and-drop functionality
    - Add progress indicators and status updates
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 6.2 Implement file upload and validation


    - Create FileUploader with size and format validation
    - Add visual feedback for drag-and-drop operations
    - Implement upload progress tracking
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 6.3 Create configuration interface


    - Build column mapping configuration UI
    - Add preset configurations for common formats
    - Implement validation for user configurations
    - _Requirements: 3.1, 3.2_

  - [x] 6.4 Build results and download interface


    - Create ResultsDownloader for CSV file generation
    - Add preview functionality for extracted data
    - Implement download links with proper file naming
    - _Requirements: 4.4, 3.4_

  - [x] 6.5 Write integration tests for web interface


    - Test complete upload-to-download workflow
    - Test error handling and user feedback
    - Test configuration interface functionality
    - _Requirements: 4.1, 4.4_

- [x] 7. Implement audit and manual review interface





  - [x] 7.1 Create audit page interface


    - Build separate Streamlit page for manual review
    - Display flagged records with confidence scores
    - Add filtering and sorting capabilities
    - _Requirements: 10.1, 10.2_

  - [x] 7.2 Build record editing functionality


    - Create RecordEditor for field-by-field editing
    - Add validation for manual corrections
    - Implement save and update functionality
    - _Requirements: 10.3, 10.4_

  - [x] 7.3 Implement audit tracking and export


    - Add AuditTracker for review status management
    - Create export functionality for corrected data
    - Generate audit reports and statistics
    - _Requirements: 10.4, 10.5_

  - [x] 7.4 Write tests for audit interface


    - Test record editing and validation
    - Test audit workflow and status tracking
    - Test export functionality with corrections
    - _Requirements: 10.1, 10.5_

- [x] 8. Set up processing queue and session management





  - [x] 8.1 Implement Redis queue system


    - Set up Redis for processing queue management
    - Create queue workers for concurrent processing
    - Add job status tracking and progress updates
    - _Requirements: 5.1, 5.2_

  - [x] 8.2 Create SQLite session storage


    - Implement database schema for sessions and records
    - Add session persistence and retrieval
    - Create cleanup routines for old sessions
    - _Requirements: 5.1, 9.1_

  - [x] 8.3 Build file storage management


    - Implement secure file storage with cleanup
    - Add temporary file management
    - Create storage quota and cleanup policies
    - _Requirements: 5.4, 9.1_



  - [x] 8.4 Write tests for queue and storage systems





    - Test queue processing and job management
    - Test session persistence and retrieval
    - Test file storage and cleanup
    - _Requirements: 5.1, 5.2_

- [x] 9. Create CSV generation and export system





  - [x] 9.1 Implement CSV generator


    - Create CSVGenerator with proper escaping
    - Add support for custom column mappings
    - Implement batch processing for large datasets
    - _Requirements: 3.3, 3.4, 3.5_

  - [x] 9.2 Build export management


    - Create download file management system
    - Add file compression for large outputs
    - Implement secure download links with expiration
    - _Requirements: 4.4, 5.2_

  - [x] 9.3 Write tests for CSV generation


    - Test CSV formatting and escaping
    - Test custom column mapping functionality
    - Test large dataset processing
    - _Requirements: 3.3, 3.4_

- [x] 10. Set up deployment and Ubuntu server configuration





  - [x] 10.1 Create Docker configuration


    - Build Dockerfile with all dependencies
    - Create docker-compose.yml for multi-service setup
    - Add environment configuration management
    - _Requirements: 9.1, 9.2_

  - [x] 10.2 Build deployment scripts


    - Create setup.sh for Ubuntu server installation
    - Add start.sh and stop.sh scripts for service management
    - Implement update.sh for Git-based deployments
    - _Requirements: 9.3, 9.4, 9.5_

  - [x] 10.3 Create documentation and README


    - Write comprehensive setup and deployment guide
    - Add troubleshooting section for common issues
    - Create user manual for web interface
    - _Requirements: 9.2, 9.3_

  - [x] 10.4 Write deployment tests


    - Test Docker container build and startup
    - Test deployment scripts on clean Ubuntu system
    - Test Git-based update workflow
    - _Requirements: 9.1, 9.5_

- [x] 11. Integrate all components and final testing





  - [x] 11.1 Wire together all processing components


    - Connect web interface to processing engine
    - Integrate NLP pipeline with document processors
    - Connect validation system to audit interface
    - _Requirements: 5.1, 7.4_

  - [x] 11.2 Implement end-to-end error handling


    - Add comprehensive error handling across all components
    - Implement graceful degradation for service failures
    - Create user-friendly error messages and recovery options
    - _Requirements: 5.3, 4.5_

  - [x] 11.3 Performance optimization and testing


    - Optimize processing pipeline for speed and memory usage
    - Add caching for repeated operations
    - Test performance with large files and concurrent users
    - _Requirements: 5.2, 5.4_

  - [x] 11.4 Comprehensive integration testing


    - Test complete workflows with various document types
    - Test error scenarios and recovery mechanisms
    - Test concurrent user scenarios and resource management
    - _Requirements: 5.1, 5.2, 7.4_