"""
CSV generation and export system for HMO processing pipeline.

Provides CSV generation with proper escaping, custom column mappings,
and batch processing for large datasets.
"""
import csv
import io
from typing import List, Dict, Any, Optional, Iterator, Union
from pathlib import Path
import tempfile
import os
from dataclasses import asdict

from models.hmo_record import HMORecord
from models.column_mapping import ColumnMappingConfig, ColumnMapping


class CSVGenerator:
    """
    Generates CSV files from HMO records with configurable column mappings
    and proper escaping for special characters.
    """
    
    def __init__(self, column_config: Optional[ColumnMappingConfig] = None):
        """
        Initialize CSV generator with column configuration.
        
        Args:
            column_config: Column mapping configuration. If None, uses default.
        """
        self.column_config = column_config or ColumnMappingConfig()
        self.batch_size = 1000  # Default batch size for large datasets
        
    def generate_csv_string(self, records: List[HMORecord]) -> str:
        """
        Generate CSV content as string from HMO records.
        
        Args:
            records: List of HMORecord objects to convert
            
        Returns:
            str: CSV content as string
        """
        output = io.StringIO()
        
        # Get column mappings
        mappings = self.column_config.get_all_mappings()
        
        # Create CSV writer with proper escaping
        writer = csv.DictWriter(
            output,
            fieldnames=self.column_config.get_user_column_names(),
            quoting=csv.QUOTE_MINIMAL,
            escapechar='\\',
            lineterminator='\n'
        )
        
        # Write header
        writer.writeheader()
        
        # Write records
        for record in records:
            row_data = self._convert_record_to_row(record, mappings)
            writer.writerow(row_data)
        
        return output.getvalue()
    
    def generate_csv_file(self, records: List[HMORecord], file_path: Union[str, Path]) -> bool:
        """
        Generate CSV file from HMO records.
        
        Args:
            records: List of HMORecord objects to convert
            file_path: Path where to save the CSV file
            
        Returns:
            bool: True if file generated successfully
        """
        try:
            file_path = Path(file_path)
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Get column mappings
            mappings = self.column_config.get_all_mappings()
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(
                    csvfile,
                    fieldnames=self.column_config.get_user_column_names(),
                    quoting=csv.QUOTE_MINIMAL,
                    escapechar='\\',
                    lineterminator='\n'
                )
                
                # Write header
                writer.writeheader()
                
                # Write records in batches for memory efficiency
                for batch in self._batch_records(records, self.batch_size):
                    for record in batch:
                        row_data = self._convert_record_to_row(record, mappings)
                        writer.writerow(row_data)
            
            return True
            
        except Exception as e:
            print(f"Error generating CSV file: {e}")
            return False
    
    def generate_csv_batches(self, records: List[HMORecord]) -> Iterator[str]:
        """
        Generate CSV content in batches for large datasets.
        
        Args:
            records: List of HMORecord objects to convert
            
        Yields:
            str: CSV batch content as string
        """
        mappings = self.column_config.get_all_mappings()
        header_written = False
        
        for batch in self._batch_records(records, self.batch_size):
            output = io.StringIO()
            
            writer = csv.DictWriter(
                output,
                fieldnames=self.column_config.get_user_column_names(),
                quoting=csv.QUOTE_MINIMAL,
                escapechar='\\',
                lineterminator='\n'
            )
            
            # Write header only for first batch
            if not header_written:
                writer.writeheader()
                header_written = True
            
            # Write batch records
            for record in batch:
                row_data = self._convert_record_to_row(record, mappings)
                writer.writerow(row_data)
            
            yield output.getvalue()
    
    def _convert_record_to_row(self, record: HMORecord, mappings: Dict[str, ColumnMapping]) -> Dict[str, str]:
        """
        Convert HMORecord to CSV row data using column mappings.
        
        Args:
            record: HMORecord to convert
            mappings: Column mapping configuration
            
        Returns:
            Dict[str, str]: Row data for CSV writer
        """
        row_data = {}
        record_dict = record.to_dict()
        
        for system_field, mapping in mappings.items():
            # Get value from record
            value = record_dict.get(system_field, "")
            
            # Apply default value if empty and default is configured
            if (not value or (isinstance(value, str) and not value.strip())) and mapping.default_value is not None:
                value = mapping.default_value
            
            # Convert value to string with proper formatting
            formatted_value = self._format_value(value, mapping)
            
            # Use user-defined column name as key
            row_data[mapping.user_column_name] = formatted_value
        
        return row_data
    
    def _format_value(self, value: Any, mapping: ColumnMapping) -> str:
        """
        Format value according to column mapping configuration.
        
        Args:
            value: Value to format
            mapping: Column mapping configuration
            
        Returns:
            str: Formatted value as string
        """
        if value is None:
            return ""
        
        # Handle different data types
        if mapping.data_type.value == "integer":
            if isinstance(value, (int, float)):
                return str(int(value))
            elif isinstance(value, str) and value.strip():
                try:
                    return str(int(float(value)))
                except (ValueError, TypeError):
                    return value.strip()
            else:
                return ""
        
        elif mapping.data_type.value == "float":
            if isinstance(value, (int, float)):
                return str(float(value))
            elif isinstance(value, str) and value.strip():
                try:
                    return str(float(value))
                except (ValueError, TypeError):
                    return value.strip()
            else:
                return ""
        
        elif mapping.data_type.value == "boolean":
            if isinstance(value, bool):
                return "true" if value else "false"
            elif isinstance(value, str):
                return "true" if value.lower() in ('true', '1', 'yes', 'on') else "false"
            else:
                return "false"
        
        else:  # string, date, or other types
            if isinstance(value, str):
                return value.strip()
            else:
                return str(value)
    
    def _batch_records(self, records: List[HMORecord], batch_size: int) -> Iterator[List[HMORecord]]:
        """
        Split records into batches for processing.
        
        Args:
            records: List of records to batch
            batch_size: Size of each batch
            
        Yields:
            List[HMORecord]: Batch of records
        """
        for i in range(0, len(records), batch_size):
            yield records[i:i + batch_size]
    
    def set_batch_size(self, batch_size: int):
        """
        Set batch size for large dataset processing.
        
        Args:
            batch_size: Number of records per batch
        """
        if batch_size > 0:
            self.batch_size = batch_size
    
    def get_column_headers(self) -> List[str]:
        """
        Get list of column headers that will be used in CSV output.
        
        Returns:
            List[str]: Column headers in order
        """
        return self.column_config.get_user_column_names()
    
    def validate_records_for_export(self, records: List[HMORecord]) -> Dict[str, Any]:
        """
        Validate records before CSV export and return validation summary.
        
        Args:
            records: List of records to validate
            
        Returns:
            Dict[str, Any]: Validation summary with statistics
        """
        validation_summary = {
            'total_records': len(records),
            'valid_records': 0,
            'invalid_records': 0,
            'validation_errors': [],
            'field_statistics': {}
        }
        
        mappings = self.column_config.get_all_mappings()
        field_stats = {field: {'empty_count': 0, 'error_count': 0} for field in mappings.keys()}
        
        for i, record in enumerate(records):
            record_valid = True
            record_dict = record.to_dict()
            
            for system_field, mapping in mappings.items():
                value = record_dict.get(system_field, "")
                
                # Check if field is empty
                if not value or (isinstance(value, str) and not value.strip()):
                    field_stats[system_field]['empty_count'] += 1
                    if mapping.is_required:
                        validation_summary['validation_errors'].append(
                            f"Record {i+1}: Required field '{mapping.user_column_name}' is empty"
                        )
                        record_valid = False
                        field_stats[system_field]['error_count'] += 1
                else:
                    # Validate value against mapping rules
                    is_valid, error = mapping.validate_value(value)
                    if not is_valid:
                        validation_summary['validation_errors'].append(
                            f"Record {i+1}: {error}"
                        )
                        record_valid = False
                        field_stats[system_field]['error_count'] += 1
            
            if record_valid:
                validation_summary['valid_records'] += 1
            else:
                validation_summary['invalid_records'] += 1
        
        validation_summary['field_statistics'] = field_stats
        return validation_summary
    
    def generate_validation_report(self, records: List[HMORecord]) -> str:
        """
        Generate a human-readable validation report for records.
        
        Args:
            records: List of records to validate
            
        Returns:
            str: Formatted validation report
        """
        validation_summary = self.validate_records_for_export(records)
        
        report_lines = [
            "CSV Export Validation Report",
            "=" * 30,
            f"Total Records: {validation_summary['total_records']}",
            f"Valid Records: {validation_summary['valid_records']}",
            f"Invalid Records: {validation_summary['invalid_records']}",
            ""
        ]
        
        if validation_summary['validation_errors']:
            report_lines.extend([
                "Validation Errors:",
                "-" * 18
            ])
            for error in validation_summary['validation_errors'][:20]:  # Limit to first 20 errors
                report_lines.append(f"  • {error}")
            
            if len(validation_summary['validation_errors']) > 20:
                report_lines.append(f"  ... and {len(validation_summary['validation_errors']) - 20} more errors")
            
            report_lines.append("")
        
        # Field statistics
        report_lines.extend([
            "Field Statistics:",
            "-" * 17
        ])
        
        mappings = self.column_config.get_all_mappings()
        for system_field, stats in validation_summary['field_statistics'].items():
            mapping = mappings[system_field]
            empty_pct = (stats['empty_count'] / validation_summary['total_records']) * 100
            error_pct = (stats['error_count'] / validation_summary['total_records']) * 100
            
            report_lines.append(
                f"  {mapping.user_column_name}: "
                f"{empty_pct:.1f}% empty, {error_pct:.1f}% errors"
            )
        
        return "\n".join(report_lines)


class CSVExportManager:
    """
    Manages CSV export operations including file generation, compression, and cleanup.
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize export manager.
        
        Args:
            temp_dir: Directory for temporary files. If None, uses system temp.
        """
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir())
        self.csv_generator = CSVGenerator()
        
    def export_to_file(self, records: List[HMORecord], filename: str, 
                      column_config: Optional[ColumnMappingConfig] = None) -> Optional[Path]:
        """
        Export records to CSV file.
        
        Args:
            records: List of HMO records to export
            filename: Name for the output file (without extension)
            column_config: Column mapping configuration
            
        Returns:
            Path: Path to generated file, or None if failed
        """
        try:
            # Update column configuration if provided
            if column_config:
                self.csv_generator.column_config = column_config
            
            # Generate unique filename
            timestamp = int(os.path.getmtime(__file__) if os.path.exists(__file__) else 0)
            safe_filename = self._sanitize_filename(filename)
            file_path = self.temp_dir / f"{safe_filename}_{timestamp}.csv"
            
            # Generate CSV file
            success = self.csv_generator.generate_csv_file(records, file_path)
            
            if success and file_path.exists():
                return file_path
            else:
                return None
                
        except Exception as e:
            print(f"Error exporting to file: {e}")
            return None
    
    def export_to_string(self, records: List[HMORecord], 
                        column_config: Optional[ColumnMappingConfig] = None) -> Optional[str]:
        """
        Export records to CSV string.
        
        Args:
            records: List of HMO records to export
            column_config: Column mapping configuration
            
        Returns:
            str: CSV content as string, or None if failed
        """
        try:
            # Update column configuration if provided
            if column_config:
                self.csv_generator.column_config = column_config
            
            return self.csv_generator.generate_csv_string(records)
            
        except Exception as e:
            print(f"Error exporting to string: {e}")
            return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to remove invalid characters.
        
        Args:
            filename: Original filename
            
        Returns:
            str: Sanitized filename
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        sanitized = filename
        
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove extra spaces and limit length
        sanitized = '_'.join(sanitized.split())
        sanitized = sanitized[:100]  # Limit to 100 characters
        
        return sanitized or 'export'
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        Clean up old temporary CSV files.
        
        Args:
            max_age_hours: Maximum age of files to keep in hours
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for file_path in self.temp_dir.glob("*.csv"):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")


import gzip
import zipfile
from datetime import datetime, timedelta
import hashlib
import secrets


class CSVCompressionManager:
    """
    Handles compression of CSV files for large outputs.
    """
    
    @staticmethod
    def compress_gzip(file_path: Path) -> Optional[Path]:
        """
        Compress CSV file using gzip.
        
        Args:
            file_path: Path to CSV file to compress
            
        Returns:
            Path: Path to compressed file, or None if failed
        """
        try:
            compressed_path = file_path.with_suffix('.csv.gz')
            
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            return compressed_path
            
        except Exception as e:
            print(f"Error compressing file with gzip: {e}")
            return None
    
    @staticmethod
    def compress_zip(file_path: Path, archive_name: Optional[str] = None) -> Optional[Path]:
        """
        Compress CSV file using zip.
        
        Args:
            file_path: Path to CSV file to compress
            archive_name: Name for the file inside the zip archive
            
        Returns:
            Path: Path to zip file, or None if failed
        """
        try:
            zip_path = file_path.with_suffix('.zip')
            archive_name = archive_name or file_path.name
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(file_path, archive_name)
            
            return zip_path
            
        except Exception as e:
            print(f"Error compressing file with zip: {e}")
            return None
    
    @staticmethod
    def get_compression_ratio(original_path: Path, compressed_path: Path) -> float:
        """
        Calculate compression ratio.
        
        Args:
            original_path: Path to original file
            compressed_path: Path to compressed file
            
        Returns:
            float: Compression ratio (compressed_size / original_size)
        """
        try:
            original_size = original_path.stat().st_size
            compressed_size = compressed_path.stat().st_size
            
            if original_size == 0:
                return 1.0
            
            return compressed_size / original_size
            
        except Exception:
            return 1.0


class SecureDownloadManager:
    """
    Manages secure download links with expiration for CSV files.
    """
    
    def __init__(self, base_url: str = "", secret_key: Optional[str] = None):
        """
        Initialize secure download manager.
        
        Args:
            base_url: Base URL for download links
            secret_key: Secret key for generating secure tokens
        """
        self.base_url = base_url.rstrip('/')
        self.secret_key = secret_key or secrets.token_hex(32)
        self.download_links: Dict[str, Dict[str, Any]] = {}
    
    def create_download_link(self, file_path: Path, expiry_hours: int = 24, 
                           max_downloads: int = 10) -> str:
        """
        Create a secure download link for a file.
        
        Args:
            file_path: Path to file to create link for
            expiry_hours: Hours until link expires
            max_downloads: Maximum number of downloads allowed
            
        Returns:
            str: Secure download token
        """
        # Generate secure token
        token = secrets.token_urlsafe(32)
        
        # Calculate expiry time
        expiry_time = datetime.now() + timedelta(hours=expiry_hours)
        
        # Store link information
        self.download_links[token] = {
            'file_path': str(file_path),
            'expiry_time': expiry_time,
            'max_downloads': max_downloads,
            'download_count': 0,
            'created_time': datetime.now(),
            'file_size': file_path.stat().st_size if file_path.exists() else 0
        }
        
        return token
    
    def get_download_url(self, token: str) -> str:
        """
        Get full download URL for a token.
        
        Args:
            token: Download token
            
        Returns:
            str: Full download URL
        """
        return f"{self.base_url}/download/{token}"
    
    def validate_download_token(self, token: str) -> tuple[bool, str, Optional[Path]]:
        """
        Validate a download token and return file path if valid.
        
        Args:
            token: Download token to validate
            
        Returns:
            tuple: (is_valid, error_message, file_path)
        """
        if token not in self.download_links:
            return False, "Invalid download token", None
        
        link_info = self.download_links[token]
        
        # Check if expired
        if datetime.now() > link_info['expiry_time']:
            return False, "Download link has expired", None
        
        # Check download count
        if link_info['download_count'] >= link_info['max_downloads']:
            return False, "Download limit exceeded", None
        
        # Check if file still exists
        file_path = Path(link_info['file_path'])
        if not file_path.exists():
            return False, "File no longer available", None
        
        return True, "", file_path
    
    def record_download(self, token: str) -> bool:
        """
        Record a download for a token.
        
        Args:
            token: Download token
            
        Returns:
            bool: True if recorded successfully
        """
        if token in self.download_links:
            self.download_links[token]['download_count'] += 1
            return True
        return False
    
    def cleanup_expired_links(self):
        """Remove expired download links."""
        current_time = datetime.now()
        expired_tokens = [
            token for token, info in self.download_links.items()
            if current_time > info['expiry_time']
        ]
        
        for token in expired_tokens:
            # Also try to clean up the associated file
            try:
                file_path = Path(self.download_links[token]['file_path'])
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors
            
            del self.download_links[token]
    
    def get_link_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a download link.
        
        Args:
            token: Download token
            
        Returns:
            Dict with link information or None if not found
        """
        if token in self.download_links:
            info = dict(self.download_links[token])
            info['file_path'] = Path(info['file_path'])  # Convert back to Path
            return info
        return None
    
    def list_active_links(self) -> List[Dict[str, Any]]:
        """
        Get list of all active download links.
        
        Returns:
            List of active link information
        """
        current_time = datetime.now()
        active_links = []
        
        for token, info in self.download_links.items():
            if current_time <= info['expiry_time']:
                link_info = dict(info)
                link_info['token'] = token
                link_info['file_path'] = Path(link_info['file_path'])
                active_links.append(link_info)
        
        return active_links


class BatchCSVProcessor:
    """
    Processes large datasets in batches for memory-efficient CSV generation.
    """
    
    def __init__(self, batch_size: int = 1000):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of records to process per batch
        """
        self.batch_size = batch_size
        self.csv_generator = CSVGenerator()
    
    def process_large_dataset(self, records: List[HMORecord], output_path: Path,
                            column_config: Optional[ColumnMappingConfig] = None,
                            progress_callback: Optional[callable] = None) -> bool:
        """
        Process large dataset in batches and write to CSV file.
        
        Args:
            records: List of HMO records to process
            output_path: Path for output CSV file
            column_config: Column mapping configuration
            progress_callback: Optional callback function for progress updates
            
        Returns:
            bool: True if processing completed successfully
        """
        try:
            if column_config:
                self.csv_generator.column_config = column_config
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            total_records = len(records)
            processed_records = 0
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = None
                
                for batch_num, batch in enumerate(self._batch_records(records)):
                    # Initialize writer with first batch (to get headers)
                    if writer is None:
                        mappings = self.csv_generator.column_config.get_all_mappings()
                        writer = csv.DictWriter(
                            csvfile,
                            fieldnames=self.csv_generator.column_config.get_user_column_names(),
                            quoting=csv.QUOTE_MINIMAL,
                            escapechar='\\',
                            lineterminator='\n'
                        )
                        writer.writeheader()
                    
                    # Process batch
                    for record in batch:
                        row_data = self.csv_generator._convert_record_to_row(record, mappings)
                        writer.writerow(row_data)
                        processed_records += 1
                    
                    # Call progress callback if provided
                    if progress_callback:
                        progress_pct = (processed_records / total_records) * 100
                        progress_callback(processed_records, total_records, progress_pct)
            
            return True
            
        except Exception as e:
            print(f"Error processing large dataset: {e}")
            return False
    
    def _batch_records(self, records: List[HMORecord]) -> Iterator[List[HMORecord]]:
        """
        Split records into batches.
        
        Args:
            records: List of records to batch
            
        Yields:
            List[HMORecord]: Batch of records
        """
        for i in range(0, len(records), self.batch_size):
            yield records[i:i + self.batch_size]
    
    def estimate_memory_usage(self, num_records: int) -> Dict[str, float]:
        """
        Estimate memory usage for processing given number of records.
        
        Args:
            num_records: Number of records to estimate for
            
        Returns:
            Dict with memory estimates in MB
        """
        # Rough estimates based on typical HMO record sizes
        avg_record_size_bytes = 1024  # ~1KB per record
        batch_memory_mb = (self.batch_size * avg_record_size_bytes) / (1024 * 1024)
        total_memory_mb = (num_records * avg_record_size_bytes) / (1024 * 1024)
        
        return {
            'batch_memory_mb': batch_memory_mb,
            'total_memory_mb': total_memory_mb,
            'recommended_batch_size': min(self.batch_size, max(100, num_records // 10))
        }