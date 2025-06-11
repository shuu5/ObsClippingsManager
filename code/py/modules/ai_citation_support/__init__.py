"""
AI理解支援引用文献統合モジュール v4.0

AIアシスタント（ChatGPT、Claude等）が引用文献を完全に理解できるよう支援する
YAMLヘッダー統合機能を提供します。

主要機能:
- 軽量引用マッピング機能
- YAMLヘッダー統合機能
- 動的引用解決機能
"""

from .data_structures import (
    CitationMapping,
    CitationInfo
)

from .citation_mapping_engine import CitationMappingEngine
from .citation_resolver import CitationResolver
from .ai_mapping_workflow import AIMappingWorkflow

__version__ = "4.0.0"
__all__ = [
    "CitationMapping",
    "CitationInfo", 
    "CitationMappingEngine",
    "CitationResolver",
    "AIMappingWorkflow"
] 