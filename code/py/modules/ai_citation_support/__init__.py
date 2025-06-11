"""
AI理解支援引用文献統合モジュール v4.0

AIアシスタント（ChatGPT、Claude等）が引用文献を完全に理解できるよう支援する
統合ファイル生成機能を提供します。

主要機能:
- 軽量引用マッピング機能
- AI用統合ファイル生成機能  
- 動的引用解決機能
"""

from .data_structures import (
    CitationMapping,
    CitationInfo,
    AIReadableDocument
)

from .citation_mapping_engine import CitationMappingEngine
from .ai_assistant_file_generator import AIAssistantFileGenerator
from .citation_resolver import CitationResolver

__version__ = "4.0.0"
__all__ = [
    "CitationMapping",
    "CitationInfo", 
    "AIReadableDocument",
    "CitationMappingEngine",
    "AIAssistantFileGenerator",
    "CitationResolver"
] 