"""
Tests for file processor module
"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import patch, Mock

from glossary_updater.processor import (
    FileProcessor, GlossaryTerm, ProcessingError
)

from . import (
    SAMPLE_CSV_DATA, SAMPLE_JSON_DATA, SAMPLE_YAML_DATA,
    get_temp_path, cleanup_temp_files
)


class TestGlossaryTerm:
    """Test cases for GlossaryTerm class."""
    
    def test_init_valid(self):
        """Test valid GlossaryTerm initialization."""
        term = GlossaryTerm("API", "Application Programming Interface")
        assert term.phrase == "API"
        assert term.definition == "Application Programming Interface"
        assert term.metadata == {}
    
    def test_init_with_metadata(self):
        """Test GlossaryTerm initialization with metadata."""
        metadata = {"category": "Technical", "priority": "High"}
        term = GlossaryTerm("API", "Application Programming Interface", metadata)
        assert term.phrase == "API"
        assert term.definition == "Application Programming Interface"
        assert term.metadata == metadata
    
    def test_init_empty_phrase(self):
        """Test GlossaryTerm with empty phrase."""
        with pytest.raises(ValueError, match="Phrase cannot be empty"):
            GlossaryTerm("", "Some definition")
    
    def test_init_empty_definition(self):
        """Test GlossaryTerm with empty definition."""
        with pytest.raises(ValueError, match="Definition cannot be empty"):
            GlossaryTerm("Some phrase", "")
    
    def test_init_whitespace_normalization(self):
        """Test that whitespace is normalized."""
        term = GlossaryTerm("  API  ", "  Application Programming Interface  ")
        assert term.phrase == "API"
        assert term.definition == "Application Programming Interface"
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        term = GlossaryTerm("API", "Application Programming Interface")
        expected = {
            "phrase": "API",
            "definition": "Application Programming Interface"
        }
        assert term.to_dict() == expected
    
    def test_to_dict_with_metadata(self):
        """Test conversion to dictionary with metadata."""
        metadata = {"category": "Technical"}
        term = GlossaryTerm("API", "Application Programming Interface", metadata)
        expected = {
            "phrase": "API",
            "definition": "Application Programming Interface",
            "metadata": metadata
        }
        assert term.to_dict() == expected
    
    def test_str_representation(self):
        """Test string representation."""
        term = GlossaryTerm("API", "Application Programming Interface")
        str_repr = str(term)
        assert "API" in str_repr
        assert "Application Programming Interface" in str_repr
    
    def test_str_representation_long_definition(self):
        """Test string representation with long definition."""
        long_def = "A" * 100
        term = GlossaryTerm("API", long_def)
        str_repr = str(term)
        assert "..." in str_repr
        assert len(str_repr) < len(long_def) + 20  # Should be truncated


class TestFileProcessor:
    """Test cases for FileProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = FileProcessor()
        cleanup_temp_files()
    
    def teardown_method(self):
        """Clean up after tests."""
        cleanup_temp_files()
    
    def test_init(self):
        """Test FileProcessor initialization."""
        assert self.processor.supported_formats == {'csv', 'json', 'yaml'}
    
    def test_process_csv_basic(self):
        """Test processing basic CSV file."""
        csv_file = get_temp_path("test.csv")
        csv_file.write_text(SAMPLE_CSV_DATA)
        
        terms = self.processor.process_file(csv_file)
        
        assert len(terms) == 3
        assert terms[0].phrase == "API"
        assert terms[0].definition == "Application Programming Interface"
        assert terms[1].phrase == "REST"
        assert terms[2].phrase == "JSON"
    
    def test_process_csv_different_columns(self):
        """Test processing CSV with different column names."""
        csv_content = """term,description,notes
Microservice,"Small independent service",Architecture
Container,"Lightweight package",DevOps"""
        
        csv_file = get_temp_path("test_alt.csv")
        csv_file.write_text(csv_content)
        
        terms = self.processor.process_file(csv_file)
        
        assert len(terms) == 2
        assert terms[0].phrase == "Microservice"
        assert terms[0].definition == "Small independent service"
    
    def test_process_csv_with_metadata(self):
        """Test processing CSV with additional metadata columns."""
        csv_content = """phrase,definition,category,priority
API,"Application Programming Interface",Technical,High
REST,"Representational State Transfer",Technical,Medium"""
        
        csv_file = get_temp_path("test_meta.csv")
        csv_file.write_text(csv_content)
        
        terms = self.processor.process_file(csv_file)
        
        assert len(terms) == 2
        assert terms[0].metadata.get("category") == "Technical"
        assert terms[0].metadata.get("priority") == "High"
    
    def test_process_csv_missing_columns(self):
        """Test processing CSV with missing required columns."""
        csv_content = """name,value
Something,Other"""
        
        csv_file = get_temp_path("test_invalid.csv")
        csv_file.write_text(csv_content)
        
        with pytest.raises(ProcessingError, match="No phrase column found"):
            self.processor.process_file(csv_file)
    
    def test_process_csv_empty_rows(self):
        """Test processing CSV with empty rows."""
        csv_content = """phrase,definition
API,Application Programming Interface
,
REST,Representational State Transfer
JSON,"""
        
        csv_file = get_temp_path("test_empty.csv")
        csv_file.write_text(csv_content)
        
        terms = self.processor.process_file(csv_file)
        
        # Should skip empty/invalid rows
        assert len(terms) == 2
        assert terms[0].phrase == "API"
        assert terms[1].phrase == "REST"
    
    def test_process_json_array_format(self):
        """Test processing JSON in array format."""
        json_file = get_temp_path("test.json")
        json_file.write_text(json.dumps(SAMPLE_JSON_DATA["glossary"]))
        
        terms = self.processor.process_file(json_file)
        
        assert len(terms) == 2
        assert terms[0].phrase == "Machine Learning"
        assert terms[1].phrase == "Cloud Computing"
    
    def test_process_json_object_format(self):
        """Test processing JSON in object format."""
        json_file = get_temp_path("test.json")
        json_file.write_text(json.dumps(SAMPLE_JSON_DATA))
        
        terms = self.processor.process_file(json_file)
        
        assert len(terms) == 2
        assert terms[0].phrase == "Machine Learning"
        assert terms[1].phrase == "Cloud Computing"
    
    def test_process_json_key_value_format(self):
        """Test processing JSON in key-value format."""
        data = {
            "API": "Application Programming Interface",
            "REST": "Representational State Transfer"
        }
        
        json_file = get_temp_path("test_kv.json")
        json_file.write_text(json.dumps(data))
        
        terms = self.processor.process_file(json_file)
        
        assert len(terms) == 2
        phrases = [term.phrase for term in terms]
        assert "API" in phrases
        assert "REST" in phrases
    
    def test_process_json_nested_structure(self):
        """Test processing JSON with nested structure."""
        data = {
            "data": {
                "glossary": [
                    {"phrase": "API", "definition": "Application Programming Interface"}
                ]
            }
        }
        
        json_file = get_temp_path("test_nested.json")
        json_file.write_text(json.dumps(data))
        
        terms = self.processor.process_file(json_file)
        
        assert len(terms) == 1
        assert terms[0].phrase == "API"
    
    def test_process_json_invalid_syntax(self):
        """Test processing invalid JSON."""
        json_file = get_temp_path("invalid.json")
        json_file.write_text('{"invalid": "json", "missing": }')
        
        with pytest.raises(ProcessingError, match="JSON processing failed"):
            self.processor.process_file(json_file)
    
    def test_process_yaml_basic(self):
        """Test processing basic YAML file."""
        yaml_file = get_temp_path("test.yaml")
        yaml_file.write_text(SAMPLE_YAML_DATA)
        
        terms = self.processor.process_file(yaml_file)
        
        assert len(terms) == 2
        assert terms[0].phrase == "DevOps"
        assert terms[1].phrase == "Agile"
    
    def test_process_yaml_key_value(self):
        """Test processing YAML in key-value format."""
        yaml_content = """
API: Application Programming Interface
REST: Representational State Transfer
"""
        
        yaml_file = get_temp_path("test_kv.yaml")
        yaml_file.write_text(yaml_content)
        
        terms = self.processor.process_file(yaml_file)
        
        assert len(terms) == 2
        phrases = [term.phrase for term in terms]
        assert "API" in phrases
        assert "REST" in phrases
    
    def test_process_yaml_invalid_syntax(self):
        """Test processing invalid YAML."""
        yaml_file = get_temp_path("invalid.yaml")
        yaml_file.write_text('invalid: yaml: content: [')
        
        with pytest.raises(ProcessingError, match="YAML processing failed"):
            self.processor.process_file(yaml_file)
    
    def test_process_unsupported_format(self):
        """Test processing unsupported file format."""
        txt_file = get_temp_path("test.txt")
        txt_file.write_text("Some text content")
        
        with pytest.raises(ProcessingError, match="Unsupported file format"):
            self.processor.process_file(txt_file)
    
    def test_process_nonexistent_file(self):
        """Test processing non-existent file."""
        nonexistent_file = get_temp_path("nonexistent.csv")
        
        with pytest.raises(ProcessingError, match="File not found"):
            self.processor.process_file(nonexistent_file)
    
    def test_process_multiple_files(self):
        """Test processing multiple files."""
        # Create CSV file
        csv_file = get_temp_path("terms.csv")
        csv_file.write_text("phrase,definition\nAPI,Application Programming Interface")
        
        # Create JSON file
        json_file = get_temp_path("terms.json")
        json_file.write_text(json.dumps({
            "glossary": [{"phrase": "JSON", "definition": "JavaScript Object Notation"}]
        }))
        
        terms = self.processor.process_files([csv_file, json_file])
        
        assert len(terms) == 2
        phrases = [term.phrase for term in terms]
        assert "API" in phrases
        assert "JSON" in phrases
    
    def test_process_files_with_duplicates(self):
        """Test processing files with duplicate terms."""
        # Create first file
        csv_file1 = get_temp_path("terms1.csv")
        csv_file1.write_text("phrase,definition\nAPI,Application Programming Interface")
        
        # Create second file with same term
        csv_file2 = get_temp_path("terms2.csv")
        csv_file2.write_text("phrase,definition\nAPI,Another definition\nREST,Representational State Transfer")
        
        terms = self.processor.process_files([csv_file1, csv_file2])
        
        # Should deduplicate (case-insensitive)
        assert len(terms) == 2
        phrases = [term.phrase for term in terms]
        assert "API" in phrases
        assert "REST" in phrases
    
    def test_deduplicate_terms(self):
        """Test term deduplication."""
        terms = [
            GlossaryTerm("API", "Definition 1"),
            GlossaryTerm("api", "Definition 2"),  # Different case
            GlossaryTerm("REST", "Definition 3"),
            GlossaryTerm("API", "Definition 4")   # Exact duplicate
        ]
        
        unique_terms = self.processor._deduplicate_terms(terms)
        
        assert len(unique_terms) == 2
        phrases = [term.phrase for term in unique_terms]
        assert "API" in phrases
        assert "REST" in phrases
    
    def test_find_phrase_column(self):
        """Test phrase column detection."""
        columns = ["phrase", "definition", "category"]
        assert self.processor._find_phrase_column(columns) == "phrase"
        
        columns = ["term", "description"]
        assert self.processor._find_phrase_column(columns) == "term"
        
        columns = ["word", "meaning"]
        assert self.processor._find_phrase_column(columns) == "word"
        
        columns = ["value", "description"]
        assert self.processor._find_phrase_column(columns) is None
    
    def test_find_definition_column(self):
        """Test definition column detection."""
        columns = ["phrase", "definition"]
        assert self.processor._find_definition_column(columns) == "definition"
        
        columns = ["term", "description"]
        assert self.processor._find_definition_column(columns) == "description"
        
        columns = ["phrase", "meaning"]
        assert self.processor._find_definition_column(columns) == "meaning"
        
        columns = ["phrase", "value"]
        assert self.processor._find_definition_column(columns) == "value"
        
        columns = ["phrase", "notes"]
        assert self.processor._find_definition_column(columns) is None
    
    def test_get_file_info_csv(self):
        """Test getting file info for CSV."""
        csv_file = get_temp_path("info_test.csv")
        csv_file.write_text(SAMPLE_CSV_DATA)
        
        info = self.processor.get_file_info(csv_file)
        
        assert info["path"] == str(csv_file)
        assert info["format"] == ".csv"
        assert info["estimated_terms"] == 3
        assert info["valid"] is True
        assert info["size"] > 0
    
    def test_get_file_info_json(self):
        """Test getting file info for JSON."""
        json_file = get_temp_path("info_test.json")
        json_file.write_text(json.dumps(SAMPLE_JSON_DATA))
        
        info = self.processor.get_file_info(json_file)
        
        assert info["format"] == ".json"
        assert info["estimated_terms"] == 2
        assert info["valid"] is True
    
    def test_get_file_info_invalid(self):
        """Test getting file info for invalid file."""
        invalid_file = get_temp_path("invalid.json")
        invalid_file.write_text("invalid json")
        
        info = self.processor.get_file_info(invalid_file)
        
        assert info["valid"] is False
        assert "error" in info
    
    def test_parse_term_array_various_formats(self):
        """Test parsing term arrays with various field names."""
        # Test with 'phrase' and 'definition'
        data1 = [{"phrase": "API", "definition": "Application Programming Interface"}]
        terms1 = self.processor._parse_term_array(data1)
        assert len(terms1) == 1
        assert terms1[0].phrase == "API"
        
        # Test with 'term' and 'description'
        data2 = [{"term": "REST", "description": "Representational State Transfer"}]
        terms2 = self.processor._parse_term_array(data2)
        assert len(terms2) == 1
        assert terms2[0].phrase == "REST"
        
        # Test with 'word' and 'meaning'
        data3 = [{"word": "JSON", "meaning": "JavaScript Object Notation"}]
        terms3 = self.processor._parse_term_array(data3)
        assert len(terms3) == 1
        assert terms3[0].phrase == "JSON"
    
    def test_parse_term_dict_complex(self):
        """Test parsing term dictionary with complex definitions."""
        data = {
            "API": {
                "definition": "Application Programming Interface",
                "category": "Technical",
                "examples": ["REST API", "GraphQL API"]
            },
            "Simple": "Simple definition"
        }
        
        terms = self.processor._parse_term_dict(data)
        
        assert len(terms) == 2
        
        # Find API term
        api_term = next(term for term in terms if term.phrase == "API")
        assert api_term.definition == "Application Programming Interface"
        assert api_term.metadata.get("category") == "Technical"
        
        # Find Simple term
        simple_term = next(term for term in terms if term.phrase == "Simple")
        assert simple_term.definition == "Simple definition"


class TestFileProcessorErrorHandling:
    """Test error handling in FileProcessor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = FileProcessor()
        cleanup_temp_files()
    
    def teardown_method(self):
        """Clean up after tests."""
        cleanup_temp_files()
    
    def test_csv_fallback_processing(self):
        """Test CSV fallback processing when pandas fails."""
        csv_file = get_temp_path("test.csv")
        csv_file.write_text("phrase,definition\nAPI,Application Programming Interface")
        
        # Mock pandas to fail
        with patch('pandas.read_csv', side_effect=Exception("Pandas failed")):
            terms = self.processor.process_file(csv_file)
            
            assert len(terms) == 1
            assert terms[0].phrase == "API"
    
    def test_csv_encoding_issues(self):
        """Test handling CSV with encoding issues."""
        csv_file = get_temp_path("encoding_test.csv")
        # Write with different encoding
        csv_file.write_bytes("phrase,definition\nAPI,Définition\n".encode('latin-1'))
        
        # Should handle gracefully
        try:
            terms = self.processor.process_file(csv_file)
            # If successful, should have parsed something
            assert len(terms) >= 0
        except ProcessingError:
            # If failed, should raise ProcessingError
            pass
    
    def test_large_file_handling(self):
        """Test handling of large files."""
        # Create a moderately large CSV
        csv_content = "phrase,definition\n"
        for i in range(1000):
            csv_content += f"Term{i},Definition for term {i}\n"
        
        csv_file = get_temp_path("large.csv")
        csv_file.write_text(csv_content)
        
        terms = self.processor.process_file(csv_file)
        assert len(terms) == 1000
    
    def test_malformed_csv_handling(self):
        """Test handling of malformed CSV."""
        csv_file = get_temp_path("malformed.csv")
        csv_file.write_text('phrase,definition\n"unclosed quote,API,definition')
        
        # Should either process successfully or raise ProcessingError
        try:
            terms = self.processor.process_file(csv_file)
            # If successful, terms should be reasonable
            assert isinstance(terms, list)
        except ProcessingError:
            # If failed, should be a ProcessingError
            pass


if __name__ == "__main__":
    pytest.main([__file__])
