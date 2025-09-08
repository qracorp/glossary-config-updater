"""
Configuration management for the Glossary Updater.

Handles environment variables, command-line arguments, and validation.
"""

import os
import argparse
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path

from .utils import logger


@dataclass
class Config:
    """Configuration settings for the Glossary Updater."""
    
    # API Configuration
    domain: str
    username: str
    password: str
    config_id: str
    
    # File Configuration  
    file_paths: List[str]
    directory_paths: List[str]
    
    # Processing Configuration
    merge_strategy: str = "merge"  # "merge" or "overwrite"
    dry_run: bool = False
    verbose: bool = False
    
    # API Configuration
    timeout: int = 30
    max_retries: int = 3
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate configuration settings."""
        errors = []
        
        # Required fields
        if not self.domain:
            errors.append("Domain is required")
        if not self.username:
            errors.append("Username is required") 
        if not self.password:
            errors.append("Password is required")
        if not self.config_id:
            errors.append("Configuration ID is required")
            
        # File validation
        if not self.file_paths and not self.directory_paths:
            errors.append("At least one file path or directory path is required")
            
        # Merge strategy validation
        if self.merge_strategy not in ["merge", "overwrite"]:
            errors.append("Merge strategy must be 'merge' or 'overwrite'")
            
        # Numeric validation
        if self.timeout <= 0:
            errors.append("Timeout must be positive")
        if self.max_retries < 0:
            errors.append("Max retries cannot be negative")
            
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "Config":
        """Create Config from command-line arguments."""
        return cls(
            domain=args.domain or os.getenv("API_DOMAIN", ""),
            username=args.username or os.getenv("API_USERNAME", ""),
            password=args.password or os.getenv("API_PASSWORD", ""),
            config_id=args.config,
            file_paths=args.files or [],
            directory_paths=args.directories or [],
            merge_strategy=args.merge_strategy,
            dry_run=args.dry_run,
            verbose=args.verbose,
            timeout=args.timeout,
            max_retries=args.max_retries
        )
    
    @classmethod
    def from_env(cls, config_id: str, **overrides) -> "Config":
        """Create Config from environment variables with optional overrides."""
        config_dict = {
            "domain": os.getenv("API_DOMAIN", ""),
            "username": os.getenv("API_USERNAME", ""),
            "password": os.getenv("API_PASSWORD", ""),
            "config_id": config_id,
            "file_paths": [],
            "directory_paths": [],
            "merge_strategy": "merge",
            "dry_run": False,
            "verbose": False,
            "timeout": 30,
            "max_retries": 3
        }
        
        # Apply overrides
        config_dict.update(overrides)
        
        return cls(**config_dict)


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="glossary-updater",
        description="Update API configurations with glossary terms from files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update from CSV file
  glossary-updater --file terms.csv --config config123 --domain api.example.com
  
  # Update from multiple files with merge
  glossary-updater --files terms1.csv terms2.json --config config123 --merge-strategy merge
  
  # Process entire directory
  glossary-updater --directory ./glossary --config config123 --verbose
  
  # Dry run to test without making changes
  glossary-updater --file terms.csv --config config123 --dry-run
  
  # Using environment variables
  export API_DOMAIN=api.example.com
  export API_USERNAME=myuser
  export API_PASSWORD=mypass
  glossary-updater --file terms.csv --config config123

Environment Variables:
  API_DOMAIN     - API domain (alternative to --domain)
  API_USERNAME   - API username (alternative to --username)  
  API_PASSWORD   - API password (alternative to --password)
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--config", "-c",
        required=True,
        help="Configuration ID to update"
    )
    
    # File input arguments (at least one required)
    file_group = parser.add_argument_group("Input Files")
    file_group.add_argument(
        "--file", "-f",
        dest="files",
        action="append",
        help="Glossary file path (CSV, JSON, or YAML). Can be used multiple times."
    )
    file_group.add_argument(
        "--directory", "-d", 
        dest="directories",
        action="append",
        help="Directory containing glossary files. Can be used multiple times."
    )
    
    # Authentication arguments
    auth_group = parser.add_argument_group("Authentication")
    auth_group.add_argument(
        "--domain",
        help="API domain (or set API_DOMAIN environment variable)"
    )
    auth_group.add_argument(
        "--username", "-u",
        help="API username (or set API_USERNAME environment variable)"
    )
    auth_group.add_argument(
        "--password", "-p",
        help="API password (or set API_PASSWORD environment variable)"
    )
    
    # Processing options
    process_group = parser.add_argument_group("Processing Options")
    process_group.add_argument(
        "--merge-strategy",
        choices=["merge", "overwrite"],
        default="merge",
        help="How to handle existing glossary terms (default: merge)"
    )
    process_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Process files and validate but don't update configuration"
    )
    
    # API options
    api_group = parser.add_argument_group("API Options")
    api_group.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="API request timeout in seconds (default: 30)"
    )
    api_group.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of API retry attempts (default: 3)"
    )
    
    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    output_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress all output except errors"
    )
    
    return parser


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    # Validate that at least one file input method is provided
    if not parsed_args.files and not parsed_args.directories:
        parser.error("At least one of --file or --directory must be specified")
    
    # Handle quiet mode
    if parsed_args.quiet:
        parsed_args.verbose = False
        logger.setLevel("ERROR")
    elif parsed_args.verbose:
        logger.setLevel("DEBUG")
    
    return parsed_args
