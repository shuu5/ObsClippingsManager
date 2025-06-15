#!/usr/bin/env python3
"""
ObsClippingsManager File System Utilities

ファイルシステム操作ユーティリティ群
- ファイル操作（コピー、移動、アトミック書き込み）
- ディレクトリ管理
- パス正規化・検証
- ファイル検索・フィルタリング
- バックアップ・リストア機能
"""

import os
import shutil
import tempfile
import fnmatch
from pathlib import Path
from typing import List, Optional, Union, Iterator
import datetime
import hashlib

from .exceptions import FileSystemError, ObsClippingsManagerError
from .config_manager import ConfigManager


class FileUtils:
    """
    ファイル操作ユーティリティクラス
    
    安全なファイル操作（コピー、移動、書き込み）と
    ディレクトリ管理機能を提供。
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        FileUtilsの初期化
        
        Args:
            config_manager (ConfigManager, optional): 設定管理インスタンス
        """
        self.config_manager = config_manager
        
    def safe_copy(self, source: Union[str, Path], destination: Union[str, Path], 
                  overwrite: bool = True) -> bool:
        """
        安全なファイルコピー
        
        Args:
            source (Union[str, Path]): コピー元ファイルパス
            destination (Union[str, Path]): コピー先ファイルパス
            overwrite (bool): 既存ファイルを上書きするか
            
        Returns:
            bool: コピー成功時True
            
        Raises:
            FileSystemError: ファイル操作エラー
        """
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            # ソースファイルの存在確認
            if not source_path.exists():
                raise FileSystemError(
                    f"Source file not found: {source_path}",
                    error_code="SOURCE_NOT_FOUND",
                    context={"source": str(source_path)}
                )
            
            # 既存ファイルの処理
            if dest_path.exists() and not overwrite:
                return False
            
            # 親ディレクトリの作成
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイルコピー実行
            shutil.copy2(source_path, dest_path)
            
            return True
            
        except Exception as e:
            if isinstance(e, FileSystemError):
                raise
            raise FileSystemError(
                f"Failed to copy file: {str(e)}",
                error_code="COPY_FAILED",
                context={"source": str(source), "destination": str(destination)},
                cause=e
            )
    
    def safe_move(self, source: Union[str, Path], destination: Union[str, Path]) -> bool:
        """
        安全なファイル移動
        
        Args:
            source (Union[str, Path]): 移動元ファイルパス
            destination (Union[str, Path]): 移動先ファイルパス
            
        Returns:
            bool: 移動成功時True
            
        Raises:
            FileSystemError: ファイル操作エラー
        """
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            # ソースファイルの存在確認
            if not source_path.exists():
                raise FileSystemError(
                    f"Source file not found: {source_path}",
                    error_code="SOURCE_NOT_FOUND",
                    context={"source": str(source_path)}
                )
            
            # 親ディレクトリの作成
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイル移動実行
            shutil.move(str(source_path), str(dest_path))
            
            return True
            
        except Exception as e:
            if isinstance(e, FileSystemError):
                raise
            raise FileSystemError(
                f"Failed to move file: {str(e)}",
                error_code="MOVE_FAILED",
                context={"source": str(source), "destination": str(destination)},
                cause=e
            )
    
    def atomic_write(self, file_path: Union[str, Path], content: str, 
                     encoding: str = 'utf-8') -> bool:
        """
        アトミックファイル書き込み
        
        一時ファイルに書き込み後、原子的にリネームして安全な書き込みを実現。
        
        Args:
            file_path (Union[str, Path]): 書き込み先ファイルパス
            content (str): 書き込み内容
            encoding (str): 文字エンコーディング
            
        Returns:
            bool: 書き込み成功時True
            
        Raises:
            FileSystemError: ファイル操作エラー
        """
        try:
            target_path = Path(file_path)
            
            # 親ディレクトリの作成
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 一時ファイルを同じディレクトリに作成
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding=encoding,
                dir=target_path.parent,
                delete=False,
                suffix='.tmp'
            ) as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())  # ディスクに確実に書き込み
                temp_path = tmp_file.name
            
            # 原子的リネーム
            Path(temp_path).replace(target_path)
            
            return True
            
        except Exception as e:
            # 一時ファイルのクリーンアップ
            try:
                if 'temp_path' in locals():
                    Path(temp_path).unlink(missing_ok=True)
            except:
                pass
                
            raise FileSystemError(
                f"Failed to write file atomically: {str(e)}",
                error_code="ATOMIC_WRITE_FAILED",
                context={"file_path": str(file_path)},
                cause=e
            )
    
    def ensure_directory(self, directory: Union[str, Path]) -> bool:
        """
        ディレクトリの存在確保
        
        Args:
            directory (Union[str, Path]): 作成するディレクトリパス
            
        Returns:
            bool: 成功時True
            
        Raises:
            FileSystemError: ディレクトリ作成エラー
        """
        try:
            dir_path = Path(directory)
            dir_path.mkdir(parents=True, exist_ok=True)
            return True
            
        except Exception as e:
            raise FileSystemError(
                f"Failed to create directory: {str(e)}",
                error_code="DIRECTORY_CREATION_FAILED",
                context={"directory": str(directory)},
                cause=e
            )
    
    def safe_remove_directory(self, directory: Union[str, Path]) -> bool:
        """
        安全なディレクトリ削除
        
        Args:
            directory (Union[str, Path]): 削除するディレクトリパス
            
        Returns:
            bool: 削除成功時True
            
        Raises:
            FileSystemError: ディレクトリ削除エラー
        """
        try:
            dir_path = Path(directory)
            
            if not dir_path.exists():
                return True  # 既に存在しない場合は成功とする
            
            if not dir_path.is_dir():
                raise FileSystemError(
                    f"Path is not a directory: {dir_path}",
                    error_code="NOT_A_DIRECTORY",
                    context={"path": str(dir_path)}
                )
            
            shutil.rmtree(dir_path)
            return True
            
        except Exception as e:
            if isinstance(e, FileSystemError):
                raise
            raise FileSystemError(
                f"Failed to remove directory: {str(e)}",
                error_code="DIRECTORY_REMOVAL_FAILED",
                context={"directory": str(directory)},
                cause=e
            )
    
    def get_directory_size(self, directory: Union[str, Path]) -> int:
        """
        ディレクトリサイズ計算
        
        Args:
            directory (Union[str, Path]): サイズを計算するディレクトリパス
            
        Returns:
            int: ディレクトリサイズ（バイト）
            
        Raises:
            FileSystemError: ディレクトリアクセスエラー
        """
        try:
            dir_path = Path(directory)
            total_size = 0
            
            for dirpath, dirnames, filenames in os.walk(dir_path):
                for filename in filenames:
                    file_path = Path(dirpath) / filename
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, IOError):
                        # アクセスできないファイルは無視
                        continue
            
            return total_size
            
        except Exception as e:
            raise FileSystemError(
                f"Failed to calculate directory size: {str(e)}",
                error_code="SIZE_CALCULATION_FAILED",
                context={"directory": str(directory)},
                cause=e
            )


class PathUtils:
    """
    パス管理ユーティリティクラス
    
    パスの正規化、検証、相対パス計算、ObsClippings専用パス処理などを提供。
    """
    
    @staticmethod
    def is_valid_path(path: str) -> bool:
        """
        パスの有効性検証
        
        Args:
            path (str): 検証するパス
            
        Returns:
            bool: 有効な場合True
        """
        if not path or path.strip() == "":
            return False
        
        # ヌル文字チェック
        if '\x00' in path:
            return False
        
        try:
            # Pathオブジェクトとして解釈可能かチェック
            Path(path)
            return True
        except (ValueError, OSError):
            return False
    
    @staticmethod
    def normalize_path(path: Union[str, Path]) -> str:
        """
        パス正規化
        
        Args:
            path (Union[str, Path]): 正規化するパス
            
        Returns:
            str: 正規化されたパス
        """
        try:
            normalized = Path(path).resolve()
            return str(normalized)
        except Exception:
            # 解決できない場合は文字列としての正規化のみ
            return str(Path(path))
    
    @staticmethod
    def get_relative_path(base: Union[str, Path], target: Union[str, Path]) -> str:
        """
        相対パス計算
        
        Args:
            base (Union[str, Path]): 基準パス
            target (Union[str, Path]): 対象パス
            
        Returns:
            str: 相対パス
        """
        try:
            base_path = Path(base).resolve()
            target_path = Path(target).resolve()
            return str(target_path.relative_to(base_path))
        except ValueError:
            # 相対パスが計算できない場合は絶対パスを返す
            return str(Path(target).resolve())
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        ファイル名のサニタイズ
        
        ファイルシステムで無効な文字を安全な文字に置換する。
        
        Args:
            filename (str): サニタイズするファイル名
            
        Returns:
            str: サニタイズされたファイル名
        """
        # OSで無効な文字のマッピング
        invalid_chars = {
            '<': '＜',
            '>': '＞',
            ':': '：',
            '"': '＂',
            '/': '／',
            '\\': '＼',
            '|': '｜',
            '?': '？',
            '*': '＊'
        }
        
        sanitized = filename
        for invalid, replacement in invalid_chars.items():
            sanitized = sanitized.replace(invalid, replacement)
        
        # 先頭・末尾の空白文字除去
        sanitized = sanitized.strip()
        
        # 空文字列の場合はデフォルト名を設定
        if not sanitized:
            sanitized = "untitled"
        
        return sanitized
    
    @staticmethod
    def is_obsidian_vault_path(path: Union[str, Path]) -> bool:
        """
        Obsidianボルトパスかどうかの判定
        
        Args:
            path (Union[str, Path]): 検証するパス
            
        Returns:
            bool: Obsidianボルトの場合True
        """
        path_obj = Path(path)
        
        # .obsidianディレクトリの存在確認
        obsidian_dir = path_obj / ".obsidian"
        return obsidian_dir.exists() and obsidian_dir.is_dir()
    
    @staticmethod
    def get_citation_key_from_filename(filename: str) -> Optional[str]:
        """
        ファイル名からcitation_keyを抽出
        
        Args:
            filename (str): ファイル名
            
        Returns:
            Optional[str]: 抽出されたcitation_key（見つからない場合None）
        """
        import re
        
        # citation_keyパターン（一般的な学術引用キー形式）
        patterns = [
            r'^([a-zA-Z]+\d{4}[a-zA-Z]?)(?:_.*)?\.md$',  # Author2024a_title.md
            r'^([a-zA-Z]+[A-Z][a-zA-Z]*\d{4}[a-zA-Z]?)(?:_.*)?\.md$',  # AuthorName2024a_title.md
            r'^(\w+_\d{4})(?:_.*)?\.md$',  # author_2024_title.md
        ]
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def generate_safe_directory_name(citation_key: str) -> str:
        """
        citation_keyから安全なディレクトリ名を生成
        
        Args:
            citation_key (str): citation_key
            
        Returns:
            str: 安全なディレクトリ名
        """
        # 基本的なサニタイズ
        safe_name = PathUtils.sanitize_filename(citation_key)
        
        # ディレクトリ名として不適切な文字をさらに置換
        # Note: citation_keyの「.」は正しいのでそのまま保持
        safe_name = safe_name.replace(' ', '_')
        
        # 長すぎる場合は切り詰め（多くのファイルシステムで255文字制限）
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        
        return safe_name
    
    @staticmethod
    def build_clippings_file_path(base_dir: Union[str, Path], 
                                 citation_key: str, 
                                 title: Optional[str] = None) -> Path:
        """
        クリッピングファイルパスの構築
        
        Args:
            base_dir (Union[str, Path]): ベースディレクトリ
            citation_key (str): citation_key
            title (Optional[str]): ファイルタイトル
            
        Returns:
            Path: 構築されたファイルパス
        """
        base_path = Path(base_dir)
        safe_citation_key = PathUtils.generate_safe_directory_name(citation_key)
        
        # ディレクトリ作成
        target_dir = base_path / safe_citation_key
        
        # ファイル名決定
        if title:
            safe_title = PathUtils.sanitize_filename(title)
            filename = f"{citation_key}_{safe_title}.md"
        else:
            filename = f"{citation_key}.md"
        
        return target_dir / filename
    
    @staticmethod
    def find_markdown_files_with_yaml_headers(directory: Union[str, Path]) -> List[Path]:
        """
        YAMLヘッダーを持つMarkdownファイルを検索
        
        Args:
            directory (Union[str, Path]): 検索対象ディレクトリ
            
        Returns:
            List[Path]: YAMLヘッダーを持つMarkdownファイルのリスト
        """
        dir_path = Path(directory)
        markdown_files = []
        
        for md_file in dir_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                # YAMLヘッダーの存在確認（---で始まり---で終わる）
                if content.startswith('---\n') and '\n---\n' in content:
                    markdown_files.append(md_file)
            except (UnicodeDecodeError, OSError):
                # 読み込めないファイルはスキップ
                continue
        
        return markdown_files
    
    @staticmethod
    def get_file_extension_stats(directory: Union[str, Path]) -> dict:
        """
        ディレクトリ内のファイル拡張子統計を取得
        
        Args:
            directory (Union[str, Path]): 分析対象ディレクトリ
            
        Returns:
            dict: 拡張子ごとのファイル数統計
        """
        dir_path = Path(directory)
        extension_stats = {}
        
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                extension = file_path.suffix.lower()
                if not extension:
                    extension = "(no extension)"
                
                extension_stats[extension] = extension_stats.get(extension, 0) + 1
        
        return extension_stats


class StringUtils:
    """
    文字列処理ユーティリティクラス
    
    文字列の正規化、変換、バリデーション機能を提供。
    ObsClippingsManagerに特化した文字列処理を含む。
    """
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        テキストのクリーニング
        
        Args:
            text (str): クリーニングするテキスト
            
        Returns:
            str: クリーニングされたテキスト
        """
        if not text:
            return ""
        
        # 連続する空白文字を単一スペースに置換
        import re
        cleaned = re.sub(r'\s+', ' ', text)
        
        # 先頭・末尾の空白を除去
        cleaned = cleaned.strip()
        
        return cleaned
    
    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """
        テキストの切り詰め
        
        Args:
            text (str): 切り詰めるテキスト
            max_length (int): 最大長
            suffix (str): 切り詰め時の接尾辞
            
        Returns:
            str: 切り詰められたテキスト
        """
        if not text or len(text) <= max_length:
            return text
        
        truncated_length = max_length - len(suffix)
        if truncated_length <= 0:
            return suffix[:max_length]
        
        return text[:truncated_length] + suffix
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        空白文字の正規化
        
        Args:
            text (str): 正規化するテキスト
            
        Returns:
            str: 正規化されたテキスト
        """
        if not text:
            return ""
        
        import re
        # 各種空白文字を通常のスペースに統一
        normalized = re.sub(r'[\t\n\r\f\v\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]', ' ', text)
        # 連続する空白を単一スペースに
        normalized = re.sub(r' +', ' ', normalized)
        # 先頭・末尾の空白除去
        normalized = normalized.strip()
        
        return normalized
    
    @staticmethod
    def extract_markdown_title(content: str) -> Optional[str]:
        """
        Markdownコンテンツからタイトルを抽出
        
        Args:
            content (str): Markdownコンテンツ
            
        Returns:
            Optional[str]: 抽出されたタイトル（見つからない場合None）
        """
        if not content:
            return None
        
        import re
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            # H1ヘッダー（# タイトル）
            if line.startswith('# '):
                title = line[2:].strip()
                if title:
                    return title
        
        return None
    
    @staticmethod
    def parse_yaml_header(content: str) -> Optional[dict]:
        """
        Markdownコンテンツからヤマルヘッダーを解析
        
        Args:
            content (str): Markdownコンテンツ
            
        Returns:
            Optional[dict]: 解析されたYAMLヘッダー辞書（失敗時None）
        """
        if not content or not content.startswith('---\n'):
            return None
        
        try:
            import yaml
            
            # YAMLヘッダー部分を抽出
            end_index = content.find('\n---\n', 4)
            if end_index == -1:
                return None
            
            yaml_content = content[4:end_index]
            parsed = yaml.safe_load(yaml_content)
            
            return parsed if isinstance(parsed, dict) else None
            
        except Exception:
            return None
    
    @staticmethod
    def format_citation_key(author: str, year: str, suffix: str = "") -> str:
        """
        citation_keyの標準フォーマット生成
        
        Args:
            author (str): 著者名
            year (str): 年
            suffix (str): 接尾辞（a, b, c等）
            
        Returns:
            str: フォーマットされたcitation_key
        """
        # 著者名のクリーニング
        clean_author = StringUtils.clean_text(author)
        clean_author = ''.join(c for c in clean_author if c.isalnum())
        
        # 年の検証
        clean_year = ''.join(c for c in year if c.isdigit())
        if len(clean_year) != 4:
            clean_year = "0000"
        
        # 接尾辞のクリーニング
        clean_suffix = ''.join(c for c in suffix if c.isalnum())
        
        citation_key = f"{clean_author}{clean_year}"
        if clean_suffix:
            citation_key += clean_suffix
        
        return citation_key
    
    @staticmethod
    def extract_doi_from_text(text: str) -> Optional[str]:
        """
        テキストからDOIを抽出
        
        Args:
            text (str): 検索対象テキスト
            
        Returns:
            Optional[str]: 抽出されたDOI（見つからない場合None）
        """
        if not text:
            return None
        
        import re
        
        # DOIパターン（10.で始まる標準形式）
        doi_pattern = r'10\.\d{4,}\/[^\s<>"{}|\\^`\[\]]*'
        match = re.search(doi_pattern, text)
        
        if match:
            return match.group(0)
        
        return None
    
    @staticmethod
    def validate_citation_key(citation_key: str) -> bool:
        """
        citation_keyの妥当性検証
        
        Args:
            citation_key (str): 検証するcitation_key
            
        Returns:
            bool: 妥当な場合True
        """
        if not citation_key:
            return False
        
        # 長さチェック（一般的な学術引用キーは50文字以下）
        if len(citation_key) > 50:
            return False
        
        import re
        
        # 基本的なパターンチェック
        patterns = [
            r'^[a-zA-Z]{1,20}\d{4}[a-zA-Z]?$',  # Author2024a (著者名1-20文字)
            r'^[a-zA-Z]{1,15}[A-Z][a-zA-Z]{1,15}\d{4}[a-zA-Z]?$',  # AuthorName2024a
            r'^\w{1,20}_\d{4}[a-zA-Z]?$',  # author_2024a
        ]
        
        for pattern in patterns:
            if re.match(pattern, citation_key):
                return True
        
        return False
    
    @staticmethod
    def generate_unique_filename(base_name: str, extension: str, 
                                existing_files: List[str]) -> str:
        """
        重複しないファイル名を生成
        
        Args:
            base_name (str): ベースとなるファイル名
            extension (str): ファイル拡張子
            existing_files (List[str]): 既存ファイル名のリスト
            
        Returns:
            str: 重複しないファイル名
        """
        if not extension.startswith('.'):
            extension = '.' + extension
        
        candidate = f"{base_name}{extension}"
        
        if candidate not in existing_files:
            return candidate
        
        # 連番を付けて重複回避
        counter = 1
        while True:
            candidate = f"{base_name}_{counter}{extension}"
            if candidate not in existing_files:
                return candidate
            counter += 1
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Markdown特殊文字のエスケープ
        
        Args:
            text (str): エスケープするテキスト
            
        Returns:
            str: エスケープされたテキスト
        """
        if not text:
            return ""
        
        # Markdownで特殊な意味を持つ文字をエスケープ
        special_chars = ['\\', '`', '*', '_', '{', '}', '[', ']', 
                        '(', ')', '#', '+', '-', '.', '!', '|']
        
        escaped = text
        for char in special_chars:
            escaped = escaped.replace(char, '\\' + char)
        
        return escaped


class FileSearch:
    """
    ファイル検索・フィルタリングクラス
    
    拡張子、パターン、再帰的検索機能を提供。
    """
    
    def find_by_extension(self, directory: Union[str, Path], 
                         extension: str, recursive: bool = True) -> List[Path]:
        """
        拡張子によるファイル検索
        
        Args:
            directory (Union[str, Path]): 検索対象ディレクトリ
            extension (str): 検索する拡張子（例: ".txt"）
            recursive (bool): 再帰的検索するか
            
        Returns:
            List[Path]: 見つかったファイルのリスト
        """
        dir_path = Path(directory)
        found_files = []
        
        if not extension.startswith('.'):
            extension = '.' + extension
        
        if recursive:
            pattern = f"**/*{extension}"
            found_files = list(dir_path.glob(pattern))
        else:
            pattern = f"*{extension}"
            found_files = list(dir_path.glob(pattern))
        
        return [f for f in found_files if f.is_file()]
    
    def find_by_pattern(self, directory: Union[str, Path], 
                       pattern: str, recursive: bool = True) -> List[Path]:
        """
        パターンによるファイル検索
        
        Args:
            directory (Union[str, Path]): 検索対象ディレクトリ
            pattern (str): 検索パターン（例: "*.txt"）
            recursive (bool): 再帰的検索するか
            
        Returns:
            List[Path]: 見つかったファイルのリスト
        """
        dir_path = Path(directory)
        found_files = []
        
        if recursive:
            search_pattern = f"**/{pattern}"
            found_files = list(dir_path.glob(search_pattern))
        else:
            found_files = list(dir_path.glob(pattern))
        
        return [f for f in found_files if f.is_file()]
    
    def find_files(self, directory: Union[str, Path], 
                   recursive: bool = True, 
                   include_patterns: Optional[List[str]] = None,
                   exclude_patterns: Optional[List[str]] = None) -> List[Path]:
        """
        汎用ファイル検索
        
        Args:
            directory (Union[str, Path]): 検索対象ディレクトリ
            recursive (bool): 再帰的検索するか
            include_patterns (List[str], optional): 含めるパターンのリスト
            exclude_patterns (List[str], optional): 除外するパターンのリスト
            
        Returns:
            List[Path]: 見つかったファイルのリスト
        """
        dir_path = Path(directory)
        
        if recursive:
            all_files = [f for f in dir_path.rglob("*") if f.is_file()]
        else:
            all_files = [f for f in dir_path.iterdir() if f.is_file()]
        
        # インクルードパターンフィルタリング
        if include_patterns:
            filtered_files = []
            for file_path in all_files:
                if any(fnmatch.fnmatch(file_path.name, pattern) for pattern in include_patterns):
                    filtered_files.append(file_path)
            all_files = filtered_files
        
        # エクスクルードパターンフィルタリング
        if exclude_patterns:
            filtered_files = []
            for file_path in all_files:
                if not any(fnmatch.fnmatch(file_path.name, pattern) for pattern in exclude_patterns):
                    filtered_files.append(file_path)
            all_files = filtered_files
        
        return all_files


class BackupManager:
    """
    バックアップ・リストア管理クラス
    
    ファイルのバックアップ作成、リストア、クリーンアップ機能を提供。
    """
    
    def __init__(self, backup_dir: Optional[Union[str, Path]] = None):
        """
        BackupManagerの初期化
        
        Args:
            backup_dir (Union[str, Path], optional): バックアップディレクトリ
        """
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = Path(tempfile.gettempdir()) / "ObsClippingsManager_Backups"
        
        # バックアップディレクトリの作成
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, file_path: Union[str, Path]) -> str:
        """
        ファイルバックアップ作成
        
        Args:
            file_path (Union[str, Path]): バックアップ対象ファイル
            
        Returns:
            str: バックアップファイルパス
            
        Raises:
            FileSystemError: バックアップ作成エラー
        """
        try:
            source_path = Path(file_path)
            
            if not source_path.exists():
                raise FileSystemError(
                    f"Backup source file not found: {source_path}",
                    error_code="BACKUP_SOURCE_NOT_FOUND",
                    context={"source": str(source_path)}
                )
            
            # バックアップファイル名生成（タイムスタンプ付き）
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source_path.stem}_{timestamp}{source_path.suffix}"
            backup_path = self.backup_dir / backup_name
            
            # バックアップファイルコピー
            shutil.copy2(source_path, backup_path)
            
            return str(backup_path)
            
        except Exception as e:
            if isinstance(e, FileSystemError):
                raise
            raise FileSystemError(
                f"Failed to create backup: {str(e)}",
                error_code="BACKUP_CREATION_FAILED",
                context={"file_path": str(file_path)},
                cause=e
            )
    
    def restore_backup(self, backup_path: Union[str, Path], 
                      target_path: Union[str, Path]) -> bool:
        """
        バックアップからリストア
        
        Args:
            backup_path (Union[str, Path]): バックアップファイルパス
            target_path (Union[str, Path]): リストア先ファイルパス
            
        Returns:
            bool: リストア成功時True
            
        Raises:
            FileSystemError: リストアエラー
        """
        try:
            backup_file = Path(backup_path)
            target_file = Path(target_path)
            
            if not backup_file.exists():
                raise FileSystemError(
                    f"Backup file not found: {backup_file}",
                    error_code="BACKUP_NOT_FOUND",
                    context={"backup_path": str(backup_file)}
                )
            
            # 親ディレクトリの作成
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # リストア実行
            shutil.copy2(backup_file, target_file)
            
            return True
            
        except Exception as e:
            if isinstance(e, FileSystemError):
                raise
            raise FileSystemError(
                f"Failed to restore backup: {str(e)}",
                error_code="RESTORE_FAILED",
                context={
                    "backup_path": str(backup_path),
                    "target_path": str(target_path)
                },
                cause=e
            )
    
    def cleanup_backup(self, backup_path: Union[str, Path]) -> bool:
        """
        バックアップファイル削除
        
        Args:
            backup_path (Union[str, Path]): 削除するバックアップファイルパス
            
        Returns:
            bool: 削除成功時True
        """
        try:
            backup_file = Path(backup_path)
            
            if backup_file.exists():
                backup_file.unlink()
            
            return True
            
        except Exception as e:
            raise FileSystemError(
                f"Failed to cleanup backup: {str(e)}",
                error_code="BACKUP_CLEANUP_FAILED",
                context={"backup_path": str(backup_path)},
                cause=e
            )
    
    def list_backups(self) -> List[Path]:
        """
        バックアップファイル一覧取得
        
        Returns:
            List[Path]: バックアップファイルのリスト
        """
        if not self.backup_dir.exists():
            return []
        
        return [f for f in self.backup_dir.iterdir() if f.is_file()] 