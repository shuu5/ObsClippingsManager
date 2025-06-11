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
        1. YAMLヘッダーからcitation_keyを取得
        2. references.bibから詳細情報を取得
        3. 文脈情報を抽出
        4. 統合したCitationInfoを返す
        """
        try:
            # キャッシュチェック
            cache_key = f"{markdown_file}:{citation_number}"
            if self.cache_enabled and cache_key in self._citation_cache:
                self.logger.debug(f"Cache hit for citation {citation_number}")
                return self._citation_cache[cache_key]
            
            self.logger.info(f"Resolving citation [{citation_number}] from {markdown_file}")
            
            # Step 1: YAMLヘッダーからcitation_keyを取得
            citation_mapping = self.mapping_engine.get_mapping_from_file(markdown_file)
            if not citation_mapping:
                self.logger.warning(f"No citation mapping found in {markdown_file}")
                return None
            
            if citation_number not in citation_mapping.index_map:
                self.logger.warning(f"Citation number {citation_number} not found in mapping")
                return None
            
            citation_key = citation_mapping.index_map[citation_number]
            self.logger.debug(f"Citation [{citation_number}] maps to key: {citation_key}")
            
            # Step 2: references.bibから詳細情報を取得
            bib_entries = self.bibtex_parser.parse_file(citation_mapping.references_file)
            if citation_key not in bib_entries:
                self.logger.warning(f"Citation key '{citation_key}' not found in references.bib")
                return None
            
            bib_entry = bib_entries[citation_key]
            
            # Step 3: BibTeX情報をCitationInfoに変換
            citation_info = self._create_citation_info(
                citation_number, citation_key, bib_entry
            )
            
            # Step 4: 文脈情報を抽出
            context = self.extract_citation_context(markdown_file, citation_number)
            citation_info.context = context
            
            # Step 5: 関連度スコア算出（簡易版）
            citation_info.relevance_score = self._calculate_relevance_score(citation_info)
            
            # キャッシュに保存
            if self.cache_enabled:
                self._citation_cache[cache_key] = citation_info
            
            self.logger.info(f"Citation [{citation_number}] resolved successfully: {citation_info.title[:50]}...")
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
    
    def _create_citation_info(self, number: int, citation_key: str, 
                             bib_entry: Dict[str, str]) -> CitationInfo:
        """BibTeXエントリからCitationInfoを作成"""
        
        # 著者情報の整形
        authors = bib_entry.get('author', 'Unknown Authors')
        authors = self._format_authors(authors)
        
        # 年の抽出
        year_str = bib_entry.get('year', '0')
        try:
            year = int(year_str)
        except ValueError:
            year = 0
        
        # 完全BibTeXエントリの再構築
        full_bibtex = self._reconstruct_bibtex_entry(citation_key, bib_entry)
        
        return CitationInfo(
            number=number,
            citation_key=citation_key,
            title=bib_entry.get('title', 'Unknown Title'),
            authors=authors,
            year=year,
            journal=bib_entry.get('journal', bib_entry.get('booktitle', 'Unknown Journal')),
            volume=bib_entry.get('volume', ''),
            pages=bib_entry.get('pages', ''),
            doi=bib_entry.get('doi', ''),
            full_bibtex=full_bibtex
        )
    
    def _format_authors(self, authors_str: str) -> str:
        """著者情報を整形"""
        if not authors_str or authors_str == 'Unknown Authors':
            return authors_str
        
        # BibTeX形式の著者情報を解析
        # "Last, First and Last2, First2" → "Last, First & Last2, First"
        authors = authors_str.split(' and ')
        formatted_authors = []
        
        for author in authors[:3]:  # 最大3人まで表示
            author = author.strip()
            if ',' in author:
                # "Last, First" 形式 - そのまま保持
                formatted_authors.append(author)
            else:
                # "First Last" 形式 - "Last, First"に変換
                parts = author.split()
                if len(parts) >= 2:
                    last_name = parts[-1]
                    first_names = ' '.join(parts[:-1])
                    formatted_authors.append(f"{last_name}, {first_names}")
                else:
                    formatted_authors.append(author)
        
        if len(authors) > 3:
            formatted_authors.append("et al.")
        
        return ' & '.join(formatted_authors)
    
    def _reconstruct_bibtex_entry(self, citation_key: str, bib_entry: Dict[str, str]) -> str:
        """BibTeXエントリを文字列形式で再構築"""
        entry_type = bib_entry.get('ENTRYTYPE', 'article')
        
        lines = [f"@{entry_type}{{{citation_key},"]
        
        for key, value in bib_entry.items():
            if key != 'ENTRYTYPE' and key != 'ID':
                lines.append(f"  {key} = {{{value}}},")
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def _calculate_relevance_score(self, citation_info: CitationInfo) -> float:
        """関連度スコアを算出（簡易版）"""
        score = 0.0
        
        # DOIがある場合はスコア向上
        if citation_info.doi:
            score += 0.3
        
        # 文脈情報がある場合はスコア向上
        if citation_info.context:
            score += 0.3
        
        # 著者情報が詳細な場合はスコア向上
        if citation_info.authors and citation_info.authors != 'Unknown Authors':
            score += 0.2
        
        # タイトルが適切な場合はスコア向上
        if citation_info.title and citation_info.title != 'Unknown Title':
            score += 0.2
        
        return min(score, 1.0)
    
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