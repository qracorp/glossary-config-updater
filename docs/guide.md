# Guide

Reference for the Glossary Configuration Updater.

## Table of Contents

- [Getting Started](#getting-started)
- [Installation Options](#installation-options)
- [Basic Usage](#basic-usage)
- [Authentication](#authentication)
- [File Processing](#file-processing)
- [Merge Strategies](#merge-strategies)
- [Advanced Usage](#advanced-usage)
- [Command Reference](#command-reference)
- [File Formats](#file-formats)
- [CI/CD Integration](#cicd-integration)
- [Best Practices](#best-practices)
- [Common Workflows](#common-workflows)

## Getting Started

### Quick Setup (5 minutes)

**Step 1: Extract and Setup**
```bash
# Extract the delivered package
tar -xzf glossary-config-updater-v1.0.0-complete.tar.gz
cd glossary-config-updater-v1.0.0/

# Install dependencies
pip install -r requirements.txt

# Create your environment file
cp examples/.env.example .env
```

**Step 2: Configure Credentials**
```bash
# Edit .env with your API details
nano .env
```
```env
API_DOMAIN=your-api-domain.com
API_USERNAME=your-username
API_PASSWORD=your-password
```

**Step 3: Test It Works**
```bash
# Test with sample data (safe - no real changes)
python tools/glossary_updater.py \
  --config your-config-id \
  --file examples/glossary/sample-terms.csv \
  --dry-run \
  --verbose
```

### Choose Your Integration Method

#### Option A: Simple File-Based Updates
**Use when:** You have CSV/JSON/YAML files with terms

```bash
# Update from a single file
python tools/glossary_updater.py --config config123 --file terms.csv

# Always test first with --dry-run
python tools/glossary_updater.py --config config123 --file terms.csv --dry-run --verbose
```

#### Option B: CI/CD Integration
**Use when:** You want automated updates in your deployment pipeline

```yaml
# GitHub Actions example
- name: Update Glossary
  run: |
    pip install -r requirements.txt
    python tools/glossary_updater.py \
      --config ${{ vars.CONFIG_ID }} \
      --directory ./glossary/ \
      --verbose
  env:
    API_DOMAIN: ${{ secrets.API_DOMAIN }}
    API_USERNAME: ${{ secrets.API_USERNAME }}
    API_PASSWORD: ${{ secrets.API_PASSWORD }}
```

#### Option C: Programmatic Integration
**Use when:** You want to pull terms from your existing systems and update configurations programmatically

```python
# Install package and use modules directly
pip install ./dist/glossary_config_updater-1.0.0-py3-none-any.whl

from glossary_updater.processor import GlossaryTerm
from glossary_updater.api_client import APIClient
from glossary_updater.merger import ConfigurationMerger

# Direct data integration (no files needed)
# Pull terms from your system, convert to GlossaryTerm objects, update directly
```

## Installation Options

### Option 1: Standalone Script (Recommended for CI/CD)
```bash
# Extract the package
tar -xzf glossary-config-updater-v1.0.0-complete.tar.gz
cd glossary-config-updater-v1.0.0/

# Install dependencies
pip install -r requirements.txt

# Use directly
python tools/glossary_updater.py --help
```

### Option 2: Python Package Installation
```bash
# Install the wheel package
pip install ./dist/glossary_config_updater-1.0.0-py3-none-any.whl

# Use from command line
glossary-updater --help

# Or import in Python scripts
python -c "import glossary_updater; print('Package installed successfully')"
```

## Basic Usage

### Command Structure

```bash
# Option 1: Standalone script
python tools/glossary_updater.py [OPTIONS] --config CONFIG_ID

# Option 2: Installed package
glossary-updater [OPTIONS] --config CONFIG_ID
```

### Minimal Examples

**Using standalone script:**
```bash
python tools/glossary_updater.py \
  --config config123 \
  --file terms.csv \
  --domain api.example.com \
  --username myuser \
  --password mypass
```

**Using installed package:**
```bash
glossary-updater \
  --config config123 \
  --file terms.csv \
  --domain api.example.com \
  --username myuser \
  --password mypass
```

**With environment variables:**
```bash
# Set credentials in .env file or environment
export API_DOMAIN=api.example.com
export API_USERNAME=myuser
export API_PASSWORD=mypass

# Use without credentials in command
python tools/glossary_updater.py --config config123 --file terms.csv
```

## Authentication

### Method 1: Environment Variables (Recommended)

Create a `.env` file in your working directory:

```bash
# Copy the example file
cp examples/.env.example .env

# Edit with your credentials
nano .env
```

**`.env` file content:**
```env
API_DOMAIN=api.example.com
API_USERNAME=myuser
API_PASSWORD=mypass
```

**Usage:**
```bash
# Standalone script - reads .env file from current directory
python tools/glossary_updater.py --config config123 --file terms.csv

# Installed package - reads .env file from current directory
glossary-updater --config config123 --file terms.csv
```

### Method 2: Environment Variables in Shell

```bash
# Set environment variables
export API_DOMAIN=api.example.com
export API_USERNAME=myuser
export API_PASSWORD=mypass

# Use without credentials in command
python tools/glossary_updater.py --config config123 --file terms.csv
```

### Method 3: Command Line Arguments

```bash
python tools/glossary_updater.py \
  --config config123 \
  --file terms.csv \
  --domain api.example.com \
  --username myuser \
  --password mypass
```

### Method 4: Mixed Approach

```bash
# Set domain in environment, pass user credentials
export API_DOMAIN=api.example.com

python tools/glossary_updater.py \
  --config config123 \
  --file terms.csv \
  --username myuser \
  --password mypass
```

### Security Best Practices

**Never put passwords in scripts or command history:**

```bash
# Good: Use environment variables
export API_PASSWORD=$(read -s -p "Enter password: " && echo $REPLY)

# Good: Use .env file
cat > .env << EOF
API_DOMAIN=api.example.com
API_USERNAME=myuser
API_PASSWORD=secret123
EOF

# Bad: Password in command (visible in history)
python tools/glossary_updater.py --password "secret123" --file terms.csv --config config123
```

## File Processing

### Single File

```bash
# Process one CSV file
python tools/glossary_updater.py --config config123 --file glossary.csv

# Process one JSON file
python tools/glossary_updater.py --config config123 --file terms.json

# Process one YAML file
python tools/glossary_updater.py --config config123 --file definitions.yaml
```

### Multiple Files

```bash
# Process multiple files of same type
python tools/glossary_updater.py \
  --config config123 \
  --file terms1.csv \
  --file terms2.csv

# Process mixed file types
python tools/glossary_updater.py \
  --config config123 \
  --file terms.csv \
  --file extra.json \
  --file more.yaml
```

### Directory Processing

```bash
# Process all supported files in directory
python tools/glossary_updater.py --config config123 --directory ./glossary-files

# Process multiple directories
python tools/glossary_updater.py \
  --config config123 \
  --directory ./terms \
  --directory ./definitions

# Mixed file and directory input
python tools/glossary_updater.py \
  --config config123 \
  --file important.csv \
  --directory ./additional-terms
```

### Supported File Formats

The tool automatically discovers and processes:

| Extension | Format | Description |
|-----------|--------|-------------|
| `.csv` | CSV | Comma-separated values with `phrase,definition` headers |
| `.json` | JSON | Array of objects with `phrase` and `definition` properties |
| `.yaml`, `.yml` | YAML | YAML structure with glossary terms |

**Example directory structure:**
```
glossary-files/
├── technical-terms.csv      ✅ Processed
├── business-glossary.json   ✅ Processed  
├── api-definitions.yaml     ✅ Processed
├── legacy-terms.yml         ✅ Processed
├── readme.txt               ❌ Ignored (unsupported)
└── backup.csv.bak           ❌ Ignored (wrong extension)
```

## Merge Strategies

### Merge Strategy (Default)

Combines new terms with existing ones. Existing terms are updated if the phrase matches (case-insensitive).

```bash
# Explicitly specify merge (default behavior)
python tools/glossary_updater.py \
  --config config123 \
  --file new-terms.csv \
  --merge-strategy merge

# Same as above (merge is default)
python tools/glossary_updater.py \
  --config config123 \
  --file new-terms.csv
```

**Example merge operation:**
- **Existing terms**: API, REST, JSON (3 terms)
- **New file terms**: GraphQL, REST (updated definition), SOAP (3 terms)
- **Result**: API, REST (updated), JSON, GraphQL, SOAP (5 terms)

### Overwrite Strategy

Completely replaces all existing glossary terms with new ones.

```bash
# Use overwrite strategy
python tools/glossary_updater.py \
  --config config123 \
  --file complete-glossary.csv \
  --merge-strategy overwrite
```

**Example overwrite operation:**
- **Existing terms**: API, REST, JSON (3 terms)
- **New file terms**: GraphQL, SOAP (2 terms)
- **Result**: GraphQL, SOAP (2 terms - original terms removed)

### Choosing the Right Strategy

| Use Case | Strategy | Command Example |
|----------|----------|-----------------|
| Adding new terms | `merge` | `--merge-strategy merge` (default) |
| Updating definitions | `merge` | `--merge-strategy merge` |
| Complete refresh | `overwrite` | `--merge-strategy overwrite` |
| System migration | `overwrite` | `--merge-strategy overwrite` |
| Monthly updates | `merge` | `--merge-strategy merge` |

## Advanced Usage

### Dry Run Mode

Test your changes without actually updating the configuration:

```bash
# Preview what would happen
python tools/glossary_updater.py \
  --config config123 \
  --file terms.csv \
  --dry-run \
  --verbose
```

**Example dry run output:**
```
Installing required package: pyyaml
Requirement already satisfied: pyyaml...

Step 1: Discovering files...
Found 1 file(s): terms.csv

Step 2: Processing files...
Processing file: terms.csv
  → Found 25 terms

Step 3: Connecting to API...
✅ Authentication successful

Step 4: Retrieving configuration...
✅ Retrieved configuration: config123

Step 5: Performing merge...
✅ Merge completed: 10 → 35 terms (25 added, 0 updated)

Step 6: Dry run - no changes made

✅ Update completed successfully!
{
  "success": true,
  "dry_run": true,
  "config_id": "config123",
  "files_processed": 1,
  "terms_extracted": 25,
  "preview": {
    "strategy": "merge",
    "current_terms": 10,
    "provided_terms": 25,
    "terms_after_merge": 35,
    "terms_that_would_be_added": 25,
    "terms_that_would_be_updated": 0
  }
}
```

### Verbose Output

Get detailed information about the update process:

```bash
python tools/glossary_updater.py \
  --config config123 \
  --file terms.csv \
  --verbose
```

**Verbose output includes:**
- File discovery details
- Term processing progress  
- API authentication status
- Configuration retrieval information
- Merge operation statistics
- Final success/failure summary

### Programmatic Usage (Installed Package Only)

When you install the wheel package, you can also use the tool programmatically in your Python scripts:

#### Command Line Usage (Installed Package)

```bash
# Install the package first
pip install ./dist/glossary_config_updater-1.0.0-py3-none-any.whl

# Use the installed command
glossary-updater --config config123 --file terms.csv
```

#### Subprocess Usage

```python
# Use subprocess to call the CLI
import subprocess
import os

# Set environment variables
os.environ['API_DOMAIN'] = 'api.example.com'
os.environ['API_USERNAME'] = 'username'
os.environ['API_PASSWORD'] = 'password'

# Run via subprocess
result = subprocess.run([
    'glossary-updater',
    '--config', 'config123',
    '--file', 'terms.csv',
    '--verbose'
], capture_output=True, text=True)

if result.returncode == 0:
    print("Success!")
    print(result.stdout)
else:
    print("Error:")
    print(result.stderr)
```

#### Direct Module Usage

```python
# Use package modules directly
from glossary_updater.config import Config
from glossary_updater.processor import FileProcessor
from glossary_updater.main import main
import sys

# Create configuration
config = Config(
    domain='api.example.com',
    username='username',
    password='password',
    config_id='config123',
    file_paths=['terms.csv'],
    directory_paths=[],
    merge_strategy='merge',
    dry_run=False,
    verbose=True
)

# Process files independently
processor = FileProcessor()
terms = processor.process_files(config.file_paths)
print(f"Extracted {len(terms)} terms")

# Or call main function programmatically
sys.argv = [
    'glossary-updater',
    '--config', 'config123',
    '--file', 'terms.csv',
    '--dry-run'
]
main()
```

#### Direct Term Data Usage (No Files)

For developers who want to pass term data directly without creating files:

```python
# Direct term data processing (most flexible)
from glossary_updater.processor import GlossaryTerm
from glossary_updater.api_client import APIClient
from glossary_updater.merger import ConfigurationMerger

# Get terms from any source (API, database, etc.)
def get_terms_from_your_system():
    """Your custom data source"""
    return [
        {"phrase": "API", "definition": "Application Programming Interface"},
        {"phrase": "REST", "definition": "Representational State Transfer"},
        {"phrase": "GraphQL", "definition": "Graph Query Language for APIs"}
    ]

# Convert to GlossaryTerm objects
terms_data = get_terms_from_your_system()
terms = [
    GlossaryTerm(phrase=t['phrase'], definition=t['definition']) 
    for t in terms_data
]

# Direct API usage - no files needed
client = APIClient('api.example.com', 'username', 'password')
current_config = client.get_configuration('config123')

# Direct merge
merger = ConfigurationMerger()
updated_config, stats = merger.merge_glossary_terms(current_config, terms, 'merge')

# Direct update
result = client.update_configuration('config123', updated_config)

print(f"Updated {stats['terms_after']} terms")
print(f"Added: {stats['terms_added']}, Updated: {stats['terms_updated']}")
```

### Testing Connection

```bash
# Test API connection without making changes
python tools/glossary_updater.py \
  --config any-config \
  --file examples/glossary/sample-terms.csv \
  --dry-run \
  --verbose
```

## Command Reference

### Available Options

```bash
# Standalone script
python tools/glossary_updater.py [OPTIONS]

# Installed package
glossary-updater [OPTIONS]
```

**Required Arguments:**
- `--config`, `-c CONFIG`: Configuration ID to update

**File Input (at least one required):**
- `--file FILES`: Glossary file path (can be used multiple times)
- `--directory DIRECTORIES`: Directory containing glossary files

**Authentication (if not in environment):**
- `--domain DOMAIN`: API domain (e.g., api.example.com)
- `--username`, `-u USERNAME`: API username
- `--password`, `-p PASSWORD`: API password

**Processing Options:**
- `--merge-strategy {merge,overwrite}`: How to handle existing terms (default: merge)
- `--dry-run`: Process files and validate but don't update configuration
- `--verbose`, `-v`: Enable detailed output

**Help:**
- `--help`, `-h`: Show help message

### Examples

#### Basic File Processing
```bash
# Process single CSV file
python tools/glossary_updater.py --config config123 --file terms.csv

# Process multiple files
python tools/glossary_updater.py --config config123 --file terms1.csv --file terms2.json --file terms3.yaml

# Process entire directory
python tools/glossary_updater.py --config config123 --directory ./glossary-files/
```

#### Different Merge Strategies
```bash
# Merge with existing terms (default)
python tools/glossary_updater.py --config config123 --file terms.csv --merge-strategy merge

# Replace all existing terms
python tools/glossary_updater.py --config config123 --file terms.csv --merge-strategy overwrite
```

#### Testing and Debugging
```bash
# Dry run - see what would happen without making changes
python tools/glossary_updater.py --config config123 --file terms.csv --dry-run

# Verbose output for debugging
python tools/glossary_updater.py --config config123 --file terms.csv --verbose

# Combine dry run with verbose
python tools/glossary_updater.py --config config123 --file terms.csv --dry-run --verbose
```

#### With API Credentials
```bash
# Provide credentials via command line
python tools/glossary_updater.py \
  --config config123 \
  --file terms.csv \
  --domain api.example.com \
  --username myuser \
  --password mypass

# Or use environment variables (recommended)
export API_DOMAIN=api.example.com
export API_USERNAME=myuser
export API_PASSWORD=mypass
python tools/glossary_updater.py --config config123 --file terms.csv
```

### Success Response Format

When the update completes successfully, the tool outputs JSON:

```json
{
  "success": true,
  "dry_run": false,
  "config_id": "config123",
  "files_processed": 2,
  "terms_extracted": 45,
  "merge_stats": {
    "strategy": "merge",
    "terms_before": 30,
    "terms_after": 65,
    "terms_added": 15,
    "terms_updated": 20,
    "terms_removed": 0,
    "timestamp": "2025-01-15T10:30:45Z"
  },
  "backup_info": {
    "created": "2025-01-15T10:30:44Z",
    "size": 2048
  },
  "updated_configuration": {
    "entities": [...],
    "resources": [...]
  }
}
```

### Error Response Format

```json
{
  "success": false,
  "error": "Authentication failed",
  "error_type": "AuthenticationError",
  "details": {
    "config_id": "config123",
    "files_attempted": ["terms.csv"],
    "timestamp": "2025-01-15T10:30:45Z"
  }
}
```

## File Formats

### CSV Format

**Required headers:** `phrase,definition`

```csv
phrase,definition
API,"Application Programming Interface"
REST,"Representational State Transfer"
JSON,"JavaScript Object Notation"
```

**Tips:**
- Quote phrases containing commas or special characters
- Ensure UTF-8 encoding
- Include headers in first row

### JSON Format

**Array of objects with `phrase` and `definition` properties:**

```json
[
  {
    "phrase": "API",
    "definition": "Application Programming Interface"
  },
  {
    "phrase": "REST",
    "definition": "Representational State Transfer"
  }
]
```

**Tips:**
- Use double quotes for all strings
- No trailing commas
- Validate JSON syntax before processing

### YAML Format

**Terms array with phrase and definition fields:**

```yaml
terms:
  - phrase: "API"
    definition: "Application Programming Interface"
  - phrase: "REST"
    definition: "Representational State Transfer"
```

**Tips:**
- Watch indentation (use spaces, not tabs)
- Quote special characters
- Validate YAML syntax before processing

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/glossary-update.yml
name: Update Glossary

on:
  push:
    paths: ['glossary/**']
  workflow_dispatch:

jobs:
  update-glossary:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      # Option 1: Using standalone script
      - name: Install dependencies (standalone)
        run: |
          pip install -r requirements.txt
      
      - name: Update glossary (standalone)
        run: |
          python tools/glossary_updater.py \
            --config ${{ vars.CONFIG_ID }} \
            --directory ./glossary/ \
            --merge-strategy merge \
            --verbose
        env:
          API_DOMAIN: ${{ secrets.API_DOMAIN }}
          API_USERNAME: ${{ secrets.API_USERNAME }}
          API_PASSWORD: ${{ secrets.API_PASSWORD }}

      # Option 2: Using installed package (alternative)
      # - name: Install package
      #   run: |
      #     pip install ./dist/glossary_config_updater-1.0.0-py3-none-any.whl
      # 
      # - name: Update glossary (package)
      #   run: |
      #     glossary-updater \
      #       --config ${{ vars.CONFIG_ID }} \
      #       --directory ./glossary/ \
      #       --merge-strategy merge \
      #       --verbose
      #   env:
      #     API_DOMAIN: ${{ secrets.API_DOMAIN }}
      #     API_USERNAME: ${{ secrets.API_USERNAME }}
      #     API_PASSWORD: ${{ secrets.API_PASSWORD }}
```

### GitLab CI Integration

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip/

validate-glossary:
  stage: validate
  image: python:3.9
  script:
    - pip install -r requirements.txt
    - echo "Validating glossary files with dry run..."
    - python tools/glossary_updater.py 
        --config $CONFIG_ID 
        --directory ./glossary/ 
        --dry-run 
        --verbose
  variables:
    API_DOMAIN: $API_DOMAIN
    API_USERNAME: $API_USERNAME
    API_PASSWORD: $API_PASSWORD
  only:
    changes:
      - glossary/**/*
  except:
    - main

deploy-glossary:
  stage: deploy
  image: python:3.9
  script:
    - pip install -r requirements.txt
    - echo "Deploying glossary updates..."
    - python tools/glossary_updater.py 
        --config $CONFIG_ID 
        --directory ./glossary/ 
        --merge-strategy merge 
        --verbose
    - echo "Glossary deployment completed successfully"
  variables:
    API_DOMAIN: $API_DOMAIN
    API_USERNAME: $API_USERNAME
    API_PASSWORD: $API_PASSWORD
  only:
    - main
  when: manual
  environment:
    name: production
```

### Jenkins Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any
    
    environment {
        API_DOMAIN = credentials('api-domain')
        API_USERNAME = credentials('api-username')  
        API_PASSWORD = credentials('api-password')
        CONFIG_ID = credentials('config-id')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }
        
        stage('Validate') {
            steps {
                sh '''
                    python tools/glossary_updater.py \
                        --config ${CONFIG_ID} \
                        --directory ./glossary/ \
                        --dry-run \
                        --verbose
                '''
            }
        }
        
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                input message: 'Deploy glossary updates?', ok: 'Deploy'
                sh '''
                    python tools/glossary_updater.py \
                        --config ${CONFIG_ID} \
                        --directory ./glossary/ \
                        --merge-strategy merge \
                        --verbose
                '''
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: '**/*.log', allowEmptyArchive: true
        }
        failure {
            emailext (
                subject: "Glossary Update Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "Check console output at ${env.BUILD_URL}",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
```

### Azure DevOps

```yaml
# azure-pipelines.yml
trigger:
  paths:
    include:
    - glossary/*

pool:
  vmImage: 'ubuntu-latest'

variables:
  pythonVersion: '3.9'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '$(pythonVersion)'
  displayName: 'Use Python $(pythonVersion)'

- script: |
    pip install -r requirements.txt
  displayName: 'Install dependencies'

- script: |
    python tools/glossary_updater.py \
      --config $(CONFIG_ID) \
      --directory ./glossary/ \
      --dry-run \
      --verbose
  env:
    API_DOMAIN: $(API_DOMAIN)
    API_USERNAME: $(API_USERNAME)
    API_PASSWORD: $(API_PASSWORD)
  displayName: 'Validate glossary updates'

- script: |
    python tools/glossary_updater.py \
      --config $(CONFIG_ID) \
      --directory ./glossary/ \
      --merge-strategy merge \
      --verbose
  env:
    API_DOMAIN: $(API_DOMAIN)
    API_USERNAME: $(API_USERNAME)
    API_PASSWORD: $(API_PASSWORD)
  displayName: 'Deploy glossary updates'
  condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
```

## Best Practices

### File Organization

**Recommended project structure:**
```
project/
├── glossary/
│   ├── technical-terms.csv      # Core technical vocabulary
│   ├── business-terms.json      # Business definitions  
│   ├── api-definitions.yaml     # API-specific terms
│   └── archived/
│       └── old-terms-2024.csv   # Keep old versions
├── scripts/
│   ├── update-glossary.sh       # Automation script
│   └── validate-terms.py        # Validation script
├── .env                         # Environment configuration
├── .env.example                 # Template for others
└── .gitignore                   # Exclude .env from version control
```

### Term Formatting

**Use consistent CSV headers:**
```csv
phrase,definition
"API","Application Programming Interface" 
"REST API","Representational State Transfer API"
"OAuth 2.0","Open Authorization 2.0"
```

**Quote phrases with special characters:**
```csv
phrase,definition
"Don't","Contraction meaning 'do not'"
"50/50","Equal split or probability"
"API (v2)","Second version of the API"
```

**Write clear, concise definitions:**
```csv
phrase,definition
"Microservice","A small, independent service that performs a specific business function"
"Container","A lightweight, standalone package that includes everything needed to run an application"
"Webhook","An HTTP callback triggered by specific events in a system"
```

### Environment Management

**Use .env files for development:**
```bash
# .env for development
API_DOMAIN=dev-api.example.com
API_USERNAME=dev-user
API_PASSWORD=dev-password

# .env.staging for staging
API_DOMAIN=staging-api.example.com
API_USERNAME=staging-user
API_PASSWORD=staging-password
```

**Never commit .env files:**
```bash
# .gitignore
.env
.env.local
.env.staging
.env.production
```

**Provide .env.example:**
```bash
# .env.example
API_DOMAIN=api.example.com
API_USERNAME=your-username
API_PASSWORD=your-password
```

### Error Recovery

**Always test with dry run first:**
```bash
# Step 1: Test the update
python tools/glossary_updater.py \
  --config config123 \
  --file terms.csv \
  --dry-run \
  --verbose

# Step 2: If successful, run for real
python tools/glossary_updater.py \
  --config config123 \
  --file terms.csv \
  --verbose
```

### Performance Optimization

**Use CSV for large datasets:**
- CSV parsing is fastest for large term lists
- Remove unnecessary metadata columns
- Keep definitions concise

**Split very large files:**
```bash
# For files with thousands of terms
head -1 huge-glossary.csv > header.csv

# Split into chunks of 1000 terms each
tail -n +2 huge-glossary.csv | split -l 1000 - chunk-

# Add header to each chunk and process
for chunk in chunk-*; do
    cat header.csv "$chunk" > "terms-$chunk.csv"
    python tools/glossary_updater.py \
        --config config123 \
        --file "terms-$chunk.csv" \
        --merge-strategy merge
done
```

## Common Workflows

### Daily Term Updates

```bash
#!/bin/bash
# daily-update.sh

set -e
source .env

echo "Starting daily glossary update..."

# Validate environment
if [ -z "$CONFIG_ID" ]; then
    echo "❌ CONFIG_ID not set in .env"
    exit 1
fi

# Test with dry run
echo "Testing update..."
python tools/glossary_updater.py \
    --config "$CONFIG_ID" \
    --directory ./daily-terms \
    --dry-run

# Perform actual update
echo "Performing update..."
python tools/glossary_updater.py \
    --config "$CONFIG_ID" \
    --directory ./daily-terms \
    --merge-strategy merge \
    --verbose

echo "✅ Daily update completed"
```

### Release Glossary Refresh

```bash
#!/bin/bash
# release-refresh.sh

set -e
source .env

echo "Starting release glossary refresh..."

# Complete overwrite with authoritative source
python tools/glossary_updater.py \
    --config "$CONFIG_ID" \
    --file ./release/complete-glossary.csv \
    --merge-strategy overwrite \
    --verbose

echo "✅ Release refresh completed"
```

### Multi-Environment Updates

```bash
#!/bin/bash
# multi-env-update.sh

declare -A environments=(
    ["dev"]="config-dev-123"
    ["staging"]="config-staging-456" 
    ["prod"]="config-prod-789"
)

glossary_file="./terms/latest-glossary.csv"

for env in "${!environments[@]}"; do
    config_id="${environments[$env]}"
    
    echo "Updating $env environment (config: $config_id)..."
    
    # Test first
    if ! python tools/glossary_updater.py \
        --config "$config_id" \
        --file "$glossary_file" \
        --dry-run; then
        echo "❌ Dry run failed for $env"
        continue
    fi
    
    # Update
    python tools/glossary_updater.py \
        --config "$config_id" \
        --file "$glossary_file" \
        --merge-strategy merge \
        --verbose
    
    echo "✅ Updated $env environment"
done

echo "✅ All environments updated"
```

### Validation Workflow

```bash
#!/bin/bash
# validate-and-update.sh

set -e
source .env

echo "Starting validation workflow..."

glossary_dir="./glossary"
config_id="$CONFIG_ID"

# Step 1: Validate files exist and are readable
echo "Step 1: Validating files..."
if [ ! -d "$glossary_dir" ]; then
    echo "❌ Glossary directory not found: $glossary_dir"
    exit 1
fi

file_count=$(find "$glossary_dir" -name "*.csv" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" | wc -l)
if [ "$file_count" -eq 0 ]; then
    echo "❌ No glossary files found in $glossary_dir"
    exit 1
fi

echo "Found $file_count glossary files"

# Step 2: Validate file contents
echo "Step 2: Validating file contents..."
for file in "$glossary_dir"/*.{csv,json,yaml,yml}; do
    if [ -f "$file" ]; then
        echo "Checking: $file"
        case "$file" in
            *.csv)
                # Check CSV has required headers
                if ! head -1 "$file" | grep -q "phrase.*definition"; then
                    echo "❌ CSV file missing required headers: $file"
                    exit 1
                fi
                ;;
            *.json)
                # Validate JSON syntax
                if ! python -m json.tool "$file" >/dev/null 2>&1; then
                    echo "❌ Invalid JSON syntax: $file"
                    exit 1
                fi
                ;;
            *.yaml|*.yml)
                # Validate YAML syntax
                if ! python -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
                    echo "❌ Invalid YAML syntax: $file"
                    exit 1
                fi
                ;;
        esac
    fi
done

# Step 3: Dry run to validate processing
echo "Step 3: Performing dry run..."
python tools/glossary_updater.py \
    --config "$config_id" \
    --directory "$glossary_dir" \
    --dry-run \
    --verbose

# Step 4: Get user confirmation  
echo ""
read -p "Validation passed. Proceed with actual update? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Update cancelled by user"
    exit 0
fi

# Step 5: Perform actual update
echo "Step 4: Performing actual update..."
python tools/glossary_updater.py \
    --config "$config_id" \
    --directory "$glossary_dir" \
    --merge-strategy merge \
    --verbose

echo "✅ Validation workflow completed successfully"
```

---

**Quick Support References:**
- Windows: Use `python tools\glossary_updater.py` (backslashes)
- Authentication errors: Check your .env file
- File format errors: Validate CSV/JSON/YAML syntax first
- Get help: `python tools/glossary_updater.py --help`