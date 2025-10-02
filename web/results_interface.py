"""
Results and download interface for processed HMO documents.
Provides data preview, quality metrics, and CSV download functionality.
"""

import streamlit as st
import pandas as pd
import io
import csv
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import zipfile
import json


class ResultsInterface:
    """Interface for displaying processing results and managing downloads."""
    
    def __init__(self):
        self.results_data = None
        self.quality_metrics = None
        
    def render_results_interface(self, processing_results: Dict[str, Any]) -> None:
        """
        Render the complete results interface.
        
        Args:
            processing_results: Dictionary containing processing results
        """
        self.results_data = processing_results
        self.quality_metrics = processing_results.get('quality_metrics', {})
        
        st.header("📊 Processing Results")
        
        # Results summary
        self._render_results_summary()
        
        # Results tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Data Preview", 
            "📈 Quality Metrics", 
            "⚠️ Flagged Records", 
            "💾 Download"
        ])
        
        with tab1:
            self._render_data_preview()
            
        with tab2:
            self._render_quality_metrics()
            
        with tab3:
            self._render_flagged_records()
            
        with tab4:
            self._render_download_interface()
            
    def _render_results_summary(self):
        """Render high-level results summary."""
        records = self.results_data.get('records', [])
        total_records = len(records)
        
        if total_records == 0:
            st.warning("⚠️ No records were extracted from the document.")
            return
            
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Records", total_records)
            
        with col2:
            avg_confidence = self.results_data.get('average_confidence', 0)
            st.metric("Average Confidence", f"{avg_confidence:.1%}")
            
        with col3:
            flagged_count = len(self.results_data.get('flagged_records', []))
            st.metric("Flagged Records", flagged_count)
            
        with col4:
            processing_time = self.results_data.get('processing_time', 0)
            st.metric("Processing Time", f"{processing_time:.1f}s")
            
        # Quality indicator
        if avg_confidence >= 0.8:
            st.success("🎉 High quality extraction achieved!")
        elif avg_confidence >= 0.6:
            st.info("✅ Good quality extraction with some records needing review")
        else:
            st.warning("⚠️ Lower quality extraction - manual review recommended")
            
    def _render_data_preview(self):
        """Render data preview with filtering and sorting options."""
        st.markdown("### 📋 Extracted Data Preview")
        
        records = self.results_data.get('records', [])
        if not records:
            st.info("No data to preview")
            return
            
        # Convert to DataFrame for easier handling
        df = pd.DataFrame(records)
        
        # Preview controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Record limit
            max_preview = st.selectbox(
                "Records to show",
                options=[10, 25, 50, 100, len(records)],
                index=0 if len(records) > 10 else len([10, 25, 50, 100, len(records)]) - 1
            )
            
        with col2:
            # Confidence filter
            min_confidence = st.slider(
                "Minimum Confidence",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.1,
                help="Filter records by minimum confidence score"
            )
            
        with col3:
            # Column selection
            available_columns = [col for col in df.columns if not col.startswith('confidence_')]
            selected_columns = st.multiselect(
                "Columns to display",
                options=available_columns,
                default=available_columns[:5] if len(available_columns) > 5 else available_columns
            )
            
        # Apply filters
        filtered_df = self._apply_preview_filters(df, min_confidence, max_preview, selected_columns)
        
        # Display data
        if not filtered_df.empty:
            # Add confidence indicators
            styled_df = self._style_dataframe_with_confidence(filtered_df)
            st.dataframe(styled_df, use_container_width=True, height=400)
            
            # Show filter results
            st.caption(f"Showing {len(filtered_df)} of {len(df)} records")
        else:
            st.info("No records match the current filters")
            
        # Data statistics
        self._render_data_statistics(df)
        
    def _render_quality_metrics(self):
        """Render detailed quality metrics and analysis."""
        st.markdown("### 📈 Quality Analysis")
        
        records = self.results_data.get('records', [])
        if not records:
            st.info("No quality metrics available")
            return
            
        # Confidence distribution
        self._render_confidence_distribution(records)
        
        # Field-level quality
        self._render_field_quality_analysis(records)
        
        # Quality recommendations
        self._render_quality_recommendations(records)
        
    def _render_flagged_records(self):
        """Render flagged records that need manual review."""
        st.markdown("### ⚠️ Records Requiring Manual Review")
        
        flagged_records = self.results_data.get('flagged_records', [])
        
        if not flagged_records:
            st.success("🎉 No records flagged for manual review!")
            return
            
        st.info(f"Found {len(flagged_records)} record(s) that may need manual review")
        
        # Display flagged records with reasons
        for i, record_id in enumerate(flagged_records):
            # Find the actual record data
            record = next((r for r in self.results_data.get('records', []) 
                          if r.get('record_id') == record_id), None)
            
            if record:
                with st.expander(f"Record {i+1}: {record.get('reference', 'Unknown')}", expanded=False):
                    self._render_flagged_record_details(record)
                    
    def _render_download_interface(self):
        """Render download options and file generation."""
        st.markdown("### 💾 Download Results")
        
        records = self.results_data.get('records', [])
        if not records:
            st.info("No data available for download")
            return
            
        # Download options
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📄 CSV Download")
            
            # CSV options
            include_confidence = st.checkbox(
                "Include confidence scores",
                value=False,
                help="Add confidence score columns to the CSV"
            )
            
            include_flagged_only = st.checkbox(
                "Flagged records only",
                value=False,
                help="Download only records flagged for review"
            )
            
            # Generate CSV
            csv_data = self._generate_csv_data(records, include_confidence, include_flagged_only)
            
            if csv_data:
                filename = self._generate_filename('csv')
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv",
                    use_container_width=True
                )
                
                # Show preview
                with st.expander("CSV Preview", expanded=False):
                    st.text(csv_data[:500] + "..." if len(csv_data) > 500 else csv_data)
                    
        with col2:
            st.markdown("#### 📦 Complete Package")
            
            # Package options
            include_original = st.checkbox(
                "Include original file",
                value=True,
                help="Include the original uploaded document"
            )
            
            include_report = st.checkbox(
                "Include quality report",
                value=True,
                help="Include detailed quality analysis report"
            )
            
            # Generate package
            if st.button("📦 Generate Complete Package", use_container_width=True):
                package_data = self._generate_complete_package(
                    records, include_original, include_report
                )
                
                if package_data:
                    filename = self._generate_filename('zip')
                    st.download_button(
                        label="📥 Download Package",
                        data=package_data,
                        file_name=filename,
                        mime="application/zip",
                        use_container_width=True
                    )
                    
        # Download statistics
        self._render_download_statistics()
        
    def _apply_preview_filters(self, df: pd.DataFrame, min_confidence: float, 
                             max_records: int, selected_columns: List[str]) -> pd.DataFrame:
        """Apply filters to the preview DataFrame."""
        filtered_df = df.copy()
        
        # Confidence filter
        if 'confidence_scores' in df.columns and min_confidence > 0:
            # Calculate average confidence for each record
            def get_avg_confidence(confidence_dict):
                if isinstance(confidence_dict, dict) and confidence_dict:
                    return sum(confidence_dict.values()) / len(confidence_dict)
                return 0
                
            filtered_df['avg_confidence'] = df['confidence_scores'].apply(get_avg_confidence)
            filtered_df = filtered_df[filtered_df['avg_confidence'] >= min_confidence]
            
        # Column selection
        if selected_columns:
            # Keep selected columns plus any confidence columns if they exist
            columns_to_keep = selected_columns.copy()
            if 'confidence_scores' in df.columns:
                columns_to_keep.append('confidence_scores')
            if 'avg_confidence' in filtered_df.columns:
                columns_to_keep.append('avg_confidence')
                
            filtered_df = filtered_df[columns_to_keep]
            
        # Limit records
        if max_records < len(filtered_df):
            filtered_df = filtered_df.head(max_records)
            
        return filtered_df
        
    def _style_dataframe_with_confidence(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add confidence styling to DataFrame."""
        # This is a simplified version - in a real implementation,
        # you might use pandas styling for color coding
        styled_df = df.copy()
        
        # Add confidence indicators if confidence data exists
        if 'avg_confidence' in df.columns:
            def confidence_indicator(conf):
                if conf >= 0.8:
                    return f"🟢 {conf:.1%}"
                elif conf >= 0.6:
                    return f"🟡 {conf:.1%}"
                else:
                    return f"🔴 {conf:.1%}"
                    
            styled_df['Confidence'] = df['avg_confidence'].apply(confidence_indicator)
            
        return styled_df
        
    def _render_data_statistics(self, df: pd.DataFrame):
        """Render data statistics summary."""
        st.markdown("#### 📊 Data Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Field completion rates
            st.markdown("**Field Completion:**")
            for column in df.columns:
                if not column.startswith('confidence_'):
                    completion_rate = (df[column].notna() & (df[column] != '')).sum() / len(df)
                    st.metric(column, f"{completion_rate:.1%}")
                    
        with col2:
            # Data types
            st.markdown("**Data Types:**")
            for column in df.columns:
                if not column.startswith('confidence_'):
                    dtype = str(df[column].dtype)
                    st.text(f"{column}: {dtype}")
                    
        with col3:
            # Unique values
            st.markdown("**Unique Values:**")
            for column in df.columns:
                if not column.startswith('confidence_'):
                    unique_count = df[column].nunique()
                    st.metric(column, unique_count)
                    
    def _render_confidence_distribution(self, records: List[Dict]):
        """Render confidence score distribution."""
        st.markdown("#### 🎯 Confidence Distribution")
        
        # Extract confidence scores
        all_confidences = []
        for record in records:
            confidence_scores = record.get('confidence_scores', {})
            if confidence_scores:
                avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
                all_confidences.append(avg_confidence)
                
        if all_confidences:
            # Create confidence bins
            high_conf = sum(1 for c in all_confidences if c >= 0.8)
            medium_conf = sum(1 for c in all_confidences if 0.6 <= c < 0.8)
            low_conf = sum(1 for c in all_confidences if c < 0.6)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("High Confidence (≥80%)", high_conf, 
                         delta=f"{high_conf/len(all_confidences):.1%}")
                         
            with col2:
                st.metric("Medium Confidence (60-80%)", medium_conf,
                         delta=f"{medium_conf/len(all_confidences):.1%}")
                         
            with col3:
                st.metric("Low Confidence (<60%)", low_conf,
                         delta=f"{low_conf/len(all_confidences):.1%}")
                         
    def _render_field_quality_analysis(self, records: List[Dict]):
        """Render field-level quality analysis."""
        st.markdown("#### 🔍 Field Quality Analysis")
        
        # Analyze each field's quality
        field_stats = {}
        
        for record in records:
            confidence_scores = record.get('confidence_scores', {})
            for field, confidence in confidence_scores.items():
                if field not in field_stats:
                    field_stats[field] = []
                field_stats[field].append(confidence)
                
        if field_stats:
            # Display field quality table
            quality_data = []
            for field, confidences in field_stats.items():
                avg_conf = sum(confidences) / len(confidences)
                min_conf = min(confidences)
                max_conf = max(confidences)
                
                quality_data.append({
                    'Field': field,
                    'Avg Confidence': f"{avg_conf:.1%}",
                    'Min Confidence': f"{min_conf:.1%}",
                    'Max Confidence': f"{max_conf:.1%}",
                    'Records': len(confidences)
                })
                
            st.table(quality_data)
            
    def _render_quality_recommendations(self, records: List[Dict]):
        """Render quality improvement recommendations."""
        st.markdown("#### 💡 Quality Recommendations")
        
        recommendations = []
        
        # Analyze common issues
        low_confidence_fields = []
        missing_data_fields = []
        
        for record in records:
            confidence_scores = record.get('confidence_scores', {})
            for field, confidence in confidence_scores.items():
                if confidence < 0.6 and field not in low_confidence_fields:
                    low_confidence_fields.append(field)
                    
            # Check for missing data
            for field, value in record.items():
                if not field.startswith('confidence_') and (not value or value == ''):
                    if field not in missing_data_fields:
                        missing_data_fields.append(field)
                        
        # Generate recommendations
        if low_confidence_fields:
            recommendations.append(
                f"Consider manual review for fields: {', '.join(low_confidence_fields[:3])}"
            )
            
        if missing_data_fields:
            recommendations.append(
                f"High missing data rate for: {', '.join(missing_data_fields[:3])}"
            )
            
        if len(records) < 5:
            recommendations.append(
                "Small dataset detected - results may be less reliable"
            )
            
        # Display recommendations
        for rec in recommendations:
            st.info(f"💡 {rec}")
            
        if not recommendations:
            st.success("✅ No specific quality issues detected")
            
    def _render_flagged_record_details(self, record: Dict):
        """Render details for a flagged record."""
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Extracted Data:**")
            for field, value in record.items():
                if not field.startswith('confidence_') and field != 'record_id':
                    st.text(f"{field}: {value}")
                    
        with col2:
            st.markdown("**Confidence Scores:**")
            confidence_scores = record.get('confidence_scores', {})
            for field, confidence in confidence_scores.items():
                color = "🟢" if confidence >= 0.8 else "🟡" if confidence >= 0.6 else "🔴"
                st.text(f"{field}: {color} {confidence:.1%}")
                
        # Flag reasons
        flag_reasons = record.get('flag_reasons', ['Low confidence score'])
        st.markdown("**Flag Reasons:**")
        for reason in flag_reasons:
            st.warning(f"⚠️ {reason}")
            
    def _generate_csv_data(self, records: List[Dict], include_confidence: bool, 
                          flagged_only: bool) -> str:
        """Generate CSV data for download."""
        if not records:
            return ""
            
        # Filter records if needed
        filtered_records = records
        if flagged_only:
            flagged_ids = self.results_data.get('flagged_records', [])
            filtered_records = [r for r in records if r.get('record_id') in flagged_ids]
            
        if not filtered_records:
            return ""
            
        # Prepare data for CSV
        csv_records = []
        for record in filtered_records:
            csv_record = {}
            
            # Add main data fields
            for field, value in record.items():
                if not field.startswith('confidence_') and field != 'record_id':
                    csv_record[field] = value
                    
            # Add confidence scores if requested
            if include_confidence:
                confidence_scores = record.get('confidence_scores', {})
                for field, confidence in confidence_scores.items():
                    csv_record[f"{field}_confidence"] = f"{confidence:.3f}"
                    
            csv_records.append(csv_record)
            
        # Convert to CSV string
        if csv_records:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=csv_records[0].keys())
            writer.writeheader()
            writer.writerows(csv_records)
            return output.getvalue()
            
        return ""
        
    def _generate_complete_package(self, records: List[Dict], include_original: bool, 
                                 include_report: bool) -> bytes:
        """Generate complete package as ZIP file."""
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add CSV data
            csv_data = self._generate_csv_data(records, True, False)
            if csv_data:
                zip_file.writestr("extracted_data.csv", csv_data)
                
            # Add flagged records CSV
            flagged_csv = self._generate_csv_data(records, True, True)
            if flagged_csv:
                zip_file.writestr("flagged_records.csv", flagged_csv)
                
            # Add quality report
            if include_report:
                report_data = self._generate_quality_report(records)
                zip_file.writestr("quality_report.json", report_data)
                
            # Add processing metadata
            metadata = {
                'processing_timestamp': datetime.now().isoformat(),
                'total_records': len(records),
                'average_confidence': self.results_data.get('average_confidence', 0),
                'processing_time': self.results_data.get('processing_time', 0),
                'flagged_records_count': len(self.results_data.get('flagged_records', []))
            }
            zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))
            
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
        
    def _generate_quality_report(self, records: List[Dict]) -> str:
        """Generate detailed quality report as JSON."""
        report = {
            'summary': {
                'total_records': len(records),
                'average_confidence': self.results_data.get('average_confidence', 0),
                'processing_time': self.results_data.get('processing_time', 0)
            },
            'field_analysis': {},
            'confidence_distribution': {},
            'recommendations': []
        }
        
        # Field analysis
        for record in records:
            confidence_scores = record.get('confidence_scores', {})
            for field, confidence in confidence_scores.items():
                if field not in report['field_analysis']:
                    report['field_analysis'][field] = {
                        'confidences': [],
                        'completion_rate': 0
                    }
                report['field_analysis'][field]['confidences'].append(confidence)
                
        # Calculate field statistics
        for field, data in report['field_analysis'].items():
            confidences = data['confidences']
            data['average_confidence'] = sum(confidences) / len(confidences)
            data['min_confidence'] = min(confidences)
            data['max_confidence'] = max(confidences)
            data['record_count'] = len(confidences)
            
        return json.dumps(report, indent=2)
        
    def _generate_filename(self, file_type: str) -> str:
        """Generate filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = st.session_state.get('session_id', 'unknown')[:8]
        
        if file_type == 'csv':
            return f"hmo_data_{timestamp}_{session_id}.csv"
        elif file_type == 'zip':
            return f"hmo_package_{timestamp}_{session_id}.zip"
        else:
            return f"hmo_export_{timestamp}_{session_id}.{file_type}"
            
    def _render_download_statistics(self):
        """Render download statistics and information."""
        st.markdown("#### 📊 Download Information")
        
        records = self.results_data.get('records', [])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv_size = len(self._generate_csv_data(records, False, False))
            st.metric("CSV Size", f"{csv_size / 1024:.1f} KB")
            
        with col2:
            flagged_count = len(self.results_data.get('flagged_records', []))
            st.metric("Flagged Records", flagged_count)
            
        with col3:
            total_fields = len(records[0]) if records else 0
            st.metric("Total Fields", total_fields)


class ResultsDownloader:
    """Specialized component for handling file downloads."""
    
    @staticmethod
    def create_download_button(data: str, filename: str, mime_type: str, 
                             label: str = "Download") -> None:
        """Create a download button with proper formatting."""
        st.download_button(
            label=label,
            data=data,
            file_name=filename,
            mime=mime_type,
            use_container_width=True
        )
        
    @staticmethod
    def show_download_preview(data: str, max_chars: int = 500) -> None:
        """Show a preview of the download data."""
        preview = data[:max_chars]
        if len(data) > max_chars:
            preview += "..."
            
        st.code(preview, language="csv")
        st.caption(f"Preview showing first {min(len(data), max_chars)} characters of {len(data)} total")