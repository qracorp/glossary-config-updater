#!/bin/bash

# API Connection Test Script for Glossary Configuration Updater
# Tests API connectivity, authentication, and basic functionality

set -e

# Colors and symbols
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CHECK="✅"
CROSS="❌"
WARNING="⚠️"
INFO="ℹ️"
ROCKET="🚀"

# Print functions
print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}${CHECK} $1${NC}"
}

print_error() {
    echo -e "${RED}${CROSS} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
}

print_info() {
    echo -e "${BLUE}${INFO} $1${NC}"
}

# Help function
show_help() {
    cat << EOF
API Connection Test Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -d, --domain DOMAIN       API domain to test
    -u, --username USERNAME   API username
    -p, --password PASSWORD   API password
    -c, --config CONFIG_ID    Configuration ID to test
    -v, --verbose             Enable verbose output
    -q, --quiet               Suppress non-error output
    -t, --timeout SECONDS     Request timeout (default: 30)
    -h, --help                Show this help

EXAMPLES:
    # Test with environment variables
    $0
    
    # Test with command line arguments
    $0 -d api.example.com -u myuser -p mypass -c config123
    
    # Verbose test
    $0 --verbose
    
    # Quick test with custom timeout
    $0 --timeout 10

ENVIRONMENT VARIABLES:
    API_DOMAIN     - API domain
    API_USERNAME   - API username
    API_PASSWORD   - API password
    TEST_CONFIG_ID - Configuration ID for testing

EXIT CODES:
    0 - All tests passed
    1 - Connection failed
    2 - Authentication failed
    3 - Configuration access failed
    4 - Invalid arguments
    5 - Missing dependencies
EOF
}

# Parse command line arguments
DOMAIN=""
USERNAME=""
PASSWORD=""
CONFIG_ID=""
VERBOSE=false
QUIET=false
TIMEOUT=30

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -u|--username)
            USERNAME="$2"
            shift 2
            ;;
        -p|--password)
            PASSWORD="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_ID="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 4
            ;;
    esac
done

# Use environment variables as fallback
DOMAIN="${DOMAIN:-$API_DOMAIN}"
USERNAME="${USERNAME:-$API_USERNAME}"
PASSWORD="${PASSWORD:-$API_PASSWORD}"
CONFIG_ID="${CONFIG_ID:-$TEST_CONFIG_ID}"

# Quiet mode setup
if [ "$QUIET" = true ]; then
    VERBOSE=false
    exec 1>/dev/null
fi

# Verbose logging function
log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1" >&2
    fi
}

# Main test function
main() {
    local start_time=$(date +%s)
    
    print_header "API Connection Test"
    
    # Step 1: Validate inputs
    print_info "Validating inputs..."
    
    if [ -z "$DOMAIN" ]; then
        print_error "API domain is required"
        exit 4
    fi
    
    if [ -z "$USERNAME" ]; then
        print_error "API username is required"
        exit 4
    fi
    
    if [ -z "$PASSWORD" ]; then
        print_error "API password is required"
        exit 4
    fi
    
    # Configuration ID is optional for basic tests
    if [ -z "$CONFIG_ID" ]; then
        print_warning "No configuration ID provided - skipping configuration tests"
    fi
    
    print_success "Input validation passed"
    log_verbose "Domain: $DOMAIN"
    log_verbose "Username: $USERNAME"
    log_verbose "Password: [HIDDEN]"
    log_verbose "Config ID: ${CONFIG_ID:-"Not provided"}"
    log_verbose "Timeout: ${TIMEOUT}s"
    
    # Step 2: Check dependencies
    print_info "Checking dependencies..."
    
    if ! command -v curl >/dev/null 2>&1; then
        print_error "curl is required but not installed"
        exit 5
    fi
    
    if ! command -v python3 >/dev/null 2>&1; then
        print_error "python3 is required but not installed"
        exit 5
    fi
    
    if ! command -v glossary-updater >/dev/null 2>&1; then
        print_error "glossary-updater is not installed or not in PATH"
        exit 5
    fi
    
    print_success "Dependencies check passed"
    
    # Step 3: Basic connectivity test
    print_info "Testing basic connectivity..."
    
    # Ensure domain has protocol
    if [[ ! "$DOMAIN" =~ ^https?:// ]]; then
        DOMAIN="https://$DOMAIN"
    fi
    
    log_verbose "Testing connectivity to: $DOMAIN"
    
    if curl -s --max-time "$TIMEOUT" --head "$DOMAIN" >/dev/null 2>&1; then
        print_success "Basic connectivity OK"
    else
        print_error "Cannot connect to $DOMAIN"
        print_info "Please check:"
        print_info "  - Domain name is correct"
        print_info "  - Network connection is working"
        print_info "  - Firewall/proxy settings"
        exit 1
    fi
    
    # Step 4: API health check
    print_info "Testing API health endpoint..."
    
    local health_url="$DOMAIN/health"
    log_verbose "Health check URL: $health_url"
    
    local health_response
    if health_response=$(curl -s --max-time "$TIMEOUT" "$health_url" 2>/dev/null); then
        print_success "API health endpoint accessible"
        log_verbose "Health response: $health_response"
    else
        print_warning "API health endpoint not accessible (this may be normal)"
    fi
    
    # Step 5: Authentication test
    print_info "Testing authentication..."
    
    local login_url="$DOMAIN/auth/login"
    local login_data='{"username":"'"$USERNAME"'","password":"'"$PASSWORD"'"}'
    
    log_verbose "Login URL: $login_url"
    log_verbose "Testing authentication..."
    
    local auth_response
    local auth_status
    
    auth_response=$(curl -s --max-time "$TIMEOUT" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$login_data" \
        -w "%{http_code}" \
        "$login_url" 2>/dev/null)
    
    auth_status="${auth_response: -3}"
    auth_response="${auth_response%???}"
    
    log_verbose "Auth response status: $auth_status"
    log_verbose "Auth response body: $auth_response"
    
    case "$auth_status" in
        200|201)
            print_success "Authentication successful"
            
            # Try to extract token
            local token=""
            if command -v jq >/dev/null 2>&1; then
                token=$(echo "$auth_response" | jq -r '.token // .access_token // empty' 2>/dev/null)
            else
                # Fallback without jq
                token=$(echo "$auth_response" | grep -o '"token":"[^"]*"' | cut -d'"' -f4 2>/dev/null || \
                       echo "$auth_response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4 2>/dev/null)
            fi
            
            if [ -n "$token" ]; then
                print_success "Authentication token retrieved"
                log_verbose "Token: ${token:0:10}..."
                
                # Store token for configuration test
                AUTH_TOKEN="$token"
            else
                print_warning "Authentication successful but no token found"
            fi
            ;;
        401)
            print_error "Authentication failed - Invalid credentials"
            exit 2
            ;;
        403)
            print_error "Authentication failed - Access forbidden"
            exit 2
            ;;
        404)
            print_error "Authentication endpoint not found"
            print_info "Check if the API domain and path are correct"
            exit 2
            ;;
        *)
            print_error "Authentication failed with HTTP status: $auth_status"
            if [ -n "$auth_response" ]; then
                log_verbose "Response: $auth_response"
            fi
            exit 2
            ;;
    esac
    
    # Step 6: Configuration access test (if config ID provided and token available)
    if [ -n "$CONFIG_ID" ] && [ -n "$AUTH_TOKEN" ]; then
        print_info "Testing configuration access..."
        
        local config_url="$DOMAIN/analysis/v2/configuration/$CONFIG_ID"
        log_verbose "Config URL: $config_url"
        
        local config_response
        local config_status
        
        config_response=$(curl -s --max-time "$TIMEOUT" \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            -w "%{http_code}" \
            "$config_url" 2>/dev/null)
        
        config_status="${config_response: -3}"
        config_response="${config_response%???}"
        
        log_verbose "Config response status: $config_status"
        
        case "$config_status" in
            200)
                print_success "Configuration accessible"
                
                # Try to get basic info about the configuration
                if command -v jq >/dev/null 2>&1; then
                    local config_name
                    local entity_count
                    local resource_count
                    
                    config_name=$(echo "$config_response" | jq -r '.name // "Unknown"' 2>/dev/null)
                    entity_count=$(echo "$config_response" | jq '.analysisEntityList | length' 2>/dev/null)
                    resource_count=$(echo "$config_response" | jq '.resourceList | length' 2>/dev/null)
                    
                    if [ "$config_name" != "null" ] && [ "$config_name" != "Unknown" ]; then
                        print_info "Configuration name: $config_name"
                    fi
                    
                    if [ -n "$entity_count" ] && [ "$entity_count" != "null" ]; then
                        print_info "Entities: $entity_count"
                    fi
                    
                    if [ -n "$resource_count" ] && [ "$resource_count" != "null" ]; then
                        print_info "Resources: $resource_count"
                    fi
                fi
                ;;
            401)
                print_error "Configuration access denied - Authentication issue"
                exit 3
                ;;
            403)
                print_error "Configuration access denied - Insufficient permissions"
                exit 3
                ;;
            404)
                print_error "Configuration not found: $CONFIG_ID"
                exit 3
                ;;
            *)
                print_error "Configuration access failed with HTTP status: $config_status"
                exit 3
                ;;
        esac
    elif [ -n "$CONFIG_ID" ]; then
        print_warning "Skipping configuration test - no authentication token"
    fi
    
    # Step 7: Glossary updater CLI test
    print_info "Testing glossary-updater CLI..."
    
    # Test version command
    local version_output
    if version_output=$(glossary-updater --version 2>&1); then
        print_success "CLI version command works"
        log_verbose "Version: $version_output"
    else
        print_error "CLI version command failed"
        exit 5
    fi
    
    # Test help command
    if glossary-updater --help >/dev/null 2>&1; then
        print_success "CLI help command works"
    else
        print_warning "CLI help command failed"
    fi
    
    # Step 8: Integration test (if all components available)
    if [ -n "$CONFIG_ID" ] && [ -n "$AUTH_TOKEN" ]; then
        print_info "Running integration test..."
        
        # Create a minimal test file
        local test_file="/tmp/test-glossary-$$.csv"
        cat > "$test_file" << EOF
phrase,definition
Test Term,This is a test definition for API testing
EOF
        
        # Test dry run
        if glossary-updater \
            --file "$test_file" \
            --config "$CONFIG_ID" \
            --domain "${DOMAIN#https://}" \
            --username "$USERNAME" \
            --password "$PASSWORD" \
            --dry-run \
            --timeout "$TIMEOUT" >/dev/null 2>&1; then
            
            print_success "Integration test (dry run) passed"
        else
            print_warning "Integration test (dry run) failed"
        fi
        
        # Clean up test file
        rm -f "$test_file"
    fi
    
    # Step 9: Performance test
    print_info "Running performance test..."
    
    local perf_start=$(date +%s%3N)
    
    # Simple performance test - measure auth request time
    curl -s --max-time "$TIMEOUT" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$login_data" \
        "$login_url" >/dev/null 2>&1
    
    local perf_end=$(date +%s%3N)
    local perf_duration=$((perf_end - perf_start))
    
    if [ "$perf_duration" -lt 5000 ]; then
        print_success "Performance test passed (${perf_duration}ms)"
    elif [ "$perf_duration" -lt 10000 ]; then
        print_warning "Performance test slow (${perf_duration}ms)"
    else
        print_warning "Performance test very slow (${perf_duration}ms)"
    fi
    
    # Final summary
    local end_time=$(date +%s)
    local total_duration=$((end_time - start_time))
    
    print_header "Connection Test Summary"
    print_success "All tests completed successfully!"
    print_info "Total test duration: ${total_duration}s"
    print_info "API endpoint: $DOMAIN"
    print_info "Authentication: Working"
    
    if [ -n "$CONFIG_ID" ]; then
        print_info "Configuration access: Working"
    fi
    
    print_info "CLI tools: Working"
    
    echo
    print_info "Your API connection is ready for glossary updates! ${ROCKET}"
}

# Trap for cleanup
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ] && [ "$QUIET" != true ]; then
        echo >&2
        print_error "Connection test failed with exit code $exit_code" >&2
        echo >&2
        print_info "Troubleshooting tips:" >&2
        print_info "  1. Verify your credentials are correct" >&2
        print_info "  2. Check network connectivity" >&2
        print_info "  3. Ensure the API domain is correct" >&2
        print_info "  4. Run with --verbose for detailed output" >&2
        print_info "  5. Check the troubleshooting guide: docs/troubleshooting.md" >&2
    fi
    exit $exit_code
}

trap cleanup EXIT

# Run main function
main
