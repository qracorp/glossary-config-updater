"""
File processor for reading and parsing glossary files.

Supports CSV, JSON, and YAML formats with permissive validation aligned with Angular implementation.
"""

import csv
import json
import yaml
import re
from pathlib import Path
from typing import List, Dict, Any, Union, Iterator, Optional
import pandas as pd

from .utils import logger, ProgressTracker


class ProcessingError(Exception):
    """Exception raised during file processing."""
    pass


class ValidationError(Exception):
    """Exception raised during term validation."""
    pass


class TermValidator:
    """Validates and cleans glossary terms with permissive rules (Angular-aligned)."""
    
    def __init__(self, schema: Optional[Dict[str, Any]] = None):
        """Initialize with optional custom schema."""
        self.schema = schema or self.get_permissive_schema()
        self.validation_errors = []
        self.cleaned_count = 0
        self.rejected_count = 0
    
    def get_permissive_schema(self) -> Dict[str, Any]:
        """Get permissive validation schema matching Angular implementation."""
        return {
            "phrase": {
                "required": True,
                "min_length": 1,  # Just non-empty after trim
                "max_length": None,  # No length limit
                "pattern": None,  # No character restrictions
                "forbidden_chars": [],  # No forbidden characters
                "max_words": None  # No word limit
            },
            "definition": {
                "required": False,  # Optional - defaults to empty string
                "min_length": 0,  # Can be empty
                "max_length": None,  # No length limit
                "forbidden_chars": [],  # No forbidden characters
                "must_end_with_punctuation": False  # No punctuation requirement
            }
        }
    
    def clean_and_validate_term(self, phrase: str, definition: str, metadata: Dict[str, Any] = None) -> Optional['GlossaryTerm']:
        """
        Clean and validate a single term with permissive rules.
        
        Returns:
            GlossaryTerm if valid, None if invalid
        """
        try:
            # Step 1: Clean the data (minimal processing)
            cleaned_phrase = self.clean_phrase(phrase)
            cleaned_definition = self.clean_definition(definition)
            
            # Step 2: Validate against permissive schema
            if self.validate_phrase(cleaned_phrase) and self.validate_definition(cleaned_definition):
                self.cleaned_count += 1
                return GlossaryTerm(cleaned_phrase, cleaned_definition, metadata or {})
            else:
                self.rejected_count += 1
                return None
                
        except Exception as e:
            self.validation_errors.append(f"Term validation error: {str(e)}")
            self.rejected_count += 1
            return None
    
    def clean_phrase(self, phrase: str) -> str:
        """Clean phrase with minimal processing (Angular-style)."""
        if not phrase or phrase == 'None':
            return ""
        
        # Convert to string and trim whitespace only
        phrase = str(phrase).strip()
        
        return phrase
    
    def clean_definition(self, definition: str) -> str:
        """Clean definition with minimal processing (Angular-style)."""
        if not definition or definition == 'None':
            return ""  # Default to empty string (optional field)
        
        # Convert to string and trim whitespace only
        definition = str(definition).strip()
        
        return definition
    
    def validate_phrase(self, phrase: str) -> bool:
        """Validate phrase with permissive rules."""
        rules = self.schema["phrase"]
        
        # Only check if required and non-empty
        if rules.get("required", False) and not phrase:
            self.validation_errors.append("Phrase is required but empty")
            return False
        
        # If phrase exists, check minimum length (only non-empty requirement)
        if phrase and rules.get("min_length", 0) > 0:
            if len(phrase) < rules["min_length"]:
                self.validation_errors.append(f"Phrase is empty after cleaning: '{phrase}'")
                return False
        
        return True
    
    def validate_definition(self, definition: str) -> bool:
        """Validate definition with permissive rules."""
        rules = self.schema["definition"]
        
        # Definition is optional - always valid
        if not rules.get("required", False):
            return True
        
        # If definition is required and empty
        if rules.get("required", False) and not definition:
            self.validation_errors.append("Definition is required but empty")
            return False
        
        return True
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            "cleaned_count": self.cleaned_count,
            "rejected_count": self.rejected_count,
            "error_count": len(self.validation_errors),
            "errors": self.validation_errors[:10],  # First 10 errors
            "success_rate": self.cleaned_count / (self.cleaned_count + self.rejected_count) if (self.cleaned_count + self.rejected_count) > 0 else 0
        }


class GlossaryTerm:
    """Represents a single glossary term."""
    
    def __init__(self, phrase: str, definition: str, metadata: Dict[str, Any] = None):
        """
        Initialize glossary term with permissive validation.
        
        Args:
            phrase: The term or phrase (required)
            definition: The definition (optional, defaults to empty)
            metadata: Additional metadata
        """
        self.phrase = phrase
        self.definition = definition or ""  # Default to empty string if None
        self.metadata = metadata or {}
        
        # Validate required fields (only phrase is required)
        if not self.phrase:
            raise ValueError("Phrase cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'phrase': self.phrase,
            'definition': self.definition
        }
        if self.metadata:
            result['metadata'] = self.metadata
        return result
    
    def __str__(self) -> str:
        return f"{self.phrase}: {self.definition[:50]}{'...' if len(self.definition) > 50 else ''}"
    
    def __repr__(self) -> str:
        return f"GlossaryTerm(phrase='{self.phrase}', definition='{self.definition[:30]}...')"


class FileProcessor:
    """Processes glossary files with permissive validation aligned with Angular implementation."""
    
    def __init__(self, validation_schema: Optional[Dict[str, Any]] = None):
        """Initialize file processor with optional validation schema."""
        self.supported_formats = {'csv', 'json', 'yaml'}
        self.validator = TermValidator(validation_schema)
        
    def process_files(self, file_paths: List[Path]) -> List[GlossaryTerm]:
        """
        Process multiple files and return validated glossary terms.
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            List of validated GlossaryTerm objects
        """
        all_terms = []
        progress = ProgressTracker(len(file_paths), "Processing files")
        
        for file_path in file_paths:
            try:
                logger.info(f"Processing file: {file_path}")
                terms = self.process_file(file_path)
                all_terms.extend(terms)
                logger.info(f"  → Found {len(terms)} valid terms")
                progress.update()
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {str(e)}")
                raise ProcessingError(f"Failed to process {file_path}: {str(e)}")
        
        progress.finish()
        
        # Remove duplicates while preserving order (case-insensitive normalization)
        unique_terms = self._deduplicate_terms(all_terms)
        
        # Report validation statistics
        report = self.validator.get_validation_report()
        logger.info(f"Validation Summary:")
        logger.info(f"  Terms processed: {report['cleaned_count'] + report['rejected_count']}")
        logger.info(f"  Terms accepted: {report['cleaned_count']}")
        logger.info(f"  Terms rejected: {report['rejected_count']}")
        logger.info(f"  Success rate: {report['success_rate']:.1%}")
        
        if report['error_count'] > 0:
            logger.warning(f"  Validation errors: {report['error_count']}")
            for error in report['errors']:
                logger.debug(f"    - {error}")
        
        logger.info(f"Final terms after deduplication: {len(unique_terms)}")
        
        return unique_terms
    
    def process_file(self, file_path: Path) -> List[GlossaryTerm]:
        """Process a single file with permissive validation."""
        if not file_path.exists():
            raise ProcessingError(f"File not found: {file_path}")
        
        extension = file_path.suffix.lower()
        
        # Extract raw terms first
        if extension == '.csv':
            raw_terms = self._extract_csv_terms(file_path)
        elif extension == '.json':
            raw_terms = self._extract_json_terms(file_path)
        elif extension in ['.yaml', '.yml']:
            raw_terms = self._extract_yaml_terms(file_path)
        else:
            raise ProcessingError(f"Unsupported file format: {extension}")
        
        # Validate and clean all terms with permissive rules
        validated_terms = []
        for raw_term in raw_terms:
            cleaned_term = self.validator.clean_and_validate_term(
                phrase=raw_term.get('phrase', ''),
                definition=raw_term.get('definition', ''),
                metadata=raw_term.get('metadata', {})
            )
            if cleaned_term:
                validated_terms.append(cleaned_term)
        
        logger.debug(f"File processing complete: {len(validated_terms)} valid terms from {file_path}")
        return validated_terms
    
    def _extract_csv_terms(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract raw terms from CSV file with UTF-8 encoding."""
        raw_terms = []
        
        try:
            # Try pandas first with UTF-8 encoding
            df = pd.read_csv(file_path, encoding='utf-8')
            df.columns = df.columns.str.strip().str.lower()
            
            phrase_col = self._find_phrase_column(df.columns)
            definition_col = self._find_definition_column(df.columns)
            
            if not phrase_col:
                raise ProcessingError(f"Required 'phrase' column not found. Available: {list(df.columns)}")
            
            for index, row in df.iterrows():
                try:
                    phrase = str(row[phrase_col]).strip() if pd.notna(row[phrase_col]) else ""
                    definition = str(row[definition_col]).strip() if definition_col and pd.notna(row[definition_col]) else ""
                    
                    # Skip completely empty rows
                    if phrase.lower() in ['nan', 'none', ''] and definition.lower() in ['nan', 'none', '']:
                        continue
                    
                    # Collect metadata
                    metadata = {}
                    for col in df.columns:
                        if col not in [phrase_col, definition_col] and pd.notna(row[col]):
                            metadata[col] = row[col]
                    
                    raw_terms.append({
                        'phrase': phrase,
                        'definition': definition,
                        'metadata': metadata
                    })
                    
                except Exception as e:
                    logger.debug(f"Skipping CSV row {index + 1}: {str(e)}")
                    continue
            
            return raw_terms
            
        except Exception as e:
            logger.debug(f"Pandas failed, trying standard csv: {str(e)}")
            return self._extract_csv_fallback(file_path)
    
    def _extract_csv_fallback(self, file_path: Path) -> List[Dict[str, Any]]:
        """Fallback CSV extraction using standard csv module with UTF-8."""
        raw_terms = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as csvfile:
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                fieldnames = [name.strip().lower() for name in reader.fieldnames]
                reader.fieldnames = fieldnames
                
                phrase_col = self._find_phrase_column(fieldnames)
                definition_col = self._find_definition_column(fieldnames)
                
                if not phrase_col:
                    raise ProcessingError(f"Required 'phrase' column not found. Available: {fieldnames}")
                
                for row in reader:
                    try:
                        phrase = row.get(phrase_col, '').strip()
                        definition = row.get(definition_col, '').strip() if definition_col else ""
                        
                        metadata = {}
                        for key, value in row.items():
                            if key not in [phrase_col, definition_col] and value:
                                metadata[key] = value.strip()
                        
                        raw_terms.append({
                            'phrase': phrase,
                            'definition': definition,
                            'metadata': metadata
                        })
                        
                    except Exception as e:
                        logger.debug(f"Skipping CSV row: {str(e)}")
                        continue
            
            return raw_terms
            
        except Exception as e:
            raise ProcessingError(f"CSV processing failed: {str(e)}")
    
    def _extract_json_terms(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract raw terms from JSON file with UTF-8 encoding."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            raw_terms = []
            
            if isinstance(data, list):
                raw_terms.extend(self._parse_term_array(data))
            elif isinstance(data, dict):
                # Look for glossary data
                glossary_data = None
                for key in ['glossary', 'terms', 'definitions', 'vocabulary']:
                    if key in data:
                        glossary_data = data[key]
                        break
                
                if glossary_data:
                    if isinstance(glossary_data, list):
                        raw_terms.extend(self._parse_term_array(glossary_data))
                    elif isinstance(glossary_data, dict):
                        raw_terms.extend(self._parse_term_dict(glossary_data))
                else:
                    raw_terms.extend(self._parse_term_dict(data))
            
            return raw_terms
            
        except json.JSONDecodeError as e:
            raise ProcessingError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ProcessingError(f"JSON processing failed: {str(e)}")
    
    def _extract_yaml_terms(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract raw terms from YAML file with UTF-8 encoding."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            raw_terms = []
            
            if isinstance(data, list):
                raw_terms.extend(self._parse_term_array(data))
            elif isinstance(data, dict):
                glossary_data = None
                for key in ['glossary', 'terms', 'definitions', 'vocabulary']:
                    if key in data:
                        glossary_data = data[key]
                        break
                
                if glossary_data:
                    if isinstance(glossary_data, list):
                        raw_terms.extend(self._parse_term_array(glossary_data))
                    elif isinstance(glossary_data, dict):
                        raw_terms.extend(self._parse_term_dict(glossary_data))
                else:
                    raw_terms.extend(self._parse_term_dict(data))
            
            return raw_terms
            
        except yaml.YAMLError as e:
            raise ProcessingError(f"Invalid YAML format: {str(e)}")
        except Exception as e:
            raise ProcessingError(f"YAML processing failed: {str(e)}")
    
    def _parse_term_array(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse array of term objects into standardized format."""
        raw_terms = []
        
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            
            phrase = None
            definition = None
            metadata = {}
            
            # Look for phrase (required)
            for key in ['phrase', 'term', 'word', 'name', 'title']:
                if key in item:
                    phrase = str(item[key]).strip()
                    break
            
            # Look for definition (optional)
            for key in ['definition', 'description', 'meaning', 'explanation', 'desc']:
                if key in item:
                    definition = str(item[key]).strip()
                    break
            
            # Collect metadata
            for key, value in item.items():
                if key not in ['phrase', 'term', 'word', 'name', 'title', 
                             'definition', 'description', 'meaning', 'explanation', 'desc']:
                    metadata[key] = value
            
            # Include term if it has a phrase (definition optional)
            if phrase:
                raw_terms.append({
                    'phrase': phrase,
                    'definition': definition or "",
                    'metadata': metadata
                })
        
        return raw_terms
    
    def _parse_term_dict(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse dictionary as key-value pairs."""
        raw_terms = []
        
        for phrase, definition in data.items():
            try:
                if isinstance(definition, str):
                    raw_terms.append({
                        'phrase': phrase,
                        'definition': definition,
                        'metadata': {}
                    })
                elif isinstance(definition, dict):
                    def_text = ''
                    metadata = {}
                    
                    # Look for definition text
                    for key in ['definition', 'description', 'meaning', 'explanation']:
                        if key in definition:
                            def_text = str(definition[key]).strip()
                            break
                    
                    # Collect metadata
                    for key, value in definition.items():
                        if key not in ['definition', 'description', 'meaning', 'explanation']:
                            metadata[key] = value
                    
                    raw_terms.append({
                        'phrase': phrase,
                        'definition': def_text,
                        'metadata': metadata
                    })
                else:
                    raw_terms.append({
                        'phrase': phrase,
                        'definition': str(definition),
                        'metadata': {}
                    })
                    
            except Exception as e:
                logger.debug(f"Skipping term '{phrase}': {str(e)}")
                continue
        
        return raw_terms
    
    def _find_phrase_column(self, columns: List[str]) -> str:
        """Find the phrase column from available columns."""
        phrase_keywords = ['phrase', 'term', 'word', 'name', 'title', 'key']
        for keyword in phrase_keywords:
            for col in columns:
                if keyword in col.lower():
                    return col
        return None
    
    def _find_definition_column(self, columns: List[str]) -> str:
        """Find the definition column from available columns."""
        definition_keywords = ['definition', 'description', 'meaning', 'explanation', 'desc', 'value']
        for keyword in definition_keywords:
            for col in columns:
                if keyword in col.lower():
                    return col
        return None
    
    def _deduplicate_terms(self, terms: List[GlossaryTerm]) -> List[GlossaryTerm]:
        """Remove duplicate terms with case-insensitive normalization (Angular-style)."""
        seen_phrases = set()
        unique_terms = []
        
        for term in terms:
            # Normalize phrase for comparison (lowercase for case-insensitive matching)
            phrase_normalized = term.phrase.lower().strip()
            
            if phrase_normalized not in seen_phrases:
                seen_phrases.add(phrase_normalized)
                unique_terms.append(term)
            else:
                logger.debug(f"Removed duplicate term: {term.phrase}")
        
        return unique_terms
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get detailed validation report."""
        return self.validator.get_validation_report()