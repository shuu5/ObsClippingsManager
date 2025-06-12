"""
共通ユーティリティモジュール

ObsClippingsManager統合システムで使用される共通的なユーティリティ関数を提供します。
"""

import logging
import os
import re
import shutil
import sys
import time
import unicodedata
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Callable, Any, Tuple, Optional

from .exceptions import FileOperationError, ValidationError


# ファイル操作関数
def safe_file_operation(operation: Callable, *args, **kwargs) -> Tuple[bool, Optional[Exception]]:
    """
    安全なファイル操作実行
    
    Args:
        operation: 実行する操作関数
        *args, **kwargs: 操作関数の引数
        
    Returns:
        (成功フラグ, 例外オブジェクト)
    """
    try:
        result = operation(*args, **kwargs)
        return True, None
    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        return False, e
    except PermissionError as e:
        logging.error(f"Permission denied: {e}")
        return False, e
    except OSError as e:
        logging.error(f"OS error: {e}")
        return False, e
    except Exception as e:
        logging.error(f"Unexpected error in {operation.__name__}: {e}")
        return False, e


def create_directory_if_not_exists(dir_path: str) -> bool:
    """ディレクトリが存在しなければ作成"""
    try:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"Failed to create directory {dir_path}: {e}")
        return False


def get_file_size_mb(file_path: str) -> float:
    """ファイルサイズをMB単位で取得"""
    try:
        size_bytes = Path(file_path).stat().st_size
        return size_bytes / (1024 * 1024)
    except Exception as e:
        logging.error(f"Failed to get file size for {file_path}: {e}")
        return 0.0


def backup_file(source_path: str, backup_dir: str, suffix: str = ".backup") -> str:
    """
    ファイルのバックアップを作成
    
    Args:
        source_path: バックアップ元ファイルパス
        backup_dir: バックアップ先ディレクトリ
        suffix: バックアップファイルのサフィックス
        
    Returns:
        バックアップファイルのパス
    """
    source = Path(source_path)
    if not source.exists():
        raise FileOperationError(f"Source file not found: {source_path}")
    
    # バックアップディレクトリの作成
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    
    # タイムスタンプ付きバックアップファイル名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{source.stem}_{timestamp}{suffix}{source.suffix}"
    backup_file_path = backup_path / backup_name
    
    try:
        shutil.copy2(source, backup_file_path)
        logging.info(f"Backup created: {backup_file_path}")
        return str(backup_file_path)
    except Exception as e:
        raise FileOperationError(f"Failed to create backup: {e}")


# 文字列処理関数
def normalize_text_for_comparison(text: str) -> str:
    """
    比較用にテキストを正規化
    - Unicode正規化
    - 特殊文字除去
    - 空白の統一
    """
    if not text:
        return ""
    
    # Unicode正規化（NFKD形式）
    text = unicodedata.normalize('NFKD', text)
    
    # アクセント記号を除去
    text = ''.join(c for c in text if not unicodedata.combining(c))
    
    # 句読点と特殊文字を空白に置換
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # 連続する空白を単一スペースに
    text = re.sub(r'\s+', ' ', text)
    
    # 小文字化と前後の空白除去
    text = text.strip().lower()
    
    return text


def escape_filename(filename: str, max_length: int = 255) -> str:
    """ファイル名に使用できない文字をエスケープ"""
    # 無効な文字を置換
    invalid_chars = r'[<>:"/\\|?*]'
    escaped = re.sub(invalid_chars, '_', filename)
    
    # 制御文字を除去
    escaped = ''.join(c for c in escaped if ord(c) >= 32)
    
    # 長さ制限（拡張子を考慮）
    if len(escaped) > max_length:
        name, ext = os.path.splitext(escaped)
        max_name_length = max_length - len(ext)
        escaped = name[:max_name_length] + ext
    
    # 先頭・末尾の空白とピリオドを除去
    escaped = escaped.strip(' .')
    
    # 空文字列になった場合のフォールバック
    if not escaped:
        escaped = "unnamed"
    
    return escaped


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """テキストを指定長で切り詰め"""
    if len(text) <= max_length:
        return text
    
    if max_length <= len(suffix):
        return suffix[:max_length]
    
    return text[:max_length - len(suffix)] + suffix


# 進捗表示関数
class ProgressTracker:
    """進捗追跡クラス"""
    
    def __init__(self, total: int, description: str = "Processing"):
        """
        Args:
            total: 総処理数
            description: 処理の説明
        """
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
        
    def update(self, current: int = None, message: str = "") -> None:
        """進捗を更新"""
        if current is not None:
            self.current = current
        else:
            self.current += 1
            
        if self.total > 0:
            progress = self.current / self.total * 100
            bar = show_progress_bar(self.current, self.total)
            
            # 経過時間と推定残り時間
            elapsed = time.time() - self.start_time
            if self.current > 0:
                eta = (elapsed / self.current) * (self.total - self.current)
                eta_str = f", ETA: {eta:.1f}s"
            else:
                eta_str = ""
                
            status = f"\r{self.description}: {bar} {progress:.1f}% ({self.current}/{self.total}){eta_str}"
            if message:
                status += f" - {message}"
                
            print(status, end='', flush=True)
            
    def finish(self, success_count: int = None, error_count: int = None) -> None:
        """処理完了"""
        elapsed = time.time() - self.start_time
        print()  # 改行
        
        if success_count is not None and error_count is not None:
            print(f"{self.description} completed in {elapsed:.1f}s - Success: {success_count}, Errors: {error_count}")
        else:
            print(f"{self.description} completed in {elapsed:.1f}s")


def show_progress_bar(current: int, total: int, width: int = 50) -> str:
    """プログレスバー文字列を生成"""
    if total == 0:
        return "[" + "-" * width + "]"
    
    filled_length = int(width * current // total)
    bar = "█" * filled_length + "-" * (width - filled_length)
    
    return f"[{bar}]"


# バリデーション関数
def validate_doi(doi: str) -> bool:
    """DOI形式の妥当性チェック"""
    # bibtex_parserのvalidate_doi関数を使用してコード重複を避ける
    from .bibtex_parser import validate_doi as bibtex_validate_doi
    return bibtex_validate_doi(doi)


def validate_citation_key(citation_key: str) -> bool:
    """Citation keyの妥当性チェック"""
    if not citation_key:
        return False
    
    # 英数字、ハイフン、アンダースコア、コロン、ピリオドのみ許可
    pattern = r'^[\w\-.:]+$'
    return bool(re.match(pattern, citation_key))


def validate_file_path(file_path: str) -> bool:
    """ファイルパスの妥当性チェック"""
    try:
        path = Path(file_path)
        # 相対パスの場合は現在のディレクトリからの相対パスとして解決
        if not path.is_absolute():
            path = path.resolve()
        return True
    except Exception:
        return False


def validate_url(url: str) -> bool:
    """URL形式の妥当性チェック"""
    if not url:
        return False
    
    # 基本的なURLパターン
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(url_pattern, url, re.IGNORECASE))


# デコレータ
def measure_time(func: Callable) -> Callable:
    """実行時間を測定するデコレータ"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logging.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
        return result
    return wrapper


def safe_operation(func: Callable) -> Callable:
    """エラーハンドリング付きの安全な操作デコレータ"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}")
            raise
    return wrapper


# ユーティリティ関数
def print_header(title: str, version: str = "2.0.0") -> None:
    """アプリケーションヘッダーを印刷"""
    separator = "=" * 50
    print(f"\n{title} v{version}")
    print(separator)


def print_summary(stats: dict) -> None:
    """操作結果のサマリーを印刷"""
    print("\n" + "=" * 30)
    print("Results Summary")
    print("=" * 30)
    
    for key, value in stats.items():
        print(f"- {key}: {value}")
    
    print("=" * 30)


def confirm_action(message: str, default: bool = False) -> bool:
    """ユーザーに確認を求める"""
    default_text = "Y/n" if default else "y/N"
    response = input(f"{message} [{default_text}]: ").strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes', 'true', '1']


# エラーハンドリング
def handle_common_error(error: Exception, context: str) -> bool:
    """
    共通エラーハンドリング
    
    Args:
        error: 発生した例外
        context: エラー発生コンテキスト
        
    Returns:
        True: 処理継続可能, False: 処理停止が必要
    """
    error_type = type(error).__name__
    
    # 処理継続可能なエラー
    recoverable_errors = [
        FileNotFoundError,
        PermissionError,
        ValidationError
    ]
    
    if type(error) in recoverable_errors:
        logging.warning(f"{context}: {error_type} - {str(error)}")
        return True
    else:
        logging.error(f"{context}: {error_type} - {str(error)}", exc_info=True)
        return False


# ファイル・ディレクトリ操作の追加関数
def is_markdown_file(filename: str) -> bool:
    """ファイルがMarkdownファイルかを確認"""
    return Path(filename).suffix.lower() in ['.md', '.markdown']


def validate_directory_name(name: str) -> bool:
    """ディレクトリ名がファイルシステムに適しているかを検証"""
    if not name:
        return False
    
    # 無効な文字をチェック
    invalid_chars = r'[<>:"/\\|?*]'
    if re.search(invalid_chars, name):
        return False
    
    # 長さをチェック
    if len(name) > 255:
        return False
    
    # 予約語をチェック（Windows）
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + \
                    [f'COM{i}' for i in range(1, 10)] + \
                    [f'LPT{i}' for i in range(1, 10)]
    if name.upper() in reserved_names:
        return False
    
    # ドットで始まるディレクトリ名は許可するが、ドットのみは拒否
    if name in ['.', '..']:
        return False
    
    return True


def cleanup_empty_directories(base_dir: str) -> int:
    """
    空ディレクトリを再帰的に削除
    
    Args:
        base_dir: 検索開始ディレクトリ
        
    Returns:
        削除されたディレクトリ数
    """
    removed_count = 0
    base_path = Path(base_dir)
    
    if not base_path.exists():
        return 0
    
    try:
        # ボトムアップでディレクトリをチェック
        for current_dir in sorted(base_path.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            if current_dir.is_dir():
                try:
                    # ディレクトリが空かチェック
                    if not any(current_dir.iterdir()):
                        current_dir.rmdir()
                        logging.info(f"Removed empty directory: {current_dir}")
                        removed_count += 1
                except OSError:
                    # 削除できない場合はスキップ
                    continue
    except Exception as e:
        logging.error(f"Error during directory cleanup: {e}")
    
    return removed_count


# YAMLヘッダー操作関数
def read_yaml_header(file_path: str) -> Tuple[dict, str]:
    """
    MarkdownファイルからYAMLヘッダーと本文を分離して読み込み
    
    Args:
        file_path: Markdownファイルのパス
        
    Returns:
        (YAMLヘッダー辞書, 本文内容)
    """
    import yaml
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # YAMLヘッダーの検出
        if not lines or lines[0].strip() != '---':
            return {}, content
        
        # YAMLヘッダーの終端を検索
        yaml_end = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                yaml_end = i
                break
        
        if yaml_end == -1:
            return {}, content
        
        # YAMLヘッダーの解析
        yaml_content = '\n'.join(lines[1:yaml_end])
        yaml_header = yaml.safe_load(yaml_content) if yaml_content.strip() else {}
        
        # 本文内容
        body_content = '\n'.join(lines[yaml_end + 1:])
        
        return yaml_header or {}, body_content
        
    except Exception as e:
        logging.error(f"Failed to read YAML header from {file_path}: {e}")
        return {}, ""


def update_yaml_header(file_path: str, yaml_header: dict, body_content: str) -> None:
    """
    MarkdownファイルのYAMLヘッダーを更新
    
    Args:
        file_path: Markdownファイルのパス
        yaml_header: 新しいYAMLヘッダー辞書
        body_content: 本文内容
    """
    import yaml
    
    try:
        # YAMLヘッダーをダンプ
        yaml_str = yaml.dump(yaml_header, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        # ファイル内容を構築
        if yaml_header:
            file_content = f"---\n{yaml_str}---\n{body_content}"
        else:
            file_content = body_content
        
        # ファイルに書き込み
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
            
        logging.debug(f"Updated YAML header in {file_path}")
        
    except Exception as e:
        logging.error(f"Failed to update YAML header in {file_path}: {e}")
        raise FileOperationError(f"Failed to update YAML header: {e}") 