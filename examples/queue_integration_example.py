"""
Example demonstrating integration of queue, session, and file storage systems.
This shows how the components work together in the document processing pipeline.
"""

import time
from pathlib import Path
from services.queue_manager import QueueManager, JobStatus
from services.session_manager import SessionManager
from services.file_storage import FileStorageManager
from services.queue_worker import QueueWorker, create_document_processor_func


def mock_document_processor():
    """Mock document processor for demonstration"""
    class MockProcessor:
        def process_document(self, file_path, column_mappings=None, progress_callback=None):
            """Mock document processing"""
            if progress_callback:
                progress_callback(25, "Starting extraction")
                time.sleep(0.1)
                progress_callback(50, "Processing content")
                time.sleep(0.1)
                progress_callback(75, "Validating data")
                time.sleep(0.1)
                progress_callback(100, "Processing complete")
            
            return {
                'records': [
                    {'council': 'Test Council', 'reference': 'HMO123', 'hmo_address': '123 Test St'},
                    {'council': 'Test Council', 'reference': 'HMO124', 'hmo_address': '124 Test St'}
                ],
                'quality_metrics': {'accuracy': 0.95, 'confidence': 0.88},
                'flagged_records': [],
                'metadata': {'processing_time': 0.3, 'file_size': 1024}
            }
    
    return MockProcessor()


def demonstrate_integration():
    """Demonstrate the integration of all queue and storage systems"""
    print("=== Document Processing Pipeline Integration Demo ===\n")
    
    # Initialize components
    print("1. Initializing components...")
    
    try:
        # Note: This requires Redis to be running for full functionality
        queue_manager = QueueManager()
        print("   ✓ Queue Manager initialized")
    except Exception as e:
        print(f"   ⚠ Queue Manager failed (Redis not available): {e}")
        print("   → Continuing with other components...")
        queue_manager = None
    
    session_manager = SessionManager(db_path="demo_sessions.db")
    print("   ✓ Session Manager initialized")
    
    file_storage = FileStorageManager(
        storage_root="demo_storage",
        temp_dir="demo_temp",
        max_storage_gb=1.0
    )
    print("   ✓ File Storage Manager initialized")
    
    # Create a demo session
    print("\n2. Creating processing session...")
    session_id = session_manager.create_session(
        file_name="demo_document.pdf",
        file_size=1024000,
        column_mappings={"Council": "council", "Reference": "reference"},
        processing_config={"confidence_threshold": 0.7}
    )
    print(f"   ✓ Created session: {session_id}")
    
    # Create a demo file
    print("\n3. Creating demo file...")
    demo_content = b"%PDF-1.4\nDemo PDF content for testing"
    temp_file = file_storage.create_temp_file(session_id, ".pdf")
    temp_file.write_bytes(demo_content)
    
    success, message, stored_path = file_storage.store_uploaded_file(
        temp_file, session_id, "demo_document.pdf"
    )
    print(f"   ✓ File stored: {success} - {message}")
    
    if queue_manager:
        # Enqueue processing job
        print("\n4. Enqueuing processing job...")
        job_id = queue_manager.enqueue_job(
            file_path=stored_path,
            session_id=session_id,
            config={"column_mappings": {"Council": "council"}}
        )
        print(f"   ✓ Job enqueued: {job_id}")
        
        # Create and start worker
        print("\n5. Starting worker to process job...")
        processor = mock_document_processor()
        processor_func = create_document_processor_func(processor)
        
        worker = QueueWorker(queue_manager, processor_func, "demo_worker")
        worker.start()
        
        # Wait for processing
        print("   → Processing job...")
        time.sleep(1)
        
        # Check job status
        job = queue_manager.get_job(job_id)
        if job:
            print(f"   ✓ Job status: {job.status.value}")
            print(f"   ✓ Job progress: {job.progress}%")
        
        worker.stop()
        
        # Get queue stats
        stats = queue_manager.get_queue_stats()
        print(f"   ✓ Queue stats: {stats}")
    
    # Update session with results
    print("\n6. Updating session with results...")
    session_manager.update_session_status(session_id, "completed", quality_score=0.95)
    session_manager.update_session_metrics(session_id, total_records=2, flagged_records=0)
    
    # Store mock results
    from models.hmo_record import HMORecord
    records = []
    for i in range(2):
        record = HMORecord()
        record.council = "Test Council"
        record.reference = f"HMO12{3+i}"
        record.hmo_address = f"12{3+i} Test St"
        record.confidence_scores = {"council": 0.95, "reference": 0.90}
        records.append(record)
    
    session_manager.store_extracted_records(session_id, records)
    print("   ✓ Results stored in session")
    
    # Create export file
    print("\n7. Creating export file...")
    csv_content = "council,reference,hmo_address\nTest Council,HMO123,123 Test St\nTest Council,HMO124,124 Test St"
    success, message, export_path = file_storage.create_export_file(
        session_id, csv_content, "results.csv"
    )
    print(f"   ✓ Export created: {success} - {message}")
    
    # Get comprehensive stats
    print("\n8. System statistics...")
    
    # Session stats
    session = session_manager.get_session(session_id)
    print(f"   → Session records: {session.total_records}")
    print(f"   → Session quality: {session.quality_score}")
    
    # Storage stats
    storage_stats = file_storage.get_storage_stats()
    print(f"   → Storage usage: {storage_stats['usage_percentage']:.1f}%")
    print(f"   → Total files: {sum(dir_stats['file_count'] for dir_stats in storage_stats['directories'].values())}")
    
    # Database stats
    db_stats = session_manager.get_database_stats()
    print(f"   → Database sessions: {sum(db_stats['session_counts'].values())}")
    print(f"   → Database records: {db_stats['total_records']}")
    
    # Cleanup demo
    print("\n9. Cleaning up demo files...")
    cleanup_stats = file_storage.cleanup_old_files()
    print(f"   ✓ Cleaned up {cleanup_stats['temp_files']} temp files")
    
    # Clean up database
    Path("demo_sessions.db").unlink(missing_ok=True)
    
    print("\n=== Demo completed successfully! ===")


if __name__ == "__main__":
    demonstrate_integration()