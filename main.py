"""
Main entry point for the Document Processing Pipeline
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    print("Document Processing Pipeline")
    print("=" * 40)
    print()
    print("To start the web interface:")
    print("  streamlit run web/app.py")
    print()
    print("Or use the deployment scripts:")
    print("  ./scripts/start.sh")
    print()
    print("For Docker deployment:")
    print("  docker-compose up -d")