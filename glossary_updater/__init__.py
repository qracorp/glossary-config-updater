"""
Glossary Configuration Updater

A professional tool for updating API configurations with glossary terms from various file formats.

This package provides both a programmatic API and command-line interface for:
- Reading glossary terms from CSV, JSON, and YAML files
- Authenticating with target APIs
- Merging or overwriting configuration glossaries
- Validating and updating configurations

Usage:
    from glossary_updater import GlossaryUpdater
    
    updater = GlossaryUpdater(domain="api.example.com", username="user", password="pass")
    result = await updater.update_from_files(
        config_id="config123",
        file_paths=["terms.csv"],
        merge_strategy="merge"
    )

Command Line:
    python -m glossary_updater --file terms.csv --config config123 --domain api.example.com
"""

__version__ = "1.0.0"
__author__ = "Your Organization"
__email__ = "support@yourorg.com"
__license__ = "MIT"

from .main import GlossaryUpdater
from .config import Config
from .api_client import APIClient
from .processor import FileProcessor
from .merger import ConfigurationMerger
from .utils import logger, validate_file_path, generate_uuid

__all__ = [
    "GlossaryUpdater",
    "Config", 
    "APIClient",
    "FileProcessor",
    "ConfigurationMerger",
    "logger",
    "validate_file_path",
    "generate_uuid"
]
