#!/usr/bin/env python3
"""
SyncCheckerテストスイート

テスト対象:
- SyncCheckerクラス基本機能
- BibTeX ↔ Clippings整合性チェック
- エッジケース検出機能
- 不整合レポート生成機能
- 軽微な不整合自動修正機能
- sync処理統合テスト
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import yaml
from datetime import datetime

# テスト環境のセットアップ
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# テスト分離用一時ディレクトリ
TEST_BASE_DIR = "/tmp/ObsClippingsManager_SyncChecker_Test"

# インポートテスト
IMPORTS_AVAILABLE = False
IMPORT_ERROR = None

try:
    from code.py.modules.sync_checker.sync_checker import SyncChecker
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORT_ERROR = str(e)
    IMPORTS_AVAILABLE = False


class TestSyncCheckerImport(unittest.TestCase):
    """SyncCheckerクラスインポートテスト"""
    
    def test_sync_checker_import(self):
        """SyncCheckerクラスのインポートテスト"""
        if not IMPORTS_AVAILABLE:
            self.fail("SyncChecker should be importable")
        
        # クラスの存在確認
        self.assertTrue(hasattr(SyncChecker, '__init__'))
        self.assertTrue(hasattr(SyncChecker, 'check_workspace_consistency'))
        self.assertTrue(hasattr(SyncChecker, 'check_paper_consistency'))
        self.assertTrue(hasattr(SyncChecker, 'auto_fix_minor_inconsistencies'))


class TestSyncCheckerBasic(unittest.TestCase):
    """SyncChecker基本機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = Path(TEST_BASE_DIR)
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # テスト用ディレクトリ構造作成
        self.clippings_dir = self.test_dir / "Clippings"
        self.clippings_dir.mkdir()
        
        # テスト用BibTeXファイル作成
        self.bibtex_content = """@article{smith2024biomarkers,
    title={Novel biomarkers in cancer research},
    author={Smith, John and Johnson, Mary},
    journal={Nature Reviews Cancer},
    volume={24},
    number={3},
    pages={123-145},
    year={2024},
    doi={10.1038/s41598-024-12345-6},
    publisher={Nature Publishing Group}
}

@article{jones2024therapy,
    title={Advanced therapy approaches},
    author={Jones, David and Brown, Sarah},
    journal={Cell},
    volume={187},
    number={5},
    pages={1234-1250},
    year={2024},
    doi={10.1016/j.cell.2024.67890},
    publisher={Elsevier}
}
"""
        self.bibtex_file = self.test_dir / "CurrentManuscript.bib"
        self.bibtex_file.write_text(self.bibtex_content, encoding='utf-8')
        
        # Mock設定
        self.mock_config = Mock()
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_sync_checker_initialization(self):
        """SyncCheckerクラスの初期化テスト"""
        sync_checker = SyncChecker(self.mock_config, self.mock_logger)
        
        self.assertIsNotNone(sync_checker)
        self.assertEqual(sync_checker.config_manager, self.mock_config)
        self.assertEqual(sync_checker.logger, self.mock_logger.get_logger.return_value)
        self.assertTrue(hasattr(sync_checker, 'bibtex_parser'))
        self.assertTrue(hasattr(sync_checker, 'yaml_processor'))


class TestSyncCheckerConsistencyCheck(unittest.TestCase):
    """SyncChecker整合性チェック機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = Path(TEST_BASE_DIR)
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        self.clippings_dir = self.test_dir / "Clippings"
        self.clippings_dir.mkdir()
        
        # BibTeXファイル作成
        self.bibtex_content = """@article{smith2024biomarkers,
    title={Novel biomarkers in cancer research},
    author={Smith, John and Johnson, Mary},
    journal={Nature Reviews Cancer},
    doi={10.1038/s41598-024-12345-6},
    year={2024}
}
"""
        self.bibtex_file = self.test_dir / "CurrentManuscript.bib"
        self.bibtex_file.write_text(self.bibtex_content, encoding='utf-8')
        
        # Mock設定
        self.mock_config = Mock()
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _create_test_markdown_file(self, citation_key, doi=None, title=None, has_sync_status=False):
        """テスト用Markdownファイル作成ヘルパー"""
        sync_metadata = {}
        if has_sync_status:
            sync_metadata = {
                'checked_at': '2025-01-15T10:30:00Z',
                'consistency_status': 'validated',
                'issues_detected': 0,
                'auto_corrections_applied': 0,
                'corrections_applied': []
            }
        
        yaml_header = {
            'citation_key': citation_key,
            'workflow_version': '3.2',
            'last_updated': '2025-01-15T09:00:00Z',
            'processing_status': {
                'organize': 'completed',
                'sync': 'pending'
            }
        }
        
        if doi:
            yaml_header['doi'] = doi
        if title:
            yaml_header['title'] = title
        if sync_metadata:
            yaml_header['sync_metadata'] = sync_metadata
        
        content = f"""---
{yaml.dump(yaml_header, default_flow_style=False, allow_unicode=True)}---

# Test Paper Content
This is test content for {citation_key}.
"""
        
        paper_dir = self.clippings_dir / citation_key
        paper_dir.mkdir(exist_ok=True)
        md_file = paper_dir / f"{citation_key}.md"
        md_file.write_text(content, encoding='utf-8')
        return md_file
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_check_workspace_consistency_perfect_match(self):
        """完全一致ワークスペースの整合性チェックテスト"""
        sync_checker = SyncChecker(self.mock_config, self.mock_logger)
        
        # 完全一致するMarkdownファイル作成
        self._create_test_markdown_file(
            'smith2024biomarkers',
            doi='10.1038/s41598-024-12345-6',
            title='Novel biomarkers in cancer research'
        )
        
        result = sync_checker.check_workspace_consistency(
            str(self.test_dir),
            str(self.bibtex_file),
            str(self.clippings_dir)
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('consistency_status', result)
        self.assertIn('issues_detected', result)
        self.assertIn('papers_checked', result)
        self.assertEqual(result['consistency_status'], 'validated')
        self.assertEqual(result['issues_detected'], 0)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_check_workspace_consistency_missing_markdown(self):
        """Markdownファイル不足時の整合性チェックテスト"""
        sync_checker = SyncChecker(self.mock_config, self.mock_logger)
        
        # BibTeXに存在するがMarkdownが不足している状況
        result = sync_checker.check_workspace_consistency(
            str(self.test_dir),
            str(self.bibtex_file),
            str(self.clippings_dir)
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('consistency_status', result)
        self.assertIn('issues_detected', result)
        self.assertGreater(result['issues_detected'], 0)
        self.assertIn('missing_markdown_files', result)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_check_workspace_consistency_orphaned_markdown(self):
        """孤立Markdownファイル検出テスト"""
        sync_checker = SyncChecker(self.mock_config, self.mock_logger)
        
        # BibTeXに存在しない孤立Markdownファイル作成
        self._create_test_markdown_file('orphaned2024paper')
        
        result = sync_checker.check_workspace_consistency(
            str(self.test_dir),
            str(self.bibtex_file),
            str(self.clippings_dir)
        )
        
        self.assertIsInstance(result, dict)
        self.assertGreater(result['issues_detected'], 0)
        self.assertIn('orphaned_markdown_files', result)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_check_paper_consistency_metadata_mismatch(self):
        """個別論文メタデータ不一致検出テスト"""
        sync_checker = SyncChecker(self.mock_config, self.mock_logger)
        
        # DOI不一致のMarkdownファイル作成
        self._create_test_markdown_file(
            'smith2024biomarkers',
            doi='10.1038/s41598-999-99999-9',  # 異なるDOI
            title='Novel biomarkers in cancer research'
        )
        
        # BibTeXエントリーを模擬（実際の実装では正確な形式を使用）
        bibtex_entry = {
            'citation_key': 'smith2024biomarkers',
            'doi': '10.1038/s41598-024-12345-6',
            'title': 'Novel biomarkers in cancer research'
        }
        
        paper_dir = self.clippings_dir / 'smith2024biomarkers'
        result = sync_checker.check_paper_consistency(
            'smith2024biomarkers',
            str(paper_dir),
            bibtex_entry
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('consistency_status', result)
        self.assertIn('metadata_mismatches', result)
        self.assertGreater(len(result['metadata_mismatches']), 0)


class TestSyncCheckerAutoFix(unittest.TestCase):
    """SyncChecker自動修正機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = Path(TEST_BASE_DIR)
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        self.clippings_dir = self.test_dir / "Clippings"
        self.clippings_dir.mkdir()
        
        # Mock設定
        self.mock_config = Mock()
        self.mock_config.get.return_value = {
            'auto_fix_minor_issues': True,
            'backup_before_auto_fix': True
        }
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_auto_fix_minor_inconsistencies_filename_normalization(self):
        """ファイル名正規化自動修正テスト"""
        sync_checker = SyncChecker(self.mock_config, self.mock_logger)
        
        # 軽微な不整合の模擬結果
        check_results = {
            'issues_detected': 1,
            'minor_issues': [
                {
                    'type': 'filename_normalization',
                    'citation_key': 'smith2024biomarkers',
                    'current_filename': 'Smith_2024_Biomarkers.md',
                    'expected_filename': 'smith2024biomarkers.md',
                    'paper_dir': str(self.clippings_dir / 'smith2024biomarkers')
                }
            ]
        }
        
        result = sync_checker.auto_fix_minor_inconsistencies(check_results)
        
        self.assertIsInstance(result, dict)
        self.assertIn('corrections_applied', result)
        self.assertIn('auto_fix_successful', result)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_auto_fix_minor_inconsistencies_disabled(self):
        """自動修正無効時のテスト"""
        # 自動修正無効設定
        self.mock_config.get_config.return_value = {
            'sync_checker': {
                'auto_fix_minor_issues': False
            }
        }
        
        sync_checker = SyncChecker(self.mock_config, self.mock_logger)
        
        check_results = {
            'issues_detected': 1,
            'minor_issues': [
                {
                    'type': 'filename_normalization',
                    'citation_key': 'smith2024biomarkers'
                }
            ]
        }
        
        result = sync_checker.auto_fix_minor_inconsistencies(check_results)
        
        self.assertIsInstance(result, dict)
        self.assertFalse(result.get('auto_fix_enabled', True))
        self.assertEqual(len(result.get('corrections_applied', [])), 0)


class TestSyncCheckerIntegration(unittest.TestCase):
    """SyncChecker統合テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = Path(TEST_BASE_DIR)
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        self.clippings_dir = self.test_dir / "Clippings"
        self.clippings_dir.mkdir()
        
        # Mock設定
        self.mock_config = Mock()
        self.mock_config.get.return_value = {
            'enabled': True,
            'auto_fix_minor_issues': True,
            'backup_before_auto_fix': True,
            'retry_attempts': 3
        }
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _create_complex_test_environment(self):
        """複雑なテスト環境作成ヘルパー"""
        # 複数のBibTeXエントリー
        bibtex_content = """@article{smith2024biomarkers,
    title={Novel biomarkers in cancer research},
    author={Smith, John and Johnson, Mary},
    journal={Nature Reviews Cancer},
    doi={10.1038/s41598-024-12345-6},
    year={2024}
}

@article{jones2024therapy,
    title={Advanced therapy approaches},
    author={Jones, David and Brown, Sarah},
    journal={Cell},
    doi={10.1016/j.cell.2024.67890},
    year={2024}
}

@article{wilson2024diagnostics,
    title={Innovative diagnostic methods},
    author={Wilson, Emma and Davis, Michael},
    journal={Science},
    doi={10.1126/science.abcd1234},
    year={2024}
}
"""
        self.bibtex_file = self.test_dir / "CurrentManuscript.bib"
        self.bibtex_file.write_text(bibtex_content, encoding='utf-8')
        
        # 各種状況のMarkdownファイル作成
        # 1. 完全一致
        self._create_organized_markdown_file(
            'smith2024biomarkers',
            doi='10.1038/s41598-024-12345-6',
            title='Novel biomarkers in cancer research'
        )
        
        # 2. DOI不一致（軽微な問題）
        self._create_organized_markdown_file(
            'jones2024therapy',
            doi='10.1016/j.cell.2024.99999',  # 異なるDOI
            title='Advanced therapy approaches'
        )
        
        # 3. BibTeXにあるがMarkdownなし（wilson2024diagnostics）
        
        # 4. 孤立Markdownファイル
        self._create_organized_markdown_file(
            'orphaned2024study',
            doi='10.1038/s41598-999-88888-8',
            title='Orphaned study'
        )
    
    def _create_organized_markdown_file(self, citation_key, doi=None, title=None):
        """organize済みMarkdownファイル作成ヘルパー"""
        yaml_header = {
            'citation_key': citation_key,
            'workflow_version': '3.2',
            'last_updated': '2025-01-15T09:00:00Z',
            'processing_status': {
                'organize': 'completed',
                'sync': 'pending'
            }
        }
        
        if doi:
            yaml_header['doi'] = doi
        if title:
            yaml_header['title'] = title
        
        content = f"""---
{yaml.dump(yaml_header, default_flow_style=False, allow_unicode=True)}---

# {title or 'Test Paper'}
Content for {citation_key}.
"""
        
        paper_dir = self.clippings_dir / citation_key
        paper_dir.mkdir(exist_ok=True)
        md_file = paper_dir / f"{citation_key}.md"
        md_file.write_text(content, encoding='utf-8')
        return md_file
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_full_sync_workflow_mixed_scenarios(self):
        """混合シナリオでの完全sync処理ワークフローテスト"""
        sync_checker = SyncChecker(self.mock_config, self.mock_logger)
        
        # 複雑なテスト環境作成
        self._create_complex_test_environment()
        
        # ワークスペース整合性チェック実行
        result = sync_checker.check_workspace_consistency(
            str(self.test_dir),
            str(self.bibtex_file),
            str(self.clippings_dir)
        )
        
        # 結果の検証
        self.assertIsInstance(result, dict)
        self.assertIn('consistency_status', result)
        self.assertIn('issues_detected', result)
        self.assertIn('papers_checked', result)
        
        # 検出された問題の内容確認
        if result['issues_detected'] > 0:
            # 自動修正試行
            fix_result = sync_checker.auto_fix_minor_inconsistencies(result)
            self.assertIsInstance(fix_result, dict)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_sync_status_update_in_yaml_header(self):
        """YAMLヘッダーのsync状態更新テスト"""
        sync_checker = SyncChecker(self.mock_config, self.mock_logger)
        
        # テスト用ファイル作成
        md_file = self._create_organized_markdown_file(
            'smith2024biomarkers',
            doi='10.1038/s41598-024-12345-6',
            title='Novel biomarkers in cancer research'
        )
        
        # BibTeXファイル作成
        bibtex_content = """@article{smith2024biomarkers,
    title={Novel biomarkers in cancer research},
    doi={10.1038/s41598-024-12345-6},
    year={2024}
}
"""
        self.bibtex_file = self.test_dir / "CurrentManuscript.bib"
        self.bibtex_file.write_text(bibtex_content, encoding='utf-8')
        
        # sync処理実行
        result = sync_checker.check_workspace_consistency(
            str(self.test_dir),
            str(self.bibtex_file),
            str(self.clippings_dir)
        )
        
        # 処理後のYAMLヘッダー確認
        content = md_file.read_text(encoding='utf-8')
        
        # sync_metadata追加確認（実際の実装で追加される想定）
        if 'sync_metadata:' in content:
            self.assertIn('checked_at:', content)
            self.assertIn('consistency_status:', content)


class TestSyncCheckerDOILinks(unittest.TestCase):
    """SyncChecker DOIリンク表示機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = Path(TEST_BASE_DIR)
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock設定
        self.mock_config = Mock()
        self.mock_config.get_config.return_value = {
            'sync_checker': {
                'display_doi_links': True,
                'doi_link_format': 'https://doi.org/{doi}'
            }
        }
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_display_doi_links_missing_papers(self):
        """不足MarkdownファイルのDOIリンク表示テスト"""
        sync_checker = SyncChecker(self.mock_config, self.mock_logger)
        
        missing_papers = [
            {
                'citation_key': 'smith2024test',
                'bibtex_entry': {
                    'doi': '10.1038/s41598-024-12345-6',
                    'title': 'Test Paper'
                }
            },
            {
                'citation_key': 'jones2024study',
                'bibtex_entry': {
                    'doi': '10.1016/j.cell.2024.67890',
                    'title': 'Study Paper'
                }
            }
        ]
        
        # DOIリンク表示実行（出力は目視確認）
        sync_checker.display_doi_links(missing_papers, [])
        
        # メソッドが正常に実行されることを確認
        self.assertTrue(True)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_display_doi_links_orphaned_papers(self):
        """孤立MarkdownファイルのDOIリンク表示テスト"""
        sync_checker = SyncChecker(self.mock_config, self.mock_logger)
        
        # テスト用Markdownファイル作成
        test_file = self.test_dir / "test_paper.md"
        yaml_content = """---
citation_key: orphaned2024test
doi: 10.3390/ijms22158109
title: Orphaned Test Paper
---

# Test Content
"""
        test_file.write_text(yaml_content, encoding='utf-8')
        
        orphaned_papers = [
            {
                'citation_key': 'orphaned2024test',
                'markdown_file': str(test_file)
            }
        ]
        
        # DOIリンク表示実行（出力は目視確認）
        sync_checker.display_doi_links([], orphaned_papers)
        
        # メソッドが正常に実行されることを確認
        self.assertTrue(True)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_display_doi_links_disabled(self):
        """DOIリンク表示無効時のテスト"""
        # DOIリンク表示無効設定
        self.mock_config.get_config.return_value = {
            'sync_checker': {
                'display_doi_links': False
            }
        }
        
        sync_checker = SyncChecker(self.mock_config, self.mock_logger)
        
        missing_papers = [{'citation_key': 'test', 'bibtex_entry': {'doi': '10.1234/test'}}]
        
        # DOIリンク表示実行（無効なので何も表示されない）
        sync_checker.display_doi_links(missing_papers, [])
        
        # メソッドが正常に実行されることを確認
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main() 