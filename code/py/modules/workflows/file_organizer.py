#!/usr/bin/env python3
"""
FileOrganizer - ファイル整理機能

ワークフローのorganizeステップを担当するクラス。
- citation_keyディレクトリ作成
- ファイル移動・リネーム
- 既存ファイル衝突回避
- YAMLヘッダー更新（processing_status.organize: completed）
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

from ..shared.config_manager import ConfigManager
from ..shared.integrated_logger import IntegratedLogger
from ..shared.exceptions import FileSystemError, ProcessingError, YAMLError
from ..shared.file_utils import FileUtils, PathUtils, StringUtils, BackupManager
from ..status_management.yaml_header_processor import YAMLHeaderProcessor


class FileOrganizer:
    """
    ファイル整理クラス
    
    論文ファイルをcitation_keyベースのディレクトリ構造に整理。
    organize処理ステップの実装。
    """
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        FileOrganizerの初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ出力オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('FileOrganizer')
        
        # 依存関係の初期化
        self.file_utils = FileUtils(config_manager)
        self.path_utils = PathUtils()
        self.string_utils = StringUtils()
        self.backup_manager = BackupManager()
        self.yaml_processor = YAMLHeaderProcessor(config_manager, logger)
        
        # 設定取得
        config = config_manager.get_config()
        self.organize_settings = config.get('workflows', {}).get('organize', {})
        
        # デフォルト設定
        self.create_backup = self.organize_settings.get('create_backup', True)
        self.handle_duplicates = self.organize_settings.get('handle_duplicates', True)
        self.update_yaml_header = self.organize_settings.get('update_yaml_header', True)
        
        self.logger.info("FileOrganizer initialized")
    
    def organize_file(self, file_path: Union[str, Path], base_dir: Union[str, Path]) -> bool:
        """
        単一ファイルのorganize処理
        
        Args:
            file_path: 整理対象ファイルのパス
            base_dir: ベースディレクトリ（通常はClippingsディレクトリ）
            
        Returns:
            bool: 処理成功時True
            
        Raises:
            FileSystemError: ファイル操作エラー
            ProcessingError: 処理エラー
        """
        try:
            file_path = Path(file_path)
            base_dir = Path(base_dir)
            
            self.logger.info(f"Starting organize process for: {file_path}")
            
            # ファイル存在確認
            if not file_path.exists():
                raise FileSystemError(
                    f"Source file not found: {file_path}",
                    error_code="SOURCE_FILE_NOT_FOUND",
                    context={"file_path": str(file_path)}
                )
            
            # YAMLヘッダー読み込みとcitation_key抽出
            yaml_header, content = self.yaml_processor.parse_yaml_header(file_path)
            citation_key = yaml_header.get('citation_key')
            
            if not citation_key:
                # ファイル名からcitation_key推測を試行
                citation_key = self.path_utils.get_citation_key_from_filename(file_path.name)
                if not citation_key:
                    raise ProcessingError(
                        f"Cannot determine citation_key for file: {file_path}",
                        error_code="CITATION_KEY_NOT_FOUND",
                        context={"file_path": str(file_path)}
                    )
                
                # YAMLヘッダーにcitation_keyを追加
                yaml_header['citation_key'] = citation_key
                self.logger.info(f"Inferred citation_key: {citation_key}")
            
            # citation_keyディレクトリ作成
            target_dir = self.create_citation_directory(str(base_dir), citation_key)
            target_dir = Path(target_dir)
            
            # 移動先ファイルパス決定
            target_file_path = target_dir / f"{citation_key}.md"
            
            # 衝突処理
            if target_file_path.exists() and self.handle_duplicates:
                target_file_path = self._handle_file_collision(target_file_path, file_path)
            
            # バックアップ作成（必要に応じて）
            if self.create_backup and target_file_path.exists():
                backup_path = self.backup_manager.create_backup(str(target_file_path))
                self.logger.info(f"Backup created: {backup_path}")
            
            # YAMLヘッダー更新
            if self.update_yaml_header:
                yaml_header = self._update_organize_status(yaml_header)
            
            # ファイル移動と内容更新
            # アトミック書き込みで移動先に保存
            self.yaml_processor.write_yaml_header(target_file_path, yaml_header, content)
            
            # 元ファイル削除（移動が成功した場合）
            if target_file_path.exists() and file_path != target_file_path:
                file_path.unlink()
                self.logger.info(f"Moved file from {file_path} to {target_file_path}")
            
            self.logger.info(f"Organize process completed for: {citation_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to organize file {file_path}: {str(e)}")
            if isinstance(e, (FileSystemError, ProcessingError, YAMLError)):
                raise
            raise ProcessingError(
                f"Unexpected error during organize: {str(e)}",
                error_code="ORGANIZE_UNEXPECTED_ERROR",
                context={"file_path": str(file_path)},
                cause=e
            )
    
    def create_citation_directory(self, base_dir: Union[str, Path], citation_key: str) -> str:
        """
        citation_keyベースのディレクトリを作成
        
        Args:
            base_dir: ベースディレクトリパス
            citation_key: 論文の識別キー
            
        Returns:
            str: 作成されたディレクトリパス
            
        Raises:
            FileSystemError: ディレクトリ作成エラー
        """
        try:
            base_path = Path(base_dir)
            
            # 安全なディレクトリ名生成
            safe_citation_key = self.path_utils.generate_safe_directory_name(citation_key)
            target_dir = base_path / safe_citation_key
            
            # ディレクトリ作成
            self.file_utils.ensure_directory(target_dir)
            
            self.logger.debug(f"Created citation directory: {target_dir}")
            return str(target_dir)
            
        except Exception as e:
            raise FileSystemError(
                f"Failed to create citation directory: {str(e)}",
                error_code="CITATION_DIRECTORY_CREATION_FAILED",
                context={
                    "base_dir": str(base_dir),
                    "citation_key": citation_key
                },
                cause=e
            )
    
    def organize_multiple_files(self, file_paths: List[Union[str, Path]], 
                              base_dir: Union[str, Path]) -> Dict[str, bool]:
        """
        複数ファイルの一括organize処理
        
        Args:
            file_paths: 整理対象ファイルパスのリスト
            base_dir: ベースディレクトリ
            
        Returns:
            Dict[str, bool]: ファイルパス -> 処理結果の辞書
        """
        results = {}
        
        for file_path in file_paths:
            try:
                result = self.organize_file(file_path, base_dir)
                results[str(file_path)] = result
            except Exception as e:
                self.logger.error(f"Failed to organize {file_path}: {str(e)}")
                results[str(file_path)] = False
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(file_paths)
        
        self.logger.info(f"Batch organize completed: {success_count}/{total_count} files processed successfully")
        
        return results
    
    def _handle_file_collision(self, target_path: Path, source_path: Path) -> Path:
        """
        ファイル衝突時の処理
        
        Args:
            target_path: 移動先ファイルパス
            source_path: 移動元ファイルパス
            
        Returns:
            Path: 最終的な移動先パス
        """
        try:
            # タイムスタンプ付きファイル名生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = target_path.stem
            suffix = target_path.suffix
            
            # 衝突回避ファイル名生成
            collision_avoided_path = target_path.parent / f"{stem}_{timestamp}{suffix}"
            
            # 既存ファイルのバックアップ作成
            if self.create_backup:
                backup_path = self.backup_manager.create_backup(str(target_path))
                self.logger.info(f"Created backup for existing file: {backup_path}")
            
            self.logger.warning(f"File collision detected. Using alternative name: {collision_avoided_path}")
            
            return collision_avoided_path
            
        except Exception as e:
            self.logger.error(f"Failed to handle file collision: {str(e)}")
            # フォールバック: 元のパスを返す（上書きされる）
            return target_path
    
    def _update_organize_status(self, yaml_header: Dict[str, Any]) -> Dict[str, Any]:
        """
        YAMLヘッダーのorganize処理状態を更新
        
        Args:
            yaml_header: 更新対象のYAMLヘッダー
            
        Returns:
            Dict[str, Any]: 更新されたYAMLヘッダー
        """
        current_time = datetime.now().isoformat()
        
        # processing_statusセクションの確認・初期化
        if 'processing_status' not in yaml_header:
            yaml_header['processing_status'] = {}
        
        # organize処理状態を完了に設定
        yaml_header['processing_status']['organize'] = 'completed'
        
        # 最終更新時刻を更新
        yaml_header['last_updated'] = current_time
        
        # workflow_versionの確認
        if 'workflow_version' not in yaml_header:
            yaml_header['workflow_version'] = '3.2'
        
        return yaml_header
    
    def get_organize_summary(self, base_dir: Union[str, Path]) -> Dict[str, Any]:
        """
        organize処理の概要情報を取得
        
        Args:
            base_dir: ベースディレクトリ
            
        Returns:
            Dict[str, Any]: 概要情報
        """
        try:
            base_path = Path(base_dir)
            
            # 統計情報収集
            organized_dirs = [d for d in base_path.iterdir() if d.is_dir()]
            organized_files = []
            pending_files = []
            
            for md_file in base_path.rglob("*.md"):
                try:
                    yaml_header, _ = self.yaml_processor.parse_yaml_header(md_file)
                    status = yaml_header.get('processing_status', {}).get('organize', 'pending')
                    
                    if status == 'completed':
                        organized_files.append(str(md_file))
                    else:
                        pending_files.append(str(md_file))
                        
                except Exception:
                    pending_files.append(str(md_file))
            
            summary = {
                'total_directories': len(organized_dirs),
                'organized_files': len(organized_files),
                'pending_files': len(pending_files),
                'organization_rate': len(organized_files) / (len(organized_files) + len(pending_files)) if (len(organized_files) + len(pending_files)) > 0 else 0,
                'directories': [d.name for d in organized_dirs],
                'pending_file_paths': pending_files
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate organize summary: {str(e)}")
            return {
                'error': str(e),
                'total_directories': 0,
                'organized_files': 0,
                'pending_files': 0,
                'organization_rate': 0
            } 