#!/usr/bin/env python3
"""
ObsClippingsManager Exception Hierarchy

階層的例外管理システム
- 基底例外クラス: ObsClippingsManagerError
- 専用例外クラス群
- エラーハンドリングユーティリティ
"""


class ObsClippingsManagerError(Exception):
    """
    ObsClippingsManager基底例外クラス
    
    全てのObsClippingsManager関連例外の基底クラス。
    エラーコード、コンテキスト、根本原因の追跡機能を提供。
    """
    
    def __init__(self, message, error_code=None, context=None, cause=None):
        """
        基底例外の初期化
        
        Args:
            message (str): エラーメッセージ
            error_code (str, optional): エラーコード
            context (dict, optional): エラー発生時のコンテキスト情報
            cause (Exception, optional): 根本原因となった例外
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.context = context or {}
        self.__cause__ = cause  # Python 3.x互換性のため__cause__を使用
    
    def __str__(self):
        """エラーメッセージの文字列表現"""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ConfigurationError(ObsClippingsManagerError):
    """
    設定エラー
    
    設定ファイル、環境変数、設定値検証エラー等で使用。
    """
    pass


class ValidationError(ObsClippingsManagerError):
    """
    データ検証エラー
    
    YAML形式、BibTeX形式、データ構造検証エラー等で使用。
    """
    pass


class ProcessingError(ObsClippingsManagerError):
    """
    処理実行エラー
    
    ワークフロー実行、ファイル処理、データ変換エラー等で使用。
    """
    pass


class APIError(ObsClippingsManagerError):
    """
    API通信エラー
    
    Claude API、CrossRef API、OpenCitations API等の通信エラーで使用。
    """
    pass


class FileSystemError(ObsClippingsManagerError):
    """
    ファイルシステムエラー
    
    ファイル読み書き、ディレクトリ操作、バックアップエラー等で使用。
    """
    pass


class YAMLError(ObsClippingsManagerError):
    """
    YAMLヘッダー処理エラー
    
    YAMLヘッダーの読み書き、構造検証、修復エラー等で使用。
    """
    pass


class BibTeXError(ObsClippingsManagerError):
    """
    BibTeX処理エラー
    
    BibTeXファイル解析、citation_key抽出、形式検証エラー等で使用。
    """
    pass


# エラーハンドリングユーティリティ

def standard_error_handler(func):
    """
    標準エラーハンドリングデコレータ
    
    未知の例外を標準形式のProcessingErrorに変換し、
    コンテキスト情報を付加する。
    
    Args:
        func: デコレートする関数
        
    Returns:
        wrapper: ラップされた関数
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ObsClippingsManagerError:
            raise  # 既知のエラーは再送出
        except Exception as e:
            # 未知のエラーを標準形式に変換
            raise ProcessingError(
                f"Unexpected error in {func.__name__}: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                context={
                    "function": func.__name__,
                    "args": args,
                    "kwargs": kwargs
                },
                cause=e
            )
    return wrapper


def create_error_context(operation, file_path=None, **kwargs):
    """
    エラーコンテキスト情報を作成
    
    Args:
        operation (str): 実行中の操作名
        file_path (str, optional): 処理対象ファイルパス
        **kwargs: 追加のコンテキスト情報
        
    Returns:
        dict: エラーコンテキスト辞書
    """
    context = {
        "operation": operation,
        "timestamp": None  # 必要に応じてdatetimeで設定
    }
    
    if file_path:
        context["file_path"] = file_path
    
    context.update(kwargs)
    return context


def format_error_for_logging(error):
    """
    ログ出力用のエラー情報フォーマット
    
    Args:
        error (ObsClippingsManagerError): エラーオブジェクト
        
    Returns:
        dict: ログ出力用辞書
    """
    error_info = {
        "error_type": type(error).__name__,
        "message": error.message,
        "error_code": error.error_code
    }
    
    if error.context:
        error_info["context"] = error.context
    
    if hasattr(error, '__cause__') and error.__cause__:
        error_info["root_cause"] = str(error.__cause__)
    
    return error_info 