"""
引用文献パーサーデータ構造
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class PatternType(Enum):
    """引用パターンタイプ"""
    SINGLE = "single"
    MULTIPLE = "multiple"
    RANGE = "range"
    FOOTNOTE = "footnote"
    LINKED = "linked"
    MIXED = "mixed"


@dataclass
class CitationMatch:
    """引用マッチング結果"""
    original_text: str                    # 元のテキスト
    citation_numbers: List[int]           # 引用番号リスト
    has_link: bool                        # リンクの有無
    link_url: Optional[str] = None        # リンクURL
    pattern_type: str = ""                # パターンタイプ
    start_pos: int = 0                    # 開始位置
    end_pos: int = 0                      # 終了位置


@dataclass
class LinkEntry:
    """リンク対応表エントリ"""
    citation_number: int                  # 引用番号
    url: str                             # URL
    display_text: Optional[str] = None    # 表示テキスト


@dataclass
class ProcessingError:
    """処理エラー情報"""
    error_type: str                      # エラータイプ
    message: str                         # エラーメッセージ
    position: Optional[int] = None       # エラー位置
    original_text: Optional[str] = None  # 問題のあるテキスト


@dataclass
class ProcessingStats:
    """処理統計情報"""
    total_citations: int = 0             # 総引用数
    converted_citations: int = 0         # 変換成功数
    errors: int = 0                      # エラー数
    pattern_breakdown: Dict[str, int] = field(default_factory=dict)  # パターン別集計
    processing_time: float = 0.0         # 処理時間（秒）


@dataclass
class CitationResult:
    """引用パーサー処理結果"""
    converted_text: str                  # 変換後テキスト
    link_table: List[LinkEntry]          # リンク対応表
    statistics: ProcessingStats          # 処理統計
    errors: List[ProcessingError]        # エラーリスト
    original_matches: List[CitationMatch] = field(default_factory=list)  # 元のマッチ結果


@dataclass
class PatternConfig:
    """パターン設定"""
    name: str                            # パターン名
    regex: str                           # 正規表現
    pattern_type: str                    # パターンタイプ
    priority: int                        # 優先度
    enabled: bool = True                 # 有効/無効 