"""
AI理解支援引用文献統合データ構造 v4.0

完全な引用文献情報を管理するためのデータ構造を定義します。
ai_tagging_translation_specification.md v4.0準拠
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional


@dataclass
class CitationInfo:
    """
    引用文献情報（完全な論文情報）
    
    ai_tagging_translation_specification.md v4.0に準拠
    """
    citation_key: str = ""           # BibTeX citation_key
    title: str = ""                  # 論文タイトル
    authors: str = ""                # 著者情報
    year: int = 0                    # 発行年
    journal: str = ""                # ジャーナル名
    volume: str = ""                 # 巻号情報
    pages: str = ""                  # ページ情報
    doi: str = ""                    # DOI
    url: str = ""                    # URL（オプション）
    keywords: List[str] = field(default_factory=list)  # キーワード（オプション）

    def to_reference_line(self) -> str:
        """引用情報の文字列表現を生成（YAMLヘッダー用）"""
        reference_line = (
            f"{self.authors} ({self.year}). "
            f"{self.title}. {self.journal}"
        )
        
        if self.volume:
            reference_line += f", {self.volume}"
        if self.pages:
            reference_line += f", {self.pages}"
        if self.doi:
            reference_line += f". DOI: {self.doi}"
        
        return reference_line


@dataclass
class CitationMapping:
    """
    引用番号と完全な論文情報のマッピング
    
    ai_tagging_translation_specification.md v4.0に準拠
    """
    index_map: Dict[int, CitationInfo] = field(default_factory=dict)  # 引用番号 → 完全な文献情報
    total_citations: int = 0                 # 総引用数
    last_updated: str = ""                   # 最終更新時刻（ISO 8601）
    references_file: str = ""                # 元のBibTeXファイル
    mapping_version: str = "2.0"             # マッピングバージョン
    is_self_contained: bool = False          # 自己完結フラグ


# AIReadableDocumentは削除されました
# 仕様書に従い、YAMLヘッダー統合機能のみを実装します


@dataclass
class MappingStatistics:
    """マッピング統計情報"""
    created_mappings: int = 0        # 作成されたマッピング数
    total_citations_mapped: int = 0  # マッピングされた総引用数
    processing_time: float = 0.0     # 処理時間（秒）
    success_rate: float = 0.0        # 成功率


@dataclass
class AIGenerationResult:
    """AI用ファイル生成結果"""
    success: bool = False            # 成功フラグ
    output_file: str = ""           # 出力ファイルパス
    error_message: str = ""         # エラーメッセージ
    warnings: List[str] = field(default_factory=list)  # 警告メッセージ
    statistics: Optional[MappingStatistics] = None      # 統計情報 