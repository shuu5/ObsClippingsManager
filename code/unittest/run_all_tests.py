#!/usr/bin/env python3
"""
ObsClippingsManager 単体テストランナー

すべてのモジュールの単体テストを実行します。
"""

import unittest
import sys
import os
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
import test_shared_exceptions
import test_citation_fetcher
import test_workflow_manager
import test_rename_mkdir_citation_key
import test_ai_citation_support
import test_ai_tagging
import test_abstract_translation
import test_main_cli

def run_all_tests():
    """全テストを実行する"""
    
    # ログレベルを設定（テスト中のノイズを減らす）
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # テストスイートを作成
    test_suite = unittest.TestSuite()
    
    # 各テストモジュールからテストを追加
    test_modules = [
        test_shared_config_manager,
        test_shared_bibtex_parser,
        test_shared_utils,
        test_shared_logger,
        test_shared_exceptions,
        test_citation_fetcher,
        test_workflow_manager,
        test_rename_mkdir_citation_key,
        test_ai_citation_support,
        test_ai_tagging,
        test_abstract_translation,
        test_main_cli
    ]
    
    for module in test_modules:
        try:
            # モジュール内のすべてのテストクラスを自動検出
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(module)
            test_suite.addTest(suite)
            print(f"✅ モジュール {module.__name__} のテストを追加しました")
        except Exception as e:
            print(f"❌ モジュール {module.__name__} のテスト追加に失敗: {str(e)}")
            raise
    
    # テストランナーを作成して実行
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        descriptions=True,
        failfast=False
    )
    
    print("\n" + "=" * 70)
    print("ObsClippingsManager 単体テスト実行開始")
    print("=" * 70)
    
    # テスト実行
    try:
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
                print(f"\n❌ {test}")
                print("-" * 50)
                print(traceback)
        
        # エラーの詳細
        if result.errors:
            print("\nエラーが発生したテスト:")
            for test, traceback in result.errors:
                print(f"\n❌ {test}")
                print("-" * 50)
                print(traceback)
        
        # 全体的な成功/失敗判定
        if result.wasSuccessful():
            print("\n✅ すべてのテストが正常に完了しました！")
            return 0
        else:
            print("\n❌ 一部のテストが失敗しました。")
            return 1
            
    except Exception as e:
        print(f"\n❌ テスト実行中に予期せぬエラーが発生しました: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 1

def run_specific_module_tests(module_name: str):
    """特定のモジュールのテストのみを実行する"""
    
    module_mapping = {
        'config': test_shared_config_manager,
        'bibtex': test_shared_bibtex_parser,
        'utils': test_shared_utils,
        'citation': test_citation_fetcher,
        'workflow': test_workflow_manager,
        'rename_mkdir_citation_key': test_rename_mkdir_citation_key,
        'ai_citation_support': test_ai_citation_support,
        'ai_tagging': test_ai_tagging,
        'abstract_translation': test_abstract_translation,
        'main_cli': test_main_cli
    }
    
    if module_name not in module_mapping:
        print(f"❌ 未知のモジュール名: {module_name}")
        print(f"利用可能なモジュール: {', '.join(module_mapping.keys())}")
        return 1
    
    try:
        # 指定されたモジュールのテストを実行
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module_mapping[module_name])
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if result.wasSuccessful():
            print(f"\n✅ モジュール {module_name} のテストが正常に完了しました！")
            return 0
        else:
            print(f"\n❌ モジュール {module_name} のテストが失敗しました。")
            return 1
            
    except Exception as e:
        print(f"\n❌ モジュール {module_name} のテスト実行中にエラーが発生しました: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 1

if __name__ == '__main__':
    # 現在のディレクトリをプロジェクトルートに設定
    os.chdir(project_root)
    
    if len(sys.argv) > 1:
        # 特定のモジュールテストを実行
        module_name = sys.argv[1]
        exit_code = run_specific_module_tests(module_name)
    else:
        # 全テストを実行
        exit_code = run_all_tests()
    
    sys.exit(exit_code) 