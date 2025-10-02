"""
Performance tests for the HMO document processing pipeline.

Tests processing speed, memory usage, concurrent user scenarios,
and resource management under various load conditions.
"""

import pytest
import asyncio
import time
import threading
from pathlib import Path
from typing import List, Dict, Any
import tempfile
import os
import psutil
from unittest.mock import Mock, patch

from services.integration_manager import IntegrationManager
from services.performance_optimizer import PerformanceOptimizer, CacheManager, MemoryManager
from models.hmo_record import HMORecord


class TestPerformanceOptimization:
    """Test performance optimization components."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.performance_optimizer = PerformanceOptimizer({
            'cache_dir': os.path.join(self.temp_dir, 'cache'),
            'memory_limit_mb': 512  # Lower limit for testing
        })
        
    def teardown_method(self):
        """Clean up test environment."""
        self.performance_optimizer.cleanup_resources()
        
    def test_cache_manager_basic_operations(self):
        """Test basic cache operations."""
        cache_manager = self.performance_optimizer.cache_manager
        
        # Test cache miss
        result = cache_manager.get_cached_result("test_op", "arg1", key="value")
        assert result is None
        
        # Test cache store and hit
        test_data = {"result": "test_result", "count": 42}
        cache_manager.cache_result("test_op", test_data, "arg1", key="value")
        
        cached_result = cache_manager.get_cached_result("test_op", "arg1", key="value")
        assert cached_result == test_data
        
        # Test cache stats
        stats = cache_manager.get_cache_stats()
        assert stats['total_hits'] == 1
        assert stats['total_misses'] == 1
        assert stats['hit_rate'] == 0.5
        
    def test_memory_manager_monitoring(self):
        """Test memory usage monitoring."""
        memory_manager = self.performance_optimizer.memory_manager
        
        # Test memory usage retrieval
        usage = memory_manager.get_memory_usage()
        assert 'rss_mb' in usage
        assert 'vms_mb' in usage
        assert 'percent' in usage
        assert 'available_mb' in usage
        
        # Test memory optimization
        optimization_result = memory_manager.optimize_memory()
        assert 'memory_freed_mb' in optimization_result
        assert 'objects_collected' in optimization_result
        
    def test_performance_monitor_operations(self):
        """Test performance monitoring."""
        monitor = self.performance_optimizer.performance_monitor
        
        # Start operation
        op_id = monitor.start_operation("test_operation")
        assert op_id in monitor.active_operations
        
        # Simulate some work
        time.sleep(0.1)
        
        # End operation
        metrics = monitor.end_operation(op_id, success=True)
        assert metrics.operation_name == "test_operation"
        assert metrics.duration_seconds >= 0.1
        assert metrics.success is True
        
        # Test performance summary
        summary = monitor.get_performance_summary("test_operation")
        assert summary['total_operations'] == 1
        assert summary['success_rate'] == 1.0
        
    def test_large_file_optimization_settings(self):
        """Test optimization settings for different file sizes."""
        optimizer = self.performance_optimizer
        
        # Small file
        small_settings = optimizer.optimize_for_large_files(5.0)  # 5MB
        assert not small_settings['use_chunked_processing']
        assert small_settings['batch_size'] == 20
        
        # Large file
        large_settings = optimizer.optimize_for_large_files(75.0)  # 75MB
        assert large_settings['use_chunked_processing']
        assert large_settings['batch_size'] == 10
        
        # Very large file
        huge_settings = optimizer.optimize_for_large_files(150.0)  # 150MB
        assert huge_settings['use_chunked_processing']
        assert huge_settings['use_streaming']
        assert huge_settings['batch_size'] == 5


class TestConcurrentProcessing:
    """Test concurrent processing capabilities."""
    
    def setup_method(self):
        """Set up test environment."""
        self.integration_manager = IntegrationManager()
        
    def test_concurrent_document_processing(self):
        """Test processing multiple documents concurrently."""
        # Create mock documents
        mock_files = []
        for i in range(3):
            mock_file = Mock()
            mock_file.name = f"test_doc_{i}.pdf"
            mock_file.size = 1024 * 1024  # 1MB
            mock_files.append(mock_file)
            
        # Mock the actual processing to avoid dependencies
        with patch.object(self.integration_manager.processing_pipeline, 'process_document_async') as mock_process:
            mock_process.return_value = {
                'session_id': 'test_session',
                'records': [HMORecord()],
                'processing_metadata': {'total_records': 1}
            }
            
            async def run_concurrent_test():
                # Submit multiple documents
                session_ids = []
                for mock_file in mock_files:
                    session_id = await self.integration_manager.submit_document_for_processing(
                        file_path=f"/tmp/{mock_file.name}",
                        filename=mock_file.name,
                        file_size=mock_file.size
                    )
                    session_ids.append(session_id)
                    
                return session_ids
                
            # Run the test
            session_ids = asyncio.run(run_concurrent_test())
            assert len(session_ids) == 3
            assert all(isinstance(sid, str) for sid in session_ids)
            
    def test_memory_usage_under_load(self):
        """Test memory usage under concurrent load."""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        def simulate_processing_load():
            """Simulate processing load."""
            # Create some data structures to simulate processing
            data = []
            for i in range(1000):
                record = HMORecord()
                record.council = f"Test Council {i}"
                record.reference = f"REF{i:06d}"
                record.hmo_address = f"{i} Test Street, Test City"
                data.append(record)
            
            # Simulate some processing time
            time.sleep(0.1)
            return len(data)
            
        # Run multiple threads to simulate concurrent processing
        threads = []
        results = []
        
        for i in range(5):
            thread = threading.Thread(target=lambda: results.append(simulate_processing_load()))
            threads.append(thread)
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100
        assert len(results) == 5
        assert all(result == 1000 for result in results)


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    def setup_method(self):
        """Set up benchmark environment."""
        self.integration_manager = IntegrationManager()
        
    def test_document_processing_speed_benchmark(self):
        """Benchmark document processing speed."""
        # Mock document processing components
        with patch.object(self.integration_manager.processing_pipeline.document_processor, 'process_document_with_fallback') as mock_doc_proc, \
             patch.object(self.integration_manager.processing_pipeline.nlp_pipeline, 'process_text') as mock_nlp, \
             patch.object(self.integration_manager.processing_pipeline.entity_extractor, 'extract_hmo_entities') as mock_entities:
            
            # Set up mocks
            mock_doc_proc.return_value = Mock(
                extracted_text="Test document content with HMO data",
                ocr_used=False,
                processing_metadata={'document_type': 'pdf'}
            )
            
            mock_nlp.return_value = {
                'entities': [],
                'tokens': ['test', 'document'],
                'sentences': ['Test document content.']
            }
            
            mock_entities.return_value = {
                'councils': [{'text': 'Test Council', 'confidence': 0.9}],
                'references': [{'text': 'REF123', 'confidence': 0.8}],
                'addresses': [{'text': '123 Test St', 'confidence': 0.7}],
                'dates': [],
                'names': [],
                'occupancies': []
            }
            
            async def benchmark_processing():
                start_time = time.time()
                
                # Process a document
                result = await self.integration_manager.processing_pipeline.process_document_async(
                    file_path="/tmp/test.pdf",
                    session_id="benchmark_session",
                    options={'confidence_threshold': 0.7}
                )
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                return processing_time, result
                
            # Run benchmark
            processing_time, result = asyncio.run(benchmark_processing())
            
            # Performance assertions
            assert processing_time < 30.0  # Should complete within 30 seconds
            assert 'records' in result
            assert 'processing_metadata' in result
            
            print(f"Document processing completed in {processing_time:.2f} seconds")
            
    def test_cache_performance_benchmark(self):
        """Benchmark cache performance."""
        cache_manager = CacheManager()
        
        # Benchmark cache operations
        test_data = {"large_result": list(range(10000))}
        
        # Measure cache write performance
        start_time = time.time()
        for i in range(100):
            cache_manager.cache_result(f"test_op_{i}", test_data, f"arg_{i}")
        write_time = time.time() - start_time
        
        # Measure cache read performance
        start_time = time.time()
        hits = 0
        for i in range(100):
            result = cache_manager.get_cached_result(f"test_op_{i}", f"arg_{i}")
            if result is not None:
                hits += 1
        read_time = time.time() - start_time
        
        # Performance assertions
        assert write_time < 5.0  # Should write 100 items in under 5 seconds
        assert read_time < 1.0   # Should read 100 items in under 1 second
        assert hits == 100       # All items should be cached
        
        print(f"Cache write: {write_time:.2f}s, Cache read: {read_time:.2f}s, Hit rate: 100%")
        
    def test_memory_optimization_benchmark(self):
        """Benchmark memory optimization effectiveness."""
        memory_manager = MemoryManager(memory_limit_mb=512)
        
        # Create memory pressure
        large_data = []
        for i in range(1000):
            large_data.append([j for j in range(1000)])  # Create large lists
            
        initial_memory = memory_manager.get_memory_usage()
        
        # Perform memory optimization
        start_time = time.time()
        optimization_result = memory_manager.optimize_memory()
        optimization_time = time.time() - start_time
        
        final_memory = memory_manager.get_memory_usage()
        
        # Performance assertions
        assert optimization_time < 5.0  # Should optimize within 5 seconds
        assert optimization_result['objects_collected'] > 0  # Should collect some objects
        
        print(f"Memory optimization: {optimization_time:.2f}s, "
              f"Objects collected: {optimization_result['objects_collected']}, "
              f"Memory freed: {optimization_result['memory_freed_mb']:.1f}MB")


class TestResourceManagement:
    """Test resource management under various conditions."""
    
    def test_file_handle_management(self):
        """Test proper file handle management."""
        initial_open_files = len(psutil.Process().open_files())
        
        # Simulate file operations
        temp_files = []
        try:
            for i in range(10):
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                temp_file.write(b"Test content for file handle test")
                temp_file.close()
                temp_files.append(temp_file.name)
                
            # Process files (mock processing)
            for file_path in temp_files:
                with open(file_path, 'r') as f:
                    content = f.read()
                    assert len(content) > 0
                    
        finally:
            # Clean up
            for file_path in temp_files:
                try:
                    os.unlink(file_path)
                except:
                    pass
                    
        final_open_files = len(psutil.Process().open_files())
        
        # Should not have leaked file handles
        assert final_open_files <= initial_open_files + 2  # Allow small variance
        
    def test_thread_pool_management(self):
        """Test thread pool resource management."""
        optimizer = PerformanceOptimizer()
        
        # Submit multiple tasks
        def dummy_task(x):
            time.sleep(0.1)
            return x * 2
            
        tasks = [lambda i=i: dummy_task(i) for i in range(20)]
        
        start_time = time.time()
        results = asyncio.run(
            optimizer.concurrency_manager.run_concurrent_tasks(tasks, timeout=10.0)
        )
        execution_time = time.time() - start_time
        
        # Verify results
        assert len(results) == 20
        assert all(isinstance(r, int) for r in results)
        assert execution_time < 5.0  # Should complete much faster than sequential
        
        # Clean up
        optimizer.cleanup_resources()
        
    def test_system_resource_monitoring(self):
        """Test system resource monitoring."""
        integration_manager = IntegrationManager()
        
        # Get performance status
        status = integration_manager.get_performance_status()
        
        # Verify status structure
        assert 'cache_stats' in status
        assert 'memory_usage' in status
        assert 'system_resources' in status
        
        system_resources = status['system_resources']
        assert 'cpu_count' in system_resources
        assert 'cpu_usage' in system_resources
        assert 'memory_total_gb' in system_resources
        assert 'memory_available_gb' in system_resources
        
        # Verify reasonable values
        assert system_resources['cpu_count'] > 0
        assert 0 <= system_resources['cpu_usage'] <= 100
        assert system_resources['memory_total_gb'] > 0
        assert system_resources['memory_available_gb'] >= 0


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short"])