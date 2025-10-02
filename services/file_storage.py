"""
File storage management system for document processing pipeline.
Handles secure file storage, temporary file management, and cleanup policies.
"""

import os
import shutil
import hashlib
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager
from loguru import logger


class FileStorageManager:
    """Manages file storage with security, quotas, and cleanup policies"""
    
    # Allowed file types and their MIME types
    ALLOWED_EXTENSIONS = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword'
    }
    
    # Maximum file size (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024
    
    def __init__(self, 
                 storage_root: str = "file_storage",
                 temp_dir: str = "temp_files",
                 max_storage_gb: float = 10.0,
                 cleanup_age_hours: int = 24):
        
        self.storage_root = Path(storage_root)
        self.temp_dir = Path(temp_dir)
        self.max_storage_bytes = int(max_storage_gb * 1024 * 1024 * 1024)
        self.cleanup_age_hours = cleanup_age_hours
        
        # Create directories
        self.storage_root.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.storage_root / "uploads").mkdir(exist_ok=True)
        (self.storage_root / "processed").mkdir(exist_ok=True)
        (self.storage_root / "exports").mkdir(exist_ok=True)
        
        logger.info(f"Initialized file storage at {self.storage_root}")
    
    def validate_file(self, file_path: Path, check_content: bool = True) -> Tuple[bool, str]:
        """Validate uploaded file for security and format compliance"""
        
        # Check if file exists
        if not file_path.exists():
            return False, "File does not exist"
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            return False, f"File size ({file_size} bytes) exceeds maximum allowed ({self.MAX_FILE_SIZE} bytes)"
        
        if file_size == 0:
            return False, "File is empty"
        
        # Check file extension
        file_ext = file_path.suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            return False, f"File type {file_ext} not allowed. Allowed types: {list(self.ALLOWED_EXTENSIONS.keys())}"
        
        # Check MIME type if requested
        if check_content:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            expected_mime = self.ALLOWED_EXTENSIONS[file_ext]
            
            if mime_type != expected_mime:
                # Additional check by reading file header
                if not self._validate_file_header(file_path, file_ext):
                    return False, f"File content does not match extension {file_ext}"
        
        return True, "File is valid"
    
    def _validate_file_header(self, file_path: Path, extension: str) -> bool:
        """Validate file by checking its header bytes"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)
            
            if extension == '.pdf':
                return header.startswith(b'%PDF-')
            elif extension in ['.docx']:
                # DOCX files are ZIP archives
                return header.startswith(b'PK\x03\x04') or header.startswith(b'PK\x05\x06')
            elif extension == '.doc':
                # DOC files have specific OLE header
                return header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')
            
            return True
        except Exception as e:
            logger.error(f"Error validating file header: {e}")
            return False
    
    def store_uploaded_file(self, source_path: Path, session_id: str, 
                           original_filename: str) -> Tuple[bool, str, Optional[str]]:
        """Store an uploaded file securely"""
        
        # Validate file first
        is_valid, validation_msg = self.validate_file(source_path)
        if not is_valid:
            return False, validation_msg, None
        
        # Check storage quota
        if not self._check_storage_quota(source_path.stat().st_size):
            return False, "Storage quota exceeded", None
        
        try:
            # Generate secure filename
            file_hash = self._calculate_file_hash(source_path)
            file_ext = Path(original_filename).suffix.lower()
            secure_filename = f"{session_id}_{file_hash}{file_ext}"
            
            # Store in uploads directory
            dest_path = self.storage_root / "uploads" / secure_filename
            
            # Copy file
            shutil.copy2(source_path, dest_path)
            
            # Set secure permissions (read-only for group/others)
            os.chmod(dest_path, 0o644)
            
            logger.info(f"Stored uploaded file: {original_filename} -> {secure_filename}")
            return True, "File stored successfully", str(dest_path)
        
        except Exception as e:
            logger.error(f"Error storing uploaded file: {e}")
            return False, f"Storage error: {str(e)}", None
    
    def create_temp_file(self, session_id: str, suffix: str = "") -> Path:
        """Create a temporary file for processing"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_filename = f"{session_id}_{timestamp}{suffix}"
        temp_path = self.temp_dir / temp_filename
        
        # Create empty file
        temp_path.touch()
        os.chmod(temp_path, 0o644)
        
        return temp_path
    
    def store_processed_result(self, session_id: str, data: bytes, 
                              filename: str) -> Tuple[bool, str, Optional[str]]:
        """Store processed results (CSV files, etc.)"""
        try:
            # Generate secure filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            secure_filename = f"{session_id}_{timestamp}_{filename}"
            dest_path = self.storage_root / "processed" / secure_filename
            
            # Write data
            with open(dest_path, 'wb') as f:
                f.write(data)
            
            os.chmod(dest_path, 0o644)
            
            logger.info(f"Stored processed result: {secure_filename}")
            return True, "Result stored successfully", str(dest_path)
        
        except Exception as e:
            logger.error(f"Error storing processed result: {e}")
            return False, f"Storage error: {str(e)}", None
    
    def create_export_file(self, session_id: str, data: str, 
                          filename: str) -> Tuple[bool, str, Optional[str]]:
        """Create export file for download"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_filename = f"{session_id}_{timestamp}_{filename}"
            export_path = self.storage_root / "exports" / export_filename
            
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(data)
            
            os.chmod(export_path, 0o644)
            
            logger.info(f"Created export file: {export_filename}")
            return True, "Export file created", str(export_path)
        
        except Exception as e:
            logger.error(f"Error creating export file: {e}")
            return False, f"Export error: {str(e)}", None
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a stored file"""
        path = Path(file_path)
        
        if not path.exists():
            return None
        
        stat = path.stat()
        
        return {
            'path': str(path),
            'filename': path.name,
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'extension': path.suffix.lower(),
            'is_valid': self.validate_file(path)[0]
        }
    
    def delete_file(self, file_path: str) -> bool:
        """Safely delete a file"""
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                logger.info(f"Deleted file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    def cleanup_old_files(self) -> Dict[str, int]:
        """Clean up old temporary and processed files"""
        cutoff_time = datetime.now() - timedelta(hours=self.cleanup_age_hours)
        cleanup_stats = {
            'temp_files': 0,
            'processed_files': 0,
            'export_files': 0,
            'bytes_freed': 0
        }
        
        # Clean temp files
        for file_path in self.temp_dir.iterdir():
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_time:
                    file_size = file_path.stat().st_size
                    if self.delete_file(str(file_path)):
                        cleanup_stats['temp_files'] += 1
                        cleanup_stats['bytes_freed'] += file_size
        
        # Clean old processed files (keep for longer - 7 days)
        processed_cutoff = datetime.now() - timedelta(days=7)
        processed_dir = self.storage_root / "processed"
        
        for file_path in processed_dir.iterdir():
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < processed_cutoff:
                    file_size = file_path.stat().st_size
                    if self.delete_file(str(file_path)):
                        cleanup_stats['processed_files'] += 1
                        cleanup_stats['bytes_freed'] += file_size
        
        # Clean old export files (keep for 3 days)
        export_cutoff = datetime.now() - timedelta(days=3)
        export_dir = self.storage_root / "exports"
        
        for file_path in export_dir.iterdir():
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < export_cutoff:
                    file_size = file_path.stat().st_size
                    if self.delete_file(str(file_path)):
                        cleanup_stats['export_files'] += 1
                        cleanup_stats['bytes_freed'] += file_size
        
        logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()[:16]  # Use first 16 chars
    
    def _check_storage_quota(self, additional_size: int) -> bool:
        """Check if adding a file would exceed storage quota"""
        current_size = self.get_storage_usage()
        return (current_size + additional_size) <= self.max_storage_bytes
    
    def get_storage_usage(self) -> int:
        """Get current storage usage in bytes"""
        total_size = 0
        
        for directory in [self.storage_root, self.temp_dir]:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        
        return total_size
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics"""
        stats = {
            'total_usage_bytes': 0,
            'max_storage_bytes': self.max_storage_bytes,
            'directories': {}
        }
        
        # Calculate usage by directory
        for dir_name, dir_path in [
            ('uploads', self.storage_root / 'uploads'),
            ('processed', self.storage_root / 'processed'),
            ('exports', self.storage_root / 'exports'),
            ('temp', self.temp_dir)
        ]:
            dir_stats = {
                'file_count': 0,
                'total_size': 0,
                'oldest_file': None,
                'newest_file': None
            }
            
            if dir_path.exists():
                files = list(dir_path.iterdir())
                dir_stats['file_count'] = len([f for f in files if f.is_file()])
                
                for file_path in files:
                    if file_path.is_file():
                        file_size = file_path.stat().st_size
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        dir_stats['total_size'] += file_size
                        
                        if dir_stats['oldest_file'] is None or file_time < dir_stats['oldest_file']:
                            dir_stats['oldest_file'] = file_time
                        
                        if dir_stats['newest_file'] is None or file_time > dir_stats['newest_file']:
                            dir_stats['newest_file'] = file_time
            
            stats['directories'][dir_name] = dir_stats
            stats['total_usage_bytes'] += dir_stats['total_size']
        
        # Calculate usage percentage
        stats['usage_percentage'] = (stats['total_usage_bytes'] / stats['max_storage_bytes']) * 100
        
        return stats
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get basic information about the file storage.
        
        Returns:
            Dict[str, Any]: Storage information
        """
        return {
            'available': True,
            'storage_root': str(self.storage_root),
            'temp_dir': str(self.temp_dir),
            'max_storage_gb': self.max_storage_bytes / (1024 * 1024 * 1024),
            'current_usage_bytes': self.get_storage_usage()
        }
    
    @contextmanager
    def temp_file_context(self, session_id: str, suffix: str = ""):
        """Context manager for temporary files"""
        temp_path = self.create_temp_file(session_id, suffix)
        try:
            yield temp_path
        finally:
            self.delete_file(str(temp_path))


class SecureFileHandler:
    """Additional security utilities for file handling"""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal attacks"""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove or replace dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        return filename
    
    @staticmethod
    def is_safe_path(path: str, base_dir: str) -> bool:
        """Check if path is within base directory (prevent path traversal)"""
        try:
            base_path = Path(base_dir).resolve()
            target_path = Path(path).resolve()
            return str(target_path).startswith(str(base_path))
        except Exception:
            return False