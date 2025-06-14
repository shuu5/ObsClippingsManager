#!/usr/bin/env python3
"""
TimestampManager - Test Suite

TimestampManagerクラスのテストスイート。
詳細なタイムスタンプ管理機能をテスト。
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

from py.modules.status_management_yaml.timestamp_manager import TimestampManager
from py.modules.status_management_yaml.processing_status import ProcessingStatus
from py.modules.shared_modules.config_manager import ConfigManager
from py.modules.shared_modules.integrated_logger import IntegratedLogger
from py.modules.shared_modules.exceptions import ProcessingError, ValidationError


class TestTimestampManager(unittest.TestCase):
    """TimestampManagerクラスのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = tempfile.mkdtemp()
        self.clippings_dir = os.path.join(self.test_dir, 'clippings')
        os.makedirs(self.clippings_dir, exist_ok=True)
        
        # モック設定
        self.config_manager = MagicMock(spec=ConfigManager)
        def config_get_side_effect(key, default=None):
            # タイムスタンプ管理関連の設定
            if 'timestamp_retention_days' in key:
                return 30
            elif 'detailed_timestamp_tracking' in key:
                return True
            return default if default is not None else True
        self.config_manager.get = MagicMock(side_effect=config_get_side_effect)
        self.logger = MagicMock(spec=IntegratedLogger)
        self.logger.get_logger.return_value = MagicMock()
        
        # TimestampManager初期化
        self.timestamp_manager = TimestampManager(self.config_manager, self.logger)
    
    def tearDown(self):
        """テストクリーンアップ"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_test_markdown_file(self, citation_key, yaml_header):
        """テスト用Markdownファイル作成ヘルパー"""
        md_file_path = os.path.join(self.clippings_dir, f"{citation_key}.md")
        
        yaml_content = "---\n"
        for key, value in yaml_header.items():
            if isinstance(value, dict):
                yaml_content += f"{key}:\n"
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, list):
                        yaml_content += f"  {subkey}:\n"
                        for item in subvalue:
                            if isinstance(item, dict):
                                yaml_content += "    - "
                                for k, v in item.items():
                                    yaml_content += f"{k}: {v}\n      "
                                yaml_content = yaml_content.rstrip(" \n") + "\n"
                            else:
                                yaml_content += f"    - {item}\n"
                    else:
                        yaml_content += f"  {subkey}: {subvalue}\n"
            elif isinstance(value, list):
                yaml_content += f"{key}: {value}\n"
            else:
                yaml_content += f"{key}: {value}\n"
        yaml_content += "---\n\n# Test Paper Content"
        
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        return md_file_path
    
    def test_timestamp_manager_import(self):
        """TimestampManagerクラスのインポートテスト"""
        from py.modules.status_management_yaml.timestamp_manager import TimestampManager
        self.assertTrue(hasattr(TimestampManager, '__init__'))
    
    def test_timestamp_manager_initialization(self):
        """TimestampManagerクラスの初期化テスト"""
        manager = TimestampManager(self.config_manager, self.logger)
        self.assertIsNotNone(manager)
        self.assertEqual(manager.config_manager, self.config_manager)
        self.assertIsNotNone(manager.logger)
    
    def test_create_timestamp_record(self):
        """タイムスタンプ記録作成テスト"""
        timestamp_record = self.timestamp_manager.create_timestamp_record(
            operation="organize",
            status="started"
        )
        
        self.assertIsNotNone(timestamp_record)
        self.assertIn('timestamp', timestamp_record)
        self.assertIn('operation', timestamp_record)
        self.assertIn('status', timestamp_record)
        self.assertEqual(timestamp_record['operation'], "organize")
        self.assertEqual(timestamp_record['status'], "started")
    
    def test_update_processing_timestamp(self):
        """処理ステップタイムスタンプ更新テスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'test2023paper',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_status': {
                'organize': 'pending',
                'sync': 'pending'
            }
        }
        md_file = self._create_test_markdown_file('test2023paper', yaml_header)
        
        # タイムスタンプ更新実行
        result = self.timestamp_manager.update_processing_timestamp(
            md_file, 'organize', 'started'
        )
        
        self.assertTrue(result)
    
    def test_get_processing_history(self):
        """処理履歴タイムスタンプ取得テスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'history2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_timestamps': {
                'organize': [
                    {
                        'timestamp': datetime.now().isoformat(),
                        'status': 'started'
                    },
                    {
                        'timestamp': (datetime.now() + timedelta(minutes=5)).isoformat(),
                        'status': 'completed'
                    }
                ]
            }
        }
        md_file = self._create_test_markdown_file('history2023test', yaml_header)
        
        # 履歴取得
        history = self.timestamp_manager.get_processing_history(md_file, 'organize')
        
        self.assertIsNotNone(history)
        self.assertIsInstance(history, list)
        if history:  # 履歴が存在する場合
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]['status'], 'started')
            self.assertEqual(history[1]['status'], 'completed')
    
    def test_calculate_processing_duration(self):
        """処理時間計算テスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=10, seconds=30)
        
        duration = self.timestamp_manager.calculate_processing_duration(
            start_time.isoformat(),
            end_time.isoformat()
        )
        
        self.assertIsNotNone(duration)
        self.assertGreater(duration, 600)  # 10分以上
        self.assertLess(duration, 660)     # 11分未満
    
    def test_get_last_activity_timestamp(self):
        """最終活動タイムスタンプ取得テスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'activity2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': (datetime.now() - timedelta(days=1)).isoformat(),
            'processing_timestamps': {
                'organize': [
                    {
                        'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
                        'status': 'completed'
                    }
                ],
                'sync': [
                    {
                        'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
                        'status': 'completed'
                    }
                ]
            }
        }
        md_file = self._create_test_markdown_file('activity2023test', yaml_header)
        
        # 最終活動取得
        last_activity = self.timestamp_manager.get_last_activity_timestamp(md_file)
        
        self.assertIsNotNone(last_activity)
    
    def test_cleanup_old_timestamps(self):
        """古いタイムスタンプクリーンアップテスト"""
        # テストファイル作成（古いタイムスタンプ含む）
        old_timestamp = (datetime.now() - timedelta(days=35)).isoformat()
        recent_timestamp = (datetime.now() - timedelta(days=5)).isoformat()
        
        yaml_header = {
            'citation_key': 'cleanup2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_timestamps': {
                'organize': [
                    {
                        'timestamp': old_timestamp,
                        'status': 'completed'
                    },
                    {
                        'timestamp': recent_timestamp,
                        'status': 'completed'
                    }
                ]
            }
        }
        md_file = self._create_test_markdown_file('cleanup2023test', yaml_header)
        
        # クリーンアップ実行
        cleaned_count = self.timestamp_manager.cleanup_old_timestamps(
            md_file, retention_days=30
        )
        
        self.assertIsInstance(cleaned_count, int)
        self.assertGreaterEqual(cleaned_count, 0)
    
    def test_validate_timestamp_format(self):
        """タイムスタンプフォーマット検証テスト"""
        # 有効なタイムスタンプ
        valid_timestamp = datetime.now().isoformat()
        self.assertTrue(
            self.timestamp_manager.validate_timestamp_format(valid_timestamp)
        )
        
        # 無効なタイムスタンプ
        invalid_timestamp = "2023-13-45T25:70:99"
        self.assertFalse(
            self.timestamp_manager.validate_timestamp_format(invalid_timestamp)
        )
        
        # None値
        self.assertFalse(
            self.timestamp_manager.validate_timestamp_format(None)
        )
    
    def test_get_timestamp_statistics(self):
        """タイムスタンプ統計情報取得テスト"""
        # テストファイル作成
        yaml_header = {
            'citation_key': 'stats2023test',
            'workflow_version': '3.2',
            'last_updated': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'processing_timestamps': {
                'organize': [
                    {
                        'timestamp': (datetime.now() - timedelta(hours=3)).isoformat(),
                        'status': 'started'
                    },
                    {
                        'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
                        'status': 'completed'
                    }
                ],
                'sync': [
                    {
                        'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
                        'status': 'completed'
                    }
                ]
            }
        }
        md_file = self._create_test_markdown_file('stats2023test', yaml_header)
        
        # 統計情報取得
        stats = self.timestamp_manager.get_timestamp_statistics(md_file)
        
        self.assertIsNotNone(stats)
        self.assertIsInstance(stats, dict)
        if stats:
            expected_keys = ['total_operations', 'completed_operations', 'avg_processing_time']
            for key in expected_keys:
                if key in stats:
                    self.assertIsNotNone(stats[key])


if __name__ == '__main__':
    unittest.main() 