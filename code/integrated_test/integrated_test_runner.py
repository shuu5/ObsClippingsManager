"""
統合テストランナー

エンドツーエンドテスト実行による品質保証・リグレッション防止・
実際のワークスペース環境での動作検証を担当。
"""

import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .test_environment_manager import TestEnvironmentManager
from .test_data_manager import TestDataManager
from .workflow_validator import WorkflowValidator
from .result_analyzer import ResultAnalyzer


class IntegratedTestRunner:
    """統合テストランナー"""
    
    def __init__(self, config_manager, logger):
        """
        統合テストランナーの初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ出力オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger
        
        # 依存クラスのインスタンス化
        self.test_env_manager = TestEnvironmentManager(config_manager, logger)
        self.data_manager = TestDataManager(config_manager, logger)
        self.workflow_validator = WorkflowValidator(config_manager, logger)
        self.result_analyzer = ResultAnalyzer(config_manager, logger)
        
        # 設定値の取得
        self.config = config_manager.get_config().get('integrated_testing', {})
        
        self.logger.info("IntegratedTestRunner initialized")
    
    def run_full_integration_test(self, test_options=None):
        """
        完全統合テスト実行
        
        Args:
            test_options (dict, optional): テストオプション
        
        Returns:
            dict: テスト実行結果
        """
        self.logger.info("Starting full integration test")
        
        test_session_id = self._generate_test_session_id()
        start_time = datetime.now()
        
        try:
            # テスト環境初期化
            test_workspace = self.test_env_manager.create_isolated_environment(test_session_id)
            
            # テストデータ準備
            self.data_manager.setup_test_data(test_workspace)
            
            # 統合ワークフロー実行
            workflow_result = self._execute_integrated_workflow(test_workspace, test_options)
            
            # 結果検証
            validation_result = self.workflow_validator.validate_processing_results(test_workspace)
            
            # 結果分析
            analysis_result = self.result_analyzer.analyze_test_results(
                test_workspace, workflow_result, validation_result
            )
            
            # 環境クリーンアップ
            if self.config.get('test_environment', {}).get('auto_cleanup', True):
                self.test_env_manager.cleanup_environment(test_workspace)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                'test_session_id': test_session_id,
                'status': 'passed',
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat(),
                'duration_seconds': duration,
                'workflow_result': workflow_result,
                'validation_result': validation_result,
                'analysis_result': analysis_result
            }
            
            self.logger.info(f"Full integration test completed successfully: {test_session_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Full integration test failed: {str(e)}")
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                'test_session_id': test_session_id,
                'status': 'failed',
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat(),
                'duration_seconds': duration,
                'error': str(e)
            }
    
    def run_regression_test(self, specific_modules=None):
        """
        リグレッションテスト実行
        
        Args:
            specific_modules (list, optional): 特定モジュールリスト
        
        Returns:
            dict: テスト実行結果
        """
        self.logger.info(f"Starting regression test for modules: {specific_modules}")
        
        test_session_id = self._generate_test_session_id()
        start_time = datetime.now()
        
        try:
            # テスト環境初期化
            test_workspace = self.test_env_manager.create_isolated_environment(test_session_id)
            
            # テストデータ準備
            self.data_manager.setup_test_data(test_workspace)
            
            # 特定モジュールのテスト実行
            regression_result = self._execute_regression_workflow(
                test_workspace, specific_modules
            )
            
            # 結果検証
            validation_result = self.workflow_validator.validate_processing_results(test_workspace)
            
            # 環境クリーンアップ
            if self.config.get('test_environment', {}).get('auto_cleanup', True):
                self.test_env_manager.cleanup_environment(test_workspace)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                'test_session_id': test_session_id,
                'status': 'passed',
                'test_type': 'regression',
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat(),
                'duration_seconds': duration,
                'regression_result': regression_result,
                'validation_result': validation_result,
                'tested_modules': specific_modules
            }
            
            self.logger.info(f"Regression test completed successfully: {test_session_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Regression test failed: {str(e)}")
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                'test_session_id': test_session_id,
                'status': 'failed',
                'test_type': 'regression',
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat(),
                'duration_seconds': duration,
                'error': str(e),
                'tested_modules': specific_modules
            }
    
    def run_performance_test(self, benchmark_data=None):
        """
        パフォーマンステスト実行
        
        Args:
            benchmark_data (dict, optional): ベンチマークデータ
        
        Returns:
            dict: テスト実行結果
        """
        self.logger.info("Starting performance test")
        
        test_session_id = self._generate_test_session_id()
        start_time = datetime.now()
        
        try:
            # テスト環境初期化
            test_workspace = self.test_env_manager.create_isolated_environment(test_session_id)
            
            # テストデータ準備
            self.data_manager.setup_test_data(test_workspace)
            
            # パフォーマンステスト実行
            performance_result = self._execute_performance_workflow(
                test_workspace, benchmark_data
            )
            
            # パフォーマンス分析
            analysis_result = self.result_analyzer.analyze_performance_metrics(
                performance_result
            )
            
            # 環境クリーンアップ
            if self.config.get('test_environment', {}).get('auto_cleanup', True):
                self.test_env_manager.cleanup_environment(test_workspace)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                'test_session_id': test_session_id,
                'status': 'passed',
                'test_type': 'performance',
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat(),
                'duration_seconds': duration,
                'performance_result': performance_result,
                'analysis_result': analysis_result
            }
            
            self.logger.info(f"Performance test completed successfully: {test_session_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Performance test failed: {str(e)}")
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                'test_session_id': test_session_id,
                'status': 'failed',
                'test_type': 'performance',
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat(),
                'duration_seconds': duration,
                'error': str(e)
            }
    
    def _generate_test_session_id(self):
        """テストセッションID生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"integration_test_{timestamp}_{unique_id}"
    
    def _execute_integrated_workflow(self, test_workspace, test_options):
        """統合ワークフロー実行"""
        # 実装は後で詳細化
        self.logger.info(f"Executing integrated workflow in {test_workspace}")
        return {'status': 'completed', 'steps_executed': []}
    
    def _execute_regression_workflow(self, test_workspace, specific_modules):
        """リグレッションワークフロー実行"""
        # 実装は後で詳細化
        self.logger.info(f"Executing regression workflow for {specific_modules}")
        return {'status': 'completed', 'modules_tested': specific_modules or []}
    
    def _execute_performance_workflow(self, test_workspace, benchmark_data):
        """パフォーマンスワークフロー実行"""
        # 実装は後で詳細化
        self.logger.info("Executing performance workflow")
        return {'status': 'completed', 'metrics': {}} 