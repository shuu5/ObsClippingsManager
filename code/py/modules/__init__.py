"""
ObsClippingsManager モジュールパッケージ - v3.0 統合システム
"""

__version__ = "3.0.0"
__author__ = "ObsClippingsManager Team"

# 新しいモジュラーアーキテクチャ
from .shared import *
from .citation_fetcher import *
from .rename_mkdir_citation_key import *
from .workflows import *
from .ai_citation_support import *

__all__ = [
    # 共有モジュール
    'ConfigManager',
    'IntegratedLogger',
    'BibTeXParser',
    'StatusManager',
    'ProcessStatus',
    
    # 引用文献取得モジュール
    'CrossRefClient',
    'OpenCitationsClient',
    'ReferenceFormatter',
    'FallbackStrategy',
    'CitationFetcher',
    
    # ファイル整理モジュール
    'FileMatcher',
    'MarkdownManager',
    'DirectoryOrganizer',
    
    # ワークフローモジュール
    'IntegratedWorkflow',
    'OrganizationWorkflow',
    'SyncCheckWorkflow',
    'CitationWorkflow',
    'AIMappingWorkflow',
    
    # AI理解支援モジュール
    'CitationMappingEngine',
    'CitationResolver',
    'AIAssistantFileGenerator'
] 