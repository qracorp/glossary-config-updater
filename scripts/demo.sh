#!/bin/bash

# Demo Script for Glossary Configuration Updater
# Demonstrates key features and capabilities

set -e

# Colors and symbols
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

CHECK="[OK]"
INFO="[INFO]"
STEP="[STEP]"
FEATURE="[FEATURE]"

# Configuration
DEMO_DIR="demo-temp"
DEMO_CONFIG_ID="demo-config-123"

# Print functions
print_header() {
    echo
    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================================${NC}"
    echo
}

print_section() {
    echo
    echo -e "${CYAN}${STEP} $1${NC}"
    echo -e "${CYAN}$(printf '─%.0s' $(seq 1 ${#1}))${NC}"
}

print_success() {
    echo -e "${GREEN}${CHECK} $1${NC}"
}

print_info() {
    echo -e "${BLUE}${INFO} $1${NC}"
}

print_feature() {
    echo -e "${PURPLE}${FEATURE} $1${NC}"
}

print_code() {
    echo -e "${YELLOW}$ $1${NC}"
}

# Wait for user input
wait_for_user() {
    if [ "${AUTO_DEMO:-false}" != "true" ]; then
        echo
        read -p "Press Enter to continue..."
    else
        sleep 2
    fi
}

# Execute and show command
demo_command() {
    local cmd="$1"
    local description="$2"
    
    if [ -n "$description" ]; then
        print_info "$description"
    fi
    
    print_code "$cmd"
    echo
    
    if eval "$cmd"; then
        echo
        print_success "Command completed successfully"
    else
        echo
        echo -e "${RED}[ERROR] Command failed (this may be expected in demo mode)${NC}"
    fi
}

# Create demo files
create_demo_files() {
    print_section "Creating Demo Files"
    
    mkdir -p "$DEMO_DIR"
    cd "$DEMO_DIR"
    
    # Create CSV demo file
    cat > demo-terms.csv << 'EOF'
phrase,definition,category,priority
API,"Application Programming Interface - a set of protocols for building software",Technical,High
REST,"Representational State Transfer - architectural style for distributed systems",Technical,High
JSON,"JavaScript Object Notation - lightweight data interchange format",Technical,Medium
Microservice,"Small independent service that performs a specific business function",Architecture,High
DevOps,"Set of practices combining software development and IT operations",Process,Medium
Docker,"Platform for developing and running applications using containerization",Tools,Medium
Kubernetes,"Container orchestration platform for automating deployment",Tools,High
CI/CD,"Continuous Integration/Continuous Deployment - automated software delivery",Process,High
Agile,"Iterative development methodology emphasizing collaboration",Methodology,Medium
Scrum,"Framework for managing product development with defined roles and events",Methodology,Medium
EOF

    # Create JSON demo file
    cat > advanced-terms.json << 'EOF'
{
  "glossary": [
    {
      "phrase": "Machine Learning",
      "definition": "Type of artificial intelligence that enables computers to learn from data",
      "category": "AI/ML",
      "aliases": ["ML"],
      "related_terms": ["Artificial Intelligence", "Deep Learning"],
      "examples": ["Image recognition", "Natural language processing"]
    },
    {
      "phrase": "Cloud Computing",
      "definition": "Delivery of computing services over the internet",
      "category": "Infrastructure",
      "service_models": ["IaaS", "PaaS", "SaaS"],
      "benefits": ["Scalability", "Cost efficiency", "Flexibility"]
    },
    {
      "phrase": "Blockchain",
      "definition": "Distributed ledger technology for secure transactions",
      "category": "Technology",
      "characteristics": ["Decentralized", "Immutable", "Transparent"],
      "use_cases": ["Cryptocurrency", "Supply chain", "Smart contracts"]
    }
  ]
}
EOF

    # Create YAML demo file
    cat > business-terms.yaml << 'EOF'
glossary:
  - phrase: "ROI"
    definition: "Return on Investment - measure of investment efficiency"
    category: "Finance"
    formula: "(Gain - Cost) / Cost"
    
  - phrase: "KPI"
    definition: "Key Performance Indicator - measurable value showing progress"
    category: "Business"
    examples:
      - "Revenue growth"
      - "Customer satisfaction"
      - "Employee retention"
      
  - phrase: "MVP"
    definition: "Minimum Viable Product - product with core features for early feedback"
    category: "Product"
    characteristics:
      - "Minimal features"
      - "Functional"
      - "Testable"
EOF

    print_success "Demo files created in $DEMO_DIR/"
    echo
    echo "Created files:"
    echo "  - demo-terms.csv (10 technical terms)"
    echo "  - advanced-terms.json (3 advanced concepts)"
    echo "  - business-terms.yaml (3 business terms)"
    
    cd ..
}

# Cleanup demo files
cleanup_demo() {
    if [ -d "$DEMO_DIR" ]; then
        print_section "Cleaning Up Demo Files"
        rm -rf "$DEMO_DIR"
        print_success "Demo files cleaned up"
    fi
}

# Demo introduction
demo_intro() {
    print_header "Welcome to Glossary Configuration Updater Demo!"
    
    echo -e "${CYAN}This demo will showcase the key features of the Glossary Configuration Updater:${NC}"
    echo
    print_feature "Multi-format file support (CSV, JSON, YAML)"
    print_feature "Intelligent file validation and processing"
    print_feature "Flexible merge strategies (merge vs overwrite)"
    print_feature "Dry-run mode for safe testing"
    print_feature "Professional CLI with comprehensive options"
    print_feature "Robust error handling and logging"
    echo
    print_info "The demo uses mock data and will not make real API calls"
    print_info "Set DEMO_API_* environment variables to test with real API"
    
    wait_for_user
}

# Demo file validation
demo_validation() {
    print_section "File Validation Demo"
    
    print_info "The tool automatically validates files before processing"
    echo
    
    # Validate the demo files
    demo_command "glossary-updater --help | head -10" "First, let's see the help options"
    
    wait_for_user
    
    demo_command "find $DEMO_DIR -name '*.csv' -o -name '*.json' -o -name '*.yaml'" "Discovering glossary files"
    
    wait_for_user
    
    print_info "Let's validate our demo files using the validation script"
    demo_command "./scripts/validate-files.sh $DEMO_DIR --verbose" "Running file validation"
    
    wait_for_user
}

# Demo dry run
demo_dry_run() {
    print_section "Dry Run Demo"
    
    print_info "Dry run mode lets you test operations safely without making changes"
    echo
    
    # Set up demo environment variables
    export API_DOMAIN="${DEMO_API_DOMAIN:-demo.example.com}"
    export API_USERNAME="${DEMO_API_USERNAME:-demo-user}"
    export API_PASSWORD="${DEMO_API_PASSWORD:-demo-pass}"
    
    print_info "Using demo credentials (API_DOMAIN: $API_DOMAIN)"
    echo
    
    # Single file dry run
    demo_command "glossary-updater --file $DEMO_DIR/demo-terms.csv --config $DEMO_CONFIG_ID --dry-run --verbose" \
                 "Testing single CSV file with dry run"
    
    wait_for_user
    
    # Multiple files dry run
    demo_command "glossary-updater --directory $DEMO_DIR --config $DEMO_CONFIG_ID --dry-run --merge-strategy merge" \
                 "Testing entire directory with merge strategy"
    
    wait_for_user
    
    # Different merge strategy
    demo_command "glossary-updater --directory $DEMO_DIR --config $DEMO_CONFIG_ID --dry-run --merge-strategy overwrite" \
                 "Testing with overwrite strategy"
    
    wait_for_user
}

# Demo Python API
demo_python_api() {
    print_section "Python API Demo"
    
    print_info "The tool can also be used programmatically in Python"
    echo
    
    # Create Python demo script
    cat > "$DEMO_DIR/python_demo.py" << 'EOF'
#!/usr/bin/env python3
"""
Python API Demo for Glossary Configuration Updater
"""

import asyncio
from glossary_updater import GlossaryUpdater, Config
from pathlib import Path

async def main():
    print("Python API Demo")
    print("=" * 50)
    
    # Create configuration
    config = Config.from_env(
        config_id="demo-config-123",
        file_paths=["demo-terms.csv"],
        merge_strategy="merge",
        dry_run=True
    )
    
    print(f"Configuration created:")
    print(f"  - Config ID: {config.config_id}")
    print(f"  - Files: {config.file_paths}")
    print(f"  - Strategy: {config.merge_strategy}")
    print(f"  - Dry run: {config.dry_run}")
    print()
    
    # Create updater (this will fail in demo mode, but shows the API)
    try:
        updater = GlossaryUpdater(
            domain=config.domain or "demo.example.com",
            username=config.username or "demo-user",
            password=config.password or "demo-pass"
        )
        
        print("[OK] GlossaryUpdater instance created")
        print(f"  - Domain: {updater.domain}")
        print()
        
        # This would normally work with real API credentials
        print("[INFO] This would perform the update with real API credentials...")
        print("       result = await updater.update_from_files(...)")
        
    except Exception as e:
        print(f"[INFO] Expected demo error: {type(e).__name__}")
        print("       (This is normal in demo mode without real API credentials)")

if __name__ == "__main__":
    asyncio.run(main())
EOF
    
    print_info "Created Python demo script"
    demo_command "cat $DEMO_DIR/python_demo.py | head -20" "Showing Python API usage"
    
    wait_for_user
    
    demo_command "cd $DEMO_DIR && python3 python_demo.py" "Running Python API demo"
    
    wait_for_user
}

# Demo advanced features
demo_advanced_features() {
    print_section "Advanced Features Demo"
    
    print_info "Exploring advanced features and options"
    echo
    
    # Show version and system info
    demo_command "glossary-updater --version" "Checking tool version"
    
    wait_for_user
    
    # Show file processing capabilities
    print_info "File processing capabilities:"
    echo "  - CSV: Automatic column detection (phrase, term, word, name)"
    echo "  - JSON: Multiple structure patterns supported"
    echo "  - YAML: Human-readable format with nested data"
    echo
    
    # Demonstrate file discovery
    demo_command "python3 -c '
from glossary_updater.utils import discover_glossary_files
files = discover_glossary_files([\"$DEMO_DIR\"])
for file_type, paths in files.items():
    print(f\"{file_type.upper()}: {len(paths)} file(s)\")
    for path in paths:
        print(f\"  - {path}\")
'" "Demonstrating file discovery API"
    
    wait_for_user
    
    # Show configuration options
    print_info "Available merge strategies:"
    echo "  - merge: Combines new terms with existing (default)"
    echo "  - overwrite: Replaces all existing terms"
    echo
    echo "Available timeout and retry options:"
    echo "  - --timeout: Request timeout in seconds"
    echo "  - --max-retries: Maximum retry attempts"
    
    wait_for_user
}

# Demo CI/CD integration
demo_cicd_integration() {
    print_section "CI/CD Integration Demo"
    
    print_info "The tool is designed for CI/CD integration"
    echo
    
    print_info "Example workflow commands:"
    echo
    
    print_code "# Validate files in CI pipeline"
    echo "glossary-updater --directory ./docs/glossary --dry-run --verbose"
    echo
    
    print_code "# Update staging environment"
    echo "glossary-updater --directory ./glossary --config \$STAGING_CONFIG_ID --merge-strategy merge"
    echo
    
    print_code "# Update production with overwrite"
    echo "glossary-updater --directory ./glossary --config \$PROD_CONFIG_ID --merge-strategy overwrite"
    echo
    
    print_info "Supported CI/CD platforms:"
    echo "  - GitHub Actions"
    echo "  - GitLab CI/CD"
    echo "  - Jenkins"
    echo "  - Azure DevOps"
    echo
    
    print_info "Example workflow files are available in examples/workflows/"
    
    wait_for_user
}

# Demo error handling
demo_error_handling() {
    print_section "Error Handling Demo"
    
    print_info "The tool provides comprehensive error handling"
    echo
    
    # Create an invalid file to demonstrate error handling
    echo "invalid,csv,content" > "$DEMO_DIR/invalid.csv"
    echo "missing header row" >> "$DEMO_DIR/invalid.csv"
    
    print_info "Testing with invalid CSV file:"
    demo_command "./scripts/validate-files.sh $DEMO_DIR/invalid.csv" "Validating invalid file"
    
    wait_for_user
    
    # Create invalid JSON
    echo '{"invalid": "json", "missing": }' > "$DEMO_DIR/invalid.json"
    
    print_info "Testing with invalid JSON file:"
    demo_command "./scripts/validate-files.sh $DEMO_DIR/invalid.json" "Validating invalid JSON"
    
    wait_for_user
    
    print_info "Error types handled:"
    echo "  - Authentication failures"
    echo "  - Network connectivity issues"
    echo "  - File format errors"
    echo "  - Configuration access problems"
    echo "  - API timeout and retry scenarios"
    
    # Clean up invalid files
    rm -f "$DEMO_DIR/invalid.csv" "$DEMO_DIR/invalid.json"
    
    wait_for_user
}

# Demo summary
demo_summary() {
    print_header "Demo Summary"
    
    echo -e "${GREEN}Congratulations! You've seen the key features of the Glossary Configuration Updater:${NC}"
    echo
    print_feature "Multi-format file support (CSV, JSON, YAML)"
    print_feature "Intelligent validation and error handling"
    print_feature "Flexible merge strategies"
    print_feature "Safe dry-run testing"
    print_feature "Professional CLI interface"
    print_feature "Python API for programmatic use"
    print_feature "CI/CD integration support"
    print_feature "Comprehensive documentation"
    echo
    
    print_info "Next steps:"
    echo "  - Read the documentation in docs/"
    echo "  - Set up your environment with .env file"
    echo "  - Test with your own API credentials"
    echo "  - Integrate into your CI/CD pipeline"
    echo "  - Check examples/ for templates and workflows"
    echo
    
    print_info "Resources:"
    echo "  - Documentation: docs/"
    echo "  - Examples: examples/"
    echo "  - Scripts: scripts/"
    echo "  - Tests: tests/"
    echo
    
    echo -e "${CYAN}Thank you for trying the Glossary Configuration Updater!${NC}"
}

# Help function
show_help() {
    cat << EOF
Glossary Configuration Updater Demo

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --auto          Run demo automatically without waiting for user input
    --quick         Quick demo (skip some sections)
    --no-cleanup    Don't clean up demo files
    -h, --help      Show this help

SECTIONS:
    1. Introduction and overview
    2. File validation demonstration
    3. Dry run testing
    4. Python API usage
    5. Advanced features
    6. CI/CD integration
    7. Error handling
    8. Summary and next steps

EXAMPLES:
    $0              # Interactive demo
    $0 --auto       # Automated demo
    $0 --quick      # Quick demo
EOF
}

# Parse command line arguments
AUTO_DEMO=false
QUICK_DEMO=false
NO_CLEANUP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --auto)
            AUTO_DEMO=true
            shift
            ;;
        --quick)
            QUICK_DEMO=true
            shift
            ;;
        --no-cleanup)
            NO_CLEANUP=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Set up cleanup trap
cleanup_on_exit() {
    if [ "$NO_CLEANUP" != "true" ]; then
        cleanup_demo
    fi
}
trap cleanup_on_exit EXIT

# Main demo execution
main() {
    # Check if we're in the right directory
    if [ ! -f "setup.py" ] && [ ! -f "pyproject.toml" ]; then
        echo "[ERROR] Please run this demo from the project root directory"
        exit 1
    fi
    
    # Check dependencies
    if ! command -v glossary-updater >/dev/null 2>&1; then
        echo "[ERROR] glossary-updater not found. Please install the package first:"
        echo "        pip install -e ."
        exit 1
    fi
    
    # Run demo sections
    demo_intro
    
    create_demo_files
    wait_for_user
    
    demo_validation
    
    demo_dry_run
    
    if [ "$QUICK_DEMO" != "true" ]; then
        demo_python_api
        demo_advanced_features
        demo_cicd_integration
        demo_error_handling
    fi
    
    demo_summary
}

# Run the demo
main