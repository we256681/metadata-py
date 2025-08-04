from update_metadata.core import (
    find_markdown_files,
    process_file,
    process_bulk,
    generate_project_report,
    create_ignore_file,
    load_ignore_patterns,
)
import sys
import os
import argparse
from typing import List, Dict, Any


def main():
    """Main CLI entry point."""
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
    args = parser.parse_args()

    # Ensure all commands have a verbose attribute
    if not hasattr(args, 'verbose'):
        args.verbose = False

    # Handle different commands
    if args.command == 'update':
        return handle_update_command(args)
    elif args.command == 'report':
        return handle_report_command(args)
    elif args.command == 'init-mdignore':
        return handle_init_command(args)
    else:
        parser.error(f"Unknown command: {args.command}")


def handle_update_command(args):
    """Handle the update command."""
    # Parse metadata from --set arguments
    new_metadata = {}
    if args.set:
        for item in args.set:
            if '=' not in item:
                print(f"Error: Invalid metadata format: {item}. Use KEY=VALUE format.")
                return 1
            key, value = item.split('=', 1)
            new_metadata[key.strip()] = value.strip()

    # Determine files to process
    if args.files:
        # Process specific files
        files_to_process = []
        for filepath in args.files:
            if not os.path.exists(filepath):
                print(f"Warning: File not found: {filepath}")
                continue
            if not filepath.lower().endswith(('.md', '.markdown')):
                print(f"Warning: Not a markdown file: {filepath}")
                continue
            files_to_process.append(filepath)

        if not files_to_process:
            print("No valid markdown files to process.")
            return 1

        # Process individual files
        modified_count = 0
        for filepath in files_to_process:
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

    else:
        # Bulk processing mode
        root_dir = "."

        # Handle ignore patterns
        ignore_patterns = None
        if args.ignore:
            ignore_patterns = load_ignore_patterns(args.ignore_file)
            ignore_patterns.extend(args.ignore)

        # Confirmation prompt
        if not args.yes and not args.dry_run:
            markdown_files = find_markdown_files(
                root_dir,
                ignore_patterns or load_ignore_patterns(args.ignore_file),
                not args.exclude_root,
                args.verbose
            )
            print(f"Found {len(markdown_files)} markdown files to process.")
            if not confirm("Do you want to continue?"):
                print("Operation cancelled.")
                return 0

        # Process files
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
            print(f"\nDry run complete. Would process {total_files} files, modify {modified_files}.")
        else:
            print(f"\nBulk processing completed: {modified_files}/{total_files} files modified")

    return 0


def handle_report_command(args):
    """Handle the report command."""
    try:
        report = generate_project_report(".", args.output if hasattr(args, 'output') else None)
        if not hasattr(args, 'output') or not args.output:
            print(report)
        return 0
    except Exception as e:
        print(f"Error generating report: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def handle_init_command(args):
    """Handle the init-mdignore command."""
    try:
        mdignore_path = ".mdignore"

        # Check if file exists and force flag
        if os.path.exists(mdignore_path) and not getattr(args, 'force', False):
            print(f"File {mdignore_path} already exists. Use --force to overwrite.")
            return 1

        create_ignore_file(mdignore_path)
        return 0
    except Exception as e:
        print(f"Error creating .mdignore file: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


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


if __name__ == '__main__':
    sys.exit(main())