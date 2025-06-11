"""
引用パターン検出エンジン

複数の引用形式を自動検出するエンジン
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .data_structures import CitationMatch, PatternConfig, PatternType
from .exceptions import PatternDetectionError


class PatternDetector:
    """引用パターン検出エンジン"""
    
    # 仕様書で定義された基本パターン + エスケープパターン
    DEFAULT_PATTERNS = {
        # エスケープされたパターン（最優先）
        'escaped_linked_citation': {
            'regex': r'\\\[\[(\d+(?:[,\s]*\d+)*)\]\(([^)]+)\)\\\]',
            'type': 'escaped_linked',
            'priority': 1
        },
        'escaped_linked_range': {
            'regex': r'\\\[\[(\d+)[-–](\d+)\]\(([^)]+)\)\\\]',
            'type': 'escaped_linked_range',
            'priority': 1
        },
        'escaped_footnote_multiple_individual': {
            'regex': r'\\\[\[\^(\d+)\](?:\s*,\s*\[\^(\d+)\])*\\\]',
            'type': 'escaped_footnote',
            'priority': 2
        },
        'escaped_footnote_single': {
            'regex': r'\\\[\[\^(\d+)\]\\\]',
            'type': 'escaped_footnote',
            'priority': 2
        },
        'escaped_individual_multiple': {
            'regex': r'\\\[\[(\d+)\](?:\s*,\s*\[(\d+)\])*\\\]',
            'type': 'escaped_individual',
            'priority': 3
        },
        'escaped_multiple_grouped': {
            'regex': r'\\\[\[(\d+(?:[,\s]*\d+)*)\]\\\]',
            'type': 'escaped_multiple',
            'priority': 3
        },
        'escaped_single': {
            'regex': r'\\\[\[(\d+)\]\\\]',
            'type': 'escaped_single',
            'priority': 3
        },
        # 標準パターン
        'linked_citation': {
            'regex': r'\[(\^?\d+)\]\(([^)]+)\)',
            'type': 'linked',
            'priority': 4
        },
        'footnote_citation': {
            'regex': r'\[\^(\d+)\]',
            'type': 'footnote', 
            'priority': 5
        },
        'range_citation': {
            'regex': r'\[(\d+)[-–](\d+)\]',
            'type': 'range',
            'priority': 6
        },
        'multiple_citation': {
            'regex': r'\[(\d+(?:[,\s]+\d+)+)\]',
            'type': 'multiple',
            'priority': 7
        },
        'single_citation': {
            'regex': r'\[(\d+)\]',
            'type': 'single',
            'priority': 8
        },
        'mixed_footnote': {
            'regex': r'\[\^(\d+(?:,\^?\d+)*)\]',
            'type': 'footnote',
            'priority': 9
        }
    }
    
    def __init__(self):
        """初期化"""
        self.patterns = {}
        self.compiled_patterns = {}
        self.pattern_stats = {}
        self.logger = logging.getLogger("ObsClippingsManager.CitationParser.PatternDetector")
        
        # デフォルトパターンを登録
        self._register_default_patterns()
    
    def _register_default_patterns(self):
        """デフォルトパターンを登録"""
        for pattern_name, pattern_config in self.DEFAULT_PATTERNS.items():
            config = PatternConfig(
                name=pattern_name,
                regex=pattern_config['regex'],
                pattern_type=pattern_config['type'],
                priority=pattern_config['priority'],
                enabled=True
            )
            self.register_pattern(config)
    
    def register_pattern(self, pattern_config: PatternConfig):
        """パターンを登録"""
        try:
            compiled_pattern = re.compile(pattern_config.regex)
            self.patterns[pattern_config.name] = pattern_config
            self.compiled_patterns[pattern_config.name] = compiled_pattern
            self.pattern_stats[pattern_config.name] = 0
            
            self.logger.debug(f"Registered pattern: {pattern_config.name}")
        except re.error as e:
            raise PatternDetectionError(f"Invalid regex pattern {pattern_config.name}: {e}")
    
    def detect_patterns(self, text: str) -> List[CitationMatch]:
        """
        テキストから引用パターンを検出
        
        Args:
            text: 検出対象テキスト
            
        Returns:
            検出された引用マッチのリスト
        """
        if not text:
            return []
        
        matches = []
        processed_positions = set()  # 重複検出を避けるための位置記録
        
        # 優先度順にパターンを処理
        sorted_patterns = sorted(
            self.patterns.items(),
            key=lambda x: x[1].priority
        )
        
        for pattern_name, pattern_config in sorted_patterns:
            if not pattern_config.enabled:
                continue
                
            compiled_pattern = self.compiled_patterns[pattern_name]
            pattern_matches = self._find_pattern_matches(
                text, compiled_pattern, pattern_config, processed_positions
            )
            
            matches.extend(pattern_matches)
            self.pattern_stats[pattern_name] += len(pattern_matches)
        
        # 位置順にソート
        matches.sort(key=lambda x: x.start_pos)
        
        self.logger.info(f"Detected {len(matches)} citation patterns")
        return matches
    
    def _find_pattern_matches(self, text: str, compiled_pattern: re.Pattern,
                             pattern_config: PatternConfig, 
                             processed_positions: set) -> List[CitationMatch]:
        """特定パターンのマッチを検索"""
        matches = []
        
        for match in compiled_pattern.finditer(text):
            start_pos = match.start()
            end_pos = match.end()
            
            # 重複位置チェック
            position_range = set(range(start_pos, end_pos))
            if position_range.intersection(processed_positions):
                continue
            
            try:
                citation_match = self._create_citation_match(match, pattern_config)
                matches.append(citation_match)
                processed_positions.update(position_range)
                
            except PatternDetectionError as e:
                self.logger.warning(f"Failed to create citation match: {e}")
                continue
        
        return matches
    
    def _create_citation_match(self, match: re.Match, 
                              pattern_config: PatternConfig) -> CitationMatch:
        """
        正規表現マッチからCitationMatchを作成
        
        Args:
            match: 正規表現マッチオブジェクト
            pattern_config: パターン設定
            
        Returns:
            CitationMatchオブジェクト
        """
        original_text = match.group(0)
        start_pos = match.start()
        end_pos = match.end()
        
        # パターンタイプ別の処理
        if pattern_config.pattern_type in ['escaped_linked', 'escaped_linked_range']:
            citation_numbers, link_url = self._parse_escaped_linked_citation(match, pattern_config.pattern_type)
            has_link = True
        elif pattern_config.pattern_type == 'escaped_footnote':
            citation_numbers = self._parse_escaped_footnote_citation(match)
            link_url = None
            has_link = False
        elif pattern_config.pattern_type == 'escaped_individual':
            citation_numbers = self._parse_escaped_individual_citation(match)
            link_url = None
            has_link = False
        elif pattern_config.pattern_type in ['escaped_multiple', 'escaped_single']:
            citation_numbers = self._parse_escaped_basic_citation(match)
            link_url = None
            has_link = False
        elif pattern_config.pattern_type == 'linked':
            citation_numbers, link_url = self._parse_linked_citation(match)
            has_link = True
        elif pattern_config.pattern_type == 'range':
            citation_numbers = self._parse_range_citation(match)
            link_url = None
            has_link = False
        elif pattern_config.pattern_type == 'multiple':
            citation_numbers = self._parse_multiple_citation(match)
            link_url = None
            has_link = False
        elif pattern_config.pattern_type == 'footnote':
            citation_numbers = self._parse_footnote_citation(match)
            link_url = None
            has_link = False
        else:  # single
            citation_numbers = self._parse_single_citation(match)
            link_url = None
            has_link = False
        
        return CitationMatch(
            original_text=original_text,
            citation_numbers=citation_numbers,
            has_link=has_link,
            link_url=link_url,
            pattern_type=pattern_config.pattern_type,
            start_pos=start_pos,
            end_pos=end_pos
        )
    
    def _parse_escaped_linked_citation(self, match: re.Match, pattern_type: str) -> Tuple[List[int], str]:
        """エスケープされたリンク付き引用を解析"""
        if pattern_type == 'escaped_linked_range':
            # 範囲リンク: \[[1-3](URL)\]
            start_num = int(match.group(1))
            end_num = int(match.group(2))
            url = match.group(3)
            
            if start_num > end_num:
                raise PatternDetectionError(f"Invalid range: {start_num}-{end_num}")
            if end_num - start_num > 50:
                raise PatternDetectionError(f"Range too large: {start_num}-{end_num}")
            
            citation_numbers = list(range(start_num, end_num + 1))
            return citation_numbers, url
        else:
            # 複数リンク: \[[1,2,3](URL)\]
            citation_part = match.group(1)
            url = match.group(2)
            
            # カンマまたは空白で分割
            parts = re.split(r'[,\s]+', citation_part.strip())
            numbers = []
            
            for part in parts:
                if part.strip():
                    try:
                        numbers.append(int(part.strip()))
                    except ValueError:
                        raise PatternDetectionError(f"Invalid citation number: {part}")
            
            return sorted(list(set(numbers))), url
    
    def _parse_escaped_footnote_citation(self, match: re.Match) -> List[int]:
        """エスケープされた脚注引用を解析"""
        original_text = match.group(0)
        
        # \[[^1],[^2],[^3]\] または \[[^1]\] のパターン
        # 脚注番号を抽出
        footnote_pattern = r'\[\^(\d+)\]'
        footnote_matches = re.findall(footnote_pattern, original_text)
        
        if footnote_matches:
            # 複数の脚注番号を処理
            numbers = []
            for num_str in footnote_matches:
                try:
                    numbers.append(int(num_str))
                except ValueError:
                    raise PatternDetectionError(f"Invalid footnote number: {num_str}")
            return sorted(list(set(numbers)))
        else:
            # 単一の脚注: \[[^1]\] のパターン
            if match.group(1):
                return [int(match.group(1))]
            else:
                raise PatternDetectionError(f"No footnote numbers found in: {original_text}")
    
    def _parse_escaped_individual_citation(self, match: re.Match) -> List[int]:
        r"""エスケープされた個別引用を解析 (\[[12], [13]\] パターン)"""
        original_text = match.group(0)
        
        # 個別の引用番号を抽出: \[[12], [13]\] から 12, 13 を取得
        individual_pattern = r'\[(\d+)\]'
        numbers = []
        
        for num_match in re.finditer(individual_pattern, original_text):
            try:
                numbers.append(int(num_match.group(1)))
            except ValueError:
                raise PatternDetectionError(f"Invalid citation number: {num_match.group(1)}")
        
        return sorted(list(set(numbers)))
    
    def _parse_escaped_basic_citation(self, match: re.Match) -> List[int]:
        """エスケープされた基本引用を解析"""
        citation_part = match.group(1)
        
        # カンマまたは空白で分割
        parts = re.split(r'[,\s]+', citation_part.strip())
        numbers = []
        
        for part in parts:
            if part.strip():
                try:
                    numbers.append(int(part.strip()))
                except ValueError:
                    raise PatternDetectionError(f"Invalid citation number: {part}")
        
        return sorted(list(set(numbers)))
    
    def _parse_linked_citation(self, match: re.Match) -> Tuple[List[int], str]:
        """リンク付き引用を解析"""
        citation_part = match.group(1)
        url = match.group(2)
        
        # 脚注記号を除去
        if citation_part.startswith('^'):
            citation_part = citation_part[1:]
        
        try:
            number = int(citation_part)
            return [number], url
        except ValueError:
            raise PatternDetectionError(f"Invalid citation number in linked citation: {citation_part}")
    
    def _parse_range_citation(self, match: re.Match) -> List[int]:
        """範囲引用を解析"""
        start_num = int(match.group(1))
        end_num = int(match.group(2))
        
        if start_num > end_num:
            raise PatternDetectionError(f"Invalid range: {start_num}-{end_num}")
        
        if end_num - start_num > 50:  # 異常に大きな範囲を防ぐ
            raise PatternDetectionError(f"Range too large: {start_num}-{end_num}")
        
        return list(range(start_num, end_num + 1))
    
    def _parse_multiple_citation(self, match: re.Match) -> List[int]:
        """複数引用を解析"""
        numbers_str = match.group(1)
        
        # カンマまたは空白で分割
        parts = re.split(r'[,\s]+', numbers_str.strip())
        numbers = []
        
        for part in parts:
            if part.strip():
                try:
                    numbers.append(int(part.strip()))
                except ValueError:
                    raise PatternDetectionError(f"Invalid citation number: {part}")
        
        return sorted(list(set(numbers)))  # 重複除去とソート
    
    def _parse_footnote_citation(self, match: re.Match) -> List[int]:
        """脚注引用を解析"""
        citation_part = match.group(1)
        
        # 複数の脚注番号の場合
        if ',' in citation_part:
            parts = citation_part.split(',')
            numbers = []
            for part in parts:
                part = part.strip()
                if part.startswith('^'):
                    part = part[1:]
                try:
                    numbers.append(int(part))
                except ValueError:
                    raise PatternDetectionError(f"Invalid footnote number: {part}")
            return sorted(list(set(numbers)))
        else:
            # 単一の脚注番号
            try:
                return [int(citation_part)]
            except ValueError:
                raise PatternDetectionError(f"Invalid footnote number: {citation_part}")
    
    def _parse_single_citation(self, match: re.Match) -> List[int]:
        """単一引用を解析"""
        try:
            number = int(match.group(1))
            return [number]
        except ValueError:
            raise PatternDetectionError(f"Invalid citation number: {match.group(1)}")
    
    def get_pattern_statistics(self) -> Dict[str, int]:
        """パターン別統計を取得"""
        return self.pattern_stats.copy()
    
    def reset_statistics(self):
        """統計をリセット"""
        for pattern_name in self.pattern_stats:
            self.pattern_stats[pattern_name] = 0
    
    def _remove_overlapping_matches(self, matches: List[CitationMatch]) -> List[CitationMatch]:
        """
        オーバーラップするマッチを除去（優先度順）
        
        重要: 脚注パターンも含めてすべて統一フォーマット \\[[number]\\] に変換される
        
        Args:
            matches: マッチリスト
            
        Returns:
            オーバーラップが除去されたマッチリスト
        """
        if not matches:
            return []
        
        # 優先度順にソート（数値が小さいほど高優先度）
        sorted_matches = sorted(matches, key=lambda m: (
            self.patterns[self._get_pattern_name_for_match(m)].priority,
            m.start_pos
        ))
        
        result = []
        used_positions = set()
        
        for match in sorted_matches:
            # 位置の範囲を計算
            match_range = set(range(match.start_pos, match.end_pos))
            
            # オーバーラップチェック
            if not match_range.intersection(used_positions):
                result.append(match)
                used_positions.update(match_range)
                
                # ログ出力（脚注パターンの処理確認用）
                if 'footnote' in match.pattern_type:
                    self.logger.debug(f"Footnote pattern detected: {match.original_text} -> numbers: {match.citation_numbers}")
        
        return result
    
    def _get_pattern_name_for_match(self, match: CitationMatch) -> str:
        """マッチに対応するパターン名を取得"""
        # パターンタイプから対応するパターン名を検索
        for name, config in self.patterns.items():
            if config.pattern_type == match.pattern_type:
                return name
        return "unknown" 