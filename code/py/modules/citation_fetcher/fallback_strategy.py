"""
フォールバック戦略

CrossRef APIが失敗した場合にOpenCitations APIを使用するフォールバック戦略を実装します。
"""

import logging
from typing import Dict, List, Any, Tuple, Optional

from .crossref_client import CrossRefClient
from .opencitations_client import OpenCitationsClient
from .exceptions import APIRequestError, CitationFetcherError


class FallbackStrategy:
    """API フォールバック戦略"""
    
    def __init__(self, 
                 crossref_client: CrossRefClient,
                 opencitations_client: OpenCitationsClient,
                 max_retries: int = 3):
        """
        Args:
            crossref_client: CrossRef APIクライアント
            opencitations_client: OpenCitations APIクライアント
            max_retries: 最大リトライ回数
        """
        self.crossref_client = crossref_client
        self.opencitations_client = opencitations_client
        self.max_retries = max_retries
        self.logger = logging.getLogger("ObsClippingsManager.CitationFetcher.FallbackStrategy")
        
    def get_references_with_fallback(self, doi: str) -> Tuple[List[Dict], str]:
        """
        フォールバック戦略で引用文献を取得
        
        Args:
            doi: 論文のDOI
            
        Returns:
            Tuple[引用文献リスト, 使用したAPIソース名]
        """
        self.logger.info(f"Starting fallback strategy for DOI: {doi}")
        
        # Phase 1: CrossRef APIを試行
        try:
            references = self._try_crossref_with_retries(doi)
            if references:
                self.logger.info(f"CrossRef successful for {doi}: {len(references)} references")
                return references, "CrossRef"
                
        except Exception as e:
            self.logger.warning(f"CrossRef failed for {doi}: {e}")
        
        # Phase 2: OpenCitations APIをフォールバック
        try:
            references = self._try_opencitations_with_retries(doi)
            if references:
                self.logger.info(f"OpenCitations successful for {doi}: {len(references)} references")
                return references, "OpenCitations"
                
        except Exception as e:
            self.logger.error(f"OpenCitations also failed for {doi}: {e}")
        
        # すべて失敗
        self.logger.error(f"All APIs failed for {doi}")
        return [], "None"
    
    def _try_crossref_with_retries(self, doi: str) -> List[Dict[str, Any]]:
        """
        CrossRef APIをリトライ付きで試行
        
        Args:
            doi: 論文のDOI
            
        Returns:
            引用文献のリスト
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"CrossRef attempt {attempt + 1}/{self.max_retries} for {doi}")
                
                references = self.crossref_client.get_references(doi)
                
                # 成功条件をチェック
                if self._is_crossref_success(references):
                    return references
                else:
                    self.logger.warning(f"CrossRef returned empty or invalid results for {doi}")
                    
            except APIRequestError as e:
                last_error = e
                if not self._should_retry_crossref_error(e):
                    self.logger.info(f"CrossRef error not retryable for {doi}: {e}")
                    break
                else:
                    self.logger.warning(f"CrossRef error, will retry for {doi}: {e}")
                    continue
                    
            except Exception as e:
                last_error = e
                self.logger.warning(f"Unexpected CrossRef error for {doi}: {e}")
                break
        
        # リトライ回数を使い切った場合
        if last_error:
            raise last_error
        else:
            raise APIRequestError(f"CrossRef failed after {self.max_retries} attempts", "CrossRef")
    
    def _try_opencitations_with_retries(self, doi: str) -> List[Dict[str, Any]]:
        """
        OpenCitations APIをリトライ付きで試行
        
        Args:
            doi: 論文のDOI
            
        Returns:
            引用文献のリスト
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"OpenCitations attempt {attempt + 1}/{self.max_retries} for {doi}")
                
                references = self.opencitations_client.get_references(doi)
                
                # 成功条件をチェック
                if self._is_opencitations_success(references):
                    return references
                else:
                    self.logger.warning(f"OpenCitations returned empty results for {doi}")
                    
            except APIRequestError as e:
                last_error = e
                if not self._should_retry_opencitations_error(e):
                    self.logger.info(f"OpenCitations error not retryable for {doi}: {e}")
                    break
                else:
                    self.logger.warning(f"OpenCitations error, will retry for {doi}: {e}")
                    continue
                    
            except Exception as e:
                last_error = e
                self.logger.warning(f"Unexpected OpenCitations error for {doi}: {e}")
                break
        
        # リトライ回数を使い切った場合
        if last_error:
            raise last_error
        else:
            raise APIRequestError(f"OpenCitations failed after {self.max_retries} attempts", "OpenCitations")
    
    def handle_api_error(self, error: Exception, api_name: str) -> bool:
        """
        APIエラーのハンドリング
        
        Args:
            error: 発生したエラー
            api_name: API名
            
        Returns:
            True: リトライ可能, False: フォールバック必要
        """
        if isinstance(error, APIRequestError):
            if api_name == "CrossRef":
                return self._should_retry_crossref_error(error)
            elif api_name == "OpenCitations":
                return self._should_retry_opencitations_error(error)
        
        # その他のエラーはリトライしない
        return False
    
    def _is_crossref_success(self, references: List[Dict[str, Any]]) -> bool:
        """
        CrossRef API成功条件をチェック
        
        Args:
            references: 取得した引用文献リスト
            
        Returns:
            成功かどうか
        """
        # 空でない結果があれば成功
        return isinstance(references, list) and len(references) > 0
    
    def _is_opencitations_success(self, references: List[Dict[str, Any]]) -> bool:
        """
        OpenCitations API成功条件をチェック
        
        Args:
            references: 取得した引用文献リスト
            
        Returns:
            成功かどうか
        """
        # 空でない結果があれば成功
        return isinstance(references, list) and len(references) > 0
    
    def _should_retry_crossref_error(self, error: APIRequestError) -> bool:
        """
        CrossRefエラーがリトライ可能かを判定
        
        Args:
            error: APIリクエストエラー
            
        Returns:
            リトライ可能かどうか
        """
        if not error.status_code:
            # ネットワークエラーなどはリトライ可能
            return True
        
        # HTTPステータスコードによる判定
        retryable_codes = {
            429,  # Rate limit exceeded
            500,  # Internal server error
            502,  # Bad gateway
            503,  # Service unavailable
            504   # Gateway timeout
        }
        
        return error.status_code in retryable_codes
    
    def _should_retry_opencitations_error(self, error: APIRequestError) -> bool:
        """
        OpenCitationsエラーがリトライ可能かを判定
        
        Args:
            error: APIリクエストエラー
            
        Returns:
            リトライ可能かどうか
        """
        if not error.status_code:
            # ネットワークエラーなどはリトライ可能
            return True
        
        # HTTPステータスコードによる判定
        retryable_codes = {
            500,  # Internal server error
            502,  # Bad gateway
            503,  # Service unavailable
            504   # Gateway timeout
        }
        
        # OpenCitationsはRate limitがないので429は含めない
        return error.status_code in retryable_codes
    
    def get_strategy_statistics(self) -> Dict[str, Any]:
        """
        フォールバック戦略の統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        # 実装では各APIの成功/失敗回数を追跡する必要がある
        # 簡易版として基本情報のみ返す
        return {
            "max_retries": self.max_retries,
            "crossref_available": self.crossref_client is not None,
            "opencitations_available": self.opencitations_client is not None
        }


# フォールバック処理フロー用のヘルパー関数
def create_fallback_strategy_from_config(config: Dict[str, Any]) -> FallbackStrategy:
    """
    設定からフォールバック戦略を作成
    
    Args:
        config: Citation Fetcher設定
        
    Returns:
        フォールバック戦略インスタンス
    """
    # CrossRefクライアントを作成
    crossref_client = CrossRefClient(
        base_url=config.get('crossref_base_url', 'https://api.crossref.org'),
        user_agent=config.get('user_agent', 'ObsClippingsManager/2.0'),
        request_delay=config.get('request_delay', 1.0),
        timeout=config.get('timeout', 30)
    )
    
    # OpenCitationsクライアントを作成
    opencitations_client = OpenCitationsClient(
        endpoints=config.get('opencitations_endpoints', [
            "https://opencitations.net/index/api/v1",
            "https://w3id.org/oc/index/coci/api/v1"
        ]),
        request_delay=config.get('request_delay', 0.5),
        timeout=config.get('timeout', 30)
    )
    
    # フォールバック戦略を作成
    return FallbackStrategy(
        crossref_client=crossref_client,
        opencitations_client=opencitations_client,
        max_retries=config.get('max_retries', 3)
    )


def determine_success_source(references: List[Dict[str, Any]], source: str) -> str:
    """
    成功したAPIソースを決定
    
    Args:
        references: 引用文献リスト
        source: APIソース名
        
    Returns:
        確定したソース名
    """
    if not references:
        return "None"
    
    # 実際のデータソースを確認
    if references and isinstance(references[0], dict):
        actual_source = references[0].get('source', source)
        return actual_source
    
    return source


def log_fallback_result(doi: str, 
                       source: str, 
                       reference_count: int, 
                       logger: Optional[logging.Logger] = None):
    """
    フォールバック結果をログ出力
    
    Args:
        doi: 論文のDOI
        source: 使用されたAPIソース
        reference_count: 取得された引用文献数
        logger: ロガーインスタンス
    """
    if not logger:
        logger = logging.getLogger("ObsClippingsManager.CitationFetcher.FallbackStrategy")
    
    if source == "None":
        logger.error(f"All APIs failed for {doi}")
    else:
        logger.info(f"{source} successful for {doi}: {reference_count} references")


def create_error_summary(errors: List[Exception]) -> Dict[str, Any]:
    """
    エラーサマリーを作成
    
    Args:
        errors: エラーのリスト
        
    Returns:
        エラーサマリー
    """
    summary = {
        "total_errors": len(errors),
        "error_types": {},
        "api_errors": {},
        "network_errors": 0,
        "other_errors": 0
    }
    
    for error in errors:
        error_type = type(error).__name__
        summary["error_types"][error_type] = summary["error_types"].get(error_type, 0) + 1
        
        if isinstance(error, APIRequestError):
            api_name = error.api_name or "Unknown"
            summary["api_errors"][api_name] = summary["api_errors"].get(api_name, 0) + 1
            
            # ネットワークエラーかどうかの判定
            if "network" in str(error).lower() or "connection" in str(error).lower():
                summary["network_errors"] += 1
        else:
            summary["other_errors"] += 1
    
    return summary 