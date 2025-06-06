"""
Markdownファイル管理

Markdownファイルの検索、移動、リネーム操作を管理します。
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from ..shared.utils import (
    safe_file_operation, 
    is_markdown_file,
    escape_filename,
    backup_file,
    validate_directory_name
)
from .exceptions import DirectoryOperationError


class MarkdownManager:
    """Markdownファイル管理クラス"""
    
    def __init__(self, clippings_dir: str, backup_dir: str = "./backups/"):
        """
        Args:
            clippings_dir: Clippingsディレクトリパス
            backup_dir: バックアップディレクトリパス
        """
        self.clippings_dir = Path(clippings_dir)
        self.backup_dir = Path(backup_dir)
        self.logger = logging.getLogger("ObsClippingsManager.RenameMkDir.MarkdownManager")
        
        # ディレクトリが存在しない場合は作成
        self.clippings_dir.mkdir(parents=True, exist_ok=True)
        if backup_dir:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def get_markdown_files(self, root_only: bool = True) -> List[str]:
        """
        Markdownファイル一覧を取得
        
        Args:
            root_only: ルートレベルのみ検索するか
            
        Returns:
            Markdownファイルパスのリスト
        """
        markdown_files = []
        
        try:
            if root_only:
                # ルートレベルのファイルのみを対象
                for file_path in self.clippings_dir.iterdir():
                    if file_path.is_file() and is_markdown_file(str(file_path)):
                        markdown_files.append(str(file_path))
            else:
                # 再帰的にすべてのMarkdownファイルを検索
                for file_path in self.clippings_dir.rglob("*.md"):
                    if file_path.is_file():
                        markdown_files.append(str(file_path))
            
            self.logger.info(f"Found {len(markdown_files)} Markdown files")
            return sorted(markdown_files)
            
        except Exception as e:
            self.logger.error(f"Error searching Markdown files: {e}")
            return []
    
    def is_already_organized(self, file_path: str) -> bool:
        """
        ファイルが既に整理済みかチェック
        
        Args:
            file_path: チェック対象ファイルパス
            
        Returns:
            True: 既に整理済み, False: 未整理
        """
        file_path_obj = Path(file_path)
        
        # ファイルがサブディレクトリ内にある場合は既に整理済み
        try:
            # 相対パスを取得
            relative_path = file_path_obj.relative_to(self.clippings_dir)
            # パスに区切り文字が含まれていればサブディレクトリ内
            return len(relative_path.parts) > 1
        except ValueError:
            # clippings_dir外のファイル
            return False
    
    def normalize_filename(self, filename: str, max_length: int = 255) -> str:
        """
        ファイル名を正規化
        - 無効文字の除去
        - 長さ制限
        - 拡張子の確保
        
        Args:
            filename: 正規化対象のファイル名
            max_length: 最大ファイル名長
            
        Returns:
            正規化されたファイル名
        """
        return escape_filename(filename, max_length)
    
    def move_file_to_citation_dir(self, 
                                 old_path: str, 
                                 citation_key: str, 
                                 backup: bool = True) -> bool:
        """
        ファイルをcitation_keyディレクトリに移動・リネーム
        
        Args:
            old_path: 元のファイルパス
            citation_key: 移動先のcitation_key
            backup: バックアップ作成有無
            
        Returns:
            True: 成功, False: 失敗
        """
        source_path = Path(old_path)
        
        if not source_path.exists():
            self.logger.error(f"Source file not found: {old_path}")
            return False
        
        # citation_keyの妥当性チェック
        if not validate_directory_name(citation_key):
            self.logger.error(f"Invalid citation key for directory name: {citation_key}")
            return False
        
        # 移動先パスを決定
        destination_dir = self.clippings_dir / citation_key
        destination_path = destination_dir / f"{citation_key}.md"
        
        try:
            # ディレクトリ作成
            destination_dir.mkdir(parents=True, exist_ok=True)
            
            # バックアップ作成
            if backup:
                backup_path = self.create_backup(old_path)
                self.logger.info(f"Backup created: {backup_path}")
            
            # ファイルを移動・リネーム
            shutil.move(str(source_path), str(destination_path))
            
            self.logger.info(f"File moved: {source_path} -> {destination_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to move file {old_path} -> {citation_key}: {e}")
            return False
    
    def create_backup(self, file_path: str) -> str:
        """
        ファイルのバックアップを作成
        
        Args:
            file_path: バックアップ対象ファイル
            
        Returns:
            バックアップファイルパス
        """
        return backup_file(file_path, str(self.backup_dir))
    
    def batch_move_files(self, 
                        file_moves: List[Tuple[str, str]], 
                        backup: bool = True, 
                        dry_run: bool = False) -> Dict[str, int]:
        """
        複数ファイルの一括移動
        
        Args:
            file_moves: [(元ファイルパス, citation_key), ...] のリスト
            backup: バックアップ作成有無
            dry_run: 実際の操作を行わない
            
        Returns:
            処理統計
        """
        stats = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "directories_created": 0
        }
        
        created_dirs = set()
        
        for file_path, citation_key in file_moves:
            if dry_run:
                print(f"[DRY RUN] {Path(file_path).name} -> {citation_key}/{citation_key}.md")
                stats["success"] += 1
                continue
            
            # 既に整理済みのファイルはスキップ
            if self.is_already_organized(file_path):
                self.logger.info(f"Skipped (already organized): {file_path}")
                stats["skipped"] += 1
                continue
            
            # ディレクトリ作成をトラック
            if citation_key not in created_dirs:
                created_dirs.add(citation_key)
                stats["directories_created"] += 1
            
            # ファイル移動
            if self.move_file_to_citation_dir(file_path, citation_key, backup):
                stats["success"] += 1
            else:
                stats["failed"] += 1
        
        return stats
    
    def get_file_info(self, file_path: str) -> Dict[str, any]:
        """
        ファイル情報を取得
        
        Args:
            file_path: 情報取得対象のファイルパス
            
        Returns:
            ファイル情報の辞書
        """
        file_path_obj = Path(file_path)
        
        try:
            stat = file_path_obj.stat()
            return {
                "name": file_path_obj.name,
                "size_bytes": stat.st_size,
                "size_mb": stat.st_size / (1024 * 1024),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "is_organized": self.is_already_organized(file_path),
                "parent_directory": file_path_obj.parent.name
            }
        except Exception as e:
            self.logger.error(f"Error getting file info for {file_path}: {e}")
            return {
                "name": file_path_obj.name,
                "error": str(e)
            }
    
    def get_directory_structure(self) -> Dict[str, List[str]]:
        """
        現在のディレクトリ構造を取得
        
        Returns:
            {"root_files": [...], "organized_dirs": {...}}
        """
        structure = {"root_files": [], "organized_dirs": {}}
        
        try:
            for item in self.clippings_dir.iterdir():
                if item.is_file() and is_markdown_file(str(item)):
                    structure["root_files"].append(item.name)
                elif item.is_dir():
                    # ディレクトリ内のファイル一覧
                    dir_files = []
                    for md_file in item.glob("*.md"):
                        if md_file.is_file():
                            dir_files.append(md_file.name)
                    if dir_files:  # ファイルがある場合のみ追加
                        structure["organized_dirs"][item.name] = dir_files
        except Exception as e:
            self.logger.error(f"Error getting directory structure: {e}")
        
        return structure


# 便利関数
def get_markdown_files(directory: str, root_only: bool = True) -> List[str]:
    """
    Markdownファイル一覧を取得
    
    Args:
        directory: 検索対象ディレクトリ
        root_only: ルートレベルのみ検索するか
        
    Returns:
        Markdownファイルパスのリスト
    """
    manager = MarkdownManager(directory)
    return manager.get_markdown_files(root_only)


def move_file_to_citation_dir(old_path: str, 
                            citation_key: str, 
                            clippings_dir: str,
                            backup: bool = True) -> bool:
    """
    ファイルをcitation_keyディレクトリに移動・リネーム
    
    Args:
        old_path: 元のファイルパス
        citation_key: 移動先のcitation_key
        clippings_dir: Clippingsディレクトリパス
        backup: バックアップ作成有無
        
    Returns:
        True: 成功, False: 失敗
    """
    manager = MarkdownManager(clippings_dir)
    return manager.move_file_to_citation_dir(old_path, citation_key, backup) 