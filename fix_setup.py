#!/usr/bin/env python3
"""
Setup and fix script for HMO Document Processing Pipeline.
This script ensures all components are properly initialized and working.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_directories():
    """Create necessary directories."""
    directories = [
        'temp',
        'sample_outputs',
        'file_storage',
        'cache',
        'logs'
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(exist_ok=True)
        logger.info(f"Created directory: {directory}")


def initialize_databases():
    """Initialize databases."""
    try:
        logger.info("Initializing databases...")
        
        # Import and run database initialization
        from init_databases import init_databases
        success = init_databases()
        
        if success:
            logger.info("✓ Databases initialized successfully")
        else:
            logger.error("✗ Database initialization failed")
            return False
            
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False
    
    return True


def test_simple_processor():
    """Test the simple processor."""
    try:
        logger.info("Testing simple processor...")
        
        from services.simple_processor import SimpleProcessor
        processor = SimpleProcessor()
        
        logger.info("✓ Simple processor initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Simple processor test failed: {e}")
        return False


def test_integration_manager():
    """Test the integration manager."""
    try:
        logger.info("Testing integration manager...")
        
        from services.integration_manager import IntegrationManager
        manager = IntegrationManager()
        
        # Test system validation
        status = manager.validate_system_components()
        logger.info(f"System status: {status['overall_status']}")
        
        logger.info("✓ Integration manager initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Integration manager test failed: {e}")
        return False


def create_sample_files():
    """Create sample files for testing."""
    try:
        logger.info("Creating sample files...")
        
        # Create a simple test PDF content
        sample_text = """
        Test Council HMO Licensing Department
        
        HMO Reference: HMO/2024/TEST001
        Property Address: 123 Test Street, Test City, TC1 2AB
        Licence Holder: John Smith
        HMO Manager: Jane Doe
        Maximum Occupancy: 5 persons
        Licence Start Date: 01/01/2024
        Licence Expiry Date: 31/12/2024
        
        This is a test document for the HMO processing system.
        """
        
        # Save as text file for testing
        test_file = Path("temp") / "test_document.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(sample_text)
        
        logger.info(f"✓ Created sample test file: {test_file}")
        return True
        
    except Exception as e:
        logger.error(f"Sample file creation failed: {e}")
        return False


def check_dependencies():
    """Check if required dependencies are available."""
    required_packages = [
        'streamlit',
        'PyPDF2',
        'python-docx',
        'pandas',
        'pathlib'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'python-docx':
                import docx
            elif package == 'PyPDF2':
                import PyPDF2
            else:
                __import__(package)
            logger.info(f"✓ {package} is available")
        except ImportError:
            missing_packages.append(package)
            logger.warning(f"✗ {package} is missing")
    
    if missing_packages:
        logger.error(f"Missing packages: {', '.join(missing_packages)}")
        logger.info("Install missing packages with: pip install " + " ".join(missing_packages))
        return False
    
    return True


def main():
    """Main setup function."""
    logger.info("Starting HMO Document Processing Pipeline setup...")
    logger.info("=" * 60)
    
    success = True
    
    # Check dependencies
    logger.info("1. Checking dependencies...")
    if not check_dependencies():
        success = False
    
    # Create directories
    logger.info("\n2. Creating directories...")
    create_directories()
    
    # Initialize databases
    logger.info("\n3. Initializing databases...")
    if not initialize_databases():
        success = False
    
    # Test simple processor
    logger.info("\n4. Testing simple processor...")
    if not test_simple_processor():
        success = False
    
    # Test integration manager
    logger.info("\n5. Testing integration manager...")
    if not test_integration_manager():
        success = False
    
    # Create sample files
    logger.info("\n6. Creating sample files...")
    if not create_sample_files():
        success = False
    
    logger.info("\n" + "=" * 60)
    
    if success:
        logger.info("✓ Setup completed successfully!")
        logger.info("\nYou can now run the application:")
        logger.info("  streamlit run app.py")
        logger.info("\nOr test with the sample file:")
        logger.info("  python test_simple.py")
    else:
        logger.error("✗ Setup completed with errors!")
        logger.info("Please check the error messages above and fix any issues.")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)