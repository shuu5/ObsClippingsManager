#!/usr/bin/env python3
"""シンプル統合テスト実行スクリプト"""

import sys
import argparse
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
from code.integrated_test.simple_integrated_test_runner import SimpleIntegratedTestRunner
from code.integrated_test.ai_feature_controller import AIFeatureController


def parse_arguments():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(description="統合テスト実行")
    
    # AI機能制御オプション（開発用）
    ai_group = parser.add_argument_group('AI機能制御オプション（開発用）')
    ai_group.add_argument('--disable-ai', action='store_true',
                         help='すべてのAI機能を無効化（API利用料金削減）')
    ai_group.add_argument('--disable-tagger', action='store_true',
                         help='enhanced-tagger機能を無効化')
    ai_group.add_argument('--disable-translate', action='store_true',
                         help='enhanced-translate機能を無効化')
    ai_group.add_argument('--disable-ochiai', action='store_true',
                         help='ochiai-format機能を無効化')
    
    # 特定AI機能のみ有効化オプション
    exclusive_group = ai_group.add_mutually_exclusive_group()
    exclusive_group.add_argument('--enable-only-tagger', action='store_true',
                                help='enhanced-tagger機能のみ有効化')
    exclusive_group.add_argument('--enable-only-translate', action='store_true',
                                help='enhanced-translate機能のみ有効化')
    exclusive_group.add_argument('--enable-only-ochiai', action='store_true',
                                help='ochiai-format機能のみ有効化')
    
    return parser.parse_args()


def main():
    """統合テスト実行"""
    try:
        # コマンドライン引数解析
        args = parse_arguments()
        
        # AI機能制御インスタンス作成
        ai_controller = AIFeatureController(args)
        
        # 設定とログ初期化
        config_manager = ConfigManager()
        integrated_logger = IntegratedLogger(config_manager)
        
        # 実行モード表示
        logger = integrated_logger.get_logger("integrated_test")
        logger.info(ai_controller.get_mode_description())
        logger.info(f"設定: {ai_controller.get_summary()}")
        
        if ai_controller.has_api_cost_savings():
            logger.info("💰 API利用料金削減モードが有効です")
        
        # 統合テスト実行
        test_runner = SimpleIntegratedTestRunner(config_manager, integrated_logger, ai_controller)
        success = test_runner.run_test()
        
        if success:
            print("✅ 統合テスト成功")
            print("📁 結果確認: test_output/latest/")
            return 0
        else:
            print("❌ 統合テスト失敗") 
            print("📁 エラー詳細: test_output/latest/test_result.yaml")
            return 1
            
    except ValueError as e:
        print(f"❌ 引数エラー: {e}")
        return 1
    except Exception as e:
        print(f"❌ 統合テスト実行エラー: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 