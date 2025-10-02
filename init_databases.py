"""
Database initialization script for HMO Document Processing Pipeline.
Run this script to create and initialize the required database files.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.session_manager import SessionManager
from services.audit_manager import AuditManager


def init_databases():
    """Initialize all required databases."""
    print("Initializing HMO Document Processing Pipeline databases...")
    
    # Get database paths from environment or use defaults
    session_db_path = os.getenv('DATABASE_URL', 'sqlite:///processing_sessions.db')
    audit_db_path = os.getenv('AUDIT_DATABASE_URL', 'sqlite:///audit_data.db')
    
    # Remove sqlite:/// or sqlite://// prefix if present
    if session_db_path.startswith('sqlite:////'):
        session_db_path = session_db_path.replace('sqlite:////', '')
    elif session_db_path.startswith('sqlite:///'):
        session_db_path = session_db_path.replace('sqlite:///', '')
    
    if audit_db_path.startswith('sqlite:////'):
        audit_db_path = audit_db_path.replace('sqlite:////', '')
    elif audit_db_path.startswith('sqlite:///'):
        audit_db_path = audit_db_path.replace('sqlite:///', '')
    
    print(f"\nSession database: {session_db_path}")
    print(f"Audit database: {audit_db_path}")
    
    # Ensure parent directories exist
    for db_path in [session_db_path, audit_db_path]:
        parent_dir = Path(db_path).parent
        if parent_dir != Path('.') and str(parent_dir) != '.':
            parent_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {parent_dir}")
    
    try:
        # Initialize session database
        print("\n1. Initializing session database...")
        session_manager = SessionManager(db_path=session_db_path)
        print("   OK: Session database initialized successfully")
        
        # Get database stats
        stats = session_manager.get_database_stats()
        print(f"   - Database size: {stats['database_size_bytes']} bytes")
        print(f"   - Total records: {stats['total_records']}")
        
    except Exception as e:
        print(f"   ERROR: Error initializing session database: {e}")
        return False
    
    try:
        # Initialize audit database
        print("\n2. Initializing audit database...")
        audit_manager = AuditManager(db_path=audit_db_path)
        print("   OK: Audit database initialized successfully")
        
    except Exception as e:
        print(f"   ERROR: Error initializing audit database: {e}")
        return False
    
    print("\n" + "="*60)
    print("OK: All databases initialized successfully!")
    print("="*60)
    print("\nYou can now run the application:")
    print("  streamlit run app.py")
    print("\nOr start the worker:")
    print("  python worker.py")
    
    return True


if __name__ == "__main__":
    success = init_databases()
    sys.exit(0 if success else 1)
