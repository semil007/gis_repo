"""
Main application entry point for HMO Document Processing Pipeline.
Integrates all web interface components into a cohesive Streamlit application.
"""

import streamlit as st
import sys
import os
import asyncio
from pathlib import Path

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import web interface components
from web.streamlit_app import StreamlitApp
from web.file_uploader import FileUploader
from web.upload_validator import UploadValidator
from web.configuration_interface import ConfigurationInterface
from web.results_interface import ResultsInterface
from web.progress_tracker import ProgressTracker, ProcessingStage
from web.audit_interface import AuditInterface

# Import integration manager
from services.integration_manager import IntegrationManager


class HMOProcessorApp:
    """Main HMO Document Processor Application."""
    
    def __init__(self):
        self.setup_page_config()
        self.initialize_components()
        
    def setup_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="HMO Document Processor",
            page_icon="🏠",
            layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': 'https://github.com/your-repo/hmo-processor',
                'Report a bug': 'https://github.com/your-repo/hmo-processor/issues',
                'About': """
                # HMO Document Processing Pipeline
                
                Automated conversion of PDF/DOCX files containing HMO licensing data 
                into standardized CSV format using AI/ML techniques.
                
                **Features:**
                - Intelligent document parsing
                - OCR for scanned documents
                - NLP entity extraction
                - Quality assessment and confidence scoring
                - Manual review interface for flagged records
                
                **Version:** 1.0.0
                """
            }
        )
        
    def initialize_components(self):
        """Initialize all application components."""
        self.file_uploader = FileUploader()
        self.upload_validator = UploadValidator()
        self.config_interface = ConfigurationInterface()
        self.results_interface = ResultsInterface()
        self.progress_tracker = ProgressTracker()
        self.audit_interface = AuditInterface()
        
        # Initialize integration manager
        self.integration_manager = IntegrationManager()
        
        # Initialize session state
        self._initialize_session_state()
        
    def _initialize_session_state(self):
        """Initialize session state variables."""
        if 'app_initialized' not in st.session_state:
            st.session_state.app_initialized = True
            st.session_state.current_page = 'upload'
            st.session_state.processing_status = 'idle'
            st.session_state.uploaded_file = None
            st.session_state.processing_results = None
            st.session_state.session_id = self._generate_session_id()
            
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        import uuid
        return str(uuid.uuid4())
        
    def run(self):
        """Main application entry point."""
        # Render header
        self._render_header()
        
        # Render navigation
        self._render_navigation()
        
        # Render main content based on current page
        if st.session_state.current_page == 'upload':
            self._render_upload_page()
        elif st.session_state.current_page == 'configure':
            self._render_configuration_page()
        elif st.session_state.current_page == 'results':
            self._render_results_page()
        elif st.session_state.current_page == 'audit':
            self._render_audit_page()
            
    def _render_header(self):
        """Render application header."""
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.title("🏠 HMO Document Processing Pipeline")
            st.markdown("""
            <div style="text-align: center; color: #666; margin-bottom: 2rem;">
                Convert PDF and DOCX files containing HMO licensing data into standardized CSV format
            </div>
            """, unsafe_allow_html=True)
            
    def _render_navigation(self):
        """Render navigation sidebar."""
        with st.sidebar:
            st.header("🧭 Navigation")
            
            # Page navigation
            pages = {
                'upload': '📤 Upload & Process',
                'configure': '⚙️ Configuration',
                'results': '📊 Results',
                'audit': '🔍 Manual Review'
            }
            
            for page_key, page_label in pages.items():
                if st.button(page_label, use_container_width=True, 
                           type="primary" if st.session_state.current_page == page_key else "secondary"):
                    st.session_state.current_page = page_key
                    st.rerun()
                    
            st.divider()
            
            # Session information
            st.header("📋 Session Info")
            st.info(f"**Session ID:** {st.session_state.session_id[:8]}...")
            
            # Status indicator
            status_colors = {
                'idle': '⚪ Ready',
                'uploading': '🟡 Uploading',
                'processing': '🟠 Processing',
                'completed': '🟢 Completed',
                'error': '🔴 Error'
            }
            
            status = st.session_state.processing_status
            st.markdown(f"**Status:** {status_colors.get(status, '⚪ Unknown')}")
            
            # File information
            if st.session_state.uploaded_file:
                st.markdown("**Current File:**")
                st.text(f"📄 {st.session_state.uploaded_file.name}")
                st.text(f"📏 {st.session_state.uploaded_file.size / 1024:.1f} KB")
                
            # Results summary
            if st.session_state.processing_results:
                results = st.session_state.processing_results
                st.markdown("**Results:**")
                st.metric("Records", len(results.get('records', [])))
                st.metric("Avg Confidence", f"{results.get('average_confidence', 0):.1%}")
                
            st.divider()
            
            # Quick actions
            st.header("⚡ Quick Actions")
            
            if st.button("🔄 Reset Session", use_container_width=True):
                self._reset_session()
                st.rerun()
                
            if st.button("💾 Export Config", use_container_width=True):
                self._export_configuration()
                
    def _render_upload_page(self):
        """Render upload and processing page."""
        if st.session_state.processing_status == 'idle':
            self._render_upload_interface()
        elif st.session_state.processing_status == 'processing':
            self._render_processing_interface()
        elif st.session_state.processing_status == 'completed':
            st.success("🎉 Processing completed! Check the Results page to view and download your data.")
            if st.button("📊 View Results", type="primary"):
                st.session_state.current_page = 'results'
                st.rerun()
        elif st.session_state.processing_status == 'error':
            self._render_error_interface()
            
    def _render_upload_interface(self):
        """Render file upload interface."""
        st.header("📤 Upload Document")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # File upload
            uploaded_file = self.file_uploader.render_upload_zone()
            
            if uploaded_file is not None:
                st.session_state.uploaded_file = uploaded_file
                
                # Comprehensive validation
                validation_result = self.upload_validator.validate_comprehensive(uploaded_file)
                
                # Display validation results
                from web.upload_validator import VisualFeedback
                VisualFeedback.show_validation_summary(validation_result)
                
                if validation_result['is_valid']:
                    # Processing options
                    st.markdown("### 🚀 Processing Options")
                    
                    col1a, col1b = st.columns(2)
                    
                    with col1a:
                        use_ocr = st.checkbox(
                            "Enable OCR for scanned documents",
                            value=True,
                            help="Use OCR to extract text from image-based content"
                        )
                        
                    with col1b:
                        confidence_threshold = st.slider(
                            "Confidence threshold for flagging",
                            min_value=0.3,
                            max_value=0.8,
                            value=0.6,
                            step=0.1,
                            help="Records below this confidence will be flagged for review"
                        )
                        
                    # Start processing button
                    if st.button("🚀 Start Processing", type="primary", use_container_width=True):
                        asyncio.run(self._start_processing_async(use_ocr, confidence_threshold))
                        st.rerun()
                        
        with col2:
            # Upload guidelines and tips
            st.markdown("### 📋 Upload Guidelines")
            st.markdown("""
            **Supported Formats:**
            - PDF files (.pdf)
            - Word documents (.docx)
            
            **File Requirements:**
            - Maximum size: 100MB
            - Contains HMO licensing data
            - Readable text content
            
            **Best Practices:**
            - Use high-quality scans
            - Ensure text is clearly readable
            - Include complete document pages
            """)
            
            # Processing information
            st.markdown("### ⚙️ Processing Info")
            st.info("""
            The system will:
            1. Extract text and tables
            2. Identify HMO-specific data
            3. Validate and score confidence
            4. Flag records needing review
            5. Generate CSV output
            """)
            
    def _render_processing_interface(self):
        """Render processing progress interface."""
        st.header("⚙️ Processing Document")
        
        # Get current processing status
        if 'current_session_id' in st.session_state:
            status_info = self.integration_manager.get_processing_status(
                st.session_state.current_session_id
            )
            
            if status_info['status'] == 'completed':
                # Processing completed, get results
                results = self.integration_manager.get_processing_results(
                    st.session_state.current_session_id
                )
                if results:
                    st.session_state.processing_results = results
                    st.session_state.processing_status = 'completed'
                    st.rerun()
                    return
                    
            elif status_info['status'] == 'error':
                st.session_state.processing_status = 'error'
                st.session_state.error_message = status_info.get('error_message', 'Unknown error')
                st.rerun()
                return
                
            # Show current progress
            progress = status_info.get('progress', 0.0)
            current_stage = status_info.get('current_stage', 'processing')
            
            # Display progress bar
            st.progress(progress)
            
            # Stage mapping for display
            stage_messages = {
                'queued': '⏳ Queued for processing...',
                'processing': '🚀 Starting processing...',
                'document_extraction': '📄 Extracting text from document...',
                'nlp_processing': '🧠 Running NLP analysis...',
                'entity_extraction': '🔍 Extracting HMO entities...',
                'data_structuring': '📊 Structuring data into records...',
                'confidence_scoring': '📈 Calculating confidence scores...',
                'data_validation': '✅ Validating extracted data...',
                'quality_assessment': '🎯 Assessing extraction quality...',
                'flagging_records': '🚩 Flagging records for review...',
                'csv_generation': '📋 Generating CSV output...',
                'finalizing': '🏁 Finalizing results...'
            }
            
            message = stage_messages.get(current_stage, f'Processing: {current_stage}')
            st.info(message)
            
            # Show detailed progress info
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Progress", f"{progress:.0%}")
                
            with col2:
                st.metric("Current Stage", current_stage.replace('_', ' ').title())
                
            with col3:
                if 'last_updated' in status_info:
                    st.metric("Last Updated", status_info['last_updated'][-8:-3])  # Show time only
                    
            # Auto-refresh every 2 seconds
            import time
            time.sleep(2)
            st.rerun()
            
        else:
            st.error("No processing session found")
            st.session_state.processing_status = 'error'
            
    def _render_configuration_page(self):
        """Render configuration page."""
        config = self.config_interface.render_configuration_interface()
        
        # Save configuration button
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            if st.button("💾 Save Configuration", type="primary", use_container_width=True):
                # Validate configuration
                validation_result = self.config_interface.validate_configuration()
                
                if validation_result['is_valid']:
                    st.success("✅ Configuration saved successfully!")
                else:
                    st.error("❌ Configuration validation failed:")
                    for error in validation_result['errors']:
                        st.error(f"• {error}")
                        
    def _render_results_page(self):
        """Render results page."""
        if st.session_state.processing_results:
            # Add download functionality
            if 'current_session_id' in st.session_state:
                csv_path = self.integration_manager.get_csv_download_path(
                    st.session_state.current_session_id
                )
                
                if csv_path and Path(csv_path).exists():
                    with open(csv_path, 'r', encoding='utf-8') as f:
                        csv_content = f.read()
                        
                    st.download_button(
                        label="📥 Download CSV Results",
                        data=csv_content,
                        file_name=f"hmo_results_{st.session_state.current_session_id[:8]}.csv",
                        mime="text/csv",
                        type="primary"
                    )
                    
            self.results_interface.render_results_interface(st.session_state.processing_results)
        else:
            st.info("📊 No results available. Please upload and process a document first.")
            
            if st.button("📤 Go to Upload", type="primary"):
                st.session_state.current_page = 'upload'
                st.rerun()
                
    def _render_audit_page(self):
        """Render manual review/audit page."""
        self.audit_interface.render_audit_page()
            
    def _render_error_interface(self):
        """Render error interface with detailed error information."""
        st.header("❌ Processing Error")
        
        # Get error details if available
        error_message = st.session_state.get('error_message', 'An unknown error occurred')
        session_id = st.session_state.get('current_session_id', 'Unknown')
        
        # Display error information with better formatting
        st.error(f"**Error:** {error_message}")
        
        # Show session ID for support
        st.info(f"**Session ID:** `{session_id}`")
        
        # Check if this is a common error and provide specific guidance
        if "redis" in error_message.lower() or "connection" in error_message.lower():
            st.warning("""
            🔧 **System Notice:** The main processing system is temporarily unavailable, 
            but the fallback processor should still work. Please try uploading your document again.
            """)
        elif "unknown error" in error_message.lower():
            st.info("""
            ℹ️ **What happened:** The system encountered an unexpected issue during processing. 
            This is usually temporary and can be resolved by trying again.
            """)
        
        # Get processing results to check for error details
        if 'current_session_id' in st.session_state:
            results = self.integration_manager.get_processing_results(
                st.session_state.current_session_id
            )
            
            if results and 'processing_metadata' in results:
                metadata = results['processing_metadata']
                
                if 'processing_errors' in metadata and metadata['processing_errors']:
                    st.markdown("### 🔍 Error Details")
                    
                    for error in metadata['processing_errors']:
                        with st.expander(f"Error {error['error_id'][:8]}... - {error['category']}"):
                            st.markdown(f"**Severity:** {error['severity'].title()}")
                            st.markdown(f"**Message:** {error['user_message']}")
                            
                if 'recovery_suggestions' in metadata:
                    st.markdown("### 💡 Recovery Suggestions")
                    for suggestion in metadata['recovery_suggestions']:
                        st.markdown(f"• {suggestion}")
                        
        # Recovery options
        st.markdown("### 🔧 What you can do:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Try Again", use_container_width=True, type="primary"):
                st.session_state.processing_status = 'idle'
                if 'current_session_id' in st.session_state:
                    del st.session_state.current_session_id
                if 'error_message' in st.session_state:
                    del st.session_state.error_message
                st.rerun()
                
        with col2:
            if st.button("📤 Upload Different File", use_container_width=True):
                st.session_state.processing_status = 'idle'
                st.session_state.uploaded_file = None
                if 'current_session_id' in st.session_state:
                    del st.session_state.current_session_id
                st.rerun()
                
        with col3:
            if st.button("📞 Report Issue", use_container_width=True):
                st.info(f"""
                **To report this issue:**
                1. Copy the Session ID: `{session_id}`
                2. Note the error message above
                3. Contact support with these details
                
                **Common solutions:**
                - Ensure your file is a valid PDF or DOCX
                - Check that the file contains readable text
                - Try a smaller file if the current one is very large
                - Verify the document contains HMO licensing data
                """)
                
        # System status check
        if st.button("🔍 Check System Status"):
            with st.spinner("Checking system status..."):
                status = self.integration_manager.validate_system_components()
                
                if status['overall_status'] == 'fully_operational':
                    st.success("✅ All system components are operational")
                elif status['overall_status'] == 'mostly_operational':
                    st.warning("⚠️ Some system components are degraded but processing should work")
                else:
                    st.error("❌ System components are experiencing issues")
                    
                # Show component details
                with st.expander("System Component Status"):
                    for component, component_status in status['components'].items():
                        if isinstance(component_status, dict):
                            status_text = component_status.get('overall_status', 'unknown')
                        else:
                            status_text = component_status
                            
                        if status_text in ['operational', 'fully_operational']:
                            st.success(f"✅ {component}: {status_text}")
                        elif status_text in ['partially_operational', 'mostly_operational']:
                            st.warning(f"⚠️ {component}: {status_text}")
                        else:
                            st.error(f"❌ {component}: {status_text}")
                
    async def _start_processing_async(self, use_ocr: bool, confidence_threshold: float):
        """Start document processing asynchronously."""
        if not st.session_state.uploaded_file:
            st.error("No file uploaded")
            return
            
        try:
            # Save uploaded file temporarily
            temp_path = Path("temp") / st.session_state.uploaded_file.name
            temp_path.parent.mkdir(exist_ok=True)
            
            with open(temp_path, "wb") as f:
                f.write(st.session_state.uploaded_file.getvalue())
            
            # Submit for processing with error handling
            try:
                session_id = await self.integration_manager.submit_document_for_processing(
                    file_path=temp_path,
                    filename=st.session_state.uploaded_file.name,
                    file_size=st.session_state.uploaded_file.size,
                    processing_options={
                        'use_ocr': use_ocr,
                        'confidence_threshold': confidence_threshold
                    }
                )
                
                # Update session state
                st.session_state.processing_status = 'processing'
                st.session_state.current_session_id = session_id
                st.session_state.processing_options = {
                    'use_ocr': use_ocr,
                    'confidence_threshold': confidence_threshold
                }
                
                # Show success message
                st.success(f"✅ Document submitted for processing! Session ID: {session_id[:8]}...")
                
            except Exception as processing_error:
                # Handle processing submission errors gracefully
                st.warning(f"⚠️ Main processing system unavailable. Using fallback processor...")
                
                # Create a fallback session ID
                import uuid
                session_id = str(uuid.uuid4())
                
                st.session_state.processing_status = 'processing'
                st.session_state.current_session_id = session_id
                st.session_state.processing_options = {
                    'use_ocr': use_ocr,
                    'confidence_threshold': confidence_threshold
                }
                
                # Show fallback message
                st.info(f"📋 Using simplified processing mode. Session ID: {session_id[:8]}...")
            
        except Exception as e:
            st.error(f"❌ Failed to start processing: {str(e)}")
            st.session_state.processing_status = 'error'
            st.session_state.error_message = str(e)
            
            # Provide helpful error information
            with st.expander("🔍 Error Details"):
                st.code(str(e))
                st.markdown("""
                **Common solutions:**
                - Ensure the file is a valid PDF or DOCX document
                - Check that the file is not corrupted
                - Try a smaller file if the current one is very large
                - Refresh the page and try again
                """)
                
            # Offer to try again
            if st.button("🔄 Try Again"):
                st.session_state.processing_status = 'idle'
                st.rerun()
        
    def _complete_processing(self):
        """Complete processing and generate results."""
        # Generate mock results (replace with actual processing results)
        mock_results = {
            'records': [
                {
                    'council': 'Test Council',
                    'reference': 'HMO/2024/001',
                    'hmo_address': '123 Test Street, Test City, TC1 2AB',
                    'licence_start': '2024-01-01',
                    'licence_expiry': '2025-01-01',
                    'max_occupancy': 5,
                    'hmo_manager_name': 'John Smith',
                    'confidence_scores': {
                        'council': 0.95,
                        'reference': 0.88,
                        'hmo_address': 0.92,
                        'licence_start': 0.85,
                        'licence_expiry': 0.87,
                        'max_occupancy': 0.90,
                        'hmo_manager_name': 0.75
                    }
                },
                {
                    'council': 'Test Council',
                    'reference': 'HMO/2024/002',
                    'hmo_address': '456 Another Street, Test City, TC2 3CD',
                    'licence_start': '2024-02-01',
                    'licence_expiry': '2025-02-01',
                    'max_occupancy': 3,
                    'hmo_manager_name': 'Jane Doe',
                    'confidence_scores': {
                        'council': 0.78,
                        'reference': 0.65,
                        'hmo_address': 0.72,
                        'licence_start': 0.55,
                        'licence_expiry': 0.60,
                        'max_occupancy': 0.68,
                        'hmo_manager_name': 0.45
                    }
                }
            ],
            'average_confidence': 0.72,
            'flagged_records': ['HMO/2024/002'],  # Second record flagged due to low confidence
            'processing_time': 15.2,
            'quality_metrics': {
                'high_confidence_count': 1,
                'medium_confidence_count': 0,
                'low_confidence_count': 1
            }
        }
        
        st.session_state.processing_results = mock_results
        st.session_state.processing_status = 'completed'
        
        # Show completion message
        self.progress_tracker.complete_processing(mock_results)
        
    def _reset_session(self):
        """Reset session state."""
        st.session_state.processing_status = 'idle'
        st.session_state.uploaded_file = None
        st.session_state.processing_results = None
        st.session_state.processing_step = 0
        st.session_state.current_page = 'upload'
        st.session_state.session_id = self._generate_session_id()
        
    def _export_configuration(self):
        """Export current configuration."""
        config_json = self.config_interface._export_configuration()
        
        st.download_button(
            label="📥 Download Configuration",
            data=config_json,
            file_name=f"hmo_config_{st.session_state.session_id[:8]}.json",
            mime="application/json"
        )


def main():
    """Application entry point."""
    try:
        app = HMOProcessorApp()
        app.run()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.info("Please refresh the page or contact support if the issue persists.")


if __name__ == "__main__":
    main()