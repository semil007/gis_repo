#!/usr/bin/env python3
"""
Startup script for HMO Document Processing Pipeline.
Ensures system is ready before starting the Streamlit app.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_setup():
    """Ensure the system is properly set up."""
    try:
        logger.info("Checking system setup...")
        
        # Run setup if needed
        from fix_setup import main as setup_main
        setup_success = setup_main()
        
        if not setup_success:
            logger.error("Setup failed. Please check the error messages.")
            return False
            
        logger.info("✓ System setup verified")
        return True
        
    except Exception as e:
        logger.error(f"Setup check failed: {e}")
        return False


def start_streamlit():
    """Start the Streamlit application."""
    try:
        logger.info("Starting Streamlit application...")
        
        # Set environment variables for better performance
        os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
        os.environ['STREAMLIT_SERVER_PORT'] = '8501'
        os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
        
        # Start Streamlit
        cmd = [sys.executable, '-m', 'streamlit', 'run', 'app.py']
        
        logger.info("🚀 Starting HMO Document Processing Pipeline...")
        logger.info("📱 Open your browser to: http://localhost:8501")
        logger.info("🛑 Press Ctrl+C to stop the application")
        
        # Run Streamlit
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        logger.info("\n👋 Application stopped by user")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start Streamlit: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False
    
    return True


def main():
    """Main startup function."""
    print("🏠 HMO Document Processing Pipeline")
    print("=" * 50)
    
    # Ensure system is set up
    if not ensure_setup():
        print("\n❌ System setup failed. Please fix the issues and try again.")
        return False
    
    # Start the application
    print("\n🚀 Starting application...")
    success = start_streamlit()
    
    if success:
        print("\n✅ Application started successfully!")
    else:
        print("\n❌ Failed to start application.")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)