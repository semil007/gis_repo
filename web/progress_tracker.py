"""
Progress tracking component for document processing pipeline.
Provides visual feedback and status updates during processing.
"""

import streamlit as st
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum


class ProcessingStage(Enum):
    """Enumeration of processing stages."""
    UPLOAD = "upload"
    VALIDATION = "validation"
    TEXT_EXTRACTION = "text_extraction"
    TABLE_DETECTION = "table_detection"
    NLP_PROCESSING = "nlp_processing"
    DATA_VALIDATION = "data_validation"
    CONFIDENCE_SCORING = "confidence_scoring"
    CSV_GENERATION = "csv_generation"
    COMPLETED = "completed"


class ProgressTracker:
    """Tracks and displays processing progress with detailed status updates."""
    
    def __init__(self):
        self.stages = [
            {
                'id': ProcessingStage.UPLOAD,
                'name': 'File Upload',
                'description': 'Uploading and validating file',
                'icon': '📤',
                'estimated_duration': 2
            },
            {
                'id': ProcessingStage.VALIDATION,
                'name': 'File Validation',
                'description': 'Checking file format and integrity',
                'icon': '🔍',
                'estimated_duration': 1
            },
            {
                'id': ProcessingStage.TEXT_EXTRACTION,
                'name': 'Text Extraction',
                'description': 'Extracting text content from document',
                'icon': '📄',
                'estimated_duration': 5
            },
            {
                'id': ProcessingStage.TABLE_DETECTION,
                'name': 'Table Detection',
                'description': 'Identifying and parsing tables',
                'icon': '📊',
                'estimated_duration': 3
            },
            {
                'id': ProcessingStage.NLP_PROCESSING,
                'name': 'NLP Processing',
                'description': 'Extracting entities and structured data',
                'icon': '🧠',
                'estimated_duration': 8
            },
            {
                'id': ProcessingStage.DATA_VALIDATION,
                'name': 'Data Validation',
                'description': 'Validating extracted data quality',
                'icon': '✅',
                'estimated_duration': 2
            },
            {
                'id': ProcessingStage.CONFIDENCE_SCORING,
                'name': 'Confidence Scoring',
                'description': 'Calculating confidence scores',
                'icon': '📈',
                'estimated_duration': 1
            },
            {
                'id': ProcessingStage.CSV_GENERATION,
                'name': 'CSV Generation',
                'description': 'Generating final CSV output',
                'icon': '📋',
                'estimated_duration': 2
            }
        ]
        
        self.current_stage_index = 0
        self.start_time = None
        self.stage_start_time = None
        
    def initialize_progress_display(self) -> None:
        """Initialize progress display components."""
        st.markdown("### ⚙️ Processing Progress")
        
        # Create containers for different progress elements
        self.overall_progress_container = st.container()
        self.current_stage_container = st.container()
        self.stage_details_container = st.container()
        self.time_estimates_container = st.container()
        
        # Initialize session state for progress tracking
        if 'progress_start_time' not in st.session_state:
            st.session_state.progress_start_time = datetime.now()
            
    def start_processing(self) -> None:
        """Start the processing workflow."""
        self.start_time = datetime.now()
        self.stage_start_time = datetime.now()
        st.session_state.progress_start_time = self.start_time
        
    def update_stage(self, stage: ProcessingStage, progress_within_stage: float = 0.0, 
                    custom_message: str = None) -> None:
        """
        Update current processing stage.
        
        Args:
            stage: Current processing stage
            progress_within_stage: Progress within current stage (0.0 to 1.0)
            custom_message: Optional custom status message
        """
        # Find stage index
        stage_index = next((i for i, s in enumerate(self.stages) if s['id'] == stage), 0)
        self.current_stage_index = stage_index
        
        # Update display
        self._render_overall_progress(progress_within_stage)
        self._render_current_stage(custom_message)
        self._render_stage_timeline()
        self._render_time_estimates()
        
    def _render_overall_progress(self, stage_progress: float) -> None:
        """Render overall progress bar."""
        with self.overall_progress_container:
            total_stages = len(self.stages)
            overall_progress = (self.current_stage_index + stage_progress) / total_stages
            
            st.progress(overall_progress)
            st.markdown(f"**Overall Progress:** {overall_progress:.1%} "
                       f"(Stage {self.current_stage_index + 1} of {total_stages})")
            
    def _render_current_stage(self, custom_message: str = None) -> None:
        """Render current stage information."""
        with self.current_stage_container:
            current_stage = self.stages[self.current_stage_index]
            
            col1, col2 = st.columns([1, 4])
            
            with col1:
                st.markdown(f"## {current_stage['icon']}")
                
            with col2:
                st.markdown(f"**{current_stage['name']}**")
                message = custom_message or current_stage['description']
                st.markdown(f"*{message}*")
                
    def _render_stage_timeline(self) -> None:
        """Render timeline of all processing stages."""
        with self.stage_details_container:
            st.markdown("#### Processing Timeline")
            
            for i, stage in enumerate(self.stages):
                col1, col2, col3 = st.columns([1, 6, 2])
                
                with col1:
                    if i < self.current_stage_index:
                        st.markdown(f"✅ {stage['icon']}")
                    elif i == self.current_stage_index:
                        st.markdown(f"🔄 {stage['icon']}")
                    else:
                        st.markdown(f"⏳ {stage['icon']}")
                        
                with col2:
                    status_text = stage['name']
                    if i < self.current_stage_index:
                        status_text += " - Completed"
                    elif i == self.current_stage_index:
                        status_text += " - In Progress"
                    else:
                        status_text += " - Pending"
                        
                    st.markdown(status_text)
                    
                with col3:
                    st.markdown(f"{stage['estimated_duration']}s")
                    
    def _render_time_estimates(self) -> None:
        """Render time estimates and elapsed time."""
        with self.time_estimates_container:
            if self.start_time:
                elapsed = datetime.now() - self.start_time
                
                # Calculate estimated total time
                total_estimated = sum(stage['estimated_duration'] for stage in self.stages)
                completed_time = sum(stage['estimated_duration'] 
                                   for stage in self.stages[:self.current_stage_index])
                remaining_estimated = total_estimated - completed_time
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Elapsed Time", f"{elapsed.seconds}s")
                    
                with col2:
                    st.metric("Estimated Remaining", f"{remaining_estimated}s")
                    
                with col3:
                    estimated_completion = datetime.now() + timedelta(seconds=remaining_estimated)
                    st.metric("Est. Completion", estimated_completion.strftime("%H:%M:%S"))
                    
    def complete_processing(self, results_summary: Dict) -> None:
        """
        Mark processing as completed and show results summary.
        
        Args:
            results_summary: Dictionary containing processing results
        """
        self.current_stage_index = len(self.stages)
        
        with self.overall_progress_container:
            st.progress(1.0)
            st.success("🎉 Processing completed successfully!")
            
        with self.current_stage_container:
            st.markdown("### ✅ Processing Complete")
            
            # Display results summary
            if results_summary:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Records Found", results_summary.get('total_records', 0))
                    
                with col2:
                    avg_confidence = results_summary.get('average_confidence', 0)
                    st.metric("Avg Confidence", f"{avg_confidence:.1%}")
                    
                with col3:
                    flagged = results_summary.get('flagged_records', 0)
                    st.metric("Flagged Records", flagged)
                    
                with col4:
                    processing_time = results_summary.get('processing_time', 0)
                    st.metric("Processing Time", f"{processing_time:.1f}s")
                    
    def show_error(self, error_message: str, stage: ProcessingStage = None) -> None:
        """
        Display error state in progress tracker.
        
        Args:
            error_message: Error message to display
            stage: Stage where error occurred (optional)
        """
        with self.overall_progress_container:
            st.error("❌ Processing failed")
            
        with self.current_stage_container:
            st.markdown("### ❌ Error Occurred")
            st.error(error_message)
            
            if stage:
                failed_stage = next((s for s in self.stages if s['id'] == stage), None)
                if failed_stage:
                    st.markdown(f"**Failed at stage:** {failed_stage['name']}")
                    
        # Show retry options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Retry Processing", use_container_width=True):
                st.session_state.processing_status = 'idle'
                st.rerun()
                
        with col2:
            if st.button("📞 Report Issue", use_container_width=True):
                st.info("Please contact support with the error details above.")


class StatusIndicator:
    """Simple status indicator component."""
    
    @staticmethod
    def show_status(status: str, message: str = None) -> None:
        """
        Show status with appropriate icon and color.
        
        Args:
            status: Status type (idle, processing, completed, error)
            message: Optional status message
        """
        status_config = {
            'idle': {'icon': '⚪', 'color': 'gray'},
            'uploading': {'icon': '🟡', 'color': 'orange'},
            'processing': {'icon': '🟠', 'color': 'orange'},
            'completed': {'icon': '🟢', 'color': 'green'},
            'error': {'icon': '🔴', 'color': 'red'}
        }
        
        config = status_config.get(status, status_config['idle'])
        display_text = f"{config['icon']} {status.title()}"
        
        if message:
            display_text += f" - {message}"
            
        st.markdown(f"**Status:** {display_text}")


class ProcessingMetrics:
    """Component for displaying processing metrics and statistics."""
    
    @staticmethod
    def display_metrics(metrics: Dict) -> None:
        """
        Display processing metrics in a formatted layout.
        
        Args:
            metrics: Dictionary containing various metrics
        """
        st.markdown("### 📊 Processing Metrics")
        
        # Primary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Records",
                metrics.get('total_records', 0),
                delta=metrics.get('records_delta')
            )
            
        with col2:
            confidence = metrics.get('average_confidence', 0)
            st.metric(
                "Avg Confidence",
                f"{confidence:.1%}",
                delta=f"{metrics.get('confidence_delta', 0):.1%}" if metrics.get('confidence_delta') else None
            )
            
        with col3:
            st.metric(
                "Processing Time",
                f"{metrics.get('processing_time', 0):.1f}s",
                delta=f"{metrics.get('time_delta', 0):.1f}s" if metrics.get('time_delta') else None
            )
            
        with col4:
            st.metric(
                "Success Rate",
                f"{metrics.get('success_rate', 0):.1%}",
                delta=f"{metrics.get('success_delta', 0):.1%}" if metrics.get('success_delta') else None
            )
            
        # Secondary metrics
        if metrics.get('show_detailed_metrics', False):
            st.markdown("#### Detailed Metrics")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Data Quality:**")
                st.metric("High Confidence", metrics.get('high_confidence_records', 0))
                st.metric("Medium Confidence", metrics.get('medium_confidence_records', 0))
                st.metric("Low Confidence", metrics.get('low_confidence_records', 0))
                
            with col2:
                st.markdown("**Processing Details:**")
                st.metric("Pages Processed", metrics.get('pages_processed', 0))
                st.metric("Tables Detected", metrics.get('tables_detected', 0))
                st.metric("Entities Extracted", metrics.get('entities_extracted', 0))