#!/usr/bin/env python3
"""
状態管理機能のテスト (YAML方式 v3.0)

YAMLヘッダーベースの状態管理機能をテストします。
"""

import unittest
import tempfile
import os
import yaml
from pathlib import Path
import sys
from datetime import datetime, timezone

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent / 'py'
sys.path.insert(0, str(project_root))

from modules.shared.status_manager import StatusManager, ProcessStatus
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.shared.exceptions import ObsClippingsError


class TestYAMLHeaderProcessing(unittest.TestCase):
    """YAMLヘッダー処理のテスト"""
    
    def setUp(self):
        """各テストの前に実行"""
        self.temp_dir = tempfile.mkdtemp()
        self.clippings_dir = os.path.join(self.temp_dir, "Clippings")
        os.makedirs(self.clippings_dir)
        
        # StatusManager初期化
        config_manager = ConfigManager()
        logger = IntegratedLogger()
        self.status_manager = StatusManager(config_manager, logger)
    
    def test_parse_yaml_header_existing(self):
        """既存YAMLヘッダーの解析テスト"""
        # テスト用.mdファイル作成
        smith_dir = os.path.join(self.clippings_dir, "smith2023test")
        os.makedirs(smith_dir)
        
        md_content = """---
obsclippings_metadata:
  citation_key: "smith2023test"
  processing_status:
    organize: "completed"
    sync: "completed"
    fetch: "pending"
    parse: "pending"
  last_updated: "2025-01-15T10:30:00Z"
  source_doi: "10.1000/example.doi"
  workflow_version: "3.0"
---

# Smith et al. (2023) - Example Paper

論文の内容...
"""
        
        md_file = os.path.join(smith_dir, "smith2023test.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # YAMLヘッダー解析
        metadata = self.status_manager.parse_yaml_header(Path(md_file))
        
        # 検証
        self.assertIn('obsclippings_metadata', metadata)
        self.assertEqual(metadata['obsclippings_metadata']['citation_key'], 'smith2023test')
        self.assertEqual(metadata['obsclippings_metadata']['processing_status']['organize'], 'completed')
        self.assertEqual(metadata['obsclippings_metadata']['processing_status']['fetch'], 'pending')
    
    def test_parse_yaml_header_missing(self):
        """YAMLヘッダーなしファイルの処理テスト"""
        # YAMLヘッダーなしの.mdファイル作成
        jones_dir = os.path.join(self.clippings_dir, "jones2024neural")
        os.makedirs(jones_dir)
        
        md_content = """# Jones et al. (2024) - Neural Networks

論文の内容...
"""
        
        md_file = os.path.join(jones_dir, "jones2024neural.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # YAMLヘッダー解析
        metadata = self.status_manager.parse_yaml_header(Path(md_file))
        
        # 空辞書が返されることを確認
        self.assertEqual(metadata, {})
    
    def test_write_yaml_header_new(self):
        """新規YAMLヘッダー作成テスト"""
        # YAMLヘッダーなしの.mdファイル作成
        new_dir = os.path.join(self.clippings_dir, "new2025paper")
        os.makedirs(new_dir)
        
        original_content = """# New Paper (2025)

論文の内容...
"""
        
        md_file = os.path.join(new_dir, "new2025paper.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        # 新しいYAMLヘッダーメタデータ
        metadata = {
            'obsclippings_metadata': {
                'citation_key': 'new2025paper',
                'processing_status': {
                    'organize': 'completed',
                    'sync': 'pending',
                    'fetch': 'pending',
                    'parse': 'pending'
                },
                'last_updated': '2025-01-15T12:00:00Z',
                'workflow_version': '3.0'
            }
        }
        
        # YAMLヘッダー書き込み
        success = self.status_manager.write_yaml_header(Path(md_file), metadata)
        self.assertTrue(success)
        
        # ファイルを読み直して確認
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('---', content)
        self.assertIn('obsclippings_metadata:', content)
        self.assertIn('citation_key: new2025paper', content)
        self.assertIn('# New Paper (2025)', content)  # 元の内容が保持されている
    
    def test_write_yaml_header_update(self):
        """既存YAMLヘッダー更新テスト"""
        # 既存YAMLヘッダー付きファイル作成
        update_dir = os.path.join(self.clippings_dir, "update2023test")
        os.makedirs(update_dir)
        
        original_content = """---
obsclippings_metadata:
  citation_key: "update2023test"
  processing_status:
    organize: "pending"
    sync: "pending"
    fetch: "pending"
    parse: "pending"
  last_updated: "2025-01-01T10:00:00Z"
  workflow_version: "3.0"
---

# Update Test (2023)

論文の内容...
"""
        
        md_file = os.path.join(update_dir, "update2023test.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        # 更新されたメタデータ
        updated_metadata = {
            'obsclippings_metadata': {
                'citation_key': 'update2023test',
                'processing_status': {
                    'organize': 'completed',
                    'sync': 'completed',
                    'fetch': 'pending',
                    'parse': 'pending'
                },
                'last_updated': '2025-01-15T15:30:00Z',
                'workflow_version': '3.0'
            }
        }
        
        # YAMLヘッダー更新
        success = self.status_manager.write_yaml_header(Path(md_file), updated_metadata)
        self.assertTrue(success)
        
        # 更新確認
        updated_metadata_read = self.status_manager.parse_yaml_header(Path(md_file))
        self.assertEqual(
            updated_metadata_read['obsclippings_metadata']['processing_status']['organize'], 
            'completed'
        )
        self.assertEqual(
            updated_metadata_read['obsclippings_metadata']['last_updated'], 
            '2025-01-15T15:30:00Z'
        )
    
    def test_yaml_format_validation(self):
        """YAMLフォーマット検証テスト"""
        # 無効なYAMLファイルを作成
        invalid_dir = os.path.join(self.clippings_dir, "invalid2023yaml")
        os.makedirs(invalid_dir)
        
        invalid_content = """---
obsclippings_metadata:
  citation_key: "invalid2023yaml"
  processing_status:
    organize: "completed"
    sync: [incomplete yaml structure
---

# Invalid YAML Test

論文の内容...
"""
        
        md_file = os.path.join(invalid_dir, "invalid2023yaml.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(invalid_content)
        
        # YAML解析でエラーハンドリングが適切に動作するか確認
        metadata = self.status_manager.parse_yaml_header(Path(md_file))
        self.assertEqual(metadata, {})  # エラー時は空辞書を返す


class TestStatusManagerV3(unittest.TestCase):
    """StatusManager v3.0のテスト"""
    
    def setUp(self):
        """各テストの前に実行"""
        self.temp_dir = tempfile.mkdtemp()
        self.clippings_dir = os.path.join(self.temp_dir, "Clippings")
        self.bibtex_file = os.path.join(self.temp_dir, "CurrentManuscript.bib")
        os.makedirs(self.clippings_dir)
        
        # StatusManager初期化
        config_manager = ConfigManager()
        logger = IntegratedLogger()
        self.status_manager = StatusManager(config_manager, logger)
        
        # テスト用サンプルファイル作成
        self._create_sample_papers()
    
    def _create_sample_papers(self):
        """テスト用サンプル論文ファイル作成"""
        # 1. smith2023test (一部状態あり)
        smith_dir = os.path.join(self.clippings_dir, "smith2023test")
        os.makedirs(smith_dir)
        
        smith_content = """---
obsclippings_metadata:
  citation_key: "smith2023test"
  processing_status:
    organize: "completed"
    sync: "completed"
    fetch: "pending"
    parse: "pending"
  last_updated: "2025-01-15T10:30:00Z"
  workflow_version: "3.0"
---

# Smith et al. (2023) - Test Paper

論文の内容...
"""
        
        with open(os.path.join(smith_dir, "smith2023test.md"), 'w', encoding='utf-8') as f:
            f.write(smith_content)
        
        # 2. jones2024neural (全て未処理)
        jones_dir = os.path.join(self.clippings_dir, "jones2024neural")
        os.makedirs(jones_dir)
        
        jones_content = """# Jones et al. (2024) - Neural Networks

論文の内容... (YAMLヘッダーなし)
"""
        
        with open(os.path.join(jones_dir, "jones2024neural.md"), 'w', encoding='utf-8') as f:
            f.write(jones_content)
        
        # 3. wilson2025ai (失敗状態含む)
        wilson_dir = os.path.join(self.clippings_dir, "wilson2025ai")
        os.makedirs(wilson_dir)
        
        wilson_content = """---
obsclippings_metadata:
  citation_key: "wilson2025ai"
  processing_status:
    organize: "completed"
    sync: "failed"
    fetch: "pending"
    parse: "pending"
  last_updated: "2025-01-14T18:45:00Z"
  workflow_version: "3.0"
---

# Wilson et al. (2025) - AI Research

論文の内容...
"""
        
        with open(os.path.join(wilson_dir, "wilson2025ai.md"), 'w', encoding='utf-8') as f:
            f.write(wilson_content)
    
    def test_load_md_statuses(self):
        """Clippingsディレクトリからの状態読み込みテスト"""
        statuses = self.status_manager.load_md_statuses(self.clippings_dir)
        
        # 3つの論文が読み込まれることを確認
        self.assertEqual(len(statuses), 3)
        
        # smith2023test: 一部完了状態
        smith_status = statuses.get('smith2023test', {})
        self.assertEqual(smith_status.get('organize'), ProcessStatus.COMPLETED)
        self.assertEqual(smith_status.get('sync'), ProcessStatus.COMPLETED)
        self.assertEqual(smith_status.get('fetch'), ProcessStatus.PENDING)
        
        # jones2024neural: 全て未設定（pending）
        jones_status = statuses.get('jones2024neural', {})
        self.assertEqual(jones_status.get('organize'), ProcessStatus.PENDING)
        self.assertEqual(jones_status.get('sync'), ProcessStatus.PENDING)
        
        # wilson2025ai: 失敗状態含む
        wilson_status = statuses.get('wilson2025ai', {})
        self.assertEqual(wilson_status.get('organize'), ProcessStatus.COMPLETED)
        self.assertEqual(wilson_status.get('sync'), ProcessStatus.FAILED)
    
    def test_update_status_yaml(self):
        """YAMLヘッダー経由の状態更新テスト"""
        # jones2024neural のorganize状態を更新
        success = self.status_manager.update_status(
            self.clippings_dir, 
            'jones2024neural',
            'organize',
            ProcessStatus.COMPLETED
        )
        self.assertTrue(success)
        
        # 更新確認
        statuses = self.status_manager.load_md_statuses(self.clippings_dir)
        jones_status = statuses.get('jones2024neural', {})
        self.assertEqual(jones_status.get('organize'), ProcessStatus.COMPLETED)
        
        # 他の状態は変更されていないことを確認
        self.assertEqual(jones_status.get('sync'), ProcessStatus.PENDING)
    
    def test_batch_update_yaml(self):
        """一括状態更新テスト（YAML）"""
        updates = {
            'smith2023test': {
                'fetch': ProcessStatus.COMPLETED
            },
            'jones2024neural': {
                'organize': ProcessStatus.COMPLETED,
                'sync': ProcessStatus.COMPLETED
            }
        }
        
        success = self.status_manager.batch_update_statuses(self.clippings_dir, updates)
        self.assertTrue(success)
        
        # 更新確認
        statuses = self.status_manager.load_md_statuses(self.clippings_dir)
        
        smith_status = statuses.get('smith2023test', {})
        self.assertEqual(smith_status.get('fetch'), ProcessStatus.COMPLETED)
        
        jones_status = statuses.get('jones2024neural', {})
        self.assertEqual(jones_status.get('organize'), ProcessStatus.COMPLETED)
        self.assertEqual(jones_status.get('sync'), ProcessStatus.COMPLETED)
    
    def test_get_papers_needing_processing(self):
        """処理が必要な論文リストの取得テスト"""
        # organize処理が必要な論文
        papers = self.status_manager.get_papers_needing_processing(
            self.clippings_dir, 'organize'
        )
        self.assertIn('jones2024neural', papers)  # pendingなので含まれる
        self.assertNotIn('smith2023test', papers)  # completedなので含まれない
        
        # sync処理が必要な論文（失敗も含む）
        papers = self.status_manager.get_papers_needing_processing(
            self.clippings_dir, 'sync', include_failed=True
        )
        self.assertIn('jones2024neural', papers)  # pending
        self.assertIn('wilson2025ai', papers)     # failed
        self.assertNotIn('smith2023test', papers) # completed
        
        # sync処理が必要な論文（失敗除外）
        papers = self.status_manager.get_papers_needing_processing(
            self.clippings_dir, 'sync', include_failed=False
        )
        self.assertIn('jones2024neural', papers)   # pending
        self.assertNotIn('wilson2025ai', papers)   # failed (excluded)
    
    def test_reset_statuses(self):
        """状態リセットテスト"""
        # 特定論文の状態をリセット
        success = self.status_manager.reset_statuses(
            self.clippings_dir, 'smith2023test'
        )
        self.assertTrue(success)
        
        # リセット確認
        statuses = self.status_manager.load_md_statuses(self.clippings_dir)
        smith_status = statuses.get('smith2023test', {})
        self.assertEqual(smith_status.get('organize'), ProcessStatus.PENDING)
        self.assertEqual(smith_status.get('sync'), ProcessStatus.PENDING)
        self.assertEqual(smith_status.get('fetch'), ProcessStatus.PENDING)
        self.assertEqual(smith_status.get('parse'), ProcessStatus.PENDING)
    
    def test_consistency_check_yaml(self):
        """BibTeX-Clippings整合性チェック（YAML）"""
        # BibTeXファイル作成
        bibtex_content = """@article{smith2023test,
    title={Test Paper},
    author={Smith, John},
    year={2023}
}

@article{jones2024neural,
    title={Neural Networks},
    author={Jones, Robert},
    year={2024}
}

@article{missing2025paper,
    title={Missing Paper},
    author={Missing, Author},
    year={2025}
}
"""
        
        with open(self.bibtex_file, 'w', encoding='utf-8') as f:
            f.write(bibtex_content)
        
        # 整合性チェック実行
        consistency_report = self.status_manager.check_status_consistency(
            self.bibtex_file, self.clippings_dir
        )
        
        # 検証
        self.assertIn('missing_directories', consistency_report)
        self.assertIn('orphaned_directories', consistency_report)
        self.assertIn('status_inconsistencies', consistency_report)
        
        # missing2025paperがmissing_directoriesに含まれることを確認
        self.assertIn('missing2025paper', consistency_report['missing_directories'])
        
        # wilson2025aiがorphaned_directoriesに含まれることを確認
        self.assertIn('wilson2025ai', consistency_report['orphaned_directories'])


class TestStatusManagerUtilities(unittest.TestCase):
    """StatusManagerのユーティリティ機能テスト"""
    
    def setUp(self):
        """各テストの前に実行"""
        self.temp_dir = tempfile.mkdtemp()
        self.clippings_dir = os.path.join(self.temp_dir, "Clippings")
        os.makedirs(self.clippings_dir)
        
        # StatusManager初期化
        config_manager = ConfigManager()
        logger = IntegratedLogger()
        self.status_manager = StatusManager(config_manager, logger)
    
    def test_ensure_yaml_header(self):
        """YAMLヘッダー自動初期化テスト"""
        # ヘッダーなしファイル作成
        test_dir = os.path.join(self.clippings_dir, "test2025new")
        os.makedirs(test_dir)
        
        test_content = """# Test New Paper (2025)

論文の内容...
"""
        
        md_file = os.path.join(test_dir, "test2025new.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # YAMLヘッダー初期化
        success = self.status_manager.ensure_yaml_header(Path(md_file), 'test2025new')
        self.assertTrue(success)
        
        # 初期化確認
        metadata = self.status_manager.parse_yaml_header(Path(md_file))
        self.assertIn('obsclippings_metadata', metadata)
        self.assertEqual(metadata['obsclippings_metadata']['citation_key'], 'test2025new')
        
        # 元のコンテンツが保持されていることを確認
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('# Test New Paper (2025)', content)
    
    def test_get_md_file_path(self):
        """Markdownファイルパス取得テスト"""
        expected_path = Path(self.clippings_dir) / "sample2023paper" / "sample2023paper.md"
        actual_path = self.status_manager.get_md_file_path(self.clippings_dir, "sample2023paper")
        
        self.assertEqual(actual_path, expected_path)


if __name__ == '__main__':
    unittest.main() 