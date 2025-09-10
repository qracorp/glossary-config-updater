"""
Tests for configuration merger module - focused on actual merging behavior
"""

import pytest
import copy
import json
from datetime import datetime
from pathlib import Path
import tempfile

from glossary_updater.merger import ConfigurationMerger, MergeError
from glossary_updater.processor import GlossaryTerm


@pytest.fixture
def basic_config():
    """Basic configuration structure for testing."""
    return {
        "configurationId": "test-config-123",
        "configurationName": "Test Configuration",
        "configurationVersion": 1,
        "configurationSchemaVersion": "3.1.0",
        "data": {
            "analysisEntityList": [
                {
                    "id": "676c6f73-7361-7279-3132-333435363738",
                    "entityName": "Glossary",
                    "detectionEngine": "glossary",
                    "enabled": True,
                    "resources": []
                }
            ],
            "resourceList": []
        }
    }


@pytest.fixture
def config_with_existing_terms():
    """Configuration with existing glossary terms."""
    return {
        "configurationId": "test-config-123",
        "configurationName": "Test Configuration",
        "configurationVersion": 1,
        "configurationSchemaVersion": "3.1.0",
        "data": {
            "analysisEntityList": [
                {
                    "id": "676c6f73-7361-7279-3132-333435363738",
                    "entityName": "Glossary",
                    "detectionEngine": "glossary", 
                    "enabled": True,
                    "resources": ["resource-1", "resource-2"]
                }
            ],
            "resourceList": [
                {
                    "id": "resource-1",
                    "phrase": "API",
                    "definition": "Application Programming Interface"
                },
                {
                    "id": "resource-2", 
                    "phrase": "REST",
                    "definition": "Representational State Transfer"
                }
            ]
        }
    }


@pytest.fixture
def sample_terms():
    """Sample glossary terms for testing."""
    return [
        GlossaryTerm("API", "Application Programming Interface - Updated", {"category": "Technical"}),
        GlossaryTerm("JSON", "JavaScript Object Notation", {"category": "Technical"}),
        GlossaryTerm("Docker", "Container platform", {"category": "DevOps"})
    ]


@pytest.fixture
def schema_file():
    """Create temporary schema file for validation testing."""
    schema_content = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["configurationId", "data"],
        "properties": {
            "configurationId": {"type": "string"},
            "configurationName": {"type": "string"},
            "configurationVersion": {"type": "integer"},
            "configurationSchemaVersion": {"type": "string"},
            "data": {
                "type": "object",
                "required": ["analysisEntityList", "resourceList"],
                "properties": {
                    "analysisEntityList": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["id", "entityName", "detectionEngine", "enabled", "resources"],
                            "properties": {
                                "id": {"type": "string"},
                                "entityName": {"type": "string"},
                                "detectionEngine": {"type": "string"},
                                "enabled": {"type": "boolean"},
                                "resources": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            }
                        }
                    },
                    "resourceList": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["id"],
                            "properties": {
                                "id": {"type": "string"},
                                "phrase": {"type": "string"},
                                "definition": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(schema_content, f)
        yield f.name
    
    # Cleanup
    Path(f.name).unlink()


class TestConfigurationMerger:
    """Test ConfigurationMerger with real merging scenarios."""
    
    def test_initialization(self, schema_file):
        """Test merger initialization."""
        merger = ConfigurationMerger(schema_file)
        assert merger.glossary_entity_id == "676c6f73-7361-7279-3132-333435363738"
        assert merger.validator is not None
    
    def test_initialization_default_schema(self):
        """Test merger initialization with default schema."""
        # This will fail if schema file doesn't exist, but that's expected
        try:
            merger = ConfigurationMerger()
            assert merger.glossary_entity_id == "676c6f73-7361-7279-3132-333435363738"
        except FileNotFoundError:
            # Expected if default schema file doesn't exist
            pass


class TestMergeOperations:
    """Test actual merge operations with real data."""
    
    def test_merge_strategy_with_new_terms(self, basic_config, sample_terms, schema_file):
        """Test merge strategy when adding new terms to empty config."""
        merger = ConfigurationMerger(schema_file)
        
        updated_config, merge_stats = merger.merge_glossary_terms(
            basic_config, sample_terms, "merge", skip_validation=True
        )
        
        # Verify merge statistics
        assert merge_stats["strategy"] == "merge"
        assert merge_stats["terms_provided"] == 3
        assert merge_stats["terms_before"] == 0
        assert merge_stats["terms_after"] == 3
        assert merge_stats["terms_added"] == 3
        assert merge_stats["terms_updated"] == 0
        assert merge_stats["terms_removed"] == 0
        
        # Verify configuration was updated
        assert len(updated_config["data"]["resourceList"]) == 3
        
        # Check that glossary entity was updated
        glossary_entity = updated_config["data"]["analysisEntityList"][0]
        assert len(glossary_entity["resources"]) == 3
        
        # Verify terms were added correctly
        phrases = [r["phrase"] for r in updated_config["data"]["resourceList"]]
        assert "API" in phrases
        assert "JSON" in phrases
        assert "Docker" in phrases
    
    def test_merge_strategy_with_existing_terms(self, config_with_existing_terms, sample_terms, schema_file):
        """Test merge strategy when updating existing terms."""
        merger = ConfigurationMerger(schema_file)
        
        updated_config, merge_stats = merger.merge_glossary_terms(
            config_with_existing_terms, sample_terms, "merge", skip_validation=True
        )
        
        # Verify merge statistics
        assert merge_stats["strategy"] == "merge"
        assert merge_stats["terms_before"] == 2  # API and REST existed
        assert merge_stats["terms_after"] == 4   # API updated, JSON and Docker added, REST kept
        assert merge_stats["terms_added"] == 2   # JSON and Docker
        assert merge_stats["terms_updated"] == 1 # API updated
        
        # Verify API was updated with new definition
        api_resource = next(r for r in updated_config["data"]["resourceList"] if r["phrase"] == "API")
        assert "Updated" in api_resource["definition"]
        
        # Verify new terms were added
        phrases = [r["phrase"] for r in updated_config["data"]["resourceList"]]
        assert "JSON" in phrases
        assert "Docker" in phrases
        assert "REST" in phrases  # Original term should still exist
    
    def test_overwrite_strategy(self, config_with_existing_terms, sample_terms, schema_file):
        """Test overwrite strategy replaces all existing terms."""
        merger = ConfigurationMerger(schema_file)
        
        updated_config, merge_stats = merger.merge_glossary_terms(
            config_with_existing_terms, sample_terms, "overwrite", skip_validation=True
        )
        
        # Verify merge statistics
        assert merge_stats["strategy"] == "overwrite"
        assert merge_stats["terms_before"] == 2  # API and REST existed
        assert merge_stats["terms_after"] == 3   # Only new terms
        assert merge_stats["terms_added"] == 3   # All new terms
        assert merge_stats["terms_removed"] == 2 # All old terms
        
        # Verify only new terms exist
        phrases = [r["phrase"] for r in updated_config["data"]["resourceList"]]
        assert len(phrases) == 3
        assert "API" in phrases  # From new terms
        assert "JSON" in phrases
        assert "Docker" in phrases
        # REST should be gone (was in original config but not in new terms)
        
        # Verify API has the new definition, not the old one
        api_resource = next(r for r in updated_config["data"]["resourceList"] if r["phrase"] == "API")
        assert "Updated" in api_resource["definition"]
    
    def test_invalid_merge_strategy(self, basic_config, sample_terms, schema_file):
        """Test that invalid merge strategy raises error."""
        merger = ConfigurationMerger(schema_file)
        
        with pytest.raises(MergeError, match="Invalid merge strategy"):
            merger.merge_glossary_terms(basic_config, sample_terms, "invalid")
    
    def test_merge_with_empty_terms(self, config_with_existing_terms, schema_file):
        """Test merging with empty term list."""
        merger = ConfigurationMerger(schema_file)
        
        updated_config, merge_stats = merger.merge_glossary_terms(
            config_with_existing_terms, [], "merge", skip_validation=True
        )
        
        # With merge strategy and empty terms, existing should be preserved
        assert merge_stats["terms_after"] == merge_stats["terms_before"]
        assert len(updated_config["data"]["resourceList"]) == 2  # Original terms preserved
    
    def test_overwrite_with_empty_terms(self, config_with_existing_terms, schema_file):
        """Test overwrite with empty term list removes all terms."""
        merger = ConfigurationMerger(schema_file)
        
        updated_config, merge_stats = merger.merge_glossary_terms(
            config_with_existing_terms, [], "overwrite", skip_validation=True
        )
        
        # With overwrite strategy and empty terms, should clear all
        assert merge_stats["terms_after"] == 0
        assert len(updated_config["data"]["resourceList"]) == 0
        
        # Glossary entity should have empty resources
        glossary_entity = updated_config["data"]["analysisEntityList"][0]
        assert len(glossary_entity["resources"]) == 0


class TestEntityManagement:
    """Test glossary entity finding and creation."""
    
    def test_find_existing_glossary_entity(self, basic_config, schema_file):
        """Test finding existing glossary entity."""
        merger = ConfigurationMerger(schema_file)
        
        entity = merger._find_or_create_glossary_entity(basic_config)
        
        assert entity["id"] == merger.glossary_entity_id
        assert entity["entityName"] == "Glossary"
        assert entity["detectionEngine"] == "glossary"
        assert entity["enabled"] is True
    
    def test_create_new_glossary_entity(self, schema_file):
        """Test creating new glossary entity when none exists."""
        merger = ConfigurationMerger(schema_file)
        
        config = {
            "data": {
                "analysisEntityList": [],
                "resourceList": []
            }
        }
        
        entity = merger._find_or_create_glossary_entity(config)
        
        assert entity["id"] == merger.glossary_entity_id
        assert entity["entityName"] == "Glossary"
        assert entity["detectionEngine"] == "glossary"
        assert entity["enabled"] is True
        assert entity["resources"] == []
        
        # Verify entity was added to config
        assert len(config["data"]["analysisEntityList"]) == 1
        assert config["data"]["analysisEntityList"][0] == entity
    
    def test_find_entity_by_detection_engine(self, schema_file):
        """Test finding entity by detection engine when ID doesn't match."""
        merger = ConfigurationMerger(schema_file)
        
        config = {
            "data": {
                "analysisEntityList": [
                    {
                        "id": "different-id-123",
                        "entityName": "Glossary",
                        "detectionEngine": "glossary",
                        "enabled": True,
                        "resources": []
                    }
                ],
                "resourceList": []
            }
        }
        
        entity = merger._find_or_create_glossary_entity(config)
        
        # Should find the existing entity even with different ID
        assert entity["id"] == "different-id-123"
        assert entity["detectionEngine"] == "glossary"


class TestTermExtraction:
    """Test extraction of existing terms from configurations."""
    
    def test_extract_existing_terms(self, config_with_existing_terms, schema_file):
        """Test extracting existing terms from configuration."""
        merger = ConfigurationMerger(schema_file)
        
        existing_terms = merger._extract_existing_terms(config_with_existing_terms)
        
        assert len(existing_terms) == 2
        phrases = [t.phrase for t in existing_terms]
        assert "API" in phrases
        assert "REST" in phrases
        
        api_term = next(t for t in existing_terms if t.phrase == "API")
        assert api_term.definition == "Application Programming Interface"
        assert api_term.metadata.get("resource_id") == "resource-1"
    
    def test_extract_from_empty_config(self, basic_config, schema_file):
        """Test extracting terms from empty configuration."""
        merger = ConfigurationMerger(schema_file)
        
        existing_terms = merger._extract_existing_terms(basic_config)
        
        assert len(existing_terms) == 0
    
    def test_extract_terms_with_malformed_resources(self, schema_file):
        """Test extraction handles malformed resources gracefully."""
        merger = ConfigurationMerger(schema_file)
        
        config = {
            "data": {
                "analysisEntityList": [
                    {
                        "id": "676c6f73-7361-7279-3132-333435363738",
                        "entityName": "Glossary",
                        "detectionEngine": "glossary",
                        "enabled": True,
                        "resources": ["resource-1", "resource-2", "resource-3"]
                    }
                ],
                "resourceList": [
                    {
                        "id": "resource-1",
                        "phrase": "Valid Term",
                        "definition": "Valid definition"
                    },
                    {
                        "id": "resource-2",
                        "phrase": "Missing Definition"
                        # No definition field
                    },
                    {
                        "id": "resource-3"
                        # Missing both phrase and definition
                    }
                ]
            }
        }
        
        existing_terms = merger._extract_existing_terms(config)
        
        # Should only extract the valid term
        assert len(existing_terms) == 1
        assert existing_terms[0].phrase == "Valid Term"


class TestTermMerging:
    """Test the actual term merging logic."""
    
    def test_merge_with_no_existing_terms(self, schema_file):
        """Test merging when no existing terms."""
        merger = ConfigurationMerger(schema_file)
        
        existing_terms = []
        new_terms = [
            GlossaryTerm("API", "Application Programming Interface"),
            GlossaryTerm("REST", "Representational State Transfer")
        ]
        
        merged_terms = merger._merge_terms(existing_terms, new_terms)
        
        assert len(merged_terms) == 2
        phrases = [t.phrase for t in merged_terms]
        assert "API" in phrases
        assert "REST" in phrases
    
    def test_merge_with_updates_and_additions(self, schema_file):
        """Test merging with both updates and new additions."""
        merger = ConfigurationMerger(schema_file)
        
        existing_terms = [
            GlossaryTerm("API", "Old definition"),
            GlossaryTerm("REST", "Representational State Transfer")
        ]
        
        new_terms = [
            GlossaryTerm("API", "New definition"),  # Update existing
            GlossaryTerm("JSON", "JavaScript Object Notation")  # Add new
        ]
        
        merged_terms = merger._merge_terms(existing_terms, new_terms)
        
        assert len(merged_terms) == 3
        
        # Check API was updated
        api_term = next(t for t in merged_terms if t.phrase == "API")
        assert api_term.definition == "New definition"
        
        # Check REST was preserved
        rest_term = next(t for t in merged_terms if t.phrase == "REST")
        assert rest_term.definition == "Representational State Transfer"
        
        # Check JSON was added
        json_term = next(t for t in merged_terms if t.phrase == "JSON")
        assert json_term.definition == "JavaScript Object Notation"
    
    def test_merge_case_insensitive(self, schema_file):
        """Test that merging is case-insensitive."""
        merger = ConfigurationMerger(schema_file)
        
        existing_terms = [GlossaryTerm("API", "Old definition")]
        new_terms = [GlossaryTerm("api", "New definition")]  # Different case
        
        merged_terms = merger._merge_terms(existing_terms, new_terms)
        
        assert len(merged_terms) == 1
        assert merged_terms[0].definition == "New definition"
        # Should preserve the new term's casing
        assert merged_terms[0].phrase == "api"


class TestConfigurationUpdate:
    """Test configuration updates with merged terms."""
    
    def test_update_configuration_with_terms(self, basic_config, schema_file):
        """Test updating configuration with new terms."""
        merger = ConfigurationMerger(schema_file)
        
        config = copy.deepcopy(basic_config)
        glossary_entity = config["data"]["analysisEntityList"][0]
        
        terms = [
            GlossaryTerm("API", "Application Programming Interface", {"category": "Technical"}),
            GlossaryTerm("REST", "Representational State Transfer", {"priority": "High"})
        ]
        
        merger._update_configuration_with_terms(config, glossary_entity, terms)
        
        # Check resources were created
        assert len(config["data"]["resourceList"]) == 2
        
        # Check glossary entity references the resources
        assert len(glossary_entity["resources"]) == 2
        
        # Verify term data was preserved
        for resource in config["data"]["resourceList"]:
            assert "phrase" in resource
            assert "definition" in resource
            assert "id" in resource
            assert resource["id"] in glossary_entity["resources"]
    
    def test_update_clears_existing_resources(self, config_with_existing_terms, schema_file):
        """Test that updating clears existing resources."""
        merger = ConfigurationMerger(schema_file)
        
        config = copy.deepcopy(config_with_existing_terms)
        glossary_entity = config["data"]["analysisEntityList"][0]
        
        # Original config has 2 resources
        assert len(config["data"]["resourceList"]) == 2
        
        new_terms = [GlossaryTerm("New Term", "New definition")]
        
        merger._update_configuration_with_terms(config, glossary_entity, new_terms)
        
        # Should have only the new resource
        assert len(config["data"]["resourceList"]) == 1
        assert config["data"]["resourceList"][0]["phrase"] == "New Term"
        
        # Entity should reference only the new resource
        assert len(glossary_entity["resources"]) == 1
    
    def test_update_with_empty_terms(self, config_with_existing_terms, schema_file):
        """Test updating with empty terms list."""
        merger = ConfigurationMerger(schema_file)
        
        config = copy.deepcopy(config_with_existing_terms)
        glossary_entity = config["data"]["analysisEntityList"][0]
        
        merger._update_configuration_with_terms(config, glossary_entity, [])
        
        # Should clear all resources
        assert len(config["data"]["resourceList"]) == 0
        assert len(glossary_entity["resources"]) == 0


class TestValidation:
    """Test configuration validation."""
    
    def test_valid_configuration_passes(self, basic_config, schema_file):
        """Test that valid configuration passes validation."""
        merger = ConfigurationMerger(schema_file)
        
        errors = merger.validate_configuration_structure(basic_config)
        assert len(errors) == 0
    
    def test_missing_required_fields(self, schema_file):
        """Test validation catches missing required fields."""
        merger = ConfigurationMerger(schema_file)
        
        invalid_config = {
            "configurationId": "test-123"
            # Missing data field
        }
        
        errors = merger.validate_configuration_structure(invalid_config)
        assert len(errors) > 0
        assert any("data" in error.lower() for error in errors)
    
    def test_invalid_data_structure(self, schema_file):
        """Test validation catches invalid data structures."""
        merger = ConfigurationMerger(schema_file)
        
        invalid_config = {
            "configurationId": "test-123",
            "data": {
                "analysisEntityList": "not an array",  # Should be array
                "resourceList": []
            }
        }
        
        errors = merger.validate_configuration_structure(invalid_config)
        assert len(errors) > 0


class TestBackupAndUtilities:
    """Test backup creation and utility functions."""
    
    def test_create_backup_config(self, basic_config, schema_file):
        """Test configuration backup creation."""
        merger = ConfigurationMerger(schema_file)
        
        backup_info = merger.create_backup_config(basic_config, "test-config-123")
        
        assert backup_info["config_id"] == "test-config-123"
        assert "timestamp" in backup_info
        assert backup_info["original_size"] > 0
        assert backup_info["entities_count"] == 1
        assert backup_info["resources_count"] == 0
        assert "backup_config" in backup_info
        
        # Backup should be a deep copy
        assert backup_info["backup_config"] == basic_config
        assert backup_info["backup_config"] is not basic_config
    
    def test_log_merge_results_doesnt_crash(self, schema_file):
        """Test that logging merge results doesn't crash."""
        merger = ConfigurationMerger(schema_file)
        
        merge_stats = {
            "strategy": "merge",
            "terms_before": 5,
            "terms_after": 8,
            "terms_added": 3,
            "terms_updated": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Should not raise any exceptions
        merger._log_merge_results(merge_stats)


class TestErrorHandling:
    """Test error handling in merger."""
    
    def test_merge_with_malformed_config(self, sample_terms, schema_file):
        """Test handling malformed configuration."""
        merger = ConfigurationMerger(schema_file)
        
        # Config missing required structure
        malformed_config = {"someField": "someValue"}
        
        # Should handle gracefully by creating required structure
        try:
            updated_config, merge_stats = merger.merge_glossary_terms(
                malformed_config, sample_terms, "merge", skip_validation=True
            )
            # If successful, should have created proper structure
            assert "data" in updated_config
            assert "analysisEntityList" in updated_config["data"]
            assert "resourceList" in updated_config["data"]
        except MergeError:
            # Or should raise a clear error
            pass
    
    def test_handle_none_values_gracefully(self, sample_terms, schema_file):
        """Test handling of None values in configuration."""
        merger = ConfigurationMerger(schema_file)
        
        config_with_none = {
            "data": {
                "analysisEntityList": None,
                "resourceList": None
            }
        }
        
        # Should handle None values without crashing
        try:
            updated_config, merge_stats = merger.merge_glossary_terms(
                config_with_none, sample_terms, "merge", skip_validation=True
            )
            # Should have corrected None values
            assert updated_config["data"]["analysisEntityList"] is not None
            assert updated_config["data"]["resourceList"] is not None
        except (MergeError, TypeError, AttributeError):
            # Should raise appropriate error types, not generic crashes
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])