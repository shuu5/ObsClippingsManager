#!/usr/bin/env python3
"""
引用文献統一機能のテスト実行スクリプト（実験用）

使用方法:
    python code/playground/run_tests.py
"""

import sys
import unittest
from pathlib import Path

# playground ディレクトリをパスに追加
playground_dir = Path(__file__).parent
sys.path.insert(0, str(playground_dir))

def run_citation_normalizer_tests():
    """引用文献統一機能のテストを実行"""
    print("=" * 60)
    print("引用文献統一機能 テスト実行開始")
    print("=" * 60)
    
    # テストスイートを作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストディレクトリからテストを発見
    test_dir = playground_dir / 'tests'
    discovered_tests = loader.discover(str(test_dir), pattern='test_*.py')
    suite.addTest(discovered_tests)
    
    # テストを実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    print("テスト実行結果サマリー")
    print("=" * 60)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    print(f"スキップ: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.wasSuccessful():
        print("\n✅ すべてのテストが正常に完了しました！")
        return True
    else:
        print("\n❌ テストに失敗がありました。")
        if result.failures:
            print("\n失敗したテスト:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        if result.errors:
            print("\nエラーが発生したテスト:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
        return False

if __name__ == '__main__':
    success = run_citation_normalizer_tests()
    sys.exit(0 if success else 1) 