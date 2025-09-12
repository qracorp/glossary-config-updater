#!/bin/bash

# Simple build script for Glossary Configuration Updater
# Creates one customer-ready tar.gz package

set -e

# Configuration
VERSION="${1:-1.0.0}"
BUILD_DIR="build"
PACKAGE_NAME="glossary-config-updater"
PACKAGE_DIR="${PACKAGE_NAME}-v${VERSION}"

# Handle --clean flag
if [[ "$*" == *"--clean"* ]]; then
    echo "[INFO] Cleaning previous builds..."
    rm -rf "$BUILD_DIR" 2>/dev/null || true
    rm -rf dist/ *.egg-info/ 2>/dev/null || true
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    echo "[SUCCESS] Cleaned previous builds"
fi

# Validate we're in the right directory
if [ ! -f "setup.py" ] && [ ! -f "pyproject.toml" ]; then
    echo "[ERROR] Must run from package root directory (setup.py or pyproject.toml not found)"
    exit 1
fi

if [ ! -d "glossary_updater" ]; then
    echo "[ERROR] glossary_updater directory not found"
    exit 1
fi

echo "[INFO] Building Glossary Configuration Updater v${VERSION}"
echo "[INFO] Creating single customer package..."

# Detect Python command
echo "[INFO] Detecting Python installation..."

PYTHON_CMD=""

# Test py launcher (Windows Python Launcher)
if command -v py >/dev/null 2>&1; then
    if py --version >/dev/null 2>&1; then
        echo "[SUCCESS] Found Python via 'py' launcher"
        PYTHON_CMD="py"
    fi
fi

# Test python3 if py not found
if [ -z "$PYTHON_CMD" ] && command -v python3 >/dev/null 2>&1; then
    python3_version=$(python3 --version 2>&1)
    if [[ $? -eq 0 ]] && ! [[ "$python3_version" =~ "Microsoft Store" ]]; then
        echo "[SUCCESS] Found Python3: $python3_version"
        PYTHON_CMD="python3"
    fi
fi

# Test python if others not found
if [ -z "$PYTHON_CMD" ] && command -v python >/dev/null 2>&1; then
    python_version=$(python --version 2>&1)
    if [[ $? -eq 0 ]] && ! [[ "$python_version" =~ "Microsoft Store" ]]; then
        echo "[SUCCESS] Found Python: $python_version"
        PYTHON_CMD="python"
    fi
fi

# Check if we found a working Python
if [ -z "$PYTHON_CMD" ]; then
    echo "[ERROR] No working Python installation found"
    echo "[ERROR] Windows users: This is likely the Microsoft Store Python alias issue"
    echo "[ERROR] Solutions:"
    echo "[ERROR]   1. Install Python from python.org (recommended)"
    echo "[ERROR]   2. Disable Windows Store Python alias in Settings"
    exit 1
fi

# Create build directory
rm -rf "$BUILD_DIR/$PACKAGE_DIR" 2>/dev/null || true
mkdir -p "$BUILD_DIR/$PACKAGE_DIR"

PACKAGE_PATH="$BUILD_DIR/$PACKAGE_DIR"

# Step 1: Build the wheel
echo "[INFO] Building Python wheel..."
rm -rf dist/ *.egg-info/ 2>/dev/null || true

# Install build dependencies
echo "[INFO] Installing build dependencies..."
$PYTHON_CMD -m pip install --upgrade pip setuptools wheel build

# Build the wheel
echo "[INFO] Building wheel package..."
$PYTHON_CMD -m build --wheel

if [ ! -f dist/*.whl ]; then
    echo "[ERROR] Wheel build failed - no .whl file created"
    exit 1
fi

echo "[SUCCESS] Wheel built successfully"

# Step 2: Copy all customer files
echo "[INFO] Copying customer files..."

# Main package files
if [ -d "glossary_updater" ]; then
    cp -r glossary_updater "$PACKAGE_PATH/"
    echo "[SUCCESS] Copied source code: glossary_updater/"
else
    echo "[ERROR] glossary_updater directory not found"
    exit 1
fi

# Tools directory
if [ -f "tools/glossary_updater.py" ]; then
    mkdir -p "$PACKAGE_PATH/tools"
    cp tools/glossary_updater.py "$PACKAGE_PATH/tools/"
    echo "[SUCCESS] Copied standalone script: tools/glossary_updater.py"
else
    echo "[ERROR] tools/glossary_updater.py not found"
    exit 1
fi

# Include the wheel file at root level
cp dist/*.whl "$PACKAGE_PATH/"
WHEEL_NAME=$(basename dist/*.whl)
echo "[SUCCESS] Added wheel: $WHEEL_NAME"

# Schema files (critical!)
echo "[INFO] Copying schema files..."
schema_count=0
for schema_file in *.json; do
    if [ -f "$schema_file" ]; then
        cp "$schema_file" "$PACKAGE_PATH/"
        echo "[SUCCESS] Copied schema: $schema_file"
        schema_count=$((schema_count + 1))
    fi
done

if [ $schema_count -eq 0 ]; then
    echo "[ERROR] No schema files (*.json) found - these are required!"
    exit 1
fi

# Documentation
echo "[INFO] Copying documentation..."
[ -f "guide.md" ] && cp guide.md "$PACKAGE_PATH/" && echo "[SUCCESS] Copied guide.md"
[ -f "requirements.txt" ] && cp requirements.txt "$PACKAGE_PATH/" && echo "[SUCCESS] Copied requirements.txt"

# Examples (customer-safe only)
if [ -d "examples" ]; then
    mkdir -p "$PACKAGE_PATH/examples"
    example_count=0
    
    # Copy regular files in examples/ directory
    for item in examples/*; do
        if [ -f "$item" ]; then
            filename=$(basename "$item")
            case "$filename" in
                *test*|*dev*|*debug*|*build*) 
                    echo "[INFO] Skipping dev example: $filename"
                    ;;
                *)
                    cp "$item" "$PACKAGE_PATH/examples/"
                    example_count=$((example_count + 1))
                    ;;
            esac
        elif [ -d "$item" ]; then
            # Copy subdirectories (like examples/glossary/)
            subdir_name=$(basename "$item")
            case "$subdir_name" in
                *test*|*dev*|*debug*)
                    echo "[INFO] Skipping dev example directory: $subdir_name"
                    ;;
                *)
                    cp -r "$item" "$PACKAGE_PATH/examples/"
                    example_count=$((example_count + 1))
                    ;;
            esac
        fi
    done
    
    # Copy hidden files (like .env.example, .gitignore.example)
    echo "[INFO] Copying hidden example files..."
    for hidden_file in examples/.*; do
        if [ -f "$hidden_file" ]; then
            filename=$(basename "$hidden_file")
            case "$filename" in
                .|..)
                    # Skip . and .. directories
                    ;;
                .env.example|.gitignore.example|.*.example)
                    cp "$hidden_file" "$PACKAGE_PATH/examples/"
                    echo "[SUCCESS] Copied hidden example: $filename"
                    example_count=$((example_count + 1))
                    ;;
                .env|.git*|.*cache*|.*tmp*)
                    echo "[INFO] Skipping hidden system file: $filename"
                    ;;
                *)
                    echo "[INFO] Skipping hidden file: $filename"
                    ;;
            esac
        fi
    done
    
    if [ $example_count -gt 0 ]; then
        echo "[SUCCESS] Copied $example_count example files/directories"
    else
        echo "[INFO] No examples to copy"
    fi
fi

# Documentation directory
if [ -d "docs" ]; then
    mkdir -p "$PACKAGE_PATH/docs"
    doc_count=0
    
    for doc_file in docs/*; do
        if [ -f "$doc_file" ]; then
            filename=$(basename "$doc_file")
            case "$filename" in
                *dev*|*api-reference*|*contributing*|*build*)
                    echo "[INFO] Skipping dev doc: $filename"
                    ;;
                *)
                    cp "$doc_file" "$PACKAGE_PATH/docs/"
                    doc_count=$((doc_count + 1))
                    ;;
            esac
        fi
    done
    
    if [ $doc_count -gt 0 ]; then
        echo "[SUCCESS] Copied $doc_count documentation files"
    else
        echo "[INFO] No documentation files to copy"
    fi
fi

# Step 3: Create version info
echo "[INFO] Creating version information..."
cat > "$PACKAGE_PATH/VERSION" << EOF
Glossary Configuration Updater
Version: ${VERSION}
Build Date: $(date)
Package Type: Customer Package

Contents:
- Standalone script: tools/glossary_updater.py
- Installable package: ${WHEEL_NAME}
- Source code: glossary_updater/
- Schema files: *.json (${schema_count} files)
- Examples and documentation

Usage Options:
1. Standalone: python tools/glossary_updater.py [options]
2. Installed: pip install ${WHEEL_NAME} && glossary-updater [options]

Quick Start:
  Extract package: tar -xzf ${PACKAGE_NAME}-v${VERSION}.tar.gz
  Change directory: cd ${PACKAGE_DIR}
  Install deps: pip install -r requirements.txt
  Run script: python tools/glossary_updater.py --help
EOF

# Step 4: Create the final tar.gz
echo "[INFO] Creating customer package archive..."
cd "$BUILD_DIR"
tar -czf "${PACKAGE_NAME}-v${VERSION}.tar.gz" "$PACKAGE_DIR"
cd ..

# Step 5: Verify and show results
if [ -f "$BUILD_DIR/${PACKAGE_NAME}-v${VERSION}.tar.gz" ]; then
    PACKAGE_SIZE=$(du -h "$BUILD_DIR/${PACKAGE_NAME}-v${VERSION}.tar.gz" | cut -f1)
    
    echo "[SUCCESS] Package created successfully!"
    echo ""
    echo "[INFO] Customer package: $BUILD_DIR/${PACKAGE_NAME}-v${VERSION}.tar.gz ($PACKAGE_SIZE)"
    echo "[INFO] Extract with: tar -xzf ${PACKAGE_NAME}-v${VERSION}.tar.gz"
    echo ""
    echo "[SUCCESS] Ready for customer delivery!"
    
    # Show package contents summary
    echo "[INFO] Package contents:"
    echo "  ${PACKAGE_DIR}/"
    echo "     ├── ${WHEEL_NAME} (installable package)"
    echo "     ├── tools/glossary_updater.py (standalone script)"
    echo "     ├── glossary_updater/ (source code)"
    echo "     ├── *.json (${schema_count} schema files)"
    [ -d "examples" ] && echo "     ├── examples/ (customer examples)"
    [ -d "docs" ] && echo "     ├── docs/ (documentation)"
    [ -f "guide.md" ] && echo "     ├── guide.md (user guide)"
    [ -f "requirements.txt" ] && echo "     ├── requirements.txt (dependencies)"
    echo "     └── VERSION (build info)"
    
else
    echo "[ERROR] Package creation failed"
    exit 1
fi

# Clean up temporary files
echo "[INFO] Cleaning up temporary files..."
rm -rf "$BUILD_DIR/$PACKAGE_DIR" 2>/dev/null || true
rm -rf dist/ *.egg-info/ 2>/dev/null || true

echo "[SUCCESS] Build complete!"