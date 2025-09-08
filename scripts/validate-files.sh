#!/bin/bash

# File Validation Script for Glossary Configuration Updater
# Validates CSV, JSON, and YAML files before processing

set -e

# Colors and symbols
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

CHECK="✅"
CROSS="❌"
WARNING="⚠️"
INFO="ℹ️"
SEARCH="🔍"

# Configuration
DEFAULT_DIRECTORY="docs/glossary"
REPORT_FILE=""
VERBOSE=false
STRICT=false
FIX_ISSUES=false

# Counters
TOTAL_FILES=0
VALID_FILES=0
INVALID_FILES=0
WARNINGS=0

# Print functions
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

print_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${PURPLE}[DEBUG] $1${NC}"
    fi
}

print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
}

# Help function
show_help() {
    cat << EOF
Glossary File Validation Script

USAGE:
    $0 [OPTIONS] [DIRECTORY|FILE...]

DESCRIPTION:
    Validates CSV, JSON, and YAML glossary files for syntax errors,
    required columns, and common issues.

OPTIONS:
    -d, --directory DIR       Directory to scan for glossary files
    -f, --file FILE          Specific file to validate
    -r, --report FILE        Generate detailed report file
    -v, --verbose            Enable verbose output
    -s, --strict             Enable strict validation (treat warnings as errors)
    --fix                    Attempt to fix common issues automatically
    -h, --help               Show this help

EXAMPLES:
    # Validate default directory
    $0
    
    # Validate specific directory
    $0 -d ./my-glossary
    
    # Validate specific files
    $0 -f terms.csv -f definitions.json
    
    # Generate detailed report
    $0 --report validation-report.html
    
    # Strict validation
    $0 --strict --verbose

EXIT CODES:
    0 - All files valid
    1 - Some files invalid
    2 - No files found
    3 - Invalid arguments
EOF
}

# Parse command line arguments
FILES=()
DIRECTORIES=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--directory)
            DIRECTORIES+=("$2")
            shift 2
            ;;
        -f|--file)
            FILES+=("$2")
            shift 2
            ;;
        -r|--report)
            REPORT_FILE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -s|--strict)
            STRICT=true
            shift
            ;;
        --fix)
            FIX_ISSUES=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            show_help
            exit 3
            ;;
        *)
            # Treat as directory or file
            if [ -d "$1" ]; then
                DIRECTORIES+=("$1")
            elif [ -f "$1" ]; then
                FILES+=("$1")
            else
                print_error "Path not found: $1"
                exit 3
            fi
            shift
            ;;
    esac
done

# Use default directory if nothing specified
if [ ${#DIRECTORIES[@]} -eq 0 ] && [ ${#FILES[@]} -eq 0 ]; then
    DIRECTORIES+=("$DEFAULT_DIRECTORY")
fi

# Discover files function
discover_files() {
    local all_files=()
    
    # Add specified files
    for file in "${FILES[@]}"; do
        if [ -f "$file" ]; then
            all_files+=("$file")
        else
            print_error "File not found: $file"
            exit 3
        fi
    done
    
    # Discover files in directories
    for dir in "${DIRECTORIES[@]}"; do
        if [ ! -d "$dir" ]; then
            print_error "Directory not found: $dir"
            exit 3
        fi
        
        print_verbose "Scanning directory: $dir"
        
        while IFS= read -r -d '' file; do
            all_files+=("$file")
        done < <(find "$dir" -type f \( -name "*.csv" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" \) -print0)
    done
    
    if [ ${#all_files[@]} -eq 0 ]; then
        print_error "No glossary files found"
        exit 2
    fi
    
    printf '%s\n' "${all_files[@]}"
}

# CSV validation function
validate_csv() {
    local file="$1"
    local issues=()
    local warnings=()
    
    print_verbose "Validating CSV: $file"
    
    # Check if file is readable
    if [ ! -r "$file" ]; then
        issues+=("File not readable")
        return 1
    fi
    
    # Check file size
    local size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null)
    if [ "$size" -eq 0 ]; then
        issues+=("File is empty")
        return 1
    fi
    
    # Check for BOM (Byte Order Mark)
    if hexdump -C "$file" | head -1 | grep -q "ef bb bf"; then
        warnings+=("File contains UTF-8 BOM")
    fi
    
    # Use Python for detailed CSV validation
    local python_result
    python_result=$(python3 << EOF
import csv
import sys
import pandas as pd

file_path = "$file"
issues = []
warnings = []

try:
    # Try pandas first for robust parsing
    df = pd.read_csv(file_path)
    
    # Check for empty dataframe
    if len(df) == 0:
        issues.append("CSV file contains no data rows")
    
    # Check columns
    columns = [col.strip().lower() for col in df.columns]
    
    # Check for required columns
    phrase_cols = ['phrase', 'term', 'word', 'name', 'title']
    definition_cols = ['definition', 'description', 'meaning', 'explanation', 'desc']
    
    has_phrase = any(any(pcol in col for pcol in phrase_cols) for col in columns)
    has_definition = any(any(dcol in col for dcol in definition_cols) for col in columns)
    
    if not has_phrase:
        issues.append("No phrase column found (expected: phrase, term, word, name, or title)")
    
    if not has_definition:
        issues.append("No definition column found (expected: definition, description, meaning, explanation, or desc)")
    
    # Check for empty cells in key columns
    if has_phrase and has_definition:
        # Find the actual column names
        phrase_col = None
        definition_col = None
        
        for col in df.columns:
            col_lower = col.strip().lower()
            if not phrase_col and any(pcol in col_lower for pcol in phrase_cols):
                phrase_col = col
            if not definition_col and any(dcol in col_lower for dcol in definition_cols):
                definition_col = col
        
        if phrase_col and definition_col:
            empty_phrases = df[phrase_col].isna().sum()
            empty_definitions = df[definition_col].isna().sum()
            
            if empty_phrases > 0:
                warnings.append(f"{empty_phrases} empty phrase(s) found")
            
            if empty_definitions > 0:
                warnings.append(f"{empty_definitions} empty definition(s) found")
            
            # Check for duplicate phrases
            if phrase_col:
                duplicates = df[phrase_col].duplicated().sum()
                if duplicates > 0:
                    warnings.append(f"{duplicates} duplicate phrase(s) found")
    
    # Check for very long lines (potential formatting issues)
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if len(line) > 10000:
                warnings.append(f"Very long line detected at row {i} ({len(line)} characters)")
            if i > 100:  # Limit check to first 100 lines for performance
                break
    
    print(f"ROWS:{len(df)}")
    print(f"COLUMNS:{len(df.columns)}")
    
except Exception as e:
    issues.append(f"Python parsing error: {str(e)}")
    
    # Fallback to basic CSV module
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Try to detect delimiter
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(f, delimiter=delimiter)
            row_count = sum(1 for row in reader)
            print(f"ROWS:{row_count}")
            print(f"COLUMNS:{len(reader.fieldnames) if reader.fieldnames else 0}")
            
    except Exception as e2:
        issues.append(f"CSV parsing failed: {str(e2)}")

for issue in issues:
    print(f"ERROR:{issue}")

for warning in warnings:
    print(f"WARNING:{warning}")
EOF
)
    
    # Parse Python output
    local rows=0
    local columns=0
    
    while IFS= read -r line; do
        if [[ $line == ROWS:* ]]; then
            rows=${line#ROWS:}
        elif [[ $line == COLUMNS:* ]]; then
            columns=${line#COLUMNS:}
        elif [[ $line == ERROR:* ]]; then
            issues+=("${line#ERROR:}")
        elif [[ $line == WARNING:* ]]; then
            warnings+=("${line#WARNING:}")
        fi
    done <<< "$python_result"
    
    # Report results
    if [ ${#issues[@]} -eq 0 ]; then
        print_success "CSV valid: $file ($rows rows, $columns columns)"
        
        if [ ${#warnings[@]} -gt 0 ]; then
            for warning in "${warnings[@]}"; do
                print_warning "  $warning"
                ((WARNINGS++))
            done
        fi
        
        return 0
    else
        print_error "CSV invalid: $file"
        for issue in "${issues[@]}"; do
            print_error "  $issue"
        done
        
        # Attempt fixes if requested
        if [ "$FIX_ISSUES" = true ]; then
            attempt_csv_fix "$file"
        fi
        
        return 1
    fi
}

# JSON validation function
validate_json() {
    local file="$1"
    
    print_verbose "Validating JSON: $file"
    
    # Check if file is readable
    if [ ! -r "$file" ]; then
        print_error "JSON not readable: $file"
        return 1
    fi
    
    # Check file size
    local size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null)
    if [ "$size" -eq 0 ]; then
        print_error "JSON file is empty: $file"
        return 1
    fi
    
    # Validate JSON syntax
    local json_result
    if json_result=$(python3 -m json.tool "$file" 2>&1 >/dev/null); then
        # Additional validation with Python
        local validation_result
        validation_result=$(python3 << EOF
import json

file_path = "$file"
issues = []
warnings = []

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check structure
    if isinstance(data, list):
        print(f"TYPE:array")
        print(f"ITEMS:{len(data)}")
        
        # Check if items are objects with phrase/definition
        if data and isinstance(data[0], dict):
            sample = data[0]
            has_phrase = any(key.lower() in ['phrase', 'term', 'word', 'name'] for key in sample.keys())
            has_definition = any(key.lower() in ['definition', 'description', 'meaning', 'explanation'] for key in sample.keys())
            
            if not has_phrase:
                warnings.append("Array items may be missing phrase field")
            if not has_definition:
                warnings.append("Array items may be missing definition field")
    
    elif isinstance(data, dict):
        print(f"TYPE:object")
        
        # Look for common glossary structures
        glossary_keys = ['glossary', 'terms', 'definitions', 'vocabulary']
        found_glossary = False
        
        for key in glossary_keys:
            if key in data:
                found_glossary = True
                glossary_data = data[key]
                if isinstance(glossary_data, list):
                    print(f"ITEMS:{len(glossary_data)}")
                elif isinstance(glossary_data, dict):
                    print(f"ITEMS:{len(glossary_data)}")
                break
        
        if not found_glossary:
            # Check if it's a simple key-value structure
            if all(isinstance(v, str) for v in data.values()):
                print(f"ITEMS:{len(data)}")
                print("STRUCTURE:key-value")
            else:
                warnings.append("No standard glossary structure found")
    
    else:
        warnings.append("Unexpected JSON structure (not array or object)")

except json.JSONDecodeError as e:
    issues.append(f"JSON syntax error: {str(e)}")
except Exception as e:
    issues.append(f"JSON processing error: {str(e)}")

for issue in issues:
    print(f"ERROR:{issue}")

for warning in warnings:
    print(f"WARNING:{warning}")
EOF
)
        
        # Parse validation output
        local json_type=""
        local items=0
        local issues=()
        local warnings=()
        
        while IFS= read -r line; do
            if [[ $line == TYPE:* ]]; then
                json_type=${line#TYPE:}
            elif [[ $line == ITEMS:* ]]; then
                items=${line#ITEMS:}
            elif [[ $line == ERROR:* ]]; then
                issues+=("${line#ERROR:}")
            elif [[ $line == WARNING:* ]]; then
                warnings+=("${line#WARNING:}")
            fi
        done <<< "$validation_result"
        
        if [ ${#issues[@]} -eq 0 ]; then
            print_success "JSON valid: $file ($json_type, $items items)"
            
            if [ ${#warnings[@]} -gt 0 ]; then
                for warning in "${warnings[@]}"; do
                    print_warning "  $warning"
                    ((WARNINGS++))
                done
            fi
            
            return 0
        else
            print_error "JSON invalid: $file"
            for issue in "${issues[@]}"; do
                print_error "  $issue"
            done
            return 1
        fi
    else
        print_error "JSON syntax error: $file"
        print_error "  $json_result"
        return 1
    fi
}

# YAML validation function
validate_yaml() {
    local file="$1"
    
    print_verbose "Validating YAML: $file"
    
    # Check if file is readable
    if [ ! -r "$file" ]; then
        print_error "YAML not readable: $file"
        return 1
    fi
    
    # Check file size
    local size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null)
    if [ "$size" -eq 0 ]; then
        print_error "YAML file is empty: $file"
        return 1
    fi
    
    # Validate YAML syntax and structure
    local yaml_result
    yaml_result=$(python3 << EOF
import yaml

file_path = "$file"
issues = []
warnings = []

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if data is None:
        warnings.append("YAML file is empty or contains only comments")
    else:
        # Check structure similar to JSON
        if isinstance(data, list):
            print(f"TYPE:array")
            print(f"ITEMS:{len(data)}")
        elif isinstance(data, dict):
            print(f"TYPE:object")
            
            # Look for glossary structures
            glossary_keys = ['glossary', 'terms', 'definitions', 'vocabulary']
            found_glossary = False
            
            for key in glossary_keys:
                if key in data:
                    found_glossary = True
                    glossary_data = data[key]
                    if isinstance(glossary_data, list):
                        print(f"ITEMS:{len(glossary_data)}")
                    elif isinstance(glossary_data, dict):
                        print(f"ITEMS:{len(glossary_data)}")
                    break
            
            if not found_glossary:
                if all(isinstance(v, str) for v in data.values()):
                    print(f"ITEMS:{len(data)}")
                else:
                    warnings.append("No standard glossary structure found")
        else:
            warnings.append("Unexpected YAML structure")

except yaml.YAMLError as e:
    issues.append(f"YAML syntax error: {str(e)}")
except Exception as e:
    issues.append(f"YAML processing error: {str(e)}")

for issue in issues:
    print(f"ERROR:{issue}")

for warning in warnings:
    print(f"WARNING:{warning}")
EOF
)
    
    # Parse output
    local yaml_type=""
    local items=0
    local issues=()
    local warnings=()
    
    while IFS= read -r line; do
        if [[ $line == TYPE:* ]]; then
            yaml_type=${line#TYPE:}
        elif [[ $line == ITEMS:* ]]; then
            items=${line#ITEMS:}
        elif [[ $line == ERROR:* ]]; then
            issues+=("${line#ERROR:}")
        elif [[ $line == WARNING:* ]]; then
            warnings+=("${line#WARNING:}")
        fi
    done <<< "$yaml_result"
    
    if [ ${#issues[@]} -eq 0 ]; then
        print_success "YAML valid: $file ($yaml_type, $items items)"
        
        if [ ${#warnings[@]} -gt 0 ]; then
            for warning in "${warnings[@]}"; do
                print_warning "  $warning"
                ((WARNINGS++))
            done
        fi
        
        return 0
    else
        print_error "YAML invalid: $file"
        for issue in "${issues[@]}"; do
            print_error "  $issue"
        done
        return 1
    fi
}

# Attempt to fix CSV issues
attempt_csv_fix() {
    local file="$1"
    print_info "Attempting to fix CSV issues in: $file"
    
    # Create backup
    cp "$file" "$file.backup"
    print_verbose "Created backup: $file.backup"
    
    # Simple fixes could be implemented here
    # For now, just report what could be fixed
    print_info "  Would attempt to fix encoding issues"
    print_info "  Would attempt to normalize column names"
    print_info "  Would attempt to fix empty cells"
    print_warning "Automatic fixing not yet implemented"
}

# Generate HTML report
generate_html_report() {
    local report_file="$1"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Glossary File Validation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #2563eb; color: white; padding: 20px; border-radius: 5px; }
        .summary { background: #f8fafc; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .success { color: #059669; }
        .error { color: #dc2626; }
        .warning { color: #d97706; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #e5e7eb; padding: 8px; text-align: left; }
        th { background-color: #f9fafb; }
        .status-valid { background-color: #dcfce7; }
        .status-invalid { background-color: #fef2f2; }
        .status-warning { background-color: #fefbf2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Glossary File Validation Report</h1>
        <p>Generated: $(date)</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Files:</strong> $TOTAL_FILES</p>
        <p><strong>Valid Files:</strong> <span class="success">$VALID_FILES</span></p>
        <p><strong>Invalid Files:</strong> <span class="error">$INVALID_FILES</span></p>
        <p><strong>Warnings:</strong> <span class="warning">$WARNINGS</span></p>
    </div>
    
    <h2>Detailed Results</h2>
    <p>Detailed validation results would be listed here...</p>
    
</body>
</html>
EOF
    
    print_success "HTML report generated: $report_file"
}

# Main validation function
main() {
    print_header "Glossary File Validation ${SEARCH}"
    
    # Check dependencies
    if ! command -v python3 >/dev/null 2>&1; then
        print_error "python3 is required but not installed"
        exit 3
    fi
    
    # Check for required Python modules
    if ! python3 -c "import pandas, yaml" 2>/dev/null; then
        print_error "Required Python modules not found (pandas, PyYAML)"
        print_info "Install with: pip install pandas PyYAML"
        exit 3
    fi
    
    # Discover files
    print_info "Discovering glossary files..."
    local files
    readarray -t files < <(discover_files)
    
    TOTAL_FILES=${#files[@]}
    print_info "Found $TOTAL_FILES file(s) to validate"
    
    # Validate each file
    for file in "${files[@]}"; do
        print_verbose "Processing: $file"
        
        local file_ext="${file##*.}"
        local is_valid=false
        
        case "${file_ext,,}" in
            csv)
                if validate_csv "$file"; then
                    is_valid=true
                fi
                ;;
            json)
                if validate_json "$file"; then
                    is_valid=true
                fi
                ;;
            yaml|yml)
                if validate_yaml "$file"; then
                    is_valid=true
                fi
                ;;
            *)
                print_warning "Unknown file type: $file"
                ;;
        esac
        
        if [ "$is_valid" = true ]; then
            ((VALID_FILES++))
        else
            ((INVALID_FILES++))
        fi
    done
    
    # Generate report if requested
    if [ -n "$REPORT_FILE" ]; then
        print_info "Generating report..."
        if [[ "$REPORT_FILE" == *.html ]]; then
            generate_html_report "$REPORT_FILE"
        else
            print_warning "Only HTML reports are currently supported"
        fi
    fi
    
    # Final summary
    print_header "Validation Summary"
    print_info "Total files processed: $TOTAL_FILES"
    print_success "Valid files: $VALID_FILES"
    
    if [ $INVALID_FILES -gt 0 ]; then
        print_error "Invalid files: $INVALID_FILES"
    fi
    
    if [ $WARNINGS -gt 0 ]; then
        print_warning "Total warnings: $WARNINGS"
    fi
    
    # Determine exit code
    if [ $INVALID_FILES -gt 0 ]; then
        exit 1
    elif [ "$STRICT" = true ] && [ $WARNINGS -gt 0 ]; then
        print_error "Strict mode: warnings treated as errors"
        exit 1
    else
        print_success "All validations passed! ${CHECK}"
        exit 0
    fi
}

# Run main function
main
