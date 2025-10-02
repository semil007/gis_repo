"""
Performance optimization and monitoring for the HMO document processing pipeline.

Provides caching, memory management, concurrent processing optimization,
and performance monitoring capabilities.
"""

import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps, lru_cache
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import hashlib
import pickle
import os
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    operation_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    memory_usage_mb: float
    cpu_usage_percent: float
    success: bool
    error_message: Optional[str] = None
    additional_metrics: Dict[str, Any] = None


class CacheManager:
    """
    Intelligent caching system for repeated operations.
    
    Requirements: 5.2, 5.4
    """
    
    def __init__(self, cache_dir: str = "cache", max_cache_size_mb: int = 500):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache storage
            max_cache_size_mb: Maximum cache size in MB
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_cache_size_mb = max_cache_size_mb
        self.memory_cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
        
    def _generate_cache_key(self, operation: str, *args, **kwargs) -> str:
        """Generate cache key from operation and parameters."""
        key_data = f"{operation}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
        
    def get_cached_result(self, operation: str, *args, **kwargs) -> Optional[Any]:
        """
        Get cached result if available.
        
        Args:
            operation: Operation name
            *args, **kwargs: Operation parameters
            
        Returns:
            Cached result or None if not found
        """
        cache_key = self._generate_cache_key(operation, *args, **kwargs)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            self.cache_stats['hits'] += 1
            return self.memory_cache[cache_key]['result']
            
        # Check disk cache
        cache_file = self.cache_dir / f"{cache_key}.cache"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    
                # Check if cache is still valid (24 hours)
                if datetime.now() - cached_data['timestamp'] < timedelta(hours=24):
                    self.memory_cache[cache_key] = cached_data
                    self.cache_stats['hits'] += 1
                    return cached_data['result']
                else:
                    # Cache expired, remove it
                    cache_file.unlink()
                    
            except Exception as e:
                logger.warning(f"Failed to load cache file {cache_file}: {str(e)}")
                
        self.cache_stats['misses'] += 1
        return None
        
    def cache_result(self, operation: str, result: Any, *args, **kwargs) -> None:
        """
        Cache operation result.
        
        Args:
            operation: Operation name
            result: Result to cache
            *args, **kwargs: Operation parameters
        """
        cache_key = self._generate_cache_key(operation, *args, **kwargs)
        
        cached_data = {
            'result': result,
            'timestamp': datetime.now(),
            'operation': operation
        }
        
        # Store in memory cache
        self.memory_cache[cache_key] = cached_data
        
        # Store in disk cache for persistence
        try:
            cache_file = self.cache_dir / f"{cache_key}.cache"
            with open(cache_file, 'wb') as f:
                pickle.dump(cached_data, f)
        except Exception as e:
            logger.warning(f"Failed to save cache file: {str(e)}")
            
        # Clean up if cache is too large
        self._cleanup_cache()
        
    def _cleanup_cache(self) -> None:
        """Clean up cache if it exceeds size limits."""
        try:
            # Check disk cache size
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.cache"))
            max_size_bytes = self.max_cache_size_mb * 1024 * 1024
            
            if total_size > max_size_bytes:
                # Remove oldest cache files
                cache_files = list(self.cache_dir.glob("*.cache"))
                cache_files.sort(key=lambda f: f.stat().st_mtime)
                
                while total_size > max_size_bytes * 0.8 and cache_files:  # Clean to 80% of limit
                    oldest_file = cache_files.pop(0)
                    file_size = oldest_file.stat().st_size
                    oldest_file.unlink()
                    total_size -= file_size
                    self.cache_stats['evictions'] += 1
                    
            # Limit memory cache size
            if len(self.memory_cache) > 100:  # Keep only 100 items in memory
                # Remove oldest items
                sorted_items = sorted(
                    self.memory_cache.items(),
                    key=lambda x: x[1]['timestamp']
                )
                
                for key, _ in sorted_items[:-50]:  # Keep only 50 newest
                    del self.memory_cache[key]
                    
        except Exception as e:
            logger.warning(f"Cache cleanup failed: {str(e)}")
            
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = self.cache_stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'hit_rate': hit_rate,
            'total_hits': self.cache_stats['hits'],
            'total_misses': self.cache_stats['misses'],
            'total_evictions': self.cache_stats['evictions'],
            'memory_cache_size': len(self.memory_cache),
            'disk_cache_files': len(list(self.cache_dir.glob("*.cache")))
        }


class MemoryManager:
    """
    Memory usage monitoring and optimization.
    
    Requirements: 5.2, 5.4
    """
    
    def __init__(self, memory_limit_mb: int = 2048):
        """
        Initialize memory manager.
        
        Args:
            memory_limit_mb: Memory limit in MB
        """
        self.memory_limit_mb = memory_limit_mb
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        self.monitoring_active = False
        self.memory_history = []
        
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024
        }
        
    def check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure."""
        memory_usage = self.get_memory_usage()
        
        # Check if we're approaching limits
        if memory_usage['rss_mb'] > self.memory_limit_mb * 0.8:
            return True
            
        # Check system memory
        if memory_usage['available_mb'] < 500:  # Less than 500MB available
            return True
            
        return False
        
    def optimize_memory(self) -> Dict[str, Any]:
        """
        Perform memory optimization.
        
        Returns:
            Dict with optimization results
        """
        import gc
        
        before_memory = self.get_memory_usage()
        
        # Force garbage collection
        collected = gc.collect()
        
        # Clear any large temporary variables
        # This would be implemented based on specific application needs
        
        after_memory = self.get_memory_usage()
        
        memory_freed = before_memory['rss_mb'] - after_memory['rss_mb']
        
        optimization_result = {
            'memory_freed_mb': memory_freed,
            'objects_collected': collected,
            'before_usage_mb': before_memory['rss_mb'],
            'after_usage_mb': after_memory['rss_mb']
        }
        
        logger.info(f"Memory optimization: freed {memory_freed:.1f}MB, collected {collected} objects")
        
        return optimization_result
        
    def start_monitoring(self, interval_seconds: int = 30) -> None:
        """Start memory monitoring in background thread."""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        
        def monitor():
            while self.monitoring_active:
                try:
                    memory_usage = self.get_memory_usage()
                    self.memory_history.append({
                        'timestamp': datetime.now(),
                        'usage': memory_usage
                    })
                    
                    # Keep only last 100 measurements
                    if len(self.memory_history) > 100:
                        self.memory_history.pop(0)
                        
                    # Check for memory pressure
                    if self.check_memory_pressure():
                        logger.warning(f"Memory pressure detected: {memory_usage['rss_mb']:.1f}MB used")
                        self.optimize_memory()
                        
                    time.sleep(interval_seconds)
                    
                except Exception as e:
                    logger.error(f"Memory monitoring error: {str(e)}")
                    time.sleep(interval_seconds)
                    
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        
    def stop_monitoring(self) -> None:
        """Stop memory monitoring."""
        self.monitoring_active = False


class ConcurrencyManager:
    """
    Manage concurrent processing for optimal performance.
    
    Requirements: 5.2
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize concurrency manager.
        
        Args:
            max_workers: Maximum number of worker threads/processes
        """
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.thread_executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=min(4, os.cpu_count() or 1))
        
    async def run_concurrent_tasks(
        self,
        tasks: List[Callable],
        use_processes: bool = False,
        timeout: Optional[float] = None
    ) -> List[Any]:
        """
        Run multiple tasks concurrently.
        
        Args:
            tasks: List of callable tasks
            use_processes: Whether to use process pool instead of thread pool
            timeout: Timeout for all tasks
            
        Returns:
            List of task results
        """
        executor = self.process_executor if use_processes else self.thread_executor
        
        loop = asyncio.get_event_loop()
        
        try:
            # Submit all tasks
            futures = [
                loop.run_in_executor(executor, task)
                for task in tasks
            ]
            
            # Wait for completion with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*futures, return_exceptions=True),
                timeout=timeout
            )
            
            return results
            
        except asyncio.TimeoutError:
            logger.error(f"Concurrent tasks timed out after {timeout} seconds")
            raise
            
    def batch_process(
        self,
        items: List[Any],
        process_func: Callable,
        batch_size: int = 10,
        use_processes: bool = False
    ) -> List[Any]:
        """
        Process items in batches for better performance.
        
        Args:
            items: Items to process
            process_func: Function to process each item
            batch_size: Size of each batch
            use_processes: Whether to use process pool
            
        Returns:
            List of processed results
        """
        results = []
        executor = self.process_executor if use_processes else self.thread_executor
        
        # Split items into batches
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        def process_batch(batch):
            return [process_func(item) for item in batch]
            
        # Process batches concurrently
        futures = [executor.submit(process_batch, batch) for batch in batches]
        
        for future in futures:
            try:
                batch_results = future.result(timeout=300)  # 5 minute timeout per batch
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"Batch processing error: {str(e)}")
                # Add None results for failed batch
                results.extend([None] * len(batches[futures.index(future)]))
                
        return results


class PerformanceMonitor:
    """
    Monitor and track performance metrics.
    
    Requirements: 5.2, 5.4
    """
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics_history = []
        self.active_operations = {}
        
    def start_operation(self, operation_name: str) -> str:
        """
        Start monitoring an operation.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            Operation ID for tracking
        """
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        
        self.active_operations[operation_id] = {
            'name': operation_name,
            'start_time': datetime.now(),
            'start_memory': self._get_memory_usage(),
            'start_cpu': self._get_cpu_usage()
        }
        
        return operation_id
        
    def end_operation(
        self,
        operation_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> PerformanceMetrics:
        """
        End monitoring an operation and record metrics.
        
        Args:
            operation_id: Operation ID from start_operation
            success: Whether operation succeeded
            error_message: Error message if failed
            additional_metrics: Additional metrics to record
            
        Returns:
            PerformanceMetrics object
        """
        if operation_id not in self.active_operations:
            logger.warning(f"Unknown operation ID: {operation_id}")
            return None
            
        operation_data = self.active_operations.pop(operation_id)
        end_time = datetime.now()
        
        metrics = PerformanceMetrics(
            operation_name=operation_data['name'],
            start_time=operation_data['start_time'],
            end_time=end_time,
            duration_seconds=(end_time - operation_data['start_time']).total_seconds(),
            memory_usage_mb=self._get_memory_usage(),
            cpu_usage_percent=self._get_cpu_usage(),
            success=success,
            error_message=error_message,
            additional_metrics=additional_metrics or {}
        )
        
        self.metrics_history.append(metrics)
        
        # Keep only last 1000 metrics
        if len(self.metrics_history) > 1000:
            self.metrics_history.pop(0)
            
        return metrics
        
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
            
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            return psutil.cpu_percent(interval=0.1)
        except:
            return 0.0
            
    def get_performance_summary(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance summary statistics.
        
        Args:
            operation_name: Filter by specific operation name
            
        Returns:
            Performance summary
        """
        filtered_metrics = self.metrics_history
        
        if operation_name:
            filtered_metrics = [m for m in self.metrics_history if m.operation_name == operation_name]
            
        if not filtered_metrics:
            return {'message': 'No metrics available'}
            
        durations = [m.duration_seconds for m in filtered_metrics]
        memory_usage = [m.memory_usage_mb for m in filtered_metrics]
        success_rate = sum(1 for m in filtered_metrics if m.success) / len(filtered_metrics)
        
        return {
            'total_operations': len(filtered_metrics),
            'success_rate': success_rate,
            'average_duration_seconds': sum(durations) / len(durations),
            'min_duration_seconds': min(durations),
            'max_duration_seconds': max(durations),
            'average_memory_mb': sum(memory_usage) / len(memory_usage),
            'max_memory_mb': max(memory_usage),
            'recent_operations': [
                {
                    'operation': m.operation_name,
                    'duration': m.duration_seconds,
                    'success': m.success,
                    'timestamp': m.start_time.isoformat()
                }
                for m in filtered_metrics[-10:]  # Last 10 operations
            ]
        }


def performance_monitor_decorator(monitor: PerformanceMonitor, operation_name: Optional[str] = None):
    """
    Decorator for automatic performance monitoring.
    
    Args:
        monitor: PerformanceMonitor instance
        operation_name: Optional operation name (defaults to function name)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            operation_id = monitor.start_operation(op_name)
            
            try:
                result = func(*args, **kwargs)
                monitor.end_operation(operation_id, success=True)
                return result
            except Exception as e:
                monitor.end_operation(operation_id, success=False, error_message=str(e))
                raise
                
        return wrapper
    return decorator


def cached_operation(cache_manager: CacheManager, operation_name: Optional[str] = None):
    """
    Decorator for automatic caching of operation results.
    
    Args:
        cache_manager: CacheManager instance
        operation_name: Optional operation name (defaults to function name)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            
            # Try to get cached result
            cached_result = cache_manager.get_cached_result(op_name, *args, **kwargs)
            if cached_result is not None:
                return cached_result
                
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.cache_result(op_name, result, *args, **kwargs)
            
            return result
            
        return wrapper
    return decorator


class PerformanceOptimizer:
    """
    Main performance optimization coordinator.
    
    Requirements: 5.2, 5.4
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize performance optimizer.
        
        Args:
            config: Configuration dictionary
        """
        config = config or {}
        
        self.cache_manager = CacheManager(
            cache_dir=config.get('cache_dir', 'cache'),
            max_cache_size_mb=config.get('max_cache_size_mb', 500)
        )
        
        self.memory_manager = MemoryManager(
            memory_limit_mb=config.get('memory_limit_mb', 2048)
        )
        
        self.concurrency_manager = ConcurrencyManager(
            max_workers=config.get('max_workers')
        )
        
        self.performance_monitor = PerformanceMonitor()
        
        # Start memory monitoring
        self.memory_manager.start_monitoring()
        
    def optimize_for_large_files(self, file_size_mb: float) -> Dict[str, Any]:
        """
        Optimize settings for large file processing.
        
        Args:
            file_size_mb: File size in MB
            
        Returns:
            Optimization recommendations
        """
        recommendations = {
            'use_chunked_processing': file_size_mb > 50,
            'chunk_size_mb': min(10, file_size_mb / 10),
            'enable_memory_monitoring': file_size_mb > 20,
            'use_disk_cache': file_size_mb > 100,
            'concurrent_processing': file_size_mb > 30
        }
        
        if file_size_mb > 100:
            # Very large files
            recommendations.update({
                'memory_limit_mb': 1024,  # Stricter memory limit
                'use_streaming': True,
                'batch_size': 5
            })
        elif file_size_mb > 50:
            # Large files
            recommendations.update({
                'memory_limit_mb': 1536,
                'batch_size': 10
            })
        else:
            # Normal files
            recommendations.update({
                'memory_limit_mb': 2048,
                'batch_size': 20
            })
            
        return recommendations
        
    def get_system_performance_status(self) -> Dict[str, Any]:
        """Get comprehensive system performance status."""
        return {
            'cache_stats': self.cache_manager.get_cache_stats(),
            'memory_usage': self.memory_manager.get_memory_usage(),
            'memory_pressure': self.memory_manager.check_memory_pressure(),
            'performance_summary': self.performance_monitor.get_performance_summary(),
            'system_resources': {
                'cpu_count': os.cpu_count(),
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'memory_available_gb': psutil.virtual_memory().available / 1024 / 1024 / 1024,
                'disk_usage': psutil.disk_usage('/').percent
            }
        }
        
    def cleanup_resources(self) -> None:
        """Clean up resources and stop monitoring."""
        self.memory_manager.stop_monitoring()
        self.concurrency_manager.thread_executor.shutdown(wait=True)
        self.concurrency_manager.process_executor.shutdown(wait=True)