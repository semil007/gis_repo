"""
Processing session model for tracking upload and processing state.
"""
import sqlite3
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from .hmo_record import HMORecord


@dataclass
class ProcessingSession:
    """
    Model for tracking document processing sessions with SQLite persistence.
    
    Manages upload state, processing progress, and quality metrics.
    """
    
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    file_name: str = ""
    file_size: int = 0
    file_path: str = ""
    upload_timestamp: datetime = field(default_factory=datetime.now)
    processing_status: str = "uploaded"  # uploaded, processing, completed, failed
    processing_start_time: Optional[datetime] = None
    processing_end_time: Optional[datetime] = None
    
    # Processing results
    extracted_records: List[HMORecord] = field(default_factory=list)
    total_records: int = 0
    flagged_records: List[str] = field(default_factory=list)  # List of record IDs
    
    # Quality metrics
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    overall_confidence: float = 0.0
    extraction_errors: List[str] = field(default_factory=list)
    
    # Configuration
    column_mappings: Dict[str, str] = field(default_factory=dict)
    processing_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default quality metrics."""
        if not self.quality_metrics:
            self.quality_metrics = {
                'total_records_found': 0,
                'records_with_high_confidence': 0,
                'records_flagged_for_review': 0,
                'average_confidence_score': 0.0,
                'field_extraction_rates': {},
                'processing_time_seconds': 0.0
            }
    
    def start_processing(self):
        """Mark session as started processing."""
        self.processing_status = "processing"
        self.processing_start_time = datetime.now()
    
    def complete_processing(self):
        """Mark session as completed and calculate final metrics."""
        self.processing_status = "completed"
        self.processing_end_time = datetime.now()
        self.calculate_quality_metrics()
    
    def fail_processing(self, error_message: str):
        """Mark session as failed with error message."""
        self.processing_status = "failed"
        self.processing_end_time = datetime.now()
        self.extraction_errors.append(error_message)
    
    def add_record(self, record: HMORecord):
        """
        Add an extracted record to the session.
        
        Args:
            record: HMORecord to add to the session
        """
        self.extracted_records.append(record)
        self.total_records = len(self.extracted_records)
        
        # Check if record should be flagged
        if record.is_flagged_for_review():
            record_id = f"{self.session_id}_{len(self.extracted_records)}"
            self.flagged_records.append(record_id)
    
    def calculate_quality_metrics(self):
        """Calculate and update quality metrics based on extracted records."""
        if not self.extracted_records:
            return
        
        total_records = len(self.extracted_records)
        high_confidence_count = 0
        total_confidence = 0.0
        field_extraction_counts = {}
        
        # Initialize field extraction tracking
        for field_name in HMORecord.get_field_names():
            field_extraction_counts[field_name] = 0
        
        # Analyze each record
        for record in self.extracted_records:
            record_confidence = record.get_overall_confidence()
            total_confidence += record_confidence
            
            if record_confidence >= 0.7:
                high_confidence_count += 1
            
            # Count successful field extractions
            for field_name in HMORecord.get_field_names():
                field_value = getattr(record, field_name, None)
                if field_value and str(field_value).strip():
                    field_extraction_counts[field_name] += 1
        
        # Calculate processing time
        processing_time = 0.0
        if self.processing_start_time and self.processing_end_time:
            processing_time = (self.processing_end_time - self.processing_start_time).total_seconds()
        
        # Update quality metrics
        self.quality_metrics.update({
            'total_records_found': total_records,
            'records_with_high_confidence': high_confidence_count,
            'records_flagged_for_review': len(self.flagged_records),
            'average_confidence_score': total_confidence / total_records if total_records > 0 else 0.0,
            'field_extraction_rates': {
                field: (count / total_records) * 100 if total_records > 0 else 0.0
                for field, count in field_extraction_counts.items()
            },
            'processing_time_seconds': processing_time
        })
        
        self.overall_confidence = self.quality_metrics['average_confidence_score']
    
    def get_flagged_records(self) -> List[HMORecord]:
        """
        Get all records that are flagged for manual review.
        
        Returns:
            List[HMORecord]: Records flagged for review
        """
        return [record for record in self.extracted_records if record.is_flagged_for_review()]
    
    def update_record(self, record_index: int, updated_record: HMORecord):
        """
        Update a specific record in the session.
        
        Args:
            record_index: Index of the record to update
            updated_record: Updated HMORecord
        """
        if 0 <= record_index < len(self.extracted_records):
            self.extracted_records[record_index] = updated_record
            # Recalculate metrics after update
            self.calculate_quality_metrics()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert session to dictionary format for JSON serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the session
        """
        return {
            'session_id': self.session_id,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'file_path': self.file_path,
            'upload_timestamp': self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            'processing_status': self.processing_status,
            'processing_start_time': self.processing_start_time.isoformat() if self.processing_start_time else None,
            'processing_end_time': self.processing_end_time.isoformat() if self.processing_end_time else None,
            'total_records': self.total_records,
            'flagged_records': self.flagged_records,
            'quality_metrics': self.quality_metrics,
            'overall_confidence': self.overall_confidence,
            'extraction_errors': self.extraction_errors,
            'column_mappings': self.column_mappings,
            'processing_config': self.processing_config,
            'extracted_records': [record.to_dict() for record in self.extracted_records]
        }


class SessionManager:
    """
    Manages ProcessingSession persistence with SQLite database.
    """
    
    def __init__(self, db_path: str = "processing_sessions.db"):
        """
        Initialize SessionManager with database path.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS processing_sessions (
                    session_id TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    file_size INTEGER,
                    file_path TEXT,
                    upload_timestamp TEXT,
                    processing_status TEXT,
                    processing_start_time TEXT,
                    processing_end_time TEXT,
                    total_records INTEGER DEFAULT 0,
                    overall_confidence REAL DEFAULT 0.0,
                    quality_metrics TEXT,
                    extraction_errors TEXT,
                    column_mappings TEXT,
                    processing_config TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS extracted_records (
                    record_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    record_index INTEGER,
                    record_data TEXT,
                    confidence_scores TEXT,
                    is_flagged BOOLEAN DEFAULT 0,
                    review_status TEXT DEFAULT 'pending',
                    reviewer_notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES processing_sessions(session_id)
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_session_status 
                ON processing_sessions(processing_status)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_record_session 
                ON extracted_records(session_id)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_record_flagged 
                ON extracted_records(is_flagged)
            ''')
    
    def save_session(self, session: ProcessingSession) -> bool:
        """
        Save or update a processing session in the database.
        
        Args:
            session: ProcessingSession to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Save session metadata
                conn.execute('''
                    INSERT OR REPLACE INTO processing_sessions (
                        session_id, file_name, file_size, file_path, upload_timestamp,
                        processing_status, processing_start_time, processing_end_time,
                        total_records, overall_confidence, quality_metrics,
                        extraction_errors, column_mappings, processing_config, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    session.session_id,
                    session.file_name,
                    session.file_size,
                    session.file_path,
                    session.upload_timestamp.isoformat() if session.upload_timestamp else None,
                    session.processing_status,
                    session.processing_start_time.isoformat() if session.processing_start_time else None,
                    session.processing_end_time.isoformat() if session.processing_end_time else None,
                    session.total_records,
                    session.overall_confidence,
                    json.dumps(session.quality_metrics),
                    json.dumps(session.extraction_errors),
                    json.dumps(session.column_mappings),
                    json.dumps(session.processing_config)
                ))
                
                # Delete existing records for this session
                conn.execute('DELETE FROM extracted_records WHERE session_id = ?', (session.session_id,))
                
                # Save extracted records
                for i, record in enumerate(session.extracted_records):
                    record_id = f"{session.session_id}_{i}"
                    is_flagged = record.is_flagged_for_review()
                    
                    conn.execute('''
                        INSERT INTO extracted_records (
                            record_id, session_id, record_index, record_data,
                            confidence_scores, is_flagged
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        record_id,
                        session.session_id,
                        i,
                        json.dumps(record.to_dict()),
                        json.dumps(record.confidence_scores),
                        is_flagged
                    ))
                
                return True
                
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
    
    def load_session(self, session_id: str) -> Optional[ProcessingSession]:
        """
        Load a processing session from the database.
        
        Args:
            session_id: ID of the session to load
            
        Returns:
            ProcessingSession or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Load session metadata
                cursor = conn.execute(
                    'SELECT * FROM processing_sessions WHERE session_id = ?',
                    (session_id,)
                )
                session_row = cursor.fetchone()
                
                if not session_row:
                    return None
                
                # Create session object
                session = ProcessingSession(
                    session_id=session_row['session_id'],
                    file_name=session_row['file_name'],
                    file_size=session_row['file_size'] or 0,
                    file_path=session_row['file_path'] or "",
                    upload_timestamp=datetime.fromisoformat(session_row['upload_timestamp']) if session_row['upload_timestamp'] else datetime.now(),
                    processing_status=session_row['processing_status'],
                    processing_start_time=datetime.fromisoformat(session_row['processing_start_time']) if session_row['processing_start_time'] else None,
                    processing_end_time=datetime.fromisoformat(session_row['processing_end_time']) if session_row['processing_end_time'] else None,
                    total_records=session_row['total_records'] or 0,
                    overall_confidence=session_row['overall_confidence'] or 0.0,
                    quality_metrics=json.loads(session_row['quality_metrics']) if session_row['quality_metrics'] else {},
                    extraction_errors=json.loads(session_row['extraction_errors']) if session_row['extraction_errors'] else [],
                    column_mappings=json.loads(session_row['column_mappings']) if session_row['column_mappings'] else {},
                    processing_config=json.loads(session_row['processing_config']) if session_row['processing_config'] else {}
                )
                
                # Load extracted records
                cursor = conn.execute('''
                    SELECT * FROM extracted_records 
                    WHERE session_id = ? 
                    ORDER BY record_index
                ''', (session_id,))
                
                records = []
                flagged_records = []
                
                for record_row in cursor.fetchall():
                    record_data = json.loads(record_row['record_data'])
                    record = HMORecord.from_dict(record_data)
                    records.append(record)
                    
                    if record_row['is_flagged']:
                        flagged_records.append(record_row['record_id'])
                
                session.extracted_records = records
                session.flagged_records = flagged_records
                
                return session
                
        except Exception as e:
            print(f"Error loading session: {e}")
            return None
    
    def list_sessions(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List processing sessions with optional status filter.
        
        Args:
            status: Optional status filter
            limit: Maximum number of sessions to return
            
        Returns:
            List of session summaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if status:
                    cursor = conn.execute('''
                        SELECT session_id, file_name, processing_status, upload_timestamp,
                               total_records, overall_confidence
                        FROM processing_sessions 
                        WHERE processing_status = ?
                        ORDER BY upload_timestamp DESC
                        LIMIT ?
                    ''', (status, limit))
                else:
                    cursor = conn.execute('''
                        SELECT session_id, file_name, processing_status, upload_timestamp,
                               total_records, overall_confidence
                        FROM processing_sessions 
                        ORDER BY upload_timestamp DESC
                        LIMIT ?
                    ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            print(f"Error listing sessions: {e}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a processing session and its records.
        
        Args:
            session_id: ID of the session to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM extracted_records WHERE session_id = ?', (session_id,))
                conn.execute('DELETE FROM processing_sessions WHERE session_id = ?', (session_id,))
                return True
                
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """
        Clean up sessions older than specified days.
        
        Args:
            days_old: Number of days after which to delete sessions
            
        Returns:
            int: Number of sessions deleted
        """
        try:
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT session_id FROM processing_sessions 
                    WHERE upload_timestamp < ?
                ''', (cutoff_date.isoformat(),))
                
                old_sessions = [row[0] for row in cursor.fetchall()]
                
                for session_id in old_sessions:
                    conn.execute('DELETE FROM extracted_records WHERE session_id = ?', (session_id,))
                    conn.execute('DELETE FROM processing_sessions WHERE session_id = ?', (session_id,))
                
                return len(old_sessions)
                
        except Exception as e:
            print(f"Error cleaning up sessions: {e}")
            return 0
    
    def create_session(self, session_data: Dict[str, Any]) -> bool:
        """
        Create a new processing session.
        
        Args:
            session_data: Session data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO processing_sessions (
                        session_id, file_name, file_size, file_path, upload_timestamp,
                        processing_status, processing_config
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_data['session_id'],
                    session_data['file_name'],
                    session_data['file_size'],
                    session_data['file_path'],
                    session_data['upload_timestamp'],
                    session_data['processing_status'],
                    json.dumps(session_data.get('processing_options', {}))
                ))
                return True
                
        except Exception as e:
            print(f"Error creating session: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by ID.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Session data if found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    'SELECT * FROM processing_sessions WHERE session_id = ?',
                    (session_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            print(f"Error getting session: {e}")
            return None
    
    def update_session_status(self, session_id: str, status: str, stage: Optional[str] = None, error_message: Optional[str] = None) -> bool:
        """
        Update session status and stage.
        
        Args:
            session_id: Session ID to update
            status: New processing status
            stage: Current processing stage
            error_message: Error message if status is error
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Update basic status
                conn.execute('''
                    UPDATE processing_sessions 
                    SET processing_status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                ''', (status, session_id))
                
                # Add stage and error info if provided
                if stage or error_message:
                    # Get current processing_config
                    cursor = conn.execute(
                        'SELECT processing_config FROM processing_sessions WHERE session_id = ?',
                        (session_id,)
                    )
                    row = cursor.fetchone()
                    
                    if row and row[0]:
                        config = json.loads(row[0])
                    else:
                        config = {}
                    
                    if stage:
                        config['current_stage'] = stage
                    if error_message:
                        config['error_message'] = error_message
                    
                    config['last_updated'] = datetime.now().isoformat()
                    
                    conn.execute('''
                        UPDATE processing_sessions 
                        SET processing_config = ?
                        WHERE session_id = ?
                    ''', (json.dumps(config), session_id))
                
                return True
                
        except Exception as e:
            print(f"Error updating session status: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dict[str, Any]: Database statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get total sessions
                cursor = conn.execute('SELECT COUNT(*) FROM processing_sessions')
                total_sessions = cursor.fetchone()[0]
                
                # Get total records
                cursor = conn.execute('SELECT COUNT(*) FROM extracted_records')
                total_records = cursor.fetchone()[0]
                
                # Get database file size
                db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
                
                return {
                    'total_sessions': total_sessions,
                    'total_records': total_records,
                    'database_size_bytes': db_size,
                    'database_path': self.db_path
                }
                
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return {
                'total_sessions': 0,
                'total_records': 0,
                'database_size_bytes': 0,
                'error': str(e)
            }