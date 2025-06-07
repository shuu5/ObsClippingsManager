"""
引用文献統一化パーサー

様々な形式で記載された引用文献を統一されたフォーマットに変換し、
リンク付き引用からは対応表を生成するメインパーサークラス
"""

import time
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import re

from .data_structures import (
    CitationResult, ProcessingStats, ProcessingError, 
    CitationMatch, LinkEntry
)
from .exceptions import CitationParserError
from .pattern_detector import PatternDetector
from .format_converter import FormatConverter, OutputFormat
from .link_extractor import LinkExtractor
from .config_manager import ConfigManager


class CitationParser:
    """引用文献統一化パーサー"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルパス
        """
        self.logger = logging.getLogger("ObsClippingsManager.CitationParser")
        
        # 設定管理
        self.config_manager = ConfigManager(config_path)
        
        # コンポーネント初期化
        self.pattern_detector = PatternDetector()
        self.format_converter = FormatConverter()
        self.link_extractor = LinkExtractor()
        
        # 設定からパターンを登録
        self._setup_patterns()
        self._setup_output_format()
        
        self.logger.info("CitationParser initialized successfully")
    
    def parse_document(self, text: str) -> CitationResult:
        """
        文書を解析して引用を統一フォーマットに変換
        
        Args:
            text: 解析対象テキスト
            
        Returns:
            CitationResult
        """
        start_time = time.time()
        errors = []
        
        try:
            self.logger.info(f"Starting citation parsing for document ({len(text)} chars)")
            
            # Step 1: パターン検出
            matches = self.pattern_detector.detect_patterns(text)
            
            if not matches:
                self.logger.info("No citation patterns detected")
                return CitationResult(
                    converted_text=text,
                    link_table=[],
                    statistics=ProcessingStats(
                        total_citations=0,
                        converted_citations=0,
                        errors=0,
                        processing_time=time.time() - start_time
                    ),
                    errors=[],
                    original_matches=[]
                )
            
            # Step 2: リンク抽出
            clean_text, link_entries = self.link_extractor.extract_links(text, matches)
            
            # Step 2.5: リンク抽出後の位置情報を更新
            updated_matches = self._update_matches_after_link_extraction(clean_text, matches, link_entries)
            
            # Step 3: フォーマット変換
            converted_text = self.format_converter.convert_to_unified(clean_text, updated_matches)
            
            # Step 4: 統計情報の生成
            statistics = self._generate_statistics(matches, errors, start_time)
            
            result = CitationResult(
                converted_text=converted_text,
                link_table=link_entries,
                statistics=statistics,
                errors=errors,
                original_matches=matches
            )
            
            self.logger.info(
                f"Citation parsing completed: {statistics.converted_citations}/{statistics.total_citations} "
                f"citations converted in {statistics.processing_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to parse document: {e}")
            raise CitationParserError(f"Document parsing failed: {e}")
    
    def _setup_patterns(self):
        """設定からパターンを設定"""
        pattern_configs = self.config_manager.get_pattern_configs()
        
        # 既存のパターンをクリア
        self.pattern_detector.patterns.clear()
        self.pattern_detector.compiled_patterns.clear()
        self.pattern_detector.pattern_stats.clear()
        
        # 設定からパターンを登録
        for pattern_config in pattern_configs:
            if pattern_config.enabled:
                self.pattern_detector.register_pattern(pattern_config)
        
        self.logger.debug(f"Registered {len(pattern_configs)} patterns")
    
    def _setup_output_format(self):
        """出力フォーマットを設定"""
        format_config = self.config_manager.get_output_format_config('standard')
        
        output_format = OutputFormat(
            single_template=format_config.get('single', '[{number}]'),
            multiple_template=format_config.get('multiple', '[{numbers}]'),
            separator=format_config.get('separator', ','),
            sort_numbers=format_config.get('sort_numbers', True),
            expand_ranges=format_config.get('expand_ranges', True),
            remove_spaces=format_config.get('remove_spaces', False)
        )
        
        self.format_converter.output_format = output_format
    
    def _generate_statistics(self, matches: List[CitationMatch], 
                            errors: List[ProcessingError], 
                            start_time: float) -> ProcessingStats:
        """処理統計を生成"""
        total_citations = len(matches)
        error_count = len(errors)
        converted_citations = total_citations - error_count
        
        # パターン別統計
        pattern_breakdown = {}
        for match in matches:
            pattern_type = match.pattern_type
            pattern_breakdown[pattern_type] = pattern_breakdown.get(pattern_type, 0) + 1
        
        return ProcessingStats(
            total_citations=total_citations,
            converted_citations=converted_citations,
            errors=error_count,
            pattern_breakdown=pattern_breakdown,
            processing_time=time.time() - start_time
        )
    
    def _update_matches_after_link_extraction(self, clean_text: str, 
                                            original_matches: List[CitationMatch], 
                                            link_entries: List[LinkEntry]) -> List[CitationMatch]:
        """
        リンク抽出後にマッチの位置情報を更新
        
        Args:
            clean_text: リンク抽出後のクリーンなテキスト
            original_matches: 元のマッチリスト  
            link_entries: 抽出されたリンクエントリ
            
        Returns:
            位置情報が更新されたマッチリスト
        """
        # よりシンプルなアプローチ：クリーンなテキストで全ての引用を再検出
        # ただし、リンク情報は保持しない（既に抽出済み）
        
        updated_matches = []
        
        # 基本的な引用パターンでクリーンなテキストを再スキャン
        citation_patterns = [
            r'\[(\d+(?:,\s*\d+)*)\]',  # [1] [1,2] [1, 2, 3]
            r'\[(\d+)[-–](\d+)\]',     # [1-3] [1–3]
        ]
        
        for pattern in citation_patterns:
            for match in re.finditer(pattern, clean_text):
                start_pos = match.start()
                end_pos = match.end()
                original_text = match.group(0)
                
                # 引用番号を解析
                if '-' in original_text or '–' in original_text:
                    # 範囲引用
                    start_num = int(match.group(1))
                    end_num = int(match.group(2))
                    citation_numbers = list(range(start_num, end_num + 1))
                    pattern_type = 'range'
                else:
                    # 単一または複数引用
                    numbers_str = match.group(1)
                    citation_numbers = [int(n.strip()) for n in numbers_str.split(',')]
                    pattern_type = 'multiple' if len(citation_numbers) > 1 else 'single'
                
                # 新しいマッチオブジェクトを作成
                updated_match = CitationMatch(
                    original_text=original_text,
                    citation_numbers=citation_numbers,
                    has_link=False,  # リンクは既に抽出済み
                    link_url=None,
                    pattern_type=pattern_type,
                    start_pos=start_pos,
                    end_pos=end_pos
                )
                updated_matches.append(updated_match)
        
        # 位置順にソート
        updated_matches.sort(key=lambda x: x.start_pos)
        
        # 重複する位置のマッチを除去
        filtered_matches = []
        used_positions = set()
        
        for match in updated_matches:
            # 位置の重複チェック
            position_range = set(range(match.start_pos, match.end_pos))
            if not position_range.intersection(used_positions):
                filtered_matches.append(match)
                used_positions.update(position_range)
        
        self.logger.debug(f"Updated {len(filtered_matches)} citation positions after link extraction")
        return filtered_matches 