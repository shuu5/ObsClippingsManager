"""
AI Citation Support Workflow Module

AI理解支援引用文献パーサー機能
- fetch機能で生成されたreferences.bibの内容をYAMLヘッダーに統合
- AI理解支援機能を提供
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..shared_modules.config_manager import ConfigManager
from ..shared_modules.integrated_logger import IntegratedLogger
from ..shared_modules.bibtex_parser import BibTeXParser
from ..shared_modules.exceptions import ProcessingError
from ..status_management_yaml.yaml_header_processor import YAMLHeaderProcessor
from ..status_management_yaml.status_manager import StatusManager
from ..status_management_yaml.processing_status import ProcessingStatus


class AICitationSupportWorkflow:
    """
    AI理解支援引用文献パーサー機能
    
    fetch機能で生成されたreferences.bibファイルの内容を解析し、
    YAMLヘッダーのcitation_metadata・citationsセクションに統合する
    """
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        AICitationSupportワークフロー初期化
        
        Args:
            config_manager (ConfigManager): 設定管理クラス
            logger (IntegratedLogger): ログ管理クラス
        """
        self.config_manager = config_manager
        self.integrated_logger = logger  # IntegratedLoggerオブジェクトを保持
        self.logger = logger.get_logger('AICitationSupportWorkflow')
        self.bibtex_parser = BibTeXParser(logger.get_logger('BibTeXParser'))
        self.yaml_processor = YAMLHeaderProcessor(config_manager, logger)
        
        # 設定読み込み
        try:
            self.config = config_manager.get('ai_citation_support', {})
        except Exception:
            # デフォルト設定を使用
            self.config = {
                'enabled': True,
                'mapping_version': '2.0',
                'preserve_existing_citations': False,
                'update_existing_mapping': True,
                'batch_size': 10
            }
        
        self.logger.info("AICitationSupportWorkflow initialized")
    
    def process_items(self, input_dir: str, target_items: Optional[List[str]] = None):
        """
        論文の一括AI理解支援処理
        
        Args:
            input_dir (str): 処理対象ディレクトリ
            target_items (Optional[List[str]]): 処理対象項目（Noneの場合は全て処理）
        """
        self.logger.info(f"Starting AI citation support processing for directory: {input_dir}")
        
        status_manager = StatusManager(self.config_manager, self.integrated_logger)
        papers_needing_processing = status_manager.get_papers_needing_processing(
            input_dir, 'ai_citation_support', target_items
        )
        
        processed_count = 0
        skipped_count = 0
        failed_count = 0
        
        for paper_path in papers_needing_processing:
            try:
                # citation_keyを抽出（ファイルパスから取得）
                citation_key = Path(paper_path).stem
                
                # 論文ディレクトリのreferences.bibファイルを検索
                references_bib_path = self._find_references_bib(paper_path)
                if not references_bib_path:
                    self.logger.warning(
                        f"references.bib not found for {paper_path}, skipping citation integration"
                    )
                    status_manager.update_status(input_dir, citation_key, 'ai_citation_support', ProcessingStatus.SKIPPED)
                    skipped_count += 1
                    continue
                
                # references.bibファイル読み込み・解析（順序・重複保持）
                bibtex_entries_ordered = self.bibtex_parser.parse_file_ordered(references_bib_path)
                citation_mapping = self.create_citation_mapping_ordered(bibtex_entries_ordered, references_bib_path)
                
                # YAMLヘッダー更新
                self.update_yaml_with_citations(paper_path, citation_mapping)
                
                # 処理状態更新
                status_manager.update_status(input_dir, citation_key, 'ai_citation_support', ProcessingStatus.COMPLETED)
                processed_count += 1
                
                self.logger.info(
                    f"Successfully processed AI citation support for {citation_key} "
                    f"({len(citation_mapping['citations'])} citations integrated)"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to add citation support for {paper_path}: {e}")
                citation_key = Path(paper_path).stem
                status_manager.update_status(input_dir, citation_key, 'ai_citation_support', ProcessingStatus.FAILED)
                failed_count += 1
        
        self.logger.info(
            f"AI citation support processing completed: "
            f"{processed_count} processed, {skipped_count} skipped, {failed_count} failed"
        )
    
    def _find_references_bib(self, paper_path: str) -> Optional[str]:
        """
        論文に対応するreferences.bibファイルを検索
        
        Args:
            paper_path (str): 論文ファイルパス
            
        Returns:
            Optional[str]: references.bibファイルパス（見つからない場合はNone）
        """
        paper_dir = Path(paper_path).parent
        references_bib = paper_dir / "references.bib"
        
        if references_bib.exists():
            return str(references_bib)
        else:
            return None
    
    def create_citation_mapping(self, bibtex_entries: Dict[str, Any], 
                              references_bib_path: str) -> Dict[str, Any]:
        """
        BibTeXエントリーから引用マッピングを作成（後方互換性用）
        
        Args:
            bibtex_entries (Dict[str, Any]): BibTeXエントリー辞書
            references_bib_path (str): references.bibファイルパス
            
        Returns:
            Dict[str, Any]: 引用マッピング（citation_metadata + citations）
        """
        citations = {}
        
        # BibTeXエントリーをcitationsフォーマットに変換
        for index, (citation_key, entry) in enumerate(bibtex_entries.items(), 1):
            citations[index] = {
                'number': index,
                'citation_key': citation_key,
                'title': entry.get('title', ''),
                'authors': entry.get('author', ''),
                'year': entry.get('year', ''),
                'journal': entry.get('journal', ''),
                'doi': entry.get('doi', '')
            }
        
        # citation_metadata作成
        citation_metadata = {
            'last_updated': datetime.now().isoformat(),
            'mapping_version': self.config.get('mapping_version', '2.0'),
            'source_bibtex': 'references.bib',
            'references_bib_path': references_bib_path,
            'total_citations': len(bibtex_entries)
        }
        
        return {
            'citation_metadata': citation_metadata,
            'citations': citations
        }
    
    def create_citation_mapping_ordered(self, bibtex_entries_ordered: List[Dict[str, Any]], 
                                      references_bib_path: str) -> Dict[str, Any]:
        """
        順序・重複保持BibTeXエントリーから引用マッピングを作成
        
        Args:
            bibtex_entries_ordered (List[Dict[str, Any]]): 順序保持BibTeXエントリーリスト
            references_bib_path (str): references.bibファイルパス
            
        Returns:
            Dict[str, Any]: 引用マッピング（citation_metadata + citations）
        """
        citations = {}
        
        # 順序保持エントリーをcitationsフォーマットに変換（重複保持）
        for entry in bibtex_entries_ordered:
            number = entry.get('number', 0)
            citations[number] = {
                'number': number,
                'citation_key': entry.get('citation_key', ''),
                'title': entry.get('title', ''),
                'authors': entry.get('author', ''),
                'year': entry.get('year', ''),
                'journal': entry.get('journal', ''),
                'doi': entry.get('doi', '')
            }
        
        # citation_metadata作成
        citation_metadata = {
            'last_updated': datetime.now().isoformat(),
            'mapping_version': self.config.get('mapping_version', '2.0'),
            'source_bibtex': 'references.bib',
            'references_bib_path': references_bib_path,
            'total_citations': len(bibtex_entries_ordered)
        }
        
        return {
            'citation_metadata': citation_metadata,
            'citations': citations
        }
    
    def update_yaml_with_citations(self, paper_path: str, citation_mapping: Dict[str, Any]):
        """
        YAMLヘッダーに引用情報を統合
        
        Args:
            paper_path (str): 論文ファイルパス
            citation_mapping (Dict[str, Any]): 引用マッピング
        """
        # YAMLヘッダー読み込み（Pathオブジェクトに変換）
        yaml_header, content = self.yaml_processor.parse_yaml_header(Path(paper_path))
        
        # citation_metadataセクション更新
        yaml_header['citation_metadata'] = citation_mapping['citation_metadata']
        
        # citationsセクション更新（references.bibの内容のみを使用）
        yaml_header['citations'] = citation_mapping['citations']
        
        # processing_status更新（ai_citation_support: completed）
        if 'processing_status' not in yaml_header:
            yaml_header['processing_status'] = {}
        yaml_header['processing_status']['ai_citation_support'] = 'completed'
        
        # ファイル更新
        self.yaml_processor.write_yaml_header(Path(paper_path), yaml_header, content) 