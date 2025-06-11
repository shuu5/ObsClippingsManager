"""
引用文献パーサー例外クラス
"""


class CitationParserError(Exception):
    """引用パーサー基底例外クラス"""
    pass


class PatternDetectionError(CitationParserError):
    """パターン検出エラー"""
    pass


class FormatConversionError(CitationParserError):
    """フォーマット変換エラー"""
    pass


class LinkExtractionError(CitationParserError):
    """リンク抽出エラー"""
    pass


class ConfigurationError(CitationParserError):
    """設定エラー"""
    pass


class ValidationError(CitationParserError):
    """バリデーションエラー"""
    pass 