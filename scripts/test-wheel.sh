#!/bin/bash
set -e

# Test wheel distribution for glossary-config-updater
# Usage: ./test-wheel.sh

WHEEL_DIR="dist-wheel"
VENV_DIR="test_wheel_env"

echo "🧪 Glossary Config Updater - Wheel Tester"
echo "=========================================="
echo ""

# Find wheel file
if [ ! -d "$WHEEL_DIR" ]; then
    echo "❌ Error: Wheel directory not found: $WHEEL_DIR"
    echo "   Run ./build-wheel.sh first"
    exit 1
fi

WHEEL_FILE=$(find $WHEEL_DIR -name "*.whl" | head -1)
if [ -z "$WHEEL_FILE" ]; then
    echo "❌ Error: No wheel file found in $WHEEL_DIR"
    echo "   Run ./build-wheel.sh first"
    exit 1
fi

echo "🔍 Testing wheel: $(basename $WHEEL_FILE)"
echo ""

# Clean up any previous test environment
echo "🧹 Cleaning previous test environment..."
rm -rf $VENV_DIR

# Create fresh virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Upgrade pip in virtual environment
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install the wheel
echo ""
echo "📦 Installing wheel package..."
pip install "$WHEEL_FILE"

# Test 1: Import test
echo ""
echo "✅ Test 1: Package import"
python -c "
import glossary_updater
print(f'✓ Package imported successfully')
print(f'✓ Version: {glossary_updater.__version__}')
"

# Test 2: CLI availability
echo ""
echo "✅ Test 2: CLI command availability"
if command -v glossary-updater >/dev/null 2>&1; then
    echo "✓ CLI command 'glossary-updater' is available"
else
    echo "❌ CLI command 'glossary-updater' not found"
    exit 1
fi

# Test 3: Help command
echo ""
echo "✅ Test 3: Help command"
glossary-updater --help > /dev/null
echo "✓ Help command works"

# Test 4: Version command
echo ""
echo "✅ Test 4: Version command"
VERSION_OUTPUT=$(glossary-updater --version 2>&1)
echo "✓ Version output: $VERSION_OUTPUT"

# Test 5: Configuration validation (dry-run mode)
echo ""
echo "✅ Test 5: Configuration validation"
python -c "
from glossary_updater.config import Config
config = Config()
print('✓ Configuration module loads successfully')
"

# Test 6: File processor validation
echo ""
echo "✅ Test 6: File processor validation"
python -c "
from glossary_updater.processor import FileProcessor
processor = FileProcessor()
print('✓ File processor module loads successfully')
"

# Test 7: API client validation
echo ""
echo "✅ Test 7: API client validation"
python -c "
from glossary_updater.api_client import ApiClient
print('✓ API client module loads successfully')
"

# Test 8: Merger validation
echo ""
echo "✅ Test 8: Merger validation"
python -c "
from glossary_updater.merger import TermsMerger
merger = TermsMerger()
print('✓ Terms merger module loads successfully')
"

# Test 9: Test with sample data (if fixtures exist)
echo ""
echo "✅ Test 9: Sample data processing"
if [ -f "tests/fixtures/valid-terms.csv" ]; then
    python -c "
from glossary_updater.processor import FileProcessor
processor = FileProcessor()
terms = processor.load_file('tests/fixtures/valid-terms.csv')
print(f'✓ Loaded {len(terms)} terms from test fixture')
"
else
    echo "⚠️  Test fixtures not available (this is okay for wheel testing)"
fi

# Test 10: CLI with invalid arguments (should fail gracefully)
echo ""
echo "✅ Test 10: CLI error handling"
if glossary-updater --invalid-arg 2>/dev/null; then
    echo "❌ CLI should reject invalid arguments"
    exit 1
else
    echo "✓ CLI properly rejects invalid arguments"
fi

# Cleanup
echo ""
echo "🧹 Cleaning up test environment..."
deactivate
rm -rf $VENV_DIR

# Summary
echo ""
echo "🎉 All wheel tests passed successfully!"
echo ""
echo "✅ Package Installation: Works"
echo "✅ CLI Commands: Available"
echo "✅ Module Imports: Working"
echo "✅ Error Handling: Proper"
echo ""
echo "📦 Wheel package is ready for distribution!"