#!/usr/bin/env python3
"""
Setup configuration for the Glossary Configuration Updater package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = (this_directory / "requirements.txt").read_text().strip().split('\n')
requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="glossary-config-updater",
    version="1.0.0",
    author="Your Organization",
    author_email="support@yourorg.com",
    description="A professional tool for updating API configurations with glossary terms",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourorg/glossary-config-updater",
    project_urls={
        "Bug Reports": "https://github.com/yourorg/glossary-config-updater/issues",
        "Source": "https://github.com/yourorg/glossary-config-updater",
        "Documentation": "https://github.com/yourorg/glossary-config-updater/docs",
    },
    
    # Package configuration
    packages=find_packages(exclude=["tests", "tests.*", "docs", "examples"]),
    include_package_data=True,
    zip_safe=False,
    
    # Python version requirement
    python_requires=">=3.8",
    
    # Dependencies
    install_requires=requirements,
    
    # Optional dependencies
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.18.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.910",
            "isort>=5.0.0",
        ],
        "docs": [
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "myst-parser>=0.17.0",
        ],
    },
    
    # Console scripts
    entry_points={
        "console_scripts": [
            "glossary-updater=glossary_updater.main:main",
        ],
    },
    
    # Package metadata
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    
    keywords="api configuration glossary terms update merge csv json yaml",
    
    # Data files
    package_data={
        "glossary_updater": [
            "py.typed",
        ],
    },
    
    # Additional metadata
    platforms=["any"],
    license="MIT",
    
    # Test configuration
    test_suite="tests",
    tests_require=[
        "pytest>=6.0",
        "pytest-asyncio>=0.18.0",
    ],
)
