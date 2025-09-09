"""
Configuration merger for updating glossary terms with JSON Schema validation.

Handles merging or overwriting glossary terms in API configurations with safety checks.
"""

import copy
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .processor import GlossaryTerm
from .utils import logger, generate_resource_id


class MergeError(Exception):
    """Exception raised during configuration merging."""
    pass


def _install_jsonschema():
    """Install jsonschema if not available."""
    try:
        import subprocess
        import sys
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'jsonschema'])
        logger.info("jsonschema installed successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to install jsonschema: {e}")
        return False


# Try to import jsonschema
try:
    import jsonschema
    from jsonschema import validate, ValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    jsonschema = None
    validate = None
    ValidationError = None
    JSONSCHEMA_AVAILABLE = False


class ConfigurationValidator:
    """Validates configuration structure using JSON Schema."""
    
    def __init__(self, schema_file: str = "qvscribe_schema_3_1_0.json"):
        """
        Initialize with JSON Schema file.
        
        Args:
            schema_file: Path to JSON schema file.
        """
        global jsonschema, validate, ValidationError, JSONSCHEMA_AVAILABLE
        
        if not JSONSCHEMA_AVAILABLE:
            logger.warning("jsonschema library not available. Installing...")
            if _install_jsonschema():
                try:
                    import jsonschema
                    from jsonschema import validate, ValidationError
                    JSONSCHEMA_AVAILABLE = True
                except ImportError as e:
                    raise ImportError(f"jsonschema library is required but could not be installed: {e}")
            else:
                raise ImportError("jsonschema library is required but not available and could not be installed")
        
        self.schema_file = schema_file
        self.schema = self.load_schema()
    
    def load_schema(self) -> Dict[str, Any]:
        """Load JSON schema from file."""
        schema_path = Path(self.schema_file)
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        try:
            with open(schema_path, 'r') as f:
                schema = json.load(f)
            logger.debug(f"Loaded JSON schema from {schema_path}")
            return schema
        except Exception as e:
            logger.error(f"Failed to load schema from {schema_path}: {e}")
            raise
    
    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate configuration against JSON schema.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        if not isinstance(config, dict):
            return False, ["Configuration must be a dictionary/object"]
        
        try:
            # Validate against JSON schema
            validate(instance=config, schema=self.schema)
            logger.debug("Configuration passed JSON schema validation")
            return True, []
            
        except ValidationError as e:
            # Convert validation error to readable message
            error_path = " -> ".join(str(p) for p in e.path) if e.path else "root"
            error_msg = f"Validation error at '{error_path}': {e.message}"
            
            logger.debug(f"JSON Schema validation failed: {error_msg}")
            return False, [error_msg]
            
        except Exception as e:
            error_msg = f"Schema validation error: {str(e)}"
            logger.error(error_msg)
            return False, [error_msg]


class ConfigurationMerger:
    """Handles merging glossary terms into configurations with JSON schema validation."""
    
    def __init__(self, schema_file: str = "qvscribe_schema_3_1_0.json"):
        """
        Initialize configuration merger with JSON schema validation.
        
        Args:
            schema_file: Path to JSON schema file for validation
        """
        self.glossary_entity_id = "676c6f73-7361-7279-3132-333435363738"
        self.validator = ConfigurationValidator(schema_file)
    
    def merge_glossary_terms(self, 
                           config: Dict[str, Any], 
                           terms: List[GlossaryTerm],
                           strategy: str = "merge",
                           skip_validation: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Merge glossary terms into configuration with JSON schema validation.
        
        Args:
            config: Original configuration
            terms: List of validated glossary terms
            strategy: Merge strategy ("merge" or "overwrite")
            skip_validation: Skip validation (useful for testing)
            
        Returns:
            Tuple of (updated_config, merge_stats)
        """
        if strategy not in ["merge", "overwrite"]:
            raise MergeError(f"Invalid merge strategy: {strategy}")
        
        logger.info(f"Starting {strategy} operation with {len(terms)} terms")
        
        # Step 1: Validate input configuration (unless skipped)
        if not skip_validation:
            logger.debug("Validating input configuration against JSON schema...")
            is_valid, validation_errors = self.validator.validate_configuration(config)
            if not is_valid:
                logger.warning(f"Configuration validation failed: {validation_errors}")
                raise MergeError(f"Input configuration validation failed: {'; '.join(validation_errors[:3])}")
        else:
            logger.debug("Skipping input validation as requested")
        
        # Step 2: Create working copy
        updated_config = copy.deepcopy(config)
        
        # Initialize merge statistics
        merge_stats = {
            "strategy": strategy,
            "terms_provided": len(terms),
            "terms_before": 0,
            "terms_after": 0,
            "terms_added": 0,
            "terms_updated": 0,
            "terms_removed": 0,
            "glossary_entity_found": False,
            "validation_passed": True,
            "validation_skipped": skip_validation,
            "backup_created": True,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Step 3: Find or create glossary entity
            logger.debug("Finding or creating glossary entity...")
            glossary_entity = self._find_or_create_glossary_entity(updated_config)
            merge_stats["glossary_entity_found"] = glossary_entity is not None
            
            # Step 4: Extract existing terms
            logger.debug("Extracting existing terms...")
            existing_terms = self._extract_existing_terms(updated_config)
            merge_stats["terms_before"] = len(existing_terms)
            
            # Step 5: Perform merge operation
            if strategy == "merge":
                final_terms = self._merge_terms(existing_terms, terms)
                merge_stats["terms_added"] = len([t for t in terms if t.phrase.lower() not in 
                                                [et.phrase.lower() for et in existing_terms]])
                merge_stats["terms_updated"] = len(terms) - merge_stats["terms_added"]
            else:  # overwrite
                final_terms = terms
                merge_stats["terms_added"] = len(terms)
                merge_stats["terms_removed"] = len(existing_terms)
            
            # Step 6: Update configuration with new terms
            logger.debug("Updating configuration with merged terms...")
            self._update_configuration_with_terms(updated_config, glossary_entity, final_terms)
            merge_stats["terms_after"] = len(final_terms)
            
            # Step 7: Validate final configuration (unless skipped)
            if not skip_validation:
                logger.debug("Validating final configuration against JSON schema...")
                final_valid, final_errors = self.validator.validate_configuration(updated_config)
                if not final_valid:
                    merge_stats["validation_passed"] = False
                    logger.warning(f"Final configuration validation failed: {final_errors}")
                    raise MergeError(f"Final configuration validation failed: {'; '.join(final_errors[:3])}")
            
            # Step 8: Log results
            self._log_merge_results(merge_stats)
            
            return updated_config, merge_stats
            
        except Exception as e:
            logger.error(f"Merge operation failed: {str(e)}")
            merge_stats["validation_passed"] = False
            raise MergeError(f"Failed to merge glossary terms: {str(e)}")
    
    def _find_or_create_glossary_entity(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Find existing glossary entity or create a new one."""
        # Your API structure has data.analysisEntityList
        data = config.get("data", {})
        entity_list = data.get("analysisEntityList", [])
        
        # Look for existing glossary entity
        for entity in entity_list:
            if (entity.get("id") == self.glossary_entity_id or 
                entity.get("entityName", "").lower() == "glossary" or
                entity.get("detectionEngine") == "glossary"):
                logger.debug("Found existing glossary entity")
                return entity
        
        # Create new glossary entity
        logger.info("Creating new glossary entity")
        new_entity = {
            "id": self.glossary_entity_id,
            "entityName": "Glossary",
            "detectionEngine": "glossary",
            "enabled": True,
            "resources": []
        }
        
        entity_list.append(new_entity)
        data["analysisEntityList"] = entity_list
        
        return new_entity
    
    def _extract_existing_terms(self, config: Dict[str, Any]) -> List[GlossaryTerm]:
        """Extract existing glossary terms from resourceList."""
        existing_terms = []
        
        # Your API structure has data.resourceList
        data = config.get("data", {})
        resource_list = data.get("resourceList", [])
        
        # Look for glossary terms in resourceList
        # Based on your schema, glossary terms have: id, phrase, definition
        for resource in resource_list:
            if "phrase" in resource and "definition" in resource:
                try:
                    phrase = str(resource["phrase"]).strip()
                    definition = str(resource["definition"]).strip()
                    
                    if phrase and definition:
                        term = GlossaryTerm(
                            phrase=phrase,
                            definition=definition,
                            metadata={"resource_id": resource.get("id", "")}
                        )
                        existing_terms.append(term)
                except Exception as e:
                    logger.warning(f"Error processing existing term: {str(e)}")
        
        logger.debug(f"Found {len(existing_terms)} existing glossary terms")
        return existing_terms
    
    def _merge_terms(self, existing_terms: List[GlossaryTerm], 
                    new_terms: List[GlossaryTerm]) -> List[GlossaryTerm]:
        """Merge new terms with existing terms."""
        # Create lookup for existing terms (case-insensitive)
        existing_lookup = {term.phrase.lower(): term for term in existing_terms}
        
        # Start with existing terms
        merged_terms = list(existing_terms)
        
        # Add or update with new terms
        for new_term in new_terms:
            phrase_lower = new_term.phrase.lower()
            
            if phrase_lower in existing_lookup:
                # Update existing term
                logger.debug(f"Updating term: {new_term.phrase}")
                for i, term in enumerate(merged_terms):
                    if term.phrase.lower() == phrase_lower:
                        merged_terms[i] = new_term
                        break
            else:
                # Add new term
                logger.debug(f"Adding new term: {new_term.phrase}")
                merged_terms.append(new_term)
        
        return merged_terms
    
    def _update_configuration_with_terms(self,
                                       config: Dict[str, Any],
                                       glossary_entity: Dict[str, Any],
                                       terms: List[GlossaryTerm]) -> None:
        """Update configuration with validated terms."""
        data = config.get("data", {})
        resource_list = data.get("resourceList", [])
        
        # Remove existing glossary terms (resources with phrase/definition)
        resource_list = [r for r in resource_list 
                        if not ("phrase" in r and "definition" in r)]
        
        # Add new glossary terms as individual resources
        new_resource_ids = []
        for term in terms:
            resource_id = generate_resource_id()
            new_resource_ids.append(resource_id)
            
            glossary_resource = {
                "id": resource_id,
                "phrase": term.phrase,
                "definition": term.definition
            }
            
            resource_list.append(glossary_resource)
        
        # Update the data structure
        data["resourceList"] = resource_list
        config["data"] = data
        
        # Update entity to reference the new resources
        glossary_entity["resources"] = new_resource_ids
        
        logger.debug(f"Updated configuration with {len(terms)} glossary terms")
    
    def _log_merge_results(self, stats: Dict[str, Any]) -> None:
        """Log merge operation results."""
        strategy = stats["strategy"]
        
        logger.info(f"Merge operation completed:")
        logger.info(f"  Strategy: {strategy}")
        logger.info(f"  Terms before: {stats['terms_before']}")
        logger.info(f"  Terms after: {stats['terms_after']}")
        
        if strategy == "merge":
            logger.info(f"  Terms added: {stats['terms_added']}")
            logger.info(f"  Terms updated: {stats['terms_updated']}")
        else:
            logger.info(f"  Terms added: {stats['terms_added']}")
            logger.info(f"  Terms removed: {stats['terms_removed']}")
        
        net_change = stats['terms_after'] - stats['terms_before']
        if net_change > 0:
            logger.info(f"  Net change: +{net_change} terms")
        elif net_change < 0:
            logger.info(f"  Net change: {net_change} terms")
        else:
            logger.info(f"  Net change: 0 terms")
        
        if stats.get('validation_skipped'):
            logger.info(f"  Validation: SKIPPED")
        else:
            logger.info(f"  Validation: {'PASSED' if stats['validation_passed'] else 'FAILED'}")
    
    def validate_configuration_structure(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration structure using JSON schema."""
        is_valid, errors = self.validator.validate_configuration(config)
        return errors
    
    def create_backup_config(self, config: Dict[str, Any], config_id: str) -> Dict[str, Any]:
        """Create a backup of the configuration before modification."""
        backup_info = {
            "config_id": config_id,
            "timestamp": datetime.now().isoformat(),
            "original_size": len(str(config)),
            "backup_config": copy.deepcopy(config)
        }
        
        # Get counts from your API structure
        data = config.get("data", {})
        backup_info["entities_count"] = len(data.get("analysisEntityList", []))
        backup_info["resources_count"] = len(data.get("resourceList", []))
        
        # Validate backup
        is_valid, errors = self.validator.validate_configuration(config)
        backup_info["validation_passed"] = is_valid
        if not is_valid:
            backup_info["validation_errors"] = errors
            logger.warning(f"Backup validation found issues: {len(errors)} errors")
        
        logger.debug(f"Created backup for configuration {config_id}")
        return backup_info