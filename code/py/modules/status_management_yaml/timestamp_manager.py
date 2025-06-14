#!/usr/bin/env python3
"""
TimestampManager

詳細なタイムスタンプ管理システム。
処理ステップごとの詳細な時刻記録、履歴管理、統計情報提供を担当。
"""

import yaml
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union

from ..shared_modules.config_manager import ConfigManager
from ..shared_modules.integrated_logger import IntegratedLogger
from ..shared_modules.exceptions import (
    ProcessingError, ValidationError, YAMLError, FileSystemError
)
from .yaml_header_processor import YAMLHeaderProcessor


class TimestampManager:
    """
    タイムスタンプ管理クラス
    
    処理ステップごとの詳細なタイムスタンプ記録と管理。
    処理時間の分析、履歴追跡、統計情報の提供を担当。
    """
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        TimestampManagerの初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ出力オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('TimestampManager')
        self.yaml_processor = YAMLHeaderProcessor(config_manager, logger)
        
        # タイムスタンプ関連設定
        self.timestamp_retention_days = config_manager.get(
            'status_management.timestamp_retention_days', 30
        )
        self.detailed_tracking_enabled = config_manager.get(
            'status_management.detailed_timestamp_tracking', True
        )
        
        self.logger.info("TimestampManager initialized")
    
    def create_timestamp_record(
        self, 
        operation: str, 
        status: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        タイムスタンプ記録を作成
        
        Args:
            operation: 操作名（organize, sync, fetch等）
            status: 状態（started, completed, failed等）
            metadata: 追加メタデータ（オプション）
            
        Returns:
            Dict[str, Any]: タイムスタンプ記録
        """
        timestamp_record = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'status': status
        }
        
        if metadata:
            timestamp_record['metadata'] = metadata
        
        self.logger.debug(f"Created timestamp record for {operation}: {status}")
        return timestamp_record
    
    def update_processing_timestamp(
        self, 
        file_path: Union[str, Path], 
        operation: str, 
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        処理ステップのタイムスタンプを更新
        
        Args:
            file_path: Markdownファイルパス
            operation: 操作名
            status: 状態
            metadata: 追加メタデータ
            
        Returns:
            bool: 更新成功の場合True
            
        Raises:
            ProcessingError: ファイル処理に失敗した場合
        """
        try:
            file_path = Path(file_path)
            yaml_header, content = self.yaml_processor.parse_yaml_header(file_path)
            
            # processing_timestampsセクションを初期化
            if 'processing_timestamps' not in yaml_header:
                yaml_header['processing_timestamps'] = {}
            
            if operation not in yaml_header['processing_timestamps']:
                yaml_header['processing_timestamps'][operation] = []
            
            # 新しいタイムスタンプ記録を追加
            timestamp_record = self.create_timestamp_record(operation, status, metadata)
            yaml_header['processing_timestamps'][operation].append(timestamp_record)
            
            # last_updatedも更新
            yaml_header['last_updated'] = datetime.now().isoformat()
            
            # ファイルに書き戻し
            self.yaml_processor.write_yaml_header(file_path, yaml_header, content)
            
            self.logger.info(f"Updated timestamp for {operation}: {status} in {file_path.name}")
            return True
            
        except Exception as e:
            raise ProcessingError(
                f"Failed to update processing timestamp: {str(e)}",
                error_code="TIMESTAMP_UPDATE_FAILED",
                context={"file": str(file_path), "operation": operation, "status": status}
            )
    
    def get_processing_history(
        self, 
        file_path: Union[str, Path], 
        operation: Optional[str] = None
    ) -> Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        """
        処理履歴タイムスタンプを取得
        
        Args:
            file_path: Markdownファイルパス
            operation: 特定操作の履歴（None の場合は全操作）
            
        Returns:
            Union[List, Dict]: 履歴データ
        """
        try:
            file_path = Path(file_path)
            yaml_header, _ = self.yaml_processor.parse_yaml_header(file_path)
            
            processing_timestamps = yaml_header.get('processing_timestamps', {})
            
            if operation:
                return processing_timestamps.get(operation, [])
            else:
                return processing_timestamps
                
        except Exception as e:
            self.logger.warning(f"Failed to get processing history from {file_path}: {e}")
            return [] if operation else {}
    
    def calculate_processing_duration(
        self, 
        start_timestamp: str, 
        end_timestamp: str
    ) -> Optional[float]:
        """
        処理時間を計算（秒単位）
        
        Args:
            start_timestamp: 開始タイムスタンプ（ISO 8601形式）
            end_timestamp: 終了タイムスタンプ（ISO 8601形式）
            
        Returns:
            Optional[float]: 処理時間（秒）。計算できない場合はNone
        """
        try:
            start_dt = datetime.fromisoformat(start_timestamp.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_timestamp.replace('Z', '+00:00'))
            
            duration = (end_dt - start_dt).total_seconds()
            return duration
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate duration: {e}")
            return None
    
    def get_last_activity_timestamp(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        最終活動タイムスタンプを取得
        
        Args:
            file_path: Markdownファイルパス
            
        Returns:
            Optional[str]: 最終活動タイムスタンプ（ISO 8601形式）
        """
        try:
            file_path = Path(file_path)
            yaml_header, _ = self.yaml_processor.parse_yaml_header(file_path)
            
            last_activity = None
            
            # last_updatedを候補に追加
            if 'last_updated' in yaml_header:
                last_activity = yaml_header['last_updated']
            
            # processing_timestampsから最新を検索
            processing_timestamps = yaml_header.get('processing_timestamps', {})
            for operation, timestamps in processing_timestamps.items():
                for record in timestamps:
                    timestamp = record.get('timestamp')
                    if timestamp:
                        if not last_activity or timestamp > last_activity:
                            last_activity = timestamp
            
            return last_activity
            
        except Exception as e:
            self.logger.warning(f"Failed to get last activity timestamp: {e}")
            return None
    
    def cleanup_old_timestamps(
        self, 
        file_path: Union[str, Path], 
        retention_days: Optional[int] = None
    ) -> int:
        """
        古いタイムスタンプをクリーンアップ
        
        Args:
            file_path: Markdownファイルパス
            retention_days: 保持日数（Noneの場合は設定値を使用）
            
        Returns:
            int: クリーンアップしたタイムスタンプ数
        """
        if retention_days is None:
            retention_days = self.timestamp_retention_days
        
        try:
            file_path = Path(file_path)
            yaml_header, content = self.yaml_processor.parse_yaml_header(file_path)
            
            processing_timestamps = yaml_header.get('processing_timestamps', {})
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            cutoff_str = cutoff_date.isoformat()
            
            cleaned_count = 0
            
            for operation in processing_timestamps:
                original_count = len(processing_timestamps[operation])
                processing_timestamps[operation] = [
                    record for record in processing_timestamps[operation]
                    if record.get('timestamp', '') >= cutoff_str
                ]
                cleaned_count += original_count - len(processing_timestamps[operation])
            
            # 変更があった場合のみ書き戻し
            if cleaned_count > 0:
                yaml_header['processing_timestamps'] = processing_timestamps
                yaml_header['last_updated'] = datetime.now().isoformat()
                self.yaml_processor.write_yaml_header(file_path, yaml_header, content)
                
                self.logger.info(f"Cleaned up {cleaned_count} old timestamps from {file_path.name}")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old timestamps: {e}")
            return 0
    
    def validate_timestamp_format(self, timestamp: Optional[str]) -> bool:
        """
        タイムスタンプフォーマットを検証
        
        Args:
            timestamp: 検証対象のタイムスタンプ文字列
            
        Returns:
            bool: 有効な場合True
        """
        if not timestamp or not isinstance(timestamp, str):
            return False
        
        try:
            # ISO 8601形式の検証
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return True
        except (ValueError, TypeError):
            return False
    
    def get_timestamp_statistics(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        タイムスタンプ統計情報を取得
        
        Args:
            file_path: Markdownファイルパス
            
        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            file_path = Path(file_path)
            yaml_header, _ = self.yaml_processor.parse_yaml_header(file_path)
            
            processing_timestamps = yaml_header.get('processing_timestamps', {})
            
            stats = {
                'total_operations': len(processing_timestamps) if processing_timestamps else 0,
                'completed_operations': 0,
                'failed_operations': 0,
                'avg_processing_time': 0.0,  # Noneではなく0.0で初期化
                'operations_detail': {}
            }
            
            total_duration = 0
            duration_count = 0
            
            for operation, timestamps in processing_timestamps.items():
                operation_stats = {
                    'total_executions': len(timestamps),
                    'completed_count': 0,
                    'failed_count': 0,
                    'last_execution': None,
                    'avg_duration': 0.0  # Noneではなく0.0で初期化
                }
                
                operation_durations = []
                started_times = {}
                
                for record in timestamps:
                    status = record.get('status')
                    timestamp = record.get('timestamp')
                    
                    if status == 'completed':
                        operation_stats['completed_count'] += 1
                        stats['completed_operations'] += 1
                    elif status == 'failed':
                        operation_stats['failed_count'] += 1
                        stats['failed_operations'] += 1
                    
                    if timestamp:
                        operation_stats['last_execution'] = timestamp
                    
                    # 処理時間計算（started -> completed のペアを探す）
                    if status == 'started':
                        started_times[operation] = timestamp
                    elif status == 'completed' and operation in started_times:
                        duration = self.calculate_processing_duration(
                            started_times[operation], timestamp
                        )
                        if duration is not None:
                            operation_durations.append(duration)
                            total_duration += duration
                            duration_count += 1
                
                # 操作別平均処理時間
                if operation_durations:
                    operation_stats['avg_duration'] = sum(operation_durations) / len(operation_durations)
                
                stats['operations_detail'][operation] = operation_stats
            
            # 全体平均処理時間
            if duration_count > 0:
                stats['avg_processing_time'] = total_duration / duration_count
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get timestamp statistics: {e}")
            return {
                'total_operations': 0,
                'completed_operations': 0,
                'failed_operations': 0,
                'avg_processing_time': 0.0,
                'operations_detail': {}
            }
    
    def get_operation_performance_report(
        self, 
        file_path: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        操作パフォーマンスレポートを生成
        
        Args:
            file_path: Markdownファイルパス
            
        Returns:
            Dict[str, Any]: パフォーマンスレポート
        """
        stats = self.get_timestamp_statistics(file_path)
        history = self.get_processing_history(file_path)
        
        report = {
            'summary': {
                'total_operations': stats.get('total_operations', 0),
                'completion_rate': 0,
                'avg_processing_time_minutes': None
            },
            'operations': {},
            'recommendations': []
        }
        
        if stats.get('total_operations', 0) > 0:
            completion_rate = (
                stats.get('completed_operations', 0) / stats.get('total_operations', 1)
            ) * 100
            report['summary']['completion_rate'] = round(completion_rate, 2)
        
        if stats.get('avg_processing_time'):
            report['summary']['avg_processing_time_minutes'] = round(
                stats['avg_processing_time'] / 60, 2
            )
        
        # 操作別詳細
        for operation, detail in stats.get('operations_detail', {}).items():
            report['operations'][operation] = {
                'executions': detail.get('total_executions', 0),
                'success_rate': 0,
                'avg_duration_minutes': None
            }
            
            if detail.get('total_executions', 0) > 0:
                success_rate = (
                    detail.get('completed_count', 0) / detail.get('total_executions', 1)
                ) * 100
                report['operations'][operation]['success_rate'] = round(success_rate, 2)
            
            if detail.get('avg_duration'):
                report['operations'][operation]['avg_duration_minutes'] = round(
                    detail['avg_duration'] / 60, 2
                )
        
        # 推奨事項生成
        if report['summary']['completion_rate'] < 80:
            report['recommendations'].append(
                "完了率が80%を下回っています。エラーログを確認してください。"
            )
        
        if report['summary'].get('avg_processing_time_minutes', 0) > 60:
            report['recommendations'].append(
                "平均処理時間が60分を超えています。パフォーマンス最適化を検討してください。"
            )
        
        return report 