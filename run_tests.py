#!/usr/bin/env python3
"""
Test runner for the filter plugins.
Run this script from the ansible directory.
"""

import os
import sys
import unittest

# Add the current directory to Python path so imports work correctly
script_dir = os.path.dirname(os.path.abspath(__file__))
ansible_dir = os.path.dirname(script_dir)
sys.path.insert(0, ansible_dir)

if __name__ == '__main__':
    # Discover and run all tests in the tests directory
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
