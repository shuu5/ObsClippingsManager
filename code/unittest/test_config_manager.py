#!/usr/bin/env python3
"""
Unit tests for ConfigManager

ConfigManagerクラスの設定管理システムのテスト
- YAML設定ファイル読み込み
- 環境変数統合
- デフォルト値適用
- 設定階層管理
- パス自動導出
"""

import unittest
import tempfile
import os
from pathlib import Path
import yaml
from unittest.mock import patch, mock_open
import sys

# テストユーティリティのインポート
sys.path.append(str(Path(__file__).parent))
from test_utils import TestEnvironmentManager, TestDataManager

class TestConfigManager(unittest.TestCase):
    """ConfigManagerクラスのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.test_env = TestEnvironmentManager.setup_test_environment("test_config_manager")
        self.test_data_manager = TestDataManager()
        self.config_file = self.test_env / "test_config.yaml"
        
    def tearDown(self):
        """テスト後クリーンアップ"""
        TestEnvironmentManager.cleanup_test_environment(self.test_env)
    
    def test_config_manager_import(self):
        """ConfigManagerクラスのインポートテスト"""
        try:
            # ConfigManagerが正常にインポートできることを確認
            from code.py.modules.shared.config_manager import ConfigManager
            self.assertTrue(True, "ConfigManager successfully imported")
        except ImportError:
            self.fail("ConfigManager should be importable")
    
    def test_load_config_file_exists(self):
        """設定ファイルが存在する場合の読み込みテスト"""
        # テスト用設定ファイル作成
        test_config = {
            'workspace_path': '/test/workspace',
            'api_settings': {
                'request_delay': 2.0,
                'max_retries': 5
            }
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f)
        
        # ConfigManagerが存在すれば以下のテストを実行
        try:
            from code.py.modules.shared.config_manager import ConfigManager
            config_manager = ConfigManager(str(self.config_file))
            
            # 設定が正しく読み込まれることを確認
            self.assertEqual(config_manager.get_workspace_path(), '/test/workspace')
            self.assertEqual(config_manager.config['api_settings']['request_delay'], 2.0)
        except ImportError:
            self.skipTest("ConfigManager not implemented yet")
    
    def test_load_config_file_not_exists(self):
        """設定ファイルが存在しない場合のデフォルト値適用テスト"""
        try:
            from code.py.modules.shared.config_manager import ConfigManager
            config_manager = ConfigManager(str(self.test_env / "nonexistent.yaml"))
            
            # デフォルト値が適用されることを確認
            self.assertEqual(config_manager.get_workspace_path(), '/home/user/ManuscriptsManager')
        except ImportError:
            self.skipTest("ConfigManager not implemented yet")
    
    def test_environment_variable_override(self):
        """環境変数による設定上書きテスト"""
        # テスト用設定ファイル作成
        test_config = {'workspace_path': '/test/workspace'}
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f)
        
        # 環境変数設定
        with patch.dict(os.environ, {'WORKSPACE_PATH': '/env/workspace'}):
            try:
                from code.py.modules.shared.config_manager import ConfigManager
                config_manager = ConfigManager(str(self.config_file))
                
                # 環境変数が優先されることを確認
                self.assertEqual(config_manager.get_workspace_path(), '/env/workspace')
            except ImportError:
                self.skipTest("ConfigManager not implemented yet")
    
    def test_path_derivation(self):
        """パス自動導出機能テスト"""
        test_config = {'workspace_path': '/test/workspace'}
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f)
        
        try:
            from code.py.modules.shared.config_manager import ConfigManager
            config_manager = ConfigManager(str(self.config_file))
            
            # パスが正しく導出されることを確認
            self.assertEqual(config_manager.get_bibtex_file(), '/test/workspace/CurrentManuscript.bib')
            self.assertEqual(config_manager.get_clippings_dir(), '/test/workspace/Clippings')
            self.assertEqual(config_manager.get_output_dir(), '/test/workspace/Clippings')
        except ImportError:
            self.skipTest("ConfigManager not implemented yet")
    
    def test_api_settings_access(self):
        """API設定取得テスト"""
        test_config = {
            'api_settings': {
                'request_delay': 1.5,
                'max_retries': 3,
                'timeout': 30
            }
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f)
        
        try:
            from code.py.modules.shared.config_manager import ConfigManager
            config_manager = ConfigManager(str(self.config_file))
            
            # API設定が正しく取得できることを確認
            self.assertEqual(config_manager.get_api_setting('request_delay'), 1.5)
            self.assertEqual(config_manager.get_api_setting('max_retries'), 3)
            self.assertEqual(config_manager.get_api_setting('timeout'), 30)
        except ImportError:
            self.skipTest("ConfigManager not implemented yet")
    
    def test_ai_settings_access(self):
        """AI設定取得テスト"""
        test_config = {
            'ai_generation': {
                'default_model': 'claude-3-5-haiku-20241022',
                'api_key_env': 'ANTHROPIC_API_KEY',
                'tagger': {
                    'enabled': True,
                    'batch_size': 8
                }
            }
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f)
        
        try:
            from code.py.modules.shared.config_manager import ConfigManager
            config_manager = ConfigManager(str(self.config_file))
            
            # AI設定が正しく取得できることを確認
            self.assertEqual(config_manager.get_ai_setting('default_model'), 'claude-3-5-haiku-20241022')
            self.assertEqual(config_manager.get_ai_setting('tagger', 'enabled'), True)
            self.assertEqual(config_manager.get_ai_setting('tagger', 'batch_size'), 8)
        except ImportError:
            self.skipTest("ConfigManager not implemented yet")
    
    def test_logging_settings_access(self):
        """ログ設定取得テスト"""
        test_config = {
            'logging': {
                'log_file': 'logs/test.log',
                'log_level': 'DEBUG',
                'max_file_size': '5MB',
                'backup_count': 3
            }
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f)
        
        try:
            from code.py.modules.shared.config_manager import ConfigManager
            config_manager = ConfigManager(str(self.config_file))
            
            # ログ設定が正しく取得できることを確認
            self.assertEqual(config_manager.get_logging_setting('log_file'), 'logs/test.log')
            self.assertEqual(config_manager.get_logging_setting('log_level'), 'DEBUG')
            self.assertEqual(config_manager.get_logging_setting('max_file_size'), '5MB')
        except ImportError:
            self.skipTest("ConfigManager not implemented yet")
    
    def test_config_validation(self):
        """設定検証機能テスト"""
        # 無効な設定でテスト
        invalid_config = {
            'workspace_path': None,  # 無効な値
            'api_settings': 'invalid'  # 辞書であるべき
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(invalid_config, f)
        
        try:
            from code.py.modules.shared.config_manager import ConfigManager, ConfigurationError
            
            # 設定検証でエラーが発生することを確認
            with self.assertRaises(ConfigurationError):
                ConfigManager(str(self.config_file))
        except ImportError:
            self.skipTest("ConfigManager not implemented yet")
    
    def test_config_hierarchical_merge(self):
        """設定階層のマージテスト"""
        # 部分的な設定ファイル作成
        partial_config = {
            'workspace_path': '/custom/path',
            'api_settings': {
                'request_delay': 2.0
                # max_retriesは設定せずデフォルト値を使用
            }
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(partial_config, f)
        
        try:
            from code.py.modules.shared.config_manager import ConfigManager
            config_manager = ConfigManager(str(self.config_file))
            
            # カスタム値とデフォルト値が正しくマージされることを確認
            self.assertEqual(config_manager.get_workspace_path(), '/custom/path')
            self.assertEqual(config_manager.get_api_setting('request_delay'), 2.0)
            self.assertEqual(config_manager.get_api_setting('max_retries'), 3)  # デフォルト値
        except ImportError:
            self.skipTest("ConfigManager not implemented yet")
    
    def test_config_update_and_save(self):
        """設定更新・保存機能テスト"""
        try:
            from code.py.modules.shared.config_manager import ConfigManager
            config_manager = ConfigManager(str(self.config_file))
            
            # 設定を更新
            config_manager.update_config('workspace_path', '/updated/path')
            config_manager.save_config()
            
            # 新しいインスタンスで読み込んで確認
            new_config_manager = ConfigManager(str(self.config_file))
            self.assertEqual(new_config_manager.get_workspace_path(), '/updated/path')
        except ImportError:
            self.skipTest("ConfigManager not implemented yet")


if __name__ == '__main__':
    unittest.main() 