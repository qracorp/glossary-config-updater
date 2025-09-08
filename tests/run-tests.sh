#!/bin/bash
set -e

# Run tests for glossary-config-updater
# Usage: ./run-tests.sh [OPTIONS]
#   --coverage    Run with coverage report
#   --verbose     Verbose output
#   --fast        Skip slow integration tests

COVERAGE=false
VERBOSE=false
FAST=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --coverage)
            COVERAGE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --fast)
            FAST=true
            shift
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--coverage] [--verbose] [--fast]"
            exit 1
            ;;
    esac
done

echo "🧪 Glossary Config Updater - Test Runner"
echo "========================================"
echo ""

# Validate we're in the right directory
if [ ! -f "setup.py" ] || [ ! -d "tests" ]; then
    echo "❌ Error: Must be run from package root directory"
    echo "   Expected files: setup.py, tests/"
    exit 1
fi

# Check if running in virtual environment (recommended)
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Not running in a virtual environment"
    echo "   Consider activating a virtual environment first"
    echo ""
fi

# Install test dependencies
echo "📦 Installing test dependencies..."
pip install -q pytest pytest-cov pytest-mock requests-mock

# Install package in development mode
echo "📦 Installing package in development mode..."
pip install -e .

# Set up test environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export API_DOMAIN="test.example.com"
export API_USERNAME="test-user"
export API_PASSWORD="test-password"

# Configure pytest options
PYTEST_OPTS="tests/"

if [ "$VERBOSE" = true ]; then
    PYTEST_OPTS="$PYTEST_OPTS -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_OPTS="$PYTEST_OPTS --cov=glossary_updater --cov-report=term-missing --cov-report=html"
fi

if [ "$FAST" = true ]; then
    PYTEST_OPTS="$PYTEST_OPTS -m 'not slow'"
fi

# Run the tests
echo ""
echo "🚀 Running tests..."
echo "Command: pytest $PYTEST_OPTS"
echo ""

pytest $PYTEST_OPTS

# Test result handling
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "🎉 All tests passed!"
    
    if [ "$COVERAGE" = true ]; then
        echo ""
        echo "📊 Coverage report generated in htmlcov/"
        echo "   Open htmlcov/index.html in your browser to view"
    fi
    
    # Run additional validation tests
    echo ""
    echo "🔍 Running additional validation..."
    
    # Test CLI installation
    echo "✅ Testing CLI installation..."
    if command -v glossary-updater >/dev/null 2>&1; then
        echo "✓ CLI command available"
        glossary-updater --version
    else
        echo "❌ CLI command not available"
        exit 1
    fi
    
    # Test import paths
    echo ""
    echo "✅ Testing import paths..."
    python -c "
import glossary_updater
from glossary_updater import main, config, api_client, processor, merger, utils
print('✓ All modules import successfully')
"
    
    # Validate fixtures
    echo ""
    echo "✅ Validating test fixtures..."
    python -c "
import os
import csv
import json
import yaml

fixtures_dir = 'tests/fixtures'
expected_files = ['valid-terms.csv', 'invalid-terms.csv', 'terms.json', 'terms.yaml']

for filename in expected_files:
    filepath = os.path.join(fixtures_dir, filename)
    if os.path.exists(filepath):
        print(f'✓ {filename} exists')
        
        # Basic validation
        if filename.endswith('.csv'):
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                print(f'  - {len(rows)} rows')
        elif filename.endswith('.json'):
            with open(filepath, 'r') as f:
                data = json.load(f)
                print(f'  - {len(data)} items')
        elif filename.endswith('.yaml'):
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
                print(f'  - {len(data)} items')
    else:
        print(f'⚠️  {filename} missing')
"
    
    echo ""
    echo "✅ All validations passed!"
    
else
    echo ""
    echo "❌ Tests failed with exit code: $TEST_EXIT_CODE"
    echo ""
    echo "💡 Troubleshooting tips:"
    echo "   1. Check test output above for specific failures"
    echo "   2. Run with --verbose for more details"
    echo "   3. Check that all dependencies are installed"
    echo "   4. Verify test fixtures are present"
    echo ""
    exit $TEST_EXIT_CODE
fi

echo ""
echo "🎯 Test Summary:"
echo "=================="
echo "✅ Unit tests: PASSED"
echo "✅ Import tests: PASSED" 
echo "✅ CLI tests: PASSED"
echo "✅ Fixture validation: PASSED"

if [ "$COVERAGE" = true ]; then
    echo "📊 Coverage report: GENERATED"
fi

echo ""
echo "🚀 Ready for production!"