"""
引用文献統一化パーサーモジュール

様々な形式で記載された引用文献を統一されたフォーマットに変換し、
リンク付き引用からは対応表を生成するパーサーシステム。
"""

from .data_structures import (
    CitationMatch,
    CitationResult,
    LinkEntry,
    ProcessingStats,
    ProcessingError,
    PatternConfig
)
from .exceptions import (
    CitationParserError,
    PatternDetectionError,
    FormatConversionError,
    LinkExtractionError
)
from .citation_parser import CitationParser
from .pattern_detector import PatternDetector
from .format_converter import FormatConverter
from .link_extractor import LinkExtractor
from .config_manager import ConfigManager

__version__ = "1.0.0"
__author__ = "ObsClippingsManager"

__all__ = [
    # Main classes
    'CitationParser',
    'PatternDetector', 
    'FormatConverter',
    'LinkExtractor',
    'ConfigManager',
    
    # Data structures
    'CitationMatch',
    'CitationResult',
    'LinkEntry',
    'ProcessingStats',
    'ProcessingError',
    'PatternConfig',
    
    # Exceptions
    'CitationParserError',
    'PatternDetectionError',
    'FormatConversionError',
    'LinkExtractionError'
] 