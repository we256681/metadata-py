#!/usr/bin/env python3
"""
Test script for the metadata-py CLI tool.

This script tests the main functionality of the metadata management tool.
"""

import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add the package directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from update_metadata.cli import main as cli_main


class TestMetadataCLI(unittest.TestCase):
    """Test cases for the metadata CLI tool."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.sample_file = os.path.join(self.test_dir, 'test.md')
        
        # Create a sample markdown file
        with open(self.sample_file, 'w', encoding='utf-8') as f:
            f.write("# Test Document\n\nThis is a test document.")
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _run_cli(self, args):
        """Helper method to run the CLI with given arguments."""
        with patch('sys.argv', ['metadata-py'] + args):
            return cli_main()
    
    def test_update_metadata(self):
        """Test updating metadata with the CLI."""
        # Test adding author and version
        result = self._run_cli([
            'update',
            '--set', 'author=Test User',
            '--set', 'version=1.0.0',
            '--yes',
            self.sample_file
        ])
        self.assertEqual(result, 0)
        
        # Verify the file was modified
        with open(self.sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check for JSON metadata block
            self.assertIn('"author": "Test User"', content)
            self.assertIn('"version": "1.0.0"', content)
            self.assertIn('"updated_at"', content)
            self.assertIn('<!-- METADATA', content)
    
    def test_remove_metadata(self):
        """Test removing metadata with the CLI."""
        # First add some metadata
        self.test_update_metadata()
        
        # Then remove it
        result = self._run_cli([
            'update',
            '--remove',
            '--yes',
            self.sample_file
        ])
        self.assertEqual(result, 0)
        
        # Verify the metadata was removed
        with open(self.sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertNotIn('"author": "Test User"', content)
    
    def test_dry_run(self):
        """Test dry run mode."""
        result = self._run_cli([
            'update',
            '--set', 'author=Test User',
            '--dry-run',
            '--yes',
            self.sample_file
        ])
        self.assertEqual(result, 0)
        
        # Verify the file was not modified
        with open(self.sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertNotIn('"author": "Test User"', content)
    
    def test_init_mdignore(self):
        """Test initializing .mdignore file."""
        # Change to test directory to create .mdignore there
        original_dir = os.getcwd()
        os.chdir(self.test_dir)
        
        try:
            mdignore_path = os.path.join(self.test_dir, '.mdignore')
            
            # Run init-mdignore command
            result = self._run_cli([
                'init-mdignore',
                '--force'
            ])
            self.assertEqual(result, 0)
            
            # Verify the file was created
            self.assertTrue(os.path.exists(mdignore_path))
            
            # Verify the default content
            with open(mdignore_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn('node_modules', content)
                self.assertIn('__pycache__', content)
                self.assertIn('.git', content)
        finally:
            # Restore original directory
            os.chdir(original_dir)


if __name__ == '__main__':
    unittest.main()
