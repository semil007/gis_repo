"""
Configuration interface for column mapping and processing settings.
Allows users to customize output column names and validation rules.
"""

import streamlit as st
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from models.column_mapping import ColumnMapping


@dataclass
class ConfigurationPreset:
    """Predefined configuration preset."""
    name: str
    description: str
    column_mappings: Dict[str, str]
    validation_rules: Dict[str, Any]


class ConfigurationInterface:
    """Main configuration interface for HMO document processing."""
    
    def __init__(self):
        self.default_system_fields = [
            'council', 'reference', 'hmo_address', 'licence_start', 'licence_expiry',
            'max_occupancy', 'hmo_manager_name', 'hmo_manager_address',
            'licence_holder_name', 'licence_holder_address', 'number_of_households',
            'number_of_shared_kitchens', 'number_of_shared_bathrooms',
            'number_of_shared_toilets', 'number_of_storeys'
        ]
        
        self.presets = self._load_configuration_presets()
        self._initialize_session_state()
        
    def _initialize_session_state(self):
        """Initialize session state for configuration."""
        if 'config_column_mappings' not in st.session_state:
            st.session_state.config_column_mappings = self._get_default_mappings()
        if 'config_validation_rules' not in st.session_state:
            st.session_state.config_validation_rules = self._get_default_validation_rules()
        if 'config_preset_selected' not in st.session_state:
            st.session_state.config_preset_selected = 'default'
            
    def render_configuration_interface(self) -> Dict[str, Any]:
        """
        Render the main configuration interface.
        
        Returns:
            Current configuration settings
        """
        st.header("⚙️ Processing Configuration")
        
        # Configuration tabs
        tab1, tab2, tab3 = st.tabs(["📋 Column Mapping", "✅ Validation Rules", "📁 Presets"])
        
        with tab1:
            self._render_column_mapping_tab()
            
        with tab2:
            self._render_validation_rules_tab()
            
        with tab3:
            self._render_presets_tab()
            
        # Configuration summary
        self._render_configuration_summary()
        
        return self._get_current_configuration()
        
    def _render_column_mapping_tab(self):
        """Render column mapping configuration tab."""
        st.markdown("### 📊 Customize Output Column Names")
        st.markdown("Configure how extracted data fields are named in the output CSV file.")
        
        # Column mapping editor
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**System Field**")
        with col2:
            st.markdown("**Output Column Name**")
            
        # Create mapping inputs
        updated_mappings = {}
        
        for system_field in self.default_system_fields:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Display system field with description
                field_description = self._get_field_description(system_field)
                st.markdown(f"**{system_field}**")
                st.caption(field_description)
                
            with col2:
                # Input for custom column name
                current_value = st.session_state.config_column_mappings.get(
                    system_field, 
                    self._format_default_column_name(system_field)
                )
                
                new_value = st.text_input(
                    f"Column name for {system_field}",
                    value=current_value,
                    key=f"mapping_{system_field}",
                    label_visibility="collapsed"
                )
                
                updated_mappings[system_field] = new_value
                
        # Update session state
        st.session_state.config_column_mappings = updated_mappings
        
        # Validation and preview
        self._validate_column_mappings(updated_mappings)
        
    def _render_validation_rules_tab(self):
        """Render validation rules configuration tab."""
        st.markdown("### ✅ Data Validation Settings")
        st.markdown("Configure validation rules and quality thresholds.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Confidence Thresholds")
            
            # Confidence threshold settings
            high_confidence = st.slider(
                "High Confidence Threshold",
                min_value=0.5,
                max_value=1.0,
                value=st.session_state.config_validation_rules.get('high_confidence_threshold', 0.8),
                step=0.05,
                help="Records above this threshold are considered high quality"
            )
            
            medium_confidence = st.slider(
                "Medium Confidence Threshold", 
                min_value=0.3,
                max_value=high_confidence,
                value=st.session_state.config_validation_rules.get('medium_confidence_threshold', 0.6),
                step=0.05,
                help="Records above this threshold require review"
            )
            
            # Flag for manual review threshold
            flag_threshold = st.slider(
                "Flag for Manual Review",
                min_value=0.0,
                max_value=medium_confidence,
                value=st.session_state.config_validation_rules.get('flag_threshold', 0.4),
                step=0.05,
                help="Records below this threshold are flagged for manual review"
            )
            
        with col2:
            st.markdown("#### Field Validation")
            
            # Required fields
            required_fields = st.multiselect(
                "Required Fields",
                options=self.default_system_fields,
                default=st.session_state.config_validation_rules.get('required_fields', [
                    'council', 'reference', 'hmo_address'
                ]),
                help="These fields must have values for a record to be considered valid"
            )
            
            # Date format validation
            strict_date_validation = st.checkbox(
                "Strict Date Validation",
                value=st.session_state.config_validation_rules.get('strict_date_validation', True),
                help="Enforce strict date format validation (YYYY-MM-DD)"
            )
            
            # Address validation
            validate_uk_addresses = st.checkbox(
                "Validate UK Address Format",
                value=st.session_state.config_validation_rules.get('validate_uk_addresses', True),
                help="Validate addresses against UK postal code format"
            )
            
        # Update validation rules in session state
        st.session_state.config_validation_rules.update({
            'high_confidence_threshold': high_confidence,
            'medium_confidence_threshold': medium_confidence,
            'flag_threshold': flag_threshold,
            'required_fields': required_fields,
            'strict_date_validation': strict_date_validation,
            'validate_uk_addresses': validate_uk_addresses
        })
        
        # Validation preview
        self._render_validation_preview()
        
    def _render_presets_tab(self):
        """Render configuration presets tab."""
        st.markdown("### 📁 Configuration Presets")
        st.markdown("Load predefined configurations or save your current settings.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Load Preset")
            
            # Preset selection
            preset_names = list(self.presets.keys())
            selected_preset = st.selectbox(
                "Choose a preset configuration",
                options=preset_names,
                index=preset_names.index(st.session_state.config_preset_selected) 
                      if st.session_state.config_preset_selected in preset_names else 0
            )
            
            # Show preset details
            if selected_preset in self.presets:
                preset = self.presets[selected_preset]
                st.markdown(f"**Description:** {preset.description}")
                
                # Preview preset mappings
                with st.expander("Preview Column Mappings", expanded=False):
                    for system_field, column_name in preset.column_mappings.items():
                        st.text(f"{system_field} → {column_name}")
                        
            # Load preset button
            if st.button("📥 Load Preset", use_container_width=True):
                self._load_preset(selected_preset)
                st.success(f"Loaded preset: {selected_preset}")
                st.rerun()
                
        with col2:
            st.markdown("#### Save Current Configuration")
            
            # Save as new preset
            new_preset_name = st.text_input(
                "Preset Name",
                placeholder="Enter name for new preset"
            )
            
            new_preset_description = st.text_area(
                "Description",
                placeholder="Describe this configuration preset"
            )
            
            if st.button("💾 Save as Preset", use_container_width=True):
                if new_preset_name and new_preset_description:
                    self._save_preset(new_preset_name, new_preset_description)
                    st.success(f"Saved preset: {new_preset_name}")
                else:
                    st.error("Please provide both name and description")
                    
        # Export/Import configuration
        st.markdown("#### Export/Import Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📤 Export Configuration", use_container_width=True):
                config_json = self._export_configuration()
                st.download_button(
                    "Download Configuration",
                    data=config_json,
                    file_name="hmo_processor_config.json",
                    mime="application/json"
                )
                
        with col2:
            uploaded_config = st.file_uploader(
                "Import Configuration",
                type=['json'],
                help="Upload a previously exported configuration file"
            )
            
            if uploaded_config is not None:
                try:
                    config_data = json.load(uploaded_config)
                    self._import_configuration(config_data)
                    st.success("Configuration imported successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to import configuration: {str(e)}")
                    
    def _render_configuration_summary(self):
        """Render configuration summary."""
        st.markdown("### 📋 Configuration Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Mapped Fields",
                len([v for v in st.session_state.config_column_mappings.values() if v.strip()])
            )
            
        with col2:
            st.metric(
                "Required Fields",
                len(st.session_state.config_validation_rules.get('required_fields', []))
            )
            
        with col3:
            flag_threshold = st.session_state.config_validation_rules.get('flag_threshold', 0.4)
            st.metric(
                "Review Threshold",
                f"{flag_threshold:.0%}"
            )
            
        # Show current mappings in expandable section
        with st.expander("Current Column Mappings", expanded=False):
            for system_field, column_name in st.session_state.config_column_mappings.items():
                if column_name.strip():
                    st.text(f"{system_field} → {column_name}")
                    
    def _get_field_description(self, field_name: str) -> str:
        """Get description for a system field."""
        descriptions = {
            'council': 'Local authority or council name',
            'reference': 'HMO license reference number',
            'hmo_address': 'Property address of the HMO',
            'licence_start': 'License start date',
            'licence_expiry': 'License expiry date',
            'max_occupancy': 'Maximum number of occupants',
            'hmo_manager_name': 'Name of HMO manager',
            'hmo_manager_address': 'Address of HMO manager',
            'licence_holder_name': 'Name of license holder',
            'licence_holder_address': 'Address of license holder',
            'number_of_households': 'Number of separate households',
            'number_of_shared_kitchens': 'Number of shared kitchen facilities',
            'number_of_shared_bathrooms': 'Number of shared bathroom facilities',
            'number_of_shared_toilets': 'Number of shared toilet facilities',
            'number_of_storeys': 'Number of floors/storeys in property'
        }
        return descriptions.get(field_name, 'System field')
        
    def _format_default_column_name(self, system_field: str) -> str:
        """Format system field name as default column name."""
        return system_field.replace('_', ' ').title()
        
    def _validate_column_mappings(self, mappings: Dict[str, str]):
        """Validate column mappings for duplicates and empty values."""
        # Check for duplicate column names
        column_names = [name.strip() for name in mappings.values() if name.strip()]
        duplicates = [name for name in set(column_names) if column_names.count(name) > 1]
        
        if duplicates:
            st.error(f"⚠️ Duplicate column names found: {', '.join(duplicates)}")
            
        # Check for empty mappings
        empty_mappings = [field for field, name in mappings.items() if not name.strip()]
        if empty_mappings:
            st.warning(f"⚠️ Empty column names for: {', '.join(empty_mappings)}")
            
        # Show validation status
        if not duplicates and not empty_mappings:
            st.success("✅ Column mappings are valid")
            
    def _render_validation_preview(self):
        """Render validation rules preview."""
        st.markdown("#### Validation Preview")
        
        rules = st.session_state.config_validation_rules
        
        # Create sample data for preview
        sample_confidence_scores = [0.95, 0.75, 0.55, 0.35, 0.15]
        
        preview_data = []
        for i, confidence in enumerate(sample_confidence_scores):
            if confidence >= rules.get('high_confidence_threshold', 0.8):
                status = "✅ High Quality"
                color = "green"
            elif confidence >= rules.get('medium_confidence_threshold', 0.6):
                status = "⚠️ Needs Review"
                color = "orange"
            elif confidence >= rules.get('flag_threshold', 0.4):
                status = "🔍 Manual Review"
                color = "red"
            else:
                status = "❌ Low Quality"
                color = "darkred"
                
            preview_data.append({
                'Record': f'Sample {i+1}',
                'Confidence': f'{confidence:.0%}',
                'Status': status
            })
            
        # Display preview table
        st.table(preview_data)
        
    def _load_configuration_presets(self) -> Dict[str, ConfigurationPreset]:
        """Load predefined configuration presets."""
        presets = {
            'default': ConfigurationPreset(
                name='Default Configuration',
                description='Standard HMO processing configuration with all fields',
                column_mappings=self._get_default_mappings(),
                validation_rules=self._get_default_validation_rules()
            ),
            'minimal': ConfigurationPreset(
                name='Minimal Configuration',
                description='Basic configuration with only essential fields',
                column_mappings={
                    'council': 'Council',
                    'reference': 'Reference',
                    'hmo_address': 'Address',
                    'licence_start': 'Start Date',
                    'licence_expiry': 'Expiry Date'
                },
                validation_rules={
                    'high_confidence_threshold': 0.7,
                    'medium_confidence_threshold': 0.5,
                    'flag_threshold': 0.3,
                    'required_fields': ['council', 'reference', 'hmo_address'],
                    'strict_date_validation': False,
                    'validate_uk_addresses': False
                }
            ),
            'comprehensive': ConfigurationPreset(
                name='Comprehensive Configuration',
                description='Detailed configuration with strict validation',
                column_mappings=self._get_comprehensive_mappings(),
                validation_rules={
                    'high_confidence_threshold': 0.9,
                    'medium_confidence_threshold': 0.7,
                    'flag_threshold': 0.5,
                    'required_fields': ['council', 'reference', 'hmo_address', 'licence_start', 'licence_expiry'],
                    'strict_date_validation': True,
                    'validate_uk_addresses': True
                }
            )
        }
        return presets
        
    def _get_default_mappings(self) -> Dict[str, str]:
        """Get default column mappings."""
        return {
            'council': 'Council',
            'reference': 'Reference',
            'hmo_address': 'HMO Address',
            'licence_start': 'Licence Start',
            'licence_expiry': 'Licence Expiry',
            'max_occupancy': 'Max Occupancy',
            'hmo_manager_name': 'Manager Name',
            'hmo_manager_address': 'Manager Address',
            'licence_holder_name': 'Holder Name',
            'licence_holder_address': 'Holder Address',
            'number_of_households': 'Households',
            'number_of_shared_kitchens': 'Shared Kitchens',
            'number_of_shared_bathrooms': 'Shared Bathrooms',
            'number_of_shared_toilets': 'Shared Toilets',
            'number_of_storeys': 'Storeys'
        }
        
    def _get_comprehensive_mappings(self) -> Dict[str, str]:
        """Get comprehensive column mappings with detailed names."""
        return {
            'council': 'Local Authority',
            'reference': 'HMO License Reference',
            'hmo_address': 'Property Address',
            'licence_start': 'License Start Date',
            'licence_expiry': 'License Expiry Date',
            'max_occupancy': 'Maximum Occupancy',
            'hmo_manager_name': 'HMO Manager Full Name',
            'hmo_manager_address': 'HMO Manager Address',
            'licence_holder_name': 'License Holder Full Name',
            'licence_holder_address': 'License Holder Address',
            'number_of_households': 'Number of Households',
            'number_of_shared_kitchens': 'Shared Kitchen Facilities',
            'number_of_shared_bathrooms': 'Shared Bathroom Facilities',
            'number_of_shared_toilets': 'Shared Toilet Facilities',
            'number_of_storeys': 'Number of Storeys'
        }
        
    def _get_default_validation_rules(self) -> Dict[str, Any]:
        """Get default validation rules."""
        return {
            'high_confidence_threshold': 0.8,
            'medium_confidence_threshold': 0.6,
            'flag_threshold': 0.4,
            'required_fields': ['council', 'reference', 'hmo_address'],
            'strict_date_validation': True,
            'validate_uk_addresses': True
        }
        
    def _load_preset(self, preset_name: str):
        """Load a configuration preset."""
        if preset_name in self.presets:
            preset = self.presets[preset_name]
            st.session_state.config_column_mappings = preset.column_mappings.copy()
            st.session_state.config_validation_rules = preset.validation_rules.copy()
            st.session_state.config_preset_selected = preset_name
            
    def _save_preset(self, name: str, description: str):
        """Save current configuration as a new preset."""
        new_preset = ConfigurationPreset(
            name=name,
            description=description,
            column_mappings=st.session_state.config_column_mappings.copy(),
            validation_rules=st.session_state.config_validation_rules.copy()
        )
        self.presets[name] = new_preset
        
    def _export_configuration(self) -> str:
        """Export current configuration as JSON."""
        config = {
            'column_mappings': st.session_state.config_column_mappings,
            'validation_rules': st.session_state.config_validation_rules,
            'export_timestamp': str(st.session_state.get('export_timestamp', 'unknown'))
        }
        return json.dumps(config, indent=2)
        
    def _import_configuration(self, config_data: Dict):
        """Import configuration from JSON data."""
        if 'column_mappings' in config_data:
            st.session_state.config_column_mappings = config_data['column_mappings']
        if 'validation_rules' in config_data:
            st.session_state.config_validation_rules = config_data['validation_rules']
            
    def _get_current_configuration(self) -> Dict[str, Any]:
        """Get current configuration settings."""
        return {
            'column_mappings': st.session_state.config_column_mappings,
            'validation_rules': st.session_state.config_validation_rules
        }
        
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration settings."""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate column mappings
        mappings = st.session_state.config_column_mappings
        column_names = [name.strip() for name in mappings.values() if name.strip()]
        
        # Check for duplicates
        duplicates = [name for name in set(column_names) if column_names.count(name) > 1]
        if duplicates:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Duplicate column names: {', '.join(duplicates)}")
            
        # Check for empty mappings
        empty_mappings = [field for field, name in mappings.items() if not name.strip()]
        if empty_mappings:
            validation_result['warnings'].append(f"Empty column names for: {', '.join(empty_mappings)}")
            
        # Validate thresholds
        rules = st.session_state.config_validation_rules
        high_threshold = rules.get('high_confidence_threshold', 0.8)
        medium_threshold = rules.get('medium_confidence_threshold', 0.6)
        flag_threshold = rules.get('flag_threshold', 0.4)
        
        if not (flag_threshold <= medium_threshold <= high_threshold):
            validation_result['is_valid'] = False
            validation_result['errors'].append("Confidence thresholds must be in ascending order")
            
        return validation_result