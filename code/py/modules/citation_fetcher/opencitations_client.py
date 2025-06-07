"""
OpenCitations APIクライアント

OpenCitations APIを使用して学術論文の引用文献を取得します。
CrossRefのフォールバックとして使用されます。
"""

import time
import logging
from typing import Dict, List, Any, Optional
import requests

from .exceptions import APIRequestError, DataParsingError


class OpenCitationsClient:
    """OpenCitations API クライアント"""
    
    def __init__(self, 
                 config=None,
                 endpoints: List[str] = None,
                 request_delay: float = 0.5,
                 timeout: int = 30):
        """
        Args:
            config: ConfigManagerオブジェクト（他のAPIクライアントとの互換性のため）
            endpoints: OpenCitations APIエンドポイントのリスト
            request_delay: リクエスト間隔（秒）
            timeout: タイムアウト時間（秒）
        """
        # ConfigManagerから設定を取得（可能な場合）
        if config:
            self.request_delay = config.get_config_value('citation_fetcher.opencitations.request_delay', 0.5)
            self.timeout = config.get_config_value('citation_fetcher.opencitations.timeout', 30)
            self.endpoints = config.get_config_value('citation_fetcher.opencitations.endpoints', [
                "https://opencitations.net/index/api/v1",
                "https://w3id.org/oc/index/coci/api/v1"
            ])
        else:
            self.endpoints = endpoints or [
                "https://opencitations.net/index/api/v1",
                "https://w3id.org/oc/index/coci/api/v1"
            ]
            self.request_delay = request_delay
            self.timeout = timeout
            
        self.logger = logging.getLogger("ObsClippingsManager.CitationFetcher.OpenCitations")
        
        # セッションを作成
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'ObsClippingsManager/2.0'
        })
        
    def get_references(self, doi: str) -> List[Dict[str, Any]]:
        """
        DOIの引用文献を取得
        
        Args:
            doi: 論文のDOI
            
        Returns:
            引用文献のリスト（DOIのみ）
        """
        self.logger.info(f"Fetching references for DOI from OpenCitations: {doi}")
        
        # 複数のエンドポイントを試行
        last_error = None
        
        for endpoint in self.endpoints:
            try:
                # 引用関係を取得
                citations = self._get_citations_from_endpoint(doi, endpoint)
                
                if citations:
                    self.logger.info(
                        f"Successfully retrieved {len(citations)} references "
                        f"from {endpoint} for {doi}"
                    )
                    
                    # メタデータを補完
                    references = self._enrich_citations_with_metadata(citations)
                    return references
                else:
                    self.logger.warning(f"No citations found at {endpoint} for {doi}")
                    
            except Exception as e:
                self.logger.warning(f"Failed to get references from {endpoint}: {e}")
                last_error = e
                continue
        
        # すべてのエンドポイントで失敗
        if last_error:
            raise last_error
        else:
            raise APIRequestError(f"No citations found for {doi}", "OpenCitations")
    
    def get_reference_metadata(self, doi: str) -> Dict[str, Any]:
        """
        引用文献のメタデータを取得
        
        Args:
            doi: 引用文献のDOI
            
        Returns:
            メタデータ辞書
        """
        # OpenCitationsはメタデータAPIを提供していないため
        # 基本的なDOI情報のみを返す
        return {
            'doi': doi,
            'source': 'OpenCitations',
            'metadata_available': False
        }
    
    def get_metadata_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        DOIから論文のメタデータを取得（MetadataEnricher用）
        
        Args:
            doi: 論文のDOI
            
        Returns:
            論文のメタデータ（OpenCitationsでは限定的）
        """
        self.logger.debug(f"Attempting to get metadata for {doi} from OpenCitations")
        
        try:
            # OpenCitationsではメタデータAPIが限定的なため、
            # 基本情報のみを提供
            metadata = {
                'doi': doi,
                'title': None,  # OpenCitationsでは通常利用不可
                'authors': None,  # OpenCitationsでは通常利用不可
                'journal': None,  # OpenCitationsでは通常利用不可
                'year': None,  # OpenCitationsでは通常利用不可
                'volume': None,
                'issue': None,
                'pages': None,
                'source': 'opencitations',
                'metadata_quality': 'limited'  # OpenCitationsは主に引用関係データ
            }
            
            self.logger.debug(f"OpenCitations metadata (limited) for {doi}")
            return metadata
            
        except Exception as e:
            self.logger.warning(f"Failed to get metadata from OpenCitations for {doi}: {e}")
            return None
    
    def is_available(self) -> bool:
        """
        APIの利用可能性をチェック
        
        Returns:
            利用可能かどうか
        """
        try:
            # 最初のエンドポイントに軽いリクエストを送信
            test_url = f"{self.endpoints[0]}/references/10.1038/nature12373"
            response = self.session.head(test_url, timeout=5)
            return response.status_code in [200, 404]  # 404も正常（データが見つからないだけ）
        except Exception:
            return False
    
    def get_client_info(self) -> Dict[str, Any]:
        """
        クライアント情報を取得
        
        Returns:
            クライアント情報
        """
        return {
            'name': 'OpenCitations',
            'endpoints': self.endpoints,
            'available': self.is_available(),
            'description': 'Citation data and limited metadata from OpenCitations'
        }
    
    def _get_citations_from_endpoint(self, doi: str, endpoint: str) -> List[Dict[str, Any]]:
        """
        特定のエンドポイントから引用関係を取得
        
        Args:
            doi: 論文のDOI
            endpoint: APIエンドポイント
            
        Returns:
            引用関係のリスト
        """
        url = f"{endpoint}/references/{doi}"
        
        try:
            response = self._make_request(url)
            
            if response.status_code == 200:
                data = response.json()
                
                # レスポンスがリストかチェック
                if not isinstance(data, list):
                    raise DataParsingError(f"Invalid OpenCitations response format from {endpoint}")
                
                return data
            
            elif response.status_code == 404:
                # 404は正常（引用文献が見つからない）
                self.logger.info(f"No references found for {doi} at {endpoint}")
                return []
            else:
                raise APIRequestError(
                    f"OpenCitations API error from {endpoint}: {response.status_code}",
                    "OpenCitations",
                    response.status_code
                )
                
        except requests.exceptions.RequestException as e:
            raise APIRequestError(f"Network error for {endpoint}: {e}", "OpenCitations")
    
    def _make_request(self, url: str) -> requests.Response:
        """
        APIリクエストを実行
        
        Args:
            url: リクエストURL
            
        Returns:
            レスポンスオブジェクト
        """
        # レート制限対応
        time.sleep(self.request_delay)
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            
            self.logger.debug(f"OpenCitations API request: {url} -> {response.status_code}")
            return response
            
        except requests.exceptions.Timeout:
            raise APIRequestError(f"Request timeout for {url}", "OpenCitations")
        except requests.exceptions.ConnectionError:
            raise APIRequestError(f"Connection error for {url}", "OpenCitations")
        except requests.exceptions.RequestException as e:
            raise APIRequestError(f"Request failed: {e}", "OpenCitations")
    
    def _enrich_citations_with_metadata(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        引用文献にメタデータを補完
        
        Args:
            citations: 生の引用文献データ
            
        Returns:
            メタデータ補完済みの引用文献リスト
        """
        enriched_references = []
        
        for i, citation in enumerate(citations):
            try:
                # OpenCitationsの引用データを正規化
                normalized_ref = self._normalize_citation(citation, i)
                if normalized_ref:
                    enriched_references.append(normalized_ref)
                    
            except Exception as e:
                self.logger.warning(f"Failed to process citation {i}: {e}")
                continue
        
        return enriched_references
    
    def _normalize_citation(self, citation: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """
        OpenCitationsの引用データを正規化
        
        Args:
            citation: 生の引用データ
            index: インデックス
            
        Returns:
            正規化された引用文献データ
        """
        normalized = {
            'index': index,
            'source': 'OpenCitations',
            'raw_data': citation
        }
        
        # OpenCitationsのフィールドマッピング
        # 'cited'フィールドから被引用DOIを取得
        cited_doi = citation.get('cited')
        if cited_doi:
            normalized['doi'] = cited_doi
        
        # その他の利用可能なフィールド
        normalized['citing'] = citation.get('citing')  # 引用元DOI
        normalized['creation'] = citation.get('creation')  # 作成日時
        normalized['timespan'] = citation.get('timespan')  # 期間
        
        # OpenCitationsには詳細なメタデータがないため基本情報のみ
        # DOIから推測可能な情報があれば追加
        if normalized.get('doi'):
            # DOIプレフィックスから出版社を推測（簡易版）
            doi_prefix = normalized['doi'].split('/')[0] if '/' in normalized['doi'] else ''
            normalized['doi_prefix'] = doi_prefix
        
        return normalized


# 便利関数
def make_opencitations_request(doi: str, endpoint: str = None) -> List[Dict[str, Any]]:
    """
    OpenCitations APIリクエストを実行（簡易版）
    
    Args:
        doi: 論文のDOI
        endpoint: APIエンドポイント
        
    Returns:
        引用関係のリスト
    """
    endpoints = [endpoint] if endpoint else [
        "https://opencitations.net/index/api/v1",
        "https://w3id.org/oc/index/coci/api/v1"
    ]
    
    client = OpenCitationsClient(endpoints=endpoints)
    return client._get_citations_from_endpoint(doi, endpoints[0])


def parse_opencitations_response(response: List[Dict[str, Any]]) -> List[str]:
    """
    OpenCitationsレスポンスからDOIリストを抽出
    
    Args:
        response: OpenCitations APIのレスポンス
        
    Returns:
        DOIのリスト
    """
    dois = []
    
    for citation in response:
        if isinstance(citation, dict):
            # 被引用DOIを取得
            cited_doi = citation.get('cited')
            if cited_doi:
                dois.append(cited_doi)
    
    return dois


def fetch_metadata_for_dois(dois: List[str]) -> List[Dict[str, Any]]:
    """
    DOIリストのメタデータを一括取得
    
    Args:
        dois: DOIのリスト
        
    Returns:
        メタデータ付き引用文献のリスト
    """
    client = OpenCitationsClient()
    references = []
    
    for i, doi in enumerate(dois):
        try:
            metadata = client.get_reference_metadata(doi)
            metadata['index'] = i
            references.append(metadata)
        except Exception:
            # メタデータ取得失敗時は基本情報のみ
            references.append({
                'index': i,
                'doi': doi,
                'source': 'OpenCitations',
                'metadata_available': False
            })
    
    return references 