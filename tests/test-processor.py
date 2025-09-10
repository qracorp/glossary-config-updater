"""
Tests for file processor module - focused on actual behavior testing
"""

import pytest
import json
import yaml
from pathlib import Path
import tempfile
import shutil
from typing import List

from glossary_updater.processor import (
    FileProcessor, GlossaryTerm, ProcessingError, TermValidator
)


class TestGlossaryTerm:
    """Test GlossaryTerm behavior with real data."""
    
    def test_creation_with_valid_data(self):
        """Test creating terms with valid data."""
        term = GlossaryTerm("API", "Application Programming Interface")
        assert term.phrase == "API"
        assert term.definition == "Application Programming Interface"
        assert term.metadata == {}
    
    def test_creation_with_metadata(self):
        """Test creating terms with metadata."""
        metadata = {"category": "Technical", "priority": "High"}
        term = GlossaryTerm("REST", "Representational State Transfer", metadata)
        assert term.metadata == metadata
    
    def test_validation_empty_phrase(self):
        """Test that empty phrase raises error."""
        with pytest.raises(ValueError, match="Phrase cannot be empty"):
            GlossaryTerm("", "Some definition")
    
    def test_validation_empty_definition(self):
        """Test that empty definition raises error."""
        with pytest.raises(ValueError, match="Definition cannot be empty"):
            GlossaryTerm("Some phrase", "")
    
    def test_to_dict_conversion(self):
        """Test dictionary conversion."""
        term = GlossaryTerm("API", "Application Programming Interface", {"category": "Tech"})
        result = term.to_dict()
        
        expected = {
            "phrase": "API",
            "definition": "Application Programming Interface",
            "metadata": {"category": "Tech"}
        }
        assert result == expected


class TestTermValidator:
    """Test term validation with real scenarios."""
    
    def setup_method(self):
        """Set up validator."""
        self.validator = TermValidator()
    
    def test_clean_and_validate_good_term(self):
        """Test validation of good terms."""
        result = self.validator.clean_and_validate_term(
            "API", "Application Programming Interface"
        )
        
        assert result is not None
        assert result.phrase == "API"
        assert result.definition == "Application Programming Interface."  # Should add period
    
    def test_clean_and_validate_needs_cleaning(self):
        """Test cleaning of terms that need it."""
        result = self.validator.clean_and_validate_term(
            "  api  ", "  application programming interface  "
        )
        
        assert result is not None
        assert result.phrase == "API"  # Should be title-cased and trimmed
        assert result.definition == "Application programming interface."
    
    def test_reject_dangerous_content(self):
        """Test rejection of potentially dangerous content."""
        result = self.validator.clean_and_validate_term(
            "<script>alert('xss')</script>", "Malicious content"
        )
        
        # Should either be rejected or have dangerous content removed
        if result:
            assert "<script>" not in result.phrase
            assert "alert" not in result.phrase
        # Or result could be None if rejected entirely
    
    def test_reject_empty_after_cleaning(self):
        """Test rejection when phrase becomes empty after cleaning."""
        result = self.validator.clean_and_validate_term("   ", "Some definition")
        assert result is None
    
    def test_clean_phrase_normalization(self):
        """Test phrase normalization."""
        cleaned = self.validator.clean_phrase("  api rest service  ")
        assert cleaned == "API REST Service"  # Title case, normalized whitespace
    
    def test_clean_definition_normalization(self):
        """Test definition normalization."""
        cleaned = self.validator.clean_definition("application programming interface")
        assert cleaned == "Application programming interface."  # Capitalized, period added


class TestFileProcessor:
    """Test FileProcessor with real files and data."""
    
    def setup_method(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.processor = FileProcessor()
    
    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    def create_test_file(self, name: str, content: str) -> Path:
        """Helper to create test files."""
        file_path = self.temp_dir / name
        file_path.write_text(content, encoding='utf-8')
        return file_path
    
    def test_process_valid_csv_file(self):
        """Test processing a valid CSV file."""
        csv_content = """phrase,definition,category
API,"Application Programming Interface",Technical
REST,"Representational State Transfer",Technical
JSON,"JavaScript Object Notation",Technical"""
        
        csv_file = self.create_test_file("terms.csv", csv_content)
        terms = self.processor.process_file(csv_file)
        
        assert len(terms) == 3
        assert terms[0].phrase == "API"
        assert terms[0].definition == "Application Programming Interface."
        assert terms[0].metadata.get("category") == "Technical"
    
    def test_process_csv_with_various_column_names(self):
        """Test CSV processing with different column naming conventions."""
        csv_content = """term,description,notes
Microservice,"Small independent service",Architecture
Container,"Lightweight package",DevOps"""
        
        csv_file = self.create_test_file("alt_terms.csv", csv_content)
        terms = self.processor.process_file(csv_file)
        
        assert len(terms) == 2
        assert any(t.phrase == "Microservice" for t in terms)
        assert any(t.phrase == "Container" for t in terms)
    
    def test_process_csv_with_invalid_rows(self):
        """Test CSV processing skips invalid rows."""
        csv_content = """phrase,definition
API,Application Programming Interface
,Empty phrase
REST,
JSON,JavaScript Object Notation"""
        
        csv_file = self.create_test_file("mixed_terms.csv", csv_content)
        terms = self.processor.process_file(csv_file)
        
        # Should only get valid terms
        valid_phrases = [t.phrase for t in terms]
        assert "API" in valid_phrases
        assert "JSON" in valid_phrases
        assert len(terms) <= 2  # Invalid rows should be skipped
    
    def test_process_json_array_format(self):
        """Test processing JSON in array format."""
        json_data = [
            {"phrase": "API", "definition": "Application Programming Interface"},
            {"phrase": "REST", "definition": "Representational State Transfer"}
        ]
        
        json_file = self.create_test_file("terms.json", json.dumps(json_data))
        terms = self.processor.process_file(json_file)
        
        assert len(terms) == 2
        phrases = [t.phrase for t in terms]
        assert "API" in phrases
        assert "REST" in phrases
    
    def test_process_json_glossary_format(self):
        """Test processing JSON with glossary wrapper."""
        json_data = {
            "glossary": [
                {"phrase": "Docker", "definition": "Container platform"},
                {"phrase": "Kubernetes", "definition": "Container orchestration"}
            ]
        }
        
        json_file = self.create_test_file("glossary.json", json.dumps(json_data))
        terms = self.processor.process_file(json_file)
        
        assert len(terms) == 2
        phrases = [t.phrase for t in terms]
        assert "Docker" in phrases
        assert "Kubernetes" in phrases
    
    def test_process_json_key_value_format(self):
        """Test processing JSON as simple key-value pairs."""
        json_data = {
            "API": "Application Programming Interface",
            "REST": "Representational State Transfer"
        }
        
        json_file = self.create_test_file("kv_terms.json", json.dumps(json_data))
        terms = self.processor.process_file(json_file)
        
        assert len(terms) == 2
        phrases = [t.phrase for t in terms]
        assert "API" in phrases
        assert "REST" in phrases
    
    def test_process_yaml_file(self):
        """Test processing YAML file."""
        yaml_data = {
            "glossary": [
                {"phrase": "DevOps", "definition": "Development and Operations practices"},
                {"phrase": "Agile", "definition": "Iterative development methodology"}
            ]
        }
        
        yaml_file = self.create_test_file("terms.yaml", yaml.dump(yaml_data))
        terms = self.processor.process_file(yaml_file)
        
        assert len(terms) == 2
        phrases = [t.phrase for t in terms]
        assert "DevOps" in phrases
        assert "Agile" in phrases
    
    def test_process_multiple_files(self):
        """Test processing multiple files together."""
        # Create CSV file
        csv_content = "phrase,definition\nAPI,Application Programming Interface"
        csv_file = self.create_test_file("terms.csv", csv_content)
        
        # Create JSON file
        json_data = [{"phrase": "REST", "definition": "Representational State Transfer"}]
        json_file = self.create_test_file("terms.json", json.dumps(json_data))
        
        terms = self.processor.process_files([csv_file, json_file])
        
        assert len(terms) == 2
        phrases = [t.phrase for t in terms]
        assert "API" in phrases
        assert "REST" in phrases
    
    def test_deduplication_across_files(self):
        """Test that duplicate terms are removed."""
        # Create first file
        csv_content1 = "phrase,definition\nAPI,First definition"
        csv_file1 = self.create_test_file("terms1.csv", csv_content1)
        
        # Create second file with duplicate
        csv_content2 = "phrase,definition\nAPI,Second definition\nREST,Unique term"
        csv_file2 = self.create_test_file("terms2.csv", csv_content2)
        
        terms = self.processor.process_files([csv_file1, csv_file2])
        
        # Should deduplicate by phrase (case-insensitive)
        phrases = [t.phrase for t in terms]
        assert len(terms) == 2
        assert "API" in phrases
        assert "REST" in phrases
    
    def test_invalid_file_format(self):
        """Test handling of unsupported file formats."""
        txt_file = self.create_test_file("terms.txt", "Some text content")
        
        with pytest.raises(ProcessingError, match="Unsupported file format"):
            self.processor.process_file(txt_file)
    
    def test_malformed_json(self):
        """Test handling of malformed JSON."""
        invalid_json = '{"phrase": "API", "definition": }'  # Missing value
        json_file = self.create_test_file("invalid.json", invalid_json)
        
        with pytest.raises(ProcessingError, match="JSON processing failed"):
            self.processor.process_file(json_file)
    
    def test_malformed_yaml(self):
        """Test handling of malformed YAML."""
        invalid_yaml = "phrase: API\ndefinition: [\n  unclosed"
        yaml_file = self.create_test_file("invalid.yaml", invalid_yaml)
        
        with pytest.raises(ProcessingError, match="YAML processing failed"):
            self.processor.process_file(yaml_file)
    
    def test_missing_required_columns(self):
        """Test handling of CSV with missing required columns."""
        csv_content = "name,value\nSomething,Other"
        csv_file = self.create_test_file("invalid.csv", csv_content)
        
        with pytest.raises(ProcessingError, match="Required columns not found"):
            self.processor.process_file(csv_file)
    
    def test_nonexistent_file(self):
        """Test handling of non-existent files."""
        nonexistent_file = self.temp_dir / "nonexistent.csv"
        
        with pytest.raises(ProcessingError, match="File not found"):
            self.processor.process_file(nonexistent_file)
    
    def test_get_file_info(self):
        """Test getting file information."""
        csv_content = "phrase,definition\nAPI,Application Programming Interface\nREST,Representational State Transfer"
        csv_file = self.create_test_file("info_test.csv", csv_content)
        
        info = self.processor.get_file_info(csv_file)
        
        assert info["path"] == str(csv_file)
        assert info["format"] == ".csv"
        assert info["size"] > 0
        assert info["valid"] is True
        assert info["estimated_terms"] >= 2
    
    def test_column_detection(self):
        """Test automatic column detection."""
        # Test phrase column detection
        columns = ["phrase", "definition", "category"]
        assert self.processor._find_phrase_column(columns) == "phrase"
        
        columns = ["term", "description"]
        assert self.processor._find_phrase_column(columns) == "term"
        
        columns = ["word", "meaning"]
        assert self.processor._find_phrase_column(columns) == "word"
        
        # Test definition column detection
        columns = ["phrase", "definition"]
        assert self.processor._find_definition_column(columns) == "definition"
        
        columns = ["term", "description"]
        assert self.processor._find_definition_column(columns) == "description"
        
        columns = ["phrase", "meaning"]
        assert self.processor._find_definition_column(columns) == "meaning"


class TestFileProcessorIntegration:
    """Integration tests with fixture files."""
    
    def setup_method(self):
        """Set up processor."""
        self.processor = FileProcessor()
        # Assume fixture files exist in tests/fixtures/
        self.fixtures_dir = Path(__file__).parent / "fixtures"
    
    @pytest.mark.skipif(not (Path(__file__).parent / "fixtures" / "valid-terms.csv").exists(), 
                       reason="Fixture file not found")
    def test_process_valid_fixture(self):
        """Test processing the valid terms fixture."""
        fixture_file = self.fixtures_dir / "valid-terms.csv"
        terms = self.processor.process_file(fixture_file)
        
        # Should successfully process the fixture
        assert len(terms) > 0
        
        # Check that all terms have required fields
        for term in terms:
            assert term.phrase
            assert term.definition
            assert isinstance(term.metadata, dict)
    
    @pytest.mark.skipif(not (Path(__file__).parent / "fixtures" / "terms.json").exists(),
                       reason="Fixture file not found")
    def test_process_json_fixture(self):
        """Test processing the JSON fixture."""
        fixture_file = self.fixtures_dir / "terms.json"
        terms = self.processor.process_file(fixture_file)
        
        assert len(terms) > 0
        
        # Verify terms are properly structured
        for term in terms:
            assert term.phrase
            assert term.definition
    
    @pytest.mark.skipif(not (Path(__file__).parent / "fixtures" / "terms.yaml").exists(),
                       reason="Fixture file not found")
    def test_process_yaml_fixture(self):
        """Test processing the YAML fixture."""
        fixture_file = self.fixtures_dir / "terms.yaml"
        terms = self.processor.process_file(fixture_file)
        
        assert len(terms) > 0
        
        # Verify terms are properly structured
        for term in terms:
            assert term.phrase
            assert term.definition


if __name__ == "__main__":
    pytest.main([__file__, "-v"])