"""
テストデータ管理システム ユニットテスト

TestDataManagerクラスの単体テスト。
TDD開発に基づく完全なテスト先行開発。
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys
import os

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from code.integrated_test.test_data_manager import TestDataManager
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


class TestTestDataManager(unittest.TestCase):
    """TestDataManagerクラスのユニットテスト"""
    
    def setUp(self):
        """テスト前準備"""
        # テスト用設定・ログの準備
        self.mock_config_manager = MagicMock()
        self.mock_logger = MagicMock()
        
        # get_loggerメソッドのモック設定（テスト用ロガーを返すよう設定）
        self.mock_test_logger = MagicMock()
        self.mock_logger.get_logger.return_value = self.mock_test_logger
        
        # デフォルト設定値
        self.mock_config_manager.get_config.return_value = {
            'integrated_testing': {
                'test_data': {
                    'master_path': 'code/test_data_master',
                    'backup_original': True,
                    'validation_enabled': True
                }
            }
        }
        
        # テスト環境ディレクトリ作成
        self.test_workspace = Path(tempfile.mkdtemp(prefix="test_data_manager_"))
        self.test_master_data = Path(tempfile.mkdtemp(prefix="test_master_data_"))
        
        # テストマスターデータ作成
        self._setup_test_master_data()
        
    def tearDown(self):
        """テスト後クリーンアップ"""
        if self.test_workspace.exists():
            shutil.rmtree(self.test_workspace, ignore_errors=True)
        if self.test_master_data.exists():
            shutil.rmtree(self.test_master_data, ignore_errors=True)
    
    def _setup_test_master_data(self):
        """テスト用マスターデータ作成"""
        # CurrentManuscript.bib作成
        bib_content = """@article{test2023,
  title = {Test Paper Title},
  author = {Test Author},
  year = {2023},
  journal = {Test Journal}
}

@article{sample2024,
  title = {Sample Paper Title},
  author = {Sample Author},
  year = {2024},
  journal = {Sample Journal}
}
"""
        (self.test_master_data / "CurrentManuscript.bib").write_text(bib_content, encoding='utf-8')
        
        # Clippingsディレクトリとファイル作成
        clippings_dir = self.test_master_data / "Clippings"
        clippings_dir.mkdir()
        
        test_md_content = """---
citation_key: test2023
processing_status:
  organize: pending
workflow_version: '3.2'
---

# Test Paper

Test content here.
"""
        (clippings_dir / "test_paper.md").write_text(test_md_content, encoding='utf-8')
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_test_data_manager_import(self):
        """TestDataManagerクラスのインポートテスト"""
        self.assertTrue(IMPORTS_AVAILABLE, "TestDataManagerクラスをインポートできること")
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_test_data_manager_initialization(self):
        """TestDataManagerクラスの初期化テスト"""
        manager = TestDataManager(self.mock_config_manager, self.mock_logger)
        
        # 初期化確認
        self.assertEqual(manager.config_manager, self.mock_config_manager)
        self.assertEqual(manager.logger, self.mock_test_logger)  # get_logger()の戻り値と比較
        
        # get_loggerが適切な引数で呼ばれていることを確認
        self.mock_logger.get_logger.assert_called_with("test_data_manager")
        
        # 初期化ログが出力されていることを確認
        self.mock_test_logger.info.assert_called_with("TestDataManager initialized")
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_setup_test_data_method_exists(self):
        """setup_test_dataメソッドの存在確認"""
        manager = TestDataManager(self.mock_config_manager, self.mock_logger)
        self.assertTrue(hasattr(manager, 'setup_test_data'), "setup_test_dataメソッドが存在すること")
        self.assertTrue(callable(getattr(manager, 'setup_test_data')), "setup_test_dataメソッドが呼び出し可能であること")
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_setup_test_data_success(self):
        """テストデータセットアップ成功テスト"""
        # マスターパスをテスト用に変更
        self.mock_config_manager.get_config.return_value = {
            'integrated_testing': {
                'test_data': {
                    'master_path': str(self.test_master_data),
                    'backup_original': True,
                    'validation_enabled': True
                }
            }
        }
        
        manager = TestDataManager(self.mock_config_manager, self.mock_logger)
        manager.setup_test_data(self.test_workspace)
        
        # ファイルがコピーされていることを確認
        self.assertTrue((self.test_workspace / "CurrentManuscript.bib").exists(), "BibTeXファイルがコピーされること")
        self.assertTrue((self.test_workspace / "Clippings").exists(), "Clippingsディレクトリがコピーされること")
        self.assertTrue((self.test_workspace / "Clippings" / "test_paper.md").exists(), "Markdownファイルがコピーされること")
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_setup_test_data_with_backup(self):
        """バックアップ付きテストデータセットアップテスト"""
        # 既存データを作成
        (self.test_workspace / "CurrentManuscript.bib").write_text("existing content", encoding='utf-8')
        existing_clippings = self.test_workspace / "Clippings"
        existing_clippings.mkdir()
        (existing_clippings / "existing.md").write_text("existing markdown", encoding='utf-8')
        
        # マスターパスをテスト用に変更
        self.mock_config_manager.get_config.return_value = {
            'integrated_testing': {
                'test_data': {
                    'master_path': str(self.test_master_data),
                    'backup_original': True,
                    'validation_enabled': True
                }
            }
        }
        
        manager = TestDataManager(self.mock_config_manager, self.mock_logger)
        manager.setup_test_data(self.test_workspace)
        
        # バックアップが作成されていることを確認
        backup_dir = self.test_workspace / "backups" / "original"
        self.assertTrue(backup_dir.exists(), "バックアップディレクトリが作成されること")
        self.assertTrue((backup_dir / "CurrentManuscript.bib").exists(), "BibTeXファイルのバックアップが作成されること")
        self.assertTrue((backup_dir / "Clippings").exists(), "Clippingsディレクトリのバックアップが作成されること")
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_setup_test_data_master_not_found(self):
        """マスターデータが見つからない場合のエラーテスト"""
        # 存在しないマスターパスを設定
        self.mock_config_manager.get_config.return_value = {
            'integrated_testing': {
                'test_data': {
                    'master_path': '/nonexistent/path',
                    'backup_original': True,
                    'validation_enabled': True
                }
            }
        }
        
        manager = TestDataManager(self.mock_config_manager, self.mock_logger)
        
        with self.assertRaises(FileNotFoundError):
            manager.setup_test_data(self.test_workspace)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_get_test_data_summary_method_exists(self):
        """get_test_data_summaryメソッドの存在確認"""
        manager = TestDataManager(self.mock_config_manager, self.mock_logger)
        self.assertTrue(hasattr(manager, 'get_test_data_summary'), "get_test_data_summaryメソッドが存在すること")
        self.assertTrue(callable(getattr(manager, 'get_test_data_summary')), "get_test_data_summaryメソッドが呼び出し可能であること")
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_get_test_data_summary_success(self):
        """テストデータ概要取得成功テスト"""
        # テストデータを準備
        (self.test_workspace / "CurrentManuscript.bib").write_text("@article{test,title={Test}}", encoding='utf-8')
        clippings_dir = self.test_workspace / "Clippings"
        clippings_dir.mkdir()
        (clippings_dir / "test1.md").write_text("test content 1", encoding='utf-8')
        (clippings_dir / "test2.md").write_text("test content 2", encoding='utf-8')
        
        manager = TestDataManager(self.mock_config_manager, self.mock_logger)
        summary = manager.get_test_data_summary(self.test_workspace)
        
        # 概要の確認
        self.assertIn('workspace_path', summary)
        self.assertIn('has_bibtex', summary)
        self.assertIn('bibtex_entries', summary)
        self.assertIn('has_clippings', summary)
        self.assertIn('clippings_count', summary)
        self.assertIn('markdown_files', summary)
        
        self.assertTrue(summary['has_bibtex'])
        self.assertEqual(summary['bibtex_entries'], 1)
        self.assertTrue(summary['has_clippings'])
        self.assertEqual(summary['clippings_count'], 2)
        self.assertIn('test1.md', summary['markdown_files'])
        self.assertIn('test2.md', summary['markdown_files'])
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_setup_test_data_validation_disabled(self):
        """バリデーション無効化時のテストデータセットアップテスト"""
        # マスターパスをテスト用に変更（バリデーション無効）
        self.mock_config_manager.get_config.return_value = {
            'integrated_testing': {
                'test_data': {
                    'master_path': str(self.test_master_data),
                    'backup_original': False,
                    'validation_enabled': False
                }
            }
        }
        
        manager = TestDataManager(self.mock_config_manager, self.mock_logger)
        manager.setup_test_data(self.test_workspace)
        
        # ファイルがコピーされていることを確認（バリデーションなし）
        self.assertTrue((self.test_workspace / "CurrentManuscript.bib").exists(), "BibTeXファイルがコピーされること")
        self.assertTrue((self.test_workspace / "Clippings").exists(), "Clippingsディレクトリがコピーされること")
        
        # バックアップが作成されていないことを確認
        backup_dir = self.test_workspace / "backups"
        self.assertFalse(backup_dir.exists(), "バックアップディレクトリが作成されないこと")
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_setup_test_data_validation_failure(self):
        """バリデーション失敗時のエラーテスト"""
        # 不正なマスターデータを作成（空のBibTeXファイル）
        invalid_master = Path(tempfile.mkdtemp(prefix="invalid_master_"))
        (invalid_master / "CurrentManuscript.bib").write_text("", encoding='utf-8')  # 空ファイル
        clippings_dir = invalid_master / "Clippings"
        clippings_dir.mkdir()
        # Clippingsディレクトリは空
        
        self.mock_config_manager.get_config.return_value = {
            'integrated_testing': {
                'test_data': {
                    'master_path': str(invalid_master),
                    'backup_original': False,
                    'validation_enabled': True
                }
            }
        }
        
        manager = TestDataManager(self.mock_config_manager, self.mock_logger)
        
        with self.assertRaises(ValueError):
            manager.setup_test_data(self.test_workspace)
        
        # クリーンアップ
        shutil.rmtree(invalid_master, ignore_errors=True)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_get_test_data_summary_empty_workspace(self):
        """空のワークスペースでの概要取得テスト"""
        manager = TestDataManager(self.mock_config_manager, self.mock_logger)
        summary = manager.get_test_data_summary(self.test_workspace)
        
        # 空の状態の確認
        self.assertFalse(summary['has_bibtex'])
        self.assertEqual(summary['bibtex_entries'], 0)
        self.assertFalse(summary['has_clippings'])
        self.assertEqual(summary['clippings_count'], 0)
        self.assertEqual(summary['markdown_files'], [])
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_private_methods_exist(self):
        """プライベートメソッドの存在確認"""
        manager = TestDataManager(self.mock_config_manager, self.mock_logger)
        
        # プライベートメソッドの存在確認
        self.assertTrue(hasattr(manager, '_backup_original_data'), "_backup_original_dataメソッドが存在すること")
        self.assertTrue(hasattr(manager, '_copy_test_data'), "_copy_test_dataメソッドが存在すること")
        self.assertTrue(hasattr(manager, '_validate_test_data'), "_validate_test_dataメソッドが存在すること")
        
        # 呼び出し可能性確認
        self.assertTrue(callable(getattr(manager, '_backup_original_data')), "_backup_original_dataメソッドが呼び出し可能であること")
        self.assertTrue(callable(getattr(manager, '_copy_test_data')), "_copy_test_dataメソッドが呼び出し可能であること")
        self.assertTrue(callable(getattr(manager, '_validate_test_data')), "_validate_test_dataメソッドが呼び出し可能であること")


if __name__ == '__main__':
    unittest.main() 