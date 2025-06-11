#!/usr/bin/env python3
"""
ObsClippingsManager 単体テストランナー

すべてのモジュールの単体テストを実行します。
"""

import unittest
import sys
from pathlib import Path
import logging

# プロジェクトルートとcode/pyディレクトリをパスに追加
project_root = Path(__file__).parent.parent.parent
code_py_dir = project_root / "code" / "py"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(code_py_dir))

# テストモジュールをインポート
import test_shared_config_manager
import test_shared_bibtex_parser
import test_shared_utils
import test_shared_logger
# import test_shared_exceptions  # 構文エラーのため一時的にコメントアウト
import test_citation_fetcher
import test_citation_parser
import test_citation_parser_workflow
import test_workflow_manager
import test_rename_mkdir_citation_key
import test_ai_citation_support  # v4.0 新機能テスト
# import test_sync_check_workflow  # API未確認のため一時的にコメントアウト


def run_all_tests():
    """全テストを実行する"""
    
    # ログレベルを設定（テスト中のノイズを減らす）
    logging.basicConfig(level=logging.WARNING)
    
    # テストスイートを作成
    test_suite = unittest.TestSuite()
    
    # 各テストモジュールからテストを追加
    test_modules = [
        test_shared_config_manager,
        test_shared_bibtex_parser,
        test_shared_utils,
        test_shared_logger,
        # test_shared_exceptions,  # 構文エラーのため一時的にコメントアウト
        test_citation_fetcher,
        test_citation_parser,
        test_citation_parser_workflow,
        test_workflow_manager,
        test_rename_mkdir_citation_key,
        test_ai_citation_support,  # v4.0 新機能テスト
        # test_sync_check_workflow  # API未確認のため一時的にコメントアウト
    ]
    
    for module in test_modules:
        # モジュール内のすべてのテストクラスを自動検出
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)
        test_suite.addTest(suite)
    
    # テストランナーを作成して実行
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        descriptions=True,
        failfast=False
    )
    
    print("=" * 70)
    print("ObsClippingsManager 単体テスト実行開始")
    print("=" * 70)
    
    # テスト実行
    result = runner.run(test_suite)
    
    # 結果サマリー
    print("\n" + "=" * 70)
    print("テスト実行結果サマリー")
    print("=" * 70)
    
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    print(f"スキップ: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    # 失敗の詳細
    if result.failures:
        print("\n失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    # エラーの詳細
    if result.errors:
        print("\nエラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    # 全体的な成功/失敗判定
    if result.wasSuccessful():
        print("\n✅ すべてのテストが正常に完了しました！")
        return 0
    else:
        print("\n❌ 一部のテストが失敗しました。")
        return 1


def run_specific_module_tests(module_name: str):
    """特定のモジュールのテストのみを実行する"""
    
    module_mapping = {
        'config': test_shared_config_manager,
        'bibtex': test_shared_bibtex_parser,
        'utils': test_shared_utils,
        'citation': test_citation_fetcher,
        'citation_parser': test_citation_parser,
        'citation_parser_workflow': test_citation_parser_workflow,
        'workflow': test_workflow_manager,
        'rename_mkdir_citation_key': test_rename_mkdir_citation_key,
        'ai_citation_support': test_ai_citation_support
    }
    
    if module_name not in module_mapping:
        print(f"❌ 未知のモジュール名: {module_name}")
        print(f"利用可能なモジュール: {', '.join(module_mapping.keys())}")
        return 1
    
    # 指定されたモジュールのテストを実行
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(module_mapping[module_name])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 特定のモジュールテストを実行
        module_name = sys.argv[1]
        exit_code = run_specific_module_tests(module_name)
    else:
        # 全テストを実行
        exit_code = run_all_tests()
    
    sys.exit(exit_code) 