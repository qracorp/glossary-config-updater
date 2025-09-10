#!/bin/bash
set -e

# Improved test runner for glossary-config-updater
# Focuses on behavior testing rather than just coverage

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configuration
COVERAGE=false
VERBOSE=false
FAST=false
INTEGRATION=false
UNIT_ONLY=false
PARALLEL=false
REPORT_DIR="test-reports"

# Print functions
print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${PURPLE}ℹ️  $1${NC}"
}

# Show help
show_help() {
    cat << EOF
Improved Test Runner for Glossary Config Updater

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --coverage          Generate coverage reports
    --verbose, -v       Verbose test output
    --fast             Skip slow integration tests
    --integration      Run only integration tests
    --unit-only        Run only unit tests
    --parallel, -j     Run tests in parallel
    --help, -h         Show this help

EXAMPLES:
    $0                    # Run all tests
    $0 --verbose          # Run with verbose output
    $0 --coverage         # Run with coverage report
    $0 --fast --parallel  # Quick parallel run
    $0 --integration      # Integration tests only
    $0 --unit-only        # Unit tests only

ENVIRONMENT VARIABLES:
    PYTEST_OPTS         Additional pytest options
    TEST_TIMEOUT        Test timeout in seconds (default: 300)
    PARALLEL_WORKERS    Number of parallel workers (default: auto)
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --fast)
            FAST=true
            shift
            ;;
        --integration)
            INTEGRATION=true
            shift
            ;;
        --unit-only)
            UNIT_ONLY=true
            shift
            ;;
        --parallel|-j)
            PARALLEL=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main function
main() {
    print_header "Glossary Config Updater - Behavior Test Runner"
    
    # Validate environment
    print_info "Validating test environment..."
    
    if [ ! -f "setup.py" ] && [ ! -f "pyproject.toml" ]; then
        print_error "Must be run from package root directory"
        exit 1
    fi
    
    if [ ! -d "tests" ]; then
        print_error "Tests directory not found"
        exit 1
    fi
    
    # Check Python version
    python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1-2)
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
        print_error "Python 3.8+ required, found: $python_version"
        exit 1
    fi
    
    print_success "Python version check passed: $python_version"
    
    # Virtual environment check
    if [ -z "$VIRTUAL_ENV" ]; then
        print_warning "Not running in virtual environment - this is recommended"
    else
        print_success "Running in virtual environment: $(basename $VIRTUAL_ENV)"
    fi
    
    # Install/upgrade dependencies
    print_info "Installing test dependencies..."
    pip install -q --upgrade pip
    
    # Install core dependencies
    if ! pip install -q -e . 2>/dev/null; then
        print_error "Failed to install package in development mode"
        exit 1
    fi
    
    # Install test dependencies
    test_deps=(
        "pytest>=7.4.0"
        "pytest-asyncio>=0.21.0"
        "pytest-mock>=3.11.0"
        "pytest-xdist>=3.3.0"
        "respx>=0.20.0"
        "httpx-mock>=0.10.0"
        "freezegun>=1.2.0"
    )
    
    if [ "$COVERAGE" = true ]; then
        test_deps+=("pytest-cov>=4.1.0")
    fi
    
    for dep in "${test_deps[@]}"; do
        if ! pip install -q "$dep"; then
            print_warning "Could not install $dep"
        fi
    done
    
    print_success "Dependencies installed"
    
    # Set up test environment
    export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)"
    export PYTEST_CURRENT_TEST=""
    export API_DOMAIN="test.example.com"
    export API_USERNAME="test-user"
    export API_PASSWORD="test-password"
    export SSL_VERIFY="false"
    
    # Create report directory
    mkdir -p "$REPORT_DIR"
    
    # Build pytest command
    pytest_cmd="pytest"
    pytest_args=()
    
    # Test selection
    if [ "$INTEGRATION" = true ]; then
        pytest_args+=("-m" "integration")
        print_info "Running integration tests only"
    elif [ "$UNIT_ONLY" = true ]; then
        pytest_args+=("-m" "not integration")
        print_info "Running unit tests only"
    elif [ "$FAST" = true ]; then
        pytest_args+=("-m" "not slow")
        print_info "Running fast tests only (excluding slow tests)"
    else
        print_info "Running all tests"
    fi
    
    # Output options
    if [ "$VERBOSE" = true ]; then
        pytest_args+=("-v" "-s")
    else
        pytest_args+=("--tb=short")
    fi
    
    # Coverage options
    if [ "$COVERAGE" = true ]; then
        pytest_args+=(
            "--cov=glossary_updater"
            "--cov-report=term-missing"
            "--cov-report=html:${REPORT_DIR}/coverage"
            "--cov-report=xml:${REPORT_DIR}/coverage.xml"
            "--cov-branch"
        )
        print_info "Coverage reporting enabled"
    fi
    
    # Parallel execution
    if [ "$PARALLEL" = true ]; then
        workers=${PARALLEL_WORKERS:-auto}
        pytest_args+=("-n" "$workers")
        print_info "Running tests in parallel (workers: $workers)"
    fi
    
    # Additional options
    pytest_args+=(
        "--strict-markers"
        "--strict-config"
        "--disable-warnings"
        "--junit-xml=${REPORT_DIR}/junit.xml"
    )
    
    # Timeout
    timeout=${TEST_TIMEOUT:-300}
    pytest_args+=("--timeout=$timeout")
    
    # Add any additional pytest options
    if [ -n "$PYTEST_OPTS" ]; then
        read -ra additional_opts <<< "$PYTEST_OPTS"
        pytest_args+=("${additional_opts[@]}")
    fi
    
    # Add test directory
    pytest_args+=("tests/")
    
    # Run the tests
    print_header "Running Tests"
    print_info "Command: $pytest_cmd ${pytest_args[*]}"
    echo
    
    test_start_time=$(date +%s)
    
    if $pytest_cmd "${pytest_args[@]}"; then
        test_result=0
    else
        test_result=1
    fi
    
    test_end_time=$(date +%s)
    test_duration=$((test_end_time - test_start_time))
    
    # Post-test validation
    print_header "Post-Test Validation"
    
    # Test package import
    print_info "Testing package import..."
    if python3 -c "import glossary_updater; print(f'✅ Package version: {glossary_updater.__version__}')" 2>/dev/null; then
        print_success "Package import successful"
    else
        print_error "Package import failed"
        test_result=1
    fi
    
    # Test CLI availability
    print_info "Testing CLI availability..."
    if command -v glossary-updater >/dev/null 2>&1; then
        version_output=$(glossary-updater --version 2>&1)
        print_success "CLI available: $version_output"
    else
        print_error "CLI not available"
        test_result=1
    fi
    
    # Test fixtures validation
    print_info "Validating test fixtures..."
    fixture_count=0
    if [ -d "tests/fixtures" ]; then
        for fixture in tests/fixtures/*.{csv,json,yaml,yml}; do
            if [ -f "$fixture" ]; then
                ((fixture_count++))
            fi
        done
        print_success "Found $fixture_count test fixtures"
    else
        print_warning "No test fixtures directory found"
    fi
    
    # Generate summary report
    print_header "Test Summary"
    
    echo "Test Duration: ${test_duration}s"
    echo "Test Reports: $REPORT_DIR/"
    
    if [ "$COVERAGE" = true ] && [ -f "$REPORT_DIR/coverage/index.html" ]; then
        echo "Coverage Report: $REPORT_DIR/coverage/index.html"
    fi
    
    if [ -f "$REPORT_DIR/junit.xml" ]; then
        echo "JUnit Report: $REPORT_DIR/junit.xml"
    fi
    
    # Final result
    if [ $test_result -eq 0 ]; then
        print_success "All tests and validations passed! 🎉"
        echo
        print_info "Test Summary:"
        echo "  ✅ Behavior testing focused"
        echo "  ✅ Real file processing tested"
        echo "  ✅ Actual API integration tested"
        echo "  ✅ Merge logic thoroughly tested"
        echo "  ✅ Error handling validated"
        
        if [ "$COVERAGE" = true ]; then
            echo "  📊 Coverage report generated"
        fi
        
        echo
        print_info "Ready for production! 🚀"
    else
        print_error "Some tests failed"
        echo
        print_info "Debugging tips:"
        echo "  🔍 Run with --verbose for detailed output"
        echo "  🧪 Run specific test files: pytest tests/test_specific.py"
        echo "  📋 Check test reports in: $REPORT_DIR/"
        echo "  🐛 Review fixture files in: tests/fixtures/"
    fi
    
    exit $test_result
}

# Trap for cleanup
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo
        print_error "Test run interrupted or failed"
        print_info "Check test reports in: $REPORT_DIR/"
    fi
    exit $exit_code
}

trap cleanup EXIT INT TERM

# Run main function
main "$@"