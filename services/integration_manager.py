"""
Integration manager that wires together all processing components.

This module serves as the central orchestrator that connects the web interface
to the processing engine, integrates the NLP pipeline with document processors,
and connects the validation system to the audit interface.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import uuid

from models.hmo_record import HMORecord
from models.processing_session import ProcessingSession, SessionManager
from processors.unified_processor import UnifiedDocumentProcessor
from nlp.nlp_pipeline import NLPPipeline
from nlp.confidence_calculator import ConfidenceCalculator
from services.data_validator import DataValidator, ValidationResult
from services.quality_assessment import QualityAssessment
from services.audit_manager import AuditManager, FlaggedRecord
from services.csv_generator import CSVGenerator
from services.file_storage import FileStorageManager
from services.queue_manager import QueueManager
from services.error_handler import ErrorHandler, GracefulDegradationManager, error_handler_decorator
from services.performance_optimizer import PerformanceOptimizer, performance_monitor_decorator, cached_operation
from services.simple_processor import SimpleProcessor

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    """
    Integrated processing pipeline that orchestrates all components.
    
    Requirements: 5.1, 7.4
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the integrated processing pipeline.
        
        Args:
            config: Configuration dictionary for all components
        """
        self.config = config or {}
        
        # Initialize error handling and performance optimization
        self.error_handler = ErrorHandler()
        self.degradation_manager = GracefulDegradationManager()
        self.performance_optimizer = PerformanceOptimizer(config)
        
        # Initialize core components with error handling
        try:
            # Get database paths from environment
            import os
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
            
            self.document_processor = UnifiedDocumentProcessor(config)
            self.nlp_pipeline = NLPPipeline()
            self.confidence_calculator = ConfidenceCalculator()
            self.data_validator = DataValidator()
            self.quality_assessment = QualityAssessment()
            self.audit_manager = AuditManager(db_path=audit_db_path)
            self.csv_generator = CSVGenerator()
            self.file_storage = FileStorageManager()
            self.session_manager = SessionManager(db_path=session_db_path)
            try:
                self.queue_manager = QueueManager()
            except Exception as e:
                logger.warning(f"Could not initialize QueueManager: {e}. The worker process will not be able to connect.")
                self.queue_manager = None
            
            # Register services for health monitoring
            self._register_services()
            
            logger.info("Processing pipeline initialized with all components")
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e, 
                {"component": "ProcessingPipeline", "action": "initialization"}
            )
            logger.critical(f"Failed to initialize processing pipeline: {error_info.error_id}")
            raise
    
    def _register_services(self):
        """Register services for health monitoring and management."""
        try:
            # Check if degradation_manager exists and has register_service method
            if not hasattr(self, 'degradation_manager') or not hasattr(self.degradation_manager, 'register_service'):
                logger.info("Degradation manager not available, skipping service registration")
                return
                
            # Register core services with the degradation manager
            services = {
                'document_processor': lambda: True,
                'nlp_pipeline': lambda: True,
                'data_validator': lambda: True,
                'quality_assessment': lambda: True,
                'audit_manager': lambda: True,
                'csv_generator': lambda: True,
                'file_storage': lambda: True,
                'session_manager': lambda: True,
                'queue_manager': lambda: True
            }
            
            # Register each service with the degradation manager
            registered_count = 0
            for service_name, health_check in services.items():
                try:
                    self.degradation_manager.register_service(service_name, health_check)
                    registered_count += 1
                except Exception as service_error:
                    logger.warning(f"Failed to register service {service_name}: {service_error}")
                    
            logger.info(f"Registered {registered_count}/{len(services)} services for health monitoring")
            
        except Exception as e:
            logger.warning(f"Failed to register services for health monitoring: {e}")
            # Don't raise here as this is not critical for basic functionality
        
    async def process_document_async(
        self, 
        file_path: Union[str, Path], 
        session_id: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process a document asynchronously through the complete pipeline with comprehensive error handling.
        
        Args:
            file_path: Path to the document to process
            session_id: Processing session ID
            options: Processing options (OCR settings, confidence thresholds, etc.)
            
        Returns:
            Dict[str, Any]: Complete processing results
            
        Requirements: 5.1, 7.4, 5.3, 4.5, 5.2, 5.4
        """
        # Start performance monitoring
        operation_id = self.performance_optimizer.performance_monitor.start_operation("document_processing")
        
        processing_errors = []
        fallback_used = False
        
        try:
            logger.info(f"Starting async document processing for session {session_id}")
            
            # Get file size for optimization
            file_size_mb = Path(file_path).stat().st_size / 1024 / 1024
            optimization_settings = self.performance_optimizer.optimize_for_large_files(file_size_mb)
            
            logger.info(f"File size: {file_size_mb:.1f}MB, optimization settings: {optimization_settings}")
            
            # Update session status
            await self._update_session_status(session_id, "processing")
            
            # Step 1: Document Processing with error handling and caching
            await self._update_processing_stage(session_id, "document_extraction")
            try:
                # Check cache for document processing results
                cache_key = f"doc_processing_{Path(file_path).name}_{file_size_mb}"
                cached_result = self.performance_optimizer.cache_manager.get_cached_result(
                    "document_processing", cache_key
                )
                
                if cached_result:
                    logger.info("Using cached document processing result")
                    doc_result = cached_result
                else:
                    # Process with optimization settings
                    if optimization_settings.get('use_chunked_processing', False):
                        doc_result = await self._process_document_chunked(file_path, optimization_settings)
                    else:
                        doc_result = await asyncio.to_thread(
                            self.document_processor.process_document_with_fallback, 
                            file_path
                        )
                    
                    # Cache the result
                    self.performance_optimizer.cache_manager.cache_result(
                        "document_processing", doc_result, cache_key
                    )
                
                if not doc_result.extracted_text:
                    # Try fallback document processing
                    fallback_result = self.degradation_manager.get_service_or_fallback(
                        'document_processor', str(file_path)
                    )
                    if fallback_result and fallback_result.get('extracted_text'):
                        doc_result.extracted_text = fallback_result['extracted_text']
                        fallback_used = True
                    else:
                        raise Exception("No text could be extracted from document")
                        
            except Exception as e:
                error_info = self.error_handler.handle_error(
                    e, 
                    {"session_id": session_id, "stage": "document_extraction", "file_path": str(file_path)}
                )
                processing_errors.append(error_info)
                
                # Try fallback
                try:
                    fallback_result = self._fallback_document_processing(str(file_path))
                    if fallback_result.get('extracted_text'):
                        doc_result = type('obj', (object,), {
                            'extracted_text': fallback_result['extracted_text'],
                            'ocr_used': False,
                            'processing_metadata': {'fallback_used': True}
                        })()
                        fallback_used = True
                    else:
                        raise Exception("Document processing and fallback both failed")
                except Exception as fallback_error:
                    await self._update_session_status(session_id, "error", str(fallback_error))
                    raise
                
            # Step 2: NLP Processing with error handling
            await self._update_processing_stage(session_id, "nlp_processing")
            try:
                if self.degradation_manager.check_service_health('nlp_pipeline'):
                    nlp_result = await asyncio.to_thread(
                        self.nlp_pipeline.process_text,
                        doc_result.extracted_text
                    )
                else:
                    # Use fallback NLP processing
                    nlp_result = self._fallback_nlp_processing(doc_result.extracted_text)
                    fallback_used = True
                    
            except Exception as e:
                error_info = self.error_handler.handle_error(
                    e, 
                    {"session_id": session_id, "stage": "nlp_processing"}
                )
                processing_errors.append(error_info)
                
                # Use fallback NLP processing
                nlp_result = self._fallback_nlp_processing(doc_result.extracted_text)
                fallback_used = True
                
            # Step 3: Entity Extraction with error handling
            await self._update_processing_stage(session_id, "entity_extraction")
            try:
                # Entity extraction is already done by NLP pipeline
                entities = nlp_result.get('entities', {})
            except Exception as e:
                error_info = self.error_handler.handle_error(
                    e, 
                    {"session_id": session_id, "stage": "entity_extraction"}
                )
                processing_errors.append(error_info)
                
                # Use empty entities as fallback
                entities = {}
                
            # Step 4: Data Structuring with error handling
            await self._update_processing_stage(session_id, "data_structuring")
            try:
                hmo_records = await asyncio.to_thread(
                    self._structure_hmo_data,
                    entities,
                    doc_result
                )
                
                if not hmo_records:
                    # Create minimal record if no structured data found
                    from models.hmo_record import HMORecord
                    minimal_record = HMORecord()
                    minimal_record.council = "Unknown"
                    minimal_record.reference = f"EXTRACTED_{session_id[:8]}"
                    hmo_records = [minimal_record]
                    
            except Exception as e:
                error_info = self.error_handler.handle_error(
                    e, 
                    {"session_id": session_id, "stage": "data_structuring"}
                )
                processing_errors.append(error_info)
                
                # Create minimal record as fallback
                from models.hmo_record import HMORecord
                minimal_record = HMORecord()
                minimal_record.council = "Processing Error"
                minimal_record.reference = f"ERROR_{session_id[:8]}"
                hmo_records = [minimal_record]
                
            # Step 5: Confidence Scoring with error handling
            await self._update_processing_stage(session_id, "confidence_scoring")
            try:
                scored_records = await asyncio.to_thread(
                    self._calculate_confidence_scores,
                    hmo_records
                )
                
                # Apply fallback penalty if used
                if fallback_used:
                    for record in scored_records:
                        for field in record.confidence_scores:
                            record.confidence_scores[field] *= 0.7  # Reduce confidence
                            
            except Exception as e:
                error_info = self.error_handler.handle_error(
                    e, 
                    {"session_id": session_id, "stage": "confidence_scoring"}
                )
                processing_errors.append(error_info)
                
                # Use default low confidence scores
                for record in hmo_records:
                    record.confidence_scores = {field: 0.3 for field in record.get_field_names()}
                scored_records = hmo_records
                
            # Step 6: Data Validation with error handling
            await self._update_processing_stage(session_id, "data_validation")
            try:
                validation_results = await asyncio.to_thread(
                    self._validate_records,
                    scored_records
                )
            except Exception as e:
                error_info = self.error_handler.handle_error(
                    e, 
                    {"session_id": session_id, "stage": "data_validation"}
                )
                processing_errors.append(error_info)
                
                # Create basic validation results
                from services.data_validator import ValidationResult
                validation_results = [
                    ValidationResult(
                        is_valid=False,
                        confidence_score=0.3,
                        validation_errors=["Validation service unavailable"],
                        warnings=[],
                        suggested_corrections={}
                    ) for _ in scored_records
                ]
                
            # Step 7: Quality Assessment with error handling
            await self._update_processing_stage(session_id, "quality_assessment")
            try:
                quality_report = await asyncio.to_thread(
                    self.quality_assessment.assess_extraction_quality,
                    scored_records,
                    validation_results
                )
            except Exception as e:
                error_info = self.error_handler.handle_error(
                    e, 
                    {"session_id": session_id, "stage": "quality_assessment"}
                )
                processing_errors.append(error_info)
                
                # Create basic quality report
                quality_report = {
                    'average_confidence': 0.3,
                    'total_records': len(scored_records),
                    'quality_issues': ['Quality assessment service unavailable']
                }
                
            # Step 8: Flag Low-Confidence Records with error handling
            await self._update_processing_stage(session_id, "flagging_records")
            try:
                flagged_records = await asyncio.to_thread(
                    self._flag_low_confidence_records,
                    scored_records,
                    validation_results,
                    session_id,
                    options
                )
            except Exception as e:
                error_info = self.error_handler.handle_error(
                    e, 
                    {"session_id": session_id, "stage": "flagging_records"}
                )
                processing_errors.append(error_info)
                
                # Flag all records if flagging service fails
                flagged_records = []
                
            # Step 9: Generate CSV Output with error handling
            await self._update_processing_stage(session_id, "csv_generation")
            try:
                csv_data = await asyncio.to_thread(
                    self._generate_csv_output,
                    scored_records,
                    session_id
                )
            except Exception as e:
                error_info = self.error_handler.handle_error(
                    e, 
                    {"session_id": session_id, "stage": "csv_generation"}
                )
                processing_errors.append(error_info)
                
                # Create basic CSV data
                csv_data = {
                    'csv_content': 'council,reference,error\nProcessing Error,CSV Generation Failed,See error log',
                    'csv_filename': f'error_{session_id}.csv',
                    'csv_path': '',
                    'record_count': len(scored_records)
                }
                
            # Step 10: Update Session with Results
            await self._update_processing_stage(session_id, "finalizing")
            final_results = {
                'session_id': session_id,
                'records': scored_records,
                'validation_results': validation_results,
                'quality_report': quality_report,
                'flagged_records': flagged_records,
                'csv_data': csv_data,
                'processing_metadata': {
                    'document_type': getattr(doc_result, 'processing_metadata', {}).get('document_type', 'unknown'),
                    'ocr_used': getattr(doc_result, 'ocr_used', False),
                    'fallback_used': fallback_used,
                    'total_records': len(scored_records),
                    'flagged_count': len(flagged_records),
                    'average_confidence': quality_report.get('average_confidence', 0),
                    'processing_time': datetime.now().isoformat(),
                    'processing_errors': [
                        {
                            'error_id': err.error_id,
                            'category': err.category.value,
                            'severity': err.severity.value,
                            'user_message': err.user_message
                        } for err in processing_errors
                    ]
                }
            }
            
            # Update session with final results
            await self._finalize_session(session_id, final_results)
            
            # End performance monitoring
            self.performance_optimizer.performance_monitor.end_operation(
                operation_id, 
                success=True,
                additional_metrics={
                    'file_size_mb': file_size_mb,
                    'total_records': len(scored_records),
                    'fallback_used': fallback_used,
                    'processing_errors': len(processing_errors)
                }
            )
            
            if processing_errors:
                logger.warning(f"Document processing completed with {len(processing_errors)} errors for session {session_id}")
            else:
                logger.info(f"Document processing completed successfully for session {session_id}")
                
            return final_results
            
        except Exception as e:
            # Handle catastrophic failures
            error_info = self.error_handler.handle_error(
                e, 
                {"session_id": session_id, "stage": "catastrophic_failure"}
            )
            
            logger.critical(f"Catastrophic failure in document processing for session {session_id}: {error_info.error_id}")
            await self._update_session_status(session_id, "error", error_info.user_message)
            
            # End performance monitoring with error
            self.performance_optimizer.performance_monitor.end_operation(
                operation_id, 
                success=False,
                error_message=error_info.user_message
            )
            
            # Return minimal error result instead of raising
            return {
                'session_id': session_id,
                'records': [],
                'processing_metadata': {
                    'error': True,
                    'error_id': error_info.error_id,
                    'error_message': error_info.user_message,
                    'recovery_suggestions': error_info.recovery_suggestions
                }
            }
            
    def _structure_hmo_data(
        self, 
        entities: Dict[str, List], 
        doc_result: Any
    ) -> List[HMORecord]:
        """
        Structure extracted entities into HMO records.
        
        Args:
            entities: Extracted entities from NLP pipeline
            doc_result: Document processing result
            
        Returns:
            List[HMORecord]: Structured HMO records
        """
        records = []
        
        # Group entities by potential records
        # This is a simplified approach - in practice, you'd use more sophisticated
        # record boundary detection based on document structure
        
        councils = entities.get('councils', [])
        references = entities.get('references', [])
        addresses = entities.get('addresses', [])
        dates = entities.get('dates', [])
        names = entities.get('names', [])
        occupancies = entities.get('occupancies', [])
        
        # Create records by matching entities
        max_records = max(len(councils), len(references), len(addresses), 1)
        
        for i in range(max_records):
            record = HMORecord()
            
            # Assign entities to record fields
            if i < len(councils):
                record.council = councils[i].get('text', '')
                
            if i < len(references):
                record.reference = references[i].get('text', '')
                
            if i < len(addresses):
                record.hmo_address = addresses[i].get('text', '')
                
            # Extract dates (start and expiry)
            if len(dates) >= 2:
                # Assume first date is start, second is expiry
                if i * 2 < len(dates):
                    record.licence_start = dates[i * 2].get('normalized', '')
                if i * 2 + 1 < len(dates):
                    record.licence_expiry = dates[i * 2 + 1].get('normalized', '')
            elif len(dates) == 1 and i == 0:
                record.licence_start = dates[0].get('normalized', '')
                
            # Extract names (manager and holder)
            if len(names) >= 2:
                if i * 2 < len(names):
                    record.hmo_manager_name = names[i * 2].get('text', '')
                if i * 2 + 1 < len(names):
                    record.licence_holder_name = names[i * 2 + 1].get('text', '')
            elif len(names) == 1 and i == 0:
                record.hmo_manager_name = names[0].get('text', '')
                
            # Extract occupancy
            if i < len(occupancies):
                try:
                    record.max_occupancy = int(occupancies[i].get('value', 0))
                except (ValueError, TypeError):
                    record.max_occupancy = 0
                    
            # Only add record if it has some meaningful data
            if any([record.council, record.reference, record.hmo_address]):
                records.append(record)
                
        # If no structured records found, create a single record with available data
        if not records and (councils or references or addresses):
            record = HMORecord()
            if councils:
                record.council = councils[0].get('text', '')
            if references:
                record.reference = references[0].get('text', '')
            if addresses:
                record.hmo_address = addresses[0].get('text', '')
            records.append(record)
            
        return records
        
    def _calculate_confidence_scores(self, records: List[HMORecord]) -> List[HMORecord]:
        """
        Calculate confidence scores for all records.
        
        Args:
            records: List of HMO records
            
        Returns:
            List[HMORecord]: Records with confidence scores
        """
        for record in records:
            confidence_scores = self.confidence_calculator.calculate_record_confidence(record)
            record.confidence_scores = confidence_scores
            
        return records
        
    def _validate_records(self, records: List[HMORecord]) -> List[ValidationResult]:
        """
        Validate all records using the data validator.
        
        Args:
            records: List of HMO records to validate
            
        Returns:
            List[ValidationResult]: Validation results for each record
        """
        return self.data_validator.validate_batch(records)
        
    def _flag_low_confidence_records(
        self,
        records: List[HMORecord],
        validation_results: List[ValidationResult],
        session_id: str,
        options: Optional[Dict] = None
    ) -> List[FlaggedRecord]:
        """
        Flag records that need manual review.
        
        Args:
            records: List of HMO records
            validation_results: Validation results
            session_id: Processing session ID
            options: Processing options including confidence threshold
            
        Returns:
            List[FlaggedRecord]: Records flagged for manual review
        """
        confidence_threshold = options.get('confidence_threshold', 0.7) if options else 0.7
        flagged_records = []
        
        for i, (record, validation) in enumerate(zip(records, validation_results)):
            should_flag = False
            flag_reasons = []
            
            # Check overall confidence
            overall_confidence = record.get_overall_confidence()
            if overall_confidence < confidence_threshold:
                should_flag = True
                flag_reasons.append(f"Low confidence ({overall_confidence:.1%})")
                
            # Check validation errors
            if not validation.is_valid:
                should_flag = True
                flag_reasons.append("Validation errors")
                
            # Check individual field confidence
            low_confidence_fields = [
                field for field, score in record.confidence_scores.items()
                if score < confidence_threshold
            ]
            
            if low_confidence_fields:
                should_flag = True
                flag_reasons.append(f"Low confidence fields: {', '.join(low_confidence_fields)}")
                
            if should_flag:
                flagged_record = self.audit_manager.flag_record(
                    record=record,
                    session_id=session_id,
                    flag_reason="; ".join(flag_reasons),
                    confidence_score=overall_confidence
                )
                flagged_records.append(flagged_record)
                
        return flagged_records
        
    def _generate_csv_output(self, records: List[HMORecord], session_id: str) -> Dict[str, Any]:
        """
        Generate CSV output for the processed records.
        
        Args:
            records: List of HMO records
            session_id: Processing session ID
            
        Returns:
            Dict[str, Any]: CSV generation results
        """
        csv_content = self.csv_generator.generate_csv(records)
        
        # Store CSV file
        csv_filename = f"hmo_data_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_path = self.file_storage.store_csv_file(csv_content, csv_filename)
        
        return {
            'csv_content': csv_content,
            'csv_filename': csv_filename,
            'csv_path': str(csv_path),
            'record_count': len(records)
        }
        
    async def _update_session_status(
        self, 
        session_id: str, 
        status: str, 
        error_message: Optional[str] = None
    ) -> None:
        """Update processing session status."""
        try:
            session_data = {
                'processing_status': status,
                'last_updated': datetime.now().isoformat()
            }
            
            if error_message:
                session_data['error_message'] = error_message
                
            await asyncio.to_thread(
                self.session_manager.update_session,
                session_id,
                session_data
            )
        except Exception as e:
            logger.error(f"Failed to update session status: {str(e)}")
            
    async def _update_processing_stage(self, session_id: str, stage: str) -> None:
        """Update current processing stage."""
        try:
            await asyncio.to_thread(
                self.session_manager.update_session,
                session_id,
                {
                    'current_stage': stage,
                    'stage_updated': datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to update processing stage: {str(e)}")
            
    async def _finalize_session(self, session_id: str, results: Dict[str, Any]) -> None:
        """Finalize processing session with results."""
        try:
            session_data = {
                'processing_status': 'completed',
                'completed_at': datetime.now().isoformat(),
                'total_records': len(results['records']),
                'flagged_records': len(results['flagged_records']),
                'average_confidence': results['quality_report'].get('average_confidence', 0),
                'csv_filename': results['csv_data']['csv_filename']
            }
            
            await asyncio.to_thread(
                self.session_manager.update_session,
                session_id,
                session_data
            )
        except Exception as e:
            logger.error(f"Failed to finalize session: {str(e)}")


class IntegrationManager:
    """
    Main integration manager that coordinates all system components.
    
    This class serves as the central hub that connects:
    - Web interface to processing engine
    - NLP pipeline with document processors  
    - Validation system to audit interface
    
    Requirements: 5.1, 7.4
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize integration manager with all components.
        
        Args:
            config: System configuration dictionary
        """
        self.config = config or {}
        
        # Initialize simple processor as fallback
        self.simple_processor = SimpleProcessor()
        
        # Try to initialize main processing pipeline
        try:
            self.processing_pipeline = ProcessingPipeline(config)
            self.pipeline_available = True
        except Exception as e:
            logger.error(f"Failed to initialize main processing pipeline: {e}")
            self.processing_pipeline = None
            self.pipeline_available = False
        
        # Initialize queue for async processing
        self.processing_queue = asyncio.Queue()
        self.is_processing = False
        
        logger.info("Integration manager initialized")
        
    async def submit_document_for_processing(
        self,
        file_path: Union[str, Path],
        filename: str,
        file_size: int,
        processing_options: Optional[Dict] = None
    ) -> str:
        """
        Submit a document for processing through the integrated pipeline.
        
        Args:
            file_path: Path to uploaded document
            filename: Original filename
            file_size: File size in bytes
            processing_options: Processing configuration options
            
        Returns:
            str: Session ID for tracking processing
            
        Requirements: 5.1
        """
        try:
            # Create processing session
            session_id = str(uuid.uuid4())
            
            session_data = {
                'session_id': session_id,
                'file_name': filename,
                'file_size': file_size,
                'file_path': str(file_path),
                'processing_status': 'queued',
                'upload_timestamp': datetime.now().isoformat(),
                'processing_options': processing_options or {}
            }
            
            # Store session with error handling
            try:
                self.processing_pipeline.session_manager.create_session(session_data)
            except Exception as e:
                logger.error(f"Failed to create session: {e}")
                # Create a simple session record as fallback
                self._create_fallback_session(session_id, session_data)
            
            # Add to processing queue
            await self.processing_queue.put({
                'session_id': session_id,
                'file_path': file_path,
                'options': processing_options
            })
            
            # Start processing if not already running
            if not self.is_processing:
                asyncio.create_task(self._process_queue())
                
            logger.info(f"Document submitted for processing: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to submit document for processing: {e}")
            # Create emergency session ID for error tracking
            emergency_session_id = f"ERROR_{str(uuid.uuid4())[:8]}"
            self._handle_submission_error(emergency_session_id, str(e))
            return emergency_session_id
        
    async def _process_queue(self) -> None:
        """Process documents from the queue."""
        self.is_processing = True
        
        try:
            while not self.processing_queue.empty():
                try:
                    # Get next item from queue
                    queue_item = await self.processing_queue.get()
                    
                    # Try main pipeline first, fallback to simple processor
                    if self.pipeline_available and self.processing_pipeline:
                        try:
                            await self.processing_pipeline.process_document_async(
                                queue_item['file_path'],
                                queue_item['session_id'],
                                queue_item['options']
                            )
                        except Exception as e:
                            logger.warning(f"Main pipeline failed, using simple processor: {e}")
                            await self.simple_processor.process_document_simple(
                                str(queue_item['file_path']),
                                queue_item['session_id'],
                                queue_item['options']
                            )
                    else:
                        # Use simple processor directly
                        logger.info(f"Using simple processor for session {queue_item['session_id']}")
                        await self.simple_processor.process_document_simple(
                            str(queue_item['file_path']),
                            queue_item['session_id'],
                            queue_item['options']
                        )
                    
                    # Mark task as done
                    self.processing_queue.task_done()
                    
                except Exception as e:
                    logger.error(f"Queue processing error: {str(e)}")
                    # Try to update session with error status
                    try:
                        session_id = queue_item.get('session_id', 'unknown')
                        self.simple_processor.processing_sessions[session_id] = {
                            'status': 'error',
                            'error_message': str(e),
                            'last_updated': datetime.now().isoformat()
                        }
                    except Exception:
                        pass
                    
        finally:
            self.is_processing = False
            
    def get_processing_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get current processing status for a session.
        
        Args:
            session_id: Processing session ID
            
        Returns:
            Dict[str, Any]: Current processing status and progress
        """
        try:
            # First check simple processor
            simple_status = self.simple_processor.get_session_status(session_id)
            if simple_status.get('status') != 'not_found':
                return {
                    'status': simple_status.get('status', 'unknown'),
                    'current_stage': simple_status.get('current_stage', 'processing'),
                    'progress': simple_status.get('progress', 0.0),
                    'error_message': simple_status.get('error_message'),
                    'last_updated': simple_status.get('last_updated')
                }
            
            # Then check main pipeline if available
            if self.pipeline_available and self.processing_pipeline:
                try:
                    session = self.processing_pipeline.session_manager.get_session(session_id)
                    
                    if session:
                        return {
                            'status': session.get('processing_status', 'unknown'),
                            'current_stage': session.get('current_stage'),
                            'progress': self._calculate_progress(session),
                            'error_message': session.get('error_message'),
                            'last_updated': session.get('last_updated')
                        }
                except Exception as e:
                    logger.warning(f"Main pipeline status check failed: {e}")
            
            # Check fallback sessions
            if hasattr(self, '_fallback_sessions') and session_id in self._fallback_sessions:
                fallback = self._fallback_sessions[session_id]
                return {
                    'status': fallback.get('processing_status', 'unknown'),
                    'current_stage': 'fallback_processing',
                    'progress': 0.5,
                    'error_message': fallback.get('error_message'),
                    'last_updated': fallback.get('created_at')
                }
            
            # Check error sessions
            if hasattr(self, '_error_sessions') and session_id in self._error_sessions:
                error_session = self._error_sessions[session_id]
                return {
                    'status': 'error',
                    'current_stage': 'error',
                    'progress': 0.0,
                    'error_message': error_session.get('error_message', 'Unknown error'),
                    'last_updated': error_session.get('created_at')
                }
            
            return {'status': 'not_found', 'error': 'Session not found'}
            
        except Exception as e:
            logger.error(f"Failed to get processing status: {str(e)}")
            return {'status': 'error', 'error': str(e)}
            
    def _calculate_progress(self, session: Dict[str, Any]) -> float:
        """Calculate processing progress percentage."""
        stage_progress = {
            'queued': 0.0,
            'processing': 0.1,
            'document_extraction': 0.2,
            'nlp_processing': 0.3,
            'entity_extraction': 0.4,
            'data_structuring': 0.5,
            'confidence_scoring': 0.6,
            'data_validation': 0.7,
            'quality_assessment': 0.8,
            'flagging_records': 0.85,
            'csv_generation': 0.9,
            'finalizing': 0.95,
            'completed': 1.0,
            'error': 0.0
        }
        
        current_stage = session.get('current_stage', session.get('processing_status', 'queued'))
        return stage_progress.get(current_stage, 0.0)
        
    def get_processing_results(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get processing results for a completed session.
        
        Args:
            session_id: Processing session ID
            
        Returns:
            Optional[Dict[str, Any]]: Processing results if available
        """
        try:
            # First check simple processor results
            simple_results = self.simple_processor.get_session_results(session_id)
            if simple_results:
                return {
                    'session_id': session_id,
                    'records': simple_results.get('records', []),
                    'total_records': simple_results.get('total_records', 0),
                    'flagged_count': len([r for r in simple_results.get('records', []) if r.get('needs_review', False)]),
                    'average_confidence': simple_results.get('processing_metadata', {}).get('average_confidence', 0.5),
                    'csv_filename': simple_results.get('csv_filename'),
                    'processing_metadata': simple_results.get('processing_metadata', {}),
                    'processor_type': 'simple_fallback'
                }
            
            # Then check main pipeline if available
            if self.pipeline_available and self.processing_pipeline:
                try:
                    session = self.processing_pipeline.session_manager.get_session(session_id)
                    
                    if session and session.get('processing_status') == 'completed':
                        # Get flagged records for audit interface
                        flagged_records = []
                        try:
                            flagged_records = self.processing_pipeline.audit_manager.get_flagged_records(session_id)
                        except Exception as e:
                            logger.warning(f"Failed to get flagged records: {e}")
                        
                        return {
                            'session_id': session_id,
                            'total_records': session.get('total_records', 0),
                            'flagged_count': session.get('flagged_records', 0),
                            'average_confidence': session.get('average_confidence', 0),
                            'csv_filename': session.get('csv_filename'),
                            'flagged_records': [
                                {
                                    'record_id': fr.record_id,
                                    'flag_reason': fr.flag_reason,
                                    'confidence': getattr(fr.hmo_record, 'get_overall_confidence', lambda: 0.5)(),
                                    'review_status': getattr(fr.review_status, 'value', 'pending')
                                }
                                for fr in flagged_records
                            ],
                            'processing_metadata': {
                                'completed_at': session.get('completed_at'),
                                'file_name': session.get('file_name'),
                                'file_size': session.get('file_size'),
                                'processor_type': 'main_pipeline'
                            }
                        }
                except Exception as e:
                    logger.warning(f"Main pipeline results check failed: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get processing results: {str(e)}")
            return None
            
    def get_csv_download_path(self, session_id: str) -> Optional[str]:
        """
        Get CSV download path for a completed session.
        
        Args:
            session_id: Processing session ID
            
        Returns:
            Optional[str]: Path to CSV file if available
        """
        try:
            session = self.processing_pipeline.session_manager.get_session(session_id)
            
            if session and session.get('csv_filename'):
                return self.processing_pipeline.file_storage.get_csv_path(
                    session['csv_filename']
                )
                
        except Exception as e:
            logger.error(f"Failed to get CSV download path: {str(e)}")
            
        return None
        
    def validate_system_components(self) -> Dict[str, Any]:
        """
        Validate that all system components are properly integrated and working.
        
        Returns:
            Dict[str, Any]: System validation results
        """
        validation_results = {
            'overall_status': 'unknown',
            'components': {},
            'integration_tests': {},
            'issues': []
        }
        
        try:
            # Test document processor
            doc_validation = self.processing_pipeline.document_processor.validate_processing_environment()
            validation_results['components']['document_processor'] = doc_validation
            
            # Test NLP pipeline
            try:
                test_result = self.processing_pipeline.nlp_pipeline.process_text("Test text for validation")
                validation_results['components']['nlp_pipeline'] = 'operational' if test_result else 'failed'
            except Exception as e:
                validation_results['components']['nlp_pipeline'] = 'failed'
                validation_results['issues'].append(f"NLP pipeline error: {str(e)}")
                
            # Test data validator
            try:
                test_record = HMORecord()
                test_record.council = "Test Council"
                validation_result = self.processing_pipeline.data_validator.validate_record(test_record)
                validation_results['components']['data_validator'] = 'operational'
            except Exception as e:
                validation_results['components']['data_validator'] = 'failed'
                validation_results['issues'].append(f"Data validator error: {str(e)}")
                
            # Test audit manager
            try:
                audit_stats = self.processing_pipeline.audit_manager.get_audit_statistics()
                validation_results['components']['audit_manager'] = 'operational'
            except Exception as e:
                validation_results['components']['audit_manager'] = 'failed'
                validation_results['issues'].append(f"Audit manager error: {str(e)}")
                
            # Test file storage
            try:
                storage_info = self.processing_pipeline.file_storage.get_storage_info()
                validation_results['components']['file_storage'] = 'operational'
            except Exception as e:
                validation_results['components']['file_storage'] = 'failed'
                validation_results['issues'].append(f"File storage error: {str(e)}")
                
            # Determine overall status
            operational_components = sum(
                1 for status in validation_results['components'].values()
                if status == 'operational' or (isinstance(status, dict) and status.get('overall_status') == 'fully_operational')
            )
            
            total_components = len(validation_results['components'])
            
            if operational_components == total_components:
                validation_results['overall_status'] = 'fully_operational'
            elif operational_components >= total_components * 0.8:
                validation_results['overall_status'] = 'mostly_operational'
            elif operational_components >= total_components * 0.5:
                validation_results['overall_status'] = 'partially_operational'
            else:
                validation_results['overall_status'] = 'limited_functionality'
                
        except Exception as e:
            validation_results['overall_status'] = 'system_error'
            validation_results['issues'].append(f"System validation error: {str(e)}")
            
        return validation_results
        
    def _register_services(self) -> None:
        """Register services for health monitoring and fallback strategies."""
        # Register document processor
        self.degradation_manager.register_service(
            'document_processor',
            lambda: self.document_processor.validate_processing_environment()['overall_status'] != 'error'
        )
        
        # Register NLP pipeline
        self.degradation_manager.register_service(
            'nlp_pipeline',
            lambda: self.nlp_pipeline.nlp is not None
        )
        
        # Register data validator
        self.degradation_manager.register_service(
            'data_validator',
            lambda: True  # Data validator is always available
        )
        
        # Register file storage
        self.degradation_manager.register_service(
            'file_storage',
            lambda: self.file_storage.get_storage_info()['available']
        )
        
        # Register fallback strategies
        self.degradation_manager.register_fallback(
            'nlp_pipeline',
            self._fallback_nlp_processing
        )
        
        self.degradation_manager.register_fallback(
            'document_processor',
            self._fallback_document_processing
        )
        
    def _fallback_nlp_processing(self, text: str) -> Dict[str, Any]:
        """Fallback NLP processing using basic text analysis."""
        logger.info("Using fallback NLP processing")
        
        # Basic entity extraction using regex patterns
        import re
        
        entities = {
            'councils': [],
            'references': [],
            'addresses': [],
            'dates': [],
            'names': [],
            'occupancies': []
        }
        
        # Simple regex patterns for fallback
        council_pattern = r'\b\w+\s+(?:council|borough|authority)\b'
        reference_pattern = r'\b[A-Z]{2,4}[/-]?\d{3,8}\b'
        date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        
        for match in re.finditer(council_pattern, text, re.IGNORECASE):
            entities['councils'].append({
                'text': match.group(),
                'confidence': 0.6  # Lower confidence for fallback
            })
            
        for match in re.finditer(reference_pattern, text):
            entities['references'].append({
                'text': match.group(),
                'confidence': 0.7
            })
            
        for match in re.finditer(date_pattern, text):
            entities['dates'].append({
                'text': match.group(),
                'normalized': match.group(),  # Basic normalization
                'confidence': 0.5
            })
            
        return {
            'entities': entities,
            'fallback_used': True,
            'confidence_penalty': 0.2  # Reduce overall confidence
        }
        
    def _fallback_document_processing(self, file_path: str) -> Dict[str, Any]:
        """Fallback document processing using basic text extraction."""
        logger.info("Using fallback document processing")
        
        try:
            # Try simple text extraction
            if str(file_path).lower().endswith('.pdf'):
                # Basic PDF text extraction
                import PyPDF2
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text()
                        
            elif str(file_path).lower().endswith('.docx'):
                # Basic DOCX text extraction
                import docx
                doc = docx.Document(file_path)
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                
            else:
                raise Exception("Unsupported file format for fallback processing")
                
            return {
                'extracted_text': text,
                'fallback_used': True,
                'confidence_penalty': 0.3
            }
            
        except Exception as e:
            logger.error(f"Fallback document processing failed: {str(e)}")
            return {
                'extracted_text': "",
                'fallback_used': True,
                'error': str(e)
            }
            
    async def _process_document_chunked(self, file_path: str, optimization_settings: Dict[str, Any]) -> Any:
        """
        Process large documents in chunks for better memory management.
        
        Args:
            file_path: Path to document
            optimization_settings: Optimization settings
            
        Returns:
            Processing result
        """
        chunk_size_mb = optimization_settings.get('chunk_size_mb', 10)
        
        try:
            # For now, use regular processing but with memory monitoring
            if self.performance_optimizer.memory_manager.check_memory_pressure():
                logger.warning("Memory pressure detected, optimizing before processing")
                self.performance_optimizer.memory_manager.optimize_memory()
                
            result = await asyncio.to_thread(
                self.document_processor.process_document_with_fallback, 
                file_path
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Chunked processing failed: {str(e)}")
            raise
            
    def get_performance_status(self) -> Dict[str, Any]:
        """
        Get comprehensive performance status.
        
        Returns:
            Dict[str, Any]: Performance status information
        """
        return self.performance_optimizer.get_system_performance_status()
        
    def optimize_system_performance(self) -> Dict[str, Any]:
        """
        Perform system performance optimization.
        
        Returns:
            Dict[str, Any]: Optimization results
        """
        results = {}
        
        # Memory optimization
        if self.performance_optimizer.memory_manager.check_memory_pressure():
            memory_result = self.performance_optimizer.memory_manager.optimize_memory()
            results['memory_optimization'] = memory_result
            
        # Cache cleanup
        cache_stats_before = self.performance_optimizer.cache_manager.get_cache_stats()
        self.performance_optimizer.cache_manager._cleanup_cache()
        cache_stats_after = self.performance_optimizer.cache_manager.get_cache_stats()
        
        results['cache_optimization'] = {
            'files_before': cache_stats_before.get('disk_cache_files', 0),
            'files_after': cache_stats_after.get('disk_cache_files', 0),
            'evictions': cache_stats_after.get('total_evictions', 0) - cache_stats_before.get('total_evictions', 0)
        }
        
        return results   
    def _create_fallback_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Create a fallback session when database fails."""
        try:
            # Store in memory as fallback
            if not hasattr(self, '_fallback_sessions'):
                self._fallback_sessions = {}
            
            self._fallback_sessions[session_id] = {
                **session_data,
                'created_at': datetime.now().isoformat(),
                'fallback_mode': True
            }
            
            logger.warning(f"Created fallback session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to create fallback session: {e}")
    
    def _handle_submission_error(self, session_id: str, error_message: str) -> None:
        """Handle submission errors by creating error session."""
        try:
            if not hasattr(self, '_error_sessions'):
                self._error_sessions = {}
                
            self._error_sessions[session_id] = {
                'session_id': session_id,
                'processing_status': 'error',
                'error_message': error_message,
                'created_at': datetime.now().isoformat()
            }
            
            logger.error(f"Created error session {session_id}: {error_message}")
            
        except Exception as e:
            logger.critical(f"Failed to handle submission error: {e}")
    
    def get_csv_download_path(self, session_id: str) -> Optional[str]:
        """
        Get CSV download path for a completed session.
        
        Args:
            session_id: Processing session ID
            
        Returns:
            Optional[str]: Path to CSV file if available
        """
        try:
            # Generate CSV path
            csv_filename = f"hmo_results_{session_id[:8]}.csv"
            csv_path = Path("sample_outputs") / csv_filename
            
            # Check if CSV already exists
            if csv_path.exists():
                return str(csv_path)
            
            # Try to get session from simple processor first
            simple_results = self.simple_processor.get_session_results(session_id)
            if simple_results and simple_results.get('csv_path'):
                return simple_results['csv_path']
            
            # Try main pipeline if available
            if self.pipeline_available and self.processing_pipeline:
                try:
                    session = self.processing_pipeline.session_manager.get_session(session_id)
                    
                    if session and session.get('processing_status') == 'completed':
                        # Create CSV if it doesn't exist
                        if not csv_path.exists():
                            self._generate_csv_for_session(session_id, csv_path)
                        
                        return str(csv_path) if csv_path.exists() else None
                except Exception as e:
                    logger.warning(f"Main pipeline CSV check failed: {e}")
            
            # Try to generate CSV from any available data
            if not csv_path.exists():
                self._generate_csv_for_session(session_id, csv_path)
            
            return str(csv_path) if csv_path.exists() else None
            
        except Exception as e:
            logger.error(f"Failed to get CSV download path: {e}")
            return None
    
    def _generate_csv_for_session(self, session_id: str, csv_path: Path) -> None:
        """Generate CSV file for a session."""
        try:
            # Ensure output directory exists
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Try to get data from simple processor first
            simple_results = self.simple_processor.get_session_results(session_id)
            if simple_results and simple_results.get('records'):
                records = simple_results['records']
                
                # Generate CSV from simple processor records
                csv_content = self._generate_simple_csv(records)
                
                # Write CSV file
                with open(csv_path, 'w', encoding='utf-8') as f:
                    f.write(csv_content)
                    
                logger.info(f"Generated CSV file from simple processor: {csv_path}")
                return
            
            # Try main pipeline if available
            if self.pipeline_available and self.processing_pipeline:
                try:
                    session = self.processing_pipeline.session_manager.get_session(session_id)
                    
                    if session:
                        # Generate CSV content
                        csv_content = self.processing_pipeline.csv_generator.generate_csv(
                            session.get('extracted_records', [])
                        )
                        
                        # Write CSV file
                        with open(csv_path, 'w', encoding='utf-8') as f:
                            f.write(csv_content)
                            
                        logger.info(f"Generated CSV file from main pipeline: {csv_path}")
                        return
                except Exception as e:
                    logger.warning(f"Main pipeline CSV generation failed: {e}")
            
            # Create minimal CSV for error case
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write("council,reference,error\n")
                f.write(f"Unknown,{session_id[:8]},Session data not found\n")
                
        except Exception as e:
            logger.error(f"Failed to generate CSV for session {session_id}: {e}")
            # Create error CSV as fallback
            try:
                csv_path.parent.mkdir(parents=True, exist_ok=True)
                with open(csv_path, 'w', encoding='utf-8') as f:
                    f.write("council,reference,error\n")
                    f.write(f"Error,{session_id[:8]},CSV generation failed: {str(e)}\n")
            except Exception as csv_error:
                logger.error(f"Failed to create error CSV: {csv_error}")
    
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
    
    def validate_system_components(self) -> Dict[str, Any]:
        """
        Validate all system components and return status.
        
        Returns:
            Dict[str, Any]: System component status
        """
        try:
            components = {}
            
            # Check processing pipeline
            try:
                if hasattr(self.processing_pipeline, 'document_processor'):
                    components['document_processor'] = 'operational'
                else:
                    components['document_processor'] = 'missing'
            except Exception:
                components['document_processor'] = 'error'
            
            # Check NLP pipeline
            try:
                if hasattr(self.processing_pipeline, 'nlp_pipeline'):
                    components['nlp_pipeline'] = 'operational'
                else:
                    components['nlp_pipeline'] = 'missing'
            except Exception:
                components['nlp_pipeline'] = 'error'
            
            # Check database
            try:
                if hasattr(self.processing_pipeline, 'session_manager'):
                    # Try a simple database operation
                    self.processing_pipeline.session_manager.get_database_stats()
                    components['database'] = 'operational'
                else:
                    components['database'] = 'missing'
            except Exception:
                components['database'] = 'error'
            
            # Check file storage
            try:
                if hasattr(self.processing_pipeline, 'file_storage'):
                    components['file_storage'] = 'operational'
                else:
                    components['file_storage'] = 'missing'
            except Exception:
                components['file_storage'] = 'error'
            
            # Determine overall status
            operational_count = sum(1 for status in components.values() if status == 'operational')
            total_count = len(components)
            
            if operational_count == total_count:
                overall_status = 'fully_operational'
            elif operational_count > total_count / 2:
                overall_status = 'mostly_operational'
            else:
                overall_status = 'degraded'
            
            return {
                'overall_status': overall_status,
                'components': components,
                'operational_count': operational_count,
                'total_count': total_count
            }
            
        except Exception as e:
            logger.error(f"Failed to validate system components: {e}")
            return {
                'overall_status': 'error',
                'components': {'system_check': 'error'},
                'error': str(e)
            }