"""
共通モジュール

ObsClippingsManager統合システムで使用される共通機能を提供します。
"""

# Version information
__version__ = "2.0.0"
__author__ = "ObsClippingsManager Team"

# Import main classes and functions
from .bibtex_parser import BibTeXParser, parse_bibtex_file, normalize_title, extract_doi_from_entry
from .config_manager import ConfigManager, DEFAULT_INTEGRATED_CONFIG
from .logger import IntegratedLogger
from .claude_api_client import ClaudeAPIClient
from .utils import (
    safe_file_operation, 
    create_directory_if_not_exists, 
    normalize_text_for_comparison,
    escape_filename,
    ProgressTracker,
    validate_doi,
    validate_citation_key
)

# Common exceptions
from .exceptions import (
    ObsClippingsError,
    ConfigError,
    BibTeXParseError,
    FileOperationError,
    ValidationError
)

__all__ = [
    # Classes
    'BibTeXParser',
    'ConfigManager',
    'IntegratedLogger',
    'ClaudeAPIClient',
    'ProgressTracker',
    
    # Functions
    'parse_bibtex_file',
    'normalize_title',
    'extract_doi_from_entry',
    'safe_file_operation',
    'create_directory_if_not_exists',
    'normalize_text_for_comparison',
    'escape_filename',
    'validate_doi',
    'validate_citation_key',
    
    # Constants
    'DEFAULT_INTEGRATED_CONFIG',
    
    # Exceptions
    'ObsClippingsError',
    'ConfigError',
    'BibTeXParseError',
    'FileOperationError',
    'ValidationError',
] 