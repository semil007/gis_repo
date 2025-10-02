"""
Specialized entity extractors for HMO document processing.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """Represents an extracted entity with metadata."""
    text: str
    normalized_value: str
    confidence: float
    start_pos: int = 0
    end_pos: int = 0
    context: str = ""


class AddressParser:
    """
    Specialized parser for UK address formats.
    
    Handles various UK address formats and standardizes them.
    """
    
    def __init__(self):
        # UK address component patterns
        self.street_suffixes = [
            'street', 'st', 'road', 'rd', 'avenue', 'ave', 'lane', 'ln',
            'drive', 'dr', 'close', 'cl', 'way', 'place', 'pl', 'court', 'ct',
            'crescent', 'cres', 'gardens', 'gdns', 'park', 'square', 'sq',
            'terrace', 'ter', 'grove', 'mews', 'hill', 'view', 'walk'
        ]
        
        # UK postcode pattern
        self.postcode_pattern = re.compile(
            r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b',
            re.IGNORECASE
        )
        
        # House number patterns
        self.house_number_patterns = [
            r'\b\d+[A-Z]?\b',  # Simple numbers like 123, 45A
            r'\b\d+-\d+\b',    # Ranges like 12-14
            r'\bFlat\s+\d+[A-Z]?\b',  # Flat numbers
            r'\bApartment\s+\d+[A-Z]?\b',  # Apartment numbers
        ]
    
    def parse_addresses(self, text: str) -> List[ExtractedEntity]:
        """
        Parse and extract UK addresses from text.
        
        Args:
            text: Input text containing addresses
            
        Returns:
            List of extracted and normalized addresses
        """
        addresses = []
        
        # Split text into potential address blocks
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Look for address patterns
            address_candidates = self._find_address_candidates(line)
            
            for candidate in address_candidates:
                normalized = self._normalize_address(candidate['text'])
                if normalized:
                    addresses.append(ExtractedEntity(
                        text=candidate['text'],
                        normalized_value=normalized,
                        confidence=candidate['confidence'],
                        start_pos=candidate['start'],
                        end_pos=candidate['end'],
                        context=f"Line {i+1}"
                    ))
        
        return addresses
    
    def _find_address_candidates(self, text: str) -> List[Dict]:
        """Find potential address candidates in text."""
        candidates = []
        
        # Pattern 1: House number + street name + suffix
        street_pattern = r'(\d+[A-Z]?)\s+([A-Za-z\s]+(?:' + '|'.join(self.street_suffixes) + r'))\b'
        matches = re.finditer(street_pattern, text, re.IGNORECASE)
        
        for match in matches:
            candidates.append({
                'text': match.group().strip(),
                'confidence': 0.8,
                'start': match.start(),
                'end': match.end(),
                'type': 'street_address'
            })
        
        # Pattern 2: Full address with postcode
        postcode_matches = list(self.postcode_pattern.finditer(text))
        for pc_match in postcode_matches:
            # Look backwards for address components
            before_postcode = text[:pc_match.start()].strip()
            if len(before_postcode) > 10:  # Minimum address length
                # Take last 100 characters before postcode as potential address
                addr_start = max(0, pc_match.start() - 100)
                full_address = text[addr_start:pc_match.end()].strip()
                
                candidates.append({
                    'text': full_address,
                    'confidence': 0.9,
                    'start': addr_start,
                    'end': pc_match.end(),
                    'type': 'full_address'
                })
        
        # Pattern 3: Multi-line addresses (common in documents)
        if '\n' in text:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) >= 2:
                # Check if this looks like a multi-line address
                has_number = any(re.search(r'\d+', line) for line in lines[:2])
                has_street = any(any(suffix in line.lower() for suffix in self.street_suffixes) for line in lines)
                
                if has_number and has_street:
                    full_addr = ', '.join(lines)
                    candidates.append({
                        'text': full_addr,
                        'confidence': 0.75,
                        'start': 0,
                        'end': len(text),
                        'type': 'multiline_address'
                    })
        
        return candidates
    
    def _normalize_address(self, address: str) -> str:
        """
        Normalize address format.
        
        Args:
            address: Raw address text
            
        Returns:
            Normalized address string
        """
        if not address:
            return ""
        
        # Clean up the address
        normalized = re.sub(r'\s+', ' ', address.strip())
        
        # Standardize common abbreviations
        replacements = {
            r'\bSt\b': 'Street',
            r'\bRd\b': 'Road', 
            r'\bAve\b': 'Avenue',
            r'\bDr\b': 'Drive',
            r'\bCl\b': 'Close',
            r'\bLn\b': 'Lane',
            r'\bPl\b': 'Place',
            r'\bCt\b': 'Court',
            r'\bCres\b': 'Crescent',
            r'\bGdns\b': 'Gardens',
            r'\bSq\b': 'Square',
            r'\bTer\b': 'Terrace'
        }
        
        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        # Ensure proper capitalization
        normalized = ' '.join(word.capitalize() for word in normalized.split())
        
        return normalized


class DateNormalizer:
    """
    Normalizer for various date formats to standard YYYY-MM-DD format.
    """
    
    def __init__(self):
        # Common date patterns
        self.date_patterns = [
            r'\b\d{1,2}\/\d{1,2}\/\d{4}\b',  # DD/MM/YYYY or MM/DD/YYYY
            r'\b\d{1,2}-\d{1,2}-\d{4}\b',    # DD-MM-YYYY or MM-DD-YYYY
            r'\b\d{4}-\d{1,2}-\d{1,2}\b',    # YYYY-MM-DD
            r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',  # DD Month YYYY
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',  # Month DD, YYYY
        ]
    
    def normalize_dates(self, text: str) -> List[ExtractedEntity]:
        """
        Extract and normalize dates from text.
        
        Args:
            text: Input text containing dates
            
        Returns:
            List of normalized dates in YYYY-MM-DD format
        """
        dates = []
        
        for pattern in self.date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                date_text = match.group().strip()
                normalized = self._parse_and_normalize_date(date_text)
                
                if normalized:
                    dates.append(ExtractedEntity(
                        text=date_text,
                        normalized_value=normalized,
                        confidence=0.85,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        context="date_pattern"
                    ))
        
        return dates
    
    def _parse_and_normalize_date(self, date_str: str) -> Optional[str]:
        """
        Parse various date formats and normalize to YYYY-MM-DD.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Normalized date string or None if parsing fails
        """
        try:
            # Use dateutil parser which handles many formats
            parsed_date = date_parser.parse(date_str, dayfirst=True)  # UK format preference
            
            # Validate the parsed date is reasonable
            if parsed_date.year < 1900 or parsed_date.year > 2100:
                return None
            if parsed_date.month < 1 or parsed_date.month > 12:
                return None
            if parsed_date.day < 1 or parsed_date.day > 31:
                return None
                
            return parsed_date.strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            # Try manual parsing for specific patterns
            try:
                # Handle DD/MM/YYYY format specifically
                if re.match(r'\d{1,2}\/\d{1,2}\/\d{4}', date_str):
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                        # Validate ranges
                        if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
                            return f"{year}-{month:02d}-{day:02d}"
                
                # Handle DD-MM-YYYY format
                if re.match(r'\d{1,2}-\d{1,2}-\d{4}', date_str):
                    parts = date_str.split('-')
                    if len(parts) == 3:
                        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                        # Validate ranges
                        if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
                            return f"{year}-{month:02d}-{day:02d}"
                        
            except (ValueError, IndexError):
                pass
        
        logger.warning(f"Could not parse date: {date_str}")
        return None


class ReferenceExtractor:
    """
    Extractor for license numbers and reference codes.
    """
    
    def __init__(self):
        # License reference patterns
        self.reference_patterns = [
            r'\b[A-Z]{2,4}\/\d{4,8}\b',      # Format: ABC/123456
            r'\bHMO\/\d{4,8}\b',             # Format: HMO/123456
            r'\b[A-Z]{1,3}\d{4,8}\b',        # Format: A123456
            r'\b\d{6,8}\b',                  # Simple numeric: 123456
            r'\bRef:\s*([A-Z0-9\/\-]+)\b',   # Ref: followed by code
            r'\bReference:\s*([A-Z0-9\/\-]+)\b',  # Reference: followed by code
            r'\bLicence\s+No[.:]\s*([A-Z0-9\/\-]+)\b',  # Licence No: code
        ]
    
    def extract_references(self, text: str) -> List[ExtractedEntity]:
        """
        Extract license reference numbers from text.
        
        Args:
            text: Input text containing references
            
        Returns:
            List of extracted reference codes
        """
        references = []
        
        for pattern in self.reference_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                ref_text = match.group().strip()
                
                # Extract the actual reference (remove labels like "Ref:")
                if ':' in ref_text:
                    ref_code = ref_text.split(':', 1)[1].strip()
                else:
                    ref_code = ref_text
                
                # Validate reference format
                if self._is_valid_reference(ref_code):
                    references.append(ExtractedEntity(
                        text=ref_text,
                        normalized_value=ref_code.upper(),
                        confidence=0.9,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        context="license_reference"
                    ))
        
        return references
    
    def _is_valid_reference(self, ref: str) -> bool:
        """
        Validate if a string looks like a valid license reference.
        
        Args:
            ref: Reference string to validate
            
        Returns:
            True if valid reference format
        """
        if not ref or len(ref) < 4:
            return False
        
        # Must contain at least one letter or number
        if not re.search(r'[A-Za-z0-9]', ref):
            return False
        
        # Should not be all letters or all numbers (unless specific patterns)
        if ref.isalpha() and len(ref) < 6:
            return False
        
        if ref.isdigit() and len(ref) < 6:
            return False
        
        return True


class PersonNameExtractor:
    """
    Extractor for person names (managers and license holders).
    """
    
    def __init__(self):
        # Common titles and prefixes
        self.titles = [
            'mr', 'mrs', 'ms', 'miss', 'dr', 'prof', 'sir', 'lady',
            'lord', 'dame', 'rev', 'father', 'sister'
        ]
        
        # Name context patterns
        self.name_contexts = [
            r'(?:manager|holder|owner|landlord|contact):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:name|person):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+\((?:manager|holder|owner)\))?',
        ]
    
    def extract_person_names(self, text: str) -> List[ExtractedEntity]:
        """
        Extract person names from text.
        
        Args:
            text: Input text containing person names
            
        Returns:
            List of extracted person names
        """
        names = []
        
        # Extract names using context patterns
        for pattern in self.name_contexts:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                name_text = match.group(1) if match.groups() else match.group()
                name_text = name_text.strip()
                
                if self._is_valid_name(name_text):
                    normalized = self._normalize_name(name_text)
                    names.append(ExtractedEntity(
                        text=name_text,
                        normalized_value=normalized,
                        confidence=0.8,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        context="person_name"
                    ))
        
        # Look for capitalized words that might be names
        # This is more speculative, so lower confidence
        capitalized_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b'
        matches = re.finditer(capitalized_pattern, text)
        
        for match in matches:
            name_text = match.group().strip()
            
            # Skip if already found or if it looks like an address/organization
            if any(existing.text == name_text for existing in names):
                continue
            
            if self._is_likely_person_name(name_text):
                normalized = self._normalize_name(name_text)
                names.append(ExtractedEntity(
                    text=name_text,
                    normalized_value=normalized,
                    confidence=0.6,  # Lower confidence for speculative matches
                    start_pos=match.start(),
                    end_pos=match.end(),
                    context="capitalized_words"
                ))
        
        return names
    
    def _is_valid_name(self, name: str) -> bool:
        """
        Check if a string is a valid person name.
        
        Args:
            name: Name string to validate
            
        Returns:
            True if valid name format
        """
        if not name or len(name) < 2:
            return False
        
        # Must have at least one space (first + last name)
        parts = name.split()
        if len(parts) < 2:
            return False
        
        # Each part should start with capital letter
        for part in parts:
            if not part[0].isupper():
                return False
        
        # Should not contain numbers
        if re.search(r'\d', name):
            return False
        
        return True
    
    def _is_likely_person_name(self, name: str) -> bool:
        """
        Check if a capitalized string is likely a person name.
        
        Args:
            name: String to check
            
        Returns:
            True if likely a person name
        """
        # Skip common non-name words
        skip_words = {
            'street', 'road', 'avenue', 'lane', 'drive', 'close', 'way',
            'council', 'borough', 'district', 'city', 'town', 'county',
            'house', 'flat', 'apartment', 'building', 'centre', 'center',
            'office', 'department', 'service', 'authority', 'committee'
        }
        
        name_lower = name.lower()
        if any(word in name_lower for word in skip_words):
            return False
        
        # Check if it's a valid name format
        return self._is_valid_name(name)
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize person name format.
        
        Args:
            name: Raw name text
            
        Returns:
            Normalized name
        """
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', name.strip())
        
        # Proper case each word
        parts = []
        for part in normalized.split():
            # Handle titles
            if part.lower() in self.titles:
                parts.append(part.capitalize())
            else:
                # Handle names with apostrophes (O'Connor, D'Angelo)
                if "'" in part:
                    subparts = part.split("'")
                    parts.append("'".join(sub.capitalize() for sub in subparts))
                else:
                    parts.append(part.capitalize())
        
        return ' '.join(parts)