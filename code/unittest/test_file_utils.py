#!/usr/bin/env python3
"""
ファイルシステムユーティリティ（File System Utilities）テストスイート

テスト対象:
- ファイル操作ユーティリティ
- ディレクトリ管理機能
- パス正規化・検証
- ファイル検索・フィルタリング
- バックアップ・リストア機能
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# テスト環境のセットアップ
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# テスト分離用一時ディレクトリ
TEST_BASE_DIR = "/tmp/ObsClippingsManager_FileUtils_Test"


class TestFileSystemUtilities(unittest.TestCase):
    """ファイルシステムユーティリティ基本機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = Path(TEST_BASE_DIR)
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # テスト用ファイル・ディレクトリ作成
        self.test_file = self.test_dir / "test_file.txt"
        self.test_file.write_text("test content")
        
        self.test_subdir = self.test_dir / "subdir"
        self.test_subdir.mkdir()
        
        self.nested_file = self.test_subdir / "nested.yaml"
        self.nested_file.write_text("yaml: content")
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_file_utils_import(self):
        """FileUtilsクラスのインポートテスト"""
        try:
            from py.modules.shared_modules.file_utils import FileUtils
            self.assertTrue(True, "FileUtilsクラスのインポートが成功")
        except ImportError:
            self.skipTest("FileUtils not implemented yet")
    
    def test_file_utils_initialization(self):
        """FileUtilsクラスの初期化テスト"""
        try:
            from py.modules.shared_modules.file_utils import FileUtils
            file_utils = FileUtils()
            self.assertIsNotNone(file_utils)
        except ImportError:
            self.skipTest("FileUtils not implemented yet")


class TestFileOperations(unittest.TestCase):
    """ファイル操作機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = Path(TEST_BASE_DIR) / "operations"
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_safe_file_copy(self):
        """安全なファイルコピーテスト"""
        try:
            from py.modules.shared_modules.file_utils import FileUtils
            
            # テスト用ファイル作成
            source = self.test_dir / "source.txt"
            source.write_text("original content")
            destination = self.test_dir / "destination.txt"
            
            file_utils = FileUtils()
            success = file_utils.safe_copy(source, destination)
            
            self.assertTrue(success)
            self.assertTrue(destination.exists())
            self.assertEqual(destination.read_text(), "original content")
        except ImportError:
            self.skipTest("FileUtils not implemented yet")
    
    def test_safe_file_move(self):
        """安全なファイル移動テスト"""
        try:
            from py.modules.shared_modules.file_utils import FileUtils
            
            # テスト用ファイル作成
            source = self.test_dir / "move_source.txt"
            source.write_text("move content")
            destination = self.test_dir / "move_destination.txt"
            
            file_utils = FileUtils()
            success = file_utils.safe_move(source, destination)
            
            self.assertTrue(success)
            self.assertFalse(source.exists())
            self.assertTrue(destination.exists())
            self.assertEqual(destination.read_text(), "move content")
        except ImportError:
            self.skipTest("FileUtils not implemented yet")
    
    def test_file_copy_with_existing_destination(self):
        """既存ファイルへのコピー処理テスト"""
        try:
            from py.modules.shared_modules.file_utils import FileUtils
            
            # テスト用ファイル作成
            source = self.test_dir / "source.txt"
            source.write_text("new content")
            destination = self.test_dir / "existing.txt"
            destination.write_text("existing content")
            
            file_utils = FileUtils()
            
            # overwrite=Falseの場合
            success = file_utils.safe_copy(source, destination, overwrite=False)
            self.assertFalse(success)
            self.assertEqual(destination.read_text(), "existing content")
            
            # overwrite=Trueの場合
            success = file_utils.safe_copy(source, destination, overwrite=True)
            self.assertTrue(success)
            self.assertEqual(destination.read_text(), "new content")
        except ImportError:
            self.skipTest("FileUtils not implemented yet")
    
    def test_atomic_file_write(self):
        """アトミックファイル書き込みテスト"""
        try:
            from py.modules.shared_modules.file_utils import FileUtils
            
            target_file = self.test_dir / "atomic.txt"
            content = "atomic write content"
            
            file_utils = FileUtils()
            success = file_utils.atomic_write(target_file, content)
            
            self.assertTrue(success)
            self.assertTrue(target_file.exists())
            self.assertEqual(target_file.read_text(), content)
        except ImportError:
            self.skipTest("FileUtils not implemented yet")


class TestDirectoryOperations(unittest.TestCase):
    """ディレクトリ操作機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = Path(TEST_BASE_DIR) / "directories"
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_ensure_directory_exists(self):
        """ディレクトリ存在確保テスト"""
        try:
            from py.modules.shared_modules.file_utils import FileUtils
            
            target_dir = self.test_dir / "new" / "nested" / "directory"
            
            file_utils = FileUtils()
            success = file_utils.ensure_directory(target_dir)
            
            self.assertTrue(success)
            self.assertTrue(target_dir.exists())
            self.assertTrue(target_dir.is_dir())
        except ImportError:
            self.skipTest("FileUtils not implemented yet")
    
    def test_safe_directory_remove(self):
        """安全なディレクトリ削除テスト"""
        try:
            from py.modules.shared_modules.file_utils import FileUtils
            
            # テスト用ディレクトリ構造作成
            target_dir = self.test_dir / "to_remove"
            target_dir.mkdir()
            (target_dir / "file1.txt").write_text("content1")
            (target_dir / "subdir").mkdir()
            (target_dir / "subdir" / "file2.txt").write_text("content2")
            
            file_utils = FileUtils()
            success = file_utils.safe_remove_directory(target_dir)
            
            self.assertTrue(success)
            self.assertFalse(target_dir.exists())
        except ImportError:
            self.skipTest("FileUtils not implemented yet")
    
    def test_directory_size_calculation(self):
        """ディレクトリサイズ計算テスト"""
        try:
            from py.modules.shared_modules.file_utils import FileUtils
            
            # テスト用ファイル作成
            (self.test_dir / "file1.txt").write_text("1" * 100)
            (self.test_dir / "file2.txt").write_text("2" * 200)
            
            file_utils = FileUtils()
            size = file_utils.get_directory_size(self.test_dir)
            
            self.assertGreaterEqual(size, 300)  # 最低でも300バイト
        except ImportError:
            self.skipTest("FileUtils not implemented yet")


class TestPathUtils(unittest.TestCase):
    """パス管理ユーティリティテスト"""
    
    def test_path_validation(self):
        """パス検証機能テスト"""
        try:
            from py.modules.shared_modules.file_utils import PathUtils
            
            path_utils = PathUtils()
            
            # 有効なパス
            self.assertTrue(path_utils.is_valid_path("/valid/path"))
            self.assertTrue(path_utils.is_valid_path("relative/path"))
            
            # 無効なパス
            self.assertFalse(path_utils.is_valid_path(""))
            self.assertFalse(path_utils.is_valid_path("path\x00with\x00null"))
        except ImportError:
            self.skipTest("PathUtils not implemented yet")
    
    def test_path_normalization(self):
        """パス正規化テスト"""
        try:
            from py.modules.shared_modules.file_utils import PathUtils
            
            path_utils = PathUtils()
            
            # パス正規化（絶対パス解決）
            normalized = path_utils.normalize_path("./path/../to//file.txt")
            # 現在の作業ディレクトリからの相対パスが解決されるため、絶対パスになる
            self.assertTrue(normalized.endswith("to/file.txt") or "to/file.txt" in normalized)
        except ImportError:
            self.skipTest("PathUtils not implemented yet")
    
    def test_relative_path_calculation(self):
        """相対パス計算テスト"""
        try:
            from py.modules.shared_modules.file_utils import PathUtils
            
            path_utils = PathUtils()
            
            base = "/home/user/project"
            target = "/home/user/project/subdir/file.txt"
            relative = path_utils.get_relative_path(base, target)
            
            self.assertEqual(relative, "subdir/file.txt")
        except ImportError:
            self.skipTest("PathUtils not implemented yet")
    
    def test_sanitize_filename(self):
        """ファイル名サニタイズテスト"""
        try:
            from py.modules.shared_modules.file_utils import PathUtils
            
            # 無効な文字を含むファイル名
            invalid_filename = 'file<name>with:invalid*chars?.txt'
            sanitized = PathUtils.sanitize_filename(invalid_filename)
            
            # 無効な文字が置換されているか確認
            self.assertNotIn('<', sanitized)
            self.assertNotIn('>', sanitized)
            self.assertNotIn(':', sanitized)
            self.assertNotIn('*', sanitized)
            self.assertNotIn('?', sanitized)
        except ImportError:
            self.skipTest("PathUtils not implemented yet")
    
    def test_citation_key_extraction(self):
        """citation_key抽出テスト"""
        try:
            from py.modules.shared_modules.file_utils import PathUtils
            
            # 標準的なcitation_keyパターン
            test_cases = [
                ("Smith2024a_example.md", "Smith2024a"),
                ("JohnsonLee2024b_title.md", "JohnsonLee2024b"),
                ("author_2024_paper.md", "author_2024"),
                ("invalid_filename.md", None),
            ]
            
            for filename, expected in test_cases:
                result = PathUtils.get_citation_key_from_filename(filename)
                self.assertEqual(result, expected, f"Failed for {filename}")
        except ImportError:
            self.skipTest("PathUtils not implemented yet")
    
    def test_safe_directory_name_generation(self):
        """安全なディレクトリ名生成テスト"""
        try:
            from py.modules.shared_modules.file_utils import PathUtils
            
            citation_key = "Smith2024a:test/invalid*chars"
            safe_name = PathUtils.generate_safe_directory_name(citation_key)
            
            # 無効な文字が含まれていないか確認
            self.assertNotIn(':', safe_name)
            self.assertNotIn('/', safe_name)
            self.assertNotIn('*', safe_name)
            self.assertNotIn('.', safe_name)
        except ImportError:
            self.skipTest("PathUtils not implemented yet")
    
    def test_clippings_file_path_building(self):
        """クリッピングファイルパス構築テスト"""
        try:
            from py.modules.shared_modules.file_utils import PathUtils
            
            base_dir = "/tmp/test_clippings"
            citation_key = "Smith2024a"
            title = "Example Paper Title"
            
            file_path = PathUtils.build_clippings_file_path(base_dir, citation_key, title)
            
            self.assertTrue(str(file_path).endswith(".md"))
            self.assertIn(citation_key, str(file_path))
        except ImportError:
            self.skipTest("PathUtils not implemented yet")


class TestFileSearch(unittest.TestCase):
    """ファイル検索・フィルタリング機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = Path(TEST_BASE_DIR) / "search"
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # テスト用ファイル構造作成
        (self.test_dir / "file1.txt").write_text("content")
        (self.test_dir / "file2.md").write_text("markdown")
        (self.test_dir / "file3.yaml").write_text("yaml")
        
        subdir = self.test_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested")
        (subdir / "other.log").write_text("log")
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_find_files_by_extension(self):
        """拡張子によるファイル検索テスト"""
        try:
            from py.modules.shared_modules.file_utils import FileSearch
            
            search = FileSearch()
            txt_files = search.find_by_extension(self.test_dir, ".txt")
            
            self.assertGreaterEqual(len(txt_files), 2)
            self.assertTrue(any("file1.txt" in str(f) for f in txt_files))
            self.assertTrue(any("nested.txt" in str(f) for f in txt_files))
        except ImportError:
            self.skipTest("FileSearch not implemented yet")
    
    def test_find_files_by_pattern(self):
        """パターンによるファイル検索テスト"""
        try:
            from py.modules.shared_modules.file_utils import FileSearch
            
            search = FileSearch()
            files = search.find_by_pattern(self.test_dir, "file*.txt")
            
            self.assertGreaterEqual(len(files), 1)
            self.assertTrue(any("file1.txt" in str(f) for f in files))
        except ImportError:
            self.skipTest("FileSearch not implemented yet")
    
    def test_recursive_search(self):
        """再帰的検索テスト"""
        try:
            from py.modules.shared_modules.file_utils import FileSearch
            
            search = FileSearch()
            all_files = search.find_files(self.test_dir, recursive=True)
            
            self.assertGreaterEqual(len(all_files), 5)
        except ImportError:
            self.skipTest("FileSearch not implemented yet")


class TestBackupUtilities(unittest.TestCase):
    """バックアップ・リストア機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.test_dir = Path(TEST_BASE_DIR) / "backup"
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        self.source_file = self.test_dir / "source.txt"
        self.source_file.write_text("original content")
    
    def tearDown(self):
        """テストクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_create_backup(self):
        """バックアップ作成テスト"""
        try:
            from py.modules.shared_modules.file_utils import BackupManager
            
            backup_manager = BackupManager()
            backup_path = backup_manager.create_backup(self.source_file)
            
            self.assertIsNotNone(backup_path)
            self.assertTrue(Path(backup_path).exists())
            self.assertEqual(Path(backup_path).read_text(), "original content")
        except ImportError:
            self.skipTest("BackupManager not implemented yet")
    
    def test_restore_from_backup(self):
        """バックアップからのリストアテスト"""
        try:
            from py.modules.shared_modules.file_utils import BackupManager
            
            backup_manager = BackupManager()
            backup_path = backup_manager.create_backup(self.source_file)
            
            # ファイルを変更
            self.source_file.write_text("modified content")
            
            # リストア
            success = backup_manager.restore_backup(backup_path, self.source_file)
            
            self.assertTrue(success)
            self.assertEqual(self.source_file.read_text(), "original content")
        except ImportError:
            self.skipTest("BackupManager not implemented yet")
    
    def test_backup_cleanup(self):
        """バックアップクリーンアップテスト"""
        try:
            from py.modules.shared_modules.file_utils import BackupManager
            
            backup_manager = BackupManager()
            backup_path = backup_manager.create_backup(self.source_file)
            
            # クリーンアップ
            success = backup_manager.cleanup_backup(backup_path)
            
            self.assertTrue(success)
            self.assertFalse(Path(backup_path).exists())
        except ImportError:
            self.skipTest("BackupManager not implemented yet")


class TestStringUtils(unittest.TestCase):
    """文字列処理ユーティリティテスト"""
    
    def test_clean_text(self):
        """テキストクリーニングテスト"""
        try:
            from py.modules.shared_modules.file_utils import StringUtils
            
            # 連続する空白の正規化
            text = "  This   has    multiple   spaces  "
            cleaned = StringUtils.clean_text(text)
            self.assertEqual(cleaned, "This has multiple spaces")
            
            # 空文字列の処理
            self.assertEqual(StringUtils.clean_text(""), "")
            self.assertEqual(StringUtils.clean_text(None), "")
        except ImportError:
            self.skipTest("StringUtils not implemented yet")
    
    def test_truncate_text(self):
        """テキスト切り詰めテスト"""
        try:
            from py.modules.shared_modules.file_utils import StringUtils
            
            # 通常の切り詰め
            text = "This is a very long text that needs to be truncated"
            truncated = StringUtils.truncate_text(text, 20)
            self.assertEqual(len(truncated), 20)
            self.assertTrue(truncated.endswith("..."))
            
            # 短いテキストの場合
            short_text = "Short"
            result = StringUtils.truncate_text(short_text, 20)
            self.assertEqual(result, short_text)
        except ImportError:
            self.skipTest("StringUtils not implemented yet")
    
    def test_extract_markdown_title(self):
        """Markdownタイトル抽出テスト"""
        try:
            from py.modules.shared_modules.file_utils import StringUtils
            
            # 標準的なH1ヘッダー
            content = "# Example Title\n\nSome content here."
            title = StringUtils.extract_markdown_title(content)
            self.assertEqual(title, "Example Title")
            
            # ヘッダーがない場合
            content_no_header = "Just some content without header."
            title = StringUtils.extract_markdown_title(content_no_header)
            self.assertIsNone(title)
        except ImportError:
            self.skipTest("StringUtils not implemented yet")
    
    def test_format_citation_key(self):
        """citation_keyフォーマットテスト"""
        try:
            from py.modules.shared_modules.file_utils import StringUtils
            
            # 標準的なケース
            citation_key = StringUtils.format_citation_key("Smith", "2024", "a")
            self.assertEqual(citation_key, "Smith2024a")
            
            # 特殊文字を含むケース
            citation_key = StringUtils.format_citation_key("Smith & Jones", "2024", "")
            self.assertEqual(citation_key, "SmithJones2024")
        except ImportError:
            self.skipTest("StringUtils not implemented yet")
    
    def test_extract_doi_from_text(self):
        """DOI抽出テスト"""
        try:
            from py.modules.shared_modules.file_utils import StringUtils
            
            # 標準的なDOI
            text = "This paper has DOI: 10.1000/123456 and more text."
            doi = StringUtils.extract_doi_from_text(text)
            self.assertEqual(doi, "10.1000/123456")
            
            # DOIがない場合
            text_no_doi = "This text has no DOI."
            doi = StringUtils.extract_doi_from_text(text_no_doi)
            self.assertIsNone(doi)
        except ImportError:
            self.skipTest("StringUtils not implemented yet")
    
    def test_validate_citation_key(self):
        """citation_key検証テスト"""
        try:
            from py.modules.shared_modules.file_utils import StringUtils
            
            # 有効なcitation_key
            valid_keys = ["Smith2024a", "JohnsonLee2024b", "author_2024"]
            for key in valid_keys:
                self.assertTrue(StringUtils.validate_citation_key(key), 
                              f"Failed for valid key: {key}")
            
            # 無効なcitation_key
            invalid_keys = ["", "123invalid", "verylongauthornamethatexceedslimit2024", "Smith"]
            for key in invalid_keys:
                self.assertFalse(StringUtils.validate_citation_key(key), 
                               f"Failed for invalid key: {key}")
        except ImportError:
            self.skipTest("StringUtils not implemented yet")
    
    def test_generate_unique_filename(self):
        """ユニークファイル名生成テスト"""
        try:
            from py.modules.shared_modules.file_utils import StringUtils
            
            # 重複なしの場合
            existing = ["file1.txt", "file2.txt"]
            unique = StringUtils.generate_unique_filename("file3", "txt", existing)
            self.assertEqual(unique, "file3.txt")
            
            # 重複ありの場合
            existing = ["file.txt", "file_1.txt"]
            unique = StringUtils.generate_unique_filename("file", "txt", existing)
            self.assertEqual(unique, "file_2.txt")
        except ImportError:
            self.skipTest("StringUtils not implemented yet")
    
    def test_escape_markdown(self):
        """Markdownエスケープテスト"""
        try:
            from py.modules.shared_modules.file_utils import StringUtils
            
            # 特殊文字を含むテキスト
            text = "Text with *bold* and [link](url) and `code`"
            escaped = StringUtils.escape_markdown(text)
            
            # 特殊文字がエスケープされているか確認
            self.assertIn("\\*", escaped)
            self.assertIn("\\[", escaped)
            self.assertIn("\\]", escaped)
            self.assertIn("\\`", escaped)
        except ImportError:
            self.skipTest("StringUtils not implemented yet")


if __name__ == '__main__':
    # テスト実行時に詳細出力
    unittest.main(verbosity=2) 