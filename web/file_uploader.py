"""
File upload component with drag-and-drop functionality and validation.
Handles file size limits, format validation, and upload progress tracking.
"""

import streamlit as st
import os
import tempfile
from typing import Optional, Dict, List
from datetime import datetime
import uuid


class FileUploader:
    """Handles file upload operations with validation and progress tracking."""
    
    def __init__(self, max_file_size_mb: int = 100):
        self.max_file_size_mb = max_file_size_mb
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.supported_formats = ['.pdf', '.docx']
        
    def render_upload_zone(self, key: str = "file_upload") -> Optional[st.runtime.uploaded_file_manager.UploadedFile]:
        """
        Render drag-and-drop file upload zone with visual feedback.
        
        Args:
            key: Unique key for the file uploader widget
            
        Returns:
            Uploaded file object or None
        """
        st.markdown("### 📁 Upload Your Document")
        
        # Custom CSS for enhanced drag-and-drop styling
        st.markdown("""
        <style>
        .uploadedFile {
            border: 2px dashed #cccccc;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            background-color: #f9f9f9;
            transition: all 0.3s ease;
        }
        .uploadedFile:hover {
            border-color: #1f77b4;
            background-color: #e6f3ff;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # File uploader with enhanced UI
        uploaded_file = st.file_uploader(
            label="",
            type=self.get_supported_extensions(),
            help=f"Drag and drop your file here or click to browse. Max size: {self.max_file_size_mb}MB",
            key=key,
            label_visibility="collapsed"
        )
        
        # Display upload guidelines
        self._render_upload_guidelines()
        
        return uploaded_file
        
    def validate_file(self, uploaded_file) -> Dict[str, any]:
        """
        Validate uploaded file against size and format requirements.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'file_info': {}
        }
        
        if uploaded_file is None:
            validation_result['is_valid'] = False
            validation_result['errors'].append("No file uploaded")
            return validation_result
            
        # Extract file information
        file_name = uploaded_file.name
        file_size = uploaded_file.size
        file_extension = os.path.splitext(file_name)[1].lower()
        
        validation_result['file_info'] = {
            'name': file_name,
            'size': file_size,
            'size_mb': file_size / (1024 * 1024),
            'extension': file_extension,
            'upload_time': datetime.now()
        }
        
        # Validate file size
        if file_size > self.max_file_size_bytes:
            validation_result['is_valid'] = False
            validation_result['errors'].append(
                f"File size ({file_size / (1024 * 1024):.1f}MB) exceeds maximum allowed size ({self.max_file_size_mb}MB)"
            )
            
        # Validate file format
        if file_extension not in self.supported_formats:
            validation_result['is_valid'] = False
            validation_result['errors'].append(
                f"Unsupported file format '{file_extension}'. Supported formats: {', '.join(self.supported_formats)}"
            )
            
        # Add warnings for large files
        if file_size > (self.max_file_size_bytes * 0.8):
            validation_result['warnings'].append(
                "Large file detected. Processing may take longer than usual."
            )
            
        return validation_result
        
    def display_validation_results(self, validation_result: Dict[str, any]) -> None:
        """
        Display validation results with appropriate styling.
        
        Args:
            validation_result: Result from validate_file method
        """
        if validation_result['is_valid']:
            file_info = validation_result['file_info']
            st.success(f"✅ File '{file_info['name']}' is ready for processing")
            
            # Display file details
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File Size", f"{file_info['size_mb']:.1f} MB")
            with col2:
                st.metric("Format", file_info['extension'].upper())
            with col3:
                st.metric("Status", "✅ Valid")
                
            # Display warnings if any
            for warning in validation_result['warnings']:
                st.warning(f"⚠️ {warning}")
                
        else:
            st.error("❌ File validation failed:")
            for error in validation_result['errors']:
                st.error(f"• {error}")
                
    def save_uploaded_file(self, uploaded_file, session_id: str) -> Optional[str]:
        """
        Save uploaded file to temporary storage.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            session_id: Current session identifier
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            # Create session-specific temporary directory
            temp_dir = os.path.join(tempfile.gettempdir(), f"hmo_processor_{session_id}")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Generate unique filename
            file_extension = os.path.splitext(uploaded_file.name)[1]
            safe_filename = f"uploaded_document_{uuid.uuid4().hex[:8]}{file_extension}"
            file_path = os.path.join(temp_dir, safe_filename)
            
            # Save file
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            return file_path
            
        except Exception as e:
            st.error(f"Failed to save uploaded file: {str(e)}")
            return None
            
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions without dots."""
        return [ext.lstrip('.') for ext in self.supported_formats]
        
    def _render_upload_guidelines(self) -> None:
        """Render upload guidelines and requirements."""
        with st.expander("📋 Upload Guidelines", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Supported Formats:**")
                st.markdown("• PDF files (.pdf)")
                st.markdown("• Word documents (.docx)")
                st.markdown("")
                st.markdown("**File Requirements:**")
                st.markdown(f"• Maximum size: {self.max_file_size_mb}MB")
                st.markdown("• Readable text content")
                st.markdown("• Contains HMO licensing data")
                
            with col2:
                st.markdown("**Expected Content:**")
                st.markdown("• Council/authority information")
                st.markdown("• License reference numbers")
                st.markdown("• Property addresses")
                st.markdown("• Manager/holder details")
                st.markdown("• Occupancy information")
                st.markdown("• License dates")
                
    def render_upload_progress(self, progress: float, status_message: str) -> None:
        """
        Render upload progress indicator.
        
        Args:
            progress: Progress value between 0.0 and 1.0
            status_message: Current status message
        """
        st.markdown("### 📤 Uploading File...")
        
        progress_bar = st.progress(progress)
        st.text(status_message)
        
        if progress >= 1.0:
            st.success("✅ Upload completed successfully!")
            
    def cleanup_temp_files(self, session_id: str) -> None:
        """
        Clean up temporary files for a session.
        
        Args:
            session_id: Session identifier for cleanup
        """
        try:
            temp_dir = os.path.join(tempfile.gettempdir(), f"hmo_processor_{session_id}")
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
        except Exception as e:
            # Log error but don't fail the application
            print(f"Warning: Failed to cleanup temp files for session {session_id}: {e}")


class UploadProgressTracker:
    """Tracks and displays upload progress with detailed status updates."""
    
    def __init__(self):
        self.current_step = 0
        self.total_steps = 5
        self.step_messages = [
            "Initializing upload...",
            "Validating file format...",
            "Checking file size...",
            "Saving file to temporary storage...",
            "Upload completed successfully!"
        ]
        
    def update_progress(self, step: int, custom_message: str = None) -> None:
        """
        Update progress display.
        
        Args:
            step: Current step number (0-based)
            custom_message: Optional custom message to display
        """
        self.current_step = min(step, self.total_steps - 1)
        progress = (self.current_step + 1) / self.total_steps
        
        message = custom_message or self.step_messages[self.current_step]
        
        # Update progress bar and status
        if 'upload_progress_bar' not in st.session_state:
            st.session_state.upload_progress_bar = st.progress(0)
            st.session_state.upload_status_text = st.empty()
            
        st.session_state.upload_progress_bar.progress(progress)
        st.session_state.upload_status_text.text(f"Step {self.current_step + 1}/{self.total_steps}: {message}")
        
    def complete(self) -> None:
        """Mark upload as completed."""
        self.update_progress(self.total_steps - 1)
        
    def reset(self) -> None:
        """Reset progress tracker."""
        self.current_step = 0
        if 'upload_progress_bar' in st.session_state:
            del st.session_state.upload_progress_bar
        if 'upload_status_text' in st.session_state:
            del st.session_state.upload_status_text