"""
Core functionality for metadata management in markdown files.

This module provides the main functionality for adding, updating, and removing
metadata blocks in markdown files, including version control integration and
author detection.
"""

import os
import re
import json
import hashlib
import argparse
import subprocess
import getpass
import fnmatch
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

try:
    from packaging import version
except ImportError:
    import subprocess
    import sys

    def install_package(package):
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

    try:
        install_package("packaging")
        from packaging import version
    except Exception as e:
        print("Warning: Could not install packaging module. Using fallback version comparison.")

# Default metadata template
DEFAULT_METADATA = {
    "created_at": "",
    "updated_at": "",
    "author": "",
    "version": "1.0.0"
}

# Default ignore patterns
DEFAULT_IGNORE_PATTERNS = [
    "node_modules",
    ".git",
    ".vscode",
    ".idea",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "Thumbs.db",
    "*.tmp",
    "*.temp",
    ".env",
    ".env.local",
    "dist",
    "build",
    "target",
    "*.log"
]

# Regular expression to match metadata blocks
METADATA_PATTERN = re.compile(
    r'<!--\s*METADATA\s*\n([\s\S]*?)\n-->\s*$',
    re.IGNORECASE | re.MULTILINE
)


def load_ignore_patterns(ignore_file: Optional[str] = None) -> List[str]:
    """
    Load ignore patterns from file or use defaults.

    Args:
        ignore_file: Path to ignore file (like .gitignore format)

    Returns:
        List of ignore patterns
    """
    patterns = DEFAULT_IGNORE_PATTERNS.copy()

    # Try to load from .gitignore if no specific file provided
    if ignore_file is None:
        ignore_file = '.gitignore'

    if os.path.exists(ignore_file):
        try:
            with open(ignore_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except Exception as e:
            print(f"Warning: Could not read ignore file {ignore_file}: {e}")

    return patterns


def should_ignore(filepath: str, ignore_patterns: List[str], project_root: str = ".") -> bool:
    """
    Check if a file should be ignored based on patterns.

    Args:
        filepath: Path to check
        ignore_patterns: List of ignore patterns
        project_root: Root directory of the project

    Returns:
        True if file should be ignored
    """
    # Convert to relative path from project root
    try:
        rel_path = os.path.relpath(filepath, project_root)
    except ValueError:
        rel_path = filepath

    # Normalize path separators
    rel_path = rel_path.replace('\\', '/')

    for pattern in ignore_patterns:
        # Remove leading slash if present
        pattern = pattern.lstrip('/')

        # Check if pattern matches the relative path or any part of it
        if fnmatch.fnmatch(rel_path, pattern):
            return True

        # Check if any parent directory matches the pattern
        path_parts = rel_path.split('/')
        for i in range(len(path_parts)):
            partial_path = '/'.join(path_parts[:i+1])
            if fnmatch.fnmatch(partial_path, pattern):
                return True

            # Also check just the directory name
            if fnmatch.fnmatch(path_parts[i], pattern):
                return True

    return False


def find_markdown_files(
    root_dir: str = ".",
    ignore_patterns: Optional[List[str]] = None,
    include_root: bool = True,
    verbose: bool = False
) -> List[str]:
    """
    Find all markdown files in the project, optionally including root files.

    Args:
        root_dir: Root directory to search
        ignore_patterns: Patterns to ignore
        include_root: Whether to include files in the root directory
        verbose: Whether to show verbose output

    Returns:
        List of markdown file paths
    """
    if ignore_patterns is None:
        ignore_patterns = DEFAULT_IGNORE_PATTERNS

    markdown_files = []

    for root, dirs, files in os.walk(root_dir):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if not should_ignore(
            os.path.join(root, d), ignore_patterns, root_dir
        )]

        for file in files:
            if file.lower().endswith(('.md', '.markdown')):
                filepath = os.path.join(root, file)

                # Skip if this file should be ignored
                if should_ignore(filepath, ignore_patterns, root_dir):
                    if verbose:
                        print(f"Ignoring: {filepath}")
                    continue

                # If not including root files, skip files in root directory
                if not include_root and os.path.dirname(filepath) == root_dir:
                    if verbose:
                        print(f"Skipping root file: {filepath}")
                    continue

                markdown_files.append(filepath)

    return sorted(markdown_files)


def get_git_author(filepath: str) -> Optional[str]:
    """
    Get the author of the last commit that modified this file.

    Returns:
        str: Git author name and email, or None if not available
    """
    try:
        # Get the last commit author for this specific file
        result = subprocess.run([
            'git', 'log', '-1', '--pretty=format:%an <%ae>', '--', filepath
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

        # Fallback: get current git user config
        name_result = subprocess.run([
            'git', 'config', 'user.name'
        ], capture_output=True, text=True, timeout=5)

        email_result = subprocess.run([
            'git', 'config', 'user.email'
        ], capture_output=True, text=True, timeout=5)

        if name_result.returncode == 0 and email_result.returncode == 0:
            name = name_result.stdout.strip()
            email = email_result.stdout.strip()
            if name and email:
                return f"{name} <{email}>"

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass

    return None


def get_git_contributors(filepath: str) -> List[str]:
    """
    Get all contributors who have modified this file.

    Returns:
        List of contributor names and emails
    """
    try:
        result = subprocess.run([
            'git', 'log', '--pretty=format:%an <%ae>', '--follow', '--', filepath
        ], capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            contributors = list(set(result.stdout.strip().split('\n')))
            return [c for c in contributors if c.strip()]

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass

    return []


def is_git_repository(path: str) -> bool:
    """Check if the given path is inside a Git repository."""
    try:
        result = subprocess.run([
            'git', 'rev-parse', '--git-dir'
        ], cwd=os.path.dirname(os.path.abspath(path)),
           capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        return False


def get_system_author() -> str:
    """
    Get author information from system environment.

    Returns:
        str: System username or environment-based author info
    """
    # Try to get from environment variables first
    author_name = os.environ.get('AUTHOR_NAME') or os.environ.get('USER_NAME')
    author_email = os.environ.get('AUTHOR_EMAIL') or os.environ.get('USER_EMAIL')

    if author_name and author_email:
        return f"{author_name} <{author_email}>"
    elif author_name:
        return author_name

    # Fallback to system username
    try:
        username = getpass.getuser()
        return username
    except Exception:
        return "Unknown"


def get_file_system_author(filepath: str) -> Optional[str]:
    """
    Get file owner information from the file system.

    Returns:
        str: File owner username or None if not available
    """
    try:
        import pwd
        stat_info = os.stat(filepath)
        owner = pwd.getpwuid(stat_info.st_uid).pw_name
        return owner
    except (ImportError, KeyError, OSError):
        return None


def determine_author(filepath: str, prefer_git: bool = True) -> str:
    """
    Determine the author using multiple methods in order of preference.

    Args:
        filepath: Path to the file
        prefer_git: Whether to prefer Git information over system info

    Returns:
        str: Author information
    """
    authors = []

    # Method 1: Git information (if in a git repo and prefer_git is True)
    if prefer_git and is_git_repository(filepath):
        git_author = get_git_author(filepath)
        if git_author:
            authors.append(("Git (last commit)", git_author))

        # Also get all contributors for reference
        contributors = get_git_contributors(filepath)
        if contributors:
            authors.append(("Git (all contributors)", ", ".join(contributors[:3])))  # Limit to first 3

    # Method 2: System environment
    system_author = get_system_author()
    if system_author and system_author != "Unknown":
        authors.append(("System environment", system_author))

    # Method 3: File system owner
    fs_author = get_file_system_author(filepath)
    if fs_author:
        authors.append(("File system owner", fs_author))

    # Return the first available author, or fallback
    if authors:
        return authors[0][1]  # Return the author string from the first method

    return "Unknown"


def get_author_info(filepath: str, verbose: bool = False) -> Dict[str, str]:
    """
    Get comprehensive author information for a file.

    Args:
        filepath: Path to the file
        verbose: Whether to return detailed information

    Returns:
        Dict with author information
    """
    info = {}

    # Primary author (best available method)
    info['author'] = determine_author(filepath)

    if verbose:
        # Git information
        if is_git_repository(filepath):
            info['git_last_author'] = get_git_author(filepath)
            info['git_contributors'] = get_git_contributors(filepath)

        # System information
        info['system_author'] = get_system_author()
        info['file_owner'] = get_file_system_author(filepath)

    return info


def read_file(filepath: str) -> str:
    """Read the content of a file with proper encoding handling."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Fallback to system default encoding if UTF-8 fails
        with open(filepath, 'r') as f:
            return f.read()


def write_file(filepath: str, content: str) -> None:
    """Write content to a file with UTF-8 encoding."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def parse_metadata(metadata_str: str) -> Dict:
    """Parse metadata string into a dictionary."""
    metadata = DEFAULT_METADATA.copy()
    if not metadata_str.strip():
        return metadata

    try:
        # Try to parse as JSON first
        parsed = json.loads(metadata_str)
        if isinstance(parsed, dict):
            metadata.update(parsed)
    except json.JSONDecodeError:
        # Fallback to simple key-value parsing
        for line in metadata_str.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip().lower()] = value.strip()

    return metadata


def extract_metadata(content: str) -> Tuple[str, Optional[Dict]]:
    """Extract metadata block from content if it exists."""
    if not content:
        return content, None

    match = METADATA_PATTERN.search(content)
    if not match:
        return content, None

    try:
        metadata_str = match.group(1).strip()
        metadata = parse_metadata(metadata_str)

        # Remove the metadata block from content
        content_without_metadata = content[:match.start()] + content[match.end():]
        return content_without_metadata, metadata
    except Exception as e:
        print(f"Warning: Error extracting metadata: {str(e)}")
        return content, None


def format_metadata(metadata: Dict) -> str:
    """Format metadata dictionary into a string."""
    # Ensure required fields are present
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if not metadata.get('created_at'):
        metadata['created_at'] = now
    metadata['updated_at'] = now

    # Convert to pretty-printed JSON
    return json.dumps(metadata, indent=2, ensure_ascii=False)


def analyze_document_changes(old_content: str, new_content: str) -> str:
    """
    Analyze changes between old and new content to determine version bump type.

    Returns:
        str: The type of version bump needed ('major', 'medium', 'minor')
    """
    # Извлекаем все заголовки из старого и нового содержимого
    import re
    def get_headings(text):
        headings = re.findall(r'^(#{1,6})\s+(.+)$', text, re.MULTILINE)
        # Убираем лишние пробелы и нормализуем
        return [(l, h.strip()) for l, h in headings]

    old_headings = get_headings(old_content)
    new_headings = get_headings(new_content)

    # Для отладки: печать заголовков если verbose
    import os
    if os.environ.get('METADATA_PY_VERBOSE') == '1':
        print('OLD MAIN:', [h for l, h in old_headings if l == '#'])
        print('NEW MAIN:', [h for l, h in new_headings if l == '#'])
        print('OLD SUB:', [(l, h) for l, h in old_headings if l != '#'])
        print('NEW SUB:', [(l, h) for l, h in new_headings if l != '#'])

    # Проверяем изменения в заголовках первого уровня (major)
    old_main = [h for l, h in old_headings if l == '#']
    new_main = [h for l, h in new_headings if l == '#']
    if old_main != new_main:
        return 'major'

    # Проверяем изменения в подзаголовках (medium)
    old_sub = [(l, h) for l, h in old_headings if l != '#']
    new_sub = [(l, h) for l, h in new_headings if l != '#']
    if old_sub != new_sub:
        return 'medium'

    # Если изменилось только содержимое — minor
    return 'minor'

def increment_version(current_version: str, bump_type: str) -> str:
    """Increment version number based on bump type."""
    if not current_version or current_version == '0.0.0':
        return '0.0.1'

    try:
        from packaging import version as version_parser
        v = version_parser.parse(str(current_version))
        major, minor, patch = v.major, v.minor, v.micro

        if bump_type == 'major':
            return f"{major + 1}.0.0"
        elif bump_type == 'medium':
            return f"{major}.{minor + 1}.0"
        else:  # minor
            return f"{major}.{minor}.{patch + 1}"
    except ImportError:
        # Fallback if packaging is not available
        parts = current_version.split('.')
        while len(parts) < 3:
            parts.append('0')

        if bump_type == 'major':
            return f"{int(parts[0]) + 1}.0.0"
        elif bump_type == 'medium':
            return f"{parts[0]}.{int(parts[1]) + 1}.0"
        else:  # minor
            return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"

def add_or_update_metadata(
    content: str,
    new_metadata: Optional[Dict] = None,
    overwrite: bool = False,
    old_content: Optional[str] = None
) -> str:
    """
    Add or update metadata in the content.

    Args:
        content: The original content of the file
        new_metadata: New metadata fields to add/update
        overwrite: If True, completely replace existing metadata

    Returns:
        Updated content with metadata
    """
    if new_metadata is None:
        new_metadata = {}

    # Remove any existing metadata and get current metadata if it exists
    content_without_metadata, current_metadata = extract_metadata(content)

    # Prepare the metadata to be saved
    if current_metadata and not overwrite:
        # Update existing metadata with new values
        metadata = {**current_metadata, **new_metadata}
    else:
        # Use new metadata, falling back to default values
        metadata = {**DEFAULT_METADATA, **new_metadata}

    # Auto-update version if content changed
    if old_content is not None and old_content != content_without_metadata:
        change_type = analyze_document_changes(old_content, content_without_metadata)
        current_version = metadata.get('version', '0.0.0')
        new_version = increment_version(current_version, change_type)
        import os
        if os.environ.get('METADATA_PY_VERBOSE') == '1':
            # Для отладки: покажем тип изменения, старую и новую версию
            print(f"[VERBOSE] Version bump type: {change_type}")
            print(f"[VERBOSE] Old version: {current_version}, New version: {new_version}")
            # Покажем подзаголовки
            import re
            def get_subheaders(text):
                return [(l, h.strip()) for l, h in re.findall(r'^(#{2,6})\s+(.+)$', text, re.MULTILINE)]
            print(f"[VERBOSE] Old subheaders: {get_subheaders(old_content)}")
            print(f"[VERBOSE] New subheaders: {get_subheaders(content_without_metadata)}")
        metadata['version'] = new_version

    # Format the metadata block
    formatted_metadata = format_metadata(metadata)
    metadata_block = f"""
<!-- METADATA
{formatted_metadata}
-->
""".strip()

    # Add the metadata block to the content
    content_with_metadata = content_without_metadata.rstrip()
    if content_with_metadata and not content_with_metadata.endswith('\n'):
        content_with_metadata += '\n'
    content_with_metadata += '\n\n' + metadata_block + '\n'
    return content_with_metadata


def remove_metadata(content: str) -> str:
    """Remove metadata block from content if it exists."""
    content_without_metadata, _ = extract_metadata(content)
    return content_without_metadata.rstrip() + '\n'


def get_content_without_metadata(content: str) -> str:
    """Return content without the metadata block for comparison."""
    if not content:
        return ""
    # First, try to extract and remove the metadata block
    if isinstance(content, str):
        content_str = content
    else:
        content_str = str(content)

    # Remove the metadata block if it exists
    match = METADATA_PATTERN.search(content_str)
    if match:
        content_str = content_str[:match.start()] + content_str[match.end():]

    # Clean up any extra whitespace
    return content_str.strip()

def calculate_hash(content: str) -> str:
    """Calculate SHA-256 hash of the content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def extract_headers(content: str) -> Set[str]:
    """Extract all headers from markdown content and return their hashes."""
    headers = set()
    # Match markdown headers (lines starting with 1-6 # followed by text)
    header_pattern = r'^(#{1,6})\s+(.+)$'
    for line in content.split('\n'):
        match = re.match(header_pattern, line.strip())
        if match:
            level = len(match.group(1))
            header_text = match.group(2).strip()
            # Store both the level and text to detect changes in header structure
            headers.add(f"{level}:{header_text}")
    return headers

def get_document_fingerprint(content: str) -> Dict:
    """Create a fingerprint of the document with content and header hashes."""
    return {
        'content_hash': calculate_hash(content),
        'headers_hash': calculate_hash('|'.join(sorted(extract_headers(content))))
    }

def process_file(
    filepath: str,
    new_metadata: Optional[Dict] = None,
    remove: bool = False,
    overwrite: bool = False,
    dry_run: bool = False,
    auto_author: bool = True,
    verbose: bool = False
) -> bool:
    """
    Process a single file to add, update, or remove metadata.

    Args:
        filepath: Path to the file to process
        new_metadata: Dictionary of new metadata to add/update
        remove: Whether to remove metadata
        overwrite: Whether to overwrite existing metadata
        dry_run: Whether to perform a dry run
        auto_author: Whether to automatically determine author
        verbose: Whether to show verbose output

    Returns:
        bool: True if the file was modified, False otherwise
    """
    try:
        # Read the file content
        content = read_file(filepath)
        if not isinstance(content, str):
            print(f"Error: Expected string content, got {type(content)}")
            return False

        original_content = content
        content_without_metadata, current_metadata = extract_metadata(content)

        if remove:
            if not current_metadata:
                if verbose:
                    print(f"No metadata found in {filepath}")
                return False
            new_content = content_without_metadata
            action = "Removed metadata from"
            if dry_run:
                print(f"[DRY-RUN] Would remove metadata block from {filepath}")
                if current_metadata:
                    print("--- Old metadata block ---")
                    print(json.dumps(current_metadata, indent=2, ensure_ascii=False))
                    print("--------------------------")
                return True
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"{action} {filepath}")
            return True

        # --- основной блок добавления/обновления метаданных ---
        if new_metadata is None:
            new_metadata = {}

        if auto_author and 'author' not in new_metadata:
            author_info = get_author_info(filepath, verbose)
            new_metadata['author'] = author_info['author']
            if verbose:
                print(f"Auto-detected author for {filepath}: {author_info['author']}")
                if 'git_contributors' in author_info and author_info['git_contributors']:
                    print(f"  All contributors: {', '.join(author_info['git_contributors'][:5])}")

        if current_metadata and not overwrite:
            metadata = {**current_metadata, **new_metadata}
        else:
            metadata = {**DEFAULT_METADATA, **new_metadata}

        current_fingerprint = get_document_fingerprint(content_without_metadata)
        previous_fingerprint = {}
        if current_metadata and '_fingerprint' in current_metadata:
            try:
                previous_fingerprint = json.loads(current_metadata['_fingerprint'])
            except (json.JSONDecodeError, TypeError):
                previous_fingerprint = {}

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if 'created_at' not in metadata or not metadata['created_at']:
            metadata['created_at'] = now

        if (previous_fingerprint and previous_fingerprint.get('content_hash') == current_fingerprint['content_hash']):
            if verbose:
                print(f"No content changes detected in {filepath}")
            if current_metadata == metadata:
                return False

        if previous_fingerprint and previous_fingerprint.get('content_hash') != current_fingerprint['content_hash']:
            current_version = metadata.get('version', '0.0.0')
            old_headers_data = previous_fingerprint.get('headers', '[]')
            try:
                old_headers_list = json.loads(old_headers_data) if isinstance(old_headers_data, str) else old_headers_data
                old_headers = set(old_headers_list) if isinstance(old_headers_list, list) else set()
            except (json.JSONDecodeError, TypeError):
                old_headers = set()
            new_headers = extract_headers(content_without_metadata)
            old_main_headers = {h for h in old_headers if h.startswith('1:')}
            new_main_headers = {h for h in new_headers if h.startswith('1:')}
            if old_main_headers != new_main_headers:
                metadata['version'] = increment_version(current_version, 'major')
                if verbose:
                    print(f"Major changes detected, updating version to {metadata['version']}")
            elif previous_fingerprint.get('headers_hash') != current_fingerprint['headers_hash']:
                metadata['version'] = increment_version(current_version, 'medium')
                if verbose:
                    print(f"Medium changes detected, updating version to {metadata['version']}")
            else:
                metadata['version'] = increment_version(current_version, 'minor')
                if verbose:
                    print(f"Minor changes detected, updating version to {metadata['version']}")
            current_fingerprint['headers'] = json.dumps(list(new_headers))

        metadata['_fingerprint'] = json.dumps(current_fingerprint)
        metadata['updated_at'] = now
        formatted_metadata = format_metadata(metadata)
        metadata_block = f"<!-- METADATA\n{formatted_metadata}\n-->"
        new_content = content_without_metadata.rstrip() + '\n\n' + metadata_block + '\n'

        # Check if metadata actually changed
        if current_metadata:
            # Compare metadata excluding updated_at field for change detection
            old_meta_for_comparison = {k: v for k, v in current_metadata.items() if k != 'updated_at'}
            new_meta_for_comparison = {k: v for k, v in metadata.items() if k != 'updated_at'}
            if old_meta_for_comparison == new_meta_for_comparison:
                if verbose:
                    print(f"No metadata changes to {filepath}")
                return False
        elif not new_metadata:
            # No existing metadata and no new metadata to add
            if verbose:
                print(f"No changes to {filepath}")
            return False
        action = "Updated metadata in"
        if dry_run:
            if not current_metadata:
                print(f"[DRY-RUN] Would add metadata block to {filepath}")
                print("--- New metadata block ---")
                print(metadata_block)
                print("--------------------------")
            else:
                print(f"[DRY-RUN] Would update metadata block in {filepath}")
                print("--- Old metadata block ---")
                print(json.dumps(current_metadata, indent=2, ensure_ascii=False))
                print("--- New metadata block ---")
                print(metadata_block)
                print("--------------------------")
            return True
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"{action} {filepath}")
        return True
    except Exception as e:
        print(f"Error processing {filepath}: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def process_bulk(
    root_dir: str = ".",
    new_metadata: Optional[Dict] = None,
    remove: bool = False,
    overwrite: bool = False,
    dry_run: bool = False,
    auto_author: bool = True,
    verbose: bool = False,
    ignore_patterns: Optional[List[str]] = None,
    include_root: bool = True,
    ignore_file: Optional[str] = None
    ) -> Tuple[int, int]:
    # Load ignore patterns
    if ignore_patterns is None:
        ignore_patterns = load_ignore_patterns(ignore_file)

    # Find all markdown files
    markdown_files = find_markdown_files(
        root_dir, ignore_patterns, include_root, verbose
    )

    if verbose:
        print(f"Found {len(markdown_files)} markdown files to process")
        if not include_root:
            print("Excluding root directory files")

    # Process each file
    modified_count = 0
    for filepath in markdown_files:
        if process_file(
            filepath,
            new_metadata,
            remove,
            overwrite,
            dry_run,
            auto_author,
            verbose
        ):
            modified_count += 1

    return len(markdown_files), modified_count


def main():
    parser = argparse.ArgumentParser(
        description='Manage metadata blocks in markdown files with automatic author detection and bulk processing.'
    )

    # Input sources
    parser.add_argument(
        'files',
        nargs='*',
        help='Specific markdown files to process'
    )
    parser.add_argument(
        '--bulk',
        '-b',
        metavar='DIR',
        help='Process all markdown files in directory tree (default: current directory)'
    )

    # Metadata operations
    parser.add_argument(
        '--set',
        '-s',
        metavar='KEY=VALUE',
        action='append',
        help='Set metadata key-value pairs (e.g., --set author=JohnDoe)'
    )
    parser.add_argument(
        '--remove',
        '-r',
        action='store_true',
        help='Remove metadata block from files'
    )
    parser.add_argument(
        '--overwrite',
        '-o',
        action='store_true',
        help='Completely overwrite existing metadata instead of updating'
    )

    # Processing options
    parser.add_argument(
        '--dry-run',
        '-n',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--no-auto-author',
        action='store_true',
        help='Disable automatic author detection'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show verbose output including author detection details'
    )

    # Bulk processing options
    parser.add_argument(
        '--ignore',
        '-i',
        metavar='PATTERN',
        action='append',
        help='Add ignore patterns (can be used multiple times)'
    )
    parser.add_argument(
        '--ignore-file',
        metavar='FILE',
        help='Path to ignore file (default: .gitignore if exists)'
    )
    parser.add_argument(
        '--exclude-root',
        action='store_true',
        help='Exclude files in the root directory when bulk processing'
    )

    # Info commands
    parser.add_argument(
        '--show-info',
        action='store_true',
        help='Show author information for files without modifying them'
    )
    parser.add_argument(
        '--list-files',
        action='store_true',
        help='List all markdown files that would be processed'
    )

    args = parser.parse_args()


    # Validate arguments
    markdown_files = []
    if args.bulk is not None and not args.files:
        # Bulk processing mode
        root_dir = args.bulk if args.bulk else "."

        # Handle ignore patterns
        ignore_patterns = None
        if args.ignore:
            ignore_patterns = DEFAULT_IGNORE_PATTERNS.copy()
            ignore_patterns.extend(args.ignore)

        # List files mode
        if args.list_files or args.show_info:
            markdown_files = find_markdown_files(
                root_dir,
                ignore_patterns or load_ignore_patterns(args.ignore_file),
                not args.exclude_root,
                args.verbose
            )
        if args.list_files:
            print(f"Found {len(markdown_files)} markdown files:")
            for filepath in sorted(markdown_files):
                print(f"  {filepath}")
            return

        # Show info mode
        if args.show_info:
            print(f"Author information for {len(markdown_files)} markdown files:\n")
            for filepath in sorted(markdown_files):
                try:
                    author_info = get_author_info(filepath, verbose=True)
                    print(f"File: {filepath}")
                    print(f"  Primary author: {author_info['author']}")

                    if args.verbose:
                        if 'git_last_author' in author_info and author_info['git_last_author']:
                            print(f"  Git last author: {author_info['git_last_author']}")
                        if 'git_contributors' in author_info:
                            contributors = author_info['git_contributors'][:3] if author_info['git_contributors'] else []
                            if contributors:
                                print(f"  Git contributors: {', '.join(contributors)}")
                        if 'system_author' in author_info:
                            print(f"  System author: {author_info['system_author']}")
                        if 'file_owner' in author_info and author_info['file_owner']:
                            print(f"  File owner: {author_info['file_owner']}")
                    print()
                except Exception as e:
                    print(f"Error getting info for {filepath}: {e}")
            return

    elif args.files:
        # Single file processing mode
        files_to_process = args.files
    else:
        parser.error("Either specify files or use --bulk option")

    # Parse metadata from --set arguments
    new_metadata = {}
    if args.set:
        for item in args.set:
            if '=' not in item:
                parser.error(f"Invalid metadata format: {item}. Use KEY=VALUE format.")
            key, value = item.split('=', 1)
            new_metadata[key.strip()] = value.strip()

    # Process files
    if args.bulk is not None:
        # Bulk processing
        total_files, modified_files = process_bulk(
            root_dir=root_dir,
            new_metadata=new_metadata,
            remove=args.remove,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            auto_author=not args.no_auto_author,
            verbose=args.verbose,
            ignore_patterns=ignore_patterns,
            include_root=not args.exclude_root,
            ignore_file=args.ignore_file
        )

        if args.dry_run:
            print(f"\nDry run completed: {modified_files}/{total_files} files would be modified")
        else:
            print(f"\nBulk processing completed: {modified_files}/{total_files} files modified")
    else:
        # Single file processing
        modified_count = 0
        for filepath in files_to_process:
            if not os.path.exists(filepath):
                print(f"Warning: File not found: {filepath}")
                continue

            if not filepath.lower().endswith(('.md', '.markdown')):
                print(f"Warning: Not a markdown file: {filepath}")
                continue

            if process_file(
                filepath,
                new_metadata,
                args.remove,
                args.overwrite,
                args.dry_run,
                not args.no_auto_author,
                args.verbose
            ):
                modified_count += 1

        if args.dry_run:
            print(f"\nDry run completed: {modified_count}/{len(files_to_process)} files would be modified")
        else:
            print(f"\nProcessing completed: {modified_count}/{len(files_to_process)} files modified")


if __name__ == '__main__':
    main()


# Дополнительная функция для более гибкого управления игнорированием файлов
def create_ignore_file(filepath: str = ".mdignore", patterns: List[str] = None) -> None:
    # Create a custom ignore file for markdown processing.
    if patterns is None:
        patterns = DEFAULT_IGNORE_PATTERNS.copy()
        patterns.extend([
            "# Markdown processing ignore file",
            "# Add patterns to ignore when processing markdown files",
            "",
            "# Common build/cache directories",
            "*.cache",
            ".pytest_cache",
            ".mypy_cache",
            "",
            "# Documentation build outputs",
            "docs/_build",
            "site/",
            "",
            "# Add your custom patterns below:",
        ])

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            for pattern in patterns:
                f.write(pattern + '\n')
        print(f"Created ignore file: {filepath}")
    except Exception as e:
        print(f"Error creating ignore file {filepath}: {e}")


# Функция для проверки статуса обработки проекта
def get_project_status(root_dir: str = ".", ignore_file: str = None) -> Dict:
    # Get comprehensive status of markdown files in the project.
    ignore_patterns = load_ignore_patterns(ignore_file)
    markdown_files = find_markdown_files(root_dir, ignore_patterns, True, False)

    status = {
        'total_files': len(markdown_files),
        'files_with_metadata': 0,
        'files_without_metadata': 0,
        'authors': set(),
        'versions': {},
        'last_updated': None,
        'files_by_author': {},
        'files_without_author': []
    }

    for filepath in markdown_files:
        try:
            content = read_file(filepath)
            _, metadata = extract_metadata(content)

            if metadata:
                status['files_with_metadata'] += 1

                # Track authors
                author = metadata.get('author', '')
                if author:
                    status['authors'].add(author)
                    if author not in status['files_by_author']:
                        status['files_by_author'][author] = []
                    status['files_by_author'][author].append(filepath)
                else:
                    status['files_without_author'].append(filepath)

                # Track versions
                version = metadata.get('version', '')
                if version:
                    if version not in status['versions']:
                        status['versions'][version] = 0
                    status['versions'][version] += 1

                # Track last updated
                updated_at = metadata.get('updated_at', '')
                if updated_at:
                    if not status['last_updated'] or updated_at > status['last_updated']:
                        status['last_updated'] = updated_at
            else:
                status['files_without_metadata'] += 1
                status['files_without_author'].append(filepath)

        except Exception as e:
            print(f"Warning: Error analyzing {filepath}: {e}")

    # Convert set to list for JSON serialization
    status['authors'] = list(status['authors'])

    return status


# Функция для создания отчета о состоянии проекта
def generate_project_report(root_dir: str = ".", output_file: str = None) -> str:
    # Generate a comprehensive report about the project's markdown files.
    status = get_project_status(root_dir)

    if status['total_files']:
        coverage = (status['files_with_metadata'] / status['total_files']) * 100
    else:
        coverage = 0.0
    report = (
        f"# Markdown Files Metadata Report\n"
        f"\n"
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Project directory: {os.path.abspath(root_dir)}\n"
        f"\n"
        f"## Summary\n"
        f"- Total markdown files: {status['total_files']}\n"
        f"- Files with metadata: {status['files_with_metadata']}\n"
        f"- Files without metadata: {status['files_without_metadata']}\n"
        f"- Coverage: {coverage:.1f}%\n"
        f"\n"
        f"## Authors\n"
        f"Total authors: {len(status['authors'])}\n"
    )

    if status['authors']:
        for author in sorted(status['authors']):
            file_count = len(status['files_by_author'].get(author, []))
            report += f"- {author}: {file_count} files\n"

    report += f"\n## Version Distribution\n"
    for version, count in sorted(status['versions'].items()):
        report += f"- v{version}: {count} files\n"

    if status['files_without_author']:
        report += f"\n## Files Without Author ({len(status['files_without_author'])})\n"
        for filepath in sorted(status['files_without_author']):
            report += f"- {filepath}\n"

    if status['last_updated']:
        report += f"\n## Last Updated\n{status['last_updated']}\n"

    if output_file:
        try:
            write_file(output_file, report)
            print(f"Report saved to: {output_file}")
        except Exception as e:
            print(f"Error saving report: {e}")

    return report