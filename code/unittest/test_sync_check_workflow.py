"""
同期チェックワークフローのテスト

ObsClippingsManager Sync Check Workflow のテストスイート
"""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# テスト対象モジュールのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'py'))

from modules.workflows.sync_check_workflow import SyncCheckWorkflow
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger


class TestSyncCheckWorkflow(unittest.TestCase):
    """同期チェックワークフローのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        
        # モック設定
        self.mock_config = Mock(spec=ConfigManager)
        self.mock_logger = Mock(spec=IntegratedLogger)
        
        # 設定のモック（実際のConfigManagerメソッドに合わせる）
        self.mock_config.get_sync_check_config.return_value = {
            'bibtex_file': os.path.join(self.temp_dir, "test.bib"),
            'clippings_dir': os.path.join(self.temp_dir, "clippings"),
            'show_missing_in_clippings': True,
            'show_missing_in_bib': True,
            'show_clickable_links': True,
            'show_doi_statistics': True,
            'max_displayed_files': 10,
            'sort_by_year': True,
            'doi_required_warning': True
        }
        
        # ロガーのモック
        mock_child_logger = Mock()
        self.mock_logger.get_logger.return_value = mock_child_logger
        
        # テスト用ディレクトリ作成
        os.makedirs(os.path.join(self.temp_dir, "clippings"), exist_ok=True)
        
        # ワークフローインスタンス作成
        self.workflow = SyncCheckWorkflow(self.mock_config, self.mock_logger)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_bibtex_file(self, entries):
        """テスト用BibTeXファイルを作成"""
        bibtex_file = os.path.join(self.temp_dir, "test.bib")
        with open(bibtex_file, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(entry + "\n\n")
        return bibtex_file
    
    def create_test_clippings_directory(self, dirname, md_files=None):
        """テスト用Clippingsディレクトリを作成"""
        clippings_dir = os.path.join(self.temp_dir, "clippings")
        dir_path = os.path.join(clippings_dir, dirname)
        os.makedirs(dir_path, exist_ok=True)
        
        if md_files:
            for md_file in md_files:
                file_path = os.path.join(dir_path, md_file)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {md_file}\n\nTest content for {md_file}")
        
        return dir_path


class TestSyncCheckWorkflowInitialization(TestSyncCheckWorkflow):
    """ワークフロー初期化のテスト"""
    
    def test_workflow_initialization(self):
        """ワークフロー初期化のテスト"""
        self.assertIsNotNone(self.workflow)
        self.assertEqual(self.workflow.config_manager, self.mock_config)
        self.assertEqual(self.workflow.logger, self.mock_logger.get_logger.return_value)
    
    def test_configuration_loading(self):
        """設定読み込みのテスト"""
        # 設定が正しく読み込まれることを確認
        self.mock_config.get_sync_check_config.assert_called_once()
        
        # 設定値の確認
        config = self.workflow.config
        self.assertTrue(config['show_missing_in_clippings'])
        self.assertTrue(config['show_missing_in_bib'])
        self.assertTrue(config['show_clickable_links'])


class TestSyncCheckExecution(TestSyncCheckWorkflow):
    """同期チェック実行のテスト"""
    
    def test_execute_basic_sync_check(self):
        """基本的な同期チェック実行のテスト"""
        # テストデータ準備
        bibtex_entries = [
            "@article{smith2023,\n  title={Test Paper},\n  author={Smith, John},\n  doi={10.1000/test}\n}",
            "@article{doe2023,\n  title={Another Paper},\n  author={Doe, Jane},\n  doi={10.1000/another}\n}"
        ]
        
        self.create_test_bibtex_file(bibtex_entries)
        self.create_test_clippings_directory("smith2023", ["smith2023.md"])
        # doe2023ディレクトリは作成しない（意図的に不一致を作成）
        
        # 同期チェック実行
        with patch.object(self.workflow, '_parse_bibtex_file') as mock_parse:
            mock_parse.return_value = {
                'smith2023': {
                    'title': 'Test Paper',
                    'author': 'Smith, John',
                    'doi': '10.1000/test'
                },
                'doe2023': {
                    'title': 'Another Paper', 
                    'author': 'Doe, Jane',
                    'doi': '10.1000/another'
                }
            }
            
            success, result = self.workflow.execute()
        
        # 結果確認
        self.assertTrue(success)
        self.assertIn('missing_in_clippings', result)
        self.assertIn('missing_in_bib', result)
        self.assertIn('statistics', result)
    
    def test_execute_with_missing_files(self):
        """ファイル不足がある場合の同期チェックテスト"""
        # BibTeXエントリのみ存在、対応するClippingsディレクトリなし
        bibtex_entries = [
            "@article{missing2023,\n  title={Missing File},\n  author={Author, Test},\n  doi={10.1000/missing}\n}"
        ]
        
        self.create_test_bibtex_file(bibtex_entries)
        # Clippingsディレクトリは作成しない
        
        with patch.object(self.workflow, '_parse_bibtex_file') as mock_parse:
            mock_parse.return_value = {
                'missing2023': {
                    'title': 'Missing File',
                    'author': 'Author, Test',
                    'doi': '10.1000/missing'
                }
            }
            
            success, result = self.workflow.execute()
        
        self.assertTrue(success)
        self.assertIn('missing_in_clippings', result)
        self.assertGreater(len(result['missing_in_clippings']), 0)
    
    def test_execute_with_orphaned_files(self):
        """孤立ファイルがある場合の同期チェックテスト"""
        # Clippingsディレクトリのみ存在、対応するBibTeXエントリなし
        self.create_test_bibtex_file([])  # 空のBibTeXファイル
        self.create_test_clippings_directory("orphaned2023", ["orphaned2023.md"])
        
        with patch.object(self.workflow, '_parse_bibtex_file') as mock_parse:
            mock_parse.return_value = {}  # 空のBibTeX項目
            
            success, result = self.workflow.execute()
        
        self.assertTrue(success)
        self.assertIn('missing_in_bib', result)
        self.assertGreater(len(result['missing_in_bib']), 0)
    
    def test_execute_dry_run(self):
        """ドライラン実行のテスト"""
        # テストデータ準備
        bibtex_entries = [
            "@article{dryrun2023,\n  title={Dry Run Test},\n  author={Dry, Run},\n  doi={10.1000/dryrun}\n}"
        ]
        
        self.create_test_bibtex_file(bibtex_entries)
        
        with patch.object(self.workflow, '_parse_bibtex_file') as mock_parse:
            mock_parse.return_value = {
                'dryrun2023': {
                    'title': 'Dry Run Test',
                    'author': 'Dry, Run',
                    'doi': '10.1000/dryrun'
                }
            }
            
            success, result = self.workflow.execute(dry_run=True)
        
        self.assertTrue(success)
        self.assertIn('execution_options', result)
        self.assertTrue(result['execution_options'].get('dry_run', False))


class TestSyncCheckMethods(TestSyncCheckWorkflow):
    """同期チェック個別メソッドのテスト"""
    
    def test_check_bib_to_clippings(self):
        """BibTeX→Clippingsチェックのテスト"""
        bib_entries = {
            'existing2023': {
                'title': 'Existing Paper',
                'author': 'Author, Test',
                'doi': '10.1000/existing'
            },
            'missing2023': {
                'title': 'Missing Paper',
                'author': 'Author, Missing',
                'doi': '10.1000/missing'
            }
        }
        
        clippings_dirs = ['existing2023']  # missing2023は存在しない
        
        missing = self.workflow.check_bib_to_clippings(bib_entries, clippings_dirs)
        
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]['citation_key'], 'missing2023')
        self.assertEqual(missing[0]['title'], 'Missing Paper')
        self.assertEqual(missing[0]['doi'], '10.1000/missing')
    
    def test_check_clippings_to_bib(self):
        """Clippings→BibTeXチェックのテスト"""
        bib_entries = {
            'existing2023': {
                'title': 'Existing Paper',
                'author': 'Author, Test',
                'doi': '10.1000/existing'
            }
        }
        
        clippings_dirs = ['existing2023', 'orphaned2023']  # orphaned2023はBibTeXにない
        
        # _get_markdown_files_in_directoryメソッドをモック
        with patch.object(self.workflow, '_get_markdown_files_in_directory') as mock_get_md:
            mock_get_md.return_value = ['orphaned2023.md']
            
            orphaned = self.workflow.check_clippings_to_bib(bib_entries, clippings_dirs)
        
        self.assertEqual(len(orphaned), 1)
        self.assertEqual(orphaned[0]['directory_name'], 'orphaned2023')
        self.assertEqual(orphaned[0]['file_count'], 1)
    
    def test_get_markdown_files_in_directory(self):
        """Markdownファイル取得のテスト"""
        # テストディレクトリとファイルを作成
        self.create_test_clippings_directory("test_dir", ["test1.md", "test2.md", "readme.txt"])
        
        md_files = self.workflow._get_markdown_files_in_directory("test_dir")
        
        self.assertEqual(len(md_files), 2)
        self.assertIn("test1.md", md_files)
        self.assertIn("test2.md", md_files)
        self.assertNotIn("readme.txt", md_files)
        
    def test_get_markdown_files_nonexistent_directory(self):
        """存在しないディレクトリでのMarkdownファイル取得テスト"""
        md_files = self.workflow._get_markdown_files_in_directory("nonexistent")
        
        self.assertEqual(len(md_files), 0)


class TestSyncCheckErrorHandling(TestSyncCheckWorkflow):
    """同期チェックエラーハンドリングのテスト"""
    
    def test_missing_bibtex_file(self):
        """BibTeXファイル不在時のエラーハンドリングテスト"""
        # 存在しないBibTeXファイルを指定
        self.workflow.config['bibtex_file'] = "/nonexistent/file.bib"
        
        success, result = self.workflow.execute()
        
        self.assertFalse(success)
        self.assertIn('error', result)
    
    def test_missing_clippings_directory(self):
        """Clippingsディレクトリ不在時のエラーハンドリングテスト"""
        # 存在しないClippingsディレクトリを指定
        self.workflow.config['clippings_dir'] = "/nonexistent/clippings"
        
        success, result = self.workflow.execute()
        
        self.assertFalse(success)
        self.assertIn('error', result)


if __name__ == '__main__':
    unittest.main() 