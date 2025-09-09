#!/usr/bin/env python3
"""
Standalone Glossary Configuration Updater Script

This script updates API configurations with glossary terms from files.
Can be run directly without installing the package.
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Add the parent directory to Python path so we can import the package
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_env_file(env_file='.env'):
    """Load environment variables from .env file if it exists."""
    env_path = Path(env_file)
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ[key.strip()] = value.strip()
        print(f"Loaded environment variables from {env_file}")
    else:
        print(f"No {env_file} file found - using command line args or environment variables")

# Load .env file first
load_env_file()

# Debug: Show loaded environment variables
print(f"API_DOMAIN: {os.getenv('API_DOMAIN', 'NOT SET')}")
print(f"API_USERNAME: {os.getenv('API_USERNAME', 'NOT SET')}")
print(f"API_PASSWORD: {'***' if os.getenv('API_PASSWORD') else 'NOT SET'}")
print(f"SSL_VERIFY: {os.getenv('SSL_VERIFY', 'NOT SET')}")

try:
    # Try to import required packages and install if missing
    required_packages = ['httpx', 'pyyaml', 'pandas']
    
    for package in required_packages:
        try:
            if package == 'pyyaml':
                import yaml
            elif package == 'pandas':
                import pandas
            elif package == 'httpx':
                import httpx
        except ImportError:
            print(f"Installing required package: {package}")
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

    # Import the main functionality
    from glossary_updater.config import create_parser, Config
    from glossary_updater.main import GlossaryUpdater
    from glossary_updater.utils import logger
    
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

def validate_args(args):
    """Validate command line arguments and environment variables."""
    errors = []
    
    # Check required authentication
    domain = args.domain or os.getenv('API_DOMAIN')
    username = args.username or os.getenv('API_USERNAME') 
    password = args.password or os.getenv('API_PASSWORD')
    
    if not domain:
        errors.append("Domain is required (use --domain or set API_DOMAIN)")
    if not username:
        errors.append("Username is required (use --username or set API_USERNAME)")
    if not password:
        errors.append("Password is required (use --password or set API_PASSWORD)")
    
    # Check file inputs
    if not args.files and not args.directories:
        errors.append("At least one file (--file) or directory (--directory) is required")
    
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    return domain, username, password

async def main():
    """Main function for standalone script."""
    try:
        # Parse arguments
        parser = create_parser()
        args = parser.parse_args()
        
        # Validate arguments
        domain, username, password = validate_args(args)
        
        # Set logging level
        if args.verbose:
            logger.setLevel("DEBUG")
        elif hasattr(args, 'quiet') and args.quiet:
            logger.setLevel("ERROR")
        
        # Create configuration
        config = Config.from_args(args)
        
        # Create updater
        updater = GlossaryUpdater(
            domain=domain,
            username=username,
            password=password,
            timeout=getattr(args, 'timeout', 30),
            max_retries=getattr(args, 'max_retries', 3)
        )
        
        # Run the update
        async with updater:
            # Test connection first
            logger.info("Testing API connection...")
            if not await updater.test_connection():
                logger.error("Failed to connect to API")
                sys.exit(1)
            
            logger.info("API connection successful")
            
            # Run the update
            result = await updater.update_from_files(
                config_id=config.config_id,
                file_paths=config.file_paths,
                directory_paths=config.directory_paths,
                merge_strategy=config.merge_strategy,
                dry_run=config.dry_run
            )
            
            if result['success']:
                logger.info("Update completed successfully!")
                
                # Show summary
                if config.verbose: 
                    if config.dry_run:
                        logger.info("  Mode: DRY RUN (no changes made)")
                    else:
                        logger.info("  Mode: LIVE UPDATE")
                
                sys.exit(0)
            else:
                logger.error("Update failed")
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        if 'args' in locals() and getattr(args, 'verbose', False):
            import traceback
            logger.error("Full traceback:")
            logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())