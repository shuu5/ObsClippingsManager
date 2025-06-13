#!/usr/bin/env python3

"""
StatusChecker - Test Suite

StatusCheckerクラスのテストスイート。
重複処理回避のための状態チェック機能をテスト。
"""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# テスト対象モジュールのパス追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from py.modules.status_management.status_checker import StatusChecker
from py.modules.status_management.processing_status import ProcessingStatus
from py.modules.shared.config_manager import ConfigManager
from py.modules.shared.integrated_logger import IntegratedLogger
from py.modules.shared.exceptions import ProcessingError, ValidationError


class TestStatusChecker(unittest.TestCase):
    """StatusCheckerクラスのテスト"""

    def setUp(self):
        """テスト前の初期化処理"""
        # テスト用の一時ディレクトリ作成
        self.test_temp_dir = tempfile.mkdtemp(prefix="ObsClippingsManager_StatusChecker_Test_")
        self.clippings_dir = os.path.join(self.test_temp_dir, "clippings")
        os.makedirs(self.clippings_dir, exist_ok=True)
        
        # モック設定
        self.config_manager = MagicMock(spec=ConfigManager)
        def config_get_side_effect(key, default=None):
            # 状態チェック関連の設定
            if 'skip_completed_operations' in key:
                return True
            elif 'force_reprocessing' in key:
                return False
            elif 'check_modification_time' in key:
                return False  # テストでは修正時刻チェックを無効にする
            return default if default is not None else True
        self.config_manager.get = MagicMock(side_effect=config_get_side_effect)
        self.logger = MagicMock(spec=IntegratedLogger)
        self.logger.get_logger.return_value = MagicMock()
        
        # StatusChecker初期化
        self.status_checker = StatusChecker(self.config_manager, self.logger)

    def tearDown(self):
        """テスト後のクリーンアップ処理"""
        if os.path.exists(self.test_temp_dir):
            shutil.rmtree(self.test_temp_dir)

    def _create_test_markdown_file(self, citation_key, yaml_header):
        """テスト用Markdownファイル作成ヘルパー"""
        md_file_path = os.path.join(self.clippings_dir, f"{citation_key}.md")
        
        yaml_content = "---\n"
        for key, value in yaml_header.items():
            if isinstance(value, dict):
                yaml_content += f"{key}:\n"
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, dict):
                        yaml_content += f"  {subkey}:\n"
                        for sub2key, sub2value in subvalue.items():
                            yaml_content += f"    {sub2key}: {sub2value}\n"
                    else:
                        yaml_content += f"  {subkey}: {subvalue}\n"
            else:
                yaml_content += f"{key}: {value}\n"
        yaml_content += "---\n\n# Test Paper Content"
        
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        return md_file_path

    def test_status_checker_import(self):
        """StatusCheckerクラスのインポートテスト"""
        from py.modules.status_management.status_checker import StatusChecker
        self.assertTrue(hasattr(StatusChecker, '__init__'))

    def test_status_checker_initialization(self):
        """StatusCheckerクラスの初期化テスト"""
        self.assertIsNotNone(self.status_checker)
        self.assertEqual(self.status_checker.config_manager, self.config_manager)
        self.assertEqual(self.status_checker.logger, self.logger)

    def test_check_processing_needed_pending_status(self):
        """処理が必要な状態（PENDING）のチェックテスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'pending2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'pending',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('pending2023test', yaml_header)
        
        # 処理必要性チェック
        result = self.status_checker.check_processing_needed(md_file, 'organize')
        
        self.assertTrue(result)

    def test_check_processing_needed_completed_status(self):
        """処理が不要な状態（COMPLETED）のチェックテスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'completed2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('completed2023test', yaml_header)
        
        # 処理必要性チェック
        result = self.status_checker.check_processing_needed(md_file, 'organize')
        
        self.assertFalse(result)

    def test_check_processing_needed_failed_status(self):
        """処理が必要な状態（FAILED）のチェックテスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'failed2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'failed',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('failed2023test', yaml_header)
        
        # 処理必要性チェック
        result = self.status_checker.check_processing_needed(md_file, 'organize')
        
        self.assertTrue(result)

    def test_check_processing_needed_force_mode(self):
        """強制実行モードのテスト"""
        # テストファイル作成（完了状態）
        yaml_header = {
            'citation_key': 'force2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'completed'
            }
        }
        md_file = self._create_test_markdown_file('force2023test', yaml_header)
        
        # 強制実行モードで処理必要性チェック
        result = self.status_checker.check_processing_needed(
            md_file, 'organize', force=True
        )
        
        self.assertTrue(result)

    def test_check_modification_time_recent_change(self):
        """最近変更されたファイルの修正時刻チェックテスト"""
        # 一時的に修正時刻チェックを有効にする
        self.status_checker.check_modification_time = True
        
        # テストファイル作成
        yaml_header = {
            'citation_key': 'modified2023test',
            'workflow_version': '3.2',
            'last_updated': (datetime.now() - timedelta(hours=1)).isoformat(),  # 1時間前
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'completed'
            }
        }
        md_file = self._create_test_markdown_file('modified2023test', yaml_header)
        
        # ファイルのタイムスタンプを現在時刻に変更（最近の変更をシミュレート）
        current_time = datetime.now().timestamp()
        os.utime(md_file, (current_time, current_time))
        
        # 修正時刻チェック
        result = self.status_checker.check_modification_time_changed(md_file)
        
        self.assertTrue(result)

    def test_get_skip_conditions(self):
        """スキップ条件取得テスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'skip2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('skip2023test', yaml_header)
        
        # スキップ条件取得
        conditions = self.status_checker.get_skip_conditions(md_file, 'organize')
        
        self.assertIsNotNone(conditions)
        self.assertIsInstance(conditions, dict)
        expected_keys = ['already_completed', 'no_changes_detected', 'skip_reasons']
        for key in expected_keys:
            self.assertIn(key, conditions)

    def test_should_skip_operation_completed(self):
        """操作スキップ判定テスト（完了済み）"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'shouldskip2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'completed',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('shouldskip2023test', yaml_header)
        
        # スキップ判定
        result = self.status_checker.should_skip_operation(md_file, 'organize')
        
        self.assertTrue(result)

    def test_should_skip_operation_pending(self):
        """操作スキップ判定テスト（未完了）"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'shouldnotskip2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'pending',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('shouldnotskip2023test', yaml_header)
        
        # スキップ判定
        result = self.status_checker.should_skip_operation(md_file, 'organize')
        
        self.assertFalse(result)

    def test_get_processing_summary(self):
        """処理サマリー取得テスト"""
        # 複数のテストファイル作成
        papers = []
        for i in range(3):
            yaml_header = {
                'citation_key': f'summary2023test{i}',
                'workflow_version': '3.2',
                'last_updated': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'processing_status': {
                    'organize': 'completed' if i == 0 else 'pending',
                    'sync': 'pending'
                }
            }
            md_file = self._create_test_markdown_file(f'summary2023test{i}', yaml_header)
            papers.append(md_file)
        
        # 処理サマリー取得
        summary = self.status_checker.get_processing_summary(papers, 'organize')
        
        self.assertIsNotNone(summary)
        self.assertIsInstance(summary, dict)
        expected_keys = ['total_papers', 'need_processing', 'skip_processing', 'completion_rate']
        for key in expected_keys:
            self.assertIn(key, summary)
        
        # 値の妥当性確認
        self.assertEqual(summary['total_papers'], 3)
        self.assertEqual(summary['need_processing'], 2)  # 2つがpending
        self.assertEqual(summary['skip_processing'], 1)  # 1つがcompleted


if __name__ == '__main__':
    unittest.main() 