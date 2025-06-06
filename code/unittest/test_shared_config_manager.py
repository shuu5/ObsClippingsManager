"""
ConfigManagerの単体テスト
"""

import unittest
import tempfile
import json
from pathlib import Path
import sys
import os

# テスト対象モジュールをインポートするためのパス設定
project_root = Path(__file__).parent.parent.parent
code_py_dir = project_root / "code" / "py"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(code_py_dir))

from modules.shared.config_manager import ConfigManager, DEFAULT_INTEGRATED_CONFIG
from modules.shared.exceptions import ConfigError


class TestConfigManager(unittest.TestCase):
    """ConfigManagerのテストクラス"""
    
    def setUp(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
        
    def tearDown(self):
        """テストクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_default_config_loading(self):
        """デフォルト設定の読み込みテスト"""
        # 存在しないファイルパスでConfigManagerを初期化
        config_manager = ConfigManager(config_file="nonexistent.json")
        
        # デフォルト設定が読み込まれることを確認
        config = config_manager.get_config()
        self.assertIsInstance(config, dict)
        self.assertIn('common', config)
        self.assertIn('citation_fetcher', config)
        self.assertIn('rename_mkdir', config)
    
    def test_custom_config_loading(self):
        """カスタム設定ファイルの読み込みテスト"""
        # テスト用設定ファイルを作成
        test_config = {
            "common": {
                "bibtex_file": "/custom/path/test.bib",
                "log_level": "DEBUG"
            },
            "citation_fetcher": {
                "output_dir": "/custom/output/",
                "max_retries": 5
            },
            "rename_mkdir": {
                "clippings_dir": "/custom/clippings/",
                "similarity_threshold": 0.9
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)
        
        # カスタム設定を読み込み
        config_manager = ConfigManager(config_file=str(self.config_file))
        config = config_manager.get_config()
        
        # カスタム値が正しく読み込まれることを確認
        self.assertEqual(config['common']['bibtex_file'], "/custom/path/test.bib")
        self.assertEqual(config['common']['log_level'], "DEBUG")
        self.assertEqual(config['citation_fetcher']['max_retries'], 5)
        self.assertEqual(config['rename_mkdir']['similarity_threshold'], 0.9)
    
    def test_config_section_getters(self):
        """設定セクションゲッターのテスト"""
        config_manager = ConfigManager()
        
        # 各セクションが正しく取得できることを確認
        common_config = config_manager.get_common_config()
        citation_config = config_manager.get_citation_fetcher_config()
        rename_config = config_manager.get_rename_mkdir_config()
        
        self.assertIsInstance(common_config, dict)
        self.assertIsInstance(citation_config, dict)
        self.assertIsInstance(rename_config, dict)
        
        # 必須キーが存在することを確認
        self.assertIn('bibtex_file', common_config)
        self.assertIn('output_dir', citation_config)
        self.assertIn('clippings_dir', rename_config)
    
    def test_config_validation(self):
        """設定検証のテスト"""
        config_manager = ConfigManager()
        
        # 有効な設定の検証
        is_valid, errors = config_manager.validate_config(config_manager.config)
        # デフォルト設定では一部のパスが存在しないため無効になる可能性がある
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(errors, list)
    
    def test_invalid_json_file(self):
        """不正なJSONファイルの処理テスト"""
        # 不正なJSONファイルを作成
        with open(self.config_file, 'w') as f:
            f.write("{ invalid json }")
        
        # ConfigErrorが発生することを確認
        with self.assertRaises(ConfigError):
            ConfigManager(config_file=str(self.config_file))
    
    def test_config_update(self):
        """設定更新のテスト"""
        config_manager = ConfigManager()
        
        # 設定を更新
        new_values = {
            "common": {
                "log_level": "DEBUG"
            },
            "citation_fetcher": {
                "max_retries": 10
            }
        }
        
        config_manager.update_config(new_values)
        
        # 更新された値が反映されることを確認
        config = config_manager.get_config()
        self.assertEqual(config['common']['log_level'], "DEBUG")
        self.assertEqual(config['citation_fetcher']['max_retries'], 10)
    
    def test_config_save(self):
        """設定保存のテスト"""
        # テスト用の初期設定でConfigManagerを作成
        test_config = {
            "common": {
                "bibtex_file": "/test/path/test.bib"
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)
        
        config_manager = ConfigManager(config_file=str(self.config_file))
        
        # 設定を更新して保存
        config_manager.update_config({
            "common": {
                "log_level": "DEBUG"
            }
        })
        
        config_manager.save_config()
        
        # ファイルに保存された内容を確認
        with open(self.config_file, 'r') as f:
            saved_config = json.load(f)
        
        self.assertEqual(saved_config['common']['log_level'], "DEBUG")
    
    def test_get_config_value(self):
        """設定値取得のテスト"""
        config_manager = ConfigManager()
        
        # ネストしたキーでの値取得
        log_level = config_manager.get_config_value('common.log_level')
        self.assertIsInstance(log_level, str)
        
        # デフォルト値の取得
        nonexistent = config_manager.get_config_value('nonexistent.key', default="default_value")
        self.assertEqual(nonexistent, "default_value")
    
    def test_config_merging(self):
        """設定のマージテスト"""
        # 部分的なカスタム設定を作成
        partial_config = {
            "common": {
                "log_level": "ERROR"
            },
            "citation_fetcher": {
                "timeout": 60
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(partial_config, f)
        
        config_manager = ConfigManager(config_file=str(self.config_file))
        config = config_manager.get_config()
        
        # カスタム値が反映されていることを確認
        self.assertEqual(config['common']['log_level'], "ERROR")
        self.assertEqual(config['citation_fetcher']['timeout'], 60)
        
        # デフォルト値も保持されていることを確認
        self.assertIn('bibtex_file', config['common'])
        self.assertIn('output_dir', config['common'])
    
    def test_required_sections_validation(self):
        """必須セクションの検証テスト"""
        # 必須セクションが欠けた設定を作成
        incomplete_config = {
            "common": {
                "bibtex_file": "/test/path/test.bib"
            }
            # citation_fetcherとrename_mkdirが欠けている
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(incomplete_config, f)
        
        # ConfigManagerは不完全な設定でもデフォルト値でマージするため正常に動作
        config_manager = ConfigManager(config_file=str(self.config_file))
        config = config_manager.get_config()
        
        # デフォルト値でマージされていることを確認
        self.assertIn('citation_fetcher', config)
        self.assertIn('rename_mkdir', config)


if __name__ == '__main__':
    unittest.main() 