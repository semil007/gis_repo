"""
Tests for file storage management system.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from services.file_storage import FileStorageManager, SecureFileHandler


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for testing"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def file_storage(temp_storage_dir):
    """Create FileStorageManager instance with temporary directory"""
    storage_root = temp_storage_dir / "storage"
    temp_dir = temp_storage_dir / "temp"
    
    return FileStorageManager(
        storage_root=str(storage_root),
        temp_dir=str(temp_dir),
        max_storage_gb=0.001,  # 1MB for testing
        cleanup_age_hours=1
    )


@pytest.fixture
def sample_pdf_file(temp_storage_dir):
    """Create a sample PDF file for testing"""
    pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
    pdf_file = temp_storage_dir / "sample.pdf"
    
    with open(pdf_file, 'wb') as f:
        f.write(pdf_content)
    
    return pdf_file


@pytest.fixture
def sample_docx_file(temp_storage_dir):
    """Create a sample DOCX file for testing"""
    # DOCX files are ZIP archives, so create a minimal ZIP structure
    docx_content = b'PK\x03\x04\x14\x00\x00\x00\x08\x00'  # ZIP header
    docx_file = temp_storage_dir / "sample.docx"
    
    with open(docx_file, 'wb') as f:
        f.write(docx_content)
    
    return docx_file


@pytest.fixture
def invalid_file(temp_storage_dir):
    """Create an invalid file for testing"""
    invalid_file = temp_storage_dir / "invalid.txt"
    
    with open(invalid_file, 'w') as f:
        f.write("This is not a valid document")
    
    return invalid_file


class TestFileStorageManager:
    """Test FileStorageManager class"""
    
    def test_initialization(self, file_storage):
        """Test FileStorageManager initialization"""
        assert file_storage.storage_root.exists()
        assert file_storage.temp_dir.exists()
        assert (file_storage.storage_root / "uploads").exists()
        assert (file_storage.storage_root / "processed").exists()
        assert (file_storage.storage_root / "exports").exists()
    
    def test_validate_pdf_file(self, file_storage, sample_pdf_file):
        """Test validating a valid PDF file"""
        is_valid, message = file_storage.validate_file(sample_pdf_file)
        
        assert is_valid is True
        assert message == "File is valid"
    
    def test_validate_docx_file(self, file_storage, sample_docx_file):
        """Test validating a valid DOCX file"""
        is_valid, message = file_storage.validate_file(sample_docx_file)
        
        assert is_valid is True
        assert message == "File is valid"
    
    def test_validate_invalid_extension(self, file_storage, invalid_file):
        """Test validating file with invalid extension"""
        is_valid, message = file_storage.validate_file(invalid_file)
        
        assert is_valid is False
        assert "not allowed" in message
    
    def test_validate_nonexistent_file(self, file_storage, temp_storage_dir):
        """Test validating non-existent file"""
        nonexistent_file = temp_storage_dir / "nonexistent.pdf"
        is_valid, message = file_storage.validate_file(nonexistent_file)
        
        assert is_valid is False
        assert message == "File does not exist"
    
    def test_validate_empty_file(self, file_storage, temp_storage_dir):
        """Test validating empty file"""
        empty_file = temp_storage_dir / "empty.pdf"
        empty_file.touch()
        
        is_valid, message = file_storage.validate_file(empty_file)
        
        assert is_valid is False
        assert message == "File is empty"
    
    def test_validate_oversized_file(self, file_storage, temp_storage_dir):
        """Test validating oversized file"""
        large_file = temp_storage_dir / "large.pdf"
        
        # Create file larger than MAX_FILE_SIZE
        with open(large_file, 'wb') as f:
            f.write(b'%PDF-1.4\n' + b'x' * (file_storage.MAX_FILE_SIZE + 1))
        
        is_valid, message = file_storage.validate_file(large_file)
        
        assert is_valid is False
        assert "exceeds maximum allowed" in message
    
    def test_store_uploaded_file(self, file_storage, sample_pdf_file):
        """Test storing an uploaded file"""
        success, message, stored_path = file_storage.store_uploaded_file(
            sample_pdf_file,
            "session123",
            "original_file.pdf"
        )
        
        assert success is True
        assert message == "File stored successfully"
        assert stored_path is not None
        assert Path(stored_path).exists()
        assert "session123" in Path(stored_path).name
    
    def test_store_invalid_file(self, file_storage, invalid_file):
        """Test storing an invalid file"""
        success, message, stored_path = file_storage.store_uploaded_file(
            invalid_file,
            "session123",
            "invalid.txt"
        )
        
        assert success is False
        assert "not allowed" in message
        assert stored_path is None
    
    def test_create_temp_file(self, file_storage):
        """Test creating temporary file"""
        temp_path = file_storage.create_temp_file("session123", ".csv")
        
        assert temp_path.exists()
        assert temp_path.suffix == ".csv"
        assert "session123" in temp_path.name
        assert temp_path.parent == file_storage.temp_dir
    
    def test_store_processed_result(self, file_storage):
        """Test storing processed results"""
        test_data = b"col1,col2,col3\nval1,val2,val3\n"
        
        success, message, result_path = file_storage.store_processed_result(
            "session123",
            test_data,
            "results.csv"
        )
        
        assert success is True
        assert message == "Result stored successfully"
        assert result_path is not None
        
        # Verify file content
        with open(result_path, 'rb') as f:
            stored_data = f.read()
        assert stored_data == test_data
    
    def test_create_export_file(self, file_storage):
        """Test creating export file"""
        test_data = "col1,col2,col3\nval1,val2,val3\n"
        
        success, message, export_path = file_storage.create_export_file(
            "session123",
            test_data,
            "export.csv"
        )
        
        assert success is True
        assert message == "Export file created"
        assert export_path is not None
        
        # Verify file content
        with open(export_path, 'r', encoding='utf-8') as f:
            stored_data = f.read()
        assert stored_data == test_data
    
    def test_get_file_info(self, file_storage, sample_pdf_file):
        """Test getting file information"""
        info = file_storage.get_file_info(str(sample_pdf_file))
        
        assert info is not None
        assert info['filename'] == sample_pdf_file.name
        assert info['size'] > 0
        assert info['extension'] == '.pdf'
        assert isinstance(info['created'], datetime)
        assert isinstance(info['modified'], datetime)
        assert info['is_valid'] is True
    
    def test_get_file_info_nonexistent(self, file_storage):
        """Test getting info for non-existent file"""
        info = file_storage.get_file_info("/nonexistent/file.pdf")
        assert info is None
    
    def test_delete_file(self, file_storage):
        """Test deleting a file"""
        # Create a test file
        test_file = file_storage.temp_dir / "test_delete.txt"
        test_file.write_text("test content")
        
        assert test_file.exists()
        
        success = file_storage.delete_file(str(test_file))
        
        assert success is True
        assert not test_file.exists()
    
    def test_delete_nonexistent_file(self, file_storage):
        """Test deleting non-existent file"""
        success = file_storage.delete_file("/nonexistent/file.txt")
        assert success is False
    
    def test_cleanup_old_files(self, file_storage):
        """Test cleaning up old files"""
        # Create old temp files
        old_file1 = file_storage.temp_dir / "old_file1.txt"
        old_file2 = file_storage.temp_dir / "old_file2.txt"
        
        old_file1.write_text("old content 1")
        old_file2.write_text("old content 2")
        
        # Manually set old modification time
        import os
        old_time = (datetime.now() - timedelta(hours=2)).timestamp()
        os.utime(old_file1, (old_time, old_time))
        os.utime(old_file2, (old_time, old_time))
        
        # Create new file that shouldn't be cleaned
        new_file = file_storage.temp_dir / "new_file.txt"
        new_file.write_text("new content")
        
        # Run cleanup (cleanup_age_hours=1 from fixture)
        stats = file_storage.cleanup_old_files()
        
        assert stats['temp_files'] == 2
        assert stats['bytes_freed'] > 0
        assert not old_file1.exists()
        assert not old_file2.exists()
        assert new_file.exists()
    
    def test_get_storage_usage(self, file_storage, sample_pdf_file):
        """Test getting storage usage"""
        initial_usage = file_storage.get_storage_usage()
        
        # Store a file
        file_storage.store_uploaded_file(sample_pdf_file, "session123", "test.pdf")
        
        new_usage = file_storage.get_storage_usage()
        
        assert new_usage > initial_usage
    
    def test_get_storage_stats(self, file_storage, sample_pdf_file):
        """Test getting storage statistics"""
        # Store some files
        file_storage.store_uploaded_file(sample_pdf_file, "session123", "test.pdf")
        file_storage.create_temp_file("session123", ".tmp")
        
        stats = file_storage.get_storage_stats()
        
        assert 'total_usage_bytes' in stats
        assert 'max_storage_bytes' in stats
        assert 'usage_percentage' in stats
        assert 'directories' in stats
        
        assert 'uploads' in stats['directories']
        assert 'temp' in stats['directories']
        assert stats['directories']['uploads']['file_count'] >= 1
        assert stats['directories']['temp']['file_count'] >= 1
    
    def test_temp_file_context(self, file_storage):
        """Test temporary file context manager"""
        temp_path = None
        
        with file_storage.temp_file_context("session123", ".csv") as path:
            temp_path = path
            assert path.exists()
            path.write_text("temporary content")
        
        # File should be deleted after context
        assert not temp_path.exists()
    
    def test_storage_quota_enforcement(self, file_storage, temp_storage_dir):
        """Test storage quota enforcement"""
        # Create a file that would exceed quota (max_storage_gb=0.001 = 1MB)
        large_file = temp_storage_dir / "large.pdf"
        large_content = b'%PDF-1.4\n' + b'x' * (2 * 1024 * 1024)  # 2MB
        
        with open(large_file, 'wb') as f:
            f.write(large_content)
        
        success, message, _ = file_storage.store_uploaded_file(
            large_file,
            "session123",
            "large.pdf"
        )
        
        assert success is False
        assert "quota exceeded" in message.lower()


class TestSecureFileHandler:
    """Test SecureFileHandler utility functions"""
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        dangerous_filename = "../../../etc/passwd"
        sanitized = SecureFileHandler.sanitize_filename(dangerous_filename)
        
        assert sanitized == "passwd"
        assert ".." not in sanitized
        assert "/" not in sanitized
    
    def test_sanitize_filename_with_special_chars(self):
        """Test sanitizing filename with special characters"""
        filename = 'file<>:"|?*_.txt'  # Remove the slash to avoid basename issues
        sanitized = SecureFileHandler.sanitize_filename(filename)
        
        assert sanitized == "file________.txt"
    
    def test_sanitize_long_filename(self):
        """Test sanitizing very long filename"""
        long_name = "a" * 300 + ".txt"
        sanitized = SecureFileHandler.sanitize_filename(long_name)
        
        assert len(sanitized) <= 255
        assert sanitized.endswith(".txt")
    
    def test_is_safe_path(self, temp_storage_dir):
        """Test path safety validation"""
        base_dir = str(temp_storage_dir)
        
        # Safe paths
        safe_path1 = str(temp_storage_dir / "file.txt")
        safe_path2 = str(temp_storage_dir / "subdir" / "file.txt")
        
        assert SecureFileHandler.is_safe_path(safe_path1, base_dir) is True
        assert SecureFileHandler.is_safe_path(safe_path2, base_dir) is True
        
        # Unsafe paths
        unsafe_path1 = str(temp_storage_dir.parent / "file.txt")
        unsafe_path2 = "../../../etc/passwd"
        
        assert SecureFileHandler.is_safe_path(unsafe_path1, base_dir) is False
        assert SecureFileHandler.is_safe_path(unsafe_path2, base_dir) is False
    
    def test_is_safe_path_with_symlinks(self, temp_storage_dir):
        """Test path safety with symbolic links"""
        base_dir = str(temp_storage_dir)
        
        # Create a file outside base directory
        outside_file = temp_storage_dir.parent / "outside.txt"
        outside_file.write_text("outside content")
        
        # Create symlink inside base directory pointing outside
        symlink_path = temp_storage_dir / "symlink.txt"
        try:
            symlink_path.symlink_to(outside_file)
            
            # Should detect this as unsafe
            assert SecureFileHandler.is_safe_path(str(symlink_path), base_dir) is False
        except OSError:
            # Skip test if symlinks not supported (e.g., Windows without admin)
            pytest.skip("Symlinks not supported on this system")


if __name__ == "__main__":
    pytest.main([__file__])