"""
シンプル統合テストシステム

統合テストシステムパッケージ。
現在実装中のintegrated_workflowをテストデータで実際に実行して動作確認する
最小限の機能に特化した統合テストシステム。
"""

__version__ = "3.2.0"
__author__ = "ObsClippingsManager Development Team"

from .simple_integrated_test_runner import SimpleIntegratedTestRunner

__all__ = [
    'SimpleIntegratedTestRunner'
] 