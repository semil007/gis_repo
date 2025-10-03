#!/usr/bin/env python3
"""
Simple test script to verify the HMO processing system works.
"""

import asyncio
import sys
import logging

from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_processing():
    """Test the document processing system."""
    try:
        logger.info("Testing HMO Document Processing System...")
        
        # Import the integration manager
        from services.integration_manager import IntegrationManager
        
        # Initialize manager
        manager = IntegrationManager()
        
        # Check system status
        status = manager.validate_system_components()
        logger.info(f"System status: {status['overall_status']}")
        
        # Create a test file if it doesn't exist
        test_file = Path("temp") / "test_document.txt"
        if not test_file.exists():
            test_content = """
            Test Council HMO Licensing Department
            
            HMO Reference: HMO/2024/TEST001
            Property Address: 123 Test Street, Test City, TC1 2AB
            Licence Holder: John Smith
            HMO Manager: Jane Doe
            Maximum Occupancy: 5 persons
            """
            
            test_file.parent.mkdir(exist_ok=True)
            with open(test_file, 'w') as f:
                f.write(test_content)
        
        # Submit for processing
        logger.info("Submitting test document for processing...")
        session_id = await manager.submit_document_for_processing(
            file_path=test_file,
            filename="test_document.txt",
            file_size=test_file.stat().st_size,
            processing_options={'use_ocr': False, 'confidence_threshold': 0.5}
        )
        
        logger.info(f"Processing started with session ID: {session_id}")
        
        # Wait for processing to complete
        max_wait = 30  # seconds
        wait_time = 0
        
        while wait_time < max_wait:
            status = manager.get_processing_status(session_id)
            logger.info(f"Status: {status.get('status')} - Stage: {status.get('current_stage')} - Progress: {status.get('progress', 0):.1%}")
            
            if status.get('status') == 'completed':
                logger.info("✓ Processing completed successfully!")
                
                # Get results
                results = manager.get_processing_results(session_id)
                if results:
                    logger.info(f"Results: {results['total_records']} records extracted")
                    
                    # Check for CSV file
                    csv_path = manager.get_csv_download_path(session_id)
                    if csv_path and Path(csv_path).exists():
                        logger.info(f"✓ CSV file created: {csv_path}")
                        
                        # Show first few lines of CSV
                        with open(csv_path, 'r') as f:
                            lines = f.readlines()[:5]
                            logger.info("CSV content preview:")
                            for line in lines:
                                logger.info(f"  {line.strip()}")
                    else:
                        logger.warning("CSV file not found")
                else:
                    logger.warning("No results available")
                
                return True
                
            elif status.get('status') == 'error':
                logger.error(f"Processing failed: {status.get('error_message', 'Unknown error')}")
                return False
            
            await asyncio.sleep(1)
            wait_time += 1
        
        logger.error("Processing timed out")
        return False
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    logger.info("Starting HMO Processing System Test")
    logger.info("=" * 50)
    
    # Run the async test
    success = asyncio.run(test_processing())
    
    logger.info("=" * 50)
    if success:
        logger.info("✓ Test completed successfully!")
        logger.info("The system is working correctly.")
    else:
        logger.error("✗ Test failed!")
        logger.info("Please check the error messages above.")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)