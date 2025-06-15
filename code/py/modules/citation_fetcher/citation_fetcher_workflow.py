"""
Citation Fetcher Workflow Module

引用文献取得ワークフロー - 外部APIから論文の引用文献を取得し、BibTeX形式で保存
"""

import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..shared_modules.bibtex_parser import BibTeXParser
from ..shared_modules.exceptions import BibTeXError, APIError, ProcessingError
from ..status_management_yaml.yaml_header_processor import YAMLHeaderProcessor
from ..status_management_yaml.status_manager import StatusManager


class CitationFetcherWorkflow:
    """
    引用文献取得ワークフロー
    
    外部APIから論文の引用文献を取得し、BibTeX形式でreferences.bibファイルに保存。
    フォールバック戦略により複数APIを使用して高品質なデータを取得。
    """
    
    def __init__(self, config_manager, logger):
        """
        CitationFetcherWorkflow初期化
        
        Args:
            config_manager: 設定管理インスタンス
            logger: ログシステムインスタンス
        """
        self.config_manager = config_manager
        self.integrated_logger = logger  # IntegratedLoggerインスタンスを保持
        self.logger = logger.get_logger('CitationFetcherWorkflow')
        
        # 共通コンポーネント初期化
        self.bibtex_parser = BibTeXParser(logger.get_logger('BibTeXParser'))
        self.yaml_processor = YAMLHeaderProcessor(config_manager, logger)
        
        # API クライアント（遅延初期化）
        self._crossref_client = None
        self._semantic_scholar_client = None
        self._opencitations_client = None
        
        # サポートクラス（遅延初期化）
        self._rate_limiter = None
        self._quality_evaluator = None
        self._statistics = None
        
        self.logger.debug("CitationFetcherWorkflow initialized")
    
    @property
    def crossref_client(self):
        """CrossRef APIクライアント（遅延初期化）"""
        if self._crossref_client is None:
            from .api_clients import CrossRefAPIClient
            self._crossref_client = CrossRefAPIClient(self.config_manager, self.integrated_logger.get_logger('CrossRefAPIClient'))
        return self._crossref_client
    
    @property
    def semantic_scholar_client(self):
        """Semantic Scholar APIクライアント（遅延初期化）"""
        if self._semantic_scholar_client is None:
            from .api_clients import SemanticScholarAPIClient
            self._semantic_scholar_client = SemanticScholarAPIClient(self.config_manager, self.integrated_logger.get_logger('SemanticScholarAPIClient'))
        return self._semantic_scholar_client
    
    @property
    def opencitations_client(self):
        """OpenCitations APIクライアント（遅延初期化）"""
        if self._opencitations_client is None:
            from .api_clients import OpenCitationsAPIClient
            self._opencitations_client = OpenCitationsAPIClient(self.config_manager, self.integrated_logger.get_logger('OpenCitationsAPIClient'))
        return self._opencitations_client
    
    @property
    def rate_limiter(self):
        """レート制限管理（遅延初期化）"""
        if self._rate_limiter is None:
            from .rate_limiter import RateLimiter
            self._rate_limiter = RateLimiter(self.config_manager, self.integrated_logger.get_logger('RateLimiter'))
        return self._rate_limiter
    
    @property
    def quality_evaluator(self):
        """データ品質評価（遅延初期化）"""
        if self._quality_evaluator is None:
            from .data_quality_evaluator import DataQualityEvaluator
            self._quality_evaluator = DataQualityEvaluator(self.config_manager, self.integrated_logger.get_logger('DataQualityEvaluator'))
        return self._quality_evaluator
    
    @property
    def statistics(self):
        """統計情報管理（遅延初期化）"""
        if self._statistics is None:
            from .citation_statistics import CitationStatistics
            self._statistics = CitationStatistics()
        return self._statistics
    
    def process_items(self, input_dir: str, target_items: Optional[List[str]] = None):
        """
        論文の一括引用文献取得処理
        
        Args:
            input_dir (str): 処理対象ディレクトリ
            target_items (Optional[List[str]]): 対象論文リスト（Noneで全体処理）
        """
        try:
            self.logger.info(f"Starting citation fetcher workflow for directory: {input_dir}")
            
            # 処理対象論文の取得
            status_manager = StatusManager(self.config_manager, self.logger)
            papers_needing_processing = status_manager.get_papers_needing_processing(
                input_dir, 'fetch', target_items
            )
            
            if not papers_needing_processing:
                self.logger.info("No papers need fetch processing")
                return
            
            self.logger.info(f"Found {len(papers_needing_processing)} papers needing fetch processing")
            
            # 各論文の処理
            for paper_path in papers_needing_processing:
                try:
                    self.logger.debug(f"Processing fetch for: {paper_path}")
                    
                    # DOI抽出
                    doi = self.extract_doi_from_paper(paper_path)
                    if not doi:
                        self.logger.warning(f"No DOI found for {paper_path}, skipping citation fetch")
                        status_manager.update_status(input_dir, paper_path, 'fetch', 'skipped')
                        continue
                    
                    # 引用文献取得（フォールバック戦略）
                    citation_data = self.fetch_citations_with_fallback(doi)
                    
                    if citation_data:
                        # references.bib生成
                        references_bib_path = self.generate_references_bib(paper_path, citation_data)
                        
                        # YAMLヘッダー更新
                        self.update_yaml_with_fetch_results(paper_path, citation_data, references_bib_path)
                        
                        status_manager.update_status(input_dir, paper_path, 'fetch', 'completed')
                        self.logger.info(f"Successfully processed fetch for: {paper_path}")
                    else:
                        self.logger.error(f"Failed to fetch citations for {paper_path}")
                        status_manager.update_status(input_dir, paper_path, 'fetch', 'failed')
                        
                except Exception as e:
                    self.logger.error(f"Failed to process citations for {paper_path}: {e}")
                    status_manager.update_status(input_dir, paper_path, 'fetch', 'failed')
            
            self.logger.info("Citation fetcher workflow completed")
            
        except Exception as e:
            self.logger.error(f"Citation fetcher workflow failed: {e}")
            raise ProcessingError(
                f"Citation fetcher workflow failed: {str(e)}",
                error_code="CITATION_FETCHER_WORKFLOW_ERROR",
                context={"input_dir": input_dir, "original_error": str(e)}
            )
    
    def extract_doi_from_paper(self, paper_path: str) -> Optional[str]:
        """
        論文ファイルからDOIを抽出
        
        Args:
            paper_path (str): 論文ファイルのパス
            
        Returns:
            Optional[str]: 抽出されたDOI（見つからない場合はNone）
        """
        try:
            self.logger.debug(f"Extracting DOI from paper: {paper_path}")
            
            # YAMLヘッダーからDOI抽出
            yaml_header, _ = self.yaml_processor.parse_yaml_header(Path(paper_path))
            
            if 'doi' in yaml_header and yaml_header['doi']:
                doi = str(yaml_header['doi']).strip()
                
                # DOI形式の検証
                if self._is_valid_doi_format(doi):
                    normalized_doi = self._normalize_doi(doi)
                    self.logger.debug(f"Extracted DOI: {normalized_doi}")
                    return normalized_doi
                else:
                    self.logger.warning(f"Invalid DOI format in {paper_path}: {doi}")
            
            self.logger.debug(f"No valid DOI found in paper: {paper_path}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting DOI from {paper_path}: {e}")
            return None
    
    def fetch_citations_with_fallback(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        フォールバック戦略による引用文献取得
        
        Args:
            doi (str): 対象論文のDOI
            
        Returns:
            Optional[Dict[str, Any]]: 引用文献データ（失敗時はNone）
        """
        try:
            self.logger.debug(f"Fetching citations for DOI: {doi}")
            
            # API優先順位とパラメータ
            apis = [
                ('crossref', self.crossref_client, 0.8, 10),  # (name, client, quality_threshold, rate_limit)
                ('semantic_scholar', self.semantic_scholar_client, 0.7, 1),
                ('opencitations', self.opencitations_client, 0.5, 5)
            ]
            
            for api_name, client, quality_threshold, rate_limit in apis:
                try:
                    self.logger.debug(f"Trying {api_name} API for DOI: {doi}")
                    
                    # レート制限チェック
                    self.rate_limiter.wait_if_needed(api_name, rate_limit)
                    
                    # API呼び出し
                    data = client.fetch_citations(doi)
                    
                    if data:
                        # データ品質評価
                        quality_score = self.quality_evaluator.evaluate(data)
                        
                        if quality_score >= quality_threshold:
                            self.statistics.record_success(api_name, quality_score)
                            self.logger.info(f"Successfully fetched citations from {api_name} (quality: {quality_score:.2f})")
                            
                            return {
                                'data': data,
                                'api_used': api_name,
                                'quality_score': quality_score,
                                'statistics': self.statistics.get_summary()
                            }
                        else:
                            self.logger.warning(f"Low quality data from {api_name} (quality: {quality_score:.2f}), trying fallback")
                            
                except APIError as e:
                    self.logger.warning(f"API error from {api_name}: {e}, trying fallback")
                    self.statistics.record_failure(api_name, str(e))
                except Exception as e:
                    self.logger.error(f"Unexpected error from {api_name}: {e}")
                    self.statistics.record_failure(api_name, str(e))
            
            self.logger.error(f"All APIs failed for DOI: {doi}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error in fetch citations with fallback: {e}")
            return None
    
    def generate_references_bib(self, paper_path: str, citation_data: Dict[str, Any]) -> str:
        """
        references.bibファイル生成
        
        Args:
            paper_path (str): 論文ファイルのパス
            citation_data (Dict[str, Any]): 引用文献データ
            
        Returns:
            str: 生成されたreferences.bibファイルのパス
        """
        try:
            paper_dir = Path(paper_path).parent
            references_bib_path = paper_dir / "references.bib"
            
            # BibTeX形式でデータを変換
            bibtex_content = self._convert_to_bibtex(citation_data['data'])
            
            # ファイル保存
            with open(references_bib_path, 'w', encoding='utf-8') as f:
                f.write(bibtex_content)
            
            self.logger.info(f"Generated references.bib: {references_bib_path}")
            return str(references_bib_path)
            
        except Exception as e:
            self.logger.error(f"Failed to generate references.bib for {paper_path}: {e}")
            raise ProcessingError(
                f"Failed to generate references.bib: {str(e)}",
                error_code="REFERENCES_BIB_GENERATION_ERROR",
                context={"paper_path": paper_path, "original_error": str(e)}
            )
    
    def update_yaml_with_fetch_results(self, paper_path: str, citation_data: Dict[str, Any], 
                                     references_bib_path: str):
        """
        YAMLヘッダーにfetch結果を記録
        
        Args:
            paper_path (str): 論文ファイルのパス
            citation_data (Dict[str, Any]): 引用文献データ
            references_bib_path (str): references.bibファイルのパス
        """
        try:
            # YAMLヘッダー読み込み
            yaml_header, content = self.yaml_processor.parse_yaml_header(Path(paper_path))
            
            # citation_metadataセクション更新
            current_time = datetime.now().isoformat()
            yaml_header['citation_metadata'] = {
                'last_updated': current_time,
                'fetch_completed_at': current_time,
                'primary_api_used': citation_data['api_used'],
                'total_references_found': len(citation_data['data']),
                'quality_score': citation_data['quality_score'],
                'references_bib_path': Path(references_bib_path).name,
                'api_statistics': citation_data['statistics']
            }
            
            # processing_status更新
            yaml_header['processing_status']['fetch'] = 'completed'
            yaml_header['last_updated'] = current_time
            
            # ファイル保存
            self.yaml_processor.write_yaml_header(Path(paper_path), yaml_header, content)
            
            self.logger.debug(f"Updated YAML header with fetch results: {paper_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to update YAML header for {paper_path}: {e}")
            raise ProcessingError(
                f"Failed to update YAML header: {str(e)}",
                error_code="YAML_UPDATE_ERROR",
                context={"paper_path": paper_path, "original_error": str(e)}
            )
    
    def _convert_to_bibtex(self, citation_data: List[Dict[str, Any]]) -> str:
        """
        引用文献データをBibTeX形式に変換
        
        Args:
            citation_data (List[Dict[str, Any]]): 引用文献データ
            
        Returns:
            str: BibTeX形式の文字列
        """
        try:
            bibtex_entries = []
            
            for i, citation in enumerate(citation_data):
                # citation_key生成（簡易実装）
                citation_key = f"ref{i+1:03d}"
                if 'authors' in citation and citation['authors']:
                    # 最初の著者の苗字を抽出（簡易）
                    first_author = citation['authors'].split(',')[0].strip()
                    year = citation.get('year', 'unknown')
                    citation_key = f"{first_author.lower()}{year}"
                
                # エントリタイプ決定
                entry_type = "article"
                if 'journal' not in citation or not citation['journal']:
                    entry_type = "misc"
                
                # BibTeXエントリ構築
                entry_lines = [f"@{entry_type}{{{citation_key},"]
                
                # フィールド追加
                for field, value in citation.items():
                    if value and field != 'citation_key':
                        # フィールド名の正規化
                        bibtex_field = self._normalize_bibtex_field(field)
                        if bibtex_field:
                            clean_value = str(value).replace('{', '').replace('}', '')
                            entry_lines.append(f"  {bibtex_field} = {{{clean_value}}},")
                
                entry_lines.append("}")
                bibtex_entries.append("\n".join(entry_lines))
            
            return "\n\n".join(bibtex_entries) + "\n"
            
        except Exception as e:
            self.logger.error(f"Error converting citation data to BibTeX: {e}")
            raise ProcessingError(
                f"Failed to convert to BibTeX: {str(e)}",
                error_code="BIBTEX_CONVERSION_ERROR",
                context={"original_error": str(e)}
            )
    
    def _normalize_bibtex_field(self, field: str) -> Optional[str]:
        """
        フィールド名をBibTeX形式に正規化
        
        Args:
            field (str): 元のフィールド名
            
        Returns:
            Optional[str]: BibTeXフィールド名（対応なしの場合はNone）
        """
        field_mapping = {
            'title': 'title',
            'authors': 'author',
            'author': 'author',
            'journal': 'journal',
            'year': 'year',
            'volume': 'volume',
            'number': 'number',
            'pages': 'pages',
            'doi': 'doi',
            'url': 'url',
            'publisher': 'publisher',
            'booktitle': 'booktitle'
        }
        
        return field_mapping.get(field.lower())
    
    def _is_valid_doi_format(self, doi: str) -> bool:
        """
        DOI形式の基本検証
        
        Args:
            doi (str): 検証対象のDOI文字列
            
        Returns:
            bool: 有効なDOI形式かどうか
        """
        if not doi or not isinstance(doi, str):
            return False
        
        # DOIの基本パターン（10.で始まり、/を含む）
        doi_pattern = r'(?:https?://(?:dx\.)?doi\.org/|doi:)?10\.\d+/.+'
        
        return bool(re.match(doi_pattern, doi.strip(), re.IGNORECASE))
    
    def _normalize_doi(self, doi: str) -> str:
        """
        DOIの正規化
        
        Args:
            doi (str): 生のDOI文字列
            
        Returns:
            str: 正規化されたDOI
        """
        # URLプレフィックスを削除
        doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', doi)
        doi = re.sub(r'^doi:', '', doi, flags=re.IGNORECASE)
        
        return doi.strip() 