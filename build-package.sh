#!/bin/bash

# Build script for Glossary Configuration Updater
# Creates both source distribution and wheel packages

set -e  # Exit on any error

echo "=========================================="
echo "Building Glossary Configuration Updater"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "setup.py" ] || [ ! -f "pyproject.toml" ]; then
    print_error "setup.py or pyproject.toml not found. Run this script from the project root."
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1-2)
required_version="3.8"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    print_error "Python 3.8 or higher is required. Found: $python_version"
    exit 1
fi

print_status "Python version check passed: $python_version"

# Clean previous builds
print_status "Cleaning previous builds..."
rm -rf build/
rm -rf dist/
rm -rf *.egg-info/
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

print_success "Cleaned build artifacts"

# Upgrade build tools
print_status "Upgrading build tools..."
python3 -m pip install --upgrade pip setuptools wheel build twine

# Install development dependencies if needed
if [ "$1" = "--dev" ]; then
    print_status "Installing development dependencies..."
    python3 -m pip install -e ".[dev]"
fi

# Run tests if requested
if [ "$1" = "--test" ] || [ "$2" = "--test" ]; then
    print_status "Running tests..."
    if [ -d "tests" ]; then
        python3 -m pytest tests/ -v
        print_success "Tests passed"
    else
        print_warning "No tests directory found, skipping tests"
    fi
fi

# Run linting if development dependencies are available
if python3 -c "import black" 2>/dev/null; then
    print_status "Running code formatting checks..."
    python3 -m black --check glossary_updater/ tools/ || {
        print_warning "Code formatting issues found. Run 'black glossary_updater/ tools/' to fix."
    }
fi

if python3 -c "import flake8" 2>/dev/null; then
    print_status "Running code quality checks..."
    python3 -m flake8 glossary_updater/ tools/ || {
        print_warning "Code quality issues found."
    }
fi

# Validate package metadata
print_status "Validating package metadata..."
python3 setup.py check --metadata --restructuredtext --strict

# Build source distribution
print_status "Building source distribution..."
python3 -m build --sdist

# Build wheel distribution
print_status "Building wheel distribution..."
python3 -m build --wheel

# Verify the build
print_status "Verifying build..."
if [ ! -d "dist" ]; then
    print_error "Build failed - no dist directory found"
    exit 1
fi

# Count and list built packages
source_count=$(find dist/ -name "*.tar.gz" | wc -l)
wheel_count=$(find dist/ -name "*.whl" | wc -l)

if [ "$source_count" -eq 0 ] || [ "$wheel_count" -eq 0 ]; then
    print_error "Build incomplete - missing source or wheel distribution"
    exit 1
fi

print_success "Build completed successfully!"
echo
echo "Built packages:"
ls -la dist/

# Check package with twine
if python3 -c "import twine" 2>/dev/null; then
    print_status "Checking package with twine..."
    python3 -m twine check dist/*
    print_success "Package validation passed"
else
    print_warning "twine not available, skipping package validation"
fi

# Display package information
echo
echo "=========================================="
echo "Package Information"
echo "=========================================="
echo "Source distributions: $source_count"
echo "Wheel distributions: $wheel_count"
echo "Total size: $(du -sh dist/ | cut -f1)"
echo

# Installation instructions
echo "=========================================="
echo "Installation Instructions"
echo "=========================================="
echo "To install locally:"
echo "  pip install dist/glossary_config_updater-*.whl"
echo
echo "To install in development mode:"
echo "  pip install -e ."
echo
echo "To upload to PyPI (when ready):"
echo "  python3 -m twine upload dist/*"
echo

print_success "Build process completed!"

# Optional: Test installation in clean environment
if [ "$1" = "--test-install" ] || [ "$2" = "--test-install" ] || [ "$3" = "--test-install" ]; then
    print_status "Testing installation in virtual environment..."
    
    # Create temporary virtual environment
    temp_venv=$(mktemp -d)
    python3 -m venv "$temp_venv"
    source "$temp_venv/bin/activate"
    
    # Install the built package
    pip install dist/glossary_config_updater-*.whl
    
    # Test import
    python3 -c "import glossary_updater; print('Import successful')"
    
    # Test CLI
    glossary-updater --help > /dev/null
    
    # Cleanup
    deactivate
    rm -rf "$temp_venv"
    
    print_success "Installation test passed"
fi

echo "Build script completed at $(date)"
