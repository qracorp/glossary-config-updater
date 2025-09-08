# Glossary Configuration Updater

A tool for updating API configurations with glossary terms from various file formats (CSV, JSON, YAML). Available as both a standalone script for CI/CD pipelines and an installable Python package for development environments.

## ✨ Features

- **Multi-format support**: Process CSV, JSON, and YAML files
- **Flexible merge strategies**: Choose between merge or overwrite operations
- **Professional CLI**: Comprehensive command-line interface with verbose output
- **Dual deployment options**: Standalone script or installable Python package
- **Robust error handling**: Detailed error messages and validation
- **Dry run mode**: Test operations without making changes
- **Environment configuration**: Secure credential management via .env files
- **File discovery**: Automatic discovery of glossary files in directories
- **Cross-platform**: Works on Windows, Linux, and macOS
- **Self-installing dependencies**: Automatically installs required packages

## 🚀 Quick Start

### Option 1: Standalone Script (Recommended for CI/CD)

```bash
# Extract the delivered package
tar -xzf glossary-config-updater-v1.0.0-complete.tar.gz
cd glossary-config-updater-v1.0.0/

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp examples/.env.example .env
# Edit .env with your API credentials

# Use immediately
python tools/glossary_updater.py --help
```

### Option 2: Python Package Installation

```bash
# Install the wheel package
pip install ./dist/glossary_config_updater-1.0.0-py3-none-any.whl

# Use the installed command
glossary-updater --help

# Or use programmatically in Python
python -c "import glossary_updater; print('Package ready!')"
```

### Basic Usage Examples

**Standalone script:**
```bash
python tools/glossary_updater.py \
  --config config123 \
  --file terms.csv \
  --domain api.example.com \
  --username myuser \
  --password mypass
```

**Installed package:**
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

## 📁 Supported File Formats

### CSV Files
```csv
phrase,definition
API,"Application Programming Interface"
REST,"Representational State Transfer"
JSON,"JavaScript Object Notation"
```

### JSON Files
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

### YAML Files
```yaml
terms:
  - phrase: "API"
    definition: "Application Programming Interface"
  - phrase: "REST"
    definition: "Representational State Transfer"
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in your working directory:

```env
API_DOMAIN=api.example.com
API_USERNAME=myuser
API_PASSWORD=mypass
```

| Variable | Description | Required |
|----------|-------------|----------|
| `API_DOMAIN` | API domain (alternative to --domain) | Yes |
| `API_USERNAME` | API username (alternative to --username) | Yes |
| `API_PASSWORD` | API password (alternative to --password) | Yes |

### Command Line Options

```bash
# Standalone script
python tools/glossary_updater.py --help

# Installed package
glossary-updater --help
```

**Required Arguments:**
- `--config`, `-c`: Configuration ID to update

**File Input (at least one required):**
- `--file`: Glossary file path (can be used multiple times)
- `--directory`: Directory containing glossary files

**Authentication (if not in environment):**
- `--domain`: API domain
- `--username`, `-u`: API username  
- `--password`, `-p`: API password

**Processing Options:**
- `--merge-strategy {merge,overwrite}`: How to handle existing terms (default: merge)
- `--dry-run`: Process files and validate but don't update configuration
- `--verbose`, `-v`: Enable detailed output

## 📚 Usage Examples

### File Processing Examples

**Single file:**
```bash
python tools/glossary_updater.py --config config123 --file ./docs/glossary.csv
```

**Multiple files:**
```bash
python tools/glossary_updater.py \
  --config config123 \
  --file terms1.csv \
  --file terms2.json \
  --file terms3.yaml
```

**Directory processing:**
```bash
python tools/glossary_updater.py --config config123 --directory ./glossary-files
```

**Mixed input:**
```bash
python tools/glossary_updater.py \
  --config config123 \
  --file important-terms.csv \
  --directory ./additional-terms
```

### Merge Strategy Examples

**Merge (Default)** - Adds new terms and updates existing ones:
```bash
python tools/glossary_updater.py \
  --config config123 \
  --file new-terms.csv \
  --merge-strategy merge
```

**Overwrite** - Replaces all existing glossary terms:
```bash
python tools/glossary_updater.py \
  --config config123 \
  --file complete-glossary.csv \
  --merge-strategy overwrite
```

### Testing and Validation

**Dry run** - Preview changes without making them:
```bash
python tools/glossary_updater.py \
  --config config123 \
  --file terms.csv \
  --dry-run \
  --verbose
```

**Verbose output** - See detailed processing information:
```bash
python tools/glossary_updater.py \
  --config config123 \
  --file terms.csv \
  --verbose
```

## 🔄 Integration Examples

### GitHub Actions

```yaml
name: Update Glossary
on:
  push:
    paths: ['glossary/**']

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Update glossary
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
```

### Shell Script Automation

```bash
#!/bin/bash
# update-glossary.sh

set -e
source .env

echo "Starting glossary update..."

# Test with dry run first
python tools/glossary_updater.py \
  --config "$CONFIG_ID" \
  --directory ./glossary \
  --dry-run \
  --verbose

# Perform actual update
python tools/glossary_updater.py \
  --config "$CONFIG_ID" \
  --directory ./glossary \
  --merge-strategy merge \
  --verbose

echo "Glossary update completed!"
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

## 🐍 Python Package Usage

When you install the wheel package, you can use it programmatically:

### Command Line (Installed Package)

```bash
# Install package
pip install ./dist/glossary_config_updater-1.0.0-py3-none-any.whl

# Use clean command
glossary-updater --config config123 --file terms.csv
```

### Programmatic Usage

```python
# Use subprocess to call the CLI
import subprocess
import os

# Set environment
os.environ['API_DOMAIN'] = 'api.example.com'
os.environ['API_USERNAME'] = 'username'
os.environ['API_PASSWORD'] = 'password'

# Run the tool
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
    print("Error:", result.stderr)
```

### Direct Module Usage

```python
# Import and use package modules
from glossary_updater.processor import FileProcessor
from glossary_updater.config import Config

# Process files independently
processor = FileProcessor()
terms = processor.process_files(['terms.csv'])
print(f"Found {len(terms)} terms")

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
```

## 📦 Package Structure

```
glossary-config-updater/
├── README.md                          # This file
├── CHANGELOG.md                       # Version history
├── LICENSE                            # MIT license
├── requirements.txt                   # Dependencies
├── setup.py                          # Package configuration
├── build-package.sh                  # Build script
│
├── tools/
│   └── glossary_updater.py           # Standalone script
│
├── glossary_updater/                 # Python package
│   ├── __init__.py                   # Package init
│   ├── main.py                       # CLI entry point
│   ├── config.py                     # Configuration management
│   ├── api_client.py                 # API client
│   ├── processor.py                  # File processing
│   ├── merger.py                     # Merge strategies
│   └── utils.py                      # Utility functions
│
├── docs/                             # Documentation
│   ├── installation.md              # Setup guide
│   ├── usage.md                      # Usage examples
│   ├── file-formats.md              # Format specs
│   ├── api-reference.md             # Command reference
│   ├── troubleshooting.md           # Problem solving
│   └── integration-guide.md         # CI/CD guide
│
├── examples/                         # Templates and samples
│   ├── .env.example                 # Environment template
│   ├── glossary/                    # Sample data files
│   ├── workflows/                   # CI/CD examples
│   ├── docker/                      # Container examples
│   └── kubernetes/                  # K8s examples
│
├── scripts/                          # Development tools
│   ├── setup-dev.sh                # Dev setup
│   ├── test-connection.sh           # Connection test
│   ├── validate-files.sh            # File validation
│   └── demo.sh                      # Interactive demo
│
└── tests/                           # Test suite
    ├── test_main.py                 # Main tests
    ├── test_processor.py            # Processor tests
    ├── test_merger.py               # Merger tests
    ├── run-tests.sh                 # Test runner
    └── fixtures/                    # Test data
```

## 🔄 Merge Strategies

### Merge Strategy (Default)
- **Behavior**: Combines new terms with existing ones
- **Existing terms**: Updated if phrase matches (case-insensitive)
- **New terms**: Added to the configuration
- **Use case**: Incremental updates, maintaining existing terms

**Example:**
- Existing: API, REST, JSON (3 terms)
- New file: GraphQL, REST (updated definition), SOAP (3 terms)
- Result: API, REST (updated), JSON, GraphQL, SOAP (5 terms)

### Overwrite Strategy
- **Behavior**: Replaces all existing glossary terms
- **Existing terms**: Completely removed
- **New terms**: Become the entire glossary
- **Use case**: Complete refresh, authoritative updates

**Example:**
- Existing: API, REST, JSON (3 terms)
- New file: GraphQL, SOAP (2 terms)  
- Result: GraphQL, SOAP (2 terms, original terms removed)

## 🛠 Development

### Setup Development Environment

```bash
# Extract the package
tar -xzf glossary-config-updater-v1.0.0-complete.tar.gz
cd glossary-config-updater-v1.0.0/

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp examples/.env.example .env
# Edit .env with your credentials

# Test the setup
python tools/glossary_updater.py --help
```

### Running Tests

```bash
# Run test suite
./tests/run-tests.sh

# Test individual components
python -m pytest tests/test_processor.py -v

# Test with sample data
python tools/glossary_updater.py \
  --config test123 \
  --file examples/glossary/sample-terms.csv \
  --dry-run \
  --verbose
```

### Building Customer Packages

```bash
# Build all delivery packages
./build-package.sh 1.0.0

# Creates:
# build/glossary-config-updater-v1.0.0-complete.tar.gz    (recommended)
# build/glossary-config-updater-v1.0.0-standalone.tar.gz
# build/glossary-config-updater-v1.0.0-wheel.tar.gz
```

## 📖 Documentation

- **[Installation Guide](docs/installation.md)** - Setup instructions
- **[Usage Guide](docs/usage.md)** - Comprehensive usage examples
- **[File Formats](docs/file-formats.md)** - Supported format specifications
- **[API Reference](docs/api-reference.md)** - Command-line reference
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[Integration Guide](docs/integration-guide.md)** - CI/CD setup examples

## 🎯 When to Use Which Option

| Use Case | Recommended Option | Why |
|----------|-------------------|-----|
| CI/CD pipelines | Standalone script | No installation needed, just run |
| Production automation | Standalone script | Fewer dependencies, more portable |
| Development environment | Either option | Package allows programmatic use |
| Python applications | Package installation | Clean CLI + programmatic access |
| Docker containers | Standalone script | Simpler container builds |
| Team sharing | Complete package | Includes examples and documentation |

## 🔍 Real-World Examples

### Daily Term Updates

```bash
#!/bin/bash
# daily-update.sh
set -e
source .env

python tools/glossary_updater.py \
  --config "$CONFIG_ID" \
  --directory ./daily-terms \
  --merge-strategy merge \
  --verbose
```

### Multi-Environment Deployment

```bash
# Deploy to dev, staging, prod
environments=("dev:config-dev-123" "staging:config-staging-456" "prod:config-prod-789")

for env_config in "${environments[@]}"; do
    env="${env_config%%:*}"
    config="${env_config##*:}"
    
    echo "Updating $env environment..."
    python tools/glossary_updater.py \
      --config "$config" \
      --file ./release/glossary.csv \
      --verbose
done
```

### Validation Workflow

```bash
# validate-and-deploy.sh
echo "Step 1: Validating with dry run..."
python tools/glossary_updater.py \
  --config config123 \
  --directory ./glossary \
  --dry-run \
  --verbose

read -p "Proceed with update? (y/N): " confirm
if [[ $confirm == [yY] ]]; then
    python tools/glossary_updater.py \
      --config config123 \
      --directory ./glossary \
      --verbose
fi
```

## ❗ Common Issues

### Windows Users
- Use `python tools\glossary_updater.py` (backslashes)
- Skip `chmod` commands (not needed on Windows)
- Use PowerShell for best compatibility

### File Format Issues
- Ensure CSV files have `phrase,definition` headers
- Quote phrases containing commas or special characters
- Validate JSON/YAML syntax before processing

### Authentication Problems
- Check .env file exists and has correct format
- Verify API credentials work manually
- Use --verbose flag to see detailed error messages

## 🆘 Support

- **Issues**: Create detailed issue reports with error logs
- **Documentation**: Check docs/ directory for comprehensive guides
- **Quick Help**: Run with `--help` flag for command options

## 📊 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Acknowledgments

- Built with [httpx](https://github.com/encode/httpx) for reliable HTTP communication
- Uses [pandas](https://pandas.pydata.org/) for robust CSV processing
- YAML support provided by [PyYAML](https://pyyaml.org/)
- Designed for professional DevOps and development workflows

---

**Ready for immediate deployment in your CI/CD pipelines and development workflows.**