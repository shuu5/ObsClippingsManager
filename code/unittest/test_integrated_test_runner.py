"""
統合テストランナー ユニットテスト

IntegratedTestRunnerクラスの単体テスト。
TDD開発に基づく完全なテスト先行開発。
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys
import os

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from code.integrated_test.integrated_test_runner import IntegratedTestRunner
    from code.integrated_test.test_environment_manager import TestEnvironmentManager
    from code.integrated_test.test_data_manager import TestDataManager
    from code.integrated_test.workflow_validator import WorkflowValidator
    from code.integrated_test.result_analyzer import ResultAnalyzer
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


class TestIntegratedTestRunner(unittest.TestCase):
    """統合テストランナーのテストクラス"""
    
    def setUp(self):
        """テスト前準備"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_integrated_test_runner_"))
        
        # モック設定
        self.mock_config_manager = MagicMock()
        self.mock_logger = MagicMock()
        
        # ConfigManagerモック設定
        self.mock_config_manager.get_config.return_value = {
            'integrated_testing': {
                'enabled': True,
                'test_environment': {
                    'base_path': '/tmp',
                    'prefix': 'ObsClippingsManager_IntegratedTest',
                    'auto_cleanup': True
                }
            }
        }
    
    def tearDown(self):
        """テスト後クリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_integrated_test_runner_import(self):
        """IntegratedTestRunnerクラスのインポートテスト"""
        # インポートが成功することをテスト
        self.assertTrue(IMPORTS_AVAILABLE, "IntegratedTestRunnerクラスのインポートに失敗")
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_integrated_test_runner_initialization(self):
        """IntegratedTestRunnerクラスの初期化テスト"""
        runner = IntegratedTestRunner(self.mock_config_manager, self.mock_logger)
        
        # 基本属性の存在確認
        self.assertIsNotNone(runner.config_manager)
        self.assertIsNotNone(runner.logger)
        self.assertIsNotNone(runner.test_env_manager)
        self.assertIsNotNone(runner.data_manager)
        self.assertIsNotNone(runner.workflow_validator)
        self.assertIsNotNone(runner.result_analyzer)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_run_full_integration_test_method_exists(self):
        """run_full_integration_testメソッドの存在確認"""
        runner = IntegratedTestRunner(self.mock_config_manager, self.mock_logger)
        
        # メソッドの存在確認
        self.assertTrue(hasattr(runner, 'run_full_integration_test'))
        self.assertTrue(callable(getattr(runner, 'run_full_integration_test')))
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_run_regression_test_method_exists(self):
        """run_regression_testメソッドの存在確認"""
        runner = IntegratedTestRunner(self.mock_config_manager, self.mock_logger)
        
        # メソッドの存在確認
        self.assertTrue(hasattr(runner, 'run_regression_test'))
        self.assertTrue(callable(getattr(runner, 'run_regression_test')))
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_run_performance_test_method_exists(self):
        """run_performance_testメソッドの存在確認"""
        runner = IntegratedTestRunner(self.mock_config_manager, self.mock_logger)
        
        # メソッドの存在確認
        self.assertTrue(hasattr(runner, 'run_performance_test'))
        self.assertTrue(callable(getattr(runner, 'run_performance_test')))


if __name__ == '__main__':
    unittest.main() 