"""
Citation Fetcher専用例外クラス
"""

from ..shared.exceptions import ObsClippingsError


class CitationFetcherError(ObsClippingsError):
    """Citation Fetcher専用例外の基底クラス"""
    pass


class APIRequestError(CitationFetcherError):
    """APIリクエストエラー"""
    def __init__(self, message: str, api_name: str = None, status_code: int = None):
        super().__init__(message)
        self.api_name = api_name
        self.status_code = status_code


class DataParsingError(CitationFetcherError):
    """データ解析エラー"""
    def __init__(self, message: str, field: str = None, data: str = None):
        super().__init__(message)
        self.field = field
        self.data = data


class BibTeXConversionError(CitationFetcherError):
    """BibTeX変換エラー"""
    def __init__(self, message: str, reference_data: dict = None):
        super().__init__(message)
        self.reference_data = reference_data 