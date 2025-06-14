#!/usr/bin/env python3
"""
FileOrganizerテストスイート

テスト対象:
- FileOrganizerクラス基本機能
- citation_keyディレクトリ作成
- ファイル移動・リネーム
- 既存ファイル衝突回避
- organize処理統合テスト
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import yaml

# テスト環境のセットアップ
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# テスト分離用一時ディレクトリ
TEST_BASE_DIR = "/tmp/ObsClippingsManager_FileOrganizer_Test"

# インポートテスト
IMPORTS_AVAILABLE = False
IMPORT_ERROR = None

try:
    from code.py.modules.workflows.file_organizer import FileOrganizer
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORT_ERROR = str(e)
    IMPORTS_AVAILABLE = False


class TestFileOrganizerImport(unittest.TestCase):
    """FileOrganizerクラスインポートテスト"""
    
    def test_file_organizer_import(self):
        """FileOrganizerクラスのインポートテスト"""
        if not IMPORTS_AVAILABLE:
            self.fail("FileOrganizer should be importable")
        
        # クラスの存在確認
        self.assertTrue(hasattr(FileOrganizer, '__init__'))
        self.assertTrue(hasattr(FileOrganizer, 'organize_file'))
        self.assertTrue(hasattr(FileOrganizer, 'create_citation_directory'))


class TestFileOrganizerBasic(unittest.TestCase):
    """FileOrganizer基本機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = Path(TEST_BASE_DIR)
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # テスト用ディレクトリ構造作成
        self.clippings_dir = self.test_dir / "Clippings"
        self.clippings_dir.mkdir()
        
        # テスト用Markdownファイル作成
        self.test_md_content = """---
citation_key: smith2024a
workflow_version: '3.2'
last_updated: '2025-01-15T09:00:00.123456'
processing_status:
  organize: pending
  sync: pending
  fetch: pending
tags: []
---

# Test Paper Title

This is a test paper content.
"""
        self.test_md_file = self.clippings_dir / "smith2024a_paper.md"
        self.test_md_file.write_text(self.test_md_content, encoding='utf-8')
        
        # Mock設定
        self.mock_config = Mock()
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_file_organizer_initialization(self):
        """FileOrganizerクラスの初期化テスト"""
        organizer = FileOrganizer(self.mock_config, self.mock_logger)
        
        self.assertIsNotNone(organizer)
        self.assertEqual(organizer.config_manager, self.mock_config)
        self.assertEqual(organizer.logger, self.mock_logger.get_logger.return_value)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_create_citation_directory_success(self):
        """citation_keyディレクトリ作成成功テスト"""
        organizer = FileOrganizer(self.mock_config, self.mock_logger)
        
        citation_key = "smith2024a"
        target_dir = organizer.create_citation_directory(str(self.clippings_dir), citation_key)
        
        # ディレクトリが作成されたか確認
        expected_dir = self.clippings_dir / citation_key
        self.assertTrue(expected_dir.exists())
        self.assertTrue(expected_dir.is_dir())
        self.assertEqual(Path(target_dir), expected_dir)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_create_citation_directory_already_exists(self):
        """既存ディレクトリの処理テスト"""
        organizer = FileOrganizer(self.mock_config, self.mock_logger)
        
        citation_key = "smith2024a"
        # 事前にディレクトリを作成
        existing_dir = self.clippings_dir / citation_key
        existing_dir.mkdir()
        
        target_dir = organizer.create_citation_directory(str(self.clippings_dir), citation_key)
        
        # ディレクトリが存在し、処理が正常に完了することを確認
        self.assertTrue(existing_dir.exists())
        self.assertEqual(Path(target_dir), existing_dir)


class TestFileOrganizerFileOperations(unittest.TestCase):
    """FileOrganizerファイル操作テスト"""
    
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
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_organize_file_basic_move(self):
        """基本的なファイル移動テスト"""
        organizer = FileOrganizer(self.mock_config, self.mock_logger)
        
        # テスト用ファイル作成
        source_file = self.clippings_dir / "smith2024a_paper.md"
        source_content = """---
citation_key: smith2024a
processing_status:
  organize: pending
---

# Test Paper
"""
        source_file.write_text(source_content, encoding='utf-8')
        
        # organize実行
        result = organizer.organize_file(str(source_file), str(self.clippings_dir))
        
        # 結果確認
        self.assertTrue(result)
        
        # 新しい場所にファイルが移動されているか確認
        target_dir = self.clippings_dir / "smith2024a"
        target_file = target_dir / "smith2024a.md"
        
        self.assertTrue(target_dir.exists())
        self.assertTrue(target_file.exists())
        self.assertFalse(source_file.exists())  # 元ファイルは削除されている
        
        # ファイル内容とYAMLヘッダー更新確認
        content = target_file.read_text(encoding='utf-8')
        self.assertIn("organize: completed", content)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_organize_file_with_collision(self):
        """ファイル衝突時の処理テスト"""
        organizer = FileOrganizer(self.mock_config, self.mock_logger)
        
        citation_key = "smith2024a"
        
        # 既存のファイル構造を作成
        target_dir = self.clippings_dir / citation_key
        target_dir.mkdir()
        existing_file = target_dir / f"{citation_key}.md"
        existing_file.write_text("Existing content", encoding='utf-8')
        
        # 新しいファイル作成
        source_file = self.clippings_dir / f"{citation_key}_new.md"
        source_content = """---
citation_key: smith2024a
processing_status:
  organize: pending
---

# New Paper
"""
        source_file.write_text(source_content, encoding='utf-8')
        
        # organize実行
        result = organizer.organize_file(str(source_file), str(self.clippings_dir))
        
        # 結果確認
        self.assertTrue(result)
        
        # 衝突回避処理の確認（バックアップまたはタイムスタンプ付きファイル名）
        files_in_target = list(target_dir.glob("*.md"))
        self.assertGreaterEqual(len(files_in_target), 2)  # 最低2つのファイルが存在


class TestFileOrganizerIntegration(unittest.TestCase):
    """FileOrganizer統合テスト"""
    
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
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_organize_multiple_files(self):
        """複数ファイルの一括organize処理テスト"""
        organizer = FileOrganizer(self.mock_config, self.mock_logger)
        
        # 複数のテストファイル作成
        test_files = [
            ("smith2024a_paper1.md", "smith2024a"),
            ("jones2024b_paper2.md", "jones2024b"),
            ("davis2023c_paper3.md", "davis2023c")
        ]
        
        source_files = []
        for filename, citation_key in test_files:
            file_path = self.clippings_dir / filename
            content = f"""---
citation_key: {citation_key}
processing_status:
  organize: pending
---

# Paper {citation_key}
"""
            file_path.write_text(content, encoding='utf-8')
            source_files.append(str(file_path))
        
        # 一括organize実行
        results = []
        for source_file in source_files:
            result = organizer.organize_file(source_file, str(self.clippings_dir))
            results.append(result)
        
        # 全て成功したか確認
        self.assertTrue(all(results))
        
        # 各ディレクトリとファイルが正しく作成されたか確認
        for _, citation_key in test_files:
            target_dir = self.clippings_dir / citation_key
            target_file = target_dir / f"{citation_key}.md"
            
            self.assertTrue(target_dir.exists(), f"Directory not created for {citation_key}")
            self.assertTrue(target_file.exists(), f"File not moved for {citation_key}")
            
            # YAML処理状態の確認
            content = target_file.read_text(encoding='utf-8')
            self.assertIn("organize: completed", content)
    
    @unittest.skipIf(not IMPORTS_AVAILABLE, f"Import failed: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}")
    def test_organize_invalid_yaml_header(self):
        """無効なYAMLヘッダーファイルの処理テスト"""
        organizer = FileOrganizer(self.mock_config, self.mock_logger)
        
        # 無効なYAMLヘッダーファイル作成
        source_file = self.clippings_dir / "invalid_yaml.md"
        content = """---
citation_key: invalid_key
processing_status:
  organize: pending
  missing_quote: invalid yaml "content
---

# Invalid YAML Paper
"""
        source_file.write_text(content, encoding='utf-8')
        
        # organize実行（エラーハンドリング確認）
        result = organizer.organize_file(str(source_file), str(self.clippings_dir))
        
        # 適切にエラー処理されることを確認
        # （実装により、修復処理またはスキップ処理が実行される）
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main() 