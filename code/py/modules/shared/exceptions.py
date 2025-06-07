"""
共通例外クラス

ObsClippingsManager統合システムで使用される例外クラスを定義します。
"""


class ObsClippingsError(Exception):
    """システム全体の基底例外クラス"""
    pass


class ConfigError(ObsClippingsError):
    """設定関連エラー"""
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message)
        self.config_key = config_key


class BibTeXParseError(ObsClippingsError):
    """BibTeX解析エラー"""
    def __init__(self, message: str, line_number: int = None, entry_key: str = None):
        super().__init__(message)
        self.line_number = line_number
        self.entry_key = entry_key


class FileOperationError(ObsClippingsError):
    """ファイル操作エラー"""
    def __init__(self, message: str, file_path: str = None, operation: str = None):
        super().__init__(message)
        self.file_path = file_path
        self.operation = operation


class ValidationError(ObsClippingsError):
    """バリデーションエラー"""
    def __init__(self, message: str, field: str = None, value: str = None):
        super().__init__(message)
        self.field = field
        self.value = value


class WorkflowError(ObsClippingsError):
    """ワークフロー実行エラー"""
    pass


class SyncCheckError(WorkflowError):
    """同期チェック固有のエラー"""
    pass


class BibTeXParsingError(SyncCheckError):
    """BibTeXファイル解析エラー（Sync Check用）"""
    pass


class ClippingsAccessError(SyncCheckError):
    """Clippingsディレクトリアクセスエラー"""
    pass


class DOIProcessingError(SyncCheckError):
    """DOI処理エラー"""
    pass


# Citation Parser専用例外クラス
class CitationParserError(WorkflowError):
    """引用文献パース関連エラー"""
    pass


class InvalidCitationPatternError(CitationParserError):
    """無効な引用パターンエラー"""
    def __init__(self, message: str, pattern: str = None, position: int = None):
        super().__init__(message)
        self.pattern = pattern
        self.position = position


class CitationParseTimeoutError(CitationParserError):
    """パース処理タイムアウトエラー"""
    def __init__(self, message: str, timeout_seconds: int = None):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


class PatternDetectionError(CitationParserError):
    """パターン検出エラー"""
    pass


class FormatConversionError(CitationParserError):
    """フォーマット変換エラー"""
    pass


class LinkExtractionError(CitationParserError):
    """リンク抽出エラー"""
    pass 