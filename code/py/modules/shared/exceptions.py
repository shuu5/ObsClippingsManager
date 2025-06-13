#!/usr/bin/env python3
"""
ObsClippingsManager Exception Hierarchy

階層的例外管理システム
- 基底例外クラス: ObsClippingsManagerError
- 専用例外クラス群
- エラーハンドリングユーティリティ
- リトライ機構
"""

import time
import random
from functools import wraps
from typing import Tuple, Type, Union, Optional


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


# リトライ機構

def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 1.5,
    jitter: bool = True,
    retry_exceptions: Tuple[Type[Exception], ...] = (APIError, ProcessingError)
):
    """
    リトライデコレーター
    
    指定した例外が発生した場合に、指数バックオフ戦略でリトライを実行する。
    
    Args:
        max_attempts (int): 最大試行回数（デフォルト: 3）
        delay (float): 初期遅延時間（秒）（デフォルト: 1.0）
        backoff_factor (float): 遅延時間の増加率（デフォルト: 1.5）
        jitter (bool): ランダムなジッターを追加するか（デフォルト: True）
        retry_exceptions (Tuple[Type[Exception], ...]): リトライ対象の例外タイプ
    
    Returns:
        decorator: リトライ機能付きのデコレーター
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # リトライ対象外の例外は即座に再発生
                    if not isinstance(e, retry_exceptions):
                        raise
                    
                    # 最大試行回数に達した場合は例外を再発生
                    if attempt >= max_attempts:
                        raise
                    
                    # リトライ前の遅延
                    sleep_time = current_delay
                    if jitter:
                        # ±20%のランダムジッターを追加
                        jitter_factor = 1.0 + (random.random() - 0.5) * 0.4
                        sleep_time *= jitter_factor
                    
                    time.sleep(sleep_time)
                    
                    # 次回の遅延時間を計算（指数バックオフ）
                    current_delay *= backoff_factor
                    attempt += 1
            
            # 論理的にここには到達しないが、念のため
            raise ProcessingError(
                f"Retry mechanism failed after {max_attempts} attempts",
                error_code="RETRY_EXHAUSTED"
            )
        
        return wrapper
    return decorator


def get_retry_config_from_settings(config_manager=None):
    """
    設定管理システムからリトライ設定を取得
    
    Args:
        config_manager: ConfigManagerインスタンス
        
    Returns:
        dict: リトライ設定辞書
    """
    default_config = {
        'max_attempts': 3,
        'delay': 1.0,
        'backoff_factor': 1.5,
        'jitter': True,
        'retry_exceptions': (APIError, ProcessingError)
    }
    
    if config_manager is None:
        return default_config
    
    try:
        # 設定管理システムからリトライ設定を取得
        retry_config = config_manager.get_setting('retry', default_config)
        
        # 例外タイプの文字列を実際のクラスに変換
        if 'retry_exceptions' in retry_config:
            exception_names = retry_config['retry_exceptions']
            if isinstance(exception_names, (list, tuple)):
                exception_classes = []
                exception_map = {
                    'APIError': APIError,
                    'ProcessingError': ProcessingError,
                    'FileSystemError': FileSystemError,
                    'ValidationError': ValidationError,
                    'ConfigurationError': ConfigurationError
                }
                
                for name in exception_names:
                    if name in exception_map:
                        exception_classes.append(exception_map[name])
                
                retry_config['retry_exceptions'] = tuple(exception_classes)
        
        return retry_config
    except Exception:
        # 設定取得に失敗した場合はデフォルト設定を返す
        return default_config


def smart_retry(config_manager=None):
    """
    設定管理システム統合リトライデコレーター
    
    ConfigManagerから設定を動的に取得してリトライを実行する。
    
    Args:
        config_manager: ConfigManagerインスタンス
        
    Returns:
        decorator: 設定連携リトライデコレーター
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = get_retry_config_from_settings(config_manager)
            
            # retry_on_errorデコレーターを動的に適用
            retry_decorator = retry_on_error(**config)
            retried_func = retry_decorator(func)
            
            return retried_func(*args, **kwargs)
        
        return wrapper
    return decorator


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