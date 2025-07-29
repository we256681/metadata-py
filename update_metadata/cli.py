"""
Command-line interface for the metadata management tool.

This module provides the command-line interface for the metadata management tool,
allowing users to add, update, or remove metadata blocks in markdown files.
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Optional, Any
from pathlib import Path

from .core import (
    process_bulk,
    load_ignore_patterns,
    create_ignore_file,
    get_project_status,
    generate_project_report,
    find_markdown_files,
    process_file
)

def parse_args(args: List[str] = None) -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Args:
        args: List of command line arguments (defaults to sys.argv[1:])
        
    Returns:
        Parsed arguments with all required attributes
    """
    parser = argparse.ArgumentParser(
        description="Manage metadata in markdown files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add/update metadata in all markdown files in the current directory
  metadata-py update --set author="John Doe" --set version=1.0.0
  
  # Remove metadata from a specific file
  metadata-py update --remove test.md
  
  # Process all markdown files except those in the docs/ directory
  metadata-py update --ignore "docs/*" --set author="John Doe"
  
  # Create a report about markdown files in the project
  metadata-py report
  
  # Create a default .mdignore file
  metadata-py init-mdignore"""
    )
    
    # Common arguments for all commands
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show verbose output including author detection details'
    )
    
    # Subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute', required=True)
    
    # Update command
    update_parser = subparsers.add_parser(
        'update',
        help='Update metadata in markdown files',
        parents=[common_parser]
    )
    update_parser.add_argument(
        'files',
        nargs='*',
        help='Markdown files to process (default: all in current directory)'
    )
    update_parser.add_argument(
        '--set',
        '-s',
        action='append',
        metavar='KEY=VALUE',
        default=[],
        help='Set metadata key-value pairs (can be used multiple times)'
    )
    update_parser.add_argument(
        '--remove',
        '-r',
        action='store_true',
        default=False,
        help='Remove metadata from files'
    )
    update_parser.add_argument(
        '--overwrite',
        '-o',
        action='store_true',
        default=False,
        help='Completely overwrite existing metadata instead of updating'
    )
    update_parser.add_argument(
        '--dry-run',
        '-n',
        action='store_true',
        default=False,
        help='Show what would be done without making changes'
    )
    update_parser.add_argument(
        '--ignore',
        '-i',
        action='append',
        default=[],
        help='Patterns to ignore (can be used multiple times)'
    )
    update_parser.add_argument(
        '--ignore-file',
        help='Path to ignore file (default: .gitignore if exists)'
    )
    update_parser.add_argument(
        '--exclude-root',
        action='store_true',
        default=False,
        help='Exclude files in the root directory when bulk processing'
    )
    update_parser.add_argument(
        '--no-auto-author',
        action='store_true',
        default=False,
        help='Disable automatic author detection'
    )
    update_parser.add_argument(
        '--yes',
        '-y',
        action='store_true',
        default=False,
        help='Skip confirmation prompts'
    )
    
    # Report command
    report_parser = subparsers.add_parser(
        'report',
        help='Generate a report about markdown files',
        parents=[common_parser]
    )
    report_parser.add_argument(
        '--output',
        '-o',
        help='Output file for the report (default: print to stdout)'
    )
    
    # Init command
    init_parser = subparsers.add_parser(
        'init-mdignore',
        help='Create a default .mdignore file',
        parents=[common_parser]
    )
    init_parser.add_argument(
        '--force',
        '-f',
        action='store_true',
        default=False,
        help='Overwrite existing .mdignore file'
    )
    
    # Parse arguments
    if args is None:
        args = sys.argv[1:]
    
    parsed_args = parser.parse_args(args)
    
    # Ensure all commands have a verbose attribute
    if not hasattr(parsed_args, 'verbose'):
        parsed_args.verbose = False
    
    # Add default values for update command attributes
    if parsed_args.command == 'update':
        if not hasattr(parsed_args, 'files'):
            parsed_args.files = []
        if not hasattr(parsed_args, 'set'):
            parsed_args.set = []
        if not hasattr(parsed_args, 'remove'):
            parsed_args.remove = False
        if not hasattr(parsed_args, 'overwrite'):
            parsed_args.overwrite = False
        if not hasattr(parsed_args, 'dry_run'):
            parsed_args.dry_run = False
        if not hasattr(parsed_args, 'ignore'):
            parsed_args.ignore = []
        if not hasattr(parsed_args, 'exclude_root'):
            parsed_args.exclude_root = False
        if not hasattr(parsed_args, 'no_auto_author'):
            parsed_args.no_auto_author = False
        if not hasattr(parsed_args, 'yes'):
            parsed_args.yes = False
    
    return parsed_args


def confirm(prompt: str = 'Continue?', default: bool = False) -> bool:
    """
    Ask for user confirmation.
    
    Args:
        prompt: The prompt to display
        default: The default value if the user just presses Enter
        
    Returns:
        bool: True if the user confirmed, False otherwise
    """
    if default:
        prompt = f"{prompt} [Y/n] "
    else:
        prompt = f"{prompt} [y/N] "
    
    while True:
        try:
            response = input(prompt).strip().lower()
            if not response:
                return default
            if response in ('y', 'yes'):
                return True
            if response in ('n', 'no'):
                return False
        except (KeyboardInterrupt, EOFError):
            print()
            return False


def parse_metadata_args(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Parse metadata arguments into a dictionary.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Dictionary of metadata key-value pairs
    """
    metadata = {}
    
    # Parse --set key=value pairs
    if hasattr(args, 'set') and args.set:
        for item in args.set:
            if '=' in item:
                key, value = item.split('=', 1)
                metadata[key.strip()] = value.strip()
    
    return metadata


def handle_update_command(args: argparse.Namespace) -> int:
    """
    Handle the 'update' command.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    # Parse metadata arguments
    metadata = parse_metadata_args(args)
    
    # Check if we have anything to do
    if not args.remove and not metadata and not args.overwrite:
        print("No metadata specified to add/update. Use --help for usage.", file=sys.stderr)
        return 1
    
    try:
        # Get ignore patterns
        ignore_patterns = args.ignore or []
        
        # Check if we have any files to process
        if not args.files and not args.yes:
            # If no files specified, confirm processing all files
            files = find_markdown_files(
                root_dir='.',
                ignore_patterns=ignore_patterns,
                ignore_file=args.ignore_file,
                exclude_root=args.exclude_root
            )
            if not files:
                print("No markdown files found to process.", file=sys.stderr)
                return 1
                
            print(f"Found {len(files)} markdown files to process.")
            if not confirm("Do you want to continue?", default=True):
                print("Operation cancelled.")
                return 0
        
        # Process files
        if args.files:
            # Process specific files
            processed = 0
            modified = 0
            
            for file_path in args.files:
                if not os.path.exists(file_path):
                    print(f"Error: File not found: {file_path}", file=sys.stderr)
                    continue
                    
                if args.verbose:
                    print(f"Processing {file_path}...")
                
                try:
                    # Process the file
                    result = process_file(
                        filepath=file_path,
                        new_metadata=metadata,
                        remove=args.remove,
                        overwrite=args.overwrite,
                        dry_run=args.dry_run,
                        auto_author=not args.no_auto_author,
                        verbose=args.verbose
                    )
                    
                    processed += 1
                    if result and not args.dry_run:
                        modified += 1
                        if args.verbose:
                            print(f"  Updated {file_path}")
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}", file=sys.stderr)
                    if args.verbose:
                        import traceback
                        traceback.print_exc()
                    return 1
            
            if args.dry_run:
                print(f"\nDry run complete. Would process {processed} files, modify {modified}.")
            else:
                print(f"\nProcessed {processed} files, modified {modified}.")
                
        else:
            # Process all markdown files
            total_files, modified_files = process_bulk(
                root_dir='.',
                new_metadata=metadata,
                remove=args.remove,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
                ignore_patterns=ignore_patterns,
                ignore_file=args.ignore_file,
                exclude_root=args.exclude_root,
                auto_author=not args.no_auto_author,
                verbose=args.verbose
            )
            
            if args.dry_run:
                print(f"\nDry run complete. Would process {total_files} files, modify {modified_files}.")
            else:
                print(f"\nProcessed {total_files} files, modified {modified_files}.")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_report_command(args: argparse.Namespace) -> int:
    """
    Handle the 'report' command.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    # Generate the report
    report = generate_project_report(root_dir='.')
    
    # Output the report
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Report saved to {args.output}")
        except Exception as e:
            print(f"Error saving report to {args.output}: {e}", file=sys.stderr)
            return 1
    else:
        print(report)
    
    return 0


def handle_init_mdignore_command(args: argparse.Namespace) -> int:
    """
    Handle the 'init-mdignore' command.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    ignore_file = '.mdignore'
    
    if os.path.exists(ignore_file) and not args.force:
        print(f"Error: {ignore_file} already exists. Use --force to overwrite.", file=sys.stderr)
        return 1
    
    try:
        create_ignore_file(ignore_file)
        print(f"Created {ignore_file} with default patterns.")
        return 0
    except Exception as e:
        print(f"Error creating {ignore_file}: {e}", file=sys.stderr)
        return 1


def main(args: List[str] = None) -> int:
    """
    Main entry point for the CLI.
    
    Args:
        args: Command line arguments (defaults to sys.argv[1:])
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    try:
        # Parse command line arguments
        args = parse_args(args)
        
        # Set up verbose output
        if args.verbose:
            import logging
            logging.basicConfig(level=logging.INFO)
        
        # Dispatch to the appropriate handler
        if args.command == 'update':
            return handle_update_command(args)
        elif args.command == 'report':
            return handle_report_command(args)
        elif args.command == 'init-mdignore':
            return handle_init_mdignore_command(args)
        else:
            # This should never happen as argparse should handle it
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args and args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())