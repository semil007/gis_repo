"""
Record editor for manual correction of flagged HMO records.
Provides field-by-field editing with validation and save functionality.
"""

import streamlit as st
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re
from models.hmo_record import HMORecord
from services.audit_manager import AuditManager, FlaggedRecord
from services.data_validator import DataValidator


class RecordEditor:
    """
    Interactive editor for HMO record fields with validation and correction tracking.
    
    Provides functionality for:
    - Field-by-field editing with appropriate input widgets
    - Real-time validation with visual feedback
    - Save and update functionality with audit trail
    """
    
    def __init__(self, audit_manager: AuditManager):
        """
        Initialize record editor.
        
        Args:
            audit_manager: AuditManager instance for tracking changes
        """
        self.audit_manager = audit_manager
        self.data_validator = DataValidator()
        
    def render_record_editor(self, record: FlaggedRecord) -> bool:
        """
        Render the record editing interface.
        
        Args:
            record: FlaggedRecord to edit
            
        Returns:
            bool: True if record was saved, False otherwise
            
        Requirements: 10.3, 10.4
        """
        st.markdown("### ✏️ Edit Record")
        st.markdown(f"**Record ID:** `{record.record_id}`")
        
        # Initialize editing session state
        if f"editing_{record.record_id}" not in st.session_state:
            st.session_state[f"editing_{record.record_id}"] = self._initialize_edit_data(record.hmo_record)
            
        edit_data = st.session_state[f"editing_{record.record_id}"]
        
        # Create tabs for different field categories
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Basic Info", 
            "🏠 Property Details", 
            "👥 People & Contacts", 
            "🔢 Occupancy & Facilities"
        ])
        
        validation_results = {}
        
        with tab1:
            validation_results.update(self._render_basic_info_fields(edit_data, record))
            
        with tab2:
            validation_results.update(self._render_property_fields(edit_data, record))
            
        with tab3:
            validation_results.update(self._render_people_fields(edit_data, record))
            
        with tab4:
            validation_results.update(self._render_occupancy_fields(edit_data, record))
            
        # Show overall validation summary
        self._render_validation_summary(validation_results)
        
        # Action buttons
        return self._render_action_buttons(record, edit_data, validation_results)
        
    def _initialize_edit_data(self, hmo_record: HMORecord) -> Dict[str, Any]:
        """
        Initialize editing data from HMO record.
        
        Args:
            hmo_record: Original HMO record
            
        Returns:
            Dict[str, Any]: Editable data dictionary
        """
        return {
            'council': hmo_record.council or '',
            'reference': hmo_record.reference or '',
            'hmo_address': hmo_record.hmo_address or '',
            'licence_start': hmo_record.licence_start or '',
            'licence_expiry': hmo_record.licence_expiry or '',
            'max_occupancy': hmo_record.max_occupancy or 0,
            'hmo_manager_name': hmo_record.hmo_manager_name or '',
            'hmo_manager_address': hmo_record.hmo_manager_address or '',
            'licence_holder_name': hmo_record.licence_holder_name or '',
            'licence_holder_address': hmo_record.licence_holder_address or '',
            'number_of_households': hmo_record.number_of_households or 0,
            'number_of_shared_kitchens': hmo_record.number_of_shared_kitchens or 0,
            'number_of_shared_bathrooms': hmo_record.number_of_shared_bathrooms or 0,
            'number_of_shared_toilets': hmo_record.number_of_shared_toilets or 0,
            'number_of_storeys': hmo_record.number_of_storeys or 0
        }
        
    def _render_basic_info_fields(self, edit_data: Dict[str, Any], record: FlaggedRecord) -> Dict[str, Dict[str, Any]]:
        """
        Render basic information fields.
        
        Args:
            edit_data: Editable data dictionary
            record: Original flagged record
            
        Returns:
            Dict[str, Dict[str, Any]]: Validation results for rendered fields
        """
        validation_results = {}
        
        st.markdown("#### Council and Reference Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Council field
            original_confidence = record.hmo_record.confidence_scores.get('council', 0.0)
            
            edit_data['council'] = st.text_input(
                "Council",
                value=edit_data['council'],
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"council_{record.record_id}"
            )
            
            validation_results['council'] = self._validate_field(
                'council', edit_data['council'], record.hmo_record
            )
            self._show_field_validation('council', validation_results['council'])
            
        with col2:
            # Reference field
            original_confidence = record.hmo_record.confidence_scores.get('reference', 0.0)
            
            edit_data['reference'] = st.text_input(
                "License Reference",
                value=edit_data['reference'],
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"reference_{record.record_id}"
            )
            
            validation_results['reference'] = self._validate_field(
                'reference', edit_data['reference'], record.hmo_record
            )
            self._show_field_validation('reference', validation_results['reference'])
            
        return validation_results
        
    def _render_property_fields(self, edit_data: Dict[str, Any], record: FlaggedRecord) -> Dict[str, Dict[str, Any]]:
        """
        Render property-related fields.
        
        Args:
            edit_data: Editable data dictionary
            record: Original flagged record
            
        Returns:
            Dict[str, Dict[str, Any]]: Validation results for rendered fields
        """
        validation_results = {}
        
        st.markdown("#### Property Information")
        
        # HMO Address
        original_confidence = record.hmo_record.confidence_scores.get('hmo_address', 0.0)
        
        edit_data['hmo_address'] = st.text_area(
            "HMO Address",
            value=edit_data['hmo_address'],
            height=100,
            help=f"Original confidence: {original_confidence:.1%}",
            key=f"hmo_address_{record.record_id}"
        )
        
        validation_results['hmo_address'] = self._validate_field(
            'hmo_address', edit_data['hmo_address'], record.hmo_record
        )
        self._show_field_validation('hmo_address', validation_results['hmo_address'])
        
        # License dates
        st.markdown("#### License Dates")
        
        col1, col2 = st.columns(2)
        
        with col1:
            original_confidence = record.hmo_record.confidence_scores.get('licence_start', 0.0)
            
            # Try to parse existing date
            start_date = self._parse_date_string(edit_data['licence_start'])
            
            new_start_date = st.date_input(
                "License Start Date",
                value=start_date,
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"licence_start_{record.record_id}"
            )
            
            edit_data['licence_start'] = new_start_date.strftime('%Y-%m-%d') if new_start_date else ''
            
            validation_results['licence_start'] = self._validate_field(
                'licence_start', edit_data['licence_start'], record.hmo_record
            )
            self._show_field_validation('licence_start', validation_results['licence_start'])
            
        with col2:
            original_confidence = record.hmo_record.confidence_scores.get('licence_expiry', 0.0)
            
            # Try to parse existing date
            expiry_date = self._parse_date_string(edit_data['licence_expiry'])
            
            new_expiry_date = st.date_input(
                "License Expiry Date",
                value=expiry_date,
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"licence_expiry_{record.record_id}"
            )
            
            edit_data['licence_expiry'] = new_expiry_date.strftime('%Y-%m-%d') if new_expiry_date else ''
            
            validation_results['licence_expiry'] = self._validate_field(
                'licence_expiry', edit_data['licence_expiry'], record.hmo_record
            )
            self._show_field_validation('licence_expiry', validation_results['licence_expiry'])
            
        return validation_results
        
    def _render_people_fields(self, edit_data: Dict[str, Any], record: FlaggedRecord) -> Dict[str, Dict[str, Any]]:
        """
        Render people and contact fields.
        
        Args:
            edit_data: Editable data dictionary
            record: Original flagged record
            
        Returns:
            Dict[str, Dict[str, Any]]: Validation results for rendered fields
        """
        validation_results = {}
        
        st.markdown("#### Manager Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Manager name
            original_confidence = record.hmo_record.confidence_scores.get('hmo_manager_name', 0.0)
            
            edit_data['hmo_manager_name'] = st.text_input(
                "Manager Name",
                value=edit_data['hmo_manager_name'],
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"hmo_manager_name_{record.record_id}"
            )
            
            validation_results['hmo_manager_name'] = self._validate_field(
                'hmo_manager_name', edit_data['hmo_manager_name'], record.hmo_record
            )
            self._show_field_validation('hmo_manager_name', validation_results['hmo_manager_name'])
            
        with col2:
            # Manager address
            original_confidence = record.hmo_record.confidence_scores.get('hmo_manager_address', 0.0)
            
            edit_data['hmo_manager_address'] = st.text_area(
                "Manager Address",
                value=edit_data['hmo_manager_address'],
                height=100,
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"hmo_manager_address_{record.record_id}"
            )
            
            validation_results['hmo_manager_address'] = self._validate_field(
                'hmo_manager_address', edit_data['hmo_manager_address'], record.hmo_record
            )
            self._show_field_validation('hmo_manager_address', validation_results['hmo_manager_address'])
            
        st.markdown("#### License Holder Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Holder name
            original_confidence = record.hmo_record.confidence_scores.get('licence_holder_name', 0.0)
            
            edit_data['licence_holder_name'] = st.text_input(
                "License Holder Name",
                value=edit_data['licence_holder_name'],
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"licence_holder_name_{record.record_id}"
            )
            
            validation_results['licence_holder_name'] = self._validate_field(
                'licence_holder_name', edit_data['licence_holder_name'], record.hmo_record
            )
            self._show_field_validation('licence_holder_name', validation_results['licence_holder_name'])
            
        with col2:
            # Holder address
            original_confidence = record.hmo_record.confidence_scores.get('licence_holder_address', 0.0)
            
            edit_data['licence_holder_address'] = st.text_area(
                "License Holder Address",
                value=edit_data['licence_holder_address'],
                height=100,
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"licence_holder_address_{record.record_id}"
            )
            
            validation_results['licence_holder_address'] = self._validate_field(
                'licence_holder_address', edit_data['licence_holder_address'], record.hmo_record
            )
            self._show_field_validation('licence_holder_address', validation_results['licence_holder_address'])
            
        return validation_results
        
    def _render_occupancy_fields(self, edit_data: Dict[str, Any], record: FlaggedRecord) -> Dict[str, Dict[str, Any]]:
        """
        Render occupancy and facility fields.
        
        Args:
            edit_data: Editable data dictionary
            record: Original flagged record
            
        Returns:
            Dict[str, Dict[str, Any]]: Validation results for rendered fields
        """
        validation_results = {}
        
        st.markdown("#### Occupancy Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Max occupancy
            original_confidence = record.hmo_record.confidence_scores.get('max_occupancy', 0.0)
            
            edit_data['max_occupancy'] = st.number_input(
                "Maximum Occupancy",
                min_value=0,
                max_value=100,
                value=int(edit_data['max_occupancy']),
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"max_occupancy_{record.record_id}"
            )
            
            validation_results['max_occupancy'] = self._validate_field(
                'max_occupancy', edit_data['max_occupancy'], record.hmo_record
            )
            self._show_field_validation('max_occupancy', validation_results['max_occupancy'])
            
        with col2:
            # Number of households
            original_confidence = record.hmo_record.confidence_scores.get('number_of_households', 0.0)
            
            edit_data['number_of_households'] = st.number_input(
                "Number of Households",
                min_value=0,
                max_value=50,
                value=int(edit_data['number_of_households']),
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"number_of_households_{record.record_id}"
            )
            
            validation_results['number_of_households'] = self._validate_field(
                'number_of_households', edit_data['number_of_households'], record.hmo_record
            )
            self._show_field_validation('number_of_households', validation_results['number_of_households'])
            
        st.markdown("#### Shared Facilities")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Shared kitchens
            original_confidence = record.hmo_record.confidence_scores.get('number_of_shared_kitchens', 0.0)
            
            edit_data['number_of_shared_kitchens'] = st.number_input(
                "Shared Kitchens",
                min_value=0,
                max_value=20,
                value=int(edit_data['number_of_shared_kitchens']),
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"number_of_shared_kitchens_{record.record_id}"
            )
            
            validation_results['number_of_shared_kitchens'] = self._validate_field(
                'number_of_shared_kitchens', edit_data['number_of_shared_kitchens'], record.hmo_record
            )
            self._show_field_validation('number_of_shared_kitchens', validation_results['number_of_shared_kitchens'])
            
            # Shared bathrooms
            original_confidence = record.hmo_record.confidence_scores.get('number_of_shared_bathrooms', 0.0)
            
            edit_data['number_of_shared_bathrooms'] = st.number_input(
                "Shared Bathrooms",
                min_value=0,
                max_value=20,
                value=int(edit_data['number_of_shared_bathrooms']),
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"number_of_shared_bathrooms_{record.record_id}"
            )
            
            validation_results['number_of_shared_bathrooms'] = self._validate_field(
                'number_of_shared_bathrooms', edit_data['number_of_shared_bathrooms'], record.hmo_record
            )
            self._show_field_validation('number_of_shared_bathrooms', validation_results['number_of_shared_bathrooms'])
            
        with col2:
            # Shared toilets
            original_confidence = record.hmo_record.confidence_scores.get('number_of_shared_toilets', 0.0)
            
            edit_data['number_of_shared_toilets'] = st.number_input(
                "Shared Toilets",
                min_value=0,
                max_value=20,
                value=int(edit_data['number_of_shared_toilets']),
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"number_of_shared_toilets_{record.record_id}"
            )
            
            validation_results['number_of_shared_toilets'] = self._validate_field(
                'number_of_shared_toilets', edit_data['number_of_shared_toilets'], record.hmo_record
            )
            self._show_field_validation('number_of_shared_toilets', validation_results['number_of_shared_toilets'])
            
            # Number of storeys
            original_confidence = record.hmo_record.confidence_scores.get('number_of_storeys', 0.0)
            
            edit_data['number_of_storeys'] = st.number_input(
                "Number of Storeys",
                min_value=0,
                max_value=20,
                value=int(edit_data['number_of_storeys']),
                help=f"Original confidence: {original_confidence:.1%}",
                key=f"number_of_storeys_{record.record_id}"
            )
            
            validation_results['number_of_storeys'] = self._validate_field(
                'number_of_storeys', edit_data['number_of_storeys'], record.hmo_record
            )
            self._show_field_validation('number_of_storeys', validation_results['number_of_storeys'])
            
        return validation_results
        
    def _validate_field(self, field_name: str, value: Any, original_record: HMORecord) -> Dict[str, Any]:
        """
        Validate a single field value.
        
        Args:
            field_name: Name of the field to validate
            value: Value to validate
            original_record: Original HMO record for comparison
            
        Returns:
            Dict[str, Any]: Validation result with confidence and errors
        """
        # Create a temporary record for validation
        temp_record = HMORecord()
        setattr(temp_record, field_name, value)
        
        # Get validation confidence
        if field_name == 'council':
            confidence = temp_record.validate_council()
        elif field_name == 'reference':
            confidence = temp_record.validate_reference()
        elif field_name in ['hmo_address', 'hmo_manager_address', 'licence_holder_address']:
            confidence = temp_record.validate_address(str(value))
        elif field_name in ['licence_start', 'licence_expiry']:
            confidence = temp_record.validate_date(str(value))
        elif field_name in ['hmo_manager_name', 'licence_holder_name']:
            confidence = temp_record.validate_name_field(str(value))
        elif field_name in ['max_occupancy', 'number_of_households', 'number_of_shared_kitchens',
                           'number_of_shared_bathrooms', 'number_of_shared_toilets', 'number_of_storeys']:
            confidence = temp_record.validate_numeric_field(int(value) if value else 0, field_name)
        else:
            confidence = 0.5  # Default confidence
            
        # Check if value changed from original
        original_value = getattr(original_record, field_name, None)
        is_changed = str(value) != str(original_value)
        
        # Determine validation status
        if confidence >= 0.8:
            status = 'excellent'
        elif confidence >= 0.6:
            status = 'good'
        elif confidence >= 0.4:
            status = 'warning'
        else:
            status = 'error'
            
        return {
            'confidence': confidence,
            'status': status,
            'is_changed': is_changed,
            'original_value': original_value,
            'errors': temp_record.validation_errors
        }
        
    def _show_field_validation(self, field_name: str, validation_result: Dict[str, Any]) -> None:
        """
        Show validation feedback for a field.
        
        Args:
            field_name: Name of the field
            validation_result: Validation result dictionary
        """
        confidence = validation_result['confidence']
        status = validation_result['status']
        is_changed = validation_result['is_changed']
        
        # Status indicators
        status_indicators = {
            'excellent': '🟢 Excellent',
            'good': '🟡 Good',
            'warning': '🟠 Warning',
            'error': '🔴 Error'
        }
        
        # Show confidence and status
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if is_changed:
                st.info(f"✏️ Modified - {status_indicators[status]} ({confidence:.1%} confidence)")
            else:
                st.text(f"{status_indicators[status]} ({confidence:.1%} confidence)")
                
        with col2:
            if is_changed:
                st.markdown("**Changed**")
                
        # Show validation errors if any
        if validation_result['errors']:
            for error in validation_result['errors']:
                st.error(f"⚠️ {error}")
                
    def _render_validation_summary(self, validation_results: Dict[str, Dict[str, Any]]) -> None:
        """
        Render overall validation summary.
        
        Args:
            validation_results: Dictionary of validation results for all fields
        """
        if not validation_results:
            return
            
        st.markdown("---")
        st.markdown("### 📊 Validation Summary")
        
        # Calculate summary statistics
        total_fields = len(validation_results)
        changed_fields = sum(1 for result in validation_results.values() if result['is_changed'])
        avg_confidence = sum(result['confidence'] for result in validation_results.values()) / total_fields
        
        # Count by status
        status_counts = {'excellent': 0, 'good': 0, 'warning': 0, 'error': 0}
        for result in validation_results.values():
            status_counts[result['status']] += 1
            
        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Fields Changed", changed_fields, delta=f"of {total_fields}")
            
        with col2:
            st.metric("Avg Confidence", f"{avg_confidence:.1%}")
            
        with col3:
            error_count = status_counts['error'] + status_counts['warning']
            st.metric("Issues", error_count, delta="fields need attention" if error_count > 0 else "all good")
            
        with col4:
            excellent_count = status_counts['excellent']
            st.metric("High Quality", excellent_count, delta=f"of {total_fields}")
            
        # Show status breakdown
        if any(count > 0 for count in status_counts.values()):
            st.markdown("**Field Quality Breakdown:**")
            
            status_labels = {
                'excellent': '🟢 Excellent (≥80%)',
                'good': '🟡 Good (60-79%)',
                'warning': '🟠 Warning (40-59%)',
                'error': '🔴 Error (<40%)'
            }
            
            for status, count in status_counts.items():
                if count > 0:
                    st.text(f"{status_labels[status]}: {count} fields")
                    
    def _render_action_buttons(self, record: FlaggedRecord, edit_data: Dict[str, Any], 
                              validation_results: Dict[str, Dict[str, Any]]) -> bool:
        """
        Render action buttons for saving or canceling edits.
        
        Args:
            record: Original flagged record
            edit_data: Edited data
            validation_results: Validation results for all fields
            
        Returns:
            bool: True if record was saved, False otherwise
        """
        st.markdown("---")
        st.markdown("### 💾 Save Changes")
        
        # Check if any changes were made
        has_changes = any(result['is_changed'] for result in validation_results.values())
        
        # Check for validation errors
        has_errors = any(result['status'] == 'error' for result in validation_results.values())
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            # Save button
            save_disabled = not has_changes or has_errors
            save_help = ""
            
            if not has_changes:
                save_help = "No changes made"
            elif has_errors:
                save_help = "Fix validation errors before saving"
            else:
                save_help = "Save all changes to the record"
                
            if st.button("💾 Save Changes", 
                        disabled=save_disabled, 
                        help=save_help,
                        type="primary" if not save_disabled else "secondary",
                        use_container_width=True):
                return self._save_record_changes(record, edit_data, validation_results)
                
        with col2:
            # Reset button
            if st.button("🔄 Reset to Original", 
                        disabled=not has_changes,
                        help="Discard all changes and reset to original values",
                        use_container_width=True):
                # Clear edit data from session state
                if f"editing_{record.record_id}" in st.session_state:
                    del st.session_state[f"editing_{record.record_id}"]
                st.rerun()
                
        with col3:
            # Cancel button
            if st.button("❌ Cancel Edit", 
                        help="Exit edit mode without saving",
                        use_container_width=True):
                # Clear edit mode and selection
                if f"editing_{record.record_id}" in st.session_state:
                    del st.session_state[f"editing_{record.record_id}"]
                if 'edit_mode' in st.session_state:
                    del st.session_state.edit_mode
                if 'selected_record_id' in st.session_state:
                    del st.session_state.selected_record_id
                st.rerun()
                
        # Show save preview if changes exist
        if has_changes:
            st.markdown("#### 📋 Changes Preview")
            
            changes_made = []
            for field_name, result in validation_results.items():
                if result['is_changed']:
                    original = result['original_value']
                    new_value = edit_data[field_name]
                    changes_made.append({
                        'Field': field_name.replace('_', ' ').title(),
                        'Original': str(original) if original else '(empty)',
                        'New Value': str(new_value) if new_value else '(empty)',
                        'Confidence': f"{result['confidence']:.1%}"
                    })
                    
            if changes_made:
                import pandas as pd
                changes_df = pd.DataFrame(changes_made)
                st.dataframe(changes_df, use_container_width=True, hide_index=True)
                
        return False
        
    def _save_record_changes(self, record: FlaggedRecord, edit_data: Dict[str, Any], 
                           validation_results: Dict[str, Dict[str, Any]]) -> bool:
        """
        Save changes to the record.
        
        Args:
            record: Original flagged record
            edit_data: Edited data
            validation_results: Validation results
            
        Returns:
            bool: True if save was successful
        """
        try:
            # Prepare updates dictionary with only changed fields
            updates = {}
            for field_name, result in validation_results.items():
                if result['is_changed']:
                    updates[field_name] = edit_data[field_name]
                    
            if not updates:
                st.warning("No changes to save")
                return False
                
            # Get save comments
            comments = st.text_area(
                "Save comments (optional):",
                placeholder="Describe the changes made...",
                key=f"save_comments_{record.record_id}"
            )
            
            # Confirm save
            if st.button("Confirm Save", key=f"confirm_save_{record.record_id}"):
                # Update the record through audit manager
                success = self.audit_manager.update_record(
                    record.record_id,
                    updates,
                    reviewer="current_user",  # In real implementation, get from auth
                    comments=comments or f"Updated {len(updates)} fields via manual edit"
                )
                
                if success:
                    st.success(f"✅ Successfully saved {len(updates)} field changes!")
                    
                    # Clear edit session state
                    if f"editing_{record.record_id}" in st.session_state:
                        del st.session_state[f"editing_{record.record_id}"]
                    if 'edit_mode' in st.session_state:
                        del st.session_state.edit_mode
                        
                    # Refresh the page
                    st.rerun()
                    return True
                else:
                    st.error("❌ Failed to save changes")
                    return False
                    
        except Exception as e:
            st.error(f"❌ Error saving changes: {str(e)}")
            return False
            
        return False
        
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string into datetime object.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Optional[datetime]: Parsed datetime or None if parsing fails
        """
        if not date_str:
            return None
            
        # Try different date formats
        date_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        return None