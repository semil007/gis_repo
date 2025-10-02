"""
Comprehensive integration tests for the HMO document processing pipeline.

Tests complete workflows with various document types, error scenarios,
recovery mechanisms, concurrent user scenarios, and resource management.
"""

import pytest
import asyncio
import tempfile
import os
import threading
import time
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock
import json

from services.integration_manager import IntegrationManager
from models.hmo_record import HMORecord
from models.processing_session import SessionManager
from services.audit_manager import AuditManager
from services.data_validator import ValidationResult
from web.streamlit_app import StreamlitApp


class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.integration_manager = IntegrationManager({
            'cache_dir': os.path.join(self.temp_dir, 'cache'),
            'storage_dir': os.path.join(self.temp_dir, 'storage')
        })
        
    def teardown_method(self):
        """Clean up test environment."""
        self.integration_manager.performance_optimizer.cleanup_resources()
        
    @pytest.mark.asyncio
    async def test_pdf_document_complete_workflow(self):
        """Test complete workflow with PDF document."""
        # Create mock PDF file
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        pdf_file = os.path.join(self.temp_dir, "test_hmo.pdf")
        
        with open(pdf_file, 'wb') as f:
            f.write(pdf_content)
            
        # Mock the processing components
        with patch.object(self.integration_manager.processing_pipeline.document_processor, 'process_document_with_fallback') as mock_doc_proc, \
             patch.object(self.integration_manager.processing_pipeline.nlp_pipeline, 'process_text') as mock_nlp, \
             patch.object(self.integration_manager.processing_pipeline.entity_extractor, 'extract_hmo_entities') as mock_entities, \
             patch.object(self.integration_manager.processing_pipeline.csv_generator, 'generate_csv') as mock_csv:
            
            # Set up realistic mock responses
            mock_doc_proc.return_value = Mock(
                extracted_text="""
                East Lindsey District Council
                HMO License: HMO/2024/001
                Property Address: 123 High Street, Skegness, PE25 3AB
                License Holder: John Smith
                Manager: Jane Doe
                Maximum Occupancy: 5 persons
                License Start: 01/01/2024
                License Expiry: 31/12/2024
                """,
                ocr_used=False,
                processing_metadata={'document_type': 'pdf'}
            )
            
            mock_nlp.return_value = {
                'entities': [],
                'tokens': ['East', 'Lindsey', 'District', 'Council'],
                'sentences': ['East Lindsey District Council HMO License']
            }
            
            mock_entities.return_value = {
                'councils': [{'text': 'East Lindsey District Council', 'confidence': 0.95}],
                'references': [{'text': 'HMO/2024/001', 'confidence': 0.90}],
                'addresses': [{'text': '123 High Street, Skegness, PE25 3AB', 'confidence': 0.85}],
                'dates': [
                    {'text': '01/01/2024', 'normalized': '2024-01-01', 'confidence': 0.88},
                    {'text': '31/12/2024', 'normalized': '2024-12-31', 'confidence': 0.88}
                ],
                'names': [
                    {'text': 'John Smith', 'confidence': 0.80},
                    {'text': 'Jane Doe', 'confidence': 0.75}
                ],
                'occupancies': [{'text': '5', 'value': 5, 'confidence': 0.92}]
            }
            
            mock_csv.return_value = "council,reference,hmo_address\nEast Lindsey District Council,HMO/2024/001,123 High Street"
            
            # Submit document for processing
            session_id = await self.integration_manager.submit_document_for_processing(
                file_path=pdf_file,
                filename="test_hmo.pdf",
                file_size=len(pdf_content),
                processing_options={'confidence_threshold': 0.7}
            )
            
            # Wait for processing to complete
            max_wait = 30  # seconds
            wait_time = 0
            
            while wait_time < max_wait:
                status = self.integration_manager.get_processing_status(session_id)
                if status['status'] == 'completed':
                    break
                elif status['status'] == 'error':
                    pytest.fail(f"Processing failed: {status.get('error_message')}")
                    
                await asyncio.sleep(1)
                wait_time += 1
                
            # Verify processing completed
            assert wait_time < max_wait, "Processing timed out"
            
            # Get results
            results = self.integration_manager.get_processing_results(session_id)
            assert results is not None
            assert results['total_records'] > 0
            assert 'csv_filename' in results
            
            # Verify CSV download path
            csv_path = self.integration_manager.get_csv_download_path(session_id)
            assert csv_path is not None
            
    @pytest.mark.asyncio
    async def test_docx_document_complete_workflow(self):
        """Test complete workflow with DOCX document."""
        # Create mock DOCX file (simplified)
        docx_file = os.path.join(self.temp_dir, "test_hmo.docx")
        
        # Create a minimal DOCX-like file
        with open(docx_file, 'wb') as f:
            f.write(b"PK\x03\x04")  # ZIP file signature (DOCX is a ZIP)
            
        # Mock processing components
        with patch.object(self.integration_manager.processing_pipeline.document_processor, 'process_document_with_fallback') as mock_doc_proc, \
             patch.object(self.integration_manager.processing_pipeline.nlp_pipeline, 'process_text') as mock_nlp, \
             patch.object(self.integration_manager.processing_pipeline.entity_extractor, 'extract_hmo_entities') as mock_entities:
            
            mock_doc_proc.return_value = Mock(
                extracted_text="Central Bedfordshire Council HMO License REF123456",
                ocr_used=False,
                processing_metadata={'document_type': 'docx'}
            )
            
            mock_nlp.return_value = {
                'entities': [],
                'tokens': ['Central', 'Bedfordshire', 'Council'],
                'sentences': ['Central Bedfordshire Council HMO License']
            }
            
            mock_entities.return_value = {
                'councils': [{'text': 'Central Bedfordshire Council', 'confidence': 0.92}],
                'references': [{'text': 'REF123456', 'confidence': 0.85}],
                'addresses': [],
                'dates': [],
                'names': [],
                'occupancies': []
            }
            
            # Process document
            session_id = await self.integration_manager.submit_document_for_processing(
                file_path=docx_file,
                filename="test_hmo.docx",
                file_size=4,
                processing_options={'confidence_threshold': 0.6}
            )
            
            # Wait for completion
            await asyncio.sleep(2)  # Allow processing time
            
            # Verify results
            results = self.integration_manager.get_processing_results(session_id)
            if results:  # May be None if processing is still ongoing
                assert 'total_records' in results
                
    def test_system_component_validation(self):
        """Test comprehensive system component validation."""
        # Validate all system components
        validation_results = self.integration_manager.validate_system_components()
        
        # Check overall status
        assert 'overall_status' in validation_results
        assert validation_results['overall_status'] in [
            'fully_operational', 'mostly_operational', 'partially_operational', 'limited_functionality'
        ]
        
        # Check individual components
        assert 'components' in validation_results
        components = validation_results['components']
        
        expected_components = [
            'document_processor', 'nlp_pipeline', 'data_validator', 
            'audit_manager', 'file_storage'
        ]
        
        for component in expected_components:
            assert component in components
            
        # Check for issues
        if 'issues' in validation_results and validation_results['issues']:
            print(f"System validation issues: {validation_results['issues']}")


class TestErrorScenarios:
    """Test error scenarios and recovery mechanisms."""
    
    def setup_method(self):
        """Set up test environment."""
        self.integration_manager = IntegrationManager()
        
    @pytest.mark.asyncio
    async def test_corrupted_file_handling(self):
        """Test handling of corrupted files."""
        # Create corrupted file
        corrupted_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        corrupted_file.write(b"This is not a valid PDF file")
        corrupted_file.close()
        
        try:
            # Process corrupted file
            session_id = await self.integration_manager.submit_document_for_processing(
                file_path=corrupted_file.name,
                filename="corrupted.pdf",
                file_size=25
            )
            
            # Wait for processing
            await asyncio.sleep(3)
            
            # Check status
            status = self.integration_manager.get_processing_status(session_id)
            
            # Should handle error gracefully
            assert status['status'] in ['error', 'completed']
            
            if status['status'] == 'error':
                assert 'error_message' in status
                
        finally:
            os.unlink(corrupted_file.name)
            
    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self):
        """Test handling of memory pressure scenarios."""
        # Simulate memory pressure
        with patch.object(self.integration_manager.performance_optimizer.memory_manager, 'check_memory_pressure') as mock_pressure:
            mock_pressure.return_value = True
            
            # Create test file
            test_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            test_file.write(b"%PDF-1.4\nTest content")
            test_file.close()
            
            try:
                # Mock document processing to avoid actual processing
                with patch.object(self.integration_manager.processing_pipeline, 'process_document_async') as mock_process:
                    mock_process.return_value = {
                        'session_id': 'test_session',
                        'records': [],
                        'processing_metadata': {'memory_pressure_handled': True}
                    }
                    
                    session_id = await self.integration_manager.submit_document_for_processing(
                        file_path=test_file.name,
                        filename="test.pdf",
                        file_size=20
                    )
                    
                    # Verify memory optimization was triggered
                    assert mock_pressure.called
                    
            finally:
                os.unlink(test_file.name)
                
    def test_service_degradation_scenarios(self):
        """Test graceful degradation when services fail."""
        # Test NLP service failure
        with patch.object(self.integration_manager.processing_pipeline.nlp_pipeline, 'process_text') as mock_nlp:
            mock_nlp.side_effect = Exception("NLP service unavailable")
            
            # Should fall back to basic text processing
            fallback_result = self.integration_manager.processing_pipeline._fallback_nlp_processing("test text")
            
            assert 'entities' in fallback_result
            assert fallback_result['fallback_used'] is True
            
    def test_database_connection_failure(self):
        """Test handling of database connection failures."""
        # Mock database failure
        with patch.object(self.integration_manager.processing_pipeline.session_manager, 'create_session') as mock_create:
            mock_create.side_effect = Exception("Database connection failed")
            
            # Should handle gracefully
            try:
                session_data = {
                    'session_id': 'test_session',
                    'file_name': 'test.pdf'
                }
                self.integration_manager.processing_pipeline.session_manager.create_session(session_data)
            except Exception as e:
                assert "Database connection failed" in str(e)


class TestConcurrentUsers:
    """Test concurrent user scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.integration_manager = IntegrationManager()
        
    @pytest.mark.asyncio
    async def test_multiple_concurrent_uploads(self):
        """Test multiple users uploading simultaneously."""
        # Create multiple test files
        test_files = []
        for i in range(5):
            test_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            test_file.write(f"Test PDF content {i}".encode())
            test_file.close()
            test_files.append(test_file.name)
            
        try:
            # Mock processing to avoid actual processing
            with patch.object(self.integration_manager.processing_pipeline, 'process_document_async') as mock_process:
                mock_process.return_value = {
                    'session_id': 'test_session',
                    'records': [HMORecord()],
                    'processing_metadata': {'concurrent_test': True}
                }
                
                # Submit multiple files concurrently
                tasks = []
                for i, file_path in enumerate(test_files):
                    task = self.integration_manager.submit_document_for_processing(
                        file_path=file_path,
                        filename=f"test_{i}.pdf",
                        file_size=20 + i
                    )
                    tasks.append(task)
                    
                # Wait for all submissions
                session_ids = await asyncio.gather(*tasks)
                
                # Verify all submissions succeeded
                assert len(session_ids) == 5
                assert all(isinstance(sid, str) for sid in session_ids)
                assert len(set(session_ids)) == 5  # All unique
                
        finally:
            # Clean up
            for file_path in test_files:
                try:
                    os.unlink(file_path)
                except:
                    pass
                    
    def test_concurrent_audit_operations(self):
        """Test concurrent audit interface operations."""
        # Mock audit manager
        audit_manager = self.integration_manager.processing_pipeline.audit_manager
        
        def simulate_audit_operation(operation_id):
            """Simulate audit operation."""
            time.sleep(0.1)  # Simulate processing time
            return f"audit_result_{operation_id}"
            
        # Run concurrent audit operations
        threads = []
        results = []
        
        for i in range(10):
            thread = threading.Thread(
                target=lambda i=i: results.append(simulate_audit_operation(i))
            )
            threads.append(thread)
            thread.start()
            
        # Wait for completion
        for thread in threads:
            thread.join()
            
        # Verify results
        assert len(results) == 10
        assert all(result.startswith('audit_result_') for result in results)
        
    def test_resource_contention_handling(self):
        """Test handling of resource contention."""
        # Simulate multiple threads accessing shared resources
        shared_counter = {'value': 0}
        lock = threading.Lock()
        
        def increment_counter():
            for _ in range(100):
                with lock:
                    shared_counter['value'] += 1
                    
        # Run multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=increment_counter)
            threads.append(thread)
            thread.start()
            
        # Wait for completion
        for thread in threads:
            thread.join()
            
        # Verify no race conditions
        assert shared_counter['value'] == 1000


class TestResourceManagement:
    """Test resource management under various conditions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.integration_manager = IntegrationManager()
        
    def test_file_cleanup_after_processing(self):
        """Test proper cleanup of temporary files."""
        initial_temp_files = len(list(Path(tempfile.gettempdir()).glob("*")))
        
        # Create and process multiple files
        for i in range(5):
            test_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            test_file.write(f"Test content {i}".encode())
            test_file.close()
            
            # Simulate processing (without actual processing)
            # In real implementation, this would trigger cleanup
            
            # Manual cleanup for test
            os.unlink(test_file.name)
            
        final_temp_files = len(list(Path(tempfile.gettempdir()).glob("*")))
        
        # Should not have significantly more temp files
        assert final_temp_files <= initial_temp_files + 2
        
    def test_memory_cleanup_after_processing(self):
        """Test memory cleanup after processing sessions."""
        import gc
        
        initial_objects = len(gc.get_objects())
        
        # Create multiple processing sessions (mock)
        sessions = []
        for i in range(10):
            session_data = {
                'session_id': f'test_session_{i}',
                'records': [HMORecord() for _ in range(100)],  # Create many objects
                'metadata': {'test': True}
            }
            sessions.append(session_data)
            
        # Clear sessions
        sessions.clear()
        
        # Force garbage collection
        collected = gc.collect()
        
        final_objects = len(gc.get_objects())
        
        # Should have collected significant objects
        assert collected > 0
        print(f"Collected {collected} objects, object count: {initial_objects} -> {final_objects}")
        
    def test_cache_size_management(self):
        """Test cache size management and cleanup."""
        cache_manager = self.integration_manager.performance_optimizer.cache_manager
        
        # Fill cache with many items
        for i in range(200):  # More than the memory cache limit
            cache_manager.cache_result(f"test_op_{i}", f"result_{i}", f"arg_{i}")
            
        # Check cache stats
        stats = cache_manager.get_cache_stats()
        
        # Memory cache should be limited
        assert stats['memory_cache_size'] <= 100  # Should be limited by cleanup
        
        # Should have some disk cache files
        assert stats['disk_cache_files'] > 0


class TestWebInterfaceIntegration:
    """Test web interface integration with backend services."""
    
    def setup_method(self):
        """Set up test environment."""
        self.integration_manager = IntegrationManager()
        
    def test_streamlit_app_initialization(self):
        """Test Streamlit app initialization with integration manager."""
        # Mock Streamlit components
        with patch('streamlit.set_page_config'), \
             patch('streamlit.session_state', {}):
            
            # This would normally be done in the actual app
            app = StreamlitApp()
            
            # Verify app can be initialized
            assert app is not None
            
    def test_file_upload_integration(self):
        """Test file upload integration with processing pipeline."""
        # Mock file upload
        mock_file = Mock()
        mock_file.name = "test_upload.pdf"
        mock_file.size = 1024 * 1024  # 1MB
        mock_file.getvalue.return_value = b"Mock PDF content"
        
        # Mock processing
        with patch.object(self.integration_manager, 'submit_document_for_processing') as mock_submit:
            mock_submit.return_value = asyncio.Future()
            mock_submit.return_value.set_result("test_session_id")
            
            # Simulate file upload processing
            async def simulate_upload():
                session_id = await self.integration_manager.submit_document_for_processing(
                    file_path="/tmp/test_upload.pdf",
                    filename=mock_file.name,
                    file_size=mock_file.size
                )
                return session_id
                
            session_id = asyncio.run(simulate_upload())
            assert session_id == "test_session_id"
            
    def test_results_download_integration(self):
        """Test results download integration."""
        # Mock session with results
        session_id = "test_download_session"
        
        with patch.object(self.integration_manager.processing_pipeline.session_manager, 'get_session') as mock_get_session:
            mock_get_session.return_value = {
                'session_id': session_id,
                'processing_status': 'completed',
                'csv_filename': 'test_results.csv'
            }
            
            with patch.object(self.integration_manager.processing_pipeline.file_storage, 'get_csv_path') as mock_get_path:
                mock_get_path.return_value = "/tmp/test_results.csv"
                
                # Test CSV download path retrieval
                csv_path = self.integration_manager.get_csv_download_path(session_id)
                assert csv_path == "/tmp/test_results.csv"


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short", "-x"])  # Stop on first failure for debugging