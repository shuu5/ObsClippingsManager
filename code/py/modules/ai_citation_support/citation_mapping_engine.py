"""
軽量引用マッピング作成エンジン v4.0

YAMLヘッダーに最小限のマッピング情報を追加し、
references.bibとの動的連携を可能にします。
"""

import re
import time
import logging
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from datetime import datetime

import yaml

from .data_structures import CitationMapping, MappingStatistics
from ..shared.bibtex_parser import BibTeXParser
from ..shared.logger import get_integrated_logger


class CitationMappingEngine:
    """軽量引用マッピング作成エンジン"""
    
    def __init__(self, config_manager=None):
        """
        初期化
        
        Args:
            config_manager: 設定管理インスタンス
        """
        self.logger = get_integrated_logger().get_logger("AICitationSupport.MappingEngine")
        self.config_manager = config_manager
        self.bibtex_parser = BibTeXParser()
        
        # 引用番号検出パターン
        self.citation_patterns = [
            r'\[(\d+)\]',                    # [1]
            r'\[(\d+(?:,\s*\d+)*)\]',       # [1,2,3] or [1, 2, 3]
            r'\[(\d+)[-–](\d+)\]',          # [1-5] or [1–5]
            r'\[\^(\d+)\]',                 # [^1]
            r'\\?\[\[(\d+)\]\\?\]',         # \[[1]\] (エスケープ)
            r'\\?\[\[\^(\d+)\]\\?\]',       # \[[^1]\] (エスケープ脚注)
            r'\\?\[\[(\d+(?:,\s*\d+)*)\]\\?\]',  # \[[1,2,3]\] (エスケープ複数)
        ]
        
        self.logger.info("CitationMappingEngine initialized")
    
    def create_citation_mapping(self, markdown_file: str, references_bib: str) -> CitationMapping:
        """
        引用番号とcitation_keyの軽量マッピングを作成
        
        Args:
            markdown_file: 対象Markdownファイル
            references_bib: 対応するreferences.bibファイル
            
        Returns:
            CitationMapping: マッピング情報オブジェクト
            
        Process:
        1. Markdownファイル内の引用番号を検出
        2. references.bibからcitation_keyを抽出
        3. 引用順序に基づいてマッピング作成
        4. YAMLヘッダーに軽量マッピング情報を追加
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Creating citation mapping for {markdown_file}")
            
            # Step 1: Markdownファイル内の引用番号を検出
            citation_numbers = self._extract_citation_numbers(markdown_file)
            if not citation_numbers:
                self.logger.warning(f"No citations found in {markdown_file}")
                return self._create_empty_mapping(references_bib)
            
            self.logger.info(f"Found {len(citation_numbers)} unique citations: {sorted(citation_numbers)}")
            
            # Step 2: references.bibからcitation_keyを抽出
            citation_keys = self._extract_citation_keys(references_bib)
            if not citation_keys:
                self.logger.warning(f"No citation keys found in {references_bib}")
                return self._create_empty_mapping(references_bib)
            
            self.logger.info(f"Found {len(citation_keys)} citation keys in references.bib")
            
            # Step 3: 引用番号とcitation_keyの対応関係を作成
            index_map = self._create_index_mapping(citation_numbers, citation_keys)
            
            # Step 4: CitationMappingオブジェクトを作成
            mapping = CitationMapping(
                references_file=str(Path(references_bib).resolve()),
                index_map=index_map,
                last_updated=datetime.now(),
                mapping_version="1.0",
                total_citations=len(index_map)
            )
            
            processing_time = time.time() - start_time
            self.logger.info(f"Citation mapping created in {processing_time:.2f}s: {len(index_map)} mappings")
            
            return mapping
            
        except Exception as e:
            self.logger.error(f"Failed to create citation mapping: {e}")
            raise
    
    def update_yaml_header(self, markdown_file: str, citation_mapping: CitationMapping) -> bool:
        """
        YAMLヘッダーにマッピング情報を追加・更新
        
        Args:
            markdown_file: 対象Markdownファイル
            citation_mapping: 作成されたマッピング情報
            
        Returns:
            成功フラグ
        """
        try:
            file_path = Path(markdown_file)
            if not file_path.exists():
                self.logger.error(f"Markdown file not found: {markdown_file}")
                return False
            
            self.logger.info(f"Updating YAML header in {markdown_file}")
            
            # ファイル内容を読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 既存のYAMLヘッダーを検出・解析
            yaml_header, content_body = self._extract_yaml_header(content)
            
            # citation_mappingセクションを追加/更新
            yaml_header['citation_mapping'] = citation_mapping.to_yaml_dict()
            
            # 新しいファイル内容を作成
            new_content = self._reconstruct_file_with_yaml(yaml_header, content_body)
            
            # ファイルに書き戻し
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            self.logger.info(f"YAML header updated successfully: {len(citation_mapping.index_map)} mappings added")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update YAML header: {e}")
            return False
    
    def _extract_citation_numbers(self, markdown_file: str) -> Set[int]:
        """Markdownファイルから引用番号を抽出"""
        try:
            with open(markdown_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.logger.error(f"Failed to read markdown file {markdown_file}: {e}")
            return set()
        
        citation_numbers = set()
        
        for pattern in self.citation_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                # パターンに応じて引用番号を抽出
                if pattern.startswith(r'\[(\d+)[-–](\d+)\]'):
                    # 範囲引用: [1-5]
                    start_num = int(match.group(1))
                    end_num = int(match.group(2))
                    citation_numbers.update(range(start_num, end_num + 1))
                elif '(?:,\\s*\\d+)*' in pattern:
                    # 複数引用: [1,2,3]
                    numbers_str = match.group(1)
                    for num_str in re.split(r'[,\s]+', numbers_str):
                        if num_str.strip():
                            citation_numbers.add(int(num_str.strip()))
                else:
                    # 単一引用
                    num_str = match.group(1)
                    if num_str.strip():
                        citation_numbers.add(int(num_str.strip()))
        
        # 脚注記号を除去した番号も追加（^記号がある場合）
        footnote_pattern = r'\[\^(\d+)\]'
        footnote_matches = re.finditer(footnote_pattern, content)
        for match in footnote_matches:
            citation_numbers.add(int(match.group(1)))
        
        return citation_numbers
    
    def _extract_citation_keys(self, references_bib: str) -> List[str]:
        """references.bibからcitation_keyを抽出"""
        try:
            bib_entries = self.bibtex_parser.parse_file(references_bib)
            citation_keys = list(bib_entries.keys())
            return citation_keys
        except Exception as e:
            self.logger.error(f"Failed to parse BibTeX file {references_bib}: {e}")
            return []
    
    def _create_index_mapping(self, citation_numbers: Set[int], citation_keys: List[str]) -> Dict[int, str]:
        """引用番号とcitation_keyの対応関係を作成"""
        # 引用番号をソート
        sorted_numbers = sorted(citation_numbers)
        
        # citation_keyの数が足りない場合の警告
        if len(citation_keys) < len(sorted_numbers):
            self.logger.warning(
                f"Insufficient citation keys ({len(citation_keys)}) for citation numbers ({len(sorted_numbers)})"
            )
        
        # 1:1対応でマッピング作成
        index_map = {}
        for i, number in enumerate(sorted_numbers):
            if i < len(citation_keys):
                index_map[number] = citation_keys[i]
            else:
                # citation_keyが足りない場合はプレースホルダーを使用
                index_map[number] = f"placeholder_{number}"
                self.logger.warning(f"Using placeholder for citation number {number}")
        
        return index_map
    
    def _create_empty_mapping(self, references_bib: str) -> CitationMapping:
        """空のマッピングを作成"""
        return CitationMapping(
            references_file=str(Path(references_bib).resolve()),
            index_map={},
            last_updated=datetime.now(),
            mapping_version="1.0",
            total_citations=0
        )
    
    def _extract_yaml_header(self, content: str) -> Tuple[Dict, str]:
        """ファイル内容からYAMLヘッダーとボディを分離"""
        # YAML frontmatterのパターン
        yaml_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)'
        match = re.match(yaml_pattern, content, re.DOTALL)
        
        if match:
            try:
                yaml_content = match.group(1)
                body_content = match.group(2)
                yaml_data = yaml.safe_load(yaml_content) or {}
                return yaml_data, body_content
            except yaml.YAMLError as e:
                self.logger.warning(f"Failed to parse existing YAML header: {e}")
                return {}, content
        else:
            # YAMLヘッダーが存在しない場合
            return {}, content
    
    def _reconstruct_file_with_yaml(self, yaml_data: Dict, body_content: str) -> str:
        """YAMLヘッダーとボディを結合して新しいファイル内容を作成"""
        if yaml_data:
            yaml_content = yaml.dump(yaml_data, default_flow_style=False, allow_unicode=True)
            return f"---\n{yaml_content}---\n{body_content}"
        else:
            return body_content
    
    def get_mapping_from_file(self, markdown_file: str) -> Optional[CitationMapping]:
        """ファイルから既存のマッピング情報を取得"""
        try:
            with open(markdown_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            yaml_header, _ = self._extract_yaml_header(content)
            
            if 'citation_mapping' in yaml_header:
                mapping_data = yaml_header['citation_mapping']
                return CitationMapping.from_yaml_dict(mapping_data)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get mapping from file {markdown_file}: {e}")
            return None 