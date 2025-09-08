"""
Utility functions and classes for the Glossary Updater.
"""

import os
import logging
import uuid
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        if hasattr(record, 'levelname') and record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(name: str = "glossary_updater", level: str = "INFO") -> logging.Logger:
    """Set up a logger with colored output."""
    logger = logging.getLogger(name)
    
    # Only add handler if logger doesn't already have one
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        # Use colored formatter if output is a terminal
        if sys.stdout.isatty():
            formatter = ColoredFormatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%H:%M:%S'
            )
        
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(getattr(logging, level.upper()))
    return logger


# Global logger instance
logger = setup_logger()


def validate_file_path(file_path: Union[str, Path]) -> Path:
    """
    Validate that a file path exists and is readable.
    
    Args:
        file_path: Path to validate
        
    Returns:
        Path object if valid
        
    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file isn't readable
        ValueError: If path is not a file
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    
    if not os.access(path, os.R_OK):
        raise PermissionError(f"File is not readable: {path}")
    
    return path


def validate_directory_path(dir_path: Union[str, Path]) -> Path:
    """
    Validate that a directory path exists and is readable.
    
    Args:
        dir_path: Directory path to validate
        
    Returns:
        Path object if valid
        
    Raises:
        FileNotFoundError: If directory doesn't exist
        PermissionError: If directory isn't readable
        ValueError: If path is not a directory
    """
    path = Path(dir_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    
    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")
    
    if not os.access(path, os.R_OK):
        raise PermissionError(f"Directory is not readable: {path}")
    
    return path


def discover_glossary_files(paths: List[Union[str, Path]]) -> Dict[str, List[Path]]:
    """
    Discover glossary files from a list of file and directory paths.
    
    Args:
        paths: List of file paths and/or directory paths
        
    Returns:
        Dictionary with file types as keys and lists of Path objects as values
        
    Raises:
        ValueError: If no valid glossary files are found
    """
    supported_extensions = {'.csv', '.json', '.yaml', '.yml'}
    discovered_files = {
        'csv': [],
        'json': [], 
        'yaml': []
    }
    
    for path_str in paths:
        path = Path(path_str)
        
        if path.is_file():
            # Single file
            try:
                validated_path = validate_file_path(path)
                if validated_path.suffix.lower() in supported_extensions:
                    file_type = get_file_type(validated_path)
                    discovered_files[file_type].append(validated_path)
                else:
                    logger.warning(f"Skipping unsupported file type: {path}")
            except (FileNotFoundError, PermissionError, ValueError) as e:
                logger.error(f"Invalid file path {path}: {e}")
                
        elif path.is_dir():
            # Directory - find all glossary files
            try:
                validated_dir = validate_directory_path(path)
                for file_path in validated_dir.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                        try:
                            file_type = get_file_type(file_path)
                            discovered_files[file_type].append(file_path)
                        except Exception as e:
                            logger.warning(f"Skipping file {file_path}: {e}")
            except (FileNotFoundError, PermissionError, ValueError) as e:
                logger.error(f"Invalid directory path {path}: {e}")
        else:
            logger.warning(f"Path does not exist or is not accessible: {path}")
    
    # Check if any files were found
    total_files = sum(len(files) for files in discovered_files.values())
    if total_files == 0:
        raise ValueError("No valid glossary files found in the specified paths")
    
    # Log discovery results
    for file_type, files in discovered_files.items():
        if files:
            logger.info(f"Found {len(files)} {file_type.upper()} file(s)")
            for file_path in files:
                logger.debug(f"  - {file_path}")
    
    return discovered_files


def get_file_type(file_path: Path) -> str:
    """
    Determine file type from extension.
    
    Args:
        file_path: Path to file
        
    Returns:
        File type string ('csv', 'json', or 'yaml')
        
    Raises:
        ValueError: If file type is not supported
    """
    extension = file_path.suffix.lower()
    
    if extension == '.csv':
        return 'csv'
    elif extension == '.json':
        return 'json'
    elif extension in ['.yaml', '.yml']:
        return 'yaml'
    else:
        raise ValueError(f"Unsupported file type: {extension}")


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


def generate_resource_id() -> str:
    """Generate a resource ID in the format used by the API."""
    # Generate UUID and format it like the example IDs in the config
    return str(uuid.uuid4())


def safe_json_dump(data: Any, indent: int = 2) -> str:
    """
    Safely serialize data to JSON string.
    
    Args:
        data: Data to serialize
        indent: JSON indentation
        
    Returns:
        JSON string
    """
    try:
        return json.dumps(data, indent=indent, ensure_ascii=False)
    except TypeError as e:
        logger.error(f"Failed to serialize data to JSON: {e}")
        raise


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def create_backup_filename(original_name: str, config_id: str) -> str:
    """
    Create a backup filename with timestamp.
    
    Args:
        original_name: Original filename or description
        config_id: Configuration ID
        
    Returns:
        Backup filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{original_name}_backup_{config_id}_{timestamp}.json"


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string if it's longer than max_length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def normalize_phrase(phrase: str) -> str:
    """
    Normalize a glossary phrase for consistent processing.
    
    Args:
        phrase: Raw phrase
        
    Returns:
        Normalized phrase
    """
    if not phrase or not isinstance(phrase, str):
        return ""
    
    # Strip whitespace and normalize
    normalized = phrase.strip()
    
    # Replace multiple whitespace with single space
    import re
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized


def normalize_definition(definition: str) -> str:
    """
    Normalize a glossary definition for consistent processing.
    
    Args:
        definition: Raw definition
        
    Returns:
        Normalized definition
    """
    if not definition or not isinstance(definition, str):
        return ""
    
    # Strip whitespace and normalize
    normalized = definition.strip()
    
    # Replace multiple whitespace with single space but preserve line breaks
    import re
    normalized = re.sub(r'[ \t]+', ' ', normalized)
    normalized = re.sub(r'\n\s*\n', '\n\n', normalized)  # Clean up line breaks
    
    return normalized


class ProgressTracker:
    """Simple progress tracker for file processing."""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        
    def update(self, increment: int = 1):
        """Update progress."""
        self.current += increment
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        logger.info(f"{self.description}: {self.current}/{self.total} ({percentage:.1f}%)")
    
    def finish(self):
        """Mark as finished."""
        logger.info(f"{self.description}: Complete!")
