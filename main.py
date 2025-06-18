#!/usr/bin/env python
"""
ObsClippingsManager main entry point.
"""

import sys
from pathlib import Path

# Add code directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from code.py.cli import cli

if __name__ == '__main__':
    cli()