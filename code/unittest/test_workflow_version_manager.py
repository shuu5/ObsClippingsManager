#!/usr/bin/env python3
"""
ワークフローバージョン管理テスト

WorkflowVersionManagerクラスの機能をテスト。
バージョン互換性、マイグレーション、アップデート機能を検証。
"""

import unittest
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from code.py.modules.status_management.workflow_version_manager import WorkflowVersionManager
from code.py.modules.shared.config_manager import ConfigManager
from code.py.modules.shared.integrated_logger import IntegratedLogger
from code.py.modules.shared.exceptions import ValidationError, ProcessingError


class TestWorkflowVersionManager(unittest.TestCase):
    """ワークフローバージョン管理テストクラス"""
    
    def setUp(self):
        """テスト用環境セットアップ"""
        self.test_dir = tempfile.mkdtemp(prefix="test_workflow_version_")
        self.config_manager = ConfigManager()
        self.logger = IntegratedLogger(self.config_manager)
        self.version_manager = WorkflowVersionManager(self.config_manager, self.logger)
        
        # テスト用YAMLファイル
        self.test_file = Path(self.test_dir) / "test_paper.md"
        
    def tearDown(self):
        """テスト環境クリーンアップ"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_workflow_version_manager_import(self):
        """WorkflowVersionManagerクラスのインポートテスト"""
        self.assertIsNotNone(WorkflowVersionManager)
        self.assertIsInstance(self.version_manager, WorkflowVersionManager)
    
    def test_workflow_version_manager_initialization(self):
        """WorkflowVersionManagerクラスの初期化テスト"""
        self.assertEqual(self.version_manager.current_version, "3.2")
        self.assertIsNotNone(self.version_manager.config_manager)
        self.assertIsNotNone(self.version_manager.logger)
    
    def test_check_version_compatibility_current_version(self):
        """現在バージョンとの互換性チェックテスト"""
        yaml_header = {
            'workflow_version': '3.2',
            'citation_key': 'test2023',
            'processing_status': {}
        }
        
        result = self.version_manager.check_version_compatibility(yaml_header)
        self.assertTrue(result['compatible'])
        self.assertEqual(result['migration_needed'], False)
        self.assertEqual(result['current_version'], '3.2')
        self.assertEqual(result['file_version'], '3.2')
    
    def test_check_version_compatibility_older_version(self):
        """古いバージョンとの互換性チェックテスト"""
        yaml_header = {
            'workflow_version': '3.1',
            'citation_key': 'test2023',
            'processing_status': {}
        }
        
        result = self.version_manager.check_version_compatibility(yaml_header)
        self.assertTrue(result['compatible'])
        self.assertEqual(result['migration_needed'], True)
        self.assertEqual(result['current_version'], '3.2')
        self.assertEqual(result['file_version'], '3.1')
        self.assertIn('version_diff', result)
    
    def test_check_version_compatibility_newer_version(self):
        """新しいバージョンとの互換性チェックテスト"""
        yaml_header = {
            'workflow_version': '3.3',
            'citation_key': 'test2023',
            'processing_status': {}
        }
        
        result = self.version_manager.check_version_compatibility(yaml_header)
        self.assertFalse(result['compatible'])
        self.assertEqual(result['migration_needed'], False)
        self.assertEqual(result['current_version'], '3.2')
        self.assertEqual(result['file_version'], '3.3')
        self.assertIn('error_message', result)
    
    def test_check_version_compatibility_missing_version(self):
        """バージョン情報が存在しない場合のテスト"""
        yaml_header = {
            'citation_key': 'test2023',
            'processing_status': {}
        }
        
        result = self.version_manager.check_version_compatibility(yaml_header)
        self.assertTrue(result['compatible'])
        self.assertEqual(result['migration_needed'], True)
        self.assertEqual(result['current_version'], '3.2')
        self.assertEqual(result['file_version'], 'unknown')
    
    def test_migrate_version_from_3_1_to_3_2(self):
        """バージョン3.1から3.2へのマイグレーションテスト"""
        yaml_header = {
            'citation_key': 'test2023',
            'workflow_version': '3.1',
            'processing_status': {
                'organize': 'completed',
                'sync': 'completed'
            },
            'last_updated': '2025-01-01T10:00:00'
        }
        
        migrated = self.version_manager.migrate_version(yaml_header, '3.1', '3.2')
        
        self.assertEqual(migrated['workflow_version'], '3.2')
        self.assertIn('migration_history', migrated)
        self.assertEqual(len(migrated['migration_history']), 1)
        self.assertEqual(migrated['migration_history'][0]['from_version'], '3.1')
        self.assertEqual(migrated['migration_history'][0]['to_version'], '3.2')
        self.assertIn('migrated_at', migrated['migration_history'][0])
        
        # 新しい処理ステップが追加されていることを確認
        expected_steps = ['organize', 'sync', 'fetch', 'section_parsing', 
                         'ai_citation_support', 'tagger', 'translate_abstract', 
                         'ochiai_format', 'final_sync']
        for step in expected_steps:
            self.assertIn(step, migrated['processing_status'])
    
    def test_migrate_version_from_unknown_to_3_2(self):
        """未知バージョンから3.2へのマイグレーションテスト"""
        yaml_header = {
            'citation_key': 'test2023',
            'processing_status': {
                'organize': 'completed'
            }
        }
        
        migrated = self.version_manager.migrate_version(yaml_header, 'unknown', '3.2')
        
        self.assertEqual(migrated['workflow_version'], '3.2')
        self.assertIn('migration_history', migrated)
        self.assertEqual(migrated['migration_history'][0]['from_version'], 'unknown')
        self.assertEqual(migrated['migration_history'][0]['to_version'], '3.2')
        
        # 必要なフィールドが追加されていることを確認
        self.assertIn('created_at', migrated)
        self.assertIn('tags', migrated)
        self.assertIn('citation_metadata', migrated)
    
    def test_migrate_version_unsupported_migration(self):
        """サポートされていないマイグレーションのエラーテスト"""
        yaml_header = {
            'citation_key': 'test2023',
            'workflow_version': '2.0'
        }
        
        with self.assertRaises(ValidationError) as context:
            self.version_manager.migrate_version(yaml_header, '2.0', '3.2')
        
        self.assertIn("unsupported migration", str(context.exception).lower())
    
    def test_update_version_success(self):
        """バージョン更新成功テスト"""
        # テストファイル作成
        yaml_content = """---
citation_key: test2023
workflow_version: '3.1'
processing_status:
  organize: completed
  sync: completed
last_updated: '2025-01-01T10:00:00'
---

# Test Paper

This is a test paper.
"""
        self.test_file.write_text(yaml_content, encoding='utf-8')
        
        result = self.version_manager.update_version(self.test_file)
        
        self.assertTrue(result['updated'])
        self.assertEqual(result['from_version'], '3.1')
        self.assertEqual(result['to_version'], '3.2')
        self.assertTrue(result['migration_performed'])
        
        # ファイルが更新されていることを確認
        updated_content = self.test_file.read_text(encoding='utf-8')
        self.assertIn("workflow_version: '3.2'", updated_content)
        self.assertIn("migration_history:", updated_content)
    
    def test_update_version_no_update_needed(self):
        """バージョン更新不要テスト"""
        yaml_content = """---
citation_key: test2023
workflow_version: '3.2'
processing_status:
  organize: completed
last_updated: '2025-01-01T10:00:00'
---

# Test Paper

This is a test paper.
"""
        self.test_file.write_text(yaml_content, encoding='utf-8')
        
        result = self.version_manager.update_version(self.test_file)
        
        self.assertFalse(result['updated'])
        self.assertEqual(result['from_version'], '3.2')
        self.assertEqual(result['to_version'], '3.2')
        self.assertFalse(result['migration_performed'])
    
    def test_update_version_file_not_found(self):
        """存在しないファイルの更新エラーテスト"""
        non_existent_file = Path(self.test_dir) / "non_existent.md"
        
        with self.assertRaises(ProcessingError) as context:
            self.version_manager.update_version(non_existent_file)
        
        self.assertIn("file not found", str(context.exception).lower())
    
    def test_batch_version_update_mixed_files(self):
        """混合ファイル群の一括バージョン更新テスト"""
        # 複数のテストファイル作成
        files_data = [
            ("paper1.md", "3.1", "completed"),
            ("paper2.md", "3.2", "completed"),
            ("paper3.md", "unknown", "pending")
        ]
        
        test_files = []
        for filename, version, status in files_data:
            file_path = Path(self.test_dir) / filename
            if version == "unknown":
                yaml_content = f"""---
citation_key: {filename.replace('.md', '')}
processing_status:
  organize: {status}
---

# Test Paper
"""
            else:
                yaml_content = f"""---
citation_key: {filename.replace('.md', '')}
workflow_version: '{version}'
processing_status:
  organize: {status}
---

# Test Paper
"""
            file_path.write_text(yaml_content, encoding='utf-8')
            test_files.append(file_path)
        
        results = self.version_manager.batch_version_update(self.test_dir)
        
        self.assertEqual(results['total_files'], 3)
        self.assertEqual(results['updated_files'], 2)  # paper1.md と paper3.md が更新
        self.assertEqual(results['skipped_files'], 1)  # paper2.md はスキップ
        self.assertEqual(results['failed_files'], 0)
        
        # 更新結果確認
        self.assertIn('paper1.md', [f['filename'] for f in results['update_details']])
        self.assertIn('paper3.md', [f['filename'] for f in results['update_details']])
    
    def test_get_version_history_tracking(self):
        """バージョン履歴追跡テスト"""
        yaml_header = {
            'citation_key': 'test2023',
            'workflow_version': '3.2',
            'migration_history': [
                {
                    'from_version': '3.1',
                    'to_version': '3.2',
                    'migrated_at': '2025-01-15T10:30:00.123456',
                    'migration_type': 'automatic'
                }
            ]
        }
        
        history = self.version_manager.get_version_history(yaml_header)
        
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['from_version'], '3.1')
        self.assertEqual(history[0]['to_version'], '3.2')
        self.assertEqual(history[0]['migration_type'], 'automatic')
    
    def test_validate_version_format(self):
        """バージョンフォーマット検証テスト"""
        valid_versions = ['3.2', '3.1', '3.0', '2.9']
        invalid_versions = ['3', '3.2.1', 'v3.2', '3.x', 'latest']
        
        for version in valid_versions:
            self.assertTrue(self.version_manager._validate_version_format(version))
        
        for version in invalid_versions:
            self.assertFalse(self.version_manager._validate_version_format(version))


if __name__ == '__main__':
    unittest.main() 