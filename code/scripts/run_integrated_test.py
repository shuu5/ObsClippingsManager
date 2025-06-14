#!/usr/bin/env python3
"""シンプル統合テスト実行スクリプト"""

import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from code.py.modules.shared_modules.config_manager import ConfigManager
from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
from code.integrated_test.simple_integrated_test_runner import SimpleIntegratedTestRunner

def main():
    """統合テスト実行"""
    try:
        # 設定とログ初期化
        config_manager = ConfigManager()
        integrated_logger = IntegratedLogger(config_manager)
        
        # 統合テスト実行
        test_runner = SimpleIntegratedTestRunner(config_manager, integrated_logger)
        success = test_runner.run_test()
        
        if success:
            print("✅ 統合テスト成功")
            print("📁 結果確認: test_output/latest/")
            return 0
        else:
            print("❌ 統合テスト失敗") 
            print("📁 エラー詳細: test_output/latest/test_result.yaml")
            return 1
            
    except Exception as e:
        print(f"❌ 統合テスト実行エラー: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 