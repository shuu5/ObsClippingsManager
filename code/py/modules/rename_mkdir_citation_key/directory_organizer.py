"""
ディレクトリ整理

Citation keyベースのディレクトリ作成と管理を行います。
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict

from ..shared.utils import (
    validate_directory_name,
    cleanup_empty_directories as util_cleanup_empty_dirs,
    create_directory_if_not_exists
)
from .exceptions import DirectoryOperationError


class DirectoryOrganizer:
    """Citation keyベースのディレクトリ整理クラス"""
    
    def __init__(self, base_dir: str):
        """
        Args:
            base_dir: ベースディレクトリパス（Clippingsディレクトリ）
        """
        self.base_dir = Path(base_dir)
        self.logger = logging.getLogger("ObsClippingsManager.RenameMkDir.DirectoryOrganizer")
        
        # ベースディレクトリが存在しない場合は作成
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def create_citation_directory(self, citation_key: str) -> bool:
        """
        Citation keyディレクトリを作成
        
        Args:
            citation_key: ディレクトリ名となるcitation_key
            
        Returns:
            True: 作成成功, False: 作成失敗
        """
        # citation_keyの妥当性チェック
        if not self.validate_citation_key(citation_key):
            self.logger.error(f"Invalid citation key: {citation_key}")
            return False
        
        try:
            citation_dir = self.base_dir / citation_key
            
            if citation_dir.exists():
                self.logger.info(f"Directory already exists: {citation_dir}")
                return True
            
            citation_dir.mkdir(parents=False, exist_ok=True)
            self.logger.info(f"Created directory: {citation_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create directory for {citation_key}: {e}")
            raise DirectoryOperationError(
                f"Failed to create directory: {e}",
                directory_path=str(self.base_dir / citation_key),
                operation="create"
            )
    
    def validate_citation_key(self, citation_key: str) -> bool:
        """
        Citation keyの妥当性をチェック
        - ファイルシステム制限
        - 特殊文字制限
        - 長さ制限
        
        Args:
            citation_key: チェック対象のcitation_key
            
        Returns:
            妥当性の真偽値
        """
        # 共通のディレクトリ名検証を使用
        if not validate_directory_name(citation_key):
            return False
        
        # 追加の制限（必要に応じて）
        # 例：citation_keyの形式チェック
        # 一般的な形式: authorYEAR や author:YEAR:keyword など
        
        return True
    
    def cleanup_empty_directories(self) -> int:
        """
        空ディレクトリを削除
        
        Returns:
            削除したディレクトリ数
        """
        return util_cleanup_empty_dirs(str(self.base_dir))
    
    def get_existing_citation_dirs(self) -> List[str]:
        """
        既存のcitation_keyディレクトリ一覧を取得
        
        Returns:
            Citation keyディレクトリ名のリスト
        """
        citation_dirs = []
        
        try:
            for item in self.base_dir.iterdir():
                if item.is_dir():
                    # 隠しディレクトリは除外
                    if not item.name.startswith('.'):
                        citation_dirs.append(item.name)
            
            self.logger.info(f"Found {len(citation_dirs)} citation directories")
            return sorted(citation_dirs)
            
        except Exception as e:
            self.logger.error(f"Error getting citation directories: {e}")
            return []
    
    def get_directory_stats(self) -> Dict[str, int]:
        """
        ディレクトリ統計を取得
        
        Returns:
            統計情報の辞書
        """
        stats = {
            "total_directories": 0,
            "empty_directories": 0,
            "single_file_directories": 0,
            "multi_file_directories": 0,
            "total_files": 0
        }
        
        try:
            for item in self.base_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    stats["total_directories"] += 1
                    
                    # ディレクトリ内のファイル数をカウント
                    file_count = sum(1 for f in item.iterdir() if f.is_file())
                    stats["total_files"] += file_count
                    
                    if file_count == 0:
                        stats["empty_directories"] += 1
                    elif file_count == 1:
                        stats["single_file_directories"] += 1
                    else:
                        stats["multi_file_directories"] += 1
                        
        except Exception as e:
            self.logger.error(f"Error getting directory statistics: {e}")
        
        return stats
    
    def check_directory_conflicts(self, citation_keys: List[str]) -> Dict[str, str]:
        """
        ディレクトリ作成の競合をチェック
        
        Args:
            citation_keys: チェック対象のcitation_keyリスト
            
        Returns:
            競合情報 {citation_key: "conflict_reason"}
        """
        conflicts = {}
        existing_dirs = set(self.get_existing_citation_dirs())
        
        for citation_key in citation_keys:
            if not self.validate_citation_key(citation_key):
                conflicts[citation_key] = "Invalid citation key format"
            elif citation_key in existing_dirs:
                # 既存ディレクトリは競合ではない（追加可能）
                pass
            elif citation_key.lower() in [d.lower() for d in existing_dirs]:
                conflicts[citation_key] = "Case-insensitive conflict with existing directory"
        
        return conflicts
    
    def prepare_directories_for_files(self, 
                                    file_citation_mapping: Dict[str, str]) -> Dict[str, bool]:
        """
        ファイル移動のためのディレクトリを準備
        
        Args:
            file_citation_mapping: {ファイルパス: citation_key} のマッピング
            
        Returns:
            {citation_key: 作成成功} の結果
        """
        results = {}
        unique_citations = set(file_citation_mapping.values())
        
        for citation_key in unique_citations:
            try:
                success = self.create_citation_directory(citation_key)
                results[citation_key] = success
            except DirectoryOperationError:
                results[citation_key] = False
        
        return results


# 便利関数
def create_citation_directory(citation_key: str, base_dir: str) -> bool:
    """
    Citation keyディレクトリを作成
    
    Args:
        citation_key: ディレクトリ名となるcitation_key
        base_dir: ベースディレクトリパス
        
    Returns:
        True: 作成成功, False: 作成失敗
    """
    organizer = DirectoryOrganizer(base_dir)
    return organizer.create_citation_directory(citation_key)


def cleanup_empty_directories(base_dir: str) -> int:
    """
    空ディレクトリを削除
    
    Args:
        base_dir: クリーンアップ対象ディレクトリ
        
    Returns:
        削除したディレクトリ数
    """
    organizer = DirectoryOrganizer(base_dir)
    return organizer.cleanup_empty_directories()


def get_existing_citation_dirs(base_dir: str) -> List[str]:
    """
    既存のcitation_keyディレクトリ一覧を取得
    
    Args:
        base_dir: ベースディレクトリパス
        
    Returns:
        Citation keyディレクトリ名のリスト
    """
    organizer = DirectoryOrganizer(base_dir)
    return organizer.get_existing_citation_dirs() 