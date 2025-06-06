"""
ObsClippingsManager モジュールパッケージ - v2.0 統合システム
"""

__version__ = "2.0.0"
__author__ = "ObsClippingsManager Team"

# 新しいモジュラーアーキテクチャ
from .shared import *
from .citation_fetcher import *
from .rename_mkdir_citation_key import *
from .workflows import *

__all__ = [
    # Shared modules
    'ConfigManager',
    'IntegratedLogger',
    'BibTeXParser',
    
    # Citation fetcher
    'CrossRefClient',
    'OpenCitationsClient',
    'ReferenceFormatter',
    'FallbackStrategy',
    
    # File organization
    'FileMatcher',
    'MarkdownManager',
    'DirectoryOrganizer',
    
    # Workflows
    'CitationWorkflow',
    'OrganizationWorkflow',
    'WorkflowManager',
    'WorkflowType'
] 