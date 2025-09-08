"""
Test suite for Glossary Configuration Updater

This package contains comprehensive tests for all components of the
Glossary Configuration Updater project.

Test Structure:
- test_main.py: Tests for main orchestration logic
- test_processor.py: Tests for file processing components
- test_merger.py: Tests for configuration merging logic
- test_api_client.py: Tests for API client functionality
- test_config.py: Tests for configuration management
- test_utils.py: Tests for utility functions
- fixtures/: Test data files and fixtures

Usage:
    # Run all tests
    pytest

    # Run specific test file
    pytest tests/test_processor.py

    # Run with coverage
    pytest --cov=glossary_updater

    # Run with verbose output
    pytest -v

    # Run specific test
    pytest tests/test_processor.py::TestFileProcessor::test_process_csv
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_DATA_DIR = Path(__file__).parent / "fixtures"
TEMP_TEST_DIR = Path(__file__).parent / "temp"

# Ensure test directories exist
TEST_DATA_DIR.mkdir(exist_ok=True)
TEMP_TEST_DIR.mkdir(exist_ok=True)

# Common test constants
TEST_API_DOMAIN = "test.example.com"
TEST_USERNAME = "test_user"
TEST_PASSWORD = "test_password"
TEST_CONFIG_ID = "test_config_123"

# Test data samples
SAMPLE_CSV_DATA = """phrase,definition,category
API,"Application Programming Interface",Technical
REST,"Representational State Transfer",Technical
JSON,"JavaScript Object Notation",Technical"""

SAMPLE_JSON_DATA = {
    "glossary": [
        {
            "phrase": "Machine Learning",
            "definition": "Type of artificial intelligence that enables computers to learn",
            "category": "AI"
        },
        {
            "phrase": "Cloud Computing", 
            "definition": "Delivery of computing services over the internet",
            "category": "Infrastructure"
        }
    ]
}

SAMPLE_YAML_DATA = """
glossary:
  - phrase: "DevOps"
    definition: "Set of practices combining software development and IT operations"
    category: "Process"
  - phrase: "Agile"
    definition: "Iterative development methodology emphasizing collaboration"
    category: "Methodology"
"""

SAMPLE_CONFIG_DATA = {
    "id": "test_config_123",
    "name": "Test Configuration",
    "analysisEntityList": [
        {
            "id": "676c6f73-7361-7279-3132-333435363738",
            "name": "Glossary",
            "type": "glossary",
            "enabled": True,
            "resources": [],
            "searchOrder": 1
        }
    ],
    "resourceList": []
}

# Helper functions for tests
def get_test_data_path(filename: str) -> Path:
    """Get path to test data file."""
    return TEST_DATA_DIR / filename

def get_temp_path(filename: str) -> Path:
    """Get path to temporary test file."""
    return TEMP_TEST_DIR / filename

def cleanup_temp_files():
    """Clean up temporary test files."""
    if TEMP_TEST_DIR.exists():
        for file in TEMP_TEST_DIR.iterdir():
            if file.is_file():
                file.unlink()
