"""
Tests for CSV generation and export system.

Tests CSV formatting, escaping, custom column mapping functionality,
and large dataset processing.
"""
import unittest
import tempfile
import csv
import io
from pathlib import Path
from datetime import datetime, timedelta
import os
import gzip
import zipfile

from models.hmo_record import HMORecord
from models.column_mapping import ColumnMappingConfig, ColumnMapping, DataType
from services.csv_generator import (
    CSVGenerator, CSVExportManager, CSVCompressionManager,
    SecureDownloadManager, BatchCSVProcessor
)
from services.export_manager import (
    ExportManager, ExportJob, ExportStatus, CompressionType,
    ExportConfigurationManager
)


class TestCSVGenerator(unittest.TestCase):
    """Test CSV generator functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.csv_generator = CSVGenerator()
        
        # Create test records
        self.test_records = [
            HMORecord(
                council="Test Council",
                reference="HMO123",
                hmo_address="123 Test Street, Test City, TC1 2AB",
                licence_start="2023-01-01",
                licence_expiry="2024-01-01",
                max_occupancy=5,
                hmo_manager_name="John Smith",
                hmo_manager_address="456 Manager Road, Test City, TC2 3CD",
                licence_holder_name="Jane Doe",
                licence_holder_address="789 Holder Avenue, Test City, TC3 4EF",
                number_of_households=3,
                number_of_shared_kitchens=1,
                number_of_shared_bathrooms=2,
                number_of_shared_toilets=2,
                number_of_storeys=2
            ),
            HMORecord(
                council="Another Council",
                reference="HMO456",
                hmo_address="456 Another Street, Another City, AC1 2XY",
                licence_start="2023-06-01",
                licence_expiry="2024-06-01",
                max_occupancy=8,
                hmo_manager_name="Alice Johnson",
                hmo_manager_address="123 Manager Lane, Another City, AC2 3YZ",
                licence_holder_name="Bob Wilson",
                licence_holder_address="789 Holder Close, Another City, AC3 4ZA",
                number_of_households=5,
                number_of_shared_kitchens=2,
                number_of_shared_bathrooms=3,
                number_of_shared_toilets=3,
                number_of_storeys=3
            )
        ]
    
    def test_generate_csv_string_basic(self):
        """Test basic CSV string generation."""
        csv_content = self.csv_generator.generate_csv_string(self.test_records)
        
        # Check that content is generated
        self.assertIsInstance(csv_content, str)
        self.assertGreater(len(csv_content), 0)
        
        # Parse CSV to verify structure
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        
        # Check number of rows
        self.assertEqual(len(rows), 2)
        
        # Check headers are present
        expected_headers = self.csv_generator.get_column_headers()
        self.assertEqual(list(reader.fieldnames), expected_headers)
        
        # Check first row data
        first_row = rows[0]
        self.assertEqual(first_row['Council'], 'Test Council')
        self.assertEqual(first_row['Reference'], 'HMO123')
        self.assertEqual(first_row['Maximum Occupancy'], '5')
    
    def test_csv_escaping_special_characters(self):
        """Test proper escaping of special characters in CSV."""
        # Create record with special characters
        special_record = HMORecord(
            council='Council with "quotes"',
            reference="REF,with,commas",
            hmo_address="Address with\nnewlines and\ttabs",
            hmo_manager_name="Name with 'apostrophes'",
            licence_holder_name="Name with; semicolons & ampersands"
        )
        
        csv_content = self.csv_generator.generate_csv_string([special_record])
        
        # Parse CSV to ensure proper handling
        reader = csv.DictReader(io.StringIO(csv_content))
        row = next(reader)
        
        # Verify special characters are preserved
        self.assertEqual(row['Council'], 'Council with "quotes"')
        self.assertEqual(row['Reference'], 'REF,with,commas')
        self.assertIn('newlines', row['HMO Address'])
        self.assertIn('tabs', row['HMO Address'])
    
    def test_custom_column_mappings(self):
        """Test CSV generation with custom column mappings."""
        # Create custom column configuration
        custom_config = ColumnMappingConfig()
        custom_config.mappings = {
            'council': ColumnMapping(
                system_field_name='council',
                user_column_name='Local Authority',
                data_type=DataType.STRING
            ),
            'reference': ColumnMapping(
                system_field_name='reference',
                user_column_name='License Number',
                data_type=DataType.STRING
            ),
            'max_occupancy': ColumnMapping(
                system_field_name='max_occupancy',
                user_column_name='Max People',
                data_type=DataType.INTEGER
            )
        }
        
        # Create generator with custom config
        custom_generator = CSVGenerator(custom_config)
        csv_content = custom_generator.generate_csv_string(self.test_records)
        
        # Parse and verify custom headers
        reader = csv.DictReader(io.StringIO(csv_content))
        headers = reader.fieldnames
        
        self.assertIn('Local Authority', headers)
        self.assertIn('License Number', headers)
        self.assertIn('Max People', headers)
        
        # Verify data is correctly mapped
        row = next(reader)
        self.assertEqual(row['Local Authority'], 'Test Council')
        self.assertEqual(row['License Number'], 'HMO123')
        self.assertEqual(row['Max People'], '5')
    
    def test_data_type_formatting(self):
        """Test proper formatting of different data types."""
        # Create record with various data types
        test_record = HMORecord(
            council="Test Council",
            reference="HMO123",
            max_occupancy=5,
            number_of_households=3
        )
        
        # Create config with specific data types
        config = ColumnMappingConfig()
        config.mappings = {
            'council': ColumnMapping(
                system_field_name='council',
                user_column_name='Council',
                data_type=DataType.STRING
            ),
            'max_occupancy': ColumnMapping(
                system_field_name='max_occupancy',
                user_column_name='Max Occupancy',
                data_type=DataType.INTEGER
            )
        }
        
        generator = CSVGenerator(config)
        csv_content = generator.generate_csv_string([test_record])
        
        reader = csv.DictReader(io.StringIO(csv_content))
        row = next(reader)
        
        # Verify integer formatting
        self.assertEqual(row['Max Occupancy'], '5')
        self.assertEqual(row['Council'], 'Test Council')
    
    def test_empty_and_none_values(self):
        """Test handling of empty and None values."""
        # Create record with empty/None values
        empty_record = HMORecord(
            council="Test Council",
            reference="",  # Empty string
            hmo_address=None,  # None value
            max_occupancy=0  # Zero value
        )
        
        csv_content = self.csv_generator.generate_csv_string([empty_record])
        
        reader = csv.DictReader(io.StringIO(csv_content))
        row = next(reader)
        
        # Verify empty values are handled correctly
        self.assertEqual(row['Council'], 'Test Council')
        self.assertEqual(row['Reference'], '')
        self.assertEqual(row['HMO Address'], '')
        self.assertEqual(row['Maximum Occupancy'], '0')
    
    def test_default_values(self):
        """Test application of default values."""
        # Create config with default values
        config = ColumnMappingConfig()
        config.mappings['council'].default_value = "Unknown Council"
        config.mappings['max_occupancy'].default_value = 1
        
        # Create record with empty values
        empty_record = HMORecord(council="", max_occupancy=0)
        
        generator = CSVGenerator(config)
        csv_content = generator.generate_csv_string([empty_record])
        
        reader = csv.DictReader(io.StringIO(csv_content))
        row = next(reader)
        
        # Verify default values are applied
        self.assertEqual(row['Council'], 'Unknown Council')
        self.assertEqual(row['Maximum Occupancy'], '1')


class TestCSVExportManager(unittest.TestCase):
    """Test CSV export manager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.export_manager = CSVExportManager(self.temp_dir)
        
        self.test_records = [
            HMORecord(
                council="Test Council",
                reference="HMO123",
                hmo_address="123 Test Street"
            )
        ]
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_export_to_file(self):
        """Test exporting records to file."""
        file_path = self.export_manager.export_to_file(self.test_records, "test_export")
        
        # Verify file was created
        self.assertIsNotNone(file_path)
        self.assertTrue(file_path.exists())
        self.assertTrue(file_path.name.endswith('.csv'))
        
        # Verify file content
        with open(file_path, 'r') as f:
            content = f.read()
            self.assertIn('Test Council', content)
            self.assertIn('HMO123', content)
    
    def test_export_to_string(self):
        """Test exporting records to string."""
        csv_string = self.export_manager.export_to_string(self.test_records)
        
        self.assertIsNotNone(csv_string)
        self.assertIsInstance(csv_string, str)
        self.assertIn('Test Council', csv_string)
        self.assertIn('HMO123', csv_string)
    
    def test_filename_sanitization(self):
        """Test filename sanitization."""
        # Test with problematic filename
        problematic_name = "test<>file:with|invalid*chars?"
        file_path = self.export_manager.export_to_file(self.test_records, problematic_name)
        
        self.assertIsNotNone(file_path)
        # Verify invalid characters are replaced
        self.assertNotIn('<', file_path.name)
        self.assertNotIn('>', file_path.name)
        self.assertNotIn(':', file_path.name)


class TestCSVCompressionManager(unittest.TestCase):
    """Test CSV compression functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.compression_manager = CSVCompressionManager()
        
        # Create test CSV file
        self.test_csv_path = Path(self.temp_dir) / "test.csv"
        with open(self.test_csv_path, 'w') as f:
            f.write("header1,header2,header3\n")
            f.write("value1,value2,value3\n" * 100)  # Create some content
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_gzip_compression(self):
        """Test gzip compression."""
        compressed_path = self.compression_manager.compress_gzip(self.test_csv_path)
        
        self.assertIsNotNone(compressed_path)
        self.assertTrue(compressed_path.exists())
        self.assertTrue(compressed_path.name.endswith('.csv.gz'))
        
        # Verify compressed file is smaller
        original_size = self.test_csv_path.stat().st_size
        compressed_size = compressed_path.stat().st_size
        self.assertLess(compressed_size, original_size)
        
        # Verify content can be decompressed
        with gzip.open(compressed_path, 'rt') as f:
            content = f.read()
            self.assertIn('header1,header2,header3', content)
    
    def test_zip_compression(self):
        """Test zip compression."""
        compressed_path = self.compression_manager.compress_zip(self.test_csv_path)
        
        self.assertIsNotNone(compressed_path)
        self.assertTrue(compressed_path.exists())
        self.assertTrue(compressed_path.name.endswith('.zip'))
        
        # Verify zip file content
        with zipfile.ZipFile(compressed_path, 'r') as zipf:
            files = zipf.namelist()
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0], self.test_csv_path.name)
            
            # Extract and verify content
            content = zipf.read(files[0]).decode('utf-8')
            self.assertIn('header1,header2,header3', content)
    
    def test_compression_ratio_calculation(self):
        """Test compression ratio calculation."""
        compressed_path = self.compression_manager.compress_gzip(self.test_csv_path)
        
        ratio = self.compression_manager.get_compression_ratio(
            self.test_csv_path, compressed_path
        )
        
        self.assertIsInstance(ratio, float)
        self.assertGreater(ratio, 0.0)
        self.assertLess(ratio, 1.0)  # Should be compressed


class TestSecureDownloadManager(unittest.TestCase):
    """Test secure download manager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.download_manager = SecureDownloadManager("http://test.com")
        
        # Create test file
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.csv"
        with open(self.test_file, 'w') as f:
            f.write("test,content\n1,2\n")
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_download_link(self):
        """Test creating download links."""
        token = self.download_manager.create_download_link(self.test_file)
        
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 20)  # Should be a substantial token
        
        # Verify link info is stored
        link_info = self.download_manager.get_link_info(token)
        self.assertIsNotNone(link_info)
        self.assertEqual(link_info['file_path'], self.test_file)
    
    def test_validate_download_token(self):
        """Test download token validation."""
        token = self.download_manager.create_download_link(self.test_file)
        
        # Test valid token
        is_valid, message, file_path = self.download_manager.validate_download_token(token)
        self.assertTrue(is_valid)
        self.assertEqual(file_path, self.test_file)
        
        # Test invalid token
        is_valid, message, file_path = self.download_manager.validate_download_token("invalid_token")
        self.assertFalse(is_valid)
        self.assertIn("Invalid", message)
    
    def test_download_counting(self):
        """Test download counting and limits."""
        token = self.download_manager.create_download_link(self.test_file, max_downloads=2)
        
        # First download
        self.download_manager.record_download(token)
        is_valid, _, _ = self.download_manager.validate_download_token(token)
        self.assertTrue(is_valid)
        
        # Second download
        self.download_manager.record_download(token)
        is_valid, _, _ = self.download_manager.validate_download_token(token)
        self.assertFalse(is_valid)  # Should exceed limit
    
    def test_link_expiration(self):
        """Test link expiration."""
        # Create link that expires immediately
        token = self.download_manager.create_download_link(self.test_file, expiry_hours=0)
        
        # Should be invalid due to expiration
        is_valid, message, _ = self.download_manager.validate_download_token(token)
        self.assertFalse(is_valid)
        self.assertIn("expired", message.lower())


class TestBatchCSVProcessor(unittest.TestCase):
    """Test batch CSV processor for large datasets."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.batch_processor = BatchCSVProcessor(batch_size=10)
        self.temp_dir = tempfile.mkdtemp()
        
        # Create large dataset
        self.large_dataset = []
        for i in range(25):  # Create 25 records (more than batch size)
            record = HMORecord(
                council=f"Council {i}",
                reference=f"HMO{i:03d}",
                hmo_address=f"{i} Test Street",
                max_occupancy=i % 10 + 1
            )
            self.large_dataset.append(record)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_large_dataset_processing(self):
        """Test processing large datasets in batches."""
        output_path = Path(self.temp_dir) / "large_output.csv"
        
        # Track progress
        progress_calls = []
        def progress_callback(processed, total, percentage):
            progress_calls.append((processed, total, percentage))
        
        success = self.batch_processor.process_large_dataset(
            self.large_dataset, output_path, progress_callback=progress_callback
        )
        
        self.assertTrue(success)
        self.assertTrue(output_path.exists())
        
        # Verify progress was tracked
        self.assertGreater(len(progress_calls), 0)
        final_call = progress_calls[-1]
        self.assertEqual(final_call[0], 25)  # All records processed
        self.assertEqual(final_call[1], 25)  # Total records
        
        # Verify file content
        with open(output_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 25)
    
    def test_memory_usage_estimation(self):
        """Test memory usage estimation."""
        estimates = self.batch_processor.estimate_memory_usage(1000)
        
        self.assertIn('batch_memory_mb', estimates)
        self.assertIn('total_memory_mb', estimates)
        self.assertIn('recommended_batch_size', estimates)
        
        self.assertIsInstance(estimates['batch_memory_mb'], float)
        self.assertGreater(estimates['batch_memory_mb'], 0)


class TestExportManager(unittest.TestCase):
    """Test comprehensive export manager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.export_manager = ExportManager(self.temp_dir)
        
        self.test_records = [
            HMORecord(
                council="Test Council",
                reference="HMO123",
                hmo_address="123 Test Street"
            )
        ]
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_export_job(self):
        """Test creating export jobs."""
        job_id = self.export_manager.create_export_job(
            session_id="test_session",
            records=self.test_records,
            filename="test_export",
            async_processing=False  # Synchronous for testing
        )
        
        self.assertIsInstance(job_id, str)
        
        # Check job status
        status = self.export_manager.get_export_status(job_id)
        self.assertIsNotNone(status)
        self.assertEqual(status['status'], ExportStatus.COMPLETED.value)
        self.assertEqual(status['total_records'], 1)
    
    def test_download_info_generation(self):
        """Test download info generation."""
        job_id = self.export_manager.create_export_job(
            session_id="test_session",
            records=self.test_records,
            filename="test_export",
            async_processing=False
        )
        
        download_info = self.export_manager.get_download_info(job_id)
        self.assertIsNotNone(download_info)
        self.assertIn('download_url', download_info)
        self.assertIn('download_token', download_info)
        self.assertIn('file_size_bytes', download_info)
    
    def test_compression_in_export_job(self):
        """Test compression during export job."""
        job_id = self.export_manager.create_export_job(
            session_id="test_session",
            records=self.test_records,
            filename="test_export",
            compression_type=CompressionType.ZIP,
            async_processing=False
        )
        
        status = self.export_manager.get_export_status(job_id)
        self.assertEqual(status['compression_type'], CompressionType.ZIP.value)
        
        download_info = self.export_manager.get_download_info(job_id)
        self.assertEqual(download_info['compression_type'], CompressionType.ZIP.value)


class TestExportConfigurationManager(unittest.TestCase):
    """Test export configuration management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ExportConfigurationManager(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_load_preset(self):
        """Test saving and loading export presets."""
        # Create test configuration
        column_config = ColumnMappingConfig()
        column_config.load_preset('compact')
        
        # Save preset
        success = self.config_manager.save_export_preset(
            "test_preset", column_config, CompressionType.GZIP
        )
        self.assertTrue(success)
        
        # Load preset
        loaded_config, compression_type = self.config_manager.load_export_preset("test_preset")
        self.assertIsNotNone(loaded_config)
        self.assertEqual(compression_type, CompressionType.GZIP)
        
        # Verify configuration matches
        original_mappings = column_config.get_all_mappings()
        loaded_mappings = loaded_config.get_all_mappings()
        self.assertEqual(len(original_mappings), len(loaded_mappings))
    
    def test_list_presets(self):
        """Test listing available presets."""
        # Initially empty
        presets = self.config_manager.list_export_presets()
        self.assertEqual(len(presets), 0)
        
        # Save a preset
        column_config = ColumnMappingConfig()
        self.config_manager.save_export_preset("test_preset", column_config)
        
        # Should now appear in list
        presets = self.config_manager.list_export_presets()
        self.assertIn("test_preset", presets)
    
    def test_delete_preset(self):
        """Test deleting presets."""
        # Save a preset
        column_config = ColumnMappingConfig()
        self.config_manager.save_export_preset("test_preset", column_config)
        
        # Verify it exists
        presets = self.config_manager.list_export_presets()
        self.assertIn("test_preset", presets)
        
        # Delete it
        success = self.config_manager.delete_export_preset("test_preset")
        self.assertTrue(success)
        
        # Verify it's gone
        presets = self.config_manager.list_export_presets()
        self.assertNotIn("test_preset", presets)


if __name__ == '__main__':
    unittest.main()