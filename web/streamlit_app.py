"""
Main Streamlit application for HMO document processing pipeline.
Provides clean, intuitive interface for file upload and processing.
"""

import streamlit as st
import os
import time
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

# Import our processing components
from models.processing_session import ProcessingSession
from models.hmo_record import HMORecord
from models.column_mapping import ColumnMapping
from processors.unified_processor import UnifiedDocumentProcessor
from services.data_validator import DataValidator
from services.quality_assessment import QualityAssessment


class StreamlitApp:
    """Main Streamlit application class for HMO document processing."""
    
    def __init__(self):
        self.setup_page_config()
        self.initialize_session_state()
        
    def setup_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="HMO Document Processor",
            page_icon="📄",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
    def initialize_session_state(self):
        """Initialize session state variables."""
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        if 'processing_status' not in st.session_state:
            st.session_state.processing_status = 'idle'
        if 'uploaded_file' not in st.session_state:
            st.session_state.uploaded_file = None
        if 'processing_results' not in st.session_state:
            st.session_state.processing_results = None
        if 'column_mappings' not in st.session_state:
            st.session_state.column_mappings = self.get_default_column_mappings()
            
    def get_default_column_mappings(self) -> Dict[str, str]:
        """Get default column mappings for HMO data."""
        return {
            'Council': 'council',
            'Reference': 'reference', 
            'HMO Address': 'hmo_address',
            'Licence Start': 'licence_start',
            'Licence Expiry': 'licence_expiry',
            'Max Occupancy': 'max_occupancy',
            'Manager Name': 'hmo_manager_name',
            'Manager Address': 'hmo_manager_address',
            'Holder Name': 'licence_holder_name',
            'Holder Address': 'licence_holder_address',
            'Households': 'number_of_households',
            'Shared Kitchens': 'number_of_shared_kitchens',
            'Shared Bathrooms': 'number_of_shared_bathrooms',
            'Shared Toilets': 'number_of_shared_toilets',
            'Storeys': 'number_of_storeys'
        }
        
    def render_header(self):
        """Render application header with title and description."""
        st.title("🏠 HMO Document Processing Pipeline")
        st.markdown("""
        Convert PDF and DOCX files containing HMO licensing data into standardized CSV format.
        Upload your documents and get structured data with confidence scoring and quality assessment.
        """)
        st.divider()
        
    def render_sidebar(self):
        """Render sidebar with navigation and status information."""
        with st.sidebar:
            st.header("📊 Processing Status")
            
            # Display current session info
            st.info(f"Session ID: {st.session_state.session_id[:8]}...")
            
            # Status indicator
            status_colors = {
                'idle': '⚪',
                'uploading': '🟡', 
                'processing': '🟠',
                'completed': '🟢',
                'error': '🔴'
            }
            
            status = st.session_state.processing_status
            st.markdown(f"**Status:** {status_colors.get(status, '⚪')} {status.title()}")
            
            # File information
            if st.session_state.uploaded_file:
                st.markdown("**Current File:**")
                st.text(f"📄 {st.session_state.uploaded_file.name}")
                st.text(f"📏 {st.session_state.uploaded_file.size / 1024:.1f} KB")
                
            # Processing results summary
            if st.session_state.processing_results:
                results = st.session_state.processing_results
                st.markdown("**Results Summary:**")
                st.metric("Records Extracted", len(results.get('records', [])))
                st.metric("Average Confidence", f"{results.get('avg_confidence', 0):.1%}")
                
            st.divider()
            
            # Navigation
            st.header("🧭 Navigation")
            if st.button("🔄 Reset Session", use_container_width=True):
                self.reset_session()
                st.rerun()
                
    def render_main_content(self):
        """Render main content area based on current state."""
        if st.session_state.processing_status == 'idle':
            self.render_upload_interface()
        elif st.session_state.processing_status == 'uploading':
            self.render_upload_progress()
        elif st.session_state.processing_status == 'processing':
            self.render_processing_progress()
        elif st.session_state.processing_status == 'completed':
            self.render_results_interface()
        elif st.session_state.processing_status == 'error':
            self.render_error_interface()
            
    def render_upload_interface(self):
        """Render file upload interface."""
        st.header("📤 Upload Document")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # File uploader with drag and drop
            uploaded_file = st.file_uploader(
                "Choose a PDF or DOCX file",
                type=['pdf', 'docx'],
                help="Drag and drop your file here or click to browse. Maximum file size: 100MB",
                key="file_uploader"
            )
            
            if uploaded_file is not None:
                st.session_state.uploaded_file = uploaded_file
                
                # File validation
                if self.validate_uploaded_file(uploaded_file):
                    st.success(f"✅ File '{uploaded_file.name}' is ready for processing")
                    
                    # Process button
                    if st.button("🚀 Start Processing", type="primary", use_container_width=True):
                        self.start_processing()
                        st.rerun()
                else:
                    st.error("❌ File validation failed. Please check file format and size.")
                    
        with col2:
            # Upload guidelines
            st.markdown("### 📋 Upload Guidelines")
            st.markdown("""
            **Supported Formats:**
            - PDF files (.pdf)
            - Word documents (.docx)
            
            **File Requirements:**
            - Maximum size: 100MB
            - Contains HMO licensing data
            - Text should be readable (not heavily corrupted)
            
            **Expected Content:**
            - Council information
            - License references
            - Property addresses
            - Manager/holder details
            - Occupancy information
            """)
            
    def render_processing_progress(self):
        """Render processing progress interface."""
        st.header("⚙️ Processing Document")
        
        # Progress bar and status
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Simulate processing steps
        processing_steps = [
            "Analyzing document format...",
            "Extracting text content...", 
            "Detecting tables and structure...",
            "Running NLP entity extraction...",
            "Validating extracted data...",
            "Generating confidence scores...",
            "Creating CSV output..."
        ]
        
        for i, step in enumerate(processing_steps):
            progress = (i + 1) / len(processing_steps)
            progress_bar.progress(progress)
            status_text.text(f"Step {i+1}/{len(processing_steps)}: {step}")
            time.sleep(0.5)  # Simulate processing time
            
        # Complete processing
        st.session_state.processing_status = 'completed'
        st.session_state.processing_results = self.mock_processing_results()
        st.rerun()
        
    def mock_processing_results(self) -> Dict[str, Any]:
        """Generate mock processing results for demonstration."""
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
                        'hmo_address': 0.92
                    }
                }
            ],
            'avg_confidence': 0.85,
            'flagged_records': [],
            'processing_time': 12.5
        }
        
    def validate_uploaded_file(self, file) -> bool:
        """Validate uploaded file format and size."""
        # Check file size (100MB limit)
        if file.size > 100 * 1024 * 1024:
            st.error("File size exceeds 100MB limit")
            return False
            
        # Check file extension
        allowed_extensions = ['.pdf', '.docx']
        file_extension = os.path.splitext(file.name)[1].lower()
        if file_extension not in allowed_extensions:
            st.error(f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}")
            return False
            
        return True
        
    def start_processing(self):
        """Start document processing workflow."""
        st.session_state.processing_status = 'processing'
        
    def reset_session(self):
        """Reset session state to initial values."""
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.processing_status = 'idle'
        st.session_state.uploaded_file = None
        st.session_state.processing_results = None
        
    def render_error_interface(self):
        """Render error interface with recovery options."""
        st.header("❌ Processing Error")
        st.error("An error occurred during document processing.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Try Again", use_container_width=True):
                st.session_state.processing_status = 'idle'
                st.rerun()
                
        with col2:
            if st.button("📞 Report Issue", use_container_width=True):
                st.info("Please contact support with your session ID")
                
    def run(self):
        """Main application entry point."""
        self.render_header()
        self.render_sidebar()
        self.render_main_content()


def main():
    """Application entry point."""
    app = StreamlitApp()
    app.run()


if __name__ == "__main__":
    main()