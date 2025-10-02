"""
Simple fallback processor for when the main processing pipeline fails.
Provides basic document processing capabilities to ensure the system always works.
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class SimpleProcessor:
    """
    Simple fallback processor that provides basic functionality.
    """
    
    def __init__(self):
        """Initialize simple processor."""
        self.processing_sessions = {}
        
    async def process_document_simple(
        self, 
        file_path: str, 
        session_id: str, 
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process document with simple fallback method.
        
        Args:
            file_path: Path to document
            session_id: Processing session ID
            options: Processing options
            
        Returns:
            Dict[str, Any]: Processing results
        """
        try:
            logger.info(f"Starting simple processing for session {session_id}")
            
            # Update session status
            self.processing_sessions[session_id] = {
                'status': 'processing',
                'current_stage': 'document_extraction',
                'progress': 0.1,
                'last_updated': datetime.now().isoformat()
            }
            
            # Try to extract basic text
            extracted_text = self._extract_text_simple(file_path)
            
            # Update progress
            self.processing_sessions[session_id].update({
                'current_stage': 'data_structuring',
                'progress': 0.5,
                'last_updated': datetime.now().isoformat()
            })
            
            # Create basic record
            records = self._create_basic_records(extracted_text, session_id)
            
            # Update progress
            self.processing_sessions[session_id].update({
                'current_stage': 'csv_generation',
                'progress': 0.8,
                'last_updated': datetime.now().isoformat()
            })
            
            # Generate CSV
            csv_content = self._generate_simple_csv(records)
            csv_filename = f"hmo_results_{session_id[:8]}.csv"
            csv_path = Path("sample_outputs") / csv_filename
            
            # Ensure output directory exists
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write CSV
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            
            # Final results
            results = {
                'session_id': session_id,
                'records': records,
                'total_records': len(records),
                'csv_filename': csv_filename,
                'csv_path': str(csv_path),
                'processing_metadata': {
                    'processor_type': 'simple_fallback',
                    'processing_time': datetime.now().isoformat(),
                    'fallback_used': True,
                    'average_confidence': 0.5  # Default confidence for fallback
                }
            }
            
            # Update final status
            self.processing_sessions[session_id].update({
                'status': 'completed',
                'current_stage': 'completed',
                'progress': 1.0,
                'last_updated': datetime.now().isoformat(),
                'results': results
            })
            
            logger.info(f"Simple processing completed for session {session_id}")
            return results
            
        except Exception as e:
            logger.error(f"Simple processing failed for session {session_id}: {e}")
            
            # Update error status
            self.processing_sessions[session_id] = {
                'status': 'error',
                'error_message': f"Simple processing failed: {str(e)}",
                'last_updated': datetime.now().isoformat()
            }
            
            # Return minimal error result
            return {
                'session_id': session_id,
                'records': [],
                'processing_metadata': {
                    'error': True,
                    'error_message': str(e),
                    'processor_type': 'simple_fallback'
                }
            }
    
    def _extract_text_simple(self, file_path: str) -> str:
        """Extract text using simple methods."""
        try:
            file_path = Path(file_path)
            
            if file_path.suffix.lower() == '.pdf':
                return self._extract_pdf_simple(file_path)
            elif file_path.suffix.lower() == '.docx':
                return self._extract_docx_simple(file_path)
            else:
                return f"Unsupported file format: {file_path.suffix}"
                
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return f"Text extraction failed: {str(e)}"
    
    def _extract_pdf_simple(self, file_path: Path) -> str:
        """Simple PDF text extraction."""
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
                return text.strip()
                
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return f"PDF extraction failed: {str(e)}"
    
    def _extract_docx_simple(self, file_path: Path) -> str:
        """Simple DOCX text extraction."""
        try:
            from docx import Document
            
            doc = Document(file_path)
            text = ""
            
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            return f"DOCX extraction failed: {str(e)}"
    
    def _create_basic_records(self, text: str, session_id: str) -> List[Dict[str, Any]]:
        """Create basic records from extracted text."""
        try:
            # Simple pattern matching for common HMO data
            lines = text.split('\n')
            records = []
            
            # Look for patterns that might indicate HMO data
            current_record = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Simple heuristics for HMO data
                if any(keyword in line.lower() for keyword in ['council', 'authority', 'borough']):
                    if current_record:
                        records.append(current_record)
                    current_record = {'council': line}
                
                elif any(keyword in line.lower() for keyword in ['hmo', 'reference', 'licence']):
                    current_record['reference'] = line
                
                elif any(keyword in line.lower() for keyword in ['address', 'property']):
                    current_record['hmo_address'] = line
                
                elif any(keyword in line.lower() for keyword in ['manager', 'holder']):
                    current_record['hmo_manager_name'] = line
                
                elif any(keyword in line.lower() for keyword in ['occupancy', 'persons']):
                    # Try to extract number
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        current_record['max_occupancy'] = int(numbers[0])
            
            # Add the last record
            if current_record:
                records.append(current_record)
            
            # If no structured records found, create a basic one
            if not records:
                records = [{
                    'council': 'Unknown Council',
                    'reference': f'EXTRACTED_{session_id[:8]}',
                    'hmo_address': 'Address not found in document',
                    'hmo_manager_name': 'Manager not specified',
                    'max_occupancy': 0,
                    'extraction_note': 'Basic extraction - manual review recommended'
                }]
            
            # Add confidence scores and metadata
            for i, record in enumerate(records):
                record.update({
                    'record_id': f"{session_id}_{i}",
                    'confidence_scores': {
                        'council': 0.5,
                        'reference': 0.5,
                        'hmo_address': 0.5,
                        'hmo_manager_name': 0.5,
                        'max_occupancy': 0.5
                    },
                    'extraction_method': 'simple_pattern_matching',
                    'needs_review': True
                })
            
            return records
            
        except Exception as e:
            logger.error(f"Record creation failed: {e}")
            return [{
                'council': 'Processing Error',
                'reference': f'ERROR_{session_id[:8]}',
                'error': str(e),
                'extraction_method': 'error_fallback'
            }]
    
    def _generate_simple_csv(self, records: List[Dict[str, Any]]) -> str:
        """Generate simple CSV from records."""
        try:
            if not records:
                return "council,reference,error\nNo Data,No Data,No records extracted\n"
            
            # Define CSV headers
            headers = [
                'council', 'reference', 'hmo_address', 'licence_start', 'licence_expiry',
                'max_occupancy', 'hmo_manager_name', 'licence_holder_name',
                'extraction_method', 'needs_review'
            ]
            
            # Create CSV content
            csv_lines = [','.join(headers)]
            
            for record in records:
                row = []
                for header in headers:
                    value = record.get(header, '')
                    # Clean value for CSV
                    if isinstance(value, str):
                        value = value.replace(',', ';').replace('\n', ' ').replace('\r', '')
                    row.append(str(value))
                
                csv_lines.append(','.join(row))
            
            return '\n'.join(csv_lines)
            
        except Exception as e:
            logger.error(f"CSV generation failed: {e}")
            return f"council,reference,error\nError,Error,CSV generation failed: {str(e)}\n"
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get session status."""
        return self.processing_sessions.get(session_id, {
            'status': 'not_found',
            'error': 'Session not found'
        })
    
    def get_session_results(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session results."""
        session = self.processing_sessions.get(session_id)
        if session and session.get('status') == 'completed':
            return session.get('results')
        return None