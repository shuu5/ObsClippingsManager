#!/usr/bin/env python3

"""
StatusChecker

重複処理回避のための状態チェック機能。
処理ステップの状態確認、スキップ条件判定、強制実行制御を担当。
"""

import yaml
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

from ..shared.config_manager import ConfigManager
from ..shared.integrated_logger import IntegratedLogger
from ..shared.exceptions import (
    ProcessingError, ValidationError, YAMLError, FileSystemError
)
from .yaml_header_processor import YAMLHeaderProcessor
from .processing_status import ProcessingStatus


class StatusChecker:
    """
    状態チェッククラス
    
    重複処理回避のための状態チェック機能。
    処理ステップの状態確認、スキップ条件判定、強制実行制御を担当。
    """
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        StatusCheckerの初期化
        
        Args:
            config_manager: 設定管理マネージャー
            logger: ログ管理システム
        """
        self.config_manager = config_manager
        self.logger = logger
        
        # YAMLヘッダープロセッサー初期化
        self.yaml_processor = YAMLHeaderProcessor(config_manager, logger)
        
        # 設定取得
        self.skip_completed_operations = self.config_manager.get(
            'processing.skip_completed_operations', True
        )
        self.check_modification_time = self.config_manager.get(
            'processing.check_modification_time', True
        )
        self.force_reprocessing = self.config_manager.get(
            'processing.force_reprocessing', False
        )
        
    def check_processing_needed(
        self, 
        file_path: Union[str, Path], 
        operation: str, 
        force: bool = False
    ) -> bool:
        """
        処理が必要かどうかをチェック
        
        Args:
            file_path: Markdownファイルパス
            operation: 処理操作名
            force: 強制実行フラグ
            
        Returns:
            bool: 処理が必要な場合True
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                self.logger.get_logger().warning(f"ファイルが存在しません: {file_path}")
                return False
            
            # 強制実行モードの場合は常に処理が必要
            if force or self.force_reprocessing:
                self.logger.get_logger().info(
                    f"強制実行モードで処理実行: {file_path.name}, operation: {operation}"
                )
                return True
            
            # YAMLヘッダーから状態を取得
            yaml_header, _ = self.yaml_processor.parse_yaml_header(file_path)
            if not yaml_header:
                # ヘッダーが存在しない場合は処理が必要
                return True
            
            processing_status = yaml_header.get('processing_status', {})
            current_status = processing_status.get(operation, 'pending')
            
            # ProcessingStatusで変換して判定
            status_enum = ProcessingStatus.from_string(current_status)
            
            # COMPLETEDの場合は、修正時刻チェックも実行
            if status_enum == ProcessingStatus.COMPLETED:
                # 完了済み操作をスキップする設定の場合
                if self.skip_completed_operations:
                    # 修正時刻チェックが有効な場合は変更をチェック
                    if self.check_modification_time:
                        if self.check_modification_time_changed(file_path):
                            self.logger.get_logger().info(
                                f"ファイルが変更されているため再処理が必要: {file_path.name}"
                            )
                            return True
                    # 変更がないか、修正時刻チェックが無効の場合はスキップ
                    return False
                else:
                    # 完了済み操作をスキップしない設定の場合は処理が必要
                    return True
            
            # PENDING, FAILED, IN_PROGRESS, SKIPPEDの場合は処理が必要
            return status_enum in [
                ProcessingStatus.PENDING, 
                ProcessingStatus.FAILED, 
                ProcessingStatus.IN_PROGRESS, 
                ProcessingStatus.SKIPPED
            ]
            
        except Exception as e:
            self.logger.get_logger().error(
                f"処理必要性チェックエラー: {file_path}: {str(e)}"
            )
            # エラーの場合は安全側に倒して処理が必要と判定
            return True
    
    def check_modification_time_changed(self, file_path: Union[str, Path]) -> bool:
        """
        ファイルの修正時刻が変更されているかチェック
        
        Args:
            file_path: Markdownファイルパス
            
        Returns:
            bool: 変更されている場合True
        """
        try:
            file_path = Path(file_path)
            
            # ファイルの最終修正時刻取得
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            # YAMLヘッダーから最終更新時刻取得
            yaml_header, _ = self.yaml_processor.parse_yaml_header(file_path)
            if not yaml_header:
                return True  # ヘッダーがない場合は変更ありと判定
            
            last_updated_str = yaml_header.get('last_updated')
            if not last_updated_str:
                return True  # 最終更新時刻がない場合は変更ありと判定
            
            try:
                last_updated = datetime.fromisoformat(last_updated_str)
                
                # ファイルの修正時刻が記録された最終更新時刻より新しい場合は変更あり（秒単位での比較）
                time_diff = abs((file_mtime - last_updated).total_seconds())
                return time_diff > 1.0  # 1秒以上の差がある場合のみ変更ありと判定
                
            except (ValueError, TypeError):
                return True  # パース失敗は変更ありと判定
            
        except Exception as e:
            self.logger.get_logger().error(
                f"修正時刻チェックエラー: {file_path}: {str(e)}"
            )
            return True  # エラーの場合は変更ありと判定
    
    def get_skip_conditions(
        self, 
        file_path: Union[str, Path], 
        operation: str
    ) -> Dict[str, Any]:
        """
        スキップ条件の詳細を取得
        
        Args:
            file_path: Markdownファイルパス
            operation: 処理操作名
            
        Returns:
            Dict[str, Any]: スキップ条件の詳細
        """
        try:
            file_path = Path(file_path)
            
            conditions = {
                'already_completed': False,
                'no_changes_detected': False,
                'skip_reasons': []
            }
            
            if not file_path.exists():
                conditions['skip_reasons'].append("ファイルが存在しません")
                return conditions
            
            # YAMLヘッダーから状態を取得
            yaml_header, _ = self.yaml_processor.parse_yaml_header(file_path)
            if not yaml_header:
                conditions['skip_reasons'].append("YAMLヘッダーが存在しません")
                return conditions
            
            processing_status = yaml_header.get('processing_status', {})
            current_status = processing_status.get(operation, 'pending')
            status_enum = ProcessingStatus.from_string(current_status)
            
            # 完了状態チェック
            if status_enum == ProcessingStatus.COMPLETED:
                conditions['already_completed'] = True
                conditions['skip_reasons'].append(f"操作 '{operation}' は既に完了済み")
                
                # 変更検出チェック
                if self.check_modification_time and not self.check_modification_time_changed(file_path):
                    conditions['no_changes_detected'] = True
                    conditions['skip_reasons'].append("ファイルの変更が検出されていません")
            
            return conditions
            
        except Exception as e:
            self.logger.get_logger().error(
                f"スキップ条件取得エラー: {file_path}: {str(e)}"
            )
            return {
                'already_completed': False,
                'no_changes_detected': False,
                'skip_reasons': [f"エラー: {str(e)}"]
            }
    
    def should_skip_operation(
        self, 
        file_path: Union[str, Path], 
        operation: str, 
        force: bool = False
    ) -> bool:
        """
        操作をスキップすべきかどうか判定
        
        Args:
            file_path: Markdownファイルパス
            operation: 処理操作名
            force: 強制実行フラグ
            
        Returns:
            bool: スキップすべき場合True
        """
        # 強制実行モードの場合はスキップしない
        if force or self.force_reprocessing:
            return False
        
        # 処理が必要かどうかの逆
        return not self.check_processing_needed(file_path, operation, force)
    
    def get_processing_summary(
        self, 
        file_paths: List[Union[str, Path]], 
        operation: str
    ) -> Dict[str, Any]:
        """
        処理対象ファイル群のサマリーを取得
        
        Args:
            file_paths: Markdownファイルパスのリスト
            operation: 処理操作名
            
        Returns:
            Dict[str, Any]: 処理サマリー
        """
        try:
            summary = {
                'total_papers': len(file_paths),
                'need_processing': 0,
                'skip_processing': 0,
                'completion_rate': 0.0,
                'status_breakdown': {
                    'pending': 0,
                    'completed': 0,
                    'failed': 0,
                    'in_progress': 0,
                    'skipped': 0
                }
            }
            
            for file_path in file_paths:
                try:
                    file_path = Path(file_path)
                    
                    if not file_path.exists():
                        continue
                    
                    yaml_header, _ = self.yaml_processor.parse_yaml_header(file_path)
                    if not yaml_header:
                        summary['need_processing'] += 1
                        summary['status_breakdown']['pending'] += 1
                        continue
                    
                    processing_status = yaml_header.get('processing_status', {})
                    current_status = processing_status.get(operation, 'pending')
                    status_enum = ProcessingStatus.from_string(current_status)
                    
                    # ステータス別カウント
                    status_str = status_enum.to_string()
                    if status_str in summary['status_breakdown']:
                        summary['status_breakdown'][status_str] += 1
                    
                    # 処理必要性判定
                    if self.check_processing_needed(file_path, operation):
                        summary['need_processing'] += 1
                    else:
                        summary['skip_processing'] += 1
                        
                except Exception as e:
                    self.logger.get_logger().warning(
                        f"ファイル処理エラー in summary: {file_path}: {str(e)}"
                    )
                    # エラーの場合は処理が必要として扱う
                    summary['need_processing'] += 1
            
            # 完了率計算
            if summary['total_papers'] > 0:
                completed_count = summary['status_breakdown']['completed']
                summary['completion_rate'] = (completed_count / summary['total_papers']) * 100
            
            return summary
            
        except Exception as e:
            self.logger.get_logger().error(f"処理サマリー取得エラー: {str(e)}")
            return {
                'total_papers': len(file_paths),
                'need_processing': 0,
                'skip_processing': 0,
                'completion_rate': 0.0,
                'status_breakdown': {
                    'pending': 0,
                    'completed': 0,
                    'failed': 0,
                    'in_progress': 0,
                    'skipped': 0
                }
            }
    
    def validate_processing_requirements(
        self, 
        file_paths: List[Union[str, Path]], 
        operation: str
    ) -> Dict[str, Any]:
        """
        処理要件を検証
        
        Args:
            file_paths: Markdownファイルパスのリスト
            operation: 処理操作名
            
        Returns:
            Dict[str, Any]: 検証結果
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_count': len(file_paths),
            'valid_files': 0,
            'invalid_files': 0
        }
        
        for file_path in file_paths:
            try:
                file_path = Path(file_path)
                
                if not file_path.exists():
                    validation_result['errors'].append(f"ファイルが存在しません: {file_path}")
                    validation_result['invalid_files'] += 1
                    validation_result['valid'] = False
                    continue
                
                if not file_path.suffix.lower() == '.md':
                    validation_result['warnings'].append(f"Markdownファイルではありません: {file_path}")
                
                # YAMLヘッダーの基本検証
                yaml_header, _ = self.yaml_processor.parse_yaml_header(file_path)
                if yaml_header and 'citation_key' not in yaml_header:
                    validation_result['warnings'].append(
                        f"citation_keyが存在しません: {file_path}"
                    )
                
                validation_result['valid_files'] += 1
                
            except Exception as e:
                validation_result['errors'].append(
                    f"ファイル検証エラー {file_path}: {str(e)}"
                )
                validation_result['invalid_files'] += 1
                validation_result['valid'] = False
        
        return validation_result 