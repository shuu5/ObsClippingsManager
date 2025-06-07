#!/usr/bin/env python3
"""
PubMed APIクライアント
metapubライブラリを使用して、DOIからPubMedの詳細な書誌情報を取得する
"""

import time
from typing import Dict, Optional, List
from dataclasses import dataclass
import re

try:
    from metapub import PubMedFetcher
    from metapub.convert import doi2pmid
    METAPUB_AVAILABLE = True
except ImportError:
    METAPUB_AVAILABLE = False

from ..shared.logger import get_integrated_logger
from ..shared.config_manager import ConfigManager


@dataclass
class PubMedMetadata:
    """PubMedから取得したメタデータ"""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    year: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    pmid: Optional[str] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    mesh_terms: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'title': self.title,
            'authors': self.authors,
            'journal': self.journal,
            'year': self.year,
            'volume': self.volume,
            'issue': self.issue,
            'pages': self.pages,
            'pmid': self.pmid,
            'doi': self.doi,
            'abstract': self.abstract,
            'mesh_terms': self.mesh_terms
        }
    
    def is_complete(self) -> bool:
        """必須フィールドが全て揃っているかチェック"""
        return all([
            self.title,
            self.authors,
            self.journal,
            self.year
        ])


class PubMedClient:
    """PubMed APIクライアント"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初期化
        
        Args:
            config_manager: 設定マネージャー
        """
        self.logger = get_integrated_logger().get_logger("CitationFetcher.PubMed")
        self.config = config_manager or ConfigManager()
        
        # metapubライブラリの可用性チェック
        if not METAPUB_AVAILABLE:
            self.logger.error("metapub library is not available. Install with: uv add metapub")
            self.fetcher = None
            return
        
        try:
            self.fetcher = PubMedFetcher()
            self.logger.info("PubMed client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize PubMed client: {e}")
            self.fetcher = None
        
        # レート制限設定（デフォルト1秒）
        self.rate_limit_delay = self.config.get_config_value(
            'citation_fetcher.metadata_enrichment.rate_limits.pubmed', 
            1.0
        )
        
        self.last_request_time = 0
    
    def _enforce_rate_limit(self):
        """レート制限を実行"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _normalize_authors(self, authors: List[str]) -> List[str]:
        """著者名を正規化（PubMed形式からBibTeX形式へ）"""
        if not authors:
            return []
        
        normalized = []
        for author in authors:
            # "Last, First Middle" 形式を "First Middle Last" 形式に変換
            if ',' in author:
                parts = author.split(',', 1)
                if len(parts) == 2:
                    last_name = parts[0].strip()
                    first_names = parts[1].strip()
                    normalized.append(f"{first_names} {last_name}")
                else:
                    normalized.append(author.strip())
            else:
                normalized.append(author.strip())
        
        return normalized
    
    def _clean_title(self, title: str) -> str:
        """タイトルをクリーンアップ"""
        if not title:
            return ""
        
        # 末尾のピリオドを除去
        title = title.rstrip('.')
        
        # 不要な空白を削除
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    def _extract_year(self, date_str: str) -> Optional[str]:
        """日付文字列から年を抽出"""
        if not date_str:
            return None
        
        # YYYY年パターンを検索
        year_match = re.search(r'(\d{4})', str(date_str))
        if year_match:
            return year_match.group(1)
        
        return None
    
    def get_metadata_by_doi(self, doi: str) -> Optional[PubMedMetadata]:
        """
        DOIからPubMedメタデータを取得
        
        Args:
            doi: DOI文字列
            
        Returns:
            PubMedMetadata: 取得されたメタデータ、失敗時はNone
        """
        if not self.fetcher:
            self.logger.error("PubMed client not initialized")
            return None
        
        if not doi:
            self.logger.warning("Empty DOI provided")
            return None
        
        self._enforce_rate_limit()
        
        try:
            self.logger.debug(f"Fetching PubMed metadata for DOI: {doi}")
            
            # DOIから論文を検索
            article = self.fetcher.article_by_doi(doi)
            
            if not article:
                self.logger.debug(f"No PubMed article found for DOI: {doi}")
                return None
            
            # メタデータを抽出
            metadata = PubMedMetadata()
            metadata.title = self._clean_title(article.title) if article.title else None
            metadata.authors = self._normalize_authors(article.authors) if article.authors else None
            metadata.journal = article.journal if article.journal else None
            metadata.year = self._extract_year(article.year) if article.year else None
            metadata.volume = article.volume if article.volume else None
            metadata.issue = article.issue if article.issue else None
            metadata.pages = article.pages if article.pages else None
            metadata.pmid = article.pmid if article.pmid else None
            metadata.doi = doi
            metadata.abstract = article.abstract if hasattr(article, 'abstract') else None
            
            # MeSH用語の取得（利用可能な場合）
            try:
                if hasattr(article, 'mesh'):
                    metadata.mesh_terms = article.mesh
            except:
                pass
            
            self.logger.info(f"Successfully retrieved PubMed metadata for {doi} (PMID: {metadata.pmid})")
            return metadata
            
        except Exception as e:
            self.logger.warning(f"PubMed API error for {doi}: {e}")
            return None
    
    def get_metadata_by_pmid(self, pmid: str) -> Optional[PubMedMetadata]:
        """
        PMIDからPubMedメタデータを取得
        
        Args:
            pmid: PubMed ID
            
        Returns:
            PubMedMetadata: 取得されたメタデータ、失敗時はNone
        """
        if not self.fetcher:
            self.logger.error("PubMed client not initialized")
            return None
        
        if not pmid:
            self.logger.warning("Empty PMID provided")
            return None
        
        self._enforce_rate_limit()
        
        try:
            self.logger.debug(f"Fetching PubMed metadata for PMID: {pmid}")
            
            # PMIDから論文を取得
            article = self.fetcher.article_by_pmid(pmid)
            
            if not article:
                self.logger.debug(f"No PubMed article found for PMID: {pmid}")
                return None
            
            # メタデータを抽出（get_metadata_by_doiと同じロジック）
            metadata = PubMedMetadata()
            metadata.title = self._clean_title(article.title) if article.title else None
            metadata.authors = self._normalize_authors(article.authors) if article.authors else None
            metadata.journal = article.journal if article.journal else None
            metadata.year = self._extract_year(article.year) if article.year else None
            metadata.volume = article.volume if article.volume else None
            metadata.issue = article.issue if article.issue else None
            metadata.pages = article.pages if article.pages else None
            metadata.pmid = pmid
            metadata.doi = article.doi if hasattr(article, 'doi') else None
            metadata.abstract = article.abstract if hasattr(article, 'abstract') else None
            
            try:
                if hasattr(article, 'mesh'):
                    metadata.mesh_terms = article.mesh
            except:
                pass
            
            self.logger.info(f"Successfully retrieved PubMed metadata for PMID: {pmid}")
            return metadata
            
        except Exception as e:
            self.logger.warning(f"PubMed API error for PMID {pmid}: {e}")
            return None
    
    def is_available(self) -> bool:
        """PubMedクライアントが利用可能かチェック"""
        return self.fetcher is not None
    
    def get_client_info(self) -> Dict:
        """クライアント情報を取得"""
        return {
            'name': 'PubMed',
            'available': self.is_available(),
            'rate_limit': self.rate_limit_delay,
            'target_fields': ['life_sciences', 'medicine', 'bioengineering'],
            'priority': 'high' if self.is_available() else 'unavailable'
        } 