"""
Export management system for CSV file generation and download handling.

Provides comprehensive export management including file generation,
compression, secure downloads, and cleanup operations.
"""
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable
from datetime import datetime, timedelta
import tempfile
import threading
import time
from dataclasses import dataclass
from enum import Enum

from models.hmo_record import HMORecord
from models.column_mapping import ColumnMappingConfig
from services.csv_generator import (
    CSVGenerator, CSVExportManager, CSVCompressionManager, 
    SecureDownloadManager, BatchCSVProcessor
)


class ExportStatus(Enum):
    """Export job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class CompressionType(Enum):
    """Supported compression types."""
    NONE = "none"
    GZIP = "gzip"
    ZIP = "zip"


@dataclass
class ExportJob:
    """
    Represents an export job with all its metadata and status.
    """
    job_id: str
    session_id: str
    filename: str
    status: ExportStatus
    created_time: datetime
    total_records: int
    processed_records: int = 0
    file_path: Optional[Path] = None
    compressed_path: Optional[Path] = None
    download_token: Optional[str] = None
    error_message: Optional[str] = None
    compression_type: CompressionType = CompressionType.NONE
    file_size_bytes: int = 0
    compressed_size_bytes: int = 0
    column_config: Optional[ColumnMappingConfig] = None
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_records == 0:
            return 0.0
        return (self.processed_records / self.total_records) * 100
    
    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio."""
        if self.file_size_bytes == 0 or self.compressed_size_bytes == 0:
            return 1.0
        return self.compressed_size_bytes / self.file_size_bytes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'job_id': self.job_id,
            'session_id': self.session_id,
            'filename': self.filename,
            'status': self.status.value,
            'created_time': self.created_time.isoformat(),
            'total_records': self.total_records,
            'processed_records': self.processed_records,
            'progress_percentage': self.progress_percentage,
            'file_path': str(self.file_path) if self.file_path else None,
            'compressed_path': str(self.compressed_path) if self.compressed_path else None,
            'download_token': self.download_token,
            'error_message': self.error_message,
            'compression_type': self.compression_type.value,
            'file_size_bytes': self.file_size_bytes,
            'compressed_size_bytes': self.compressed_size_bytes,
            'compression_ratio': self.compression_ratio
        }


class ExportManager:
    """
    Comprehensive export management system for CSV file generation and downloads.
    """
    
    def __init__(self, base_export_dir: Optional[str] = None, base_url: str = ""):
        """
        Initialize export manager.
        
        Args:
            base_export_dir: Base directory for export files
            base_url: Base URL for download links
        """
        self.base_export_dir = Path(base_export_dir) if base_export_dir else Path(tempfile.gettempdir()) / "hmo_exports"
        self.base_export_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.csv_export_manager = CSVExportManager(str(self.base_export_dir))
        self.compression_manager = CSVCompressionManager()
        self.download_manager = SecureDownloadManager(base_url)
        self.batch_processor = BatchCSVProcessor()
        
        # Job tracking
        self.export_jobs: Dict[str, ExportJob] = {}
        self.job_lock = threading.Lock()
        
        # Configuration
        self.default_expiry_hours = 24
        self.max_downloads_per_file = 10
        self.cleanup_interval_hours = 6
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def create_export_job(self, session_id: str, records: List[HMORecord], 
                         filename: str, column_config: Optional[ColumnMappingConfig] = None,
                         compression_type: CompressionType = CompressionType.NONE,
                         async_processing: bool = True) -> str:
        """
        Create a new export job.
        
        Args:
            session_id: Session identifier
            records: List of HMO records to export
            filename: Desired filename (without extension)
            column_config: Column mapping configuration
            compression_type: Type of compression to apply
            async_processing: Whether to process asynchronously
            
        Returns:
            str: Job ID for tracking the export
        """
        import uuid
        
        job_id = str(uuid.uuid4())
        
        # Create export job
        export_job = ExportJob(
            job_id=job_id,
            session_id=session_id,
            filename=filename,
            status=ExportStatus.PENDING,
            created_time=datetime.now(),
            total_records=len(records),
            compression_type=compression_type,
            column_config=column_config
        )
        
        with self.job_lock:
            self.export_jobs[job_id] = export_job
        
        # Start processing
        if async_processing:
            thread = threading.Thread(
                target=self._process_export_job,
                args=(job_id, records),
                daemon=True
            )
            thread.start()
        else:
            self._process_export_job(job_id, records)
        
        return job_id
    
    def get_export_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of an export job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dict with job status or None if not found
        """
        with self.job_lock:
            job = self.export_jobs.get(job_id)
            return job.to_dict() if job else None
    
    def get_download_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get download information for a completed export job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dict with download information or None if not available
        """
        with self.job_lock:
            job = self.export_jobs.get(job_id)
            
            if not job or job.status != ExportStatus.COMPLETED or not job.download_token:
                return None
            
            # Get download URL
            download_url = self.download_manager.get_download_url(job.download_token)
            
            # Get file info
            file_path = job.compressed_path or job.file_path
            if not file_path or not file_path.exists():
                return None
            
            return {
                'job_id': job_id,
                'download_url': download_url,
                'download_token': job.download_token,
                'filename': file_path.name,
                'file_size_bytes': file_path.stat().st_size,
                'compression_type': job.compression_type.value,
                'compression_ratio': job.compression_ratio,
                'expires_at': (job.created_time + timedelta(hours=self.default_expiry_hours)).isoformat()
            }
    
    def download_file(self, token: str) -> tuple[bool, str, Optional[Path]]:
        """
        Handle file download request.
        
        Args:
            token: Download token
            
        Returns:
            tuple: (success, message, file_path)
        """
        # Validate token
        is_valid, error_msg, file_path = self.download_manager.validate_download_token(token)
        
        if not is_valid:
            return False, error_msg, None
        
        # Record download
        self.download_manager.record_download(token)
        
        return True, "Download authorized", file_path
    
    def cancel_export_job(self, job_id: str) -> bool:
        """
        Cancel an export job if it's still pending or processing.
        
        Args:
            job_id: Job identifier
            
        Returns:
            bool: True if cancelled successfully
        """
        with self.job_lock:
            job = self.export_jobs.get(job_id)
            
            if not job:
                return False
            
            if job.status in [ExportStatus.PENDING, ExportStatus.PROCESSING]:
                job.status = ExportStatus.FAILED
                job.error_message = "Job cancelled by user"
                return True
            
            return False
    
    def list_session_exports(self, session_id: str) -> List[Dict[str, Any]]:
        """
        List all export jobs for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of export job information
        """
        with self.job_lock:
            session_jobs = [
                job.to_dict() for job in self.export_jobs.values()
                if job.session_id == session_id
            ]
        
        # Sort by creation time (newest first)
        session_jobs.sort(key=lambda x: x['created_time'], reverse=True)
        return session_jobs
    
    def cleanup_expired_exports(self):
        """Clean up expired export jobs and files."""
        current_time = datetime.now()
        expired_job_ids = []
        
        with self.job_lock:
            for job_id, job in self.export_jobs.items():
                # Check if job is expired
                if current_time > job.created_time + timedelta(hours=self.default_expiry_hours):
                    expired_job_ids.append(job_id)
                    
                    # Clean up files
                    try:
                        if job.file_path and job.file_path.exists():
                            job.file_path.unlink()
                        if job.compressed_path and job.compressed_path.exists():
                            job.compressed_path.unlink()
                    except Exception as e:
                        print(f"Error cleaning up files for job {job_id}: {e}")
            
            # Remove expired jobs
            for job_id in expired_job_ids:
                del self.export_jobs[job_id]
        
        # Clean up expired download links
        self.download_manager.cleanup_expired_links()
        
        print(f"Cleaned up {len(expired_job_ids)} expired export jobs")
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get storage usage statistics.
        
        Returns:
            Dict with storage statistics
        """
        total_size = 0
        file_count = 0
        
        try:
            for file_path in self.base_export_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
        except Exception as e:
            print(f"Error calculating storage statistics: {e}")
        
        return {
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'file_count': file_count,
            'active_jobs': len(self.export_jobs),
            'base_directory': str(self.base_export_dir)
        }
    
    def _process_export_job(self, job_id: str, records: List[HMORecord]):
        """
        Process an export job (internal method).
        
        Args:
            job_id: Job identifier
            records: List of records to export
        """
        try:
            with self.job_lock:
                job = self.export_jobs.get(job_id)
                if not job:
                    return
                job.status = ExportStatus.PROCESSING
            
            # Progress callback
            def progress_callback(processed: int, total: int, percentage: float):
                with self.job_lock:
                    if job_id in self.export_jobs:
                        self.export_jobs[job_id].processed_records = processed
            
            # Generate CSV file
            if job.column_config:
                self.csv_export_manager.csv_generator.column_config = job.column_config
            
            # Use batch processing for large datasets
            if len(records) > 5000:
                output_path = self.base_export_dir / f"{job.filename}_{job_id}.csv"
                success = self.batch_processor.process_large_dataset(
                    records, output_path, job.column_config, progress_callback
                )
                file_path = output_path if success else None
            else:
                file_path = self.csv_export_manager.export_to_file(
                    records, f"{job.filename}_{job_id}", job.column_config
                )
            
            if not file_path or not file_path.exists():
                raise Exception("Failed to generate CSV file")
            
            # Update job with file info
            with self.job_lock:
                job.file_path = file_path
                job.file_size_bytes = file_path.stat().st_size
                job.processed_records = len(records)
            
            # Apply compression if requested
            compressed_path = None
            if job.compression_type == CompressionType.GZIP:
                compressed_path = self.compression_manager.compress_gzip(file_path)
            elif job.compression_type == CompressionType.ZIP:
                compressed_path = self.compression_manager.compress_zip(
                    file_path, f"{job.filename}.csv"
                )
            
            if compressed_path and compressed_path.exists():
                with self.job_lock:
                    job.compressed_path = compressed_path
                    job.compressed_size_bytes = compressed_path.stat().st_size
            
            # Create download link
            download_file = compressed_path or file_path
            download_token = self.download_manager.create_download_link(
                download_file, self.default_expiry_hours, self.max_downloads_per_file
            )
            
            # Mark job as completed
            with self.job_lock:
                job.download_token = download_token
                job.status = ExportStatus.COMPLETED
            
        except Exception as e:
            # Mark job as failed
            with self.job_lock:
                if job_id in self.export_jobs:
                    self.export_jobs[job_id].status = ExportStatus.FAILED
                    self.export_jobs[job_id].error_message = str(e)
            
            print(f"Export job {job_id} failed: {e}")
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread."""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(self.cleanup_interval_hours * 3600)  # Convert hours to seconds
                    self.cleanup_expired_exports()
                except Exception as e:
                    print(f"Error in cleanup thread: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()


class ExportConfigurationManager:
    """
    Manages export configurations and presets.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory for configuration files
        """
        self.config_dir = Path(config_dir) if config_dir else Path.home() / ".hmo_processor" / "export_configs"
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def save_export_preset(self, name: str, column_config: ColumnMappingConfig, 
                          compression_type: CompressionType = CompressionType.NONE) -> bool:
        """
        Save an export configuration preset.
        
        Args:
            name: Preset name
            column_config: Column mapping configuration
            compression_type: Default compression type
            
        Returns:
            bool: True if saved successfully
        """
        try:
            preset_data = {
                'name': name,
                'column_config': column_config.to_dict(),
                'compression_type': compression_type.value,
                'created_time': datetime.now().isoformat()
            }
            
            preset_file = self.config_dir / f"{name}.json"
            
            import json
            with open(preset_file, 'w') as f:
                json.dump(preset_data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error saving export preset: {e}")
            return False
    
    def load_export_preset(self, name: str) -> Optional[tuple[ColumnMappingConfig, CompressionType]]:
        """
        Load an export configuration preset.
        
        Args:
            name: Preset name
            
        Returns:
            tuple: (column_config, compression_type) or None if not found
        """
        try:
            preset_file = self.config_dir / f"{name}.json"
            
            if not preset_file.exists():
                return None
            
            import json
            with open(preset_file, 'r') as f:
                preset_data = json.load(f)
            
            # Reconstruct column config
            column_config = ColumnMappingConfig()
            column_config.from_dict(preset_data['column_config'])
            
            # Get compression type
            compression_type = CompressionType(preset_data.get('compression_type', 'none'))
            
            return column_config, compression_type
            
        except Exception as e:
            print(f"Error loading export preset: {e}")
            return None
    
    def list_export_presets(self) -> List[str]:
        """
        List available export presets.
        
        Returns:
            List of preset names
        """
        try:
            preset_files = list(self.config_dir.glob("*.json"))
            return [f.stem for f in preset_files]
        except Exception:
            return []
    
    def delete_export_preset(self, name: str) -> bool:
        """
        Delete an export preset.
        
        Args:
            name: Preset name
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            preset_file = self.config_dir / f"{name}.json"
            if preset_file.exists():
                preset_file.unlink()
                return True
            return False
        except Exception:
            return False