#!/usr/bin/env python3

"""
StatusChecker

重複処理回避のための状態チェック機能。
処理ステップの状態確認、スキップ条件判定、強制実行制御を担当。
"""

import yaml
import os
import hashlib
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
            
            # COMPLETEDの場合は、修正時刻とコンテンツ変更をチェック
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
                    
                    # コンテンツ変更チェック
                    content_result = self.detect_content_changes(file_path, update_hash=False)
                    if content_result['has_changes']:
                        self.logger.get_logger().info(
                            f"コンテンツが変更されているため再処理が必要: {file_path.name}"
                        )
                        return True
                    
                    # 変更がない場合はスキップ
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

    def get_advanced_skip_conditions(
        self,
        file_path: Union[str, Path],
        operation: str,
        check_dependencies: bool = False,
        check_workflow_stage: bool = False,
        check_custom_rules: bool = False
    ) -> Dict[str, Any]:
        """
        高度なスキップ条件判定
        
        Args:
            file_path: Markdownファイルパス
            operation: 処理操作名
            check_dependencies: 依存関係チェック有効化
            check_workflow_stage: ワークフロー段階チェック有効化
            check_custom_rules: カスタムルールチェック有効化
            
        Returns:
            Dict[str, Any]: 高度なスキップ条件の詳細
        """
        try:
            file_path = Path(file_path)
            
            conditions = {
                'can_proceed': True,
                'skip_reasons': [],
                'dependency_violations': [],
                'workflow_stage_compatible': True,
                'custom_skip_rules': [],
                'custom_skip_applied': False
            }
            
            if not file_path.exists():
                conditions['can_proceed'] = False
                conditions['skip_reasons'].append("ファイルが存在しません")
                return conditions
            
            # YAMLヘッダー取得
            yaml_header, _ = self.yaml_processor.parse_yaml_header(file_path)
            if not yaml_header:
                conditions['skip_reasons'].append("YAMLヘッダーが存在しません")
                return conditions
            
            processing_status = yaml_header.get('processing_status', {})
            
            # 依存関係チェック
            if check_dependencies:
                dependency_result = self._check_operation_dependencies(
                    processing_status, operation
                )
                conditions['dependency_violations'] = dependency_result['violations']
                if dependency_result['violations']:
                    conditions['can_proceed'] = False
                    conditions['skip_reasons'].extend([
                        f"依存関係違反: {violation}" 
                        for violation in dependency_result['violations']
                    ])
            
            # ワークフロー段階チェック
            if check_workflow_stage:
                workflow_stage = yaml_header.get('workflow_stage', 'unknown')
                stage_compatible = self._check_workflow_stage_compatibility(
                    workflow_stage, operation
                )
                conditions['workflow_stage_compatible'] = stage_compatible
                if not stage_compatible:
                    conditions['can_proceed'] = False
                    conditions['skip_reasons'].append(
                        f"ワークフロー段階 '{workflow_stage}' と操作 '{operation}' が非互換"
                    )
            
            # カスタムルールチェック
            if check_custom_rules:
                skip_rules = yaml_header.get('skip_rules', {})
                custom_rules = skip_rules.get(operation, [])
                conditions['custom_skip_rules'] = custom_rules
                if custom_rules:
                    conditions['custom_skip_applied'] = True
                    conditions['can_proceed'] = False
                    conditions['skip_reasons'].append(
                        f"カスタムスキップルールが適用: {', '.join(custom_rules)}"
                    )
            
            return conditions
            
        except Exception as e:
            self.logger.get_logger().error(
                f"高度スキップ条件判定エラー: {file_path}: {str(e)}"
            )
            return {
                'can_proceed': False,
                'skip_reasons': [f"エラー: {str(e)}"],
                'dependency_violations': [],
                'workflow_stage_compatible': False,
                'custom_skip_rules': [],
                'custom_skip_applied': False
            }
    
    def get_skip_condition_priority(
        self,
        file_path: Union[str, Path],
        operation: str
    ) -> Dict[str, Any]:
        """
        スキップ条件の優先度処理
        
        Args:
            file_path: Markdownファイルパス
            operation: 処理操作名
            
        Returns:
            Dict[str, Any]: 優先度処理結果
        """
        try:
            file_path = Path(file_path)
            
            result = {
                'final_decision': 'skip',
                'priority_reason': '',
                'conditions_evaluated': []
            }
            
            if not file_path.exists():
                result['final_decision'] = 'skip'
                result['priority_reason'] = "ファイルが存在しません"
                return result
            
            # YAMLヘッダー取得
            yaml_header, _ = self.yaml_processor.parse_yaml_header(file_path)
            if not yaml_header:
                result['final_decision'] = 'process'
                result['priority_reason'] = "YAMLヘッダーが存在しないため処理が必要"
                return result
            
            processing_status = yaml_header.get('processing_status', {})
            current_status = processing_status.get(operation, 'pending')
            status_enum = ProcessingStatus.from_string(current_status)
            
            # 1. 強制再処理フラグチェック（最高優先度）
            priority_settings = yaml_header.get('priority_settings', {})
            force_key = f'force_reprocess_{operation}'
            if priority_settings.get(force_key, False):
                result['final_decision'] = 'process'
                result['priority_reason'] = f"強制再処理フラグが設定: {force_key}"
                result['conditions_evaluated'].append('force_reprocess_flag')
                return result
            
            # 2. 操作固有の優先度ルール
            if operation in ['organize', 'sync']:
                # 基盤操作は高優先度
                if status_enum in [ProcessingStatus.PENDING, ProcessingStatus.FAILED]:
                    result['final_decision'] = 'process'
                    result['priority_reason'] = f"基盤操作 '{operation}' の {status_enum.to_string()} 状態"
                    result['conditions_evaluated'].append('foundation_operation_priority')
                    return result
            
            # 3. 通常の状態ベース判定
            if status_enum == ProcessingStatus.COMPLETED:
                if self.check_modification_time and self.check_modification_time_changed(file_path):
                    result['final_decision'] = 'process'
                    result['priority_reason'] = "ファイルが変更されているため再処理が必要"
                    result['conditions_evaluated'].append('modification_time_check')
                else:
                    result['final_decision'] = 'skip'
                    result['priority_reason'] = "完了済みで変更なし"
                    result['conditions_evaluated'].append('completed_unchanged')
            else:
                result['final_decision'] = 'process'
                result['priority_reason'] = f"状態が {status_enum.to_string()}"
                result['conditions_evaluated'].append('status_based_decision')
            
            return result
            
        except Exception as e:
            self.logger.get_logger().error(
                f"優先度処理エラー: {file_path}: {str(e)}"
            )
            return {
                'final_decision': 'process',  # エラー時は安全側に倒す
                'priority_reason': f"エラー: {str(e)}",
                'conditions_evaluated': ['error_fallback']
            }
    
    def analyze_batch_skip_conditions(
        self,
        file_paths: List[Union[str, Path]],
        operation: str
    ) -> Dict[str, Any]:
        """
        バッチファイルのスキップ条件分析
        
        Args:
            file_paths: Markdownファイルパスのリスト
            operation: 処理操作名
            
        Returns:
            Dict[str, Any]: バッチ分析結果
        """
        try:
            analysis = {
                'total_files': len(file_paths),
                'skip_breakdown': {
                    'can_skip': 0,
                    'need_processing': 0,
                    'errors': 0
                },
                'processing_recommendations': [],
                'efficiency_metrics': {
                    'skip_rate': 0.0,
                    'estimated_time_saved': 0.0
                }
            }
            
            for file_path in file_paths:
                try:
                    file_path = Path(file_path)
                    
                    # 優先度処理で最終判定
                    priority_result = self.get_skip_condition_priority(file_path, operation)
                    
                    if priority_result['final_decision'] == 'skip':
                        analysis['skip_breakdown']['can_skip'] += 1
                    else:
                        analysis['skip_breakdown']['need_processing'] += 1
                        analysis['processing_recommendations'].append({
                            'file': str(file_path),
                            'reason': priority_result['priority_reason']
                        })
                    
                except Exception as e:
                    analysis['skip_breakdown']['errors'] += 1
                    self.logger.get_logger().warning(
                        f"バッチ分析エラー {file_path}: {str(e)}"
                    )
            
            # 効率性メトリクス計算
            if analysis['total_files'] > 0:
                analysis['efficiency_metrics']['skip_rate'] = (
                    analysis['skip_breakdown']['can_skip'] / analysis['total_files']
                ) * 100
                
                # 簡易的な時間節約推定（1ファイル = 30秒と仮定）
                analysis['efficiency_metrics']['estimated_time_saved'] = (
                    analysis['skip_breakdown']['can_skip'] * 30
                )
            
            return analysis
            
        except Exception as e:
            self.logger.get_logger().error(f"バッチ分析エラー: {str(e)}")
            return {
                'total_files': len(file_paths),
                'skip_breakdown': {'can_skip': 0, 'need_processing': 0, 'errors': len(file_paths)},
                'processing_recommendations': [],
                'efficiency_metrics': {'skip_rate': 0.0, 'estimated_time_saved': 0.0}
            }
    
    def _check_operation_dependencies(
        self,
        processing_status: Dict[str, str],
        operation: str
    ) -> Dict[str, Any]:
        """
        操作の依存関係チェック
        
        Args:
            processing_status: 処理状態辞書
            operation: 処理操作名
            
        Returns:
            Dict[str, Any]: 依存関係チェック結果
        """
        # 操作の依存関係定義
        dependencies = {
            'sync': ['organize'],  # syncはorganizeに依存
            'enhance': ['organize', 'sync'],  # enhanceはorganizeとsyncに依存
            'ai_processing': ['organize', 'sync'],  # AI処理はorganizeとsyncに依存
            'summarize': ['enhance'],  # 要約はenhanceに依存
        }
        
        result = {
            'has_dependencies': operation in dependencies,
            'required_operations': dependencies.get(operation, []),
            'violations': []
        }
        
        if operation not in dependencies:
            return result
        
        # 依存操作の状態チェック
        for required_op in dependencies[operation]:
            required_status = processing_status.get(required_op, 'pending')
            if ProcessingStatus.from_string(required_status) != ProcessingStatus.COMPLETED:
                result['violations'].append(
                    f"必要な操作 '{required_op}' が未完了: {required_status}"
                )
        
        return result
    
    def _check_workflow_stage_compatibility(
        self,
        workflow_stage: str,
        operation: str
    ) -> bool:
        """
        ワークフロー段階と操作の互換性チェック
        
        Args:
            workflow_stage: ワークフロー段階
            operation: 処理操作名
            
        Returns:
            bool: 互換性がある場合True
        """
        # ワークフロー段階と操作の互換性マッピング
        stage_operations = {
            'organization': ['organize', 'sync'],
            'enhancement': ['enhance', 'ai_processing'],
            'analysis': ['summarize', 'report'],
            'completion': []  # 完了段階では新規操作なし
        }
        
        # unknownまたは未定義の段階では全操作を許可
        if workflow_stage in ['unknown', '']:
            return True
        
        # 段階に対応する操作をチェック
        allowed_operations = stage_operations.get(workflow_stage, [])
        return operation in allowed_operations

    def get_force_execution_control(
        self,
        file_path: Union[str, Path],
        operation: str,
        force_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        強制実行制御機能
        
        Args:
            file_path: Markdownファイルパス
            operation: 処理操作名
            force_config: 強制実行設定
            
        Returns:
            Dict[str, Any]: 強制実行制御結果
        """
        try:
            file_path = Path(file_path)
            
            result = {
                'should_force': False,
                'force_reasons': [],
                'safety_warnings': [],
                'backup_required': False,
                'confirmation_required': False
            }
            
            if not file_path.exists():
                result['force_reasons'].append("ファイルが存在しません")
                return result
            
            # YAMLヘッダー取得
            yaml_header, _ = self.yaml_processor.parse_yaml_header(file_path)
            if not yaml_header:
                result['should_force'] = True
                result['force_reasons'].append("YAMLヘッダーが存在しないため強制実行")
                return result
            
            # グローバル強制実行チェック
            if force_config.get('force_all_operations', False):
                result['should_force'] = True
                result['force_reasons'].append("グローバル強制実行が有効")
                
                # 設定から理由を追加
                config_reasons = force_config.get('force_reasons', [])
                result['force_reasons'].extend(config_reasons)
            
            # 選択的操作強制実行チェック
            elif force_config.get('force_operations', []):
                force_operations = force_config['force_operations']
                if operation in force_operations:
                    result['should_force'] = True
                    result['force_reasons'].append(f"操作 '{operation}' が強制実行対象")
            
            # 安全性チェック
            if force_config.get('enable_safety_checks', False):
                safety_flags = yaml_header.get('safety_flags', {})
                
                if safety_flags.get('critical_data', False):
                    result['safety_warnings'].append('critical_data')
                    result['confirmation_required'] = True
                
                if safety_flags.get('backup_required', False) or force_config.get('require_backup', False):
                    result['backup_required'] = True
            
            # 依存関係チェック
            if force_config.get('respect_dependencies', True) and result['should_force']:
                processing_status = yaml_header.get('processing_status', {})
                dependency_result = self._check_operation_dependencies(
                    processing_status, operation
                )
                
                if dependency_result['violations']:
                    result['safety_warnings'].append('dependency_violations')
                    result['force_reasons'].append("依存関係違反を無視して強制実行")
            
            return result
            
        except Exception as e:
            self.logger.get_logger().error(
                f"強制実行制御エラー: {file_path}: {str(e)}"
            )
            return {
                'should_force': False,
                'force_reasons': [f"エラー: {str(e)}"],
                'safety_warnings': ['error'],
                'backup_required': True,
                'confirmation_required': True
            }
    
    def analyze_force_execution_impact(
        self,
        file_paths: List[Union[str, Path]],
        force_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        強制実行影響分析（ドライラン）
        
        Args:
            file_paths: Markdownファイルパスのリスト
            force_config: 強制実行設定
            
        Returns:
            Dict[str, Any]: 影響分析結果
        """
        try:
            analysis = {
                'affected_files': 0,
                'operations_to_force': [],
                'estimated_impact': {
                    'total_operations': 0,
                    'critical_operations': 0,
                    'backup_required_count': 0
                },
                'safety_concerns': [],
                'execution_plan': []
            }
            
            for file_path in file_paths:
                try:
                    file_path = Path(file_path)
                    
                    if not file_path.exists():
                        continue
                    
                    # 強制実行対象かチェック
                    operations_to_check = force_config.get('force_operations', [])
                    if force_config.get('force_all_operations', False):
                        operations_to_check = ['organize', 'sync', 'enhance', 'ai_processing']
                    
                    file_operations = []
                    for operation in operations_to_check:
                        force_result = self.get_force_execution_control(
                            file_path, operation, force_config
                        )
                        
                        if force_result['should_force']:
                            file_operations.append(operation)
                            analysis['estimated_impact']['total_operations'] += 1
                            
                            if force_result['safety_warnings']:
                                analysis['estimated_impact']['critical_operations'] += 1
                                analysis['safety_concerns'].extend(force_result['safety_warnings'])
                            
                            if force_result['backup_required']:
                                analysis['estimated_impact']['backup_required_count'] += 1
                    
                    if file_operations:
                        analysis['affected_files'] += 1
                        analysis['operations_to_force'].extend(file_operations)
                        analysis['execution_plan'].append({
                            'file': str(file_path),
                            'operations': file_operations
                        })
                    
                except Exception as e:
                    self.logger.get_logger().warning(
                        f"影響分析エラー {file_path}: {str(e)}"
                    )
            
            # 重複削除
            analysis['operations_to_force'] = list(set(analysis['operations_to_force']))
            analysis['safety_concerns'] = list(set(analysis['safety_concerns']))
            
            return analysis
            
        except Exception as e:
            self.logger.get_logger().error(f"強制実行影響分析エラー: {str(e)}")
            return {
                'affected_files': 0,
                'operations_to_force': [],
                'estimated_impact': {'total_operations': 0, 'critical_operations': 0, 'backup_required_count': 0},
                'safety_concerns': ['analysis_error'],
                'execution_plan': []
            }
    
    def create_batch_force_execution_plan(
        self,
        file_paths: List[Union[str, Path]],
        force_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        バッチ強制実行計画作成
        
        Args:
            file_paths: Markdownファイルパスのリスト
            force_config: 強制実行設定
            
        Returns:
            Dict[str, Any]: バッチ実行計画
        """
        try:
            plan = {
                'execution_batches': [],
                'total_operations': 0,
                'estimated_duration': 0,
                'batch_configuration': {
                    'batch_size': force_config.get('batch_size', 10),
                    'parallel_execution': force_config.get('parallel_execution', False),
                    'stop_on_error': force_config.get('stop_on_error', True)
                }
            }
            
            # 影響分析を実行
            impact_analysis = self.analyze_force_execution_impact(file_paths, force_config)
            plan['total_operations'] = impact_analysis['estimated_impact']['total_operations']
            
            # バッチに分割
            batch_size = plan['batch_configuration']['batch_size']
            execution_items = impact_analysis['execution_plan']
            
            for i in range(0, len(execution_items), batch_size):
                batch = execution_items[i:i + batch_size]
                batch_operations = sum(len(item['operations']) for item in batch)
                
                plan['execution_batches'].append({
                    'batch_id': len(plan['execution_batches']) + 1,
                    'files': [item['file'] for item in batch],
                    'operations_count': batch_operations,
                    'estimated_time': batch_operations * 30  # 30秒/操作と仮定
                })
            
            # 総推定時間計算
            if plan['batch_configuration']['parallel_execution']:
                # 並列実行の場合は最大バッチ時間
                plan['estimated_duration'] = max(
                    (batch['estimated_time'] for batch in plan['execution_batches']),
                    default=0
                )
            else:
                # シーケンシャル実行の場合は合計時間
                plan['estimated_duration'] = sum(
                    batch['estimated_time'] for batch in plan['execution_batches']
                )
            
            return plan
            
        except Exception as e:
            self.logger.get_logger().error(f"バッチ実行計画作成エラー: {str(e)}")
            return {
                'execution_batches': [],
                'total_operations': 0,
                'estimated_duration': 0,
                'batch_configuration': {},
                'error': str(e)
            }
    
    def create_force_execution_rollback_plan(
        self,
        file_path: Union[str, Path],
        force_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        強制実行ロールバック計画作成
        
        Args:
            file_path: Markdownファイルパス
            force_config: 強制実行設定
            
        Returns:
            Dict[str, Any]: ロールバック計画
        """
        try:
            file_path = Path(file_path)
            
            plan = {
                'snapshot_required': False,
                'rollback_steps': [],
                'recovery_operations': [],
                'rollback_points': []
            }
            
            if not file_path.exists():
                return plan
            
            # ロールバック機能が有効かチェック
            if not force_config.get('enable_rollback', False):
                return plan
            
            # YAMLヘッダー取得
            yaml_header, _ = self.yaml_processor.parse_yaml_header(file_path)
            if yaml_header:
                processing_status = yaml_header.get('processing_status', {})
                
                # 現在の状態をスナップショットポイントとして記録
                plan['snapshot_required'] = True
                plan['rollback_points'].append({
                    'timestamp': datetime.now().isoformat(),
                    'processing_status': processing_status.copy(),
                    'workflow_version': yaml_header.get('workflow_version', '3.2')
                })
            
            # スナップショット作成設定
            if force_config.get('create_snapshots', False):
                plan['rollback_steps'].append({
                    'step': 'create_file_backup',
                    'description': 'ファイルのバックアップを作成',
                    'target': str(file_path)
                })
            
            # 状態復旧操作
            plan['recovery_operations'] = [
                'restore_processing_status',
                'revert_yaml_header',
                'validate_file_integrity'
            ]
            
            # 最大ロールバックポイント数チェック
            max_rollback_points = force_config.get('max_rollback_points', 3)
            if len(plan['rollback_points']) > max_rollback_points:
                plan['rollback_points'] = plan['rollback_points'][-max_rollback_points:]
            
            return plan
            
        except Exception as e:
            self.logger.get_logger().error(
                f"ロールバック計画作成エラー: {file_path}: {str(e)}"
            )
            return {
                'snapshot_required': True,  # エラー時は安全側に倒す
                'rollback_steps': [],
                'recovery_operations': ['emergency_recovery'],
                'rollback_points': [],
                'error': str(e)
            }

    def calculate_content_hash(self, file_path: Union[str, Path]) -> str:
        """
        ファイルコンテンツのハッシュ値を計算
        YAMLヘッダーを除いたコンテンツ部分のみをハッシュ計算対象とする
        
        Args:
            file_path: Markdownファイルパス
            
        Returns:
            str: SHA256ハッシュ値
            
        Raises:
            FileSystemError: ファイル読み込みエラー
        """
        try:
            file_path = Path(file_path)
            
            # YAMLヘッダーとコンテンツを分離
            yaml_header, content = self.yaml_processor.parse_yaml_header(file_path)
            
            # コンテンツ部分のみでハッシュ計算（YAMLヘッダーは除外）
            content_bytes = content.encode('utf-8')
            hash_object = hashlib.sha256(content_bytes)
            return hash_object.hexdigest()
            
        except Exception as e:
            raise FileSystemError(
                f"ファイルハッシュ計算エラー: {file_path}: {str(e)}",
                error_code="HASH_CALCULATION_ERROR",
                context={"file": str(file_path)}
            )

    def detect_content_changes(self, file_path: Union[str, Path], update_hash: bool = True) -> Dict[str, Any]:
        """
        ファイルコンテンツの変更を検出
        
        Args:
            file_path: Markdownファイルパス
            update_hash: ハッシュを更新するかどうか
            
        Returns:
            Dict[str, Any]: 変更検出結果
        """
        try:
            file_path = Path(file_path)
            
            # 現在のコンテンツハッシュ計算
            current_hash = self.calculate_content_hash(file_path)
            
            # YAMLヘッダーから保存されたハッシュを取得
            yaml_header, content = self.yaml_processor.parse_yaml_header(file_path)
            previous_hash = None
            
            if yaml_header:
                previous_hash = yaml_header.get('content_hash')
            
            # 変更検出
            has_changes = previous_hash is None or current_hash != previous_hash
            
            # 初回実行または変更があった場合、ハッシュを更新
            if update_hash and (previous_hash is None or has_changes):
                if not yaml_header:
                    yaml_header = {}
                yaml_header['content_hash'] = current_hash
                yaml_header['last_updated'] = datetime.now().isoformat()
                self.yaml_processor.write_yaml_header(file_path, yaml_header, content)
            
            result = {
                'has_changes': has_changes,
                'current_hash': current_hash,
                'previous_hash': previous_hash,
                'file_path': str(file_path),
                'timestamp': datetime.now().isoformat()
            }
            
            if has_changes:
                self.logger.get_logger().info(
                    f"コンテンツ変更検出: {file_path.name}"
                )
            else:
                self.logger.get_logger().debug(
                    f"コンテンツ変更なし: {file_path.name}"
                )
            
            return result
            
        except Exception as e:
            self.logger.get_logger().error(
                f"コンテンツ変更検出エラー: {file_path}: {str(e)}"
            )
            return {
                'has_changes': True,  # エラー時は安全側に倒す
                'current_hash': None,
                'previous_hash': None,
                'file_path': str(file_path),
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }

    def detect_batch_content_changes(
        self, 
        file_paths: List[Union[str, Path]]
    ) -> Dict[str, Any]:
        """
        複数ファイルのコンテンツ変更をバッチ検出
        
        Args:
            file_paths: Markdownファイルパスのリスト
            
        Returns:
            Dict[str, Any]: バッチ変更検出結果
        """
        try:
            result = {
                'changed_files': [],
                'unchanged_files': [],
                'total_files': len(file_paths),
                'error_files': [],
                'timestamp': datetime.now().isoformat()
            }
            
            for file_path in file_paths:
                try:
                    # バッチ処理では自動ハッシュ更新は行わない
                    change_result = self.detect_content_changes(file_path, update_hash=False)
                    
                    if change_result.get('has_changes', False):
                        result['changed_files'].append({
                            'file_path': change_result['file_path'],
                            'current_hash': change_result['current_hash'],
                            'previous_hash': change_result['previous_hash']
                        })
                    else:
                        result['unchanged_files'].append({
                            'file_path': change_result['file_path'],
                            'hash': change_result['current_hash']
                        })
                        
                except Exception as e:
                    result['error_files'].append({
                        'file_path': str(file_path),
                        'error': str(e)
                    })
            
            self.logger.get_logger().info(
                f"バッチ変更検出完了: 変更{len(result['changed_files'])}件, "
                f"未変更{len(result['unchanged_files'])}件, "
                f"エラー{len(result['error_files'])}件"
            )
            
            return result
            
        except Exception as e:
            self.logger.get_logger().error(f"バッチ変更検出エラー: {str(e)}")
            return {
                'changed_files': [],
                'unchanged_files': [],
                'total_files': len(file_paths),
                'error_files': [{'error': str(e)}],
                'timestamp': datetime.now().isoformat()
            }

    def should_skip_operation_intelligent(
        self, 
        file_path: Union[str, Path], 
        operation: str
    ) -> Dict[str, Any]:
        """
        コンテンツ変更を考慮したインテリジェントスキップ判定
        
        Args:
            file_path: Markdownファイルパス
            operation: 処理操作名
            
        Returns:
            Dict[str, Any]: スキップ判定結果
        """
        try:
            file_path = Path(file_path)
            
            result = {
                'should_skip': False,
                'skip_reasons': [],
                'content_analysis': {
                    'has_changes': False,
                    'hash_comparison': None
                },
                'status_analysis': {
                    'current_status': 'unknown',
                    'completion_time': None
                }
            }
            
            # 基本的な処理必要性チェック
            processing_needed = self.check_processing_needed(file_path, operation)
            
            # コンテンツ変更検出（判定のみ、ハッシュは更新しない）
            content_result = self.detect_content_changes(file_path, update_hash=False)
            result['content_analysis'] = {
                'has_changes': content_result['has_changes'],
                'hash_comparison': {
                    'current': content_result['current_hash'],
                    'previous': content_result['previous_hash']
                }
            }
            
            # YAMLヘッダーから処理状態取得
            yaml_header, _ = self.yaml_processor.parse_yaml_header(file_path)
            if yaml_header:
                processing_status = yaml_header.get('processing_status', {})
                current_status = processing_status.get(operation, 'pending')
                result['status_analysis']['current_status'] = current_status
                
                # 完了時刻情報取得
                completion_info = processing_status.get(f"{operation}_completed_at")
                if completion_info:
                    result['status_analysis']['completion_time'] = completion_info
            
            # インテリジェントスキップ判定
            if not processing_needed:
                # 基本的にはスキップ対象
                result['should_skip'] = True
                result['skip_reasons'].append('operation_completed')
                
                # ただし、コンテンツ変更がある場合はスキップしない
                if content_result['has_changes']:
                    result['should_skip'] = False
                    result['skip_reasons'].append('content_changed')
            else:
                result['should_skip'] = False
                result['skip_reasons'].append('processing_required')
            
            return result
            
        except Exception as e:
            self.logger.get_logger().error(
                f"インテリジェントスキップ判定エラー: {file_path}: {str(e)}"
            )
            return {
                'should_skip': False,  # エラー時は処理を実行
                'skip_reasons': [f'error: {str(e)}'],
                'content_analysis': {'has_changes': True, 'hash_comparison': None},
                'status_analysis': {'current_status': 'error', 'completion_time': None}
            }

    def update_processing_status_with_hash(
        self, 
        file_path: Union[str, Path], 
        operation: str, 
        status: ProcessingStatus
    ) -> None:
        """
        処理状態とコンテンツハッシュを同時に更新
        
        Args:
            file_path: Markdownファイルパス
            operation: 処理操作名
            status: 新しい処理状態
            
        Raises:
            ProcessingError: 状態更新エラー
        """
        try:
            file_path = Path(file_path)
            
            # YAMLヘッダー取得
            yaml_header, content = self.yaml_processor.parse_yaml_header(file_path)
            if not yaml_header:
                yaml_header = {}
            
            # 処理状態更新
            if 'processing_status' not in yaml_header:
                yaml_header['processing_status'] = {}
            
            yaml_header['processing_status'][operation] = status.to_string()
            
            # 完了時の追加情報
            if status == ProcessingStatus.COMPLETED:
                yaml_header['processing_status'][f"{operation}_completed_at"] = datetime.now().isoformat()
                # コンテンツハッシュ更新
                yaml_header['content_hash'] = self.calculate_content_hash(file_path)
            
            # 最終更新時刻更新
            yaml_header['last_updated'] = datetime.now().isoformat()
            
            # YAMLヘッダー書き込み
            self.yaml_processor.write_yaml_header(file_path, yaml_header, content)
            
            self.logger.get_logger().info(
                f"処理状態・ハッシュ更新完了: {file_path.name}, {operation} -> {status.to_string()}"
            )
            
        except Exception as e:
            raise ProcessingError(
                f"処理状態・ハッシュ更新エラー: {file_path}: {str(e)}",
                error_code="STATUS_HASH_UPDATE_ERROR",
                context={"file": str(file_path), "operation": operation, "status": status.to_string()}
            ) 