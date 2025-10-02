"""
Audit tracking and export functionality for HMO record reviews.
Provides review status management, audit reports, and data export capabilities.
"""

import streamlit as st
import pandas as pd
import json
import csv
import io
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from services.audit_manager import AuditManager, FlaggedRecord, ReviewStatus, AuditAction
from models.processing_session import SessionManager


class AuditTracker:
    """
    Audit tracking system for managing review status and generating reports.
    
    Provides functionality for:
    - Review status management and tracking
    - Audit report generation with statistics
    - Export functionality for corrected data
    """
    
    def __init__(self, audit_manager: AuditManager, session_manager: SessionManager):
        """
        Initialize audit tracker.
        
        Args:
            audit_manager: AuditManager instance
            session_manager: SessionManager instance
        """
        self.audit_manager = audit_manager
        self.session_manager = session_manager
        
    def render_audit_tracking_interface(self, session_id: Optional[str] = None) -> None:
        """
        Render audit tracking and export interface.
        
        Args:
            session_id: Optional session ID to filter by
            
        Requirements: 10.4, 10.5
        """
        st.header("📊 Audit Tracking & Export")
        
        # Create tabs for different tracking views
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Status Overview",
            "📋 Detailed Reports", 
            "📤 Export Data",
            "⏱️ Performance Metrics"
        ])
        
        with tab1:
            self._render_status_overview(session_id)
            
        with tab2:
            self._render_detailed_reports(session_id)
            
        with tab3:
            self._render_export_interface(session_id)
            
        with tab4:
            self._render_performance_metrics(session_id)
            
    def _render_status_overview(self, session_id: Optional[str] = None) -> None:
        """
        Render audit status overview with key metrics.
        
        Args:
            session_id: Optional session ID to filter by
        """
        st.markdown("### 📊 Review Status Overview")
        
        # Get flagged records
        flagged_records = self.audit_manager.get_flagged_records(session_id=session_id)
        
        if not flagged_records:
            st.info("No flagged records found for audit tracking.")
            return
            
        # Calculate status metrics
        status_counts = self._calculate_status_metrics(flagged_records)
        
        # Display key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_flagged = len(flagged_records)
            st.metric("Total Flagged", total_flagged)
            
        with col2:
            completed = status_counts.get('approved', 0) + status_counts.get('rejected', 0)
            completion_rate = (completed / total_flagged * 100) if total_flagged > 0 else 0
            st.metric("Completion Rate", f"{completion_rate:.1f}%", 
                     delta=f"{completed}/{total_flagged}")
            
        with col3:
            pending = status_counts.get('pending', 0)
            st.metric("Pending Review", pending, 
                     delta="needs attention" if pending > 0 else "all reviewed")
            
        with col4:
            approved = status_counts.get('approved', 0)
            approval_rate = (approved / completed * 100) if completed > 0 else 0
            st.metric("Approval Rate", f"{approval_rate:.1f}%", 
                     delta=f"{approved} approved")
            
        # Status breakdown chart
        st.markdown("#### 📈 Status Breakdown")
        
        if status_counts:
            # Create status data for chart
            status_data = []
            status_colors = {
                'pending': '#FFA500',
                'in_review': '#1E90FF', 
                'approved': '#32CD32',
                'rejected': '#DC143C',
                'needs_revision': '#FF6347'
            }
            
            for status, count in status_counts.items():
                if count > 0:
                    status_data.append({
                        'Status': status.replace('_', ' ').title(),
                        'Count': count,
                        'Percentage': (count / total_flagged * 100)
                    })
                    
            if status_data:
                df = pd.DataFrame(status_data)
                
                # Display as bar chart
                st.bar_chart(df.set_index('Status')['Count'])
                
                # Display as table
                st.dataframe(df, use_container_width=True, hide_index=True)
                
        # Recent activity
        self._render_recent_activity(flagged_records)
        
    def _render_recent_activity(self, flagged_records: List[FlaggedRecord]) -> None:
        """
        Render recent audit activity.
        
        Args:
            flagged_records: List of flagged records
        """
        st.markdown("#### 🕒 Recent Activity")
        
        # Collect all recent audit actions
        recent_actions = []
        
        for record in flagged_records:
            for audit_entry in record.audit_trail:
                recent_actions.append({
                    'timestamp': audit_entry.timestamp,
                    'record_id': record.record_id[:8] + '...',
                    'action': audit_entry.action.value,
                    'reviewer': audit_entry.reviewer,
                    'comments': audit_entry.comments[:50] + '...' if len(audit_entry.comments) > 50 else audit_entry.comments
                })
                
        # Sort by timestamp (most recent first)
        recent_actions.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Display recent actions (last 10)
        if recent_actions:
            recent_df = pd.DataFrame(recent_actions[:10])
            recent_df['timestamp'] = recent_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
            
            st.dataframe(
                recent_df.rename(columns={
                    'timestamp': 'Time',
                    'record_id': 'Record',
                    'action': 'Action',
                    'reviewer': 'Reviewer',
                    'comments': 'Comments'
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No recent audit activity found.")
            
    def _render_detailed_reports(self, session_id: Optional[str] = None) -> None:
        """
        Render detailed audit reports.
        
        Args:
            session_id: Optional session ID to filter by
        """
        st.markdown("### 📋 Detailed Audit Reports")
        
        # Generate comprehensive audit report
        audit_report = self.audit_manager.generate_audit_report(session_id)
        
        if not audit_report or audit_report.get('message'):
            st.info("No audit data available for detailed reporting.")
            return
            
        # Report summary
        st.markdown("#### 📊 Report Summary")
        
        summary = audit_report.get('summary', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.json({
                'Total Flagged Records': summary.get('total_flagged_records', 0),
                'Completion Rate': f"{summary.get('completion_rate', 0):.1%}",
                'Generated': audit_report.get('report_generated', 'Unknown')
            })
            
        with col2:
            status_breakdown = summary.get('status_breakdown', {})
            if status_breakdown:
                st.json(status_breakdown)
                
        # Reviewer performance
        reviewer_performance = audit_report.get('reviewer_performance', {})
        if reviewer_performance:
            st.markdown("#### 👥 Reviewer Performance")
            
            reviewer_data = []
            for reviewer, stats in reviewer_performance.items():
                reviewer_data.append({
                    'Reviewer': reviewer,
                    'Assigned': stats.get('assigned', 0),
                    'Completed': stats.get('completed', 0),
                    'Approved': stats.get('approved', 0),
                    'Rejected': stats.get('rejected', 0),
                    'Completion Rate': f"{(stats.get('completed', 0) / max(stats.get('assigned', 1), 1) * 100):.1f}%"
                })
                
            if reviewer_data:
                reviewer_df = pd.DataFrame(reviewer_data)
                st.dataframe(reviewer_df, use_container_width=True, hide_index=True)
                
        # Flag analysis
        flag_analysis = audit_report.get('flag_analysis', {})
        if flag_analysis:
            st.markdown("#### 🚩 Flag Analysis")
            
            most_common_reasons = flag_analysis.get('most_common_reasons', [])
            if most_common_reasons:
                st.markdown("**Most Common Flag Reasons:**")
                
                for i, (reason, count) in enumerate(most_common_reasons, 1):
                    st.text(f"{i}. {reason}: {count} records")
                    
        # Correction analysis
        correction_analysis = audit_report.get('correction_analysis', {})
        if correction_analysis:
            st.markdown("#### ✏️ Correction Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Corrections", correction_analysis.get('total_corrections', 0))
                st.metric("Records with Corrections", correction_analysis.get('records_with_corrections', 0))
                
            with col2:
                most_corrected = correction_analysis.get('most_corrected_fields', {})
                if most_corrected:
                    st.markdown("**Most Corrected Fields:**")
                    
                    # Sort by correction count
                    sorted_fields = sorted(most_corrected.items(), key=lambda x: x[1], reverse=True)
                    
                    for field, count in sorted_fields[:5]:
                        st.text(f"• {field.replace('_', ' ').title()}: {count}")
                        
        # Export report button
        if st.button("📥 Download Full Report", use_container_width=True):
            self._export_audit_report(audit_report, session_id)
            
    def _render_export_interface(self, session_id: Optional[str] = None) -> None:
        """
        Render data export interface.
        
        Args:
            session_id: Optional session ID to filter by
        """
        st.markdown("### 📤 Export Audited Data")
        
        # Get available sessions for export
        if session_id:
            sessions = [{'session_id': session_id}]
        else:
            sessions = self._get_sessions_with_completed_audits()
            
        if not sessions:
            st.info("No sessions with completed audits available for export.")
            return
            
        # Session selection for export
        if len(sessions) > 1:
            session_options = {f"Session {s['session_id'][:8]}...": s['session_id'] for s in sessions}
            selected_session = st.selectbox(
                "Select session to export:",
                options=list(session_options.keys())
            )
            export_session_id = session_options[selected_session] if selected_session else None
        else:
            export_session_id = sessions[0]['session_id']
            st.info(f"Exporting data for session: {export_session_id[:8]}...")
            
        if export_session_id:
            # Export options
            st.markdown("#### 📋 Export Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                include_rejected = st.checkbox(
                    "Include rejected records",
                    value=False,
                    help="Include records that were rejected during review"
                )
                
                include_metadata = st.checkbox(
                    "Include audit metadata",
                    value=True,
                    help="Include audit trail and review information"
                )
                
            with col2:
                export_format = st.selectbox(
                    "Export format:",
                    options=['CSV', 'JSON', 'Excel'],
                    help="Choose the output format for exported data"
                )
                
                include_confidence = st.checkbox(
                    "Include confidence scores",
                    value=True,
                    help="Include confidence scores for each field"
                )
                
            # Preview export data
            st.markdown("#### 👀 Export Preview")
            
            preview_data = self._prepare_export_data(
                export_session_id, 
                include_rejected, 
                include_metadata, 
                include_confidence
            )
            
            if preview_data:
                st.info(f"Ready to export {len(preview_data)} records")
                
                # Show preview (first 3 records)
                preview_df = pd.DataFrame(preview_data[:3])
                st.dataframe(preview_df, use_container_width=True)
                
                if len(preview_data) > 3:
                    st.text(f"... and {len(preview_data) - 3} more records")
                    
                # Export buttons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📥 Download CSV", use_container_width=True):
                        self._download_csv_export(preview_data, export_session_id)
                        
                with col2:
                    if st.button("📥 Download JSON", use_container_width=True):
                        self._download_json_export(preview_data, export_session_id)
                        
                with col3:
                    if st.button("📥 Download Excel", use_container_width=True):
                        self._download_excel_export(preview_data, export_session_id)
                        
            else:
                st.warning("No data available for export with current settings.")
                
    def _render_performance_metrics(self, session_id: Optional[str] = None) -> None:
        """
        Render performance metrics and analytics.
        
        Args:
            session_id: Optional session ID to filter by
        """
        st.markdown("### ⏱️ Performance Metrics")
        
        # Get audit summary
        if session_id:
            audit_summary = self.audit_manager.get_session_audit_summary(session_id)
        else:
            # Aggregate across all sessions
            audit_summary = self._get_aggregate_performance_metrics()
            
        if not audit_summary:
            st.info("No performance data available.")
            return
            
        # Key performance indicators
        st.markdown("#### 📊 Key Performance Indicators")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_review_time = audit_summary.get('average_review_time_hours')
            if avg_review_time is not None:
                st.metric("Avg Review Time", f"{avg_review_time:.1f}h")
            else:
                st.metric("Avg Review Time", "N/A")
                
        with col2:
            completion_rate = audit_summary.get('completion_rate', 0)
            st.metric("Completion Rate", f"{completion_rate:.1%}")
            
        with col3:
            total_corrections = audit_summary.get('total_corrections_made', 0)
            st.metric("Total Corrections", total_corrections)
            
        with col4:
            total_flagged = audit_summary.get('total_flagged', 0)
            st.metric("Total Flagged", total_flagged)
            
        # Performance trends (if multiple sessions)
        if not session_id:
            self._render_performance_trends()
            
        # Efficiency metrics
        st.markdown("#### ⚡ Efficiency Metrics")
        
        efficiency_data = self._calculate_efficiency_metrics(session_id)
        
        if efficiency_data:
            col1, col2 = st.columns(2)
            
            with col1:
                st.json({
                    'Records per Hour': efficiency_data.get('records_per_hour', 0),
                    'Corrections per Record': efficiency_data.get('corrections_per_record', 0),
                    'First-Pass Approval Rate': f"{efficiency_data.get('first_pass_approval_rate', 0):.1%}"
                })
                
            with col2:
                quality_metrics = efficiency_data.get('quality_metrics', {})
                if quality_metrics:
                    st.json(quality_metrics)
                    
    def _calculate_status_metrics(self, flagged_records: List[FlaggedRecord]) -> Dict[str, int]:
        """
        Calculate status metrics from flagged records.
        
        Args:
            flagged_records: List of flagged records
            
        Returns:
            Dict[str, int]: Status counts
        """
        status_counts = {}
        
        for status in ReviewStatus:
            status_counts[status.value] = 0
            
        for record in flagged_records:
            status_counts[record.review_status.value] += 1
            
        return status_counts
        
    def _get_sessions_with_completed_audits(self) -> List[Dict[str, Any]]:
        """
        Get sessions that have completed audit records.
        
        Returns:
            List[Dict[str, Any]]: Sessions with completed audits
        """
        all_sessions = self.session_manager.list_sessions(limit=50)
        sessions_with_audits = []
        
        for session in all_sessions:
            session_id = session['session_id']
            flagged_records = self.audit_manager.get_flagged_records(session_id=session_id)
            
            # Check if any records are approved or rejected
            completed_count = sum(
                1 for record in flagged_records 
                if record.review_status in [ReviewStatus.APPROVED, ReviewStatus.REJECTED]
            )
            
            if completed_count > 0:
                session_info = session.copy()
                session_info['completed_audits'] = completed_count
                sessions_with_audits.append(session_info)
                
        return sessions_with_audits
        
    def _prepare_export_data(self, session_id: str, include_rejected: bool, 
                           include_metadata: bool, include_confidence: bool) -> List[Dict[str, Any]]:
        """
        Prepare data for export.
        
        Args:
            session_id: Session ID to export
            include_rejected: Whether to include rejected records
            include_metadata: Whether to include audit metadata
            include_confidence: Whether to include confidence scores
            
        Returns:
            List[Dict[str, Any]]: Prepared export data
        """
        # Get audited data from audit manager
        audited_data = self.audit_manager.export_audited_data(session_id, include_rejected)
        
        if not audited_data:
            return []
            
        # Process data based on options
        export_data = []
        
        for record_data in audited_data:
            # Start with base record data
            export_record = {}
            
            # Add main HMO fields
            hmo_fields = [
                'council', 'reference', 'hmo_address', 'licence_start', 'licence_expiry',
                'max_occupancy', 'hmo_manager_name', 'hmo_manager_address',
                'licence_holder_name', 'licence_holder_address', 'number_of_households',
                'number_of_shared_kitchens', 'number_of_shared_bathrooms',
                'number_of_shared_toilets', 'number_of_storeys'
            ]
            
            for field in hmo_fields:
                export_record[field] = record_data.get(field, '')
                
            # Add confidence scores if requested
            if include_confidence:
                confidence_scores = record_data.get('confidence_scores', {})
                for field in hmo_fields:
                    export_record[f'{field}_confidence'] = confidence_scores.get(field, 0.0)
                    
            # Add audit metadata if requested
            if include_metadata:
                audit_metadata = record_data.get('_audit_metadata', {})
                export_record.update({
                    'audit_record_id': audit_metadata.get('record_id', ''),
                    'audit_flag_reason': audit_metadata.get('flag_reason', ''),
                    'audit_review_status': audit_metadata.get('review_status', ''),
                    'audit_reviewer': audit_metadata.get('reviewer', ''),
                    'audit_review_completed': audit_metadata.get('review_completed', ''),
                    'audit_corrections_made': audit_metadata.get('corrections_made', 0)
                })
                
            export_data.append(export_record)
            
        return export_data
        
    def _download_csv_export(self, data: List[Dict[str, Any]], session_id: str) -> None:
        """
        Generate and download CSV export.
        
        Args:
            data: Export data
            session_id: Session ID for filename
        """
        if not data:
            st.error("No data to export")
            return
            
        # Create CSV content
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        csv_content = output.getvalue()
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"hmo_audit_export_{session_id[:8]}_{timestamp}.csv"
        
        # Download button
        st.download_button(
            label="📥 Download CSV File",
            data=csv_content,
            file_name=filename,
            mime="text/csv"
        )
        
    def _download_json_export(self, data: List[Dict[str, Any]], session_id: str) -> None:
        """
        Generate and download JSON export.
        
        Args:
            data: Export data
            session_id: Session ID for filename
        """
        if not data:
            st.error("No data to export")
            return
            
        # Create JSON content
        json_content = json.dumps(data, indent=2, default=str)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"hmo_audit_export_{session_id[:8]}_{timestamp}.json"
        
        # Download button
        st.download_button(
            label="📥 Download JSON File",
            data=json_content,
            file_name=filename,
            mime="application/json"
        )
        
    def _download_excel_export(self, data: List[Dict[str, Any]], session_id: str) -> None:
        """
        Generate and download Excel export.
        
        Args:
            data: Export data
            session_id: Session ID for filename
        """
        if not data:
            st.error("No data to export")
            return
            
        try:
            # Create Excel content
            df = pd.DataFrame(data)
            
            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='HMO_Audit_Data', index=False)
                
            excel_content = output.getvalue()
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"hmo_audit_export_{session_id[:8]}_{timestamp}.xlsx"
            
            # Download button
            st.download_button(
                label="📥 Download Excel File",
                data=excel_content,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except ImportError:
            st.error("Excel export requires openpyxl package. Please install it or use CSV export.")
            
    def _export_audit_report(self, audit_report: Dict[str, Any], session_id: Optional[str]) -> None:
        """
        Export audit report as JSON.
        
        Args:
            audit_report: Audit report data
            session_id: Optional session ID
        """
        # Create JSON content
        json_content = json.dumps(audit_report, indent=2, default=str)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_part = f"_{session_id[:8]}" if session_id else "_all_sessions"
        filename = f"audit_report{session_part}_{timestamp}.json"
        
        # Download button
        st.download_button(
            label="📥 Download Audit Report",
            data=json_content,
            file_name=filename,
            mime="application/json"
        )
        
    def _get_aggregate_performance_metrics(self) -> Dict[str, Any]:
        """
        Get aggregate performance metrics across all sessions.
        
        Returns:
            Dict[str, Any]: Aggregate performance metrics
        """
        # This would aggregate metrics across all sessions
        # For now, return empty dict as placeholder
        return {}
        
    def _render_performance_trends(self) -> None:
        """Render performance trends across multiple sessions."""
        st.markdown("#### 📈 Performance Trends")
        st.info("Performance trends across sessions will be implemented with historical data.")
        
    def _calculate_efficiency_metrics(self, session_id: Optional[str]) -> Dict[str, Any]:
        """
        Calculate efficiency metrics.
        
        Args:
            session_id: Optional session ID
            
        Returns:
            Dict[str, Any]: Efficiency metrics
        """
        # Placeholder for efficiency calculations
        return {
            'records_per_hour': 2.5,
            'corrections_per_record': 1.8,
            'first_pass_approval_rate': 0.65,
            'quality_metrics': {
                'avg_confidence_improvement': 0.15,
                'error_reduction_rate': 0.78
            }
        }