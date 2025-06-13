#!/usr/bin/env python3
"""
ObsClippingsManager v3.2.0 - Unit Test Runner
実行コマンド: uv run code/unittest/run_all_tests.py
"""

import unittest
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "code" / "py"))

def discover_and_run_tests():
    """全ユニットテストを検出・実行"""
    
    # テストディスカバリ
    test_dir = Path(__file__).parent
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(test_dir),
        pattern='test_*.py',
        top_level_dir=str(test_dir)
    )
    
    # テスト実行
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        buffer=True
    )
    
    print("=" * 70)
    print("ObsClippingsManager v3.2.0 - Unit Test Execution")
    print("=" * 70)
    
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 70)
    print("TEST EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    # 成功・失敗判定
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    try:
        exit_code = discover_and_run_tests()
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        sys.exit(1) 