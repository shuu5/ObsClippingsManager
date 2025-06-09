"""
CrossRef APIクライアント

CrossRef APIを使用して学術論文の引用文献を取得します。
"""

import time
import logging
from typing import Dict, List, Any, Optional
import requests

from .exceptions import APIRequestError, DataParsingError


class CrossRefClient:
    """CrossRef API クライアント"""
    
    def __init__(self, 
                 base_url: str = "https://api.crossref.org",
                 user_agent: str = "ObsClippingsManager/2.0 (mailto:user@example.com)",
                 request_delay: float = 1.0,
                 timeout: int = 30):
        """
        Args:
            base_url: CrossRef API ベースURL
            user_agent: User-Agentヘッダー
            request_delay: リクエスト間隔（秒）
            timeout: リクエストタイムアウト（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.user_agent = user_agent
        self.request_delay = request_delay
        self.timeout = timeout
        self.logger = logging.getLogger("ObsClippingsManager.CitationFetcher.CrossRef")
        
        # セッションを作成してヘッダーを設定
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        })
        
    def get_references(self, doi: str) -> List[Dict[str, Any]]:
        """
        DOIの引用文献を取得
        
        Args:
            doi: 論文のDOI
            
        Returns:
            引用文献のリスト
        """
        self.logger.info(f"Fetching references for DOI: {doi}")
        
        try:
            # 論文メタデータを取得
            work_data = self.get_work_metadata(doi)
            
            # 引用文献を抽出
            references = self._extract_references_from_work(work_data)
            
            self.logger.info(f"Successfully retrieved {len(references)} references for {doi}")
            return references
            
        except Exception as e:
            self.logger.error(f"Failed to get references for {doi}: {e}")
            raise
    
    def get_work_metadata(self, doi: str) -> Dict[str, Any]:
        """
        論文メタデータを取得
        
        Args:
            doi: 論文のDOI
            
        Returns:
            論文メタデータ
        """
        url = f"{self.base_url}/works/{doi}"
        
        try:
            response = self._make_request(url)
            
            if response.status_code == 200:
                data = response.json()
                
                # レスポンス構造の検証
                if 'message' not in data:
                    raise DataParsingError("Invalid CrossRef response structure")
                
                return data['message']
            
            elif response.status_code == 404:
                raise APIRequestError(f"DOI not found: {doi}", "CrossRef", 404)
            elif response.status_code == 429:
                raise APIRequestError("Rate limit exceeded", "CrossRef", 429)
            else:
                raise APIRequestError(
                    f"CrossRef API error: {response.status_code}",
                    "CrossRef", 
                    response.status_code
                )
                
        except requests.exceptions.RequestException as e:
            raise APIRequestError(f"Network error: {e}", "CrossRef")
    
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
            
            self.logger.debug(f"CrossRef API request: {url} -> {response.status_code}")
            return response
            
        except requests.exceptions.Timeout:
            raise APIRequestError(f"Request timeout for {url}", "CrossRef")
        except requests.exceptions.ConnectionError:
            raise APIRequestError(f"Connection error for {url}", "CrossRef")
        except requests.exceptions.RequestException as e:
            raise APIRequestError(f"Request failed: {e}", "CrossRef")
    
    def _extract_references_from_work(self, work_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        論文データから引用文献を抽出
        
        Args:
            work_data: CrossRefから取得した論文データ
            
        Returns:
            引用文献のリスト
        """
        references = []
        
        # 'reference'フィールドから引用文献を取得
        raw_references = work_data.get('reference', [])
        
        if not raw_references:
            self.logger.warning("No references found in work data")
            return references
        
        for i, ref in enumerate(raw_references):
            try:
                # 引用文献データを正規化
                normalized_ref = self._normalize_reference(ref, i)
                if normalized_ref:
                    references.append(normalized_ref)
                    
            except Exception as e:
                self.logger.warning(f"Failed to process reference {i}: {e}")
                continue
        
        return references
    
    def _normalize_reference(self, ref_data: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """
        引用文献データを正規化
        
        Args:
            ref_data: 生の引用文献データ
            index: 引用文献のインデックス
            
        Returns:
            正規化された引用文献データ
        """
        normalized = {
            'index': index,
            'source': 'CrossRef',
            'raw_data': ref_data
        }
        
        # 基本情報を抽出
        normalized['key'] = ref_data.get('key', f"ref_{index}")
        normalized['doi'] = ref_data.get('DOI')
        normalized['title'] = ref_data.get('article-title', ref_data.get('volume-title', ''))
        normalized['author'] = ref_data.get('author')
        normalized['year'] = ref_data.get('year')
        normalized['journal'] = ref_data.get('journal-title')
        normalized['volume'] = ref_data.get('volume')
        normalized['issue'] = ref_data.get('issue')
        normalized['page'] = ref_data.get('first-page')
        normalized['publisher'] = ref_data.get('publisher')
        
        # ISBN/ISSN
        normalized['isbn'] = ref_data.get('ISBN')
        normalized['issn'] = ref_data.get('ISSN')
        
        # 書籍情報
        normalized['book_title'] = ref_data.get('volume-title')
        normalized['edition'] = ref_data.get('edition')
        
        # 著者情報の正規化
        if normalized['author']:
            normalized['formatted_author'] = self._format_authors(normalized['author'])
        
        return normalized
    
    def _format_authors(self, authors: Any) -> str:
        """
        著者情報をフォーマット
        
        Args:
            authors: 著者データ（文字列またはリスト）
            
        Returns:
            フォーマットされた著者文字列
        """
        if isinstance(authors, str):
            return authors
        elif isinstance(authors, list):
            formatted_authors = []
            for author in authors:
                if isinstance(author, dict):
                    given = author.get('given', '')
                    family = author.get('family', '')
                    if given and family:
                        formatted_authors.append(f"{given} {family}")
                    elif family:
                        formatted_authors.append(family)
                elif isinstance(author, str):
                    formatted_authors.append(author)
            return ' and '.join(formatted_authors)
        else:
            return str(authors)
    
    def get_metadata_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        DOIを使用してメタデータを取得（MetadataEnricher互換）
        
        Args:
            doi: 論文のDOI
            
        Returns:
            正規化されたメタデータ（None if failed）
        """
        try:
            work_data = self.get_work_metadata(doi)
            if not work_data:
                return None
            
            # work_dataがすでにmessageの内容である場合の処理
            message = work_data
            
            # 正規化されたフォーマットに変換
            metadata = {
                'doi': message.get('DOI'),
                'title': message.get('title', [''])[0] if message.get('title') else '',
                'authors': [],
                'journal': message.get('container-title', [''])[0] if message.get('container-title') else '',
                'year': None,
                'volume': message.get('volume'),
                'issue': message.get('issue'),
                'pages': message.get('page'),
                'publisher': message.get('publisher'),
                'issn': message.get('ISSN', [None])[0] if message.get('ISSN') else None,
                'isbn': message.get('ISBN', [None])[0] if message.get('ISBN') else None,
                'source': 'CrossRef'
            }
            
            # 著者情報の処理
            if 'author' in message:
                authors = []
                for author in message['author']:
                    if isinstance(author, dict):
                        given = author.get('given', '')
                        family = author.get('family', '')
                        if given and family:
                            authors.append(f"{given} {family}")
                        elif family:
                            authors.append(family)
                metadata['authors'] = authors
            
            # 年度の取得
            if 'published-print' in message:
                date_parts = message['published-print'].get('date-parts', [[]])[0]
                if date_parts:
                    metadata['year'] = date_parts[0]
            elif 'published-online' in message:
                date_parts = message['published-online'].get('date-parts', [[]])[0]
                if date_parts:
                    metadata['year'] = date_parts[0]
            elif 'created' in message:
                date_parts = message['created'].get('date-parts', [[]])[0]
                if date_parts:
                    metadata['year'] = date_parts[0]
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata for DOI {doi}: {e}")
            return None


# 便利関数
def make_crossref_request(doi: str, user_agent: str = None) -> Dict[str, Any]:
    """
    CrossRef APIリクエストを実行（簡易版）
    
    Args:
        doi: 論文のDOI
        user_agent: User-Agentヘッダー
        
    Returns:
        論文メタデータ
    """
    client = CrossRefClient(user_agent=user_agent or "ObsClippingsManager/2.0")
    return client.get_work_metadata(doi)


def parse_crossref_references(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    CrossRefレスポンスから引用文献を抽出（簡易版）
    
    Args:
        response: CrossRef APIのレスポンス
        
    Returns:
        引用文献のリスト
    """
    client = CrossRefClient()
    return client._extract_references_from_work(response)


def validate_crossref_response(response: Dict[str, Any]) -> bool:
    """
    CrossRefレスポンスの妥当性チェック
    
    Args:
        response: チェック対象のレスポンス
        
    Returns:
        妥当性の真偽値
    """
    if not isinstance(response, dict):
        return False
    
    # 基本構造のチェック
    if 'message' not in response:
        return False
    
    message = response['message']
    
    # 必須フィールドのチェック
    required_fields = ['DOI', 'title']
    for field in required_fields:
        if field not in message:
            return False
    
    return True 