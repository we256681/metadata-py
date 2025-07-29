"""
Metadata Management for Markdown Files

This package provides tools for managing metadata in markdown files,
including version control integration, author detection, and bulk processing.
"""

# Version of the package
__version__ = "1.0.0"

# Import core functionality
from .core import (
    # File operations
    read_file,
    write_file,

    # Metadata processing
    parse_metadata,
    extract_metadata,
    format_metadata,
    add_or_update_metadata,
    remove_metadata,
    get_content_without_metadata,

    # Version control
    analyze_document_changes,
    increment_version,

    # Author detection
    get_author_info,
    determine_author,
    get_git_author,
    get_git_contributors,
    get_system_author,
    get_file_system_author,
    is_git_repository,

    # File operations
    find_markdown_files,
    load_ignore_patterns,
    should_ignore,

    # Processing functions
    process_file,
    process_bulk,
)

# Import CLI if needed
from .cli import main as cli

# Define what gets imported with 'from update_metadata import *'
__all__ = [
    # Version
    '__version__',

    # Core functions
    'read_file',
    'write_file',
    'parse_metadata',
    'extract_metadata',
    'format_metadata',
    'add_or_update_metadata',
    'remove_metadata',
    'get_content_without_metadata',
    'analyze_document_changes',
    'increment_version',
    'get_author_info',
    'determine_author',
    'get_git_author',
    'get_git_contributors',
    'get_system_author',
    'get_file_system_author',
    'is_git_repository',
    'find_markdown_files',
    'load_ignore_patterns',
    'should_ignore',
    'process_file',
    'process_bulk',
    'create_ignore_file',
    'get_project_status',
    'generate_project_report',

    # CLI
    'cli',
]

# Package metadata
__author__ = "we256681@gmail.com"
__license__ = "MIT"
__status__ = "Development"
