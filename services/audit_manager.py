"""
Audit management system for HMO data processing.

Provides tracking for flagged records, review workflow management,
and audit trail for manual corrections.
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sqlite3
import json
import uuid
from pathlib import Path
from models.hmo_record import HMORecord
from services.data_validator import ValidationResult


class ReviewStatus(Enum):
    """Status of record review process."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class AuditAction(Enum):
    """Types of audit actions."""
    FLAGGED = "flagged"
    REVIEWED = "reviewed"
    CORRECTED = "corrected"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMMENT_ADDED = "comment_added"


@dataclass
class AuditRecord:
    """Audit record for tracking changes and reviews."""
    audit_id: str
    record_id: str
    session_id: str
    action: AuditAction
    timestamp: datetime
    reviewer: str
    original_data: Dict[str, Any]
    modified_data: Optional[Dict[str, Any]] = None
    comments: str = ""
    confidence_before: float = 0.0
    confidence_after: Optional[float] = None
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class FlaggedRecord:
    """Record flagged for manual review."""
    record_id: str
    session_id: str
    hmo_record: HMORecord
    flag_reason: str
    flag_timestamp: datetime
    review_status: ReviewStatus
    assigned_reviewer: Optional[str] = None
    review_started: Optional[datetime] = None
    review_completed: Optional[datetime] = None
    audit_trail: List[AuditRecord] = field(default_factory=list)


class AuditManager:
    """
    Audit management system for tracking flagged records and manual reviews.
    
    Provides functionality for:
    - Tracking flagged records
    - Managing review workflow and status
    - Maintaining audit trail for manual corrections
    - Generating audit reports
    """
    
    def __init__(self, db_path: str = "audit_data.db"):
        """
        Initialize audit manager with database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()
        self.flagged_records: Dict[str, FlaggedRecord] = {}
        self._load_flagged_records()
    
    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create flagged_records table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flagged_records (
                    record_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    hmo_data JSON NOT NULL,
                    flag_reason TEXT NOT NULL,
                    flag_timestamp TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    assigned_reviewer TEXT,
                    review_started TEXT,
                    review_completed TEXT
                )
            """)
            
            # Create audit_trail table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    audit_id TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    original_data JSON NOT NULL,
                    modified_data JSON,
                    comments TEXT,
                    confidence_before REAL,
                    confidence_after REAL,
                    validation_errors JSON,
                    FOREIGN KEY (record_id) REFERENCES flagged_records(record_id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON flagged_records(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_review_status ON flagged_records(review_status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_record_id ON audit_trail(record_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_trail(timestamp)")
            
            conn.commit()
    
    def flag_record(
        self, 
        record: HMORecord, 
        session_id: str, 
        reason: str,
        reviewer: str = "system"
    ) -> str:
        """
        Flag a record for manual review.
        
        Args:
            record: HMO record to flag
            session_id: Processing session ID
            reason: Reason for flagging
            reviewer: Who flagged the record
            
        Returns:
            str: Unique record ID for the flagged record
        """
        record_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Create flagged record
        flagged_record = FlaggedRecord(
            record_id=record_id,
            session_id=session_id,
            hmo_record=record,
            flag_reason=reason,
            flag_timestamp=timestamp,
            review_status=ReviewStatus.PENDING
        )
        
        # Create audit trail entry
        audit_record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            record_id=record_id,
            session_id=session_id,
            action=AuditAction.FLAGGED,
            timestamp=timestamp,
            reviewer=reviewer,
            original_data=record.to_dict(),
            comments=reason,
            confidence_before=record.get_overall_confidence()
        )
        
        flagged_record.audit_trail.append(audit_record)
        self.flagged_records[record_id] = flagged_record
        
        # Save to database
        self._save_flagged_record(flagged_record)
        self._save_audit_record(audit_record)
        
        return record_id
    
    def assign_reviewer(self, record_id: str, reviewer: str) -> bool:
        """
        Assign a reviewer to a flagged record.
        
        Args:
            record_id: ID of the flagged record
            reviewer: Username of the assigned reviewer
            
        Returns:
            bool: True if assignment successful
        """
        if record_id not in self.flagged_records:
            return False
        
        flagged_record = self.flagged_records[record_id]
        flagged_record.assigned_reviewer = reviewer
        flagged_record.review_status = ReviewStatus.IN_REVIEW
        flagged_record.review_started = datetime.now()
        
        # Create audit trail entry
        audit_record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            record_id=record_id,
            session_id=flagged_record.session_id,
            action=AuditAction.REVIEWED,
            timestamp=datetime.now(),
            reviewer=reviewer,
            original_data=flagged_record.hmo_record.to_dict(),
            comments=f"Review assigned to {reviewer}"
        )
        
        flagged_record.audit_trail.append(audit_record)
        
        # Update database
        self._update_flagged_record(flagged_record)
        self._save_audit_record(audit_record)
        
        return True
    
    def update_record(
        self, 
        record_id: str, 
        updates: Dict[str, Any], 
        reviewer: str,
        comments: str = ""
    ) -> bool:
        """
        Update a flagged record with corrections.
        
        Args:
            record_id: ID of the record to update
            updates: Dictionary of field updates
            reviewer: Username of the reviewer making changes
            comments: Optional comments about the changes
            
        Returns:
            bool: True if update successful
        """
        if record_id not in self.flagged_records:
            return False
        
        flagged_record = self.flagged_records[record_id]
        original_data = flagged_record.hmo_record.to_dict()
        
        # Apply updates to the record
        for field, value in updates.items():
            if hasattr(flagged_record.hmo_record, field):
                setattr(flagged_record.hmo_record, field, value)
        
        # Recalculate confidence scores after updates
        flagged_record.hmo_record.validate_all_fields()
        new_confidence = flagged_record.hmo_record.get_overall_confidence()
        
        # Create audit trail entry
        audit_record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            record_id=record_id,
            session_id=flagged_record.session_id,
            action=AuditAction.CORRECTED,
            timestamp=datetime.now(),
            reviewer=reviewer,
            original_data=original_data,
            modified_data=flagged_record.hmo_record.to_dict(),
            comments=comments,
            confidence_before=original_data.get('confidence_scores', {}).get('overall', 0.0),
            confidence_after=new_confidence
        )
        
        flagged_record.audit_trail.append(audit_record)
        
        # Update database
        self._update_flagged_record(flagged_record)
        self._save_audit_record(audit_record)
        
        return True
    
    def approve_record(self, record_id: str, reviewer: str, comments: str = "") -> bool:
        """
        Approve a reviewed record.
        
        Args:
            record_id: ID of the record to approve
            reviewer: Username of the approving reviewer
            comments: Optional approval comments
            
        Returns:
            bool: True if approval successful
        """
        if record_id not in self.flagged_records:
            return False
        
        flagged_record = self.flagged_records[record_id]
        flagged_record.review_status = ReviewStatus.APPROVED
        flagged_record.review_completed = datetime.now()
        
        # Create audit trail entry
        audit_record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            record_id=record_id,
            session_id=flagged_record.session_id,
            action=AuditAction.APPROVED,
            timestamp=datetime.now(),
            reviewer=reviewer,
            original_data=flagged_record.hmo_record.to_dict(),
            comments=comments
        )
        
        flagged_record.audit_trail.append(audit_record)
        
        # Update database
        self._update_flagged_record(flagged_record)
        self._save_audit_record(audit_record)
        
        return True
    
    def reject_record(self, record_id: str, reviewer: str, reason: str) -> bool:
        """
        Reject a reviewed record.
        
        Args:
            record_id: ID of the record to reject
            reviewer: Username of the rejecting reviewer
            reason: Reason for rejection
            
        Returns:
            bool: True if rejection successful
        """
        if record_id not in self.flagged_records:
            return False
        
        flagged_record = self.flagged_records[record_id]
        flagged_record.review_status = ReviewStatus.REJECTED
        flagged_record.review_completed = datetime.now()
        
        # Create audit trail entry
        audit_record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            record_id=record_id,
            session_id=flagged_record.session_id,
            action=AuditAction.REJECTED,
            timestamp=datetime.now(),
            reviewer=reviewer,
            original_data=flagged_record.hmo_record.to_dict(),
            comments=reason
        )
        
        flagged_record.audit_trail.append(audit_record)
        
        # Update database
        self._update_flagged_record(flagged_record)
        self._save_audit_record(audit_record)
        
        return True
    
    def add_comment(self, record_id: str, reviewer: str, comment: str) -> bool:
        """
        Add a comment to a flagged record.
        
        Args:
            record_id: ID of the record
            reviewer: Username of the commenter
            comment: Comment text
            
        Returns:
            bool: True if comment added successfully
        """
        if record_id not in self.flagged_records:
            return False
        
        flagged_record = self.flagged_records[record_id]
        
        # Create audit trail entry
        audit_record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            record_id=record_id,
            session_id=flagged_record.session_id,
            action=AuditAction.COMMENT_ADDED,
            timestamp=datetime.now(),
            reviewer=reviewer,
            original_data=flagged_record.hmo_record.to_dict(),
            comments=comment
        )
        
        flagged_record.audit_trail.append(audit_record)
        
        # Save to database
        self._save_audit_record(audit_record)
        
        return True
    
    def get_flagged_records(
        self, 
        session_id: Optional[str] = None,
        status: Optional[ReviewStatus] = None,
        reviewer: Optional[str] = None
    ) -> List[FlaggedRecord]:
        """
        Get flagged records with optional filtering.
        
        Args:
            session_id: Filter by session ID
            status: Filter by review status
            reviewer: Filter by assigned reviewer
            
        Returns:
            List[FlaggedRecord]: Filtered list of flagged records
        """
        records = list(self.flagged_records.values())
        
        if session_id:
            records = [r for r in records if r.session_id == session_id]
        
        if status:
            records = [r for r in records if r.review_status == status]
        
        if reviewer:
            records = [r for r in records if r.assigned_reviewer == reviewer]
        
        return records
    
    def get_audit_trail(self, record_id: str) -> List[AuditRecord]:
        """
        Get complete audit trail for a record.
        
        Args:
            record_id: ID of the record
            
        Returns:
            List[AuditRecord]: Chronological list of audit records
        """
        if record_id not in self.flagged_records:
            return []
        
        return sorted(
            self.flagged_records[record_id].audit_trail,
            key=lambda x: x.timestamp
        )
    
    def get_session_audit_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get audit summary for a processing session.
        
        Args:
            session_id: Processing session ID
            
        Returns:
            Dict[str, Any]: Audit summary statistics
        """
        session_records = [r for r in self.flagged_records.values() if r.session_id == session_id]
        
        if not session_records:
            return {}
        
        status_counts = {}
        for status in ReviewStatus:
            status_counts[status.value] = sum(1 for r in session_records if r.review_status == status)
        
        # Calculate review times
        completed_records = [r for r in session_records if r.review_completed]
        avg_review_time = None
        
        if completed_records:
            review_times = []
            for record in completed_records:
                if record.review_started and record.review_completed:
                    duration = (record.review_completed - record.review_started).total_seconds() / 3600  # hours
                    review_times.append(duration)
            
            if review_times:
                avg_review_time = sum(review_times) / len(review_times)
        
        # Count corrections made
        total_corrections = 0
        for record in session_records:
            corrections = [a for a in record.audit_trail if a.action == AuditAction.CORRECTED]
            total_corrections += len(corrections)
        
        return {
            'session_id': session_id,
            'total_flagged': len(session_records),
            'status_breakdown': status_counts,
            'average_review_time_hours': avg_review_time,
            'total_corrections_made': total_corrections,
            'completion_rate': status_counts.get('approved', 0) / len(session_records) if session_records else 0
        }
    
    def export_audited_data(self, session_id: str, include_rejected: bool = False) -> List[Dict[str, Any]]:
        """
        Export audited data for a session.
        
        Args:
            session_id: Processing session ID
            include_rejected: Whether to include rejected records
            
        Returns:
            List[Dict[str, Any]]: List of audited record data
        """
        session_records = [r for r in self.flagged_records.values() if r.session_id == session_id]
        
        exported_data = []
        
        for record in session_records:
            # Include approved records and optionally rejected ones
            if record.review_status == ReviewStatus.APPROVED or (include_rejected and record.review_status == ReviewStatus.REJECTED):
                record_data = record.hmo_record.to_dict()
                
                # Add audit metadata
                record_data['_audit_metadata'] = {
                    'record_id': record.record_id,
                    'flag_reason': record.flag_reason,
                    'review_status': record.review_status.value,
                    'reviewer': record.assigned_reviewer,
                    'review_completed': record.review_completed.isoformat() if record.review_completed else None,
                    'corrections_made': len([a for a in record.audit_trail if a.action == AuditAction.CORRECTED])
                }
                
                exported_data.append(record_data)
        
        return exported_data
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """
        Get audit statistics from the database.
        
        Returns:
            Dict[str, Any]: Audit statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get total flagged records
            cursor.execute("SELECT COUNT(*) FROM flagged_records")
            total_flagged = cursor.fetchone()[0]
            
            # Get status breakdown
            cursor.execute("SELECT review_status, COUNT(*) FROM flagged_records GROUP BY review_status")
            status_breakdown = {status: count for status, count in cursor.fetchall()}
            
            return {
                'total_flagged_records': total_flagged,
                'status_breakdown': status_breakdown
            }
    
    def generate_audit_report(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive audit report.
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            Dict[str, Any]: Comprehensive audit report
        """
        records = self.get_flagged_records(session_id=session_id)
        
        if not records:
            return {'message': 'No flagged records found'}
        
        # Basic statistics
        total_records = len(records)
        status_counts = {}
        for status in ReviewStatus:
            status_counts[status.value] = sum(1 for r in records if r.review_status == status)
        
        # Reviewer statistics
        reviewer_stats = {}
        for record in records:
            if record.assigned_reviewer:
                if record.assigned_reviewer not in reviewer_stats:
                    reviewer_stats[record.assigned_reviewer] = {
                        'assigned': 0,
                        'completed': 0,
                        'approved': 0,
                        'rejected': 0
                    }
                
                reviewer_stats[record.assigned_reviewer]['assigned'] += 1
                
                if record.review_status in [ReviewStatus.APPROVED, ReviewStatus.REJECTED]:
                    reviewer_stats[record.assigned_reviewer]['completed'] += 1
                    
                    if record.review_status == ReviewStatus.APPROVED:
                        reviewer_stats[record.assigned_reviewer]['approved'] += 1
                    else:
                        reviewer_stats[record.assigned_reviewer]['rejected'] += 1
        
        # Flag reason analysis
        flag_reasons = {}
        for record in records:
            reason = record.flag_reason
            flag_reasons[reason] = flag_reasons.get(reason, 0) + 1
        
        # Correction analysis
        correction_stats = {
            'total_corrections': 0,
            'records_with_corrections': 0,
            'most_corrected_fields': {}
        }
        
        for record in records:
            corrections = [a for a in record.audit_trail if a.action == AuditAction.CORRECTED]
            if corrections:
                correction_stats['records_with_corrections'] += 1
                correction_stats['total_corrections'] += len(corrections)
                
                # Analyze which fields were corrected
                for correction in corrections:
                    if correction.modified_data and correction.original_data:
                        for field, new_value in correction.modified_data.items():
                            if field in correction.original_data and correction.original_data[field] != new_value:
                                correction_stats['most_corrected_fields'][field] = correction_stats['most_corrected_fields'].get(field, 0) + 1
        
        return {
            'report_generated': datetime.now().isoformat(),
            'session_id': session_id,
            'summary': {
                'total_flagged_records': total_records,
                'status_breakdown': status_counts,
                'completion_rate': (status_counts.get('approved', 0) + status_counts.get('rejected', 0)) / total_records if total_records > 0 else 0
            },
            'reviewer_performance': reviewer_stats,
            'flag_analysis': {
                'most_common_reasons': sorted(flag_reasons.items(), key=lambda x: x[1], reverse=True)[:5]
            },
            'correction_analysis': correction_stats
        }
    
    def _save_flagged_record(self, flagged_record: FlaggedRecord) -> None:
        """Save flagged record to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO flagged_records 
                (record_id, session_id, hmo_data, flag_reason, flag_timestamp, 
                 review_status, assigned_reviewer, review_started, review_completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                flagged_record.record_id,
                flagged_record.session_id,
                json.dumps(flagged_record.hmo_record.to_dict()),
                flagged_record.flag_reason,
                flagged_record.flag_timestamp.isoformat(),
                flagged_record.review_status.value,
                flagged_record.assigned_reviewer,
                flagged_record.review_started.isoformat() if flagged_record.review_started else None,
                flagged_record.review_completed.isoformat() if flagged_record.review_completed else None
            ))
            conn.commit()
    
    def _update_flagged_record(self, flagged_record: FlaggedRecord) -> None:
        """Update existing flagged record in database."""
        self._save_flagged_record(flagged_record)  # INSERT OR REPLACE handles updates
    
    def _save_audit_record(self, audit_record: AuditRecord) -> None:
        """Save audit record to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_trail 
                (audit_id, record_id, session_id, action, timestamp, reviewer,
                 original_data, modified_data, comments, confidence_before, 
                 confidence_after, validation_errors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                audit_record.audit_id,
                audit_record.record_id,
                audit_record.session_id,
                audit_record.action.value,
                audit_record.timestamp.isoformat(),
                audit_record.reviewer,
                json.dumps(audit_record.original_data),
                json.dumps(audit_record.modified_data) if audit_record.modified_data else None,
                audit_record.comments,
                audit_record.confidence_before,
                audit_record.confidence_after,
                json.dumps(audit_record.validation_errors)
            ))
            conn.commit()
    
    def _load_flagged_records(self) -> None:
        """Load flagged records from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Load flagged records
                cursor.execute("SELECT * FROM flagged_records")
                for row in cursor.fetchall():
                    record_id, session_id, hmo_data_json, flag_reason, flag_timestamp, review_status, assigned_reviewer, review_started, review_completed = row
                    
                    # Parse data
                    hmo_data = json.loads(hmo_data_json)
                    hmo_record = HMORecord.from_dict(hmo_data)
                    
                    flagged_record = FlaggedRecord(
                        record_id=record_id,
                        session_id=session_id,
                        hmo_record=hmo_record,
                        flag_reason=flag_reason,
                        flag_timestamp=datetime.fromisoformat(flag_timestamp),
                        review_status=ReviewStatus(review_status),
                        assigned_reviewer=assigned_reviewer,
                        review_started=datetime.fromisoformat(review_started) if review_started else None,
                        review_completed=datetime.fromisoformat(review_completed) if review_completed else None
                    )
                    
                    self.flagged_records[record_id] = flagged_record
                
                # Load audit trail for each record
                for record_id in self.flagged_records:
                    cursor.execute("SELECT * FROM audit_trail WHERE record_id = ? ORDER BY timestamp", (record_id,))
                    
                    for audit_row in cursor.fetchall():
                        audit_id, _, session_id, action, timestamp, reviewer, original_data_json, modified_data_json, comments, confidence_before, confidence_after, validation_errors_json = audit_row
                        
                        audit_record = AuditRecord(
                            audit_id=audit_id,
                            record_id=record_id,
                            session_id=session_id,
                            action=AuditAction(action),
                            timestamp=datetime.fromisoformat(timestamp),
                            reviewer=reviewer,
                            original_data=json.loads(original_data_json),
                            modified_data=json.loads(modified_data_json) if modified_data_json else None,
                            comments=comments or "",
                            confidence_before=confidence_before or 0.0,
                            confidence_after=confidence_after,
                            validation_errors=json.loads(validation_errors_json) if validation_errors_json else []
                        )
                        
                        self.flagged_records[record_id].audit_trail.append(audit_record)
        
        except sqlite3.Error:
            # Database doesn't exist or is corrupted, start fresh
            pass