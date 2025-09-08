#!/usr/bin/env python3
"""
Standalone Glossary Configuration Updater

A single-file tool for updating API configurations with glossary terms from various file formats.
This standalone version contains all necessary functionality without external package dependencies.

Usage:
    python glossary_updater.py --file terms.csv --config config123 --domain api.example.com
    
Requirements:
    - Python 3.8 or higher
    - External packages: httpx, pandas, pyyaml (installed automatically if missing)
"""

import sys
import os
import subprocess
import asyncio
import argparse
import json
import csv
import logging
import uuid
import copy
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
from urllib.parse import urljoin

# Auto-install required packages
def install_package(package_name: str) -> None:
    """Install a Python package using pip."""
    try:
        __import__(package_name.replace('-', '_'))
    except ImportError:
        print(f"Installing required package: {package_name}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

# Install required packages
required_packages = ["httpx", "pandas", "pyyaml"]
for package in required_packages:
    install_package(package)

# Now import the packages
import httpx
import pandas as pd
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class GlossaryUpdaterError(Exception):
    """Base exception for updater errors."""
    pass


class APIError(Exception):
    """Base exception for API-related errors."""
    pass


class AuthenticationError(APIError):
    """Exception raised when authentication fails."""
    pass


class ConfigurationError(APIError):
    """Exception raised when configuration operations fail."""
    pass


class ProcessingError(Exception):
    """Exception raised during file processing."""
    pass


class MergeError(Exception):
    """Exception raised during configuration merging."""
    pass


class GlossaryTerm:
    """Represents a single glossary term."""
    
    def __init__(self, phrase: str, definition: str, metadata: Dict[str, Any] = None):
        self.phrase = phrase.strip()
        self.definition = definition.strip()
        self.metadata = metadata or {}
        
        if not self.phrase:
            raise ValueError("Phrase cannot be empty")
        if not self.definition:
            raise ValueError("Definition cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        result = {'phrase': self.phrase, 'definition': self.definition}
        if self.metadata:
            result['metadata'] = self.metadata
        return result
    
    def __str__(self) -> str:
        return f"{self.phrase}: {self.definition[:50]}{'...' if len(self.definition) > 50 else ''}"


class APIClient:
    """Client for interacting with the configuration management API."""
    
    def __init__(self, domain: str, username: str, password: str, timeout: int = 30):
        self.domain = domain.rstrip('/')
        if not self.domain.startswith(('http://', 'https://')):
            self.domain = f"https://{self.domain}"
        
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session: Optional[httpx.AsyncClient] = None
        self.auth_token: Optional[str] = None
        self._authenticated = False
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    async def connect(self):
        self.session = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout))
        await self.authenticate()
    
    async def disconnect(self):
        if self.session:
            await self.session.aclose()
            self.session = None
        self._authenticated = False
        self.auth_token = None
    
    async def authenticate(self):
        if not self.session:
            raise APIError("Session not initialized")
        
        login_url = urljoin(self.domain, "/auth/login")
        login_data = {"username": self.username, "password": self.password}
        
        try:
            response = await self.session.post(login_url, json=login_data)
            response.raise_for_status()
            
            result = response.json()
            self.auth_token = result.get("token") or result.get("access_token")
            
            if not self.auth_token:
                raise AuthenticationError("No token found in response")
            
            self._authenticated = True
            logger.info("✅ Authentication successful")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid username or password")
            else:
                raise AuthenticationError(f"Authentication failed: {e.response.status_code}")
    
    async def get_configuration(self, config_id: str) -> Dict[str, Any]:
        if not self._authenticated:
            raise APIError("Not authenticated")
        
        config_url = urljoin(self.domain, f"/analysis/v2/configuration/{config_id}")
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        
        try:
            response = await self.session.get(config_url, headers=headers)
            response.raise_for_status()
            logger.info(f"✅ Retrieved configuration: {config_id}")
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ConfigurationError(f"Configuration not found: {config_id}")
            else:
                raise ConfigurationError(f"Failed to retrieve configuration: {e.response.status_code}")
    
    async def update_configuration(self, config_id: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._authenticated:
            raise APIError("Not authenticated")
        
        config_url = urljoin(self.domain, f"/analysis/v2/configuration/{config_id}")
        headers = {'Authorization': f'Bearer {self.auth_token}', 'Content-Type': 'application/json'}
        
        try:
            response = await self.session.put(config_url, json=config_data, headers=headers)
            response.raise_for_status()
            logger.info(f"✅ Updated configuration: {config_id}")
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ConfigurationError(f"Configuration not found: {config_id}")
            elif e.response.status_code == 400:
                raise ConfigurationError(f"Invalid configuration data: {e.response.text}")
            else:
                raise ConfigurationError(f"Failed to update configuration: {e.response.status_code}")


class FileProcessor:
    """Processes glossary files in various formats."""
    
    def process_files(self, file_paths: List[Path]) -> List[GlossaryTerm]:
        all_terms = []
        
        for file_path in file_paths:
            logger.info(f"Processing file: {file_path}")
            terms = self.process_file(file_path)
            all_terms.extend(terms)
            logger.info(f"  → Found {len(terms)} terms")
        
        # Remove duplicates
        unique_terms = self._deduplicate_terms(all_terms)
        logger.info(f"Total unique terms: {len(unique_terms)}")
        return unique_terms
    
    def process_file(self, file_path: Path) -> List[GlossaryTerm]:
        if not file_path.exists():
            raise ProcessingError(f"File not found: {file_path}")
        
        extension = file_path.suffix.lower()
        
        if extension == '.csv':
            return self._process_csv(file_path)
        elif extension == '.json':
            return self._process_json(file_path)
        elif extension in ['.yaml', '.yml']:
            return self._process_yaml(file_path)
        else:
            raise ProcessingError(f"Unsupported file format: {extension}")
    
    def _process_csv(self, file_path: Path) -> List[GlossaryTerm]:
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            df.columns = df.columns.str.strip().str.lower()
            
            # Find phrase and definition columns
            phrase_col = self._find_phrase_column(df.columns)
            definition_col = self._find_definition_column(df.columns)
            
            if not phrase_col or not definition_col:
                raise ProcessingError(f"Required columns not found. Available: {list(df.columns)}")
            
            terms = []
            for index, row in df.iterrows():
                try:
                    phrase = str(row[phrase_col]).strip()
                    definition = str(row[definition_col]).strip()
                    
                    if phrase and phrase.lower() not in ['nan', 'none'] and \
                       definition and definition.lower() not in ['nan', 'none']:
                        terms.append(GlossaryTerm(phrase, definition))
                except Exception as e:
                    logger.warning(f"Skipping row {index + 1}: {str(e)}")
                    continue
            
            return terms
        except Exception as e:
            raise ProcessingError(f"CSV processing failed: {str(e)}")
    
    def _process_json(self, file_path: Path) -> List[GlossaryTerm]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            terms = []
            
            if isinstance(data, list):
                terms.extend(self._parse_term_array(data))
            elif isinstance(data, dict):
                # Look for glossary data
                glossary_data = None
                for key in ['glossary', 'terms', 'definitions']:
                    if key in data:
                        glossary_data = data[key]
                        break
                
                if glossary_data:
                    if isinstance(glossary_data, list):
                        terms.extend(self._parse_term_array(glossary_data))
                    elif isinstance(glossary_data, dict):
                        terms.extend(self._parse_term_dict(glossary_data))
                else:
                    terms.extend(self._parse_term_dict(data))
            
            return terms
        except Exception as e:
            raise ProcessingError(f"JSON processing failed: {str(e)}")
    
    def _process_yaml(self, file_path: Path) -> List[GlossaryTerm]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            terms = []
            
            if isinstance(data, list):
                terms.extend(self._parse_term_array(data))
            elif isinstance(data, dict):
                # Look for glossary data
                glossary_data = None
                for key in ['glossary', 'terms', 'definitions']:
                    if key in data:
                        glossary_data = data[key]
                        break
                
                if glossary_data:
                    if isinstance(glossary_data, list):
                        terms.extend(self._parse_term_array(glossary_data))
                    elif isinstance(glossary_data, dict):
                        terms.extend(self._parse_term_dict(glossary_data))
                else:
                    terms.extend(self._parse_term_dict(data))
            
            return terms
        except Exception as e:
            raise ProcessingError(f"YAML processing failed: {str(e)}")
    
    def _parse_term_array(self, data: List[Dict[str, Any]]) -> List[GlossaryTerm]:
        terms = []
        for item in data:
            if isinstance(item, dict):
                phrase = None
                definition = None
                
                for key in ['phrase', 'term', 'word', 'name']:
                    if key in item:
                        phrase = str(item[key]).strip()
                        break
                
                for key in ['definition', 'description', 'meaning']:
                    if key in item:
                        definition = str(item[key]).strip()
                        break
                
                if phrase and definition:
                    terms.append(GlossaryTerm(phrase, definition))
        return terms
    
    def _parse_term_dict(self, data: Dict[str, Any]) -> List[GlossaryTerm]:
        terms = []
        for phrase, definition in data.items():
            if isinstance(definition, str):
                terms.append(GlossaryTerm(phrase, definition))
            elif isinstance(definition, dict) and 'definition' in definition:
                terms.append(GlossaryTerm(phrase, definition['definition']))
        return terms
    
    def _find_phrase_column(self, columns: List[str]) -> str:
        phrase_keywords = ['phrase', 'term', 'word', 'name']
        for keyword in phrase_keywords:
            for col in columns:
                if keyword in col.lower():
                    return col
        return None
    
    def _find_definition_column(self, columns: List[str]) -> str:
        definition_keywords = ['definition', 'description', 'meaning', 'explanation']
        for keyword in definition_keywords:
            for col in columns:
                if keyword in col.lower():
                    return col
        return None
    
    def _deduplicate_terms(self, terms: List[GlossaryTerm]) -> List[GlossaryTerm]:
        seen_phrases = set()
        unique_terms = []
        
        for term in terms:
            phrase_lower = term.phrase.lower()
            if phrase_lower not in seen_phrases:
                seen_phrases.add(phrase_lower)
                unique_terms.append(term)
        
        return unique_terms


class ConfigurationMerger:
    """Handles merging glossary terms into configurations."""
    
    def __init__(self):
        self.glossary_entity_id = "676c6f73-7361-7279-3132-333435363738"
    
    def merge_glossary_terms(self, config: Dict[str, Any], terms: List[GlossaryTerm],
                           strategy: str = "merge") -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if strategy not in ["merge", "overwrite"]:
            raise MergeError(f"Invalid merge strategy: {strategy}")
        
        logger.info(f"Starting {strategy} operation with {len(terms)} terms")
        
        updated_config = copy.deepcopy(config)
        
        # Find or create glossary entity
        glossary_entity = self._find_or_create_glossary_entity(updated_config)
        
        # Get existing terms
        existing_terms = self._extract_existing_terms(updated_config, glossary_entity)
        
        # Merge statistics
        merge_stats = {
            "strategy": strategy,
            "terms_before": len(existing_terms),
            "terms_provided": len(terms),
            "timestamp": datetime.now().isoformat()
        }
        
        # Perform merge or overwrite
        if strategy == "merge":
            final_terms = self._merge_terms(existing_terms, terms)
        else:
            final_terms = terms
        
        merge_stats["terms_after"] = len(final_terms)
        
        # Update configuration
        self._update_configuration_with_terms(updated_config, glossary_entity, final_terms)
        
        logger.info(f"✅ {strategy.title()} completed: {merge_stats['terms_before']} → {merge_stats['terms_after']} terms")
        
        return updated_config, merge_stats
    
    def _find_or_create_glossary_entity(self, config: Dict[str, Any]) -> Dict[str, Any]:
        entity_list = config.get("analysisEntityList", [])
        
        for entity in entity_list:
            if (entity.get("id") == self.glossary_entity_id or 
                entity.get("name", "").lower() == "glossary"):
                return entity
        
        # Create new entity
        new_entity = {
            "id": self.glossary_entity_id,
            "name": "Glossary",
            "type": "glossary",
            "enabled": True,
            "resources": [],
            "searchOrder": len(entity_list) + 1
        }
        
        entity_list.append(new_entity)
        config["analysisEntityList"] = entity_list
        
        return new_entity
    
    def _extract_existing_terms(self, config: Dict[str, Any], glossary_entity: Dict[str, Any]) -> List[GlossaryTerm]:
        existing_terms = []
        resource_list = config.get("resourceList", [])
        resource_ids = glossary_entity.get("resources", [])
        
        for resource_id in resource_ids:
            for resource in resource_list:
                if resource.get("id") == resource_id:
                    terms_from_resource = self._extract_terms_from_resource(resource)
                    existing_terms.extend(terms_from_resource)
                    break
        
        return existing_terms
    
    def _extract_terms_from_resource(self, resource: Dict[str, Any]) -> List[GlossaryTerm]:
        terms = []
        
        if "glossary" in resource and isinstance(resource["glossary"], list):
            for item in resource["glossary"]:
                if isinstance(item, dict) and "phrase" in item and "definition" in item:
                    try:
                        terms.append(GlossaryTerm(item["phrase"], item["definition"]))
                    except Exception:
                        continue
        
        return terms
    
    def _merge_terms(self, existing_terms: List[GlossaryTerm], new_terms: List[GlossaryTerm]) -> List[GlossaryTerm]:
        existing_lookup = {term.phrase.lower(): term for term in existing_terms}
        merged_terms = list(existing_terms)
        
        for new_term in new_terms:
            phrase_lower = new_term.phrase.lower()
            
            if phrase_lower in existing_lookup:
                # Update existing term
                for i, term in enumerate(merged_terms):
                    if term.phrase.lower() == phrase_lower:
                        merged_terms[i] = new_term
                        break
            else:
                # Add new term
                merged_terms.append(new_term)
        
        return merged_terms
    
    def _update_configuration_with_terms(self, config: Dict[str, Any], 
                                       glossary_entity: Dict[str, Any], 
                                       terms: List[GlossaryTerm]) -> None:
        if "resourceList" not in config:
            config["resourceList"] = []
        
        # Remove old glossary resources
        existing_resource_ids = set(glossary_entity.get("resources", []))
        config["resourceList"] = [r for r in config["resourceList"] 
                                if r.get("id") not in existing_resource_ids]
        
        # Create new resource with all terms
        if terms:
            resource_id = str(uuid.uuid4())
            
            glossary_resource = {
                "id": resource_id,
                "alias": f"Glossary Terms ({len(terms)} terms)",
                "type": "glossary",
                "searchOrder": 1,
                "glossary": [term.to_dict() for term in terms]
            }
            
            config["resourceList"].append(glossary_resource)
            glossary_entity["resources"] = [resource_id]
        else:
            glossary_entity["resources"] = []


class GlossaryUpdater:
    """Main class for updating API configurations with glossary terms."""
    
    def __init__(self, domain: str, username: str, password: str, timeout: int = 30):
        self.api_client = APIClient(domain, username, password, timeout)
        self.file_processor = FileProcessor()
        self.merger = ConfigurationMerger()
    
    async def update_from_files(self, config_id: str, file_paths: List[str], 
                              merge_strategy: str = "merge", dry_run: bool = False) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("Starting Glossary Configuration Update")
        logger.info("=" * 60)
        
        try:
            # Step 1: Discover files
            logger.info("Step 1: Discovering files...")
            discovered_files = []
            for path_str in file_paths:
                path = Path(path_str)
                if path.is_file():
                    discovered_files.append(path)
                elif path.is_dir():
                    # Find all supported files in directory
                    for ext in ['.csv', '.json', '.yaml', '.yml']:
                        discovered_files.extend(path.glob(f'*{ext}'))
            
            if not discovered_files:
                raise GlossaryUpdaterError("No valid files found")
            
            logger.info(f"Found {len(discovered_files)} file(s)")
            
            # Step 2: Process files
            logger.info("Step 2: Processing files...")
            terms = self.file_processor.process_files(discovered_files)
            
            if not terms:
                raise GlossaryUpdaterError("No terms found in files")
            
            # Step 3: Connect to API
            logger.info("Step 3: Connecting to API...")
            async with self.api_client:
                # Step 4: Get configuration
                logger.info("Step 4: Retrieving configuration...")
                current_config = await self.api_client.get_configuration(config_id)
                
                # Step 5: Merge terms
                logger.info(f"Step 5: Performing {merge_strategy}...")
                updated_config, merge_stats = self.merger.merge_glossary_terms(
                    current_config, terms, merge_strategy
                )
                
                # Step 6: Update or dry run
                if dry_run:
                    logger.info("Step 6: Dry run - no changes made")
                    result = {
                        "success": True,
                        "dry_run": True,
                        "config_id": config_id,
                        "files_processed": len(discovered_files),
                        "merge_stats": merge_stats
                    }
                else:
                    logger.info("Step 6: Updating configuration...")
                    await self.api_client.update_configuration(config_id, updated_config)
                    
                    result = {
                        "success": True,
                        "dry_run": False,
                        "config_id": config_id,
                        "files_processed": len(discovered_files),
                        "merge_stats": merge_stats
                    }
            
            # Success summary
            logger.info("=" * 60)
            logger.info("✅ Update completed successfully!")
            logger.info(f"   Files processed: {len(discovered_files)}")
            logger.info(f"   Terms extracted: {len(terms)}")
            logger.info(f"   Terms before: {merge_stats['terms_before']}")
            logger.info(f"   Terms after: {merge_stats['terms_after']}")
            logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Update failed: {str(e)}")
            raise GlossaryUpdaterError(f"Update failed: {str(e)}")


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Update API configurations with glossary terms from files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python glossary_updater.py --file terms.csv --config config123 --domain api.example.com
  python glossary_updater.py --files terms1.csv terms2.json --config config123 --merge-strategy merge
  python glossary_updater.py --directory ./glossary --config config123 --dry-run

Environment Variables:
  API_DOMAIN, API_USERNAME, API_PASSWORD
        """
    )
    
    parser.add_argument("--config", "-c", required=True, help="Configuration ID to update")
    parser.add_argument("--file", dest="files", action="append", help="Glossary file (can be used multiple times)")
    parser.add_argument("--directory", dest="directories", action="append", help="Directory with glossary files")
    parser.add_argument("--domain", help="API domain (or set API_DOMAIN)")
    parser.add_argument("--username", "-u", help="API username (or set API_USERNAME)")
    parser.add_argument("--password", "-p", help="API password (or set API_PASSWORD)")
    parser.add_argument("--merge-strategy", choices=["merge", "overwrite"], default="merge", 
                       help="Merge strategy (default: merge)")
    parser.add_argument("--dry-run", action="store_true", help="Test without making changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    return parser


async def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Get credentials
    domain = args.domain or os.getenv("API_DOMAIN")
    username = args.username or os.getenv("API_USERNAME")
    password = args.password or os.getenv("API_PASSWORD")
    
    if not all([domain, username, password]):
        parser.error("Domain, username, and password are required (via args or environment)")
    
    # Get file paths
    file_paths = (args.files or []) + (args.directories or [])
    if not file_paths:
        parser.error("At least one --file or --directory must be specified")
    
    try:
        updater = GlossaryUpdater(domain, username, password)
        result = await updater.update_from_files(
            config_id=args.config,
            file_paths=file_paths,
            merge_strategy=args.merge_strategy,
            dry_run=args.dry_run
        )
        
        if result["success"]:
            print("✅ Operation completed successfully!")
        else:
            print("❌ Operation failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
