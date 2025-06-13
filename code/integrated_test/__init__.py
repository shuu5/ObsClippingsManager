"""
統合テストシステム

統合テストシステムパッケージ。
エンドツーエンドテスト実行による品質保証とリグレッション防止を担当。
"""

__version__ = "3.2.0"
__author__ = "ObsClippingsManager Development Team"

from .integrated_test_runner import IntegratedTestRunner
from .test_environment_manager import TestEnvironmentManager
from .test_data_manager import TestDataManager
from .workflow_validator import WorkflowValidator
from .result_analyzer import ResultAnalyzer

__all__ = [
    'IntegratedTestRunner',
    'TestEnvironmentManager',
    'TestDataManager',
    'WorkflowValidator',
    'ResultAnalyzer'
] 