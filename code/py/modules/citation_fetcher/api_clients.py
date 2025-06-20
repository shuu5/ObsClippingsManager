"""
API Clients Module

外部API連携クライアント群 - CrossRef, Semantic Scholar, OpenCitations
"""

import time
import requests
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from ..shared_modules.exceptions import APIError


class BaseAPIClient(ABC):
    """
    APIクライアントベースクラス
    
    共通のAPIアクセス機能とエラーハンドリングを提供
    """
    
    def __init__(self, config_manager, logger, api_name: str):
        """
        BaseAPIClient初期化
        
        Args:
            config_manager: 設定管理インスタンス
            logger: ログシステムインスタンス
            api_name (str): API名
        """
        self.config_manager = config_manager
        self.logger = logger
        self.api_name = api_name
        
        # API設定取得
        self.config = self._get_api_config()
        
        # HTTPセッション
        self.session = requests.Session()
        self.session.timeout = self.config.get('timeout', 30)
        
        # ヘッダー設定
        self.session.headers.update({
            'User-Agent': 'ObsClippingsManager/3.2.0 (Academic Research Tool)',
            'Accept': 'application/json'
        })
        
        self.logger.debug(f"{api_name} API client initialized")
    
    @abstractmethod
    def fetch_citations(self, doi: str) -> List[Dict[str, Any]]:
        """
        DOIから引用文献を取得（サブクラスで実装）
        
        Args:
            doi (str): 論文のDOI
            
        Returns:
            List[Dict[str, Any]]: 引用文献データリスト
        """
        pass
    
    def _get_api_config(self) -> Dict[str, Any]:
        """API設定を取得"""
        try:
            config = self.config_manager.get_config()
            citation_config = config.get('citation_fetcher', {})
            api_config = citation_config.get('apis', {}).get(self.api_name, {})
            return api_config
        except Exception as e:
            self.logger.warning(f"Failed to load {self.api_name} config: {e}")
            return {}
    
    def _make_request(self, url: str, params: Optional[Dict] = None, 
                     headers: Optional[Dict] = None) -> Dict[str, Any]:
        """
        HTTP請求を実行
        
        Args:
            url (str): 請求URL
            params (Optional[Dict]): クエリパラメータ
            headers (Optional[Dict]): 追加ヘッダー
            
        Returns:
            Dict[str, Any]: レスポンスデータ
            
        Raises:
            APIError: API請求エラー時
        """
        try:
            if headers:
                request_headers = {**self.session.headers, **headers}
            else:
                request_headers = self.session.headers
            
            self.logger.debug(f"Making request to {url}")
            
            response = self.session.get(url, params=params, headers=request_headers)
            
            # ステータスコード確認
            if response.status_code == 404:
                self.logger.debug(f"Resource not found: {url}")
                return {}
            elif response.status_code == 429:
                raise APIError(
                    f"Rate limit exceeded for {self.api_name}",
                    error_code="API_RATE_LIMIT_EXCEEDED",
                    context={"api_name": self.api_name, "url": url}
                )
            elif response.status_code >= 400:
                raise APIError(
                    f"HTTP {response.status_code} error from {self.api_name}: {response.text}",
                    error_code="API_HTTP_ERROR",
                    context={"api_name": self.api_name, "status_code": response.status_code, "url": url}
                )
            
            # JSON解析
            try:
                return response.json()
            except ValueError as e:
                raise APIError(
                    f"Invalid JSON response from {self.api_name}: {str(e)}",
                    error_code="API_INVALID_JSON",
                    context={"api_name": self.api_name, "response_text": response.text[:200]}
                )
                
        except requests.exceptions.Timeout:
            raise APIError(
                f"Timeout error for {self.api_name}",
                error_code="API_TIMEOUT",
                context={"api_name": self.api_name, "url": url}
            )
        except requests.exceptions.ConnectionError:
            raise APIError(
                f"Connection error for {self.api_name}",
                error_code="API_CONNECTION_ERROR",
                context={"api_name": self.api_name, "url": url}
            )
        except APIError:
            raise
        except Exception as e:
            raise APIError(
                f"Unexpected error from {self.api_name}: {str(e)}",
                error_code="API_UNEXPECTED_ERROR",
                context={"api_name": self.api_name, "original_error": str(e)}
            )


class CrossRefAPIClient(BaseAPIClient):
    """
    CrossRef API クライアント
    
    CrossRef APIから引用文献情報を取得
    """
    
    def __init__(self, config_manager, logger):
        super().__init__(config_manager, logger, 'crossref')
        self.base_url = self.config.get('base_url', 'https://api.crossref.org')
    
    def fetch_citations(self, doi: str) -> List[Dict[str, Any]]:
        """
        CrossRef APIから引用文献を取得
        
        Args:
            doi (str): 論文のDOI
            
        Returns:
            List[Dict[str, Any]]: 引用文献データリスト
        """
        try:
            self.logger.debug(f"Fetching citations from CrossRef for DOI: {doi}")
            
            # API URL構築
            url = self._build_api_url(doi)
            
            # API呼び出し
            response_data = self._make_request(url)
            
            # レスポンス解析
            citations = self._parse_crossref_response(response_data)
            
            self.logger.debug(f"Successfully fetched {len(citations)} citations from CrossRef")
            return citations
            
        except APIError:
            # API関連のエラーはそのまま再発生させる
            raise
        except Exception as e:
            self.logger.error(f"CrossRef API error for DOI {doi}: {e}")
            raise APIError(
                f"CrossRef API failed for DOI {doi}: {str(e)}",
                error_code="CROSSREF_API_ERROR",
                context={"doi": doi, "original_error": str(e)}
            )
    
    def _build_api_url(self, doi: str) -> str:
        """CrossRef API URLを構築"""
        return f"{self.base_url}/works/{doi}"
    
    def _parse_crossref_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """CrossRef APIレスポンスを解析して引用文献リストを返す"""
        citations = []
        
        # レスポンスが空の場合
        if not response_data:
            return citations
        
        try:
            # CrossRef APIレスポンス構造を解析
            message = response_data.get('message', {})
            references = message.get('reference', [])
            
            for ref in references:
                citation = {}
                
                # タイトル
                if 'article-title' in ref:
                    citation['title'] = ref['article-title']
                elif 'unstructured' in ref:
                    # 構造化されていない引用文献の場合
                    citation['title'] = ref['unstructured'][:100] + "..." if len(ref['unstructured']) > 100 else ref['unstructured']
                
                # 著者
                if 'author' in ref:
                    citation['authors'] = ref['author']
                
                # ジャーナル
                if 'journal-title' in ref:
                    citation['journal'] = ref['journal-title']
                
                # 年
                if 'year' in ref:
                    citation['year'] = int(ref['year']) if str(ref['year']).isdigit() else ref['year']
                
                # DOI
                if 'DOI' in ref:
                    citation['doi'] = ref['DOI']
                
                # 巻・ページ
                if 'volume' in ref:
                    citation['volume'] = ref['volume']
                if 'page' in ref:
                    citation['pages'] = ref['page']
                
                # 最低限のデータがある場合のみ追加
                if citation.get('title') or citation.get('unstructured'):
                    citations.append(citation)
            
            self.logger.debug(f"Parsed {len(citations)} citations from CrossRef response")
            return citations
            
        except Exception as e:
            self.logger.warning(f"Error parsing CrossRef response: {e}")
            return citations
    
    def _get_mock_citation_data(self, doi: str) -> List[Dict[str, Any]]:
        """モック引用文献データを返す（開発用）"""
        return [
            {
                'title': 'Mock Reference Paper 1',
                'authors': 'Smith, John and Doe, Jane',
                'journal': 'Nature',
                'year': 2023,
                'volume': '615',
                'pages': '123-135',
                'doi': '10.1038/nature.2023.001'
            },
            {
                'title': 'Mock Reference Paper 2',
                'authors': 'Brown, Alice',
                'journal': 'Science',
                'year': 2022,
                'volume': '378',
                'pages': '456-468',
                'doi': '10.1126/science.2022.002'
            }
        ]


class SemanticScholarAPIClient(BaseAPIClient):
    """
    Semantic Scholar API クライアント
    
    Semantic Scholar APIから引用文献情報を取得
    """
    
    def __init__(self, config_manager, logger):
        super().__init__(config_manager, logger, 'semantic_scholar')
        self.base_url = self.config.get('base_url', 'https://api.semanticscholar.org')
        
        # API Key設定
        api_key = self.config.get('api_key_env')
        if api_key:
            import os
            actual_key = os.getenv(api_key)
            if actual_key:
                self.session.headers['x-api-key'] = actual_key
    
    def fetch_citations(self, doi: str) -> List[Dict[str, Any]]:
        """
        Semantic Scholar APIから引用文献を取得
        
        Args:
            doi (str): 論文のDOI
            
        Returns:
            List[Dict[str, Any]]: 引用文献データリスト
        """
        try:
            self.logger.debug(f"Fetching citations from Semantic Scholar for DOI: {doi}")
            
            # API URL構築 
            url = self._build_api_url(doi)
            
            # API呼び出し
            response_data = self._make_request(url)
            
            # レスポンス解析
            citations = self._parse_semantic_scholar_response(response_data)
            
            self.logger.debug(f"Successfully fetched {len(citations)} citations from Semantic Scholar")
            return citations
            
        except APIError:
            # API関連のエラーはそのまま再発生させる
            raise
        except Exception as e:
            self.logger.error(f"Semantic Scholar API error for DOI {doi}: {e}")
            raise APIError(
                f"Semantic Scholar API failed for DOI {doi}: {str(e)}",
                error_code="SEMANTIC_SCHOLAR_API_ERROR",
                context={"doi": doi, "original_error": str(e)}
            )
    
    def _build_api_url(self, doi: str) -> str:
        """Semantic Scholar API URLを構築"""
        # DOIからpaper情報を取得し、そこからreferencesを取得するエンドポイントを構築
        return f"{self.base_url}/graph/v1/paper/{doi}/references"
    
    def _parse_semantic_scholar_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Semantic Scholar APIレスポンスを解析して引用文献リストを返す"""
        citations = []
        
        # レスポンスが空の場合
        if not response_data:
            return citations
        
        try:
            # Semantic Scholar APIレスポンス構造を解析
            data = response_data.get('data', [])
            
            for item in data:
                ref = item.get('citedPaper', {})
                if not ref:
                    continue
                
                citation = {}
                
                # タイトル
                if 'title' in ref:
                    citation['title'] = ref['title']
                
                # 著者
                if 'authors' in ref and ref['authors']:
                    # 著者リストを文字列に変換
                    author_names = []
                    for author in ref['authors']:
                        if 'name' in author:
                            author_names.append(author['name'])
                    if author_names:
                        citation['authors'] = ', '.join(author_names)
                
                # ジャーナル/出版venue
                if 'venue' in ref:
                    citation['journal'] = ref['venue']
                
                # 年
                if 'year' in ref and ref['year']:
                    citation['year'] = ref['year']
                
                # DOI
                if 'externalIds' in ref and ref['externalIds']:
                    external_ids = ref['externalIds']
                    if 'DOI' in external_ids:
                        citation['doi'] = external_ids['DOI']
                
                # abstract
                if 'abstract' in ref:
                    citation['abstract'] = ref['abstract']
                
                # citationCount
                if 'citationCount' in ref:
                    citation['citationCount'] = ref['citationCount']
                
                # URL
                if 'url' in ref:
                    citation['url'] = ref['url']
                
                # 最低限のデータがある場合のみ追加
                if citation.get('title'):
                    citations.append(citation)
            
            self.logger.debug(f"Parsed {len(citations)} citations from Semantic Scholar response")
            return citations
            
        except Exception as e:
            self.logger.warning(f"Error parsing Semantic Scholar response: {e}")
            return citations
    
    def _get_mock_citation_data(self, doi: str) -> List[Dict[str, Any]]:
        """モック引用文献データを返す（開発用）"""
        return [
            {
                'title': 'Semantic Scholar Mock Reference 1',
                'authors': 'Wilson, Carol and Taylor, David',
                'journal': 'Cell',
                'year': 2023,
                'doi': '10.1016/j.cell.2023.001',
                'abstract': 'This is a mock abstract for testing purposes.'
            },
            {
                'title': 'Semantic Scholar Mock Reference 2',
                'authors': 'Lee, Michael',
                'journal': 'PNAS',
                'year': 2022,
                'doi': '10.1073/pnas.2022.002'
            }
        ]


class OpenCitationsAPIClient(BaseAPIClient):
    """
    OpenCitations API クライアント
    
    OpenCitations APIから引用文献情報を取得
    """
    
    def __init__(self, config_manager, logger):
        super().__init__(config_manager, logger, 'opencitations')
        self.base_url = self.config.get('base_url', 'https://opencitations.net/index/api/v1')
        
        # レート制限設定（5req/sec）
        self.rate_limit = 5
        self.min_request_interval = 1.0 / self.rate_limit
    
    def fetch_citations(self, doi: str) -> List[Dict[str, Any]]:
        """
        OpenCitations APIから引用文献を取得
        
        Args:
            doi (str): 論文のDOI
            
        Returns:
            List[Dict[str, Any]]: 引用文献データリスト
        """
        try:
            self.logger.debug(f"Fetching citations from OpenCitations for DOI: {doi}")
            
            # DOI正規化
            normalized_doi = self._normalize_doi_for_api(doi)
            
            # API URL構築
            url = self._build_api_url(normalized_doi)
            
            # API呼び出し
            response_data = self._make_request(url)
            
            # レスポンス解析
            citations = self._parse_opencitations_response(response_data)
            
            self.logger.debug(f"Successfully fetched {len(citations)} citations from OpenCitations")
            return citations
            
        except APIError:
            # API関連のエラーはそのまま再発生させる
            raise
        except Exception as e:
            self.logger.error(f"OpenCitations API error for DOI {doi}: {e}")
            raise APIError(
                f"OpenCitations API failed for DOI {doi}: {str(e)}",
                error_code="OPENCITATIONS_API_ERROR",
                context={"doi": doi, "original_error": str(e)}
            )
    
    def _build_api_url(self, doi: str) -> str:
        """OpenCitations API URLを構築"""
        return f"{self.base_url}/references/{doi}"
    
    def _normalize_doi_for_api(self, doi: str) -> str:
        """OpenCitations API用にDOIを正規化"""
        if not doi:
            return doi
        
        # DOI URLプレフィックスを除去
        if doi.startswith('https://doi.org/'):
            return doi[len('https://doi.org/'):]
        elif doi.startswith('http://dx.doi.org/'):
            return doi[len('http://dx.doi.org/'):]
        elif doi.startswith('doi:'):
            return doi[len('doi:'):]
        
        return doi
    
    def _parse_opencitations_response(self, response_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """OpenCitations APIレスポンスを解析して引用文献リストを返す"""
        citations = []
        
        # レスポンスが空の場合
        if not response_data:
            return citations
        
        try:
            # OpenCitations APIレスポンス構造を解析
            for ref in response_data:
                citation = {}
                
                # Open Citation Identifier (OCI)
                if 'oci' in ref:
                    citation['oci'] = ref['oci']
                
                # 引用元論文DOI
                if 'citing' in ref:
                    citation['citing_doi'] = ref['citing']
                
                # 被引用論文DOI（これが引用文献）
                if 'cited' in ref:
                    citation['doi'] = ref['cited']
                
                # 作成日（出版日）
                if 'creation' in ref:
                    citation['creation'] = ref['creation']
                    # 年を抽出（OpenCitations形式：YYYY-MM-DD または YYYY）
                    try:
                        if ref['creation']:
                            year_str = str(ref['creation']).split('-')[0]
                            if year_str.isdigit():
                                citation['year'] = int(year_str)
                    except (ValueError, IndexError):
                        pass
                
                # タイムスパン
                if 'timespan' in ref:
                    citation['timespan'] = ref['timespan']
                
                # 自己引用情報
                if 'journal_sc' in ref:
                    citation['journal_self_citation'] = ref['journal_sc']
                if 'author_sc' in ref:
                    citation['author_self_citation'] = ref['author_sc']
                
                # 最低限のデータがある場合のみ追加
                if citation.get('doi'):
                    citations.append(citation)
            
            self.logger.debug(f"Parsed {len(citations)} citations from OpenCitations response")
            return citations
            
        except Exception as e:
            self.logger.warning(f"Error parsing OpenCitations response: {e}")
            return citations
    
    def _get_mock_citation_data(self, doi: str) -> List[Dict[str, Any]]:
        """モック引用文献データを返す（開発用）"""
        return [
            {
                'title': 'OpenCitations Mock Reference 1',
                'authors': 'Garcia, Maria',
                'year': 2021,
                'doi': '10.1000/opencitations.001'
            },
            {
                'title': 'OpenCitations Mock Reference 2', 
                'authors': 'Johnson, Robert',
                'year': 2020,
                'doi': '10.1000/opencitations.002'
            }
        ] 