#!/usr/bin/env python3
"""
OpenAlex APIクライアント
完全無料のOpenAlex APIを使用して、DOIから学術論文のメタデータを取得する
"""

import time
import requests
from typing import Dict, Optional, List
from dataclasses import dataclass
import re

from ..shared.logger import get_integrated_logger
from ..shared.config_manager import ConfigManager


@dataclass
class OpenAlexMetadata:
    """OpenAlexから取得したメタデータ"""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    year: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    openalex_id: Optional[str] = None
    publication_date: Optional[str] = None
    cited_by_count: Optional[int] = None
    concepts: Optional[List[str]] = None
    is_oa: Optional[bool] = None
    
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
            'doi': self.doi,
            'openalex_id': self.openalex_id,
            'publication_date': self.publication_date,
            'cited_by_count': self.cited_by_count,
            'concepts': self.concepts,
            'is_oa': self.is_oa
        }
    
    def is_complete(self) -> bool:
        """必須フィールドが全て揃っているかチェック"""
        return all([
            self.title,
            self.authors,
            self.journal,
            self.year
        ])


class OpenAlexClient:
    """OpenAlex APIクライアント"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初期化
        
        Args:
            config_manager: 設定マネージャー
        """
        self.logger = get_integrated_logger().get_logger("CitationFetcher.OpenAlex")
        self.config = config_manager or ConfigManager()
        
        # API設定
        self.base_url = "https://api.openalex.org/works"
        self.timeout = 10
        
        # レート制限設定（制限なしだが、礼儀正しく0.1秒間隔）
        self.rate_limit_delay = self.config.get_config_value(
            'citation_fetcher.rate_limits.openalex',
            0.1
        )
        
        self.last_request_time = 0
        
        self.logger.info("OpenAlex client initialized successfully")
    
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
            display_name = author.get('author', {}).get('display_name', '')
            if not display_name:
                # フォールバック: raw_author_nameを使用
                display_name = author.get('raw_author_name', '')
            
            if display_name:
                normalized.append(display_name.strip())
        
        return normalized
    
    def _clean_title(self, title: str) -> str:
        """タイトルをクリーンアップ"""
        if not title:
            return ""
        
        # 不要な空白を削除
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    def _extract_year(self, publication_date: str) -> Optional[str]:
        """発行日から年を抽出"""
        if not publication_date:
            return None
        
        # YYYY-MM-DD形式から年を抽出
        year_match = re.search(r'(\d{4})', publication_date)
        if year_match:
            return year_match.group(1)
        
        return None
    
    def _extract_journal_info(self, host_venue: Dict) -> tuple:
        """ジャーナル情報を抽出"""
        if not host_venue:
            return None, None, None
        
        journal_name = host_venue.get('display_name', '')
        volume = None
        issue = None
        
        # ボリューム・号情報があればそれも取得
        if 'volume' in host_venue:
            volume = str(host_venue['volume'])
        if 'issue' in host_venue:
            issue = str(host_venue['issue'])
        
        return journal_name if journal_name else None, volume, issue
    
    def _extract_pages(self, biblio: Dict) -> Optional[str]:
        """ページ情報を抽出"""
        if not biblio:
            return None
        
        first_page = biblio.get('first_page')
        last_page = biblio.get('last_page')
        
        if first_page and last_page:
            return f"{first_page}-{last_page}"
        elif first_page:
            return str(first_page)
        
        return None
    
    def _extract_concepts(self, concepts_data: List[Dict]) -> List[str]:
        """コンセプト（分野）情報を抽出"""
        if not concepts_data:
            return []
        
        concepts = []
        for concept in concepts_data[:5]:  # 上位5つのコンセプトのみ
            display_name = concept.get('display_name', '')
            if display_name:
                concepts.append(display_name)
        
        return concepts
    
    def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """HTTP リクエストを実行"""
        self._enforce_rate_limit()
        
        try:
            headers = {
                'User-Agent': 'ObsClippingsManager/2.2 (https://github.com/your-repo) metapub',
                'Accept': 'application/json'
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
                self.logger.debug(f"Work not found in OpenAlex: {url}")
                return None
            else:
                self.logger.warning(f"OpenAlex API error {response.status_code}: {response.text}")
                return None
                
        except requests.RequestException as e:
            self.logger.warning(f"Request error: {e}")
            return None
    
    def get_metadata_by_doi(self, doi: str) -> Optional[OpenAlexMetadata]:
        """
        DOIからOpenAlexメタデータを取得
        
        Args:
            doi: DOI文字列
            
        Returns:
            OpenAlexMetadata: 取得されたメタデータ、失敗時はNone
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
        
        # DOI URLを作成
        doi_url = f"https://doi.org/{clean_doi}"
        
        self.logger.debug(f"Fetching OpenAlex metadata for DOI: {clean_doi}")
        
        # APIエンドポイント
        url = f"{self.base_url}/{doi_url}"
        
        data = self._make_request(url)
        if not data:
            return None
        
        try:
            # メタデータを抽出
            metadata = OpenAlexMetadata()
            metadata.title = self._clean_title(data.get('title')) if data.get('title') else None
            metadata.authors = self._normalize_authors(data.get('authorships', [])) or None
            
            # ジャーナル情報
            journal_name, volume, issue = self._extract_journal_info(data.get('host_venue', {}))
            metadata.journal = journal_name
            metadata.volume = volume
            metadata.issue = issue
            
            # 発行年
            metadata.year = self._extract_year(data.get('publication_date')) if data.get('publication_date') else None
            
            # ページ情報
            metadata.pages = self._extract_pages(data.get('biblio', {}))
            
            # その他の情報
            metadata.doi = clean_doi
            metadata.openalex_id = data.get('id')
            metadata.publication_date = data.get('publication_date')
            metadata.cited_by_count = data.get('cited_by_count')
            metadata.concepts = self._extract_concepts(data.get('concepts', []))
            metadata.is_oa = data.get('open_access', {}).get('is_oa', False)
            
            self.logger.info(f"Successfully retrieved OpenAlex metadata for {clean_doi} (ID: {metadata.openalex_id})")
            return metadata
            
        except Exception as e:
            self.logger.warning(f"Error parsing OpenAlex response for {clean_doi}: {e}")
            return None
    
    def search_by_title(self, title: str) -> Optional[OpenAlexMetadata]:
        """
        タイトルからOpenAlexメタデータを検索
        
        Args:
            title: 論文タイトル
            
        Returns:
            OpenAlexMetadata: 取得されたメタデータ、失敗時はNone
        """
        if not title:
            self.logger.warning("Empty title provided")
            return None
        
        self.logger.debug(f"Searching OpenAlex by title: {title[:50]}...")
        
        # 検索パラメータ
        params = {
            'search': title,
            'limit': 1,
            'sort': 'relevance_score:desc'
        }
        
        data = self._make_request(self.base_url, params)
        if not data or not data.get('results'):
            return None
        
        # 最初の結果を使用
        work_data = data['results'][0]
        
        try:
            # メタデータを抽出（get_metadata_by_doiと同じロジック）
            metadata = OpenAlexMetadata()
            metadata.title = self._clean_title(work_data.get('title')) if work_data.get('title') else None
            metadata.authors = self._normalize_authors(work_data.get('authorships', [])) or None
            
            # ジャーナル情報
            journal_name, volume, issue = self._extract_journal_info(work_data.get('host_venue', {}))
            metadata.journal = journal_name
            metadata.volume = volume
            metadata.issue = issue
            
            # 発行年
            metadata.year = self._extract_year(work_data.get('publication_date')) if work_data.get('publication_date') else None
            
            # ページ情報
            metadata.pages = self._extract_pages(work_data.get('biblio', {}))
            
            # その他の情報
            metadata.doi = work_data.get('doi')
            metadata.openalex_id = work_data.get('id')
            metadata.publication_date = work_data.get('publication_date')
            metadata.cited_by_count = work_data.get('cited_by_count')
            metadata.concepts = self._extract_concepts(work_data.get('concepts', []))
            metadata.is_oa = work_data.get('open_access', {}).get('is_oa', False)
            
            self.logger.info(f"Successfully found OpenAlex work by title (ID: {metadata.openalex_id})")
            return metadata
            
        except Exception as e:
            self.logger.warning(f"Error parsing OpenAlex search response: {e}")
            return None
    
    def is_available(self) -> bool:
        """OpenAlexクライアントが利用可能かチェック"""
        try:
            # 簡単なヘルスチェック
            test_url = f"{self.base_url}/https://doi.org/10.1038/nature12373"  # 有名な論文
            
            response = requests.get(test_url, timeout=5)
            return response.status_code in [200, 404]  # 404も正常（論文が見つからないだけ）
        except:
            return False
    
    def get_client_info(self) -> Dict:
        """クライアント情報を取得"""
        return {
            'name': 'OpenAlex',
            'available': self.is_available(),
            'rate_limit': self.rate_limit_delay,
            'target_fields': ['all_fields'],
            'priority': 'high',
            'features': ['comprehensive', 'free', 'open_access_info']
        } 