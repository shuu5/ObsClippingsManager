#!/usr/bin/env python3
"""
状態管理機能のテスト

BibTeXエントリの処理状態管理機能をテストします。
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent / 'py'
sys.path.insert(0, str(project_root))

from modules.shared.status_manager import StatusManager, ProcessStatus
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.shared.exceptions import ObsClippingsError


class TestProcessStatus(unittest.TestCase):
    """ProcessStatus enumのテスト"""
    
    def test_status_values(self):
        """ステータス値のテスト"""
        self.assertEqual(ProcessStatus.PENDING.value, "pending")
        self.assertEqual(ProcessStatus.COMPLETED.value, "completed")
        self.assertEqual(ProcessStatus.FAILED.value, "failed")
    
    def test_status_from_string(self):
        """文字列からのステータス変換テスト"""
        self.assertEqual(ProcessStatus.from_string("pending"), ProcessStatus.PENDING)
        self.assertEqual(ProcessStatus.from_string("completed"), ProcessStatus.COMPLETED)
        self.assertEqual(ProcessStatus.from_string("failed"), ProcessStatus.FAILED)
        
        # 不正な値
        with self.assertRaises(ValueError):
            ProcessStatus.from_string("invalid")


class TestStatusManager(unittest.TestCase):
    """StatusManagerクラスのテスト"""
    
    def setUp(self):
        """各テストの前に実行"""
        self.temp_dir = tempfile.mkdtemp()
        self.bibtex_file = os.path.join(self.temp_dir, "test.bib")
        
        # テスト用BibTeXファイル作成
        self.sample_bibtex = """@article{smith2023test,
    title={Test Paper},
    author={Smith, John},
    journal={Test Journal},
    year={2023},
    doi={10.1000/test.doi}
}

@article{jones2024neural,
    title={Neural Networks},
    author={Jones, Robert},
    year={2024},
    obsclippings_organize_status={completed},
    obsclippings_sync_status={pending},
    obsclippings_fetch_status={failed}
}"""
        
        with open(self.bibtex_file, 'w', encoding='utf-8') as f:
            f.write(self.sample_bibtex)
        
        # StatusManager初期化
        config_manager = ConfigManager()
        logger = IntegratedLogger()
        self.status_manager = StatusManager(config_manager, logger)
    
    def test_initialization(self):
        """StatusManager初期化のテスト"""
        self.assertIsInstance(self.status_manager, StatusManager)
    
    def test_load_bib_statuses(self):
        """BibTeX状態読み込みのテスト"""
        statuses = self.status_manager.load_bib_statuses(self.bibtex_file)
        
        # smith2023test: 状態フラグなし（初期値）
        smith_status = statuses.get('smith2023test', {})
        self.assertEqual(smith_status.get('organize'), ProcessStatus.PENDING)
        self.assertEqual(smith_status.get('sync'), ProcessStatus.PENDING)
        self.assertEqual(smith_status.get('fetch'), ProcessStatus.PENDING)
        self.assertEqual(smith_status.get('parse'), ProcessStatus.PENDING)
        
        # jones2024neural: 一部状態フラグあり
        jones_status = statuses.get('jones2024neural', {})
        self.assertEqual(jones_status.get('organize'), ProcessStatus.COMPLETED)
        self.assertEqual(jones_status.get('sync'), ProcessStatus.PENDING)
        self.assertEqual(jones_status.get('fetch'), ProcessStatus.FAILED)
        self.assertEqual(jones_status.get('parse'), ProcessStatus.PENDING)
    
    def test_update_status(self):
        """状態更新のテスト"""
        # 状態を更新
        success = self.status_manager.update_status(
            self.bibtex_file, 
            'smith2023test',
            'organize',
            ProcessStatus.COMPLETED
        )
        self.assertTrue(success)
        
        # 更新された状態を確認
        statuses = self.status_manager.load_bib_statuses(self.bibtex_file)
        smith_status = statuses.get('smith2023test', {})
        self.assertEqual(smith_status.get('organize'), ProcessStatus.COMPLETED)
    
    def test_batch_update_statuses(self):
        """一括状態更新のテスト"""
        updates = {
            'smith2023test': {
                'organize': ProcessStatus.COMPLETED,
                'sync': ProcessStatus.COMPLETED
            },
            'jones2024neural': {
                'fetch': ProcessStatus.COMPLETED
            }
        }
        
        success = self.status_manager.batch_update_statuses(self.bibtex_file, updates)
        self.assertTrue(success)
        
        # 更新確認
        statuses = self.status_manager.load_bib_statuses(self.bibtex_file)
        smith_status = statuses.get('smith2023test', {})
        self.assertEqual(smith_status.get('organize'), ProcessStatus.COMPLETED)
        self.assertEqual(smith_status.get('sync'), ProcessStatus.COMPLETED)
    
    def test_get_papers_needing_processing(self):
        """処理が必要な論文の取得テスト"""
        # organize処理が必要な論文
        papers = self.status_manager.get_papers_needing_processing(
            self.bibtex_file, 'organize'
        )
        self.assertIn('smith2023test', papers)
        self.assertNotIn('jones2024neural', papers)  # already completed
        
        # fetch処理が必要な論文（失敗したものも含む）
        papers = self.status_manager.get_papers_needing_processing(
            self.bibtex_file, 'fetch', include_failed=True
        )
        self.assertIn('smith2023test', papers)
        self.assertIn('jones2024neural', papers)  # failed, needs retry
    
    def test_check_status_consistency(self):
        """状態整合性チェックのテスト"""
        clippings_dir = os.path.join(self.temp_dir, "Clippings")
        os.makedirs(clippings_dir)
        
        # smith2023testディレクトリを作成
        smith_dir = os.path.join(clippings_dir, "smith2023test")
        os.makedirs(smith_dir)
        with open(os.path.join(smith_dir, "smith2023test.md"), 'w') as f:
            f.write("# Test paper")
        
        # 整合性チェック実行
        consistency_report = self.status_manager.check_status_consistency(
            self.bibtex_file, clippings_dir
        )
        
        self.assertIn('missing_directories', consistency_report)
        self.assertIn('orphaned_directories', consistency_report)
        self.assertIn('status_inconsistencies', consistency_report)
    
    def test_reset_statuses(self):
        """状態リセットのテスト"""
        # 全状態をリセット
        success = self.status_manager.reset_statuses(
            self.bibtex_file, 'jones2024neural'
        )
        self.assertTrue(success)
        
        # リセット確認
        statuses = self.status_manager.load_bib_statuses(self.bibtex_file)
        jones_status = statuses.get('jones2024neural', {})
        self.assertEqual(jones_status.get('organize'), ProcessStatus.PENDING)
        self.assertEqual(jones_status.get('sync'), ProcessStatus.PENDING)
        self.assertEqual(jones_status.get('fetch'), ProcessStatus.PENDING)
        self.assertEqual(jones_status.get('parse'), ProcessStatus.PENDING)


class TestStatusIntegration(unittest.TestCase):
    """状態管理機能の統合テスト"""
    
    def setUp(self):
        """各テストの前に実行"""
        self.temp_dir = tempfile.mkdtemp()
        self.bibtex_file = os.path.join(self.temp_dir, "CurrentManuscript.bib")
        self.clippings_dir = os.path.join(self.temp_dir, "Clippings")
        
        os.makedirs(self.clippings_dir)
        
        # テスト用設定
        config_manager = ConfigManager()
        logger = IntegratedLogger()
        self.status_manager = StatusManager(config_manager, logger)
    
    def test_full_workflow_status_tracking(self):
        """完全ワークフローの状態追跡テスト"""
        # 初期BibTeXファイル作成
        bibtex_content = """@article{test2023paper,
    title={Test Paper for Status Tracking},
    author={Author, Test},
    year={2023},
    doi={10.1000/status.test}
}"""
        
        with open(self.bibtex_file, 'w', encoding='utf-8') as f:
            f.write(bibtex_content)
        
        # 1. organize処理完了を記録
        self.status_manager.update_status(
            self.bibtex_file, 'test2023paper', 'organize', ProcessStatus.COMPLETED
        )
        
        # 2. sync処理完了を記録
        self.status_manager.update_status(
            self.bibtex_file, 'test2023paper', 'sync', ProcessStatus.COMPLETED
        )
        
        # 3. fetch処理失敗を記録
        self.status_manager.update_status(
            self.bibtex_file, 'test2023paper', 'fetch', ProcessStatus.FAILED
        )
        
        # 状態確認
        statuses = self.status_manager.load_bib_statuses(self.bibtex_file)
        paper_status = statuses.get('test2023paper', {})
        
        self.assertEqual(paper_status.get('organize'), ProcessStatus.COMPLETED)
        self.assertEqual(paper_status.get('sync'), ProcessStatus.COMPLETED)
        self.assertEqual(paper_status.get('fetch'), ProcessStatus.FAILED)
        self.assertEqual(paper_status.get('parse'), ProcessStatus.PENDING)


if __name__ == '__main__':
    unittest.main() 