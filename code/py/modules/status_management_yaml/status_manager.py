#!/usr/bin/env python3
"""
StatusManager

YAMLヘッダーベースの状態管理システムの中核クラス。
処理状態の読み込み、更新、処理対象論文の特定を担当。
"""

import os
import glob
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union

from .processing_status import ProcessingStatus
from .yaml_header_processor import YAMLHeaderProcessor
from ..shared_modules.config_manager import ConfigManager
from ..shared_modules.integrated_logger import IntegratedLogger
from ..shared_modules.exceptions import ProcessingError, YAMLError, FileSystemError
from ..shared_modules.file_utils import BackupManager


class StatusManager:
    """
    状態管理クラス
    
    YAMLヘッダーベースの処理状態管理システムの中核。
    各論文の処理状態を追跡し、重複処理回避を実現。
    """
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        StatusManagerの初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ出力オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('StatusManager')
        self.yaml_processor = YAMLHeaderProcessor(config_manager, logger)
        self.backup_manager = BackupManager()
        
        self.logger.info("StatusManager initialized")
    
    def load_md_statuses(self, clippings_dir: str) -> Dict[str, Dict[str, ProcessingStatus]]:
        """
        全論文の状態を読み込み
        
        Args:
            clippings_dir: Clippingsディレクトリのパス
            
        Returns:
            Dict[str, Dict[str, ProcessingStatus]]: {citation_key: {step: status}}形式の辞書
        """
        statuses = {}
        
        # MarkdownファイルをGlobで検索
        pattern = os.path.join(clippings_dir, "**/*.md")
        md_files = glob.glob(pattern, recursive=True)
        
        for md_file in md_files:
            try:
                yaml_header, _ = self.yaml_processor.parse_yaml_header(Path(md_file))
                citation_key = yaml_header.get('citation_key')
                processing_status = yaml_header.get('processing_status', {})
                
                if citation_key:
                    statuses[citation_key] = {
                        step: ProcessingStatus.from_string(status) 
                        for step, status in processing_status.items()
                    }
                    
            except Exception as e:
                self.logger.warning(f"Failed to load status from {md_file}: {e}")
                
        self.logger.info(f"Loaded statuses for {len(statuses)} papers from {clippings_dir}")
        return statuses
    
    def update_status(
        self, 
        clippings_dir: str, 
        citation_key: str, 
        step: str, 
        status: ProcessingStatus
    ) -> bool:
        """
        特定論文の特定ステップの状態を更新
        
        Args:
            clippings_dir: Clippingsディレクトリのパス
            citation_key: 論文の識別キー
            step: 処理ステップ名
            status: 新しい処理状態
            
        Returns:
            bool: 更新成功の場合True
            
        Raises:
            ProcessingError: ファイルが見つからない、更新に失敗した場合
        """
        md_file = self._find_markdown_file(clippings_dir, citation_key)
        if not md_file:
            raise ProcessingError(
                f"Markdown file not found for {citation_key}", 
                error_code="FILE_NOT_FOUND"
            )
            
        try:
            # 更新前バックアップ作成
            if self.config_manager.get('status_management.backup_strategy.backup_before_status_update', True):
                self.backup_manager.create_backup(md_file, backup_type="status_update")
            
            yaml_header, content = self.yaml_processor.parse_yaml_header(Path(md_file))
            
            # YAML検証
            if self.config_manager.get('status_management.error_handling.validate_yaml_before_update', True):
                self.yaml_processor.validate_yaml_structure(yaml_header)
            
            # processing_statusを更新
            if 'processing_status' not in yaml_header:
                yaml_header['processing_status'] = {}
            yaml_header['processing_status'][step] = status.to_string()
            
            # メタデータ更新
            yaml_header['last_updated'] = datetime.now().isoformat()
            yaml_header['workflow_version'] = '3.2'
            
            # ファイルに書き戻し
            self.yaml_processor.write_yaml_header(Path(md_file), yaml_header, content)
            
            self.logger.info(f"Updated status for {citation_key}.{step} to {status.to_string()}")
            return True
            
        except YAMLError as e:
            # YAML構造エラー：バックアップ作成後修復試行
            if self.config_manager.get('status_management.error_handling.create_backup_on_yaml_error', True):
                self.backup_manager.create_backup(md_file, backup_type="yaml_error")
            
            if self.config_manager.get('status_management.error_handling.auto_repair_corrupted_headers', True):
                return self._attempt_yaml_repair(md_file, citation_key, step, status, clippings_dir)
            raise
            
        except Exception as e:
            # 一般的なエラー：バックアップからの復旧試行
            if self.config_manager.get('status_management.error_handling.fallback_to_backup_on_failure', True):
                return self._attempt_backup_recovery(md_file, citation_key, step, status, clippings_dir)
            
            raise ProcessingError(
                f"Failed to update status for {citation_key}: {e}",
                error_code="STATUS_UPDATE_FAILED",
                context={"file": md_file, "step": step, "status": status.to_string()}
            )
    
    def get_papers_needing_processing(
        self, 
        clippings_dir: str, 
        step: str, 
        target_papers: List[str]
    ) -> List[str]:
        """
        指定ステップで処理が必要な論文リストを取得
        
        Args:
            clippings_dir: Clippingsディレクトリのパス
            step: 処理ステップ名
            target_papers: 対象論文のcitation_keyリスト
            
        Returns:
            List[str]: 処理が必要な論文のファイルパスリスト
        """
        if not target_papers:
            return []
            
        papers_needing_processing = []
        statuses = self.load_md_statuses(clippings_dir)
        
        for citation_key in target_papers:
            current_status = statuses.get(citation_key, {}).get(step, ProcessingStatus.PENDING)
            if current_status in [ProcessingStatus.PENDING, ProcessingStatus.FAILED]:
                md_file = self._find_markdown_file(clippings_dir, citation_key)
                if md_file:
                    papers_needing_processing.append(md_file)
                
        self.logger.info(
            f"Found {len(papers_needing_processing)} papers needing processing for step '{step}'"
        )
        return papers_needing_processing
    
    def _find_markdown_file(self, clippings_dir: str, citation_key: str) -> Optional[str]:
        """
        citation_keyに対応するMarkdownファイルを検索
        
        Args:
            clippings_dir: Clippingsディレクトリのパス
            citation_key: 論文の識別キー
            
        Returns:
            Optional[str]: ファイルパス（見つからない場合はNone）
        """
        # 直接的なファイル名パターンで検索
        possible_paths = [
            os.path.join(clippings_dir, f"{citation_key}.md"),
            os.path.join(clippings_dir, citation_key, f"{citation_key}.md")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 再帰的検索
        pattern = os.path.join(clippings_dir, "**", f"{citation_key}.md")
        matches = glob.glob(pattern, recursive=True)
        
        if matches:
            return matches[0]  # 最初にマッチしたファイルを返す
        
        return None
    
    def _attempt_yaml_repair(
        self, 
        md_file: str, 
        citation_key: str, 
        step: str, 
        status: ProcessingStatus,
        clippings_dir: str
    ) -> bool:
        """
        YAML修復を試行
        
        Args:
            md_file: 修復対象ファイル
            citation_key: 論文の識別キー
            step: 処理ステップ名
            status: 設定する処理状態
            clippings_dir: Clippingsディレクトリのパス
            
        Returns:
            bool: 修復成功の場合True
        """
        try:
            success = self.yaml_processor.repair_yaml_header(Path(md_file), citation_key)
            if success:
                # 修復後に再度状態更新を試行
                return self.update_status(clippings_dir, citation_key, step, status)
        except Exception as e:
            self.logger.error(f"YAML repair failed for {citation_key}: {e}")
        
        return False
    
    def _attempt_backup_recovery(
        self, 
        md_file: str, 
        citation_key: str, 
        step: str, 
        status: ProcessingStatus,
        clippings_dir: str
    ) -> bool:
        """
        バックアップからの復旧を試行
        
        Args:
            md_file: 復旧対象ファイル
            citation_key: 論文の識別キー
            step: 処理ステップ名
            status: 設定する処理状態
            clippings_dir: Clippingsディレクトリのパス
            
        Returns:
            bool: 復旧成功の場合True
        """
        try:
            backup_restored = self.backup_manager.restore_from_backup(md_file)
            if backup_restored:
                # 復旧後に再度状態更新を試行
                return self.update_status(clippings_dir, citation_key, step, status)
        except Exception as e:
            self.logger.error(f"Backup recovery failed for {citation_key}: {e}")
        
        return False 