"""
Tests for configuration merger module
"""

import pytest
import copy
from datetime import datetime
from unittest.mock import patch

from glossary_updater.merger import ConfigurationMerger, MergeError
from glossary_updater.processor import GlossaryTerm

from . import SAMPLE_CONFIG_DATA


class TestConfigurationMerger:
    """Test cases for ConfigurationMerger class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.merger = ConfigurationMerger()
        self.sample_config = copy.deepcopy(SAMPLE_CONFIG_DATA)
    
    def test_init(self):
        """Test ConfigurationMerger initialization."""
        assert self.merger.glossary_entity_id == "676c6f73-7361-7279-3132-333435363738"
    
    def test_merge_glossary_terms_merge_strategy(self):
        """Test merging with merge strategy."""
        terms = [
            GlossaryTerm("API", "Application Programming Interface"),
            GlossaryTerm("REST", "Representational State Transfer")
        ]
        
        updated_config, merge_stats = self.merger.merge_glossary_terms(
            self.sample_config, terms, "merge"
        )
        
        assert merge_stats["strategy"] == "merge"
        assert merge_stats["terms_provided"] == 2
        assert merge_stats["terms_before"] == 0
        assert merge_stats["terms_after"] == 2
        assert merge_stats["terms_added"] == 2
        assert merge_stats["terms_updated"] == 0
        assert "timestamp" in merge_stats
        
        # Check that configuration was updated
        assert "resourceList" in updated_config
        assert len(updated_config["resourceList"]) == 1
        
        # Check glossary entity was updated
        glossary_entity = updated_config["analysisEntityList"][0]
        assert len(glossary_entity["resources"]) == 1
    
    def test_merge_glossary_terms_overwrite_strategy(self):
        """Test merging with overwrite strategy."""
        terms = [GlossaryTerm("API", "Application Programming Interface")]
        
        updated_config, merge_stats = self.merger.merge_glossary_terms(
            self.sample_config, terms, "overwrite"
        )
        
        assert merge_stats["strategy"] == "overwrite"
        assert merge_stats["terms_after"] == 1
        assert merge_stats["terms_added"] == 1
        assert merge_stats["terms_removed"] == 0
    
    def test_merge_glossary_terms_invalid_strategy(self):
        """Test merging with invalid strategy."""
        terms = [GlossaryTerm("API", "Application Programming Interface")]
        
        with pytest.raises(MergeError, match="Invalid merge strategy"):
            self.merger.merge_glossary_terms(self.sample_config, terms, "invalid")
    
    def test_find_existing_glossary_entity(self):
        """Test finding existing glossary entity."""
        entity = self.merger._find_or_create_glossary_entity(self.sample_config)
        
        assert entity["id"] == self.merger.glossary_entity_id
        assert entity["name"] == "Glossary"
    
    def test_create_new_glossary_entity(self):
        """Test creating new glossary entity."""
        # Remove existing glossary entity
        config = {"analysisEntityList": [], "resourceList": []}
        
        entity = self.merger._find_or_create_glossary_entity(config)
        
        assert entity["id"] == self.merger.glossary_entity_id
        assert entity["name"] == "Glossary"
        assert entity["type"] == "glossary"
        assert entity["enabled"] is True
        assert entity["resources"] == []
        
        # Check entity was added to config
        assert len(config["analysisEntityList"]) == 1
    
    def test_extract_existing_terms_empty(self):
        """Test extracting terms from empty configuration."""
        glossary_entity = self.sample_config["analysisEntityList"][0]
        
        terms = self.merger._extract_existing_terms(self.sample_config, glossary_entity)
        
        assert len(terms) == 0
    
    def test_extract_existing_terms_with_data(self):
        """Test extracting terms from configuration with existing data."""
        # Add some resources to the configuration
        config = copy.deepcopy(self.sample_config)
        resource_id = "test-resource-123"
        
        config["resourceList"].append({
            "id": resource_id,
            "alias": "Test Glossary",
            "type": "glossary",
            "glossary": [
                {"phrase": "API", "definition": "Application Programming Interface"},
                {"phrase": "REST", "definition": "Representational State Transfer"}
            ]
        })
        
        # Update glossary entity to reference this resource
        config["analysisEntityList"][0]["resources"] = [resource_id]
        
        glossary_entity = config["analysisEntityList"][0]
        terms = self.merger._extract_existing_terms(config, glossary_entity)
        
        assert len(terms) == 2
        assert terms[0].phrase == "API"
        assert terms[1].phrase == "REST"
    
    def test_extract_terms_from_resource_glossary_format(self):
        """Test extracting terms from resource with glossary format."""
        resource = {
            "id": "test-resource",
            "glossary": [
                {"phrase": "API", "definition": "Application Programming Interface"},
                {"phrase": "REST", "definition": "Representational State Transfer"}
            ]
        }
        
        terms = self.merger._extract_terms_from_resource(resource)
        
        assert len(terms) == 2
        assert terms[0].phrase == "API"
        assert terms[1].phrase == "REST"
    
    def test_extract_terms_from_resource_terms_format(self):
        """Test extracting terms from resource with terms format."""
        resource = {
            "id": "test-resource",
            "terms": {
                "API": "Application Programming Interface",
                "REST": "Representational State Transfer"
            }
        }
        
        terms = self.merger._extract_terms_from_resource(resource)
        
        assert len(terms) == 2
        phrases = [term.phrase for term in terms]
        assert "API" in phrases
        assert "REST" in phrases
    
    def test_extract_terms_from_resource_direct_format(self):
        """Test extracting terms from resource with direct phrase/definition."""
        resource = {
            "id": "test-resource",
            "phrase": "API",
            "definition": "Application Programming Interface",
            "category": "Technical"
        }
        
        terms = self.merger._extract_terms_from_resource(resource)
        
        assert len(terms) == 1
        assert terms[0].phrase == "API"
        assert terms[0].definition == "Application Programming Interface"
        assert terms[0].metadata.get("category") == "Technical"
    
    def test_merge_terms_new_terms(self):
        """Test merging when all terms are new."""
        existing_terms = []
        new_terms = [
            GlossaryTerm("API", "Application Programming Interface"),
            GlossaryTerm("REST", "Representational State Transfer")
        ]
        
        merged_terms = self.merger._merge_terms(existing_terms, new_terms)
        
        assert len(merged_terms) == 2
        phrases = [term.phrase for term in merged_terms]
        assert "API" in phrases
        assert "REST" in phrases
    
    def test_merge_terms_update_existing(self):
        """Test merging with updates to existing terms."""
        existing_terms = [
            GlossaryTerm("API", "Old definition"),
            GlossaryTerm("REST", "Representational State Transfer")
        ]
        
        new_terms = [
            GlossaryTerm("API", "New definition"),  # Update existing
            GlossaryTerm("JSON", "JavaScript Object Notation")  # Add new
        ]
        
        merged_terms = self.merger._merge_terms(existing_terms, new_terms)
        
        assert len(merged_terms) == 3
        
        # Check API was updated
        api_term = next(term for term in merged_terms if term.phrase == "API")
        assert api_term.definition == "New definition"
        
        # Check REST remained unchanged
        rest_term = next(term for term in merged_terms if term.phrase == "REST")
        assert rest_term.definition == "Representational State Transfer"
        
        # Check JSON was added
        json_term = next(term for term in merged_terms if term.phrase == "JSON")
        assert json_term.definition == "JavaScript Object Notation"
    
    def test_merge_terms_case_insensitive(self):
        """Test that merging is case-insensitive."""
        existing_terms = [GlossaryTerm("API", "Old definition")]
        new_terms = [GlossaryTerm("api", "New definition")]  # Different case
        
        merged_terms = self.merger._merge_terms(existing_terms, new_terms)
        
        assert len(merged_terms) == 1
        assert merged_terms[0].definition == "New definition"
    
    def test_update_configuration_with_terms(self):
        """Test updating configuration with new terms."""
        config = copy.deepcopy(self.sample_config)
        glossary_entity = config["analysisEntityList"][0]
        
        terms = [
            GlossaryTerm("API", "Application Programming Interface"),
            GlossaryTerm("REST", "Representational State Transfer")
        ]
        
        self.merger._update_configuration_with_terms(config, glossary_entity, terms)
        
        # Check resource was created
        assert len(config["resourceList"]) == 1
        resource = config["resourceList"][0]
        assert resource["type"] == "glossary"
        assert len(resource["glossary"]) == 2
        
        # Check glossary entity references the resource
        assert len(glossary_entity["resources"]) == 1
        assert glossary_entity["resources"][0] == resource["id"]
    
    def test_update_configuration_empty_terms(self):
        """Test updating configuration with empty terms."""
        config = copy.deepcopy(self.sample_config)
        glossary_entity = config["analysisEntityList"][0]
        
        self.merger._update_configuration_with_terms(config, glossary_entity, [])
        
        # Should clear resources
        assert len(config["resourceList"]) == 0
        assert len(glossary_entity["resources"]) == 0
    
    def test_update_configuration_replaces_existing(self):
        """Test that updating configuration replaces existing resources."""
        config = copy.deepcopy(self.sample_config)
        
        # Add existing resource
        old_resource_id = "old-resource-123"
        config["resourceList"].append({
            "id": old_resource_id,
            "alias": "Old Glossary",
            "glossary": [{"phrase": "Old", "definition": "Old definition"}]
        })
        config["analysisEntityList"][0]["resources"] = [old_resource_id]
        
        # Update with new terms
        glossary_entity = config["analysisEntityList"][0]
        new_terms = [GlossaryTerm("New", "New definition")]
        
        self.merger._update_configuration_with_terms(config, glossary_entity, new_terms)
        
        # Old resource should be removed
        resource_ids = [r["id"] for r in config["resourceList"]]
        assert old_resource_id not in resource_ids
        
        # New resource should be present
        assert len(config["resourceList"]) == 1
        assert config["resourceList"][0]["glossary"][0]["phrase"] == "New"
    
    def test_validate_configuration_structure_valid(self):
        """Test validation of valid configuration structure."""
        errors = self.merger.validate_configuration_structure(self.sample_config)
        assert len(errors) == 0
    
    def test_validate_configuration_structure_missing_keys(self):
        """Test validation with missing required keys."""
        invalid_config = {"someOtherKey": "value"}
        
        errors = self.merger.validate_configuration_structure(invalid_config)
        
        assert len(errors) >= 2
        error_text = " ".join(errors)
        assert "analysisEntityList" in error_text
        assert "resourceList" in error_text
    
    def test_validate_configuration_structure_invalid_types(self):
        """Test validation with invalid data types."""
        invalid_config = {
            "analysisEntityList": "not a list",
            "resourceList": {"not": "a list"}
        }
        
        errors = self.merger.validate_configuration_structure(invalid_config)
        
        assert len(errors) >= 2
        error_text = " ".join(errors)
        assert "must be a list" in error_text
    
    def test_validate_configuration_structure_invalid_entities(self):
        """Test validation with invalid entities."""
        invalid_config = {
            "analysisEntityList": [
                "not an object",
                {"name": "Missing ID"}
            ],
            "resourceList": []
        }
        
        errors = self.merger.validate_configuration_structure(invalid_config)
        
        assert len(errors) >= 2
        error_text = " ".join(errors)
        assert "must be an object" in error_text
        assert "missing required 'id' field" in error_text
    
    def test_create_backup_config(self):
        """Test creating configuration backup."""
        config_id = "test-config-123"
        
        backup_info = self.merger.create_backup_config(self.sample_config, config_id)
        
        assert backup_info["config_id"] == config_id
        assert "timestamp" in backup_info
        assert "original_size" in backup_info
        assert "entities_count" in backup_info
        assert "resources_count" in backup_info
        assert "backup_config" in backup_info
        
        # Backup should be a deep copy
        assert backup_info["backup_config"] == self.sample_config
        assert backup_info["backup_config"] is not self.sample_config
    
    def test_get_merge_preview_merge_strategy(self):
        """Test merge preview with merge strategy."""
        # Add existing term to config
        config = copy.deepcopy(self.sample_config)
        resource_id = "existing-resource"
        config["resourceList"].append({
            "id": resource_id,
            "glossary": [{"phrase": "API", "definition": "Old definition"}]
        })
        config["analysisEntityList"][0]["resources"] = [resource_id]
        
        new_terms = [
            GlossaryTerm("API", "New definition"),  # Update
            GlossaryTerm("REST", "Representational State Transfer")  # Add
        ]
        
        preview = self.merger.get_merge_preview(config, new_terms, "merge")
        
        assert preview["strategy"] == "merge"
        assert preview["terms_current"] == 1
        assert preview["terms_provided"] == 2
        assert preview["terms_after"] == 2
        assert len(preview["terms_that_would_be_added"]) == 1
        assert len(preview["terms_that_would_be_updated"]) == 1
        assert len(preview["terms_that_would_be_removed"]) == 0
        
        # Check specific terms
        added_term = preview["terms_that_would_be_added"][0]
        assert added_term["phrase"] == "REST"
        
        updated_term = preview["terms_that_would_be_updated"][0]
        assert updated_term["phrase"] == "API"
        assert updated_term["old_definition"] == "Old definition"
        assert updated_term["new_definition"] == "New definition"
    
    def test_get_merge_preview_overwrite_strategy(self):
        """Test merge preview with overwrite strategy."""
        # Add existing terms to config
        config = copy.deepcopy(self.sample_config)
        resource_id = "existing-resource"
        config["resourceList"].append({
            "id": resource_id,
            "glossary": [
                {"phrase": "API", "definition": "Old definition"},
                {"phrase": "OLD", "definition": "Will be removed"}
            ]
        })
        config["analysisEntityList"][0]["resources"] = [resource_id]
        
        new_terms = [GlossaryTerm("REST", "Representational State Transfer")]
        
        preview = self.merger.get_merge_preview(config, new_terms, "overwrite")
        
        assert preview["strategy"] == "overwrite"
        assert preview["terms_current"] == 2
        assert preview["terms_after"] == 1
        assert len(preview["terms_that_would_be_added"]) == 1
        assert len(preview["terms_that_would_be_updated"]) == 0
        assert len(preview["terms_that_would_be_removed"]) == 2
    
    def test_get_merge_preview_no_existing_entity(self):
        """Test merge preview when no glossary entity exists."""
        config = {"analysisEntityList": [], "resourceList": []}
        new_terms = [GlossaryTerm("API", "Application Programming Interface")]
        
        preview = self.merger.get_merge_preview(config, new_terms, "merge")
        
        assert preview["glossary_entity_exists"] is False
        assert preview["terms_current"] == 0
        assert preview["terms_after"] == 1
    
    def test_log_merge_results(self):
        """Test logging of merge results."""
        merge_stats = {
            "strategy": "merge",
            "terms_before": 5,
            "terms_after": 8,
            "terms_added": 3,
            "terms_updated": 0
        }
        
        # Should not raise any exceptions
        self.merger._log_merge_results(merge_stats)
    
    def test_merge_with_metadata_preservation(self):
        """Test that metadata is preserved during merge operations."""
        terms = [
            GlossaryTerm("API", "Application Programming Interface", {"category": "Technical", "priority": "High"})
        ]
        
        updated_config, merge_stats = self.merger.merge_glossary_terms(
            self.sample_config, terms, "merge"
        )
        
        # Find the created resource
        resource = updated_config["resourceList"][0]
        glossary_item = resource["glossary"][0]
        
        assert glossary_item["phrase"] == "API"
        assert glossary_item["definition"] == "Application Programming Interface"
        assert glossary_item["metadata"]["category"] == "Technical"
        assert glossary_item["metadata"]["priority"] == "High"


class TestConfigurationMergerErrorHandling:
    """Test error handling in ConfigurationMerger."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.merger = ConfigurationMerger()
    
    def test_merge_with_malformed_config(self):
        """Test merging with malformed configuration."""
        malformed_config = {"invalid": "structure"}
        terms = [GlossaryTerm("API", "Application Programming Interface")]
        
        # Should handle gracefully by creating required structure
        updated_config, merge_stats = self.merger.merge_glossary_terms(
            malformed_config, terms, "merge"
        )
        
        assert "analysisEntityList" in updated_config
        assert "resourceList" in updated_config
        assert merge_stats["terms_after"] == 1
    
    def test_extract_terms_with_invalid_resource_structure(self):
        """Test extracting terms from resources with invalid structure."""
        resource = {
            "id": "test-resource",
            "glossary": [
                {"phrase": "API", "definition": "Valid term"},
                {"phrase": "Invalid"},  # Missing definition
                {"definition": "Missing phrase"},  # Missing phrase
                "not an object"  # Invalid item type
            ]
        }
        
        # Should extract only valid terms
        terms = self.merger._extract_terms_from_resource(resource)
        
        assert len(terms) == 1
        assert terms[0].phrase == "API"
    
    def test_merge_with_none_values(self):
        """Test merging with None values in configuration."""
        config = {
            "analysisEntityList": None,
            "resourceList": None
        }
        
        terms = [GlossaryTerm("API", "Application Programming Interface")]
        
        # Should handle None values gracefully
        try:
            updated_config, merge_stats = self.merger.merge_glossary_terms(config, terms, "merge")
            # If successful, check results
            assert merge_stats["terms_after"] >= 1
        except (MergeError, TypeError):
            # If it raises an error, it should be a specific error type
            pass


if __name__ == "__main__":
    pytest.main([__file__])
