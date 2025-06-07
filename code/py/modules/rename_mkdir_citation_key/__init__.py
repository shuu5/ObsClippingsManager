"""
Rename & MkDir Citation Keyモジュール

Markdownファイルの整理とBibTeX参照キーとの連携を行う機能を提供します。
研究ノートやクリッピングファイルの管理を効率化し、学術文献との関連付けを自動化します。
"""

# Version information
__version__ = "2.0.0"
__author__ = "ObsClippingsManager Team"

# Import main classes and functions
from .file_matcher import FileMatcher, match_files_to_citations, calculate_similarity
from .markdown_manager import MarkdownManager, get_markdown_files, move_file_to_citation_dir
from .directory_organizer import DirectoryOrganizer, create_citation_directory, cleanup_empty_directories

# Import exceptions
from .exceptions import (
    RenameOrganizeError,
    FileMatchingError,
    DirectoryOperationError
)

__all__ = [
    # Classes
    'FileMatcher',
    'MarkdownManager',
    'DirectoryOrganizer',
    
    # Functions
    'match_files_to_citations',
    'calculate_similarity',
    'get_markdown_files',
    'move_file_to_citation_dir',
    'create_citation_directory',
    'cleanup_empty_directories',
    
    # Exceptions
    'RenameOrganizeError',
    'FileMatchingError',
    'DirectoryOperationError',
] 