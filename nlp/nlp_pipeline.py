"""
Main NLP pipeline for processing HMO documents using spaCy.
"""

import spacy
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EntityMatch:
    """Represents an extracted entity with confidence score."""
    text: str
    label: str
    start: int
    end: int
    confidence: float


class NLPPipeline:
    """
    Main NLP pipeline for HMO document processing.
    
    Configures spaCy with appropriate language model and implements
    custom entity recognition for HMO-specific terms.
    """
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize the NLP pipeline.
        
        Args:
            model_name: spaCy model to use (default: en_core_web_sm)
        """
        self.model_name = model_name
        self.nlp = None
        self._load_model()
        self._setup_custom_patterns()
    
    def _load_model(self):
        """Load the spaCy model with error handling."""
        try:
            self.nlp = spacy.load(self.model_name)
            logger.info(f"Loaded spaCy model: {self.model_name}")
        except OSError:
            logger.error(f"Model {self.model_name} not found. Please install it with: python -m spacy download {self.model_name}")
            # Fallback to blank model
            self.nlp = spacy.blank("en")
            logger.warning("Using blank English model as fallback")
    
    def _setup_custom_patterns(self):
        """Set up custom patterns for HMO-specific entity recognition."""
        if not self.nlp:
            return
            
        # Add custom patterns using spaCy's EntityRuler
        ruler = self.nlp.add_pipe("entity_ruler", before="ner")
        
        # HMO-specific patterns
        patterns = [
            # License reference patterns
            {"label": "LICENSE_REF", "pattern": [{"TEXT": {"REGEX": r"^[A-Z]{2,4}\/\d{4,6}$"}}]},
            {"label": "LICENSE_REF", "pattern": [{"TEXT": {"REGEX": r"^HMO\/\d{4,6}$"}}]},
            {"label": "LICENSE_REF", "pattern": [{"TEXT": {"REGEX": r"^\d{4,8}$"}}]},
            
            # Council names (common UK councils)
            {"label": "COUNCIL", "pattern": [{"LOWER": "east"}, {"LOWER": "lindsey"}, {"LOWER": "district"}, {"LOWER": "council"}]},
            {"label": "COUNCIL", "pattern": [{"LOWER": "central"}, {"LOWER": "bedfordshire"}, {"LOWER": "council"}]},
            {"label": "COUNCIL", "pattern": [{"LOWER": "dacorum"}, {"LOWER": "borough"}, {"LOWER": "council"}]},
            {"label": "COUNCIL", "pattern": [{"LOWER": "fife"}, {"LOWER": "council"}]},
            
            # HMO-specific terms
            {"label": "HMO_TERM", "pattern": [{"LOWER": "hmo"}]},
            {"label": "HMO_TERM", "pattern": [{"LOWER": "house"}, {"LOWER": "in"}, {"LOWER": "multiple"}, {"LOWER": "occupation"}]},
            {"label": "HMO_TERM", "pattern": [{"LOWER": "licence"}, {"LOWER": "holder"}]},
            {"label": "HMO_TERM", "pattern": [{"LOWER": "hmo"}, {"LOWER": "manager"}]},
            {"label": "HMO_TERM", "pattern": [{"LOWER": "maximum"}, {"LOWER": "occupancy"}]},
            {"label": "HMO_TERM", "pattern": [{"LOWER": "max"}, {"LOWER": "occupancy"}]},
            
            # Date patterns
            {"label": "DATE_PATTERN", "pattern": [{"TEXT": {"REGEX": r"\d{1,2}\/\d{1,2}\/\d{4}"}}]},
            {"label": "DATE_PATTERN", "pattern": [{"TEXT": {"REGEX": r"\d{1,2}-\d{1,2}-\d{4}"}}]},
            {"label": "DATE_PATTERN", "pattern": [{"TEXT": {"REGEX": r"\d{4}-\d{1,2}-\d{1,2}"}}]},
            
            # UK postcode patterns
            {"label": "POSTCODE", "pattern": [{"TEXT": {"REGEX": r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$"}}]},
        ]
        
        ruler.add_patterns(patterns)
        logger.info(f"Added {len(patterns)} custom patterns to NLP pipeline")
    
    def process_text(self, text: str) -> Dict:
        """
        Process text and extract entities.
        
        Args:
            text: Input text to process
            
        Returns:
            Dictionary containing extracted entities and metadata
        """
        if not self.nlp or not text.strip():
            return {"entities": [], "tokens": [], "sentences": []}
        
        # Process the text
        doc = self.nlp(text)
        
        # Extract entities
        entities = []
        for ent in doc.ents:
            entities.append(EntityMatch(
                text=ent.text,
                label=ent.label_,
                start=ent.start_char,
                end=ent.end_char,
                confidence=self._calculate_entity_confidence(ent)
            ))
        
        # Extract tokens and sentences
        tokens = [token.text for token in doc]
        sentences = [sent.text.strip() for sent in doc.sents]
        
        return {
            "entities": entities,
            "tokens": tokens,
            "sentences": sentences,
            "doc": doc  # Keep spaCy doc for further processing
        }
    
    def _calculate_entity_confidence(self, entity) -> float:
        """
        Calculate confidence score for an entity.
        
        Args:
            entity: spaCy entity object
            
        Returns:
            Confidence score between 0 and 1
        """
        # Base confidence from spaCy (if available)
        base_confidence = 0.7
        
        # Adjust based on entity type
        if entity.label_ in ["LICENSE_REF", "POSTCODE"]:
            # High confidence for pattern-matched entities
            base_confidence = 0.9
        elif entity.label_ in ["PERSON", "ORG"]:
            # Medium confidence for named entities
            base_confidence = 0.8
        elif entity.label_ in ["DATE", "DATE_PATTERN"]:
            # High confidence for dates
            base_confidence = 0.85
        
        # Adjust based on entity length and context
        if len(entity.text) < 3:
            base_confidence *= 0.8
        elif len(entity.text) > 50:
            base_confidence *= 0.9
        
        return min(base_confidence, 1.0)
    
    def extract_addresses(self, text: str) -> List[EntityMatch]:
        """
        Extract address-like entities from text.
        
        Args:
            text: Input text
            
        Returns:
            List of address entities
        """
        result = self.process_text(text)
        addresses = []
        
        # Look for address patterns
        address_patterns = [
            r'\d+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr|Close|Cl|Way|Place|Pl)\b',
            r'[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr|Close|Cl|Way|Place|Pl)\s*\d*',
        ]
        
        for pattern in address_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                addresses.append(EntityMatch(
                    text=match.group().strip(),
                    label="ADDRESS",
                    start=match.start(),
                    end=match.end(),
                    confidence=0.8
                ))
        
        # Also include GPE (geopolitical entities) from spaCy
        for entity in result["entities"]:
            if entity.label in ["GPE", "LOC"]:
                addresses.append(entity)
        
        return addresses
    
    def extract_dates(self, text: str) -> List[EntityMatch]:
        """
        Extract date entities from text.
        
        Args:
            text: Input text
            
        Returns:
            List of date entities
        """
        result = self.process_text(text)
        dates = []
        
        # Get dates from spaCy
        for entity in result["entities"]:
            if entity.label in ["DATE", "DATE_PATTERN"]:
                dates.append(entity)
        
        # Additional date patterns
        date_patterns = [
            r'\b\d{1,2}\/\d{1,2}\/\d{4}\b',
            r'\b\d{1,2}-\d{1,2}-\d{4}\b',
            r'\b\d{4}-\d{1,2}-\d{1,2}\b',
            r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',
        ]
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                dates.append(EntityMatch(
                    text=match.group().strip(),
                    label="DATE",
                    start=match.start(),
                    end=match.end(),
                    confidence=0.85
                ))
        
        return dates
    
    def extract_references(self, text: str) -> List[EntityMatch]:
        """
        Extract license reference numbers from text.
        
        Args:
            text: Input text
            
        Returns:
            List of reference entities
        """
        result = self.process_text(text)
        references = []
        
        # Get license references from custom patterns
        for entity in result["entities"]:
            if entity.label == "LICENSE_REF":
                references.append(entity)
        
        # Additional reference patterns
        ref_patterns = [
            r'\b[A-Z]{2,4}\/\d{4,8}\b',
            r'\bHMO\/\d{4,8}\b',
            r'\b\d{6,8}\b',  # Simple numeric references
            r'\b[A-Z]{1,3}\d{4,8}\b',  # Letter-number combinations
        ]
        
        for pattern in ref_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                references.append(EntityMatch(
                    text=match.group().strip(),
                    label="LICENSE_REF",
                    start=match.start(),
                    end=match.end(),
                    confidence=0.9
                ))
        
        return references
    
    def extract_person_names(self, text: str) -> List[EntityMatch]:
        """
        Extract person names from text.
        
        Args:
            text: Input text
            
        Returns:
            List of person name entities
        """
        result = self.process_text(text)
        names = []
        
        # Get person names from spaCy
        for entity in result["entities"]:
            if entity.label == "PERSON":
                names.append(entity)
        
        return names