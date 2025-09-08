#!/bin/bash
set -e

# Build wheel distribution for glossary-config-updater
# Usage: ./build-wheel.sh [VERSION]

VERSION=${1:-"1.0.0"}
BUILD_DIR="dist"
WHEEL_DIR="dist-wheel"

echo "🔨 Glossary Config Updater - Wheel Builder"
echo "=========================================="
echo "Version: $VERSION"
echo ""

# Validate we're in the right directory
if [ ! -f "setup.py" ] || [ ! -d "glossary_updater" ]; then
    echo "❌ Error: Must be run from package root directory"
    echo "   Expected files: setup.py, glossary_updater/"
    exit 1
fi

# Check Python version
echo "🐍 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "✅ Python: $PYTHON_VERSION"

# Clean previous builds
echo ""
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info/
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Install build dependencies
echo ""
echo "📦 Installing build dependencies..."
python3 -m pip install --upgrade pip setuptools wheel build twine

# Update version in __init__.py
echo ""
echo "📝 Updating version to ${VERSION}..."
sed -i.bak "s/__version__ = \".*\"/__version__ = \"${VERSION}\"/" glossary_updater/__init__.py
rm -f glossary_updater/__init__.py.bak

# Build source distribution and wheel
echo ""
echo "🔨 Building source distribution and wheel..."
python3 -m build

# Verify build
echo ""
echo "🔍 Verifying build..."
if [ ! -d "$BUILD_DIR" ]; then
    echo "❌ Build directory not found!"
    exit 1
fi

WHEEL_FILE=$(find $BUILD_DIR -name "*.whl" | head -1)
TAR_FILE=$(find $BUILD_DIR -name "*.tar.gz" | head -1)

if [ -z "$WHEEL_FILE" ] || [ -z "$TAR_FILE" ]; then
    echo "❌ Build files not found!"
    ls -la $BUILD_DIR/
    exit 1
fi

echo "✅ Built successfully:"
echo "   Wheel: $(basename $WHEEL_FILE)"
echo "   Source: $(basename $TAR_FILE)"

# Create wheel distribution directory
echo ""
echo "📁 Organizing distribution files..."
mkdir -p $WHEEL_DIR
cp $BUILD_DIR/*.whl $WHEEL_DIR/
cp $BUILD_DIR/*.tar.gz $WHEEL_DIR/

# Generate checksums
echo ""
echo "🔐 Generating checksums..."
cd $WHEEL_DIR
for file in *.whl *.tar.gz; do
    if [ -f "$file" ]; then
        md5sum "$file" > "${file}.md5"
        sha256sum "$file" > "${file}.sha256"
    fi
done
cd ..

# Display results
echo ""
echo "✅ Wheel Build Complete!"
echo ""
echo "📦 Distribution files available in: $WHEEL_DIR/"
ls -la $WHEEL_DIR/
echo ""
echo "🚀 Ready for distribution!"
echo ""
echo "To install:"
echo "  pip install $WHEEL_DIR/*.whl"
echo ""
echo "To test:"
echo "  ./test-wheel.sh"