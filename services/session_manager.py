"""
SQLite-based session management system for document processing pipeline.
Handles session persistence, record storage, and cleanup operations.
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from contextlib import contextmanager
from loguru import logger

from models.processing_session import ProcessingSession
from models.hmo_record import HMORecord


class SessionManager:
    """SQLite-based session manager for processing sessions and records"""
    
    def __init__(self, db_path: str = "processing_sessions.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create processing_sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_sessions (
                    session_id TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    file_size INTEGER,
                    upload_timestamp DATETIME,
                    processing_status TEXT,
                    quality_score REAL,
                    total_records INTEGER DEFAULT 0,
                    flagged_records INTEGER DEFAULT 0,
                    column_mappings TEXT,
                    processing_config TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create extracted_records table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extracted_records (
                    record_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    record_data TEXT,
                    confidence_scores TEXT,
                    is_flagged BOOLEAN DEFAULT 0,
                    review_status TEXT DEFAULT 'pending',
                    reviewer_notes TEXT,
                    original_data TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES processing_sessions(session_id)
                )
            """)
            
            # Create column_mappings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS column_mappings (
                    mapping_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    user_column_name TEXT,
                    system_field_name TEXT,
                    data_type TEXT,
                    validation_rules TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES processing_sessions(session_id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_status 
                ON processing_sessions(processing_status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_records_session 
                ON extracted_records(session_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_records_flagged 
                ON extracted_records(is_flagged)
            """)
            
            conn.commit()
            logger.info(f"Initialized database at {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def create_session(self, file_name: str, file_size: int, 
                      column_mappings: Dict[str, str] = None,
                      processing_config: Dict[str, Any] = None) -> str:
        """Create a new processing session"""
        session_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO processing_sessions 
                (session_id, file_name, file_size, upload_timestamp, 
                 processing_status, column_mappings, processing_config)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                file_name,
                file_size,
                datetime.now().isoformat(),
                'pending',
                json.dumps(column_mappings) if column_mappings else None,
                json.dumps(processing_config) if processing_config else None
            ))
            
            conn.commit()
            logger.info(f"Created session {session_id} for file {file_name}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ProcessingSession]:
        """Retrieve a processing session by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM processing_sessions WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Convert row to ProcessingSession object
            session_data = dict(row)
            
            # Parse JSON fields
            if session_data.get('column_mappings'):
                session_data['column_mappings'] = json.loads(session_data['column_mappings'])
            
            if session_data.get('processing_config'):
                session_data['processing_config'] = json.loads(session_data['processing_config'])
            
            # Get associated records
            session_data['extracted_records'] = self.get_session_records(session_id)
            
            return ProcessingSession.from_dict(session_data)
    
    def update_session_status(self, session_id: str, status: str, 
                             quality_score: float = None) -> bool:
        """Update session processing status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            update_fields = ['processing_status = ?', 'updated_at = ?']
            values = [status, datetime.now().isoformat()]
            
            if quality_score is not None:
                update_fields.append('quality_score = ?')
                values.append(quality_score)
            
            values.append(session_id)
            
            cursor.execute(f"""
                UPDATE processing_sessions 
                SET {', '.join(update_fields)}
                WHERE session_id = ?
            """, values)
            
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                logger.info(f"Updated session {session_id} status to {status}")
            
            return success
    
    def update_session_metrics(self, session_id: str, total_records: int, 
                              flagged_records: int) -> bool:
        """Update session record counts"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE processing_sessions 
                SET total_records = ?, flagged_records = ?, updated_at = ?
                WHERE session_id = ?
            """, (total_records, flagged_records, datetime.now().isoformat(), session_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            return success
    
    def store_extracted_records(self, session_id: str, 
                               records: List[HMORecord]) -> bool:
        """Store extracted records for a session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for record in records:
                record_id = str(uuid.uuid4())
                
                cursor.execute("""
                    INSERT INTO extracted_records 
                    (record_id, session_id, record_data, confidence_scores, 
                     is_flagged, original_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    record_id,
                    session_id,
                    json.dumps(record.to_dict()),
                    json.dumps(record.confidence_scores),
                    record.is_flagged_for_review(),
                    json.dumps(record.to_dict())  # Store original for audit trail
                ))
            
            conn.commit()
            logger.info(f"Stored {len(records)} records for session {session_id}")
            return True
    
    def get_session_records(self, session_id: str, 
                           flagged_only: bool = False) -> List[HMORecord]:
        """Get all records for a session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM extracted_records 
                WHERE session_id = ?
            """
            params = [session_id]
            
            if flagged_only:
                query += " AND is_flagged = 1"
            
            query += " ORDER BY created_at"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            records = []
            for row in rows:
                record_data = json.loads(row['record_data'])
                confidence_scores = json.loads(row['confidence_scores']) if row['confidence_scores'] else {}
                
                record = HMORecord.from_dict(record_data)
                record.confidence_scores = confidence_scores
                records.append(record)
            
            return records
    
    def update_record(self, record_id: str, updated_data: Dict[str, Any], 
                     reviewer_notes: str = None) -> bool:
        """Update an extracted record with manual corrections"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current record
            cursor.execute("""
                SELECT record_data FROM extracted_records WHERE record_id = ?
            """, (record_id,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            current_data = json.loads(row['record_data'])
            current_data.update(updated_data)
            
            cursor.execute("""
                UPDATE extracted_records 
                SET record_data = ?, review_status = 'reviewed', 
                    reviewer_notes = ?, updated_at = ?
                WHERE record_id = ?
            """, (
                json.dumps(current_data),
                reviewer_notes,
                datetime.now().isoformat(),
                record_id
            ))
            
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                logger.info(f"Updated record {record_id}")
            
            return success
    
    def get_sessions_by_status(self, status: str) -> List[ProcessingSession]:
        """Get all sessions with a specific status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM processing_sessions 
                WHERE processing_status = ?
                ORDER BY created_at DESC
            """, (status,))
            
            rows = cursor.fetchall()
            sessions = []
            
            for row in rows:
                session_data = dict(row)
                
                # Parse JSON fields
                if session_data.get('column_mappings'):
                    session_data['column_mappings'] = json.loads(session_data['column_mappings'])
                
                if session_data.get('processing_config'):
                    session_data['processing_config'] = json.loads(session_data['processing_config'])
                
                sessions.append(ProcessingSession.from_dict(session_data))
            
            return sessions
    
    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """Clean up sessions older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get sessions to delete
            cursor.execute("""
                SELECT session_id FROM processing_sessions 
                WHERE created_at < ?
            """, (cutoff_date.isoformat(),))
            
            session_ids = [row[0] for row in cursor.fetchall()]
            
            if not session_ids:
                return 0
            
            # Delete records first (foreign key constraint)
            placeholders = ','.join(['?' for _ in session_ids])
            cursor.execute(f"""
                DELETE FROM extracted_records 
                WHERE session_id IN ({placeholders})
            """, session_ids)
            
            cursor.execute(f"""
                DELETE FROM column_mappings 
                WHERE session_id IN ({placeholders})
            """, session_ids)
            
            # Delete sessions
            cursor.execute(f"""
                DELETE FROM processing_sessions 
                WHERE session_id IN ({placeholders})
            """, session_ids)
            
            conn.commit()
            
            logger.info(f"Cleaned up {len(session_ids)} old sessions")
            return len(session_ids)
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Session counts by status
            cursor.execute("""
                SELECT processing_status, COUNT(*) 
                FROM processing_sessions 
                GROUP BY processing_status
            """)
            status_counts = dict(cursor.fetchall())
            
            # Total records
            cursor.execute("SELECT COUNT(*) FROM extracted_records")
            total_records = cursor.fetchone()[0]
            
            # Flagged records
            cursor.execute("SELECT COUNT(*) FROM extracted_records WHERE is_flagged = 1")
            flagged_records = cursor.fetchone()[0]
            
            # Database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()[0]
            
            return {
                'session_counts': status_counts,
                'total_records': total_records,
                'flagged_records': flagged_records,
                'database_size_bytes': db_size,
                'database_path': str(self.db_path)
            }