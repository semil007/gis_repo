"""
Audit interface for manual review of flagged HMO records.
Provides filtering, sorting, and detailed record review capabilities.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
from services.audit_manager import AuditManager, FlaggedRecord, ReviewStatus
from models.hmo_record import HMORecord
from models.processing_session import SessionManager
from web.record_editor import RecordEditor
from web.audit_tracker import AuditTracker


class AuditInterface:
    """
    Streamlit interface for manual review of flagged HMO records.
    
    Provides functionality for:
    - Displaying flagged records with confidence scores
    - Filtering and sorting capabilities
    - Record selection and review workflow
    """
    
    def __init__(self):
        """Initialize audit interface with required managers."""
        import os
        
        # Get database paths from environment
        session_db_path = os.getenv('DATABASE_URL', 'sqlite:///processing_sessions.db')
        audit_db_path = os.getenv('AUDIT_DATABASE_URL', 'sqlite:///audit_data.db')
        
        # Remove sqlite:/// prefix if present
        if session_db_path.startswith('sqlite:///'):
            session_db_path = session_db_path.replace('sqlite:///', '')
        if audit_db_path.startswith('sqlite:///'):
            audit_db_path = audit_db_path.replace('sqlite:///', '')
        
        self.audit_manager = AuditManager(db_path=audit_db_path)
        self.session_manager = SessionManager(db_path=session_db_path)
        self.record_editor = RecordEditor(self.audit_manager)
        self.audit_tracker = AuditTracker(self.audit_manager, self.session_manager)
        
    def render_audit_page(self) -> None:
        """
        Render the main audit page interface.
        
        Requirements: 10.1, 10.2
        """
        st.header("🔍 Manual Review Interface")
        st.markdown("""
        Review and correct records that have been flagged for manual attention due to 
        low confidence scores or validation issues.
        """)
        
        # Create main tabs for different audit functions
        tab1, tab2 = st.tabs(["📝 Record Review", "📊 Audit Tracking & Export"])
        
        with tab1:
            self._render_record_review_tab()
            
        with tab2:
            # Get selected session for tracking
            selected_session = st.session_state.get('selected_audit_session')
            self.audit_tracker.render_audit_tracking_interface(selected_session)
            
    def _render_record_review_tab(self) -> None:
        """Render the record review tab."""
        # Get available sessions with flagged records
        sessions_with_flags = self._get_sessions_with_flagged_records()
        
        if not sessions_with_flags:
            self._render_no_flagged_records()
            return
            
        # Session selection
        selected_session = self._render_session_selector(sessions_with_flags)
        
        # Store selected session for tracking tab
        if selected_session:
            st.session_state.selected_audit_session = selected_session
        
        if selected_session:
            # Get flagged records for selected session
            flagged_records = self.audit_manager.get_flagged_records(session_id=selected_session)
            
            if flagged_records:
                # Render filtering and sorting controls
                filtered_records = self._render_filter_controls(flagged_records)
                
                # Render records table
                self._render_flagged_records_table(filtered_records)
                
                # Render detailed view for selected record
                if 'selected_record_id' in st.session_state and st.session_state.selected_record_id:
                    selected_record = next(
                        (r for r in filtered_records if r.record_id == st.session_state.selected_record_id),
                        None
                    )
                    if selected_record:
                        # Check if in edit mode
                        if st.session_state.get('edit_mode', False):
                            # Render record editor
                            record_saved = self.record_editor.render_record_editor(selected_record)
                            if record_saved:
                                # Record was saved, exit edit mode and refresh
                                if 'edit_mode' in st.session_state:
                                    del st.session_state.edit_mode
                                st.rerun()
                        else:
                            # Render normal detail view
                            self._render_record_detail_view(selected_record)
            else:
                st.info("No flagged records found for the selected session.")
                
    def _get_sessions_with_flagged_records(self) -> List[Dict[str, Any]]:
        """
        Get list of sessions that have flagged records.
        
        Returns:
            List[Dict[str, Any]]: Sessions with flagged record counts
        """
        # Get all sessions
        all_sessions = self.session_manager.list_sessions(limit=50)
        sessions_with_flags = []
        
        for session in all_sessions:
            session_id = session['session_id']
            flagged_count = len(self.audit_manager.get_flagged_records(session_id=session_id))
            
            if flagged_count > 0:
                session_info = session.copy()
                session_info['flagged_count'] = flagged_count
                sessions_with_flags.append(session_info)
                
        return sessions_with_flags
        
    def _render_no_flagged_records(self) -> None:
        """Render interface when no flagged records are available."""
        st.info("🎉 No records currently flagged for manual review!")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            ### What this means:
            - All processed records have high confidence scores
            - No validation errors were detected
            - No manual intervention is required
            
            ### Next steps:
            - Process more documents to generate data
            - Check the Results page for completed processing
            - Adjust confidence thresholds if needed
            """)
            
        if st.button("📤 Go to Upload Page", type="primary", use_container_width=True):
            st.session_state.current_page = 'upload'
            st.rerun()
            
    def _render_session_selector(self, sessions: List[Dict[str, Any]]) -> Optional[str]:
        """
        Render session selection interface.
        
        Args:
            sessions: List of sessions with flagged records
            
        Returns:
            Optional[str]: Selected session ID
        """
        st.markdown("### 📋 Select Processing Session")
        
        # Create session options
        session_options = {}
        for session in sessions:
            upload_time = session.get('upload_timestamp', 'Unknown')
            if upload_time != 'Unknown':
                try:
                    upload_dt = datetime.fromisoformat(upload_time.replace('Z', '+00:00'))
                    upload_time = upload_dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
                    
            label = f"{session['file_name']} ({upload_time}) - {session['flagged_count']} flagged"
            session_options[label] = session['session_id']
            
        if session_options:
            selected_label = st.selectbox(
                "Choose a session to review:",
                options=list(session_options.keys()),
                help="Sessions are listed with filename, upload time, and number of flagged records"
            )
            
            return session_options[selected_label] if selected_label else None
            
        return None
        
    def _render_filter_controls(self, records: List[FlaggedRecord]) -> List[FlaggedRecord]:
        """
        Render filtering and sorting controls.
        
        Args:
            records: List of flagged records to filter
            
        Returns:
            List[FlaggedRecord]: Filtered and sorted records
        """
        st.markdown("### 🔍 Filter & Sort Records")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Status filter
            status_options = ['All'] + [status.value for status in ReviewStatus]
            selected_status = st.selectbox(
                "Review Status",
                options=status_options,
                help="Filter by review status"
            )
            
        with col2:
            # Confidence range filter
            confidence_range = st.slider(
                "Confidence Range",
                min_value=0.0,
                max_value=1.0,
                value=(0.0, 1.0),
                step=0.1,
                help="Filter by overall confidence score"
            )
            
        with col3:
            # Flag reason filter
            flag_reasons = list(set(record.flag_reason for record in records))
            flag_reasons.insert(0, 'All')
            selected_reason = st.selectbox(
                "Flag Reason",
                options=flag_reasons,
                help="Filter by flagging reason"
            )
            
        with col4:
            # Sort options
            sort_options = {
                'Flag Date (Newest)': ('flag_timestamp', True),
                'Flag Date (Oldest)': ('flag_timestamp', False),
                'Confidence (Lowest)': ('confidence', False),
                'Confidence (Highest)': ('confidence', True),
                'Status': ('review_status', False)
            }
            
            selected_sort = st.selectbox(
                "Sort By",
                options=list(sort_options.keys()),
                help="Choose sorting criteria"
            )
            
        # Apply filters
        filtered_records = records.copy()
        
        # Status filter
        if selected_status != 'All':
            filtered_records = [r for r in filtered_records if r.review_status.value == selected_status]
            
        # Confidence filter
        min_conf, max_conf = confidence_range
        filtered_records = [
            r for r in filtered_records 
            if min_conf <= r.hmo_record.get_overall_confidence() <= max_conf
        ]
        
        # Flag reason filter
        if selected_reason != 'All':
            filtered_records = [r for r in filtered_records if r.flag_reason == selected_reason]
            
        # Apply sorting
        sort_field, reverse = sort_options[selected_sort]
        
        if sort_field == 'flag_timestamp':
            filtered_records.sort(key=lambda x: x.flag_timestamp, reverse=reverse)
        elif sort_field == 'confidence':
            filtered_records.sort(key=lambda x: x.hmo_record.get_overall_confidence(), reverse=reverse)
        elif sort_field == 'review_status':
            filtered_records.sort(key=lambda x: x.review_status.value, reverse=reverse)
            
        # Show filter results
        st.info(f"Showing {len(filtered_records)} of {len(records)} flagged records")
        
        return filtered_records
        
    def _render_flagged_records_table(self, records: List[FlaggedRecord]) -> None:
        """
        Render table of flagged records with selection capability.
        
        Args:
            records: List of flagged records to display
        """
        if not records:
            st.warning("No records match the current filters.")
            return
            
        st.markdown("### 📊 Flagged Records")
        
        # Prepare data for table
        table_data = []
        for record in records:
            confidence = record.hmo_record.get_overall_confidence()
            
            # Status emoji mapping
            status_emoji = {
                ReviewStatus.PENDING: '⏳',
                ReviewStatus.IN_REVIEW: '👀',
                ReviewStatus.APPROVED: '✅',
                ReviewStatus.REJECTED: '❌',
                ReviewStatus.NEEDS_REVISION: '🔄'
            }
            
            table_data.append({
                'Select': False,
                'Record ID': record.record_id[:8] + '...',
                'Council': record.hmo_record.council or 'N/A',
                'Reference': record.hmo_record.reference or 'N/A',
                'Address': (record.hmo_record.hmo_address[:30] + '...' 
                           if len(record.hmo_record.hmo_address or '') > 30 
                           else record.hmo_record.hmo_address or 'N/A'),
                'Confidence': f"{confidence:.1%}",
                'Status': f"{status_emoji.get(record.review_status, '❓')} {record.review_status.value}",
                'Flag Reason': record.flag_reason,
                'Flagged': record.flag_timestamp.strftime('%Y-%m-%d %H:%M'),
                'Reviewer': record.assigned_reviewer or 'Unassigned'
            })
            
        # Create DataFrame for display
        df = pd.DataFrame(table_data)
        
        # Use data editor for selection
        edited_df = st.data_editor(
            df,
            column_config={
                'Select': st.column_config.CheckboxColumn(
                    'Select',
                    help='Select record for detailed review',
                    default=False
                ),
                'Confidence': st.column_config.ProgressColumn(
                    'Confidence',
                    help='Overall confidence score',
                    min_value=0,
                    max_value=1,
                    format='%.1f%%'
                )
            },
            disabled=['Record ID', 'Council', 'Reference', 'Address', 'Confidence', 
                     'Status', 'Flag Reason', 'Flagged', 'Reviewer'],
            hide_index=True,
            use_container_width=True
        )
        
        # Handle record selection
        selected_rows = edited_df[edited_df['Select'] == True]
        
        if len(selected_rows) > 0:
            # Get the first selected record
            selected_index = selected_rows.index[0]
            selected_record_id = records[selected_index].record_id
            st.session_state.selected_record_id = selected_record_id
            
            st.success(f"Selected record: {selected_record_id[:8]}... for detailed review")
            
        elif len(selected_rows) == 0 and 'selected_record_id' in st.session_state:
            # Clear selection if no rows selected
            del st.session_state.selected_record_id
            
    def _render_record_detail_view(self, record: FlaggedRecord) -> None:
        """
        Render detailed view of selected flagged record.
        
        Args:
            record: Selected flagged record for detailed review
        """
        st.markdown("---")
        st.markdown("### 📝 Record Details")
        
        # Record header
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"**Record ID:** `{record.record_id}`")
            st.markdown(f"**Flag Reason:** {record.flag_reason}")
            
        with col2:
            confidence = record.hmo_record.get_overall_confidence()
            st.metric("Overall Confidence", f"{confidence:.1%}")
            
        with col3:
            status_colors = {
                ReviewStatus.PENDING: '🟡',
                ReviewStatus.IN_REVIEW: '🔵',
                ReviewStatus.APPROVED: '🟢',
                ReviewStatus.REJECTED: '🔴',
                ReviewStatus.NEEDS_REVISION: '🟠'
            }
            
            status_color = status_colors.get(record.review_status, '⚪')
            st.markdown(f"**Status:** {status_color} {record.review_status.value}")
            
        # Record data display
        st.markdown("#### 📋 Extracted Data")
        
        # Create two columns for field display
        col1, col2 = st.columns(2)
        
        fields = record.hmo_record.get_field_names()
        mid_point = len(fields) // 2
        
        with col1:
            for field in fields[:mid_point]:
                self._render_field_display(record.hmo_record, field)
                
        with col2:
            for field in fields[mid_point:]:
                self._render_field_display(record.hmo_record, field)
                
        # Validation errors
        if record.hmo_record.validation_errors:
            st.markdown("#### ⚠️ Validation Issues")
            for error in record.hmo_record.validation_errors:
                st.warning(f"• {error}")
                
        # Audit trail
        if record.audit_trail:
            st.markdown("#### 📜 Audit Trail")
            
            for audit_entry in sorted(record.audit_trail, key=lambda x: x.timestamp, reverse=True):
                with st.expander(f"{audit_entry.action.value} - {audit_entry.timestamp.strftime('%Y-%m-%d %H:%M')}"):
                    st.markdown(f"**Reviewer:** {audit_entry.reviewer}")
                    if audit_entry.comments:
                        st.markdown(f"**Comments:** {audit_entry.comments}")
                    if audit_entry.confidence_before is not None:
                        st.markdown(f"**Confidence Before:** {audit_entry.confidence_before:.1%}")
                    if audit_entry.confidence_after is not None:
                        st.markdown(f"**Confidence After:** {audit_entry.confidence_after:.1%}")
                        
        # Action buttons
        st.markdown("#### 🎯 Actions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("✏️ Edit Record", use_container_width=True):
                st.session_state.edit_mode = True
                st.rerun()
                
        with col2:
            if st.button("✅ Approve", use_container_width=True, type="primary"):
                self._approve_record(record)
                
        with col3:
            if st.button("❌ Reject", use_container_width=True):
                self._reject_record(record)
                
        with col4:
            if st.button("💬 Add Comment", use_container_width=True):
                self._add_comment(record)
                
    def _render_field_display(self, record: HMORecord, field_name: str) -> None:
        """
        Render individual field display with confidence indicator.
        
        Args:
            record: HMO record containing the field
            field_name: Name of the field to display
        """
        value = getattr(record, field_name, '')
        confidence = record.confidence_scores.get(field_name, 0.0)
        
        # Format field name for display
        display_name = field_name.replace('_', ' ').title()
        
        # Confidence color coding
        if confidence >= 0.8:
            confidence_color = '🟢'
        elif confidence >= 0.6:
            confidence_color = '🟡'
        else:
            confidence_color = '🔴'
            
        # Display field with confidence indicator
        st.markdown(f"**{display_name}:** {confidence_color} ({confidence:.1%})")
        
        if value:
            st.text(str(value))
        else:
            st.text("(empty)")
            
        st.markdown("")  # Add spacing
        
    def _approve_record(self, record: FlaggedRecord) -> None:
        """
        Approve a flagged record.
        
        Args:
            record: Record to approve
        """
        # Get approval comments
        comments = st.text_input("Approval comments (optional):", key=f"approve_comments_{record.record_id}")
        
        if st.button("Confirm Approval", key=f"confirm_approve_{record.record_id}"):
            success = self.audit_manager.approve_record(
                record.record_id,
                reviewer="current_user",  # In real implementation, get from auth
                comments=comments
            )
            
            if success:
                st.success("✅ Record approved successfully!")
                # Clear selection and refresh
                if 'selected_record_id' in st.session_state:
                    del st.session_state.selected_record_id
                st.rerun()
            else:
                st.error("❌ Failed to approve record")
                
    def _reject_record(self, record: FlaggedRecord) -> None:
        """
        Reject a flagged record.
        
        Args:
            record: Record to reject
        """
        # Get rejection reason
        reason = st.text_area("Rejection reason (required):", key=f"reject_reason_{record.record_id}")
        
        if reason and st.button("Confirm Rejection", key=f"confirm_reject_{record.record_id}"):
            success = self.audit_manager.reject_record(
                record.record_id,
                reviewer="current_user",  # In real implementation, get from auth
                reason=reason
            )
            
            if success:
                st.success("❌ Record rejected successfully!")
                # Clear selection and refresh
                if 'selected_record_id' in st.session_state:
                    del st.session_state.selected_record_id
                st.rerun()
            else:
                st.error("❌ Failed to reject record")
        elif not reason:
            st.warning("Please provide a rejection reason")
            
    def _add_comment(self, record: FlaggedRecord) -> None:
        """
        Add a comment to a flagged record.
        
        Args:
            record: Record to comment on
        """
        # Get comment text
        comment = st.text_area("Add comment:", key=f"add_comment_{record.record_id}")
        
        if comment and st.button("Add Comment", key=f"confirm_comment_{record.record_id}"):
            success = self.audit_manager.add_comment(
                record.record_id,
                reviewer="current_user",  # In real implementation, get from auth
                comment=comment
            )
            
            if success:
                st.success("💬 Comment added successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to add comment")
        elif not comment:
            st.warning("Please enter a comment")
            
    def get_audit_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get audit statistics for display.
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            Dict[str, Any]: Audit statistics
        """
        return self.audit_manager.get_session_audit_summary(session_id) if session_id else {}