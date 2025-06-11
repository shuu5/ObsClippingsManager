"""
AI理解支援引用文献マッピングエンジン v4.0

完全な引用文献情報をYAMLヘッダーに統合し、
自己完結型ファイルを生成するマッピングエンジン。
"""

import re
import time
import logging
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from datetime import datetime

import yaml

from .data_structures import CitationMapping, CitationInfo
from ..shared.bibtex_parser import BibTeXParser
from ..shared.logger import get_integrated_logger


class CitationMappingEngine:
    """引用マッピング作成エンジン"""
    
    def __init__(self, config_manager=None):
        """
        初期化
        
        Args:
            config_manager: 設定管理インスタンス
        """
        self.logger = get_integrated_logger().get_logger("AICitationSupport.MappingEngine")
        self.config_manager = config_manager
        self.bibtex_parser = BibTeXParser()
        

        
        self.logger.info("CitationMappingEngine initialized")
    
    def create_citation_mapping(self, markdown_file: str, references_bib: str = None) -> CitationMapping:
        """
        引用マッピングを作成（シンプル版）
        references.bibの内容をそのまま順番通りにマッピング
        
        Args:
            markdown_file: Markdownファイルパス
            references_bib: references.bibファイルパス（Noneの場合は自動推測）
            
        Returns:
            CitationMapping: 作成されたマッピング
        """
        start_time = time.time()
        
        try:
            # references.bibパスの決定
            if references_bib is None:
                # Markdownファイルと同じディレクトリのreferences.bibを使用
                markdown_path = Path(markdown_file)
                references_bib = str(markdown_path.parent / "references.bib")
            
            self.logger.info(f"Creating citation mapping from {references_bib}")
            
            # references.bibから論文情報を読み込み（重複を含む）
            bib_entries_list = []
            if Path(references_bib).exists():
                try:
                    bib_entries_list = self.bibtex_parser.parse_file_with_duplicates(references_bib)
                    self.logger.info(f"Loaded {len(bib_entries_list)} entries from {references_bib}")
                except Exception as e:
                    self.logger.warning(f"Failed to parse {references_bib}: {e}")
            else:
                self.logger.warning(f"References file not found: {references_bib}")
                return CitationMapping(
                    index_map={},
                    total_citations=0,
                    last_updated=datetime.now().isoformat(),
                    references_file=references_bib,
                    mapping_version="2.0"
                )
            
            # references.bibの順序通りにマッピング（重複を含む）
            index_map = {}
            for i, bib_entry in enumerate(bib_entries_list):
                citation_num = i + 1  # 1から開始
                bib_key = bib_entry.get('citation_key', f'entry_{i}')
                
                # 論文情報をそのまま抽出
                citation_info = CitationInfo(
                    citation_key=bib_key,
                    title=bib_entry.get('title', '').strip('{}'),
                    authors=bib_entry.get('author', '').replace(' and ', ', '),
                    year=int(bib_entry.get('year', 0)),
                    journal=bib_entry.get('journal', ''),
                    volume=bib_entry.get('volume', ''),
                    pages=bib_entry.get('pages', ''),
                    doi=bib_entry.get('doi', ''),
                    url=bib_entry.get('url', '')
                )
                
                index_map[citation_num] = citation_info
                self.logger.info(f"Mapped citation [{citation_num}] to {bib_key}: {citation_info.title[:50]}...")
            
            mapping = CitationMapping(
                index_map=index_map,
                total_citations=len(index_map),  # BibTeXエントリー数そのまま
                last_updated=datetime.now().isoformat(),
                references_file=references_bib,
                mapping_version="2.0"
            )
            
            processing_time = time.time() - start_time
            self.logger.info(f"Citation mapping created in {processing_time:.2f}s: {len(index_map)} mappings")
            
            return mapping
            
        except Exception as e:
            self.logger.error(f"Failed to create citation mapping: {e}")
            raise
    
    def update_yaml_header(self, markdown_file: str, mapping: CitationMapping) -> bool:
        """
        YAMLヘッダーにマッピング情報を追加・更新
        
        Args:
            markdown_file: 対象Markdownファイル
            mapping: 追加するマッピング情報
            
        Returns:
            更新成功時 True, 失敗時 False
        """
        try:
            self.logger.info(f"Updating YAML header in {markdown_file}")
            
            # 現在のファイル内容を読み込み
            with open(markdown_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # YAMLヘッダーとbodyを分離
            yaml_header, body = self._parse_markdown_with_yaml(content)
            
            # citation_keyを取得（ファイル名から推測）
            citation_key = Path(markdown_file).stem
            
            # 新しいYAMLヘッダー構造に従って更新
            if yaml_header is None:
                yaml_header = {}
            
            # 1. citations セクション（完全な論文情報、abstractとnumberは除外）
            # 引用番号は本文の番号をそのまま使用（本文[1]→表示1、本文[2]→表示2）
            citations = {}
            for citation_num, citation_info in mapping.index_map.items():
                citations[citation_num] = {
                    'citation_key': citation_info.citation_key,
                    'title': citation_info.title,
                    'authors': citation_info.authors,
                    'year': citation_info.year,
                    'journal': citation_info.journal,
                    'volume': citation_info.volume,
                    'pages': citation_info.pages,
                    'doi': citation_info.doi
                }
                if citation_info.url:
                    citations[citation_num]['url'] = citation_info.url
            
            yaml_header['citations'] = citations
            
            # 2. citation_metadata セクション
            yaml_header['citation_metadata'] = {
                'total_citations': mapping.total_citations,
                'last_updated': mapping.last_updated,
                'source_bibtex': Path(mapping.references_file).name,
                'mapping_version': mapping.mapping_version
            }
            
            # 3. メタデータセクション（従来の互換性のため）
            yaml_header['citation_key'] = citation_key
            yaml_header['last_updated'] = mapping.last_updated
            yaml_header['workflow_version'] = "3.0"
            
            # 4. 処理状態管理（existing status are preserved）
            if 'processing_status' not in yaml_header:
                yaml_header['processing_status'] = {
                    'organize': 'pending',
                    'sync': 'pending', 
                    'fetch': 'pending',
                    'ai-citation-support': 'pending'
                }
            
            # 更新されたコンテンツを書き戻し
            new_content = self._reconstruct_markdown_with_yaml(yaml_header, body)
            
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            self.logger.info(f"YAML header updated successfully: {len(mapping.index_map)} mappings added")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update YAML header: {e}")
            return False
    

    

    
    def _parse_markdown_with_yaml(self, content: str) -> Tuple[Optional[Dict], str]:
        """ファイル内容からYAMLヘッダーとボディを分離"""
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
    
    def _reconstruct_markdown_with_yaml(self, yaml_data: Dict, body_content: str) -> str:
        """YAMLヘッダーとボディを結合して新しいファイル内容を作成"""
        if yaml_data:
            yaml_content = yaml.dump(yaml_data, default_flow_style=False, allow_unicode=True)
            return f"---\n{yaml_content}---\n{body_content}"
        else:
            return body_content
    
    def get_mapping_from_file(self, markdown_file: str) -> Optional[CitationMapping]:
        """
        MarkdownファイルからCitationMappingを取得
        
        Args:
            markdown_file: Markdownファイルパス
            
        Returns:
            CitationMapping or None
        """
        try:
            with open(markdown_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            yaml_header, _ = self._parse_markdown_with_yaml(content)
            
            if not yaml_header or 'citations' not in yaml_header:
                return None
            
            # 新しい形式のYAMLヘッダーからCitationMappingを復元
            citations_data = yaml_header['citations']
            citation_metadata = yaml_header.get('citation_metadata', {})
            
            index_map = {}
            for citation_num_str, citation_data in citations_data.items():
                citation_num = int(citation_num_str)
                citation_info = CitationInfo(
                    citation_key=citation_data.get('citation_key', ''),
                    title=citation_data.get('title', ''),
                    authors=citation_data.get('authors', ''),
                    year=citation_data.get('year', 0),
                    journal=citation_data.get('journal', ''),
                    volume=citation_data.get('volume', ''),
                    pages=citation_data.get('pages', ''),
                    doi=citation_data.get('doi', ''),
                    url=citation_data.get('url', '')
                )
                index_map[citation_num] = citation_info
            
            return CitationMapping(
                index_map=index_map,
                total_citations=citation_metadata.get('total_citations', len(index_map)),
                last_updated=citation_metadata.get('last_updated', ''),
                references_file=citation_metadata.get('source_bibtex', ''),
                mapping_version=citation_metadata.get('mapping_version', '2.0'),
                is_self_contained=True
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get mapping from file {markdown_file}: {e}")
            return None 