"""
Main module for the Glossary Configuration Updater.

Provides the primary GlossaryUpdater class and command-line interface.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import Config, parse_args
from .api_client import APIClient, APIError, AuthenticationError, ConfigurationError
from .processor import FileProcessor, ProcessingError
from .merger import ConfigurationMerger, MergeError
from .utils import logger, discover_glossary_files, create_backup_filename, safe_json_dump


class GlossaryUpdaterError(Exception):
    """Base exception for GlossaryUpdater errors."""
    pass


class GlossaryUpdater:
    """
    Main class for updating API configurations with glossary terms.
    
    Orchestrates the entire process:
    1. Parse and validate input files
    2. Authenticate with API
    3. Retrieve current configuration
    4. Merge or overwrite glossary terms
    5. Validate and update configuration (only if changes detected)
    """
    
    def __init__(self, domain: str, username: str, password: str, 
                 timeout: int = 30, max_retries: int = 3):
        """
        Initialize GlossaryUpdater.
        
        Args:
            domain: API domain
            username: API username
            password: API password
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.domain = domain
        self.username = username
        self.password = password
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize components
        self.api_client = APIClient(domain, username, password, timeout, max_retries)
        self.file_processor = FileProcessor()
        self.merger = ConfigurationMerger()
        
        # State
        self._connected = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self):
        """Connect and authenticate with the API."""
        if not self._connected:
            await self.api_client.connect()
            self._connected = True
            logger.info("Connected to API")
    
    async def disconnect(self):
        """Disconnect from the API."""
        if self._connected:
            await self.api_client.disconnect()
            self._connected = False
            logger.info("Disconnected from API")
    
    async def update_from_files(self,
                              config_id: str,
                              file_paths: List[str] = None,
                              directory_paths: List[str] = None,
                              merge_strategy: str = "merge",
                              dry_run: bool = False) -> Dict[str, Any]:
        """
        Update configuration with glossary terms from files.
        
        Args:
            config_id: Configuration ID to update
            file_paths: List of file paths to process
            directory_paths: List of directory paths to search
            merge_strategy: "merge" or "overwrite"
            dry_run: If True, process files and validate but don't update
            
        Returns:
            Dictionary with update results
            
        Raises:
            GlossaryUpdaterError: If update fails
        """
        logger.info("=" * 60)
        logger.info("Starting Glossary Configuration Update")
        logger.info("=" * 60)
        
        try:
            # Step 0: Check for reserved configuration IDs
            # These are system/reserved configurations that should never be modified
            # NOTE: Server is too permissive and allows these updates, but they should be blocked
            RESERVED_CONFIG_IDS = {
                "08a785dd-9c90-3c8e-b9e6-dea1c560bfb9",
                "9d8d0029-0b2c-37f3-924a-87e97085ff34", 
                "6d2af803-4078-374f-917e-81735a65f251",
                "e52e00a8-5136-3ac1-a2c9-7a2d938ef4fd"
            }
            
            if config_id in RESERVED_CONFIG_IDS:
                raise GlossaryUpdaterError(
                    f"Configuration ID {config_id} is reserved and cannot be modified. "
                    f"Reserved IDs are system configurations that must not be updated."
                )
            
            logger.debug(f"Configuration ID {config_id} passed reserved ID validation")
            # Step 1: Discover and validate files
            all_paths = (file_paths or []) + (directory_paths or [])
            if not all_paths:
                raise GlossaryUpdaterError("No file paths or directory paths provided")
            
            logger.info("Step 1: Discovering files...")
            discovered_files = discover_glossary_files(all_paths)
            
            # Flatten file list
            all_file_paths = []
            for file_type, paths in discovered_files.items():
                all_file_paths.extend(paths)
            
            if not all_file_paths:
                raise GlossaryUpdaterError("No valid glossary files found")
            
            logger.info(f"Found {len(all_file_paths)} file(s)")
            
            # Step 2: Process files and extract terms
            logger.info("Step 2: Processing files...")
            terms = self.file_processor.process_files(all_file_paths)
            
            if not terms:
                raise GlossaryUpdaterError("No glossary terms found in files")
            
            logger.info(f"Total unique terms: {len(terms)}")
            
            # Step 3: Connect to API if not already connected
            if not self._connected:
                logger.info("Step 3: Connecting to API...")
                await self.connect()
            else:
                logger.info("Step 3: Using existing API connection")
            
            # Step 4: Retrieve current configuration
            logger.info("Step 4: Retrieving current configuration...")
            current_config = await self.api_client.get_configuration(config_id)
            
            # Step 5: Create backup
            logger.info("Step 5: Creating configuration backup...")
            backup_info = self.merger.create_backup_config(current_config, config_id)
            
            # Step 6: Validate configuration structure using JSON schema
            logger.info("Step 6: Validating configuration structure using JSON schema...")
            validation_errors = self.merger.validate_configuration_structure(current_config)
            if validation_errors:
                logger.warning(f"Configuration validation issues: {validation_errors}")
                logger.info("Proceeding with merge operation...")
            
            # Step 7: Merge or overwrite terms
            logger.info(f"Step 7: Performing {merge_strategy} operation...")
            updated_config, merge_stats = self.merger.merge_glossary_terms(
                current_config, terms, merge_strategy
            )
            
            # Step 8: Check if there are any changes to apply
            net_change = merge_stats['terms_after'] - merge_stats['terms_before']
            has_changes = (
                merge_stats['terms_added'] > 0 or
                merge_stats['terms_removed'] > 0 or
                net_change != 0
)            
            logger.info(f"Change analysis:")
            logger.info(f"  Terms before: {merge_stats['terms_before']}")
            logger.info(f"  Terms after: {merge_stats['terms_after']}")
            logger.info(f"  Terms added: {merge_stats.get('terms_added', 0)}")
            logger.info(f"  Terms updated: {merge_stats.get('terms_updated', 0)}")
            logger.info(f"  Terms removed: {merge_stats.get('terms_removed', 0)}")
            logger.info(f"  Net change: {'+' if net_change > 0 else ''}{net_change}")
            
            # Step 9: Update configuration (only if there are changes)
            if dry_run:
                logger.info("Step 8: Dry run - skipping actual update")
                if has_changes:
                    logger.info("  Would have updated configuration with changes")
                else:
                    logger.info("  No changes detected - would skip update")
                    
                result = {
                    "success": True,
                    "dry_run": True,
                    "config_id": config_id,
                    "files_processed": len(all_file_paths),
                    "terms_extracted": len(terms),
                    "merge_stats": merge_stats,
                    "changes_detected": has_changes,
                    "update_skipped": not has_changes,
                    "backup_info": {
                        "created": backup_info["timestamp"],
                        "size": backup_info["original_size"]
                    }
                }
            elif not has_changes:
                logger.info("Step 8: No changes detected - skipping configuration update")
                logger.info("  Configuration already contains the same glossary terms")
                
                result = {
                    "success": True,
                    "dry_run": False,
                    "config_id": config_id,
                    "files_processed": len(all_file_paths),
                    "terms_extracted": len(terms),
                    "merge_stats": merge_stats,
                    "changes_detected": False,
                    "update_skipped": True,
                    "message": "No changes needed - configuration already up to date",
                    "backup_info": {
                        "created": backup_info["timestamp"],
                        "size": backup_info["original_size"]
                    }
                }
            else:
                logger.info("Step 8: Updating configuration...")
                logger.info(f"  Applying {net_change:+d} net change{'s' if abs(net_change) != 1 else ''}")
                
                final_config = await self.api_client.update_configuration(config_id, updated_config)
                
                result = {
                    "success": True,
                    "dry_run": False,
                    "config_id": config_id,
                    "files_processed": len(all_file_paths),
                    "terms_extracted": len(terms),
                    "merge_stats": merge_stats,
                    "changes_detected": True,
                    "update_skipped": False,
                    "updated_configuration": final_config,
                    "backup_info": {
                        "created": backup_info["timestamp"],
                        "size": backup_info["original_size"]
                    }
                }
            
            # Log success summary (updated to show whether update was skipped)
            logger.info("=" * 60)
            if result.get("update_skipped", False):
                logger.info("[OK] Analysis completed - No update needed!")
                logger.info("     Configuration already contains the same glossary terms")
            else:
                logger.info("[OK] Update completed successfully!")
                
            logger.info(f"     Configuration: {config_id}")
            logger.info(f"     Files processed: {len(all_file_paths)}")
            logger.info(f"     Terms extracted: {len(terms)}")
            logger.info(f"     Strategy: {merge_strategy}")
            logger.info(f"     Terms before: {merge_stats['terms_before']}")
            logger.info(f"     Terms after: {merge_stats['terms_after']}")
            
            if result.get("update_skipped", False):
                logger.info("     Action: No changes needed")
            elif dry_run:
                logger.info("     Action: Dry run (no changes made)")
            else:
                logger.info("     Action: Configuration updated")
                
            logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            logger.error(f"[ERROR] Update failed: {str(e)}")
            raise GlossaryUpdaterError(f"Update failed: {str(e)}")
    
    async def test_connection(self) -> bool:
        """
        Test API connection and authentication.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if not self._connected:
                await self.connect()
            return await self.api_client.test_connection()
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    async def get_configuration_info(self, config_id: str) -> Dict[str, Any]:
        """
        Get information about a configuration without modifying it.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Configuration information
        """
        if not self._connected:
            await self.connect()
        
        config = await self.api_client.get_configuration(config_id)
        
        # Extract glossary information from your API structure
        glossary_info = {
            "config_id": config_id,
            "configuration_name": config.get("configurationName", ""),
            "configuration_version": config.get("configurationVersion", 0),
            "schema_version": config.get("configurationSchemaVersion", ""),
            "total_entities": 0,
            "total_resources": 0,
            "current_glossary_terms": 0
        }
        
        # Get counts from data section
        data = config.get("data", {})
        if data:
            glossary_info["total_entities"] = len(data.get("analysisEntityList", []))
            glossary_info["total_resources"] = len(data.get("resourceList", []))
            
            # Count existing glossary terms
            existing_terms = self.merger._extract_existing_terms(config)
            glossary_info["current_glossary_terms"] = len(existing_terms)
        
        return glossary_info
    
    async def preview_update(self,
                           config_id: str,
                           file_paths: List[str] = None,
                           directory_paths: List[str] = None,
                           merge_strategy: str = "merge") -> Dict[str, Any]:
        """
        Preview what would happen during an update without making changes.
        
        Args:
            config_id: Configuration ID
            file_paths: List of file paths
            directory_paths: List of directory paths
            merge_strategy: Merge strategy
            
        Returns:
            Preview information
        """
        # Discover and process files
        all_paths = (file_paths or []) + (directory_paths or [])
        discovered_files = discover_glossary_files(all_paths)
        
        all_file_paths = []
        for file_type, paths in discovered_files.items():
            all_file_paths.extend(paths)
        
        terms = self.file_processor.process_files(all_file_paths)
        
        # Get current configuration
        if not self._connected:
            await self.connect()
        
        current_config = await self.api_client.get_configuration(config_id)
        
        # Get existing terms
        existing_terms = self.merger._extract_existing_terms(current_config)
        
        # Calculate what changes would be made
        preview = {
            "files_to_process": len(all_file_paths),
            "terms_extracted": len(terms),
            "terms_current": len(existing_terms),
            "file_types": {
                file_type: len(paths) for file_type, paths in discovered_files.items()
            },
            "strategy": merge_strategy,
            "terms_that_would_be_added": [],
            "terms_that_would_be_updated": [],
            "terms_that_would_be_removed": []
        }
        
        if merge_strategy == "merge":
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
        
        # Determine if changes would be made
        preview["would_make_changes"] = (
            len(preview["terms_that_would_be_added"]) > 0 or
            len(preview["terms_that_would_be_updated"]) > 0 or
            len(preview["terms_that_would_be_removed"]) > 0
        )
        
        return preview


async def run_cli():
    """
    Run the command-line interface.
    
    This is the main entry point for the CLI application.
    """
    try:
        # Parse command-line arguments
        args = parse_args()
        config = Config.from_args(args)
        
        # Set up verbose logging if requested
        if config.verbose:
            logger.setLevel("DEBUG")
            logger.debug("Verbose logging enabled")
        
        # Create updater
        updater = GlossaryUpdater(
            domain=config.domain,
            username=config.username,
            password=config.password,
            timeout=config.timeout,
            max_retries=config.max_retries
        )
        
        # Use async context manager for proper cleanup
        async with updater:
            # Test connection first
            logger.info("Testing API connection...")
            if not await updater.test_connection():
                logger.error("[ERROR] Failed to connect to API")
                sys.exit(1)
            
            # Run update
            result = await updater.update_from_files(
                config_id=config.config_id,
                file_paths=config.file_paths,
                directory_paths=config.directory_paths,
                merge_strategy=config.merge_strategy,
                dry_run=config.dry_run
            )
            
            if result["success"]:
                if result.get("update_skipped", False):
                    logger.info("Operation completed - No changes needed")
                    logger.info("The configuration already contains the same glossary terms")
                else:
                    logger.info("Operation completed successfully")
                
                # Show summary in verbose mode
                if config.verbose:
                    logger.info("\n" + "=" * 50)
                    logger.info("OPERATION SUMMARY")
                    logger.info("=" * 50)
                    logger.info(f"Configuration ID: {result['config_id']}")
                    logger.info(f"Files processed: {result['files_processed']}")
                    logger.info(f"Terms extracted: {result['terms_extracted']}")
                    logger.info(f"Merge strategy: {result['merge_stats']['strategy']}")
                    logger.info(f"Terms before: {result['merge_stats']['terms_before']}")
                    logger.info(f"Terms after: {result['merge_stats']['terms_after']}")
                    
                    # Show change details
                    if result.get("changes_detected", True):
                        logger.info(f"Terms added: {result['merge_stats'].get('terms_added', 0)}")
                        logger.info(f"Terms updated: {result['merge_stats'].get('terms_updated', 0)}")
                        logger.info(f"Terms removed: {result['merge_stats'].get('terms_removed', 0)}")
                    
                    # Show action taken
                    if result.get("update_skipped", False):
                        logger.info("Action: No update needed (no changes detected)")
                    elif config.dry_run:
                        logger.info("Action: DRY RUN (no changes made)")
                    else:
                        logger.info("Action: Configuration updated successfully")
                    
                    logger.info("=" * 50)
                
                sys.exit(0)
            else:
                logger.error("Operation failed")
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        if 'config' in locals() and config.verbose:
            import traceback
            logger.error("Full traceback:")
            logger.error(traceback.format_exc())
        sys.exit(1)


def main():
    """
    Main entry point for the package.
    
    Can be called as:
    - python -m glossary_updater
    - glossary-updater (if installed)
    """
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()