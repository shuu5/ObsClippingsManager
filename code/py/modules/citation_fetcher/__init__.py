"""
Citation Fetcherモジュール

学術論文の引用文献を自動取得し、BibTeX形式で出力する機能を提供します。
CrossRef APIをメインとし、失敗時にOpenCitations APIをフォールバックとして使用します。
"""

# Version information
__version__ = "2.0.0"
__author__ = "ObsClippingsManager Team"

# Import main classes
from .crossref_client import CrossRefClient
from .opencitations_client import OpenCitationsClient
from .reference_formatter import ReferenceFormatter
from .fallback_strategy import FallbackStrategy
from .sync_integration import SyncIntegration

# Import exceptions
from .exceptions import (
    CitationFetcherError,
    APIRequestError,
    DataParsingError,
    BibTeXConversionError
)

__all__ = [
    # Classes
    'CrossRefClient',
    'OpenCitationsClient',
    'ReferenceFormatter',
    'FallbackStrategy',
    'SyncIntegration',
    
    # Exceptions
    'CitationFetcherError',
    'APIRequestError',
    'DataParsingError',
    'BibTeXConversionError',
] 