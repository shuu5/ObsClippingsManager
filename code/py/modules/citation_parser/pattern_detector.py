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
    
    # 仕様書で定義された基本パターン
    DEFAULT_PATTERNS = {
        'linked_citation': {
            'regex': r'\[(\^?\d+)\]\(([^)]+)\)',
            'type': 'linked',
            'priority': 1
        },
        'footnote_citation': {
            'regex': r'\[\^(\d+)\]',
            'type': 'footnote', 
            'priority': 2
        },
        'range_citation': {
            'regex': r'\[(\d+)[-–](\d+)\]',
            'type': 'range',
            'priority': 3
        },
        'multiple_citation': {
            'regex': r'\[(\d+(?:[,\s]+\d+)+)\]',
            'type': 'multiple',
            'priority': 4
        },
        'single_citation': {
            'regex': r'\[(\d+)\]',
            'type': 'single',
            'priority': 5
        },
        'mixed_footnote': {
            'regex': r'\[\^(\d+(?:,\^?\d+)*)\]',
            'type': 'footnote',
            'priority': 6
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
        for name, config in self.DEFAULT_PATTERNS.items():
            pattern_config = PatternConfig(
                name=name,
                regex=config['regex'],
                pattern_type=config['type'],
                priority=config['priority']
            )
            self.register_pattern(pattern_config)
    
    def register_pattern(self, pattern: PatternConfig) -> None:
        """
        新しいパターンを登録
        
        Args:
            pattern: パターン設定
        """
        try:
            # 正規表現をコンパイルして検証
            compiled_regex = re.compile(pattern.regex)
            
            self.patterns[pattern.name] = pattern
            self.compiled_patterns[pattern.name] = compiled_regex
            self.pattern_stats[pattern.name] = 0
            
            self.logger.debug(f"Registered pattern: {pattern.name}")
            
        except re.error as e:
            raise PatternDetectionError(f"Invalid regex pattern '{pattern.name}': {e}")
    
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
        """
        特定のパターンでマッチを検索
        
        Args:
            text: 検索対象テキスト
            compiled_pattern: コンパイル済み正規表現
            pattern_config: パターン設定
            processed_positions: 処理済み位置のセット
            
        Returns:
            マッチしたCitationMatchのリスト
        """
        matches = []
        
        for match in compiled_pattern.finditer(text):
            start_pos = match.start()
            end_pos = match.end()
            
            # 重複チェック
            if any(pos in processed_positions for pos in range(start_pos, end_pos)):
                continue
            
            try:
                citation_match = self._create_citation_match(match, pattern_config)
                matches.append(citation_match)
                
                # 処理済み位置を記録
                for pos in range(start_pos, end_pos):
                    processed_positions.add(pos)
                    
            except Exception as e:
                self.logger.warning(f"Failed to process match: {e}")
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
        if pattern_config.pattern_type == 'linked':
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
        numbers_str = match.group(1)
        
        if ',' in numbers_str:
            # 複数脚注の場合
            parts = numbers_str.split(',')
            numbers = []
            for part in parts:
                part = part.strip()
                if part.startswith('^'):
                    part = part[1:]
                try:
                    numbers.append(int(part))
                except ValueError:
                    raise PatternDetectionError(f"Invalid footnote number: {part}")
            return sorted(numbers)
        else:
            # 単一脚注
            try:
                return [int(numbers_str)]
            except ValueError:
                raise PatternDetectionError(f"Invalid footnote number: {numbers_str}")
    
    def _parse_single_citation(self, match: re.Match) -> List[int]:
        """単一引用を解析"""
        try:
            number = int(match.group(1))
            return [number]
        except ValueError:
            raise PatternDetectionError(f"Invalid citation number: {match.group(1)}")
    
    def get_pattern_stats(self) -> Dict[str, int]:
        """
        パターン別統計を取得
        
        Returns:
            パターン名: 検出回数の辞書
        """
        return self.pattern_stats.copy()
    
    def reset_stats(self):
        """統計をリセット"""
        for pattern_name in self.pattern_stats:
            self.pattern_stats[pattern_name] = 0 