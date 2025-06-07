"""
エッジケーステストスイート

ObsClippingsManager システム全体のエラーハンドリングと
エッジケースのテストを包括的に実施します。
"""

import unittest
import sys
import os
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch

# テスト対象モジュールのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'py'))

from modules.shared.config_manager import ConfigManager
from modules.shared.bibtex_parser import BibTeXParser
from modules.shared.utils import ProgressTracker
from modules.shared.exceptions import (
    ConfigError, BibTeXParseError, FileOperationError, 
    ValidationError, WorkflowError
)
from modules.workflows.sync_check_workflow import SyncCheckWorkflow


class TestEdgeCases(unittest.TestCase):
    """エッジケーステストの基底クラス"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
    
    def create_temp_file(self, filename, content="", encoding='utf-8'):
        """テンポラリファイルを作成"""
        file_path = os.path.join(self.temp_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        return file_path


class TestConfigManagerEdgeCases(TestEdgeCases):
    """ConfigManagerのエッジケーステスト"""
    
    def test_config_with_unicode_characters(self):
        """Unicode文字を含む設定ファイルのテスト"""
        config_content = {
            "common": {
                "bibtex_file": "/path/with/日本語/file.bib",
                "clippings_dir": "/path/with/émojis/📚/clippings",
                "log_level": "INFO"
            }
        }
        
        config_file = self.create_temp_file("unicode_config.json", json.dumps(config_content, ensure_ascii=False))
        
        config_manager = ConfigManager(config_file)
        loaded_config = config_manager.get_config()
        
        self.assertEqual(loaded_config["common"]["bibtex_file"], "/path/with/日本語/file.bib")
        self.assertEqual(loaded_config["common"]["clippings_dir"], "/path/with/émojis/📚/clippings")
    
    def test_config_with_malformed_json(self):
        """不正なJSON形式の設定ファイルのテスト"""
        malformed_configs = [
            '{"common": {"bibtex_file": "test.bib",}}',  # 末尾カンマ
            '{"common": {"bibtex_file": "test.bib"',     # 閉じ括弧なし
            '{common: {bibtex_file: "test.bib"}}',       # クォートなし
        ]
        
        for i, malformed_content in enumerate(malformed_configs):
            with self.subTest(config_index=i):
                config_file = self.create_temp_file(f"malformed_{i}.json", malformed_content)
                
                with self.assertRaises(ConfigError):
                    ConfigManager(config_file)
    
    def test_config_with_empty_values(self):
        """空の値を含む設定のテスト"""
        config_content = {
            "common": {
                "bibtex_file": "",
                "clippings_dir": None,
                "log_level": ""
            }
        }
        
        config_file = self.create_temp_file("empty_config.json", json.dumps(config_content))
        
        config_manager = ConfigManager(config_file)
        
        # バリデーションでエラーが検出されるべき
        is_valid, errors = config_manager.validate_config(config_content)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)


class TestBibTeXParserEdgeCases(TestEdgeCases):
    """BibTeXParserのエッジケーステスト"""
    
    def test_bibtex_with_nested_braces(self):
        """ネストした括弧を含むBibTeXのテスト"""
        bibtex_content = """
        @article{nested2023,
          title={{A Study of {Nested {Braces}} in {Academic {Writing}}}},
          author={Author, Test},
          journal={Journal of {{Complex}} Formatting},
          year={2023}
        }
        """
        
        bibtex_file = self.create_temp_file("nested.bib", bibtex_content)
        
        parser = BibTeXParser()
        entries = parser.parse_file(bibtex_file)
        
        self.assertEqual(len(entries), 1)
        self.assertIn("nested2023", entries)
        self.assertIn("Nested", entries["nested2023"]["title"])
    
    def test_bibtex_with_special_characters(self):
        """特殊文字を含むBibTeXのテスト"""
        bibtex_content = """
        @article{special2023,
          title={Étude des caractères spéciaux: α, β, γ & ∑},
          author={Müller, Hans and García, José},
          journal={Revue Européenne},
          year={2023},
          doi={10.1000/special-chars_test}
        }
        """
        
        bibtex_file = self.create_temp_file("special.bib", bibtex_content)
        
        parser = BibTeXParser()
        entries = parser.parse_file(bibtex_file)
        
        self.assertEqual(len(entries), 1)
        self.assertIn("special2023", entries)
        self.assertIn("Étude", entries["special2023"]["title"])
        self.assertIn("Müller", entries["special2023"]["author"])
    
    def test_bibtex_with_malformed_entries(self):
        """不正な形式のエントリを含むBibTeXのテスト"""
        bibtex_content = """
        @article{valid2023,
          title={Valid Entry},
          author={Author, Test},
          year={2023}
        }
        
        @article{broken2023
          title={Missing opening brace},
          author={Author, Test},
          year={2023}
        }
        
        @article{another_valid2023,
          title={Another Valid Entry},
          author={Author, Test},
          year={2023}
        }
        """
        
        bibtex_file = self.create_temp_file("malformed.bib", bibtex_content)
        
        parser = BibTeXParser()
        entries = parser.parse_file(bibtex_file)
        
        # 有効なエントリのみが解析される
        self.assertIn("valid2023", entries)
        self.assertIn("another_valid2023", entries)
        # 不正なエントリは含まれない
        self.assertNotIn("broken2023", entries)
    
    def test_bibtex_with_empty_file(self):
        """空のBibTeXファイルのテスト"""
        bibtex_file = self.create_temp_file("empty.bib", "")
        
        parser = BibTeXParser()
        entries = parser.parse_file(bibtex_file)
        
        self.assertEqual(len(entries), 0)


class TestProgressTrackerEdgeCases(TestEdgeCases):
    """ProgressTrackerのエッジケーステスト"""
    
    def test_progress_tracker_with_zero_total(self):
        """総数が0の場合のProgressTrackerテスト"""
        tracker = ProgressTracker(0, "Zero items")
        
        # 0個の場合でも正常に動作する
        tracker.finish()
        
        self.assertEqual(tracker.current, 0)
        self.assertEqual(tracker.total, 0)
    
    def test_progress_tracker_overflow(self):
        """進捗がtotalを超える場合のテスト"""
        tracker = ProgressTracker(5, "Overflow test")
        
        # totalを超えてincrementしても例外は発生しない
        for _ in range(10):
            tracker.increment()
        
        self.assertGreaterEqual(tracker.current, tracker.total)


class TestWorkflowEdgeCases(TestEdgeCases):
    """ワークフローのエッジケーステスト"""
    
    def test_workflow_with_corrupted_state(self):
        """破損した状態でのワークフロー実行テスト"""
        mock_config = Mock()
        mock_logger = Mock()
        
        # 不正な設定を返すモック
        mock_config.get_sync_check_config.return_value = {
            'bibtex_file': None,  # 不正な値
            'clippings_dir': 123,  # 不正な型
        }
        
        mock_logger.get_logger.return_value = Mock()
        
        workflow = SyncCheckWorkflow(mock_config, mock_logger)
        
        # 不正な設定でも例外処理により失敗が適切に処理される
        success, result = workflow.execute()
        
        self.assertFalse(success)
        self.assertIn('error', result)
    
    def test_workflow_with_interrupted_execution(self):
        """実行中断されたワークフローのテスト"""
        mock_config = Mock()
        mock_logger = Mock()
        
        mock_config.get_sync_check_config.return_value = {
            'bibtex_file': self.create_temp_file("test.bib", "@article{test,title={Test},year={2023}}"),
            'clippings_dir': self.temp_dir,
        }
        
        mock_logger.get_logger.return_value = Mock()
        
        workflow = SyncCheckWorkflow(mock_config, mock_logger)
        
        # _parse_bibtex_fileメソッドで例外を発生させる
        with patch.object(workflow, '_parse_bibtex_file', side_effect=KeyboardInterrupt("User interrupted")):
            success, result = workflow.execute()
        
        self.assertFalse(success)
        self.assertIn('error', result)


class TestExceptionHandlingEdgeCases(TestEdgeCases):
    """例外処理のエッジケーステスト"""
    
    def test_nested_exception_handling(self):
        """ネストした例外処理のテスト"""
        def inner_function():
            raise ValueError("Inner error")
        
        def middle_function():
            try:
                inner_function()
            except ValueError as e:
                # Python 3.x互換性のため、from e構文の代わりにsetattr使用
                error = BibTeXParseError("Middle error")
                error.__cause__ = e
                raise error
        
        def outer_function():
            try:
                middle_function()
            except BibTeXParseError as e:
                # Python 3.x互換性のため、from e構文の代わりにsetattr使用
                error = WorkflowError("Outer error")
                error.__cause__ = e
                raise error
        
        with self.assertRaises(WorkflowError) as context:
            outer_function()
        
        # 例外チェーンが正しく保持されている
        self.assertIsInstance(context.exception.__cause__, BibTeXParseError)
        self.assertIsInstance(context.exception.__cause__.__cause__, ValueError)
    
    def test_exception_with_unicode_messages(self):
        """Unicode文字を含む例外メッセージのテスト"""
        unicode_message = "エラーが発生しました: 文献「論文タイトル」の処理中"
        
        error = ConfigError(unicode_message)
        
        self.assertEqual(str(error), unicode_message)
        self.assertIn("論文タイトル", str(error))
    
    def test_exception_serialization(self):
        """例外のシリアライゼーションテスト"""
        error = FileOperationError(
            "File operation failed",
            file_path="/path/to/file.txt",
            operation="move"
        )
        
        # 例外の属性が正しく設定されている
        self.assertEqual(error.file_path, "/path/to/file.txt")
        self.assertEqual(error.operation, "move")
        
        # 文字列表現が正常
        error_str = str(error)
        self.assertEqual(error_str, "File operation failed")


if __name__ == '__main__':
    unittest.main() 