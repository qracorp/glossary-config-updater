"""
File processor for reading and parsing glossary files.

Supports CSV, JSON, and YAML formats with automatic data validation and cleaning.
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
    """Validates and cleans glossary terms according to schema."""
    
    def __init__(self, schema: Optional[Dict[str, Any]] = None):
        """Initialize with optional custom schema."""
        self.schema = schema or self.get_default_schema()
        self.validation_errors = []
        self.cleaned_count = 0
        self.rejected_count = 0
    
    def get_default_schema(self) -> Dict[str, Any]:
        """Get default validation schema for glossary terms."""
        return {
            "phrase": {
                "required": True,
                "min_length": 1,
                "max_length": 100,
                "pattern": r"^[A-Za-z0-9\s\-_\(\)\.\/\&]+$",
                "forbidden_chars": ["<", ">", "\"", "'", ";", "script"],
                "max_words": 10
            },
            "definition": {
                "required": True,
                "min_length": 5,
                "max_length": 500,
                "forbidden_chars": ["<", ">", "script", "javascript"],
                "must_end_with_punctuation": True
            }
        }
    
    def clean_and_validate_term(self, phrase: str, definition: str, metadata: Dict[str, Any] = None) -> Optional['GlossaryTerm']:
        """
        Clean and validate a single term.
        
        Returns:
            GlossaryTerm if valid, None if invalid
        """
        try:
            # Step 1: Clean the data
            cleaned_phrase = self.clean_phrase(phrase)
            cleaned_definition = self.clean_definition(definition)
            
            # Step 2: Validate against schema
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
        """Clean and normalize phrase."""
        if not phrase or phrase == 'None':
            return ""
        
        # Convert to string and strip
        phrase = str(phrase).strip()
        
        # Remove HTML tags
        phrase = re.sub(r'<[^>]+>', '', phrase)
        
        # Remove dangerous characters
        for char in self.schema["phrase"]["forbidden_chars"]:
            phrase = phrase.replace(char, "")
        
        # Normalize whitespace
        phrase = re.sub(r'\s+', ' ', phrase).strip()
        
        # Title case for consistency
        phrase = phrase.title()
        
        # Handle common abbreviations
        abbreviations = ['Api', 'Rest', 'Json', 'Xml', 'Http', 'Https', 'Url', 'Uri', 'Sql', 'Css', 'Html']
        for abbr in abbreviations:
            phrase = phrase.replace(abbr, abbr.upper())
        
        return phrase
    
    def clean_definition(self, definition: str) -> str:
        """Clean and normalize definition."""
        if not definition or definition == 'None':
            return ""
        
        # Convert to string and strip
        definition = str(definition).strip()
        
        # Remove HTML tags
        definition = re.sub(r'<[^>]+>', '', definition)
        
        # Remove dangerous characters/strings
        for forbidden in self.schema["definition"]["forbidden_chars"]:
            definition = definition.replace(forbidden, "")
        
        # Clean whitespace
        definition = re.sub(r'\s+', ' ', definition).strip()
        
        # Capitalize first letter
        if definition and definition[0].islower():
            definition = definition[0].upper() + definition[1:]
        
        # Ensure ends with punctuation
        if definition and not definition.endswith(('.', '!', '?')):
            definition += '.'
        
        return definition
    
    def validate_phrase(self, phrase: str) -> bool:
        """Validate phrase against schema."""
        rules = self.schema["phrase"]
        
        if not phrase and rules.get("required", False):
            self.validation_errors.append("Phrase is required but empty")
            return False
        
        if phrase:
            # Length checks
            if len(phrase) < rules.get("min_length", 0):
                self.validation_errors.append(f"Phrase too short: '{phrase}'")
                return False
            
            if len(phrase) > rules.get("max_length", 1000):
                self.validation_errors.append(f"Phrase too long: '{phrase[:50]}...'")
                return False
            
            # Pattern check
            if "pattern" in rules and not re.match(rules["pattern"], phrase):
                self.validation_errors.append(f"Phrase contains invalid characters: '{phrase}'")
                return False
            
            # Word count check
            if "max_words" in rules and len(phrase.split()) > rules["max_words"]:
                self.validation_errors.append(f"Phrase has too many words: '{phrase}'")
                return False
        
        return True
    
    def validate_definition(self, definition: str) -> bool:
        """Validate definition against schema."""
        rules = self.schema["definition"]
        
        if not definition and rules.get("required", False):
            self.validation_errors.append("Definition is required but empty")
            return False
        
        if definition:
            # Length checks
            if len(definition) < rules.get("min_length", 0):
                self.validation_errors.append(f"Definition too short: '{definition}'")
                return False
            
            if len(definition) > rules.get("max_length", 1000):
                self.validation_errors.append(f"Definition too long: '{definition[:50]}...'")
                return False
            
            # Punctuation check
            if rules.get("must_end_with_punctuation", False):
                if not definition.endswith(('.', '!', '?')):
                    self.validation_errors.append(f"Definition must end with punctuation: '{definition}'")
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
        Initialize glossary term.
        
        Args:
            phrase: The term or phrase
            definition: The definition
            metadata: Additional metadata
        """
        self.phrase = phrase
        self.definition = definition
        self.metadata = metadata or {}
        
        # Validate required fields (basic check, detailed validation happens in TermValidator)
        if not self.phrase:
            raise ValueError("Phrase cannot be empty")
        if not self.definition:
            raise ValueError("Definition cannot be empty")
    
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
    """Processes glossary files with automatic validation and cleaning."""
    
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
        
        # Remove duplicates while preserving order
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
        """Process a single file with automatic validation."""
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
        
        # Validate and clean all terms
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
        """Extract raw terms from CSV file."""
        raw_terms = []
        
        try:
            # Try pandas first
            df = pd.read_csv(file_path, encoding='utf-8')
            df.columns = df.columns.str.strip().str.lower()
            
            phrase_col = self._find_phrase_column(df.columns)
            definition_col = self._find_definition_column(df.columns)
            
            if not phrase_col or not definition_col:
                raise ProcessingError(f"Required columns not found. Available: {list(df.columns)}")
            
            for index, row in df.iterrows():
                try:
                    phrase = str(row[phrase_col]).strip()
                    definition = str(row[definition_col]).strip()
                    
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
        """Fallback CSV extraction using standard csv module."""
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
                
                if not phrase_col or not definition_col:
                    raise ProcessingError(f"Required columns not found. Available: {fieldnames}")
                
                for row in reader:
                    try:
                        phrase = row.get(phrase_col, '').strip()
                        definition = row.get(definition_col, '').strip()
                        
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
        """Extract raw terms from JSON file."""
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
        """Extract raw terms from YAML file."""
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
            
            # Look for phrase
            for key in ['phrase', 'term', 'word', 'name', 'title']:
                if key in item:
                    phrase = str(item[key]).strip()
                    break
            
            # Look for definition
            for key in ['definition', 'description', 'meaning', 'explanation', 'desc']:
                if key in item:
                    definition = str(item[key]).strip()
                    break
            
            # Collect metadata
            for key, value in item.items():
                if key not in ['phrase', 'term', 'word', 'name', 'title', 
                             'definition', 'description', 'meaning', 'explanation', 'desc']:
                    metadata[key] = value
            
            if phrase or definition:  # Allow validator to handle empty values
                raw_terms.append({
                    'phrase': phrase or '',
                    'definition': definition or '',
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
        """Remove duplicate terms while preserving order."""
        seen_phrases = set()
        unique_terms = []
        
        for term in terms:
            phrase_lower = term.phrase.lower()
            if phrase_lower not in seen_phrases:
                seen_phrases.add(phrase_lower)
                unique_terms.append(term)
            else:
                logger.debug(f"Removed duplicate term: {term.phrase}")
        
        return unique_terms
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get detailed validation report."""
        return self.validator.get_validation_report()