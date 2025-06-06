"""
sync機能連携モジュール

Citation Fetcher v2.1における同期チェック機能との連携を提供します。
CurrentManuscript.bibとClippings/ディレクトリの一致確認および
対象論文の特定を行います。
"""

import logging
from typing import Dict, List, Any, Tuple, Optional, Set
from pathlib import Path

from ..shared.bibtex_parser import BibTeXParser
from ..shared.exceptions import SyncCheckError, BibTeXParsingError, ClippingsAccessError


class SyncIntegration:
    """sync機能連携クラス"""
    
    def __init__(self, config_manager, logger):
        """
        Args:
            config_manager: 設定管理インスタンス
            logger: 統合ロガーインスタンス
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('CitationFetcher.SyncIntegration')
        self.config = config_manager.get_citation_fetcher_config()
        
        # BibTeX解析器の初期化
        self.bibtex_parser = BibTeXParser()
        
    def get_synced_papers_info(self) -> Tuple[bool, Dict[str, Any]]:
        """
        同期状態を確認し、一致している論文の情報を取得
        
        Returns:
            (成功フラグ, 同期情報詳細)
        """
        self.logger.info("Starting sync integration analysis")
        
        try:
            # BibTeXファイルの解析
            bib_entries = self._parse_bibtex_file()
            
            # Clippingsディレクトリの確認
            clippings_dirs = self._get_clippings_directories()
            
            # 一致している論文を特定
            synced_papers = self._identify_synced_papers(bib_entries, clippings_dirs)
            
            # DOI情報の抽出
            papers_with_dois = self._extract_doi_information(synced_papers, bib_entries)
            
            # ディレクトリパスの確認
            validated_papers = self._validate_directory_paths(papers_with_dois)
            
            sync_info = {
                "total_papers_in_bib": len(bib_entries),
                "total_directories_in_clippings": len(clippings_dirs),
                "synced_papers_count": len(synced_papers),
                "papers_with_valid_dois": len(papers_with_dois),
                "validated_papers": validated_papers,
                "sync_rate": len(synced_papers) / len(bib_entries) * 100 if bib_entries else 0
            }
            
            self.logger.info(
                f"Sync analysis completed: {len(synced_papers)}/{len(bib_entries)} papers synced"
            )
            
            return True, sync_info
            
        except Exception as e:
            self.logger.error(f"Sync integration analysis failed: {e}")
            return False, {"error": str(e)}
    
    def get_target_papers_for_citation_fetching(self) -> Tuple[bool, List[Dict[str, str]]]:
        """
        引用文献取得の対象論文リストを生成
        
        Returns:
            (成功フラグ, 対象論文リスト)
        """
        success, sync_info = self.get_synced_papers_info()
        
        if not success:
            return False, []
        
        validated_papers = sync_info.get("validated_papers", [])
        
        # 有効なDOIを持つ論文のみを対象とする
        target_papers = [
            paper for paper in validated_papers 
            if paper.get("doi") and paper["doi"].strip()
        ]
        
        self.logger.info(f"Identified {len(target_papers)} target papers for citation fetching")
        
        return True, target_papers
    
    def _parse_bibtex_file(self) -> Dict[str, Dict[str, Any]]:
        """BibTeXファイルを解析"""
        try:
            bibtex_file = self.config.get('bibtex_file')
            if not bibtex_file:
                # デフォルトパスを試行
                bibtex_file = self.config_manager.get_sync_check_config().get('bibtex_file')
            
            if not bibtex_file or not Path(bibtex_file).exists():
                raise BibTeXParsingError(f"BibTeX file not found: {bibtex_file}")
                
            self.logger.info(f"Parsing BibTeX file: {bibtex_file}")
            return self.bibtex_parser.parse_file(bibtex_file)
            
        except Exception as e:
            raise BibTeXParsingError(f"Failed to parse BibTeX file: {e}")
    
    def _get_clippings_directories(self) -> List[str]:
        """Clippings内のサブディレクトリ一覧を取得"""
        try:
            clippings_dir = self.config.get('clippings_dir')
            if not clippings_dir:
                # デフォルトパスを試行
                clippings_dir = self.config_manager.get_sync_check_config().get('clippings_dir')
            
            clippings_path = Path(clippings_dir)
            if not clippings_path.exists():
                raise ClippingsAccessError(f"Clippings directory not found: {clippings_path}")
            
            directories = [d.name for d in clippings_path.iterdir() if d.is_dir()]
            self.logger.info(f"Found {len(directories)} directories in Clippings")
            
            return directories
            
        except Exception as e:
            raise ClippingsAccessError(f"Failed to access Clippings directory: {e}")
    
    def _identify_synced_papers(self, bib_entries: Dict[str, Dict], clippings_dirs: List[str]) -> Set[str]:
        """一致している論文のcitation_keyを特定"""
        bib_keys = set(bib_entries.keys())
        clipping_keys = set(clippings_dirs)
        
        synced_papers = bib_keys.intersection(clipping_keys)
        
        self.logger.info(f"Identified {len(synced_papers)} synced papers")
        self.logger.debug(f"Synced papers: {sorted(synced_papers)}")
        
        return synced_papers
    
    def _extract_doi_information(self, synced_papers: Set[str], bib_entries: Dict[str, Dict]) -> List[Dict[str, str]]:
        """同期済み論文からDOI情報を抽出"""
        papers_with_dois = []
        
        for citation_key in synced_papers:
            if citation_key in bib_entries:
                entry = bib_entries[citation_key]
                
                # DOIの正規化（空白や改行を除去）
                doi_raw = entry.get('doi', '').strip()
                doi_clean = doi_raw.replace('\n', '').replace('\r', '') if doi_raw else ''
                
                paper_info = {
                    'citation_key': citation_key,
                    'doi': doi_clean,
                    'title': entry.get('title', ''),
                    'authors': entry.get('author', ''),
                    'year': entry.get('year', ''),
                    'has_valid_doi': bool(doi_clean)
                }
                
                papers_with_dois.append(paper_info)
        
        valid_doi_count = sum(1 for paper in papers_with_dois if paper['has_valid_doi'])
        self.logger.info(f"Found {valid_doi_count}/{len(papers_with_dois)} papers with valid DOIs")
        
        return papers_with_dois
    
    def _validate_directory_paths(self, papers_with_dois: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """ディレクトリパスの存在確認と保存先パス生成"""
        clippings_dir = self.config.get('clippings_dir')
        if not clippings_dir:
            clippings_dir = self.config_manager.get_sync_check_config().get('clippings_dir')
        
        clippings_path = Path(clippings_dir)
        validated_papers = []
        
        for paper in papers_with_dois:
            citation_key = paper['citation_key']
            paper_dir = clippings_path / citation_key
            references_file = paper_dir / "references.bib"
            
            # ディレクトリ存在確認
            if paper_dir.exists() and paper_dir.is_dir():
                paper_info = paper.copy()
                paper_info.update({
                    'directory_path': str(paper_dir),
                    'references_file_path': str(references_file),
                    'references_file_exists': references_file.exists(),
                    'directory_validated': True
                })
                validated_papers.append(paper_info)
            else:
                self.logger.warning(f"Directory not found for {citation_key}: {paper_dir}")
        
        self.logger.info(f"Validated {len(validated_papers)} paper directories")
        
        return validated_papers
    
    def prepare_backup_existing_references(self, target_papers: List[Dict[str, str]]) -> Dict[str, bool]:
        """既存のreferences.bibファイルのバックアップを準備"""
        backup_results = {}
        
        for paper in target_papers:
            citation_key = paper['citation_key']
            references_file = Path(paper['references_file_path'])
            
            if references_file.exists():
                backup_file = references_file.with_suffix('.bib.backup')
                
                try:
                    # バックアップ作成
                    backup_file.write_text(references_file.read_text(encoding='utf-8'))
                    backup_results[citation_key] = True
                    self.logger.info(f"Created backup for {citation_key}: {backup_file}")
                except Exception as e:
                    backup_results[citation_key] = False
                    self.logger.error(f"Failed to backup {citation_key}: {e}")
            else:
                backup_results[citation_key] = True  # ファイルが存在しない場合は成功扱い
        
        return backup_results
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """同期状態の統計情報を取得"""
        success, sync_info = self.get_synced_papers_info()
        
        if not success:
            return {"error": sync_info.get("error", "Unknown error")}
        
        return {
            "total_papers_in_bib": sync_info["total_papers_in_bib"],
            "total_directories_in_clippings": sync_info["total_directories_in_clippings"],
            "synced_papers": sync_info["synced_papers_count"],
            "sync_rate": round(sync_info["sync_rate"], 1),
            "papers_with_valid_dois": sync_info["papers_with_valid_dois"],
            "doi_coverage": round(
                sync_info["papers_with_valid_dois"] / sync_info["synced_papers_count"] * 100
                if sync_info["synced_papers_count"] > 0 else 0, 1
            )
        }


def create_sync_integration_from_config(config_manager, logger) -> SyncIntegration:
    """
    設定からsync連携インスタンスを作成
    
    Args:
        config_manager: 設定管理インスタンス
        logger: ロガーインスタンス
        
    Returns:
        SyncIntegrationインスタンス
    """
    return SyncIntegration(config_manager, logger)


def get_synced_papers_dois(config_manager, logger) -> List[str]:
    """
    同期済み論文のDOIリストを取得（簡易版）
    
    Args:
        config_manager: 設定管理インスタンス
        logger: ロガーインスタンス
        
    Returns:
        DOIのリスト
    """
    sync_integration = create_sync_integration_from_config(config_manager, logger)
    success, target_papers = sync_integration.get_target_papers_for_citation_fetching()
    
    if success:
        return [paper['doi'] for paper in target_papers if paper.get('doi')]
    else:
        return [] 