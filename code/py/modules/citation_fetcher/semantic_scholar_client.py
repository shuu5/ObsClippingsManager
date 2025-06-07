#!/usr/bin/env python3
"""
Semantic Scholar APIクライアント
無料のSemantic Scholar APIを使用して、DOIから学術論文のメタデータを取得する
"""

import time
import requests
from typing import Dict, Optional, List
from dataclasses import dataclass
import re

from ..shared.logger import get_integrated_logger
from ..shared.config_manager import ConfigManager


@dataclass
class SemanticScholarMetadata:
    """Semantic Scholarから取得したメタデータ"""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    year: Optional[str] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None
    doi: Optional[str] = None
    paper_id: Optional[str] = None
    abstract: Optional[str] = None
    fields_of_study: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'title': self.title,
            'authors': self.authors,
            'journal': self.journal or self.venue,  # journalがない場合はvenueを使用
            'year': self.year,
            'venue': self.venue,
            'citation_count': self.citation_count,
            'doi': self.doi,
            'paper_id': self.paper_id,
            'abstract': self.abstract,
            'fields_of_study': self.fields_of_study
        }
    
    def is_complete(self) -> bool:
        """必須フィールドが全て揃っているかチェック"""
        return all([
            self.title,
            self.authors,
            self.journal or self.venue,
            self.year
        ])


class SemanticScholarClient:
    """Semantic Scholar APIクライアント"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初期化
        
        Args:
            config_manager: 設定マネージャー
        """
        self.logger = get_integrated_logger().get_logger("CitationFetcher.SemanticScholar")
        self.config = config_manager or ConfigManager()
        
        # API設定
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper"
        self.timeout = 10
        
        # レート制限設定（100リクエスト/5分 = 1.2秒間隔）
        self.rate_limit_delay = self.config.get_config_value(
            'citation_fetcher.rate_limits.semantic_scholar', 
            1.2
        )
        
        self.last_request_time = 0
        
        # APIフィールド設定
        self.fields = [
            'title',
            'authors',
            'journal',
            'year',
            'venue',
            'citationCount',
            'abstract',
            'fieldsOfStudy',
            'paperId'
        ]
        
        self.logger.info("Semantic Scholar client initialized successfully")
    
    def _enforce_rate_limit(self):
        """レート制限を実行"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _normalize_authors(self, authors_data: List[Dict]) -> List[str]:
        """著者情報を正規化"""
        if not authors_data:
            return []
        
        normalized = []
        for author in authors_data:
            if isinstance(author, dict):
                name = author.get('name', '')
            else:
                name = str(author)
            
            if name:
                normalized.append(name.strip())
        
        return normalized
    
    def _clean_title(self, title: str) -> str:
        """タイトルをクリーンアップ"""
        if not title:
            return ""
        
        # HTMLエンティティのデコード
        title = title.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        
        # 不要な空白を削除
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    def _extract_year(self, year_data) -> Optional[str]:
        """年情報を抽出"""
        if not year_data:
            return None
        
        # 数値型の場合
        if isinstance(year_data, int):
            return str(year_data)
        
        # 文字列型の場合
        year_str = str(year_data)
        year_match = re.search(r'(\d{4})', year_str)
        if year_match:
            return year_match.group(1)
        
        return None
    
    def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """HTTP リクエストを実行"""
        self._enforce_rate_limit()
        
        try:
            headers = {
                'User-Agent': 'ObsClippingsManager/2.2 (https://github.com/your-repo) metapub'
            }
            
            response = requests.get(
                url, 
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                self.logger.debug(f"Paper not found in Semantic Scholar: {url}")
                return None
            elif response.status_code == 429:
                self.logger.warning("Rate limit exceeded, waiting...")
                time.sleep(5)  # 5秒待機
                return None
            else:
                self.logger.warning(f"Semantic Scholar API error {response.status_code}: {response.text}")
                return None
                
        except requests.RequestException as e:
            self.logger.warning(f"Request error: {e}")
            return None
    
    def get_metadata_by_doi(self, doi: str) -> Optional[SemanticScholarMetadata]:
        """
        DOIからSemantic Scholarメタデータを取得
        
        Args:
            doi: DOI文字列
            
        Returns:
            SemanticScholarMetadata: 取得されたメタデータ、失敗時はNone
        """
        if not doi:
            self.logger.warning("Empty DOI provided")
            return None
        
        # DOIをクリーンアップ
        clean_doi = doi.strip()
        if clean_doi.startswith('http'):
            # URLからDOIを抽出
            doi_match = re.search(r'10\.\d+/.+', clean_doi)
            if doi_match:
                clean_doi = doi_match.group(0)
        
        self.logger.debug(f"Fetching Semantic Scholar metadata for DOI: {clean_doi}")
        
        # APIエンドポイント
        url = f"{self.base_url}/DOI:{clean_doi}"
        params = {
            'fields': ','.join(self.fields)
        }
        
        data = self._make_request(url, params)
        if not data:
            return None
        
        try:
            # メタデータを抽出
            metadata = SemanticScholarMetadata()
            metadata.title = self._clean_title(data.get('title')) if data.get('title') else None
            metadata.authors = self._normalize_authors(data.get('authors', [])) or None
            metadata.journal = data.get('journal', {}).get('name') if data.get('journal') else None
            metadata.year = self._extract_year(data.get('year')) if data.get('year') else None
            metadata.venue = data.get('venue') if data.get('venue') else None
            metadata.citation_count = data.get('citationCount') if data.get('citationCount') else None
            metadata.doi = clean_doi
            metadata.paper_id = data.get('paperId') if data.get('paperId') else None
            metadata.abstract = data.get('abstract') if data.get('abstract') else None
            metadata.fields_of_study = data.get('fieldsOfStudy') if data.get('fieldsOfStudy') else None
            
            self.logger.info(f"Successfully retrieved Semantic Scholar metadata for {clean_doi} (Paper ID: {metadata.paper_id})")
            return metadata
            
        except Exception as e:
            self.logger.warning(f"Error parsing Semantic Scholar response for {clean_doi}: {e}")
            return None
    
    def get_metadata_by_title(self, title: str) -> Optional[SemanticScholarMetadata]:
        """
        タイトルからSemantic Scholarメタデータを取得
        
        Args:
            title: 論文タイトル
            
        Returns:
            SemanticScholarMetadata: 取得されたメタデータ、失敗時はNone
        """
        if not title:
            self.logger.warning("Empty title provided")
            return None
        
        self.logger.debug(f"Searching Semantic Scholar by title: {title[:50]}...")
        
        # 検索APIエンドポイント
        url = f"{self.base_url}/search"
        params = {
            'query': title,
            'fields': ','.join(self.fields),
            'limit': 1
        }
        
        data = self._make_request(url, params)
        if not data or not data.get('data'):
            return None
        
        # 最初の結果を使用
        paper_data = data['data'][0]
        
        try:
            # メタデータを抽出
            metadata = SemanticScholarMetadata()
            metadata.title = self._clean_title(paper_data.get('title')) if paper_data.get('title') else None
            metadata.authors = self._normalize_authors(paper_data.get('authors', [])) or None
            metadata.journal = paper_data.get('journal', {}).get('name') if paper_data.get('journal') else None
            metadata.year = self._extract_year(paper_data.get('year')) if paper_data.get('year') else None
            metadata.venue = paper_data.get('venue') if paper_data.get('venue') else None
            metadata.citation_count = paper_data.get('citationCount') if paper_data.get('citationCount') else None
            metadata.doi = paper_data.get('doi') if paper_data.get('doi') else None
            metadata.paper_id = paper_data.get('paperId') if paper_data.get('paperId') else None
            metadata.abstract = paper_data.get('abstract') if paper_data.get('abstract') else None
            metadata.fields_of_study = paper_data.get('fieldsOfStudy') if paper_data.get('fieldsOfStudy') else None
            
            self.logger.info(f"Successfully found Semantic Scholar paper by title (Paper ID: {metadata.paper_id})")
            return metadata
            
        except Exception as e:
            self.logger.warning(f"Error parsing Semantic Scholar search response: {e}")
            return None
    
    def is_available(self) -> bool:
        """Semantic Scholarクライアントが利用可能かチェック"""
        try:
            # 簡単なヘルスチェック
            test_url = f"{self.base_url}/DOI:10.1038/nature12373"  # 有名な論文
            params = {'fields': 'title'}
            
            response = requests.get(test_url, params=params, timeout=5)
            return response.status_code in [200, 404]  # 404も正常（論文が見つからないだけ）
        except:
            return False
    
    def get_client_info(self) -> Dict:
        """クライアント情報を取得"""
        return {
            'name': 'Semantic Scholar',
            'available': self.is_available(),
            'rate_limit': self.rate_limit_delay,
            'target_fields': ['computer_science', 'ai', 'engineering', 'mathematics'],
            'priority': 'medium'
        } 