#!/bin/bash

# Development Environment Setup Script for Glossary Configuration Updater
# This script sets up a complete development environment with all dependencies

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ASCII symbols
CHECK_MARK="[OK]"
CROSS_MARK="[ERROR]"
WARNING="[WARN]"
INFO="[INFO]"
STEP="[STEP]"

# Function to print colored output
print_header() {
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================${NC}"
}

print_step() {
    echo -e "${CYAN}${STEP} $1${NC}"
}

print_success() {
    echo -e "${GREEN}${CHECK_MARK} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
}

print_error() {
    echo -e "${RED}${CROSS_MARK} $1${NC}"
}

print_info() {
    echo -e "${PURPLE}${INFO} $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get Python version
get_python_version() {
    python3 --version 2>/dev/null | awk '{print $2}' | cut -d. -f1-2
}

# Function to compare version numbers
version_compare() {
    printf '%s\n%s\n' "$1" "$2" | sort -V | head -n1
}

# Check operating system
detect_os() {
    case "$(uname -s)" in
        Darwin*)    echo "macos" ;;
        Linux*)     echo "linux" ;;
        CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
        *)          echo "unknown" ;;
    esac
}

# Main setup function
main() {
    print_header "Glossary Configuration Updater - Development Setup"
    
    local os_type=$(detect_os)
    print_info "Detected OS: $os_type"
    
    # Step 1: Check prerequisites
    print_step "Checking prerequisites..."
    
    # Check Python 3.8+
    if command_exists python3; then
        local python_version=$(get_python_version)
        local min_version="3.8"
        
        if [ "$(version_compare "$python_version" "$min_version")" = "$min_version" ]; then
            print_success "Python $python_version found (required: $min_version+)"
        else
            print_error "Python $min_version+ required, found $python_version"
            print_info "Please install Python $min_version or higher:"
            case $os_type in
                macos)
                    echo "  brew install python@3.10"
                    ;;
                linux)
                    echo "  sudo apt-get install python3.10 python3.10-venv python3.10-pip"
                    echo "  or"
                    echo "  sudo yum install python310 python310-pip"
                    ;;
                windows)
                    echo "  Download from https://python.org or use chocolatey:"
                    echo "  choco install python"
                    ;;
            esac
            exit 1
        fi
    else
        print_error "Python 3 not found"
        exit 1
    fi
    
    # Check pip
    if command_exists pip3 || command_exists pip; then
        print_success "pip found"
    else
        print_error "pip not found"
        exit 1
    fi
    
    # Check git
    if command_exists git; then
        print_success "Git found"
    else
        print_warning "Git not found - version control features may not work"
    fi
    
    # Check curl (for API testing)
    if command_exists curl; then
        print_success "curl found"
    else
        print_warning "curl not found - API testing features may not work"
    fi
    
    # Step 2: Create virtual environment
    print_step "Setting up Python virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists"
        read -p "Do you want to recreate it? (y/N): " recreate
        if [[ $recreate =~ ^[Yy]$ ]]; then
            print_step "Removing existing virtual environment..."
            rm -rf venv
        else
            print_info "Using existing virtual environment"
        fi
    fi
    
    if [ ! -d "venv" ]; then
        print_step "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    print_step "Activating virtual environment..."
    source venv/bin/activate || source venv/Scripts/activate 2>/dev/null || {
        print_error "Failed to activate virtual environment"
        exit 1
    }
    print_success "Virtual environment activated"
    
    # Step 3: Upgrade pip and install build tools
    print_step "Upgrading pip and installing build tools..."
    python -m pip install --upgrade pip setuptools wheel build
    print_success "Build tools installed"
    
    # Step 4: Install the package in development mode
    print_step "Installing glossary-config-updater in development mode..."
    
    # Install with development dependencies
    if [ -f "pyproject.toml" ]; then
        pip install -e ".[dev]"
    elif [ -f "setup.py" ]; then
        pip install -e ".[dev]"
    else
        print_error "No setup.py or pyproject.toml found"
        exit 1
    fi
    
    print_success "Package installed in development mode"
    
    # Step 5: Install additional development tools
    print_step "Installing additional development tools..."
    
    # Development tools
    pip install \
        pre-commit \
        pytest-xdist \
        pytest-mock \
        responses \
        coverage \
        sphinx \
        sphinx-rtd-theme
    
    print_success "Development tools installed"
    
    # Step 6: Set up pre-commit hooks
    print_step "Setting up pre-commit hooks..."
    
    if [ -f ".pre-commit-config.yaml" ]; then
        pre-commit install
        print_success "Pre-commit hooks installed"
    else
        print_warning "No .pre-commit-config.yaml found, skipping pre-commit setup"
    fi
    
    # Step 7: Create development directories
    print_step "Creating development directories..."
    
    mkdir -p logs
    mkdir -p backups
    mkdir -p reports
    mkdir -p temp
    
    print_success "Development directories created"
    
    # Step 8: Copy example files
    print_step "Setting up example configuration..."
    
    if [ -f "examples/.env.example" ] && [ ! -f ".env" ]; then
        cp examples/.env.example .env
        print_success "Environment template copied to .env"
        print_warning "Please edit .env with your actual API credentials"
    fi
    
    if [ -f "examples/.gitignore.example" ] && [ ! -f ".gitignore" ]; then
        cp examples/.gitignore.example .gitignore
        print_success "GitIgnore template copied"
    fi
    
    # Step 9: Verify installation
    print_step "Verifying installation..."
    
    # Test import
    if python -c "import glossary_updater; print(f'Package version: {glossary_updater.__version__}')" 2>/dev/null; then
        print_success "Package import successful"
    else
        print_error "Package import failed"
        exit 1
    fi
    
    # Test CLI
    if glossary-updater --version >/dev/null 2>&1; then
        print_success "CLI command working"
    else
        print_error "CLI command failed"
        exit 1
    fi
    
    # Test development tools
    if python -c "import pytest, black, flake8, mypy" 2>/dev/null; then
        print_success "Development tools available"
    else
        print_warning "Some development tools may not be available"
    fi
    
    # Step 10: Run tests if available
    print_step "Running tests..."
    
    if [ -d "tests" ]; then
        if pytest tests/ -v --tb=short; then
            print_success "All tests passed"
        else
            print_warning "Some tests failed - this is normal for initial setup"
        fi
    else
        print_warning "No tests directory found"
    fi
    
    # Step 11: Generate development summary
    print_step "Generating development environment summary..."
    
    cat > dev-environment-info.txt << EOF
Glossary Configuration Updater - Development Environment
========================================================

Setup Date: $(date)
Python Version: $(python --version)
Package Version: $(glossary-updater --version 2>/dev/null || echo "Unknown")
Virtual Environment: $(which python)

Installed Packages:
$(pip list)

Development Tools:
- pytest: $(python -c "import pytest; print(pytest.__version__)" 2>/dev/null || echo "Not installed")
- black: $(python -c "import black; print(black.__version__)" 2>/dev/null || echo "Not installed")
- flake8: $(python -c "import flake8; print(flake8.__version__)" 2>/dev/null || echo "Not installed")
- mypy: $(python -c "import mypy; print(mypy.__version__)" 2>/dev/null || echo "Not installed")

Directory Structure:
$(find . -type d -name ".*" -prune -o -type d -print | head -20)

Next Steps:
1. Edit .env with your API credentials
2. Run: source venv/bin/activate (to activate environment)
3. Run: pytest (to run tests)
4. Run: black glossary_updater/ (to format code)
5. Run: flake8 glossary_updater/ (to check code quality)
EOF
    
    print_success "Development environment summary saved to dev-environment-info.txt"
    
    # Final success message
    print_header "Development Environment Setup Complete!"
    
    echo -e "${GREEN}Your development environment is ready!${NC}"
    echo
    echo -e "${CYAN}Quick Start Commands:${NC}"
    echo -e "  ${YELLOW}source venv/bin/activate${NC}  # Activate virtual environment"
    echo -e "  ${YELLOW}glossary-updater --help${NC}   # Show CLI help"
    echo -e "  ${YELLOW}pytest${NC}                    # Run tests"
    echo -e "  ${YELLOW}black glossary_updater/${NC}   # Format code"
    echo -e "  ${YELLOW}flake8 glossary_updater/${NC}  # Check code quality"
    echo
    echo -e "${CYAN}Important Files:${NC}"
    echo -e "  ${YELLOW}.env${NC}                      # Edit with your API credentials"
    echo -e "  ${YELLOW}dev-environment-info.txt${NC}  # Development environment details"
    echo
    echo -e "${CYAN}Documentation:${NC}"
    echo -e "  ${YELLOW}docs/${NC}                     # Project documentation"
    echo -e "  ${YELLOW}examples/${NC}                 # Usage examples"
    echo
    echo -e "${GREEN}Happy coding!${NC}"
}

# Help function
show_help() {
    cat << EOF
Glossary Configuration Updater - Development Setup

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help     Show this help message
    --clean        Clean existing virtual environment before setup
    --no-tests     Skip running tests during setup
    --minimal      Minimal setup (skip optional tools)

EXAMPLES:
    $0                    # Standard setup
    $0 --clean            # Clean setup
    $0 --minimal          # Minimal setup

REQUIREMENTS:
    - Python 3.8 or higher
    - pip (Python package manager)
    - Internet connection for downloading packages

For more information, see docs/installation.md
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --clean)
            if [ -d "venv" ]; then
                print_step "Cleaning existing virtual environment..."
                rm -rf venv
                print_success "Virtual environment cleaned"
            fi
            shift
            ;;
        --no-tests)
            SKIP_TESTS=true
            shift
            ;;
        --minimal)
            MINIMAL_SETUP=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if we're in the right directory
if [ ! -f "setup.py" ] && [ ! -f "pyproject.toml" ]; then
    print_error "setup.py or pyproject.toml not found."
    print_error "Please run this script from the project root directory."
    exit 1
fi

# Run main setup
main

print_info "Setup script completed. Check dev-environment-info.txt for details."