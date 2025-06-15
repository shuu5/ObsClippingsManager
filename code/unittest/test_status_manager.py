#!/usr/bin/env python3
"""
StatusManager - Test Suite

StatusManagerクラスのテストスイート。
YAMLヘッダーベースの状態管理機能をテスト。
"""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# テスト対象モジュールのパス追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from py.modules.status_management_yaml.status_manager import StatusManager
from py.modules.status_management_yaml.processing_status import ProcessingStatus
from py.modules.shared_modules.config_manager import ConfigManager
from py.modules.shared_modules.integrated_logger import IntegratedLogger
from py.modules.shared_modules.exceptions import ProcessingError, ValidationError


class TestStatusManager(unittest.TestCase):
    """StatusManagerクラスのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = tempfile.mkdtemp()
        self.clippings_dir = os.path.join(self.test_dir, 'clippings')
        os.makedirs(self.clippings_dir, exist_ok=True)
        
        # モック設定
        self.config_manager = MagicMock(spec=ConfigManager)
        def config_get_side_effect(key, default=None):
            # バックアップ関連の設定を無効化
            if 'backup' in key:
                return False
            return True
        self.config_manager.get = MagicMock(side_effect=config_get_side_effect)
        
        # config属性のモック設定（AttributeError修正用）
        mock_config = MagicMock()
        def config_nested_get_side_effect(key, default=None):
            # status_management関連の設定を返す
            if key == 'status_management':
                return {
                    'backup_strategy': {
                        'backup_before_status_update': False  # テスト用に無効化
                    },
                    'error_handling': {
                        'validate_yaml_before_update': False,  # テスト用に無効化
                        'create_backup_on_yaml_error': False,
                        'auto_repair_corrupted_headers': False,
                        'fallback_to_backup_on_failure': False
                    }
                }
            return default
        mock_config.get = MagicMock(side_effect=config_nested_get_side_effect)
        self.config_manager.config = mock_config
        self.logger = MagicMock(spec=IntegratedLogger)
        self.logger.get_logger.return_value = MagicMock()
        
        # StatusManager初期化
        self.status_manager = StatusManager(self.config_manager, self.logger)
    
    def tearDown(self):
        """テストクリーンアップ"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_status_manager_import(self):
        """StatusManagerクラスのインポートテスト"""
        self.assertTrue(hasattr(StatusManager, 'load_md_statuses'))
        self.assertTrue(hasattr(StatusManager, 'update_status'))
        self.assertTrue(hasattr(StatusManager, 'get_papers_needing_processing'))
    
    def test_status_manager_initialization(self):
        """StatusManagerクラスの初期化テスト"""
        self.assertIsNotNone(self.status_manager.config_manager)
        self.assertIsNotNone(self.status_manager.logger)
    
    def test_load_md_statuses_empty_directory(self):
        """空のディレクトリでの状態読み込みテスト"""
        statuses = self.status_manager.load_md_statuses(self.clippings_dir)
        self.assertEqual(statuses, {})
    
    def test_load_md_statuses_single_file(self):
        """単一ファイルの状態読み込みテスト"""
        # テストファイル作成
        test_file = os.path.join(self.clippings_dir, 'smith2023test.md')
        yaml_content = """---
citation_key: smith2023test
processing_status:
  organize: completed
  sync: pending
  fetch: failed
---
# Test Content"""
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        statuses = self.status_manager.load_md_statuses(self.clippings_dir)
        
        self.assertIn('smith2023test', statuses)
        self.assertEqual(statuses['smith2023test']['organize'], ProcessingStatus.COMPLETED)
        self.assertEqual(statuses['smith2023test']['sync'], ProcessingStatus.PENDING)
        self.assertEqual(statuses['smith2023test']['fetch'], ProcessingStatus.FAILED)
    
    def test_load_md_statuses_multiple_files(self):
        """複数ファイルの状態読み込みテスト"""
        # テストファイル1
        test_file1 = os.path.join(self.clippings_dir, 'smith2023test.md')
        yaml_content1 = """---
citation_key: smith2023test
processing_status:
  organize: completed
---
# Test Content 1"""
        
        # テストファイル2
        test_file2 = os.path.join(self.clippings_dir, 'jones2023bio.md')
        yaml_content2 = """---
citation_key: jones2023bio
processing_status:
  organize: pending
  fetch: completed
---
# Test Content 2"""
        
        with open(test_file1, 'w', encoding='utf-8') as f:
            f.write(yaml_content1)
        with open(test_file2, 'w', encoding='utf-8') as f:
            f.write(yaml_content2)
        
        statuses = self.status_manager.load_md_statuses(self.clippings_dir)
        
        self.assertEqual(len(statuses), 2)
        self.assertIn('smith2023test', statuses)
        self.assertIn('jones2023bio', statuses)
    
    def test_load_md_statuses_corrupted_file(self):
        """破損ファイルの状態読み込みテスト"""
        # 破損ファイル作成
        test_file = os.path.join(self.clippings_dir, 'corrupted.md')
        corrupted_content = """---
invalid: yaml: content
---
# Test Content"""
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(corrupted_content)
        
        statuses = self.status_manager.load_md_statuses(self.clippings_dir)
        # 破損ファイルはスキップされ、空の結果が返される
        self.assertEqual(statuses, {})
    
    def test_update_status_success(self):
        """状態更新成功テスト"""
        # テストファイル作成
        test_file = os.path.join(self.clippings_dir, 'smith2023test.md')
        yaml_content = """---
citation_key: smith2023test
processing_status:
  organize: pending
last_updated: '2025-01-15T09:00:00.123456+00:00'
created_at: '2025-01-15T09:00:00.123456+00:00'
workflow_version: '3.2'
tags: []
---
# Test Content"""
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        success = self.status_manager.update_status(
            self.clippings_dir, 'smith2023test', 'organize', ProcessingStatus.COMPLETED
        )
        
        self.assertTrue(success)
        
        # ファイル内容を確認
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('organize: completed', content)
    
    def test_update_status_file_not_found(self):
        """存在しないファイルの状態更新エラーテスト"""
        with self.assertRaises(ProcessingError) as context:
            self.status_manager.update_status(
                self.clippings_dir, 'nonexistent', 'organize', ProcessingStatus.COMPLETED
            )
        
        self.assertEqual(context.exception.error_code, "FILE_NOT_FOUND")
    
    def test_get_papers_needing_processing_pending_status(self):
        """処理が必要な論文（PENDING状態）の取得テスト"""
        # テストファイル作成
        test_file = os.path.join(self.clippings_dir, 'smith2023test.md')
        yaml_content = """---
citation_key: smith2023test
processing_status:
  organize: pending
  sync: completed
---
# Test Content"""
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        target_papers = ['smith2023test']
        papers = self.status_manager.get_papers_needing_processing(
            self.clippings_dir, 'organize', target_papers
        )
        
        self.assertEqual(len(papers), 1)
        self.assertTrue(papers[0].endswith('smith2023test.md'))
    
    def test_get_papers_needing_processing_failed_status(self):
        """処理が必要な論文（FAILED状態）の取得テスト"""
        # テストファイル作成
        test_file = os.path.join(self.clippings_dir, 'smith2023test.md')
        yaml_content = """---
citation_key: smith2023test
processing_status:
  organize: failed
---
# Test Content"""
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        target_papers = ['smith2023test']
        papers = self.status_manager.get_papers_needing_processing(
            self.clippings_dir, 'organize', target_papers
        )
        
        self.assertEqual(len(papers), 1)
        self.assertTrue(papers[0].endswith('smith2023test.md'))
    
    def test_get_papers_needing_processing_completed_status(self):
        """完了済み論文は処理対象外テスト"""
        # テストファイル作成
        test_file = os.path.join(self.clippings_dir, 'smith2023test.md')
        yaml_content = """---
citation_key: smith2023test
processing_status:
  organize: completed
---
# Test Content"""
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        target_papers = ['smith2023test']
        papers = self.status_manager.get_papers_needing_processing(
            self.clippings_dir, 'organize', target_papers
        )
        
        self.assertEqual(len(papers), 0)
    
    def test_get_papers_needing_processing_empty_target(self):
        """対象論文リストが空の場合のテスト"""
        papers = self.status_manager.get_papers_needing_processing(
            self.clippings_dir, 'organize', []
        )
        
        self.assertEqual(papers, [])
    
    def test_get_papers_needing_processing_nonexistent_paper(self):
        """存在しない論文が対象リストに含まれる場合のテスト"""
        target_papers = ['nonexistent_paper']
        papers = self.status_manager.get_papers_needing_processing(
            self.clippings_dir, 'organize', target_papers
        )
        
        self.assertEqual(papers, [])


if __name__ == '__main__':
    unittest.main() 