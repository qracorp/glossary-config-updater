"""
Test suite for Glossary Configuration Updater

This package contains comprehensive behavior-focused tests for all components 
of the Glossary Configuration Updater project.

Test Philosophy:
- Focus on testing actual behavior rather than implementation details
- Use realistic test data and scenarios
- Minimize unnecessary mocking - test real code paths where possible
- Test integration scenarios with controlled dependencies
- Validate error handling with real error conditions

Test Structure:
- test_processor.py: File processing behavior with real files and validation
- test_main.py: Main orchestration and integration testing with HTTP mocking
- test_merger.py: Configuration merging logic with realistic data scenarios
- fixtures/: Real test data files for comprehensive testing

Test Categories:
- Unit tests: Test individual component behavior
- Integration tests: Test component interactions
- Behavior tests: Test end-to-end workflows

Usage:
    # Run all tests
    ./run-tests.sh
    
    # Run specific test module
    pytest tests/test_processor.py -v
    
    # Run with coverage
    ./run-tests.sh --coverage
    
    # Run only integration tests
    pytest -m integration
    
    # Run excluding slow tests
    pytest -m "not slow"

Environment Variables for Testing:
    API_DOMAIN: Test API domain (default: test.example.com)
    API_USERNAME: Test username (default: test-user)  
    API_PASSWORD: Test password (default: test-password)
    SSL_VERIFY: SSL verification for tests (default: false)
"""

import os
import sys
from pathlib import Path
import tempfile
import shutil
from typing import Dict, Any, List

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Test configuration constants
TEST_DATA_DIR = Path(__file__).parent / "fixtures"
TEMP_TEST_DIR = Path(__file__).parent / "temp"

# Ensure test directories exist
TEST_DATA_DIR.mkdir(exist_ok=True)
TEMP_TEST_DIR.mkdir(exist_ok=True)

# Test API constants
TEST_API_DOMAIN = os.getenv("API_DOMAIN", "test.example.com")
TEST_USERNAME = os.getenv("API_USERNAME", "test-user")
TEST_PASSWORD = os.getenv("API_PASSWORD", "test-password")
TEST_CONFIG_ID = "test-config-123"

# Sample test data for use across test modules
SAMPLE_CSV_DATA = """phrase,definition,category,priority
API,"Application Programming Interface - a set of protocols for building software",Technical,High
REST,"Representational State Transfer - architectural style for web services",Technical,High
JSON,"JavaScript Object Notation - lightweight data interchange format",Technical,Medium
YAML,"YAML Ain't Markup Language - human-readable data serialization",Technical,Medium
OAuth,"Open Authorization - open standard for access delegation",Security,High"""

SAMPLE_JSON_DATA = {
    "glossary_terms": [
        {
            "phrase": "Docker",
            "definition": "Platform for developing and running applications in containers",
            "category": "DevOps"
        },
        {
            "phrase": "Kubernetes",
            "definition": "Open-source container orchestration platform",
            "category": "DevOps"
        },
        {
            "phrase": "Microservices",
            "definition": "Architectural approach with small independent services",
            "category": "Architecture"
        }
    ]
}

SAMPLE_YAML_DATA = """
glossary_terms:
  - phrase: "CI/CD"
    definition: "Continuous Integration/Continuous Deployment practices"
    category: "DevOps"
  - phrase: "DevOps"
    definition: "Development and Operations collaboration practices"
    category: "Culture"
  - phrase: "Agile"
    definition: "Iterative development methodology"
    category: "Methodology"
"""

# Sample configuration data matching the actual API schema
SAMPLE_CONFIG_DATA = {
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


class TestDataManager:
    """Utility class for managing test data and fixtures."""
    
    @staticmethod
    def create_temp_file(name: str, content: str, directory: Path = None) -> Path:
        """Create a temporary file with given content."""
        if directory is None:
            directory = TEMP_TEST_DIR
        
        file_path = directory / name
        file_path.write_text(content, encoding='utf-8')
        return file_path
    
    @staticmethod
    def create_temp_dir() -> Path:
        """Create a temporary directory for test files."""
        return Path(tempfile.mkdtemp(dir=TEMP_TEST_DIR))
    
    @staticmethod
    def cleanup_temp_files():
        """Clean up all temporary test files."""
        if TEMP_TEST_DIR.exists():
            for file in TEMP_TEST_DIR.rglob('*'):
                if file.is_file():
                    try:
                        file.unlink()
                    except OSError:
                        pass
                elif file.is_dir() and file != TEMP_TEST_DIR:
                    try:
                        shutil.rmtree(file)
                    except OSError:
                        pass
    
    @staticmethod
    def get_fixture_path(filename: str) -> Path:
        """Get path to a test fixture file."""
        return TEST_DATA_DIR / filename
    
    @staticmethod
    def fixture_exists(filename: str) -> bool:
        """Check if a fixture file exists."""
        return (TEST_DATA_DIR / filename).exists()
    
    @staticmethod
    def create_sample_csv(filename: str = "sample.csv") -> Path:
        """Create a sample CSV file for testing."""
        return TestDataManager.create_temp_file(filename, SAMPLE_CSV_DATA)
    
    @staticmethod
    def create_sample_json(filename: str = "sample.json") -> Path:
        """Create a sample JSON file for testing."""
        import json
        content = json.dumps(SAMPLE_JSON_DATA, indent=2)
        return TestDataManager.create_temp_file(filename, content)
    
    @staticmethod
    def create_sample_yaml(filename: str = "sample.yaml") -> Path:
        """Create a sample YAML file for testing."""
        return TestDataManager.create_temp_file(filename, SAMPLE_YAML_DATA)


class MockAPIResponses:
    """Utility class for creating mock API responses."""
    
    @staticmethod
    def create_auth_response(token: str = "test-token-123") -> Dict[str, Any]:
        """Create a mock authentication response."""
        return {"token": token}
    
    @staticmethod
    def create_config_response(config_id: str = None, 
                             with_existing_terms: bool = False) -> Dict[str, Any]:
        """Create a mock configuration response."""
        config = SAMPLE_CONFIG_DATA.copy()
        if config_id:
            config["configurationId"] = config_id
            
        if with_existing_terms:
            config["data"]["resourceList"] = [
                {
                    "id": "existing-resource-1",
                    "phrase": "Existing Term",
                    "definition": "An existing term definition"
                }
            ]
            config["data"]["analysisEntityList"][0]["resources"] = ["existing-resource-1"]
            
        return config
    
    @staticmethod
    def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
        """Create a mock error response."""
        return {
            "error": {
                "status": status_code,
                "message": message
            }
        }


def setup_test_environment():
    """Set up the test environment."""
    # Ensure test directories exist
    TEST_DATA_DIR.mkdir(exist_ok=True)
    TEMP_TEST_DIR.mkdir(exist_ok=True)
    
    # Set environment variables for testing
    os.environ.setdefault("API_DOMAIN", TEST_API_DOMAIN)
    os.environ.setdefault("API_USERNAME", TEST_USERNAME)
    os.environ.setdefault("API_PASSWORD", TEST_PASSWORD)
    os.environ.setdefault("SSL_VERIFY", "false")
    
    # Set Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def teardown_test_environment():
    """Clean up the test environment."""
    TestDataManager.cleanup_temp_files()


# Test markers for pytest
pytest_plugins = []

# Custom pytest markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "behavior: marks tests as behavior tests")


# Auto-setup when module is imported
setup_test_environment()

# Export commonly used items
__all__ = [
    "TEST_DATA_DIR",
    "TEMP_TEST_DIR", 
    "TEST_API_DOMAIN",
    "TEST_USERNAME",
    "TEST_PASSWORD",
    "TEST_CONFIG_ID",
    "SAMPLE_CSV_DATA",
    "SAMPLE_JSON_DATA", 
    "SAMPLE_YAML_DATA",
    "SAMPLE_CONFIG_DATA",
    "TestDataManager",
    "MockAPIResponses",
    "setup_test_environment",
    "teardown_test_environment"
]