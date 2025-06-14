"""
Citation Fetcher - 引用文献取得システム

CrossRef API、OpenCitations API との連携により、学術論文の引用文献データを
取得・正規化・管理する統合システム。
"""

import re
import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

from ..shared.exceptions import APIError, BibTeXError


class RateLimiter:
    """
    API レート制限管理クラス
    
    指定されたレート制限に従って API 呼び出しを制御。
    """
    
    def __init__(self, max_requests_per_second: int):
        """
        レート制限の初期化
        
        Args:
            max_requests_per_second: 秒間最大リクエスト数
        """
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0.0
        
    def wait_if_needed(self):
        """
        必要に応じて待機してレート制限を守る
        """
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


class CitationFetcher:
    """
    引用文献取得システム
    
    CrossRef API、OpenCitations API を用いて引用文献データを取得し、
    レート制限、エラーハンドリング、データ正規化を統一的に管理。
    """
    
    def __init__(self, config_manager, logger):
        """
        CitationFetcherの初期化
        
        Args:
            config_manager: 設定管理インスタンス
            logger: ログシステムインスタンス
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('CitationFetcher')
        
        # API設定の取得
        api_settings = self.config_manager.get_api_settings()
        self.crossref_config = api_settings.get('crossref', {})
        self.opencitations_config = api_settings.get('opencitations', {})
        
        # レート制限機能の初期化
        self.rate_limiters = {
            'crossref': RateLimiter(self.crossref_config.get('rate_limit', 10)),
            'opencitations': RateLimiter(self.opencitations_config.get('rate_limit', 5))
        }
        
        # デフォルト設定
        self.default_timeout = 30
        self.max_retry_attempts = 3
        self.retry_delay = 1.0
        
        self.logger.debug("CitationFetcher initialized successfully")
    
    def validate_doi(self, doi: str) -> bool:
        """
        DOI形式の検証
        
        Args:
            doi: 検証するDOI
            
        Returns:
            bool: 有効な場合True
        """
        if not doi or not isinstance(doi, str):
            return False
        
        # DOI形式の正規表現（10.で始まる）
        doi_pattern = r'^10\.\d{4,}/[^\s]+$'
        return bool(re.match(doi_pattern, doi.strip()))
    
    def fetch_from_crossref(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        CrossRef APIから引用文献データを取得
        
        Args:
            doi: 取得するDOI
            
        Returns:
            Optional[Dict[str, Any]]: 正規化された引用文献データ
            
        Raises:
            APIError: API呼び出しエラー時
        """
        if not self.validate_doi(doi):
            raise APIError(
                f"Invalid DOI format: {doi}",
                error_code="INVALID_DOI_FORMAT",
                context={"doi": doi}
            )
        
        self.logger.debug(f"Fetching citation data from CrossRef for DOI: {doi}")
        
        # レート制限の適用
        self.rate_limiters['crossref'].wait_if_needed()
        
        base_url = self.crossref_config.get('base_url', 'https://api.crossref.org')
        url = f"{base_url}/works/{doi}"
        
        # リトライ機構付きリクエスト
        for attempt in range(self.max_retry_attempts):
            try:
                response = requests.get(
                    url,
                    timeout=self.crossref_config.get('timeout', self.default_timeout),
                    headers={'Accept': 'application/json'}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'ok':
                        return self.normalize_crossref_data(data['message'])
                    else:
                        raise APIError(
                            f"CrossRef API returned error status: {data.get('message', 'Unknown error')}",
                            error_code="CROSSREF_API_ERROR",
                            context={"doi": doi, "response": data}
                        )
                
                elif response.status_code == 404:
                    raise APIError(
                        f"DOI not found in CrossRef: {doi}",
                        error_code="DOI_NOT_FOUND",
                        context={"doi": doi, "status_code": response.status_code}
                    )
                
                elif response.status_code >= 500:
                    # サーバーエラーの場合はリトライ
                    if attempt < self.max_retry_attempts - 1:
                        self.logger.warning(f"CrossRef server error (attempt {attempt + 1}): {response.status_code}")
                        time.sleep(self.retry_delay * (2 ** attempt))  # 指数バックオフ
                        continue
                    else:
                        raise APIError(
                            f"CrossRef server error: {response.status_code}",
                            error_code="CROSSREF_SERVER_ERROR",
                            context={"doi": doi, "status_code": response.status_code}
                        )
                
                else:
                    raise APIError(
                        f"CrossRef API error: {response.status_code}",
                        error_code="CROSSREF_API_ERROR",
                        context={"doi": doi, "status_code": response.status_code}
                    )
                
            except requests.exceptions.Timeout:
                raise APIError(
                    f"CrossRef API timeout for DOI: {doi}",
                    error_code="CROSSREF_TIMEOUT",
                    context={"doi": doi}
                )
            
            except requests.exceptions.ConnectionError:
                raise APIError(
                    f"Connection error to CrossRef API for DOI: {doi}",
                    error_code="CROSSREF_CONNECTION_ERROR",
                    context={"doi": doi}
                )
            
            except requests.exceptions.RequestException as e:
                raise APIError(
                    f"CrossRef API request error: {str(e)}",
                    error_code="CROSSREF_REQUEST_ERROR",
                    context={"doi": doi, "original_error": str(e)}
                )
        
        return None
    
    def fetch_citations_from_opencitations(self, doi: str) -> List[Dict[str, Any]]:
        """
        OpenCitations APIから引用関係データを取得
        
        Args:
            doi: 取得するDOI
            
        Returns:
            List[Dict[str, Any]]: 引用関係データのリスト
            
        Raises:
            APIError: API呼び出しエラー時
        """
        if not self.validate_doi(doi):
            raise APIError(
                f"Invalid DOI format: {doi}",
                error_code="INVALID_DOI_FORMAT",
                context={"doi": doi}
            )
        
        self.logger.debug(f"Fetching citation relations from OpenCitations for DOI: {doi}")
        
        # レート制限の適用
        self.rate_limiters['opencitations'].wait_if_needed()
        
        base_url = self.opencitations_config.get('base_url', 'https://opencitations.net/index/api/v1')
        url = f"{base_url}/citations/{doi}"
        
        try:
            response = requests.get(
                url,
                timeout=self.opencitations_config.get('timeout', self.default_timeout),
                headers={'Accept': 'application/json'}
            )
            
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 404:
                # OpenCitationsでは404は正常（引用関係がない場合）
                return []
            
            else:
                raise APIError(
                    f"OpenCitations API error: {response.status_code}",
                    error_code="OPENCITATIONS_API_ERROR",
                    context={"doi": doi, "status_code": response.status_code}
                )
        
        except requests.exceptions.Timeout:
            raise APIError(
                f"OpenCitations API timeout for DOI: {doi}",
                error_code="OPENCITATIONS_TIMEOUT",
                context={"doi": doi}
            )
        
        except requests.exceptions.ConnectionError:
            raise APIError(
                f"Connection error to OpenCitations API for DOI: {doi}",
                error_code="OPENCITATIONS_CONNECTION_ERROR",
                context={"doi": doi}
            )
        
        except requests.exceptions.RequestException as e:
            raise APIError(
                f"OpenCitations API request error: {str(e)}",
                error_code="OPENCITATIONS_REQUEST_ERROR",
                context={"doi": doi, "original_error": str(e)}
            )
    
    def normalize_crossref_data(self, crossref_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        CrossRef APIレスポンスデータの正規化
        
        Args:
            crossref_data: CrossRef APIからの生データ
            
        Returns:
            Dict[str, Any]: 正規化されたデータ
        """
        normalized = {}
        
        # DOI
        normalized['doi'] = crossref_data.get('DOI', '')
        
        # タイトル
        title_list = crossref_data.get('title', [])
        normalized['title'] = title_list[0].strip() if title_list else ''
        
        # 著者
        authors = crossref_data.get('author', [])
        author_names = []
        for author in authors:
            given = author.get('given', '')
            family = author.get('family', '')
            if given and family:
                author_names.append(f"{given} {family}")
            elif family:
                author_names.append(family)
        normalized['authors'] = ', '.join(author_names)
        
        # 年
        published_date = crossref_data.get('published-print', {}).get('date-parts', [[]])
        if published_date and published_date[0]:
            normalized['year'] = str(published_date[0][0])
        else:
            # フォールバック: published-online
            online_date = crossref_data.get('published-online', {}).get('date-parts', [[]])
            if online_date and online_date[0]:
                normalized['year'] = str(online_date[0][0])
            else:
                normalized['year'] = ''
        
        # ジャーナル
        journal_list = crossref_data.get('container-title', [])
        normalized['journal'] = journal_list[0] if journal_list else ''
        
        # 発行者
        normalized['publisher'] = crossref_data.get('publisher', '')
        
        # 抽象
        normalized['abstract'] = crossref_data.get('abstract', '')
        
        return normalized
    
    def normalize_citation_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        引用データの正規化（統合メソッド）
        
        Args:
            raw_data: 生の引用データ
            
        Returns:
            Dict[str, Any]: 正規化されたデータ
        """
        # CrossRefデータの正規化として処理
        return self.normalize_crossref_data(raw_data)
    
    def batch_fetch(self, dois: List[str]) -> List[Dict[str, Any]]:
        """
        複数DOIのバッチ処理
        
        Args:
            dois: DOIのリスト
            
        Returns:
            List[Dict[str, Any]]: 取得結果のリスト
        """
        results = []
        
        for doi in dois:
            try:
                result = self.fetch_from_crossref(doi)
                if result:
                    results.append(result)
                else:
                    # 取得失敗時のプレースホルダー
                    results.append({
                        'doi': doi,
                        'title': '',
                        'authors': '',
                        'year': '',
                        'journal': '',
                        'error': 'Failed to fetch data'
                    })
            except APIError as e:
                self.logger.error(f"Failed to fetch data for DOI {doi}: {e}")
                results.append({
                    'doi': doi,
                    'title': '',
                    'authors': '',
                    'year': '',
                    'journal': '',
                    'error': str(e)
                })
        
        return results
    
    def remove_duplicate_dois(self, dois: List[str]) -> List[str]:
        """
        DOIリストから重複を除去
        
        Args:
            dois: DOIのリスト
            
        Returns:
            List[str]: 重複を除去したDOIリスト
        """
        seen = set()
        unique_dois = []
        
        for doi in dois:
            if doi not in seen:
                seen.add(doi)
                unique_dois.append(doi)
        
        return unique_dois
    
    def get_citation_statistics(self, doi: str) -> Dict[str, Any]:
        """
        引用統計情報の取得
        
        Args:
            doi: 対象DOI
            
        Returns:
            Dict[str, Any]: 統計情報
        """
        stats = {
            'doi': doi,
            'citation_count': 0,
            'citing_papers': [],
            'cited_papers': [],
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            citations = self.fetch_citations_from_opencitations(doi)
            stats['citation_count'] = len(citations)
            
            for citation in citations:
                if citation.get('citing'):
                    stats['citing_papers'].append(citation['citing'])
                if citation.get('cited'):
                    stats['cited_papers'].append(citation['cited'])
                    
        except APIError as e:
            self.logger.warning(f"Failed to get citation statistics for {doi}: {e}")
            stats['error'] = str(e)
        
        return stats 