"""
動的引用解決機能 v4.0

引用番号からリアルタイムでBibTeX情報を取得し、
文脈情報を抽出してAI理解を支援します。
"""

import re
import logging
from typing import Dict, List, Optional
from pathlib import Path

from .data_structures import CitationInfo, CitationMapping
from .citation_mapping_engine import CitationMappingEngine
from ..shared.bibtex_parser import BibTeXParser
from ..shared.logger import get_integrated_logger


class CitationResolver:
    """引用番号からリアルタイムでBibTeX情報を取得"""
    
    def __init__(self, config_manager=None):
        """
        初期化
        
        Args:
            config_manager: 設定管理インスタンス
        """
        self.logger = get_integrated_logger().get_logger("AICitationSupport.CitationResolver")
        self.config_manager = config_manager
        self.bibtex_parser = BibTeXParser()
        self.mapping_engine = CitationMappingEngine(config_manager)
        
        # 設定値
        self.context_window = 50  # 文脈抽出時の前後文字数
        self.cache_enabled = True
        self._citation_cache = {}  # 解決結果キャッシュ
        
        self.logger.info("CitationResolver initialized")
    
    def resolve_citation(self, citation_number: int, markdown_file: str) -> Optional[CitationInfo]:
        """
        引用番号から完全な文献情報を動的に取得
        
        Args:
            citation_number: 引用番号
            markdown_file: Markdownファイルパス
            
        Returns:
            CitationInfo: 完全な引用文献情報（見つからない場合はNone）
            
        Process:
        1. citation_mappingから直接CitationInfoを取得
        2. 文脈情報を抽出
        3. 関連度スコア算出（簡易版）
        4. 統合したCitationInfoを返す
        """
        try:
            # キャッシュチェック
            cache_key = f"{markdown_file}:{citation_number}"
            if self.cache_enabled and cache_key in self._citation_cache:
                self.logger.debug(f"Cache hit for citation {citation_number}")
                return self._citation_cache[cache_key]
            
            self.logger.info(f"Resolving citation [{citation_number}] from {markdown_file}")
            
            # Step 1: citation_mappingから直接CitationInfoを取得
            citation_mapping = self.mapping_engine.get_mapping_from_file(markdown_file)
            if not citation_mapping:
                self.logger.warning(f"No citation mapping found in {markdown_file}")
                return None
            
            if citation_number not in citation_mapping.index_map:
                self.logger.warning(f"Citation number {citation_number} not found in mapping")
                return None
            
            # citation_mappingにはすでに完全なCitationInfoが含まれている
            citation_info = citation_mapping.index_map[citation_number]
            self.logger.debug(f"Citation [{citation_number}] retrieved: {citation_info.citation_key}")
            
            # キャッシュに保存
            if self.cache_enabled:
                self._citation_cache[cache_key] = citation_info
            
            return citation_info
            
        except Exception as e:
            self.logger.error(f"Failed to resolve citation {citation_number}: {e}")
            return None
    
    def batch_resolve_citations(self, citation_numbers: List[int], 
                               markdown_file: str) -> Dict[int, CitationInfo]:
        """
        複数の引用番号を一括解決
        
        Args:
            citation_numbers: 引用番号のリスト
            markdown_file: Markdownファイルパス
            
        Returns:
            引用番号 → CitationInfo の辞書
        """
        self.logger.info(f"Batch resolving {len(citation_numbers)} citations from {markdown_file}")
        
        results = {}
        for number in citation_numbers:
            citation_info = self.resolve_citation(number, markdown_file)
            if citation_info:
                results[number] = citation_info
        
        self.logger.info(f"Resolved {len(results)}/{len(citation_numbers)} citations successfully")
        return results
    
    def extract_citation_context(self, markdown_file: str, citation_number: int) -> str:
        """
        引用箇所周辺の文脈を抽出してAI理解を支援
        
        Args:
            markdown_file: Markdownファイルパス
            citation_number: 引用番号
            
        Returns:
            引用箇所周辺の文脈文字列
        """
        try:
            with open(markdown_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # YAMLヘッダーを除去（本文のみ対象）
            yaml_pattern = r'^---\s*\n.*?\n---\s*\n'
            content = re.sub(yaml_pattern, '', content, flags=re.DOTALL)
            
            # 引用パターンを検索
            citation_patterns = [
                rf'\[{citation_number}\]',
                rf'\[\^{citation_number}\]',
                rf'\\?\[\[{citation_number}\]\\?\]',
                rf'\\?\[\[\^{citation_number}\]\\?\]'
            ]
            
            for pattern in citation_patterns:
                matches = list(re.finditer(pattern, content))
                if matches:
                    # 最初のマッチの前後文脈を取得
                    match = matches[0]
                    start = max(0, match.start() - self.context_window)
                    end = min(len(content), match.end() + self.context_window)
                    
                    context = content[start:end].strip()
                    # 改行を空白に変換し、連続する空白を単一化
                    context = re.sub(r'\s+', ' ', context)
                    
                    self.logger.debug(f"Context extracted for citation [{citation_number}]: {context[:100]}...")
                    return context
            
            self.logger.warning(f"No context found for citation [{citation_number}]")
            return ""
            
        except Exception as e:
            self.logger.error(f"Failed to extract context for citation {citation_number}: {e}")
            return ""
    

    
    def clear_cache(self):
        """キャッシュをクリア"""
        self._citation_cache.clear()
        self.logger.info("Citation cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """キャッシュ統計を取得"""
        return {
            'cached_citations': len(self._citation_cache),
            'cache_enabled': self.cache_enabled
        } 