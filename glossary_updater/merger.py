"""
Configuration merger for updating glossary terms with comprehensive validation.

Handles merging or overwriting glossary terms in API configurations with safety checks.
"""

import copy
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .processor import GlossaryTerm
from .utils import logger, generate_resource_id


class MergeError(Exception):
    """Exception raised during configuration merging."""
    pass


class ConfigurationValidator:
    """Validates configuration structure and content."""
    
    def __init__(self, schema: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration schema."""
        self.schema = schema or self.get_default_schema()
    
    def get_default_schema(self) -> Dict[str, Any]:
        """Get default configuration validation schema."""
        return {
            "required_fields": ["analysisEntityList", "resourceList"],
            "analysisEntityList": {
                "type": "array",
                "required_item_fields": ["id", "name"],
                "max_entities": 100
            },
            "resourceList": {
                "type": "array", 
                "required_item_fields": ["id"],
                "max_resources": 1000
            },
            "glossary_entity": {
                "id_pattern": r"^[a-f0-9\-]+$",
                "required_fields": ["id", "name", "type", "resources"],
                "max_terms_per_resource": 5000
            }
        }
    
    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Comprehensive configuration validation.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Basic structure validation
            if not isinstance(config, dict):
                errors.append("Configuration must be a dictionary")
                return False, errors
            
            # Check required top-level fields
            for field in self.schema["required_fields"]:
                if field not in config:
                    errors.append(f"Missing required field: {field}")
            
            # Validate analysisEntityList
            if "analysisEntityList" in config:
                entity_errors = self._validate_entity_list(config["analysisEntityList"])
                errors.extend(entity_errors)
            
            # Validate resourceList
            if "resourceList" in config:
                resource_errors = self._validate_resource_list(config["resourceList"])
                errors.extend(resource_errors)
            
            # Cross-reference validation
            cross_ref_errors = self._validate_cross_references(config)
            errors.extend(cross_ref_errors)
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Configuration validation error: {str(e)}")
            return False, errors
    
    def _validate_entity_list(self, entity_list: Any) -> List[str]:
        """Validate analysisEntityList structure."""
        errors = []
        
        if not isinstance(entity_list, list):
            errors.append("analysisEntityList must be an array")
            return errors
        
        if len(entity_list) > self.schema["analysisEntityList"]["max_entities"]:
            errors.append(f"Too many entities (max: {self.schema['analysisEntityList']['max_entities']})")
        
        entity_ids = set()
        for i, entity in enumerate(entity_list):
            if not isinstance(entity, dict):
                errors.append(f"Entity {i} must be an object")
                continue
            
            # Check required fields
            for field in self.schema["analysisEntityList"]["required_item_fields"]:
                if field not in entity:
                    errors.append(f"Entity {i} missing required field: {field}")
            
            # Check for duplicate IDs
            entity_id = entity.get("id")
            if entity_id:
                if entity_id in entity_ids:
                    errors.append(f"Duplicate entity ID: {entity_id}")
                entity_ids.add(entity_id)
            
            # Validate glossary entity if present
            if entity.get("type") == "glossary" or entity.get("name", "").lower() == "glossary":
                glossary_errors = self._validate_glossary_entity(entity, i)
                errors.extend(glossary_errors)
        
        return errors
    
    def _validate_resource_list(self, resource_list: Any) -> List[str]:
        """Validate resourceList structure."""
        errors = []
        
        if not isinstance(resource_list, list):
            errors.append("resourceList must be an array")
            return errors
        
        if len(resource_list) > self.schema["resourceList"]["max_resources"]:
            errors.append(f"Too many resources (max: {self.schema['resourceList']['max_resources']})")
        
        resource_ids = set()
        for i, resource in enumerate(resource_list):
            if not isinstance(resource, dict):
                errors.append(f"Resource {i} must be an object")
                continue
            
            # Check required fields
            for field in self.schema["resourceList"]["required_item_fields"]:
                if field not in resource:
                    errors.append(f"Resource {i} missing required field: {field}")
            
            # Check for duplicate IDs
            resource_id = resource.get("id")
            if resource_id:
                if resource_id in resource_ids:
                    errors.append(f"Duplicate resource ID: {resource_id}")
                resource_ids.add(resource_id)
            
            # Validate glossary resource content
            if resource.get("type") == "glossary" and "glossary" in resource:
                glossary_errors = self._validate_glossary_resource(resource, i)
                errors.extend(glossary_errors)
        
        return errors
    
    def _validate_glossary_entity(self, entity: Dict[str, Any], index: int) -> List[str]:
        """Validate glossary entity structure."""
        errors = []
        
        # Check required glossary fields
        for field in self.schema["glossary_entity"]["required_fields"]:
            if field not in entity:
                errors.append(f"Glossary entity {index} missing required field: {field}")
        
        # Validate resources array
        resources = entity.get("resources", [])
        if not isinstance(resources, list):
            errors.append(f"Glossary entity {index} resources must be an array")
        
        return errors
    
    def _validate_glossary_resource(self, resource: Dict[str, Any], index: int) -> List[str]:
        """Validate glossary resource content."""
        errors = []
        
        glossary_data = resource.get("glossary", [])
        if not isinstance(glossary_data, list):
            errors.append(f"Glossary resource {index} glossary field must be an array")
            return errors
        
        # Check term count
        max_terms = self.schema["glossary_entity"]["max_terms_per_resource"]
        if len(glossary_data) > max_terms:
            errors.append(f"Glossary resource {index} has too many terms (max: {max_terms})")
        
        # Validate individual terms
        for term_idx, term in enumerate(glossary_data):
            if not isinstance(term, dict):
                errors.append(f"Glossary term {term_idx} in resource {index} must be an object")
                continue
            
            if "phrase" not in term:
                errors.append(f"Glossary term {term_idx} in resource {index} missing phrase")
            
            if "definition" not in term:
                errors.append(f"Glossary term {term_idx} in resource {index} missing definition")
        
        return errors
    
    def _validate_cross_references(self, config: Dict[str, Any]) -> List[str]:
        """Validate cross-references between entities and resources."""
        errors = []
        
        # Get all resource IDs
        resource_ids = set()
        for resource in config.get("resourceList", []):
            if "id" in resource:
                resource_ids.add(resource["id"])
        
        # Check entity resource references
        for i, entity in enumerate(config.get("analysisEntityList", [])):
            entity_resources = entity.get("resources", [])
            for resource_ref in entity_resources:
                if resource_ref not in resource_ids:
                    errors.append(f"Entity {i} references non-existent resource: {resource_ref}")
        
        return errors


class ConfigurationMerger:
    """Handles merging glossary terms into configurations with validation."""
    
    def __init__(self, validation_schema: Optional[Dict[str, Any]] = None):
        """Initialize configuration merger with optional validation schema."""
        self.glossary_entity_id = "676c6f73-7361-7279-3132-333435363738"
        self.validator = ConfigurationValidator(validation_schema)
    
    def merge_glossary_terms(self, 
                           config: Dict[str, Any], 
                           terms: List[GlossaryTerm],
                           strategy: str = "merge") -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Merge glossary terms into configuration with comprehensive validation.
        
        Args:
            config: Original configuration
            terms: List of validated glossary terms
            strategy: Merge strategy ("merge" or "overwrite")
            
        Returns:
            Tuple of (updated_config, merge_stats)
        """
        if strategy not in ["merge", "overwrite"]:
            raise MergeError(f"Invalid merge strategy: {strategy}")
        
        logger.info(f"Starting {strategy} operation with {len(terms)} terms")
        
        # Step 1: Validate input configuration
        logger.debug("Validating input configuration...")
        is_valid, validation_errors = self.validator.validate_configuration(config)
        if not is_valid:
            raise MergeError(f"Input configuration validation failed: {'; '.join(validation_errors[:5])}")
        
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
            existing_terms = self._extract_existing_terms(updated_config, glossary_entity)
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
            
            # Step 7: Validate final configuration
            logger.debug("Validating final configuration...")
            final_valid, final_errors = self.validator.validate_configuration(updated_config)
            if not final_valid:
                merge_stats["validation_passed"] = False
                raise MergeError(f"Final configuration validation failed: {'; '.join(final_errors[:5])}")
            
            # Step 8: Log results
            self._log_merge_results(merge_stats)
            
            return updated_config, merge_stats
            
        except Exception as e:
            logger.error(f"Merge operation failed: {str(e)}")
            merge_stats["validation_passed"] = False
            raise MergeError(f"Failed to merge glossary terms: {str(e)}")
    
    def _find_or_create_glossary_entity(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Find existing glossary entity or create a new one."""
        entity_list = config.get("analysisEntityList", [])
        
        # Look for existing glossary entity
        for entity in entity_list:
            if (entity.get("id") == self.glossary_entity_id or 
                entity.get("name", "").lower() == "glossary" or
                entity.get("type") == "glossary"):
                logger.debug("Found existing glossary entity")
                return entity
        
        # Create new glossary entity
        logger.info("Creating new glossary entity")
        new_entity = {
            "id": self.glossary_entity_id,
            "name": "Glossary",
            "type": "glossary",
            "enabled": True,
            "resources": [],
            "searchOrder": len(entity_list) + 1,
            "description": "Automatically managed glossary terms",
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat()
        }
        
        entity_list.append(new_entity)
        config["analysisEntityList"] = entity_list
        
        return new_entity
    
    def _extract_existing_terms(self, 
                               config: Dict[str, Any], 
                               glossary_entity: Dict[str, Any]) -> List[GlossaryTerm]:
        """Extract existing glossary terms with validation."""
        existing_terms = []
        resource_list = config.get("resourceList", [])
        resource_ids = glossary_entity.get("resources", [])
        
        for resource_id in resource_ids:
            # Find resource in resourceList
            for resource in resource_list:
                if resource.get("id") == resource_id:
                    try:
                        terms_from_resource = self._extract_terms_from_resource(resource)
                        existing_terms.extend(terms_from_resource)
                    except Exception as e:
                        logger.warning(f"Failed to extract terms from resource {resource_id}: {str(e)}")
                    break
        
        logger.debug(f"Found {len(existing_terms)} existing terms")
        return existing_terms
    
    def _extract_terms_from_resource(self, resource: Dict[str, Any]) -> List[GlossaryTerm]:
        """Extract glossary terms from a resource with validation."""
        terms = []
        
        # Check glossary array structure
        if "glossary" in resource and isinstance(resource["glossary"], list):
            for i, item in enumerate(resource["glossary"]):
                try:
                    if isinstance(item, dict) and "phrase" in item and "definition" in item:
                        # Basic validation of existing terms
                        phrase = str(item["phrase"]).strip()
                        definition = str(item["definition"]).strip()
                        
                        if phrase and definition:
                            term = GlossaryTerm(
                                phrase=phrase,
                                definition=definition,
                                metadata=item.get("metadata", {})
                            )
                            terms.append(term)
                        else:
                            logger.debug(f"Skipping empty term at index {i}")
                    else:
                        logger.debug(f"Skipping malformed term at index {i}")
                except Exception as e:
                    logger.warning(f"Error processing existing term {i}: {str(e)}")
        
        # Handle legacy formats
        elif "terms" in resource and isinstance(resource["terms"], dict):
            for phrase, definition in resource["terms"].items():
                try:
                    if phrase and definition:
                        term = GlossaryTerm(phrase=str(phrase), definition=str(definition))
                        terms.append(term)
                except Exception as e:
                    logger.warning(f"Error processing legacy term '{phrase}': {str(e)}")
        
        return terms
    
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
        # Ensure resourceList exists
        if "resourceList" not in config:
            config["resourceList"] = []
        
        # Clear existing glossary resources
        resource_list = config["resourceList"]
        existing_resource_ids = set(glossary_entity.get("resources", []))
        
        # Remove old glossary resources
        config["resourceList"] = [r for r in resource_list 
                                if r.get("id") not in existing_resource_ids]
        
        # Create new resource with all terms
        if terms:
            resource_id = generate_resource_id()
            
            # Validate term count
            max_terms = self.validator.schema["glossary_entity"]["max_terms_per_resource"]
            if len(terms) > max_terms:
                logger.warning(f"Term count ({len(terms)}) exceeds recommended maximum ({max_terms})")
            
            glossary_resource = {
                "id": resource_id,
                "alias": f"Glossary Terms ({len(terms)} terms)",
                "type": "glossary",
                "searchOrder": 1,
                "created": datetime.now().isoformat(),
                "updated": datetime.now().isoformat(),
                "glossary": [term.to_dict() for term in terms]
            }
            
            # Add to resource list
            config["resourceList"].append(glossary_resource)
            
            # Update entity to reference this resource
            glossary_entity["resources"] = [resource_id]
            glossary_entity["updated"] = datetime.now().isoformat()
        else:
            # No terms, clear resources
            glossary_entity["resources"] = []
            glossary_entity["updated"] = datetime.now().isoformat()
    
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
        
        logger.info(f"  Validation: {'PASSED' if stats['validation_passed'] else 'FAILED'}")
    
    def validate_configuration_structure(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration structure (public interface)."""
        is_valid, errors = self.validator.validate_configuration(config)
        return errors
    
    def create_backup_config(self, config: Dict[str, Any], config_id: str) -> Dict[str, Any]:
        """Create a backup of the configuration before modification."""
        backup_info = {
            "config_id": config_id,
            "timestamp": datetime.now().isoformat(),
            "original_size": len(str(config)),
            "entities_count": len(config.get("analysisEntityList", [])),
            "resources_count": len(config.get("resourceList", [])),
            "validation_passed": True,
            "backup_config": copy.deepcopy(config)
        }
        
        # Validate backup
        is_valid, errors = self.validator.validate_configuration(config)
        if not is_valid:
            backup_info["validation_passed"] = False
            backup_info["validation_errors"] = errors
            logger.warning(f"Backup validation found issues: {len(errors)} errors")
        
        logger.debug(f"Created validated backup for configuration {config_id}")
        return backup_info
    
    def get_merge_preview(self, 
                         config: Dict[str, Any],
                         terms: List[GlossaryTerm],
                         strategy: str = "merge") -> Dict[str, Any]:
        """Get a preview of merge operation with validation."""
        # Validate input configuration first
        is_valid, validation_errors = self.validator.validate_configuration(config)
        
        preview = {
            "strategy": strategy,
            "input_valid": is_valid,
            "validation_errors": validation_errors if not is_valid else [],
            "terms_provided": len(terms),
            "terms_current": 0,
            "terms_after": 0,
            "glossary_entity_exists": False,
            "terms_that_would_be_added": [],
            "terms_that_would_be_updated": [],
            "terms_that_would_be_removed": []
        }
        
        if not is_valid:
            preview["error"] = "Configuration validation failed"
            return preview
        
        try:
            # Find glossary entity
            entity_list = config.get("analysisEntityList", [])
            glossary_entity = None
            
            for entity in entity_list:
                if (entity.get("id") == self.glossary_entity_id or 
                    entity.get("name", "").lower() == "glossary" or
                    entity.get("type") == "glossary"):
                    glossary_entity = entity
                    break
            
            preview["glossary_entity_exists"] = glossary_entity is not None
            
            # Get existing terms
            existing_terms = []
            if glossary_entity:
                existing_terms = self._extract_existing_terms(config, glossary_entity)
            
            preview["terms_current"] = len(existing_terms)
            
            # Calculate preview based on strategy
            if strategy == "merge":
                existing_phrases = {t.phrase.lower(): t for t in existing_terms}
                
                for term in terms:
                    phrase_lower = term.phrase.lower()
                    if phrase_lower in existing_phrases:
                        if existing_phrases[phrase_lower].definition != term.definition:
                            preview["terms_that_would_be_updated"].append({
                                "phrase": term.phrase,
                                "old_definition": existing_phrases[phrase_lower].definition,
                                "new_definition": term.definition
                            })
                    else:
                        preview["terms_that_would_be_added"].append({
                            "phrase": term.phrase,
                            "definition": term.definition
                        })
                        
                preview["terms_after"] = len(existing_terms) + len(preview["terms_that_would_be_added"])
                
            else:  # overwrite
                preview["terms_that_would_be_added"] = [
                    {"phrase": t.phrase, "definition": t.definition} for t in terms
                ]
                preview["terms_that_would_be_removed"] = [
                    {"phrase": t.phrase, "definition": t.definition} for t in existing_terms
                ]
                preview["terms_after"] = len(terms)
            
            return preview
            
        except Exception as e:
            preview["error"] = f"Preview generation failed: {str(e)}"
            return preview