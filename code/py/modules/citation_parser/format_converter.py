"""
引用フォーマット変換エンジン

検出された引用を統一されたフォーマットに変換する
"""

import re
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from .data_structures import CitationMatch, ProcessingError, OutputFormat
from .exceptions import FormatConversionError


@dataclass
class OutputFormat:
    """出力フォーマット設定"""
    single_template: str = "[{number}]"
    multiple_template: str = "[{numbers}]"
    separator: str = ", "  # 正しい区切り文字に修正
    sort_numbers: bool = True
    expand_ranges: bool = True
    remove_spaces: bool = False
    individual_citations: bool = True  # デフォルトで個別引用形式を有効化


class FormatConverter:
    """引用フォーマット変換エンジン"""
    
    def __init__(self, output_format: Optional[OutputFormat] = None):
        """
        初期化
        
        Args:
            output_format: 出力フォーマット設定
        """
        self.logger = logging.getLogger("ObsClippingsManager.CitationParser.FormatConverter")
        
        if output_format is None:
            self.output_format = OutputFormat()
        else:
            self.output_format = output_format
        
        # 個別引用モードを確実に有効化
        self.set_individual_citation_mode(True)
        
        self.current_text = ""  # テキスト参照用
        self.conversion_stats = {
            'converted': 0,
            'errors': 0,
            'total': 0
        }
        
        self.logger.debug("FormatConverter initialized with individual citation mode enabled")
    
    def convert_to_unified(self, text: str, matches: List[CitationMatch]) -> str:
        """
        引用を統一フォーマットに変換
        
        Args:
            text: 元のテキスト
            matches: 検出された引用マッチ
            
        Returns:
            変換後のテキスト
        """
        if not matches:
            return text
        
        # 位置を逆順でソート（後ろから置換して位置ずれを防ぐ）
        sorted_matches = sorted(matches, key=lambda x: x.start_pos, reverse=True)
        
        converted_text = text
        errors = []
        
        for match in sorted_matches:
            try:
                unified_citation = self._format_citation(match)
                
                # テキストを置換
                converted_text = (
                    converted_text[:match.start_pos] +
                    unified_citation +
                    converted_text[match.end_pos:]
                )
                
            except Exception as e:
                self.logger.warning(f"Failed to convert citation: {match.original_text} - {e}")
                errors.append(ProcessingError(
                    error_type="CONVERSION_ERROR",
                    message=str(e),
                    position=match.start_pos,
                    original_text=match.original_text
                ))
                continue
        
        self.logger.info(f"Converted {len(sorted_matches) - len(errors)} citations")
        return converted_text
    
    def _format_citation(self, match: CitationMatch) -> str:
        """
        CitationMatchを統一フォーマットに変換
        
        Args:
            match: 引用マッチ
            
        Returns:
            フォーマット済み引用文字列
        """
        numbers = match.citation_numbers.copy()
        
        # 数値の妥当性チェック
        if not numbers or any(n <= 0 for n in numbers):
            raise FormatConversionError(f"Invalid citation numbers: {numbers}")
        
        # ソート
        if self.output_format.sort_numbers:
            numbers.sort()
        
        # 重複除去
        numbers = list(dict.fromkeys(numbers))  # 順序を保持して重複除去
        
        # エスケープパターンかどうかを判定
        is_escaped_pattern = match.pattern_type.startswith('escaped_')
        
        # 統一フォーマット原則:
        # - すべての引用（脚注含む）は \[[number]\] 形式に統一
        # - 複数の場合は個別形式: \[[20], [21], [22]\]
        # - 脚注の^記号は除去される
        
        # 個別引用形式での出力（統一フォーマット）
        if hasattr(self.output_format, 'individual_citations') and self.output_format.individual_citations:
            # 常に個別の引用として出力: [1], [2], [3]
            if len(numbers) == 1:
                formatted_citation = f'[{numbers[0]}]'
            else:
                individual_citations = [f'[{n}]' for n in numbers]
                formatted_citation = ', '.join(individual_citations)
            
            # エスケープパターンの場合は外側に \[\] を追加
            if is_escaped_pattern:
                return f'\\[{formatted_citation}\\]'
            else:
                return formatted_citation
        else:
            # 従来のグループ化形式（使用しないが、後方互換性のため保持）
            if len(numbers) == 1:
                formatted_citation = self.output_format.single_template.format(number=numbers[0])
            else:
                numbers_str = self.output_format.separator.join(str(n) for n in numbers)
                if self.output_format.remove_spaces:
                    numbers_str = numbers_str.replace(" ", "")
                formatted_citation = self.output_format.multiple_template.format(numbers=numbers_str)
            
            # エスケープパターンの場合は外側に \[\] を追加
            if is_escaped_pattern:
                return f'\\[{formatted_citation}\\]'
            else:
                return formatted_citation
    
    def expand_ranges(self, range_citation: str) -> List[int]:
        """
        範囲引用を個別の引用番号に展開
        
        Args:
            range_citation: 範囲引用文字列（例: "1-5"）
            
        Returns:
            展開された引用番号リスト
        """
        # 範囲パターンをマッチ
        range_pattern = r'(\d+)[-–](\d+)'
        match = re.search(range_pattern, range_citation)
        
        if not match:
            raise FormatConversionError(f"Invalid range format: {range_citation}")
        
        start = int(match.group(1))
        end = int(match.group(2))
        
        # 妥当性チェック
        if start > end:
            raise FormatConversionError(f"Invalid range: start > end ({start} > {end})")
        
        if end - start > 100:  # 異常に大きな範囲を防ぐ
            raise FormatConversionError(f"Range too large: {start}-{end}")
        
        return list(range(start, end + 1))
    
    def standardize_spacing(self, citation: str) -> str:
        """
        引用文字列のスペースを標準化
        
        Args:
            citation: 引用文字列
            
        Returns:
            スペースが標準化された引用文字列
        """
        # 複数の空白を単一の空白に変換
        citation = re.sub(r'\s+', ' ', citation)
        
        # 個別引用形式の場合はコンマ+スペース
        if hasattr(self.output_format, 'individual_citations') and self.output_format.individual_citations:
            # 個別引用: [1], [2], [3] 形式
            citation = re.sub(r'\s*,\s*', ', ', citation)
        elif self.output_format.remove_spaces:
            citation = re.sub(r'\s*,\s*', ',', citation)
        else:
            citation = re.sub(r'\s*,\s*', ', ', citation)
        
        # 括弧内の不要なスペースを除去
        citation = re.sub(r'\[\s+', '[', citation)
        citation = re.sub(r'\s+\]', ']', citation)
        
        return citation.strip()
    
    def format_multiple_citations(self, numbers: List[int]) -> str:
        """
        複数の引用番号を統一フォーマットで出力
        
        Args:
            numbers: 引用番号のリスト
            
        Returns:
            フォーマット済み引用文字列
        """
        if not numbers:
            return ""
        
        # ソートと重複除去
        if self.output_format.sort_numbers:
            numbers = sorted(list(set(numbers)))
        else:
            numbers = list(dict.fromkeys(numbers))
        
        # 個別引用形式
        if hasattr(self.output_format, 'individual_citations') and self.output_format.individual_citations:
            individual_citations = [f'[{n}]' for n in numbers]
            return ', '.join(individual_citations)
        
        # グループ化形式（レガシー）
        if len(numbers) == 1:
            return f'[{numbers[0]}]'
        else:
            numbers_str = ', '.join(str(n) for n in numbers)
            return f'[{numbers_str}]'
    
    def set_individual_citation_mode(self, enabled: bool = True):
        """
        個別引用モードの設定
        
        Args:
            enabled: 個別引用モードを有効にするか
        """
        # OutputFormatにindividual_citationsアトリビュートを確実に設定
        self.output_format.individual_citations = enabled
        
        if enabled:
            self.output_format.separator = ', '  # 正しい区切り文字に修正
            self.output_format.multiple_template = '[{numbers}]'
        else:
            self.output_format.separator = ','
        
        self.logger.debug(f"Individual citation mode: {'enabled' if enabled else 'disabled'}")
    
    def merge_adjacent_citations(self, matches: List[CitationMatch]) -> List[CitationMatch]:
        """
        隣接する引用をマージ
        
        Args:
            matches: 引用マッチリスト
            
        Returns:
            マージされた引用マッチリスト
        """
        if not matches:
            return matches
        
        # 位置順にソート
        sorted_matches = sorted(matches, key=lambda x: x.start_pos)
        merged = []
        current_group = [sorted_matches[0]]
        
        for i in range(1, len(sorted_matches)):
            current = sorted_matches[i]
            last_in_group = current_group[-1]
            
            # 隣接判定（間にテキストがほとんどない場合）
            gap = current.start_pos - last_in_group.end_pos
            gap_text = self._extract_gap_text(last_in_group.end_pos, current.start_pos)
            
            if gap <= 10 and self._is_mergeable_gap(gap_text):
                current_group.append(current)
            else:
                # 現在のグループをマージして追加
                if len(current_group) > 1:
                    merged_match = self._merge_citation_group(current_group)
                    merged.append(merged_match)
                else:
                    merged.append(current_group[0])
                
                current_group = [current]
        
        # 最後のグループを処理
        if len(current_group) > 1:
            merged_match = self._merge_citation_group(current_group)
            merged.append(merged_match)
        else:
            merged.append(current_group[0])
        
        return merged
    
    def _extract_gap_text(self, start_pos: int, end_pos: int) -> str:
        """
        指定された位置間のテキストを抽出
        
        Args:
            start_pos: 開始位置
            end_pos: 終了位置
            
        Returns:
            ギャップテキスト
        """
        # 現在処理中のテキストが保存されていない場合は空文字を返す
        if not hasattr(self, '_current_text'):
            return ""
        
        try:
            if 0 <= start_pos < end_pos <= len(self._current_text):
                return self._current_text[start_pos:end_pos]
        except (IndexError, TypeError):
            pass
        
        return ""

    def set_current_text(self, text: str) -> None:
        """
        現在処理中のテキストを設定
        
        Args:
            text: 処理中のテキスト
        """
        self._current_text = text

    def _is_mergeable_gap(self, gap_text: str) -> bool:
        """
        ギャップテキストがマージ可能かを判定
        
        Args:
            gap_text: 引用間のテキスト
            
        Returns:
            マージ可能かどうか
        """
        # 空白、カンマ、ダッシュ、"and"等のみの場合はマージ可能
        mergeable_pattern = r'^[\s,\-–]*(?:and|&)?[\s,\-–]*$'
        return bool(re.match(mergeable_pattern, gap_text, re.IGNORECASE))
    
    def _merge_citation_group(self, group: List[CitationMatch]) -> CitationMatch:
        """
        引用グループをマージ
        
        Args:
            group: マージ対象の引用マッチリスト
            
        Returns:
            マージされた引用マッチ
        """
        if not group:
            raise FormatConversionError("Empty group cannot be merged")
        
        if len(group) == 1:
            return group[0]
        
        # 全ての引用番号を収集
        all_numbers = []
        has_any_link = False
        all_urls = []
        
        for match in group:
            all_numbers.extend(match.citation_numbers)
            if match.has_link:
                has_any_link = True
                if match.link_url:
                    all_urls.append(match.link_url)
        
        # 重複除去とソート
        unique_numbers = sorted(list(set(all_numbers)))
        
        # 結合されたテキストを作成
        first_match = group[0]
        last_match = group[-1]
        original_text = f"{first_match.original_text}...{last_match.original_text}"
        
        return CitationMatch(
            original_text=original_text,
            citation_numbers=unique_numbers,
            has_link=has_any_link,
            link_url=all_urls[0] if all_urls else None,
            pattern_type="merged",
            start_pos=first_match.start_pos,
            end_pos=last_match.end_pos
        )
    
    def set_output_format(self, format_type: str, **kwargs):
        """
        出力フォーマットを設定
        
        Args:
            format_type: フォーマットタイプ（compact, spaced, custom等）
            **kwargs: 追加設定
        """
        if format_type == "compact":
            self.output_format = OutputFormat(
                separator=",",
                remove_spaces=True
            )
        elif format_type == "spaced":
            self.output_format = OutputFormat(
                separator=", ",
                remove_spaces=False
            )
        elif format_type == "custom":
            # カスタム設定を適用
            for key, value in kwargs.items():
                if hasattr(self.output_format, key):
                    setattr(self.output_format, key, value)
        else:
            raise FormatConversionError(f"Unknown format type: {format_type}")
        
        self.logger.debug(f"Set output format to: {format_type}")
    
    def validate_citation_range(self, start: int, end: int) -> bool:
        """
        範囲引用の妥当性チェック
        
        Args:
            start: 開始番号
            end: 終了番号
            
        Returns:
            妥当性
        """
        return start <= end and start > 0 and end - start <= 100
    
    def validate_citation_sequence(self, numbers: List[int]) -> bool:
        """
        引用番号シーケンスの妥当性チェック
        
        Args:
            numbers: 引用番号リスト
            
        Returns:
            妥当性
        """
        return all(n > 0 for n in numbers) and len(numbers) <= 50 