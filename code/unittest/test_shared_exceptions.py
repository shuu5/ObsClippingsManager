"""
共有例外モジュールのテスト

ObsClippingsManager カスタム例外クラスのテストスイート
"""

import unittest
import sys
import os

# テスト対象モジュールのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'py'))

from modules.shared.exceptions import (
    ObsClippingsError,
    ConfigError,
    BibTeXParseError,
    FileOperationError,
    ValidationError,
    WorkflowError,
    SyncCheckError,
    CitationParserError,
    InvalidCitationPatternError,
    PatternDetectionError,
    FormatConversionError,
    LinkExtractionError
)


class TestBaseException(unittest.TestCase):
    """基底例外クラスのテスト"""
    
    def test_base_exception_instantiation(self):
        """基底例外の基本インスタンス化テスト"""
        message = "Test error message"
        error = ObsClippingsError(message)
        
        self.assertEqual(str(error), message)
        self.assertIsInstance(error, Exception)
    
    def test_base_exception_inheritance(self):
        """基底例外の継承関係テスト"""
        error = ObsClippingsError("Test")
        
        self.assertIsInstance(error, Exception)
        self.assertIsInstance(error, ObsClippingsError)


class TestConfigError(unittest.TestCase):
    """設定エラーのテスト"""
    
    def test_config_error_basic(self):
        """基本的な設定エラーテスト"""
        message = "Invalid configuration"
        error = ConfigError(message)
        
        self.assertEqual(str(error), message)
        self.assertIsInstance(error, ObsClippingsError)
    
    def test_config_error_with_config_key(self):
        """設定キー付きエラーテスト"""
        message = "Missing required configuration"
        config_key = "api_key"
        
        error = ConfigError(message, config_key=config_key)
        
        self.assertEqual(str(error), message)
        self.assertEqual(error.config_key, config_key)


class TestBibTeXParseError(unittest.TestCase):
    """BibTeX解析エラーのテスト"""
    
    def test_bibtex_parse_error_basic(self):
        """基本的なBibTeX解析エラーテスト"""
        message = "Invalid BibTeX entry"
        error = BibTeXParseError(message)
        
        self.assertEqual(str(error), message)
        self.assertIsInstance(error, ObsClippingsError)
    
    def test_bibtex_parse_error_with_details(self):
        """詳細情報付きBibTeX解析エラーテスト"""
        message = "Parse error"
        line_number = 25
        entry_key = "invalid_entry"
        
        error = BibTeXParseError(
            message,
            line_number=line_number,
            entry_key=entry_key
        )
        
        self.assertEqual(str(error), message)
        self.assertEqual(error.line_number, line_number)
        self.assertEqual(error.entry_key, entry_key)


class TestFileOperationError(unittest.TestCase):
    """ファイル操作エラーのテスト"""
    
    def test_file_operation_error_basic(self):
        """基本的なファイル操作エラーテスト"""
        message = "File operation failed"
        error = FileOperationError(message)
        
        self.assertEqual(str(error), message)
        self.assertIsInstance(error, ObsClippingsError)
    
    def test_file_operation_error_with_details(self):
        """詳細情報付きファイル操作エラーテスト"""
        message = "Cannot move file"
        file_path = "source.md"
        operation = "move"
        
        error = FileOperationError(
            message,
            file_path=file_path,
            operation=operation
        )
        
        self.assertEqual(str(error), message)
        self.assertEqual(error.file_path, file_path)
        self.assertEqual(error.operation, operation)


class TestValidationError(unittest.TestCase):
    """バリデーションエラーのテスト"""
    
    def test_validation_error_basic(self):
        """基本的なバリデーションエラーテスト"""
        message = "Validation failed"
        error = ValidationError(message)
        
        self.assertEqual(str(error), message)
        self.assertIsInstance(error, ObsClippingsError)
    
    def test_validation_error_with_details(self):
        """詳細情報付きバリデーションエラーテスト"""
        message = "DOI validation failed"
        field = "doi"
        value = "invalid"
        
        error = ValidationError(message, field=field, value=value)
        
        self.assertEqual(str(error), message)
        self.assertEqual(error.field, field)
        self.assertEqual(error.value, value)


class TestWorkflowErrors(unittest.TestCase):
    """ワークフローエラーのテスト"""
    
    def test_workflow_error_basic(self):
        """基本的なワークフローエラーテスト"""
        message = "Workflow execution failed"
        error = WorkflowError(message)
        
        self.assertEqual(str(error), message)
        self.assertIsInstance(error, ObsClippingsError)
    
    def test_sync_check_error(self):
        """同期チェックエラーのテスト"""
        message = "Sync check failed"
        error = SyncCheckError(message)
        
        self.assertEqual(str(error), message)
        self.assertIsInstance(error, WorkflowError)
        self.assertIsInstance(error, ObsClippingsError)





class TestExceptionInteraction(unittest.TestCase):
    """例外の相互作用テスト"""
    
    def test_exception_chaining(self):
        """例外チェーンのテスト"""
        original_error = ValueError("Original error")
        
        try:
            raise original_error
        except ValueError as e:
            # Python 3.x互換性のため、from e構文の代わりにsetattr使用
            chained_error = WorkflowError("Workflow failed due to validation")
            chained_error.__cause__ = e
        
        self.assertIsInstance(chained_error, WorkflowError)
        self.assertIs(chained_error.__cause__, original_error)
    
    def test_multiple_exception_types(self):
        """複数の例外タイプの確認テスト"""
        exceptions = [
            ObsClippingsError("Base error"),
            ConfigError("Config error"),
            BibTeXParseError("BibTeX error"),
            FileOperationError("File error"),
            ValidationError("Validation error"),
            WorkflowError("Workflow error"),
            SyncCheckError("Sync check error")
        ]
        
        # すべてが基底例外から継承されていることを確認
        for exc in exceptions:
            self.assertIsInstance(exc, ObsClippingsError)
            self.assertIsInstance(exc, Exception)
    
    def test_exception_str_representation(self):
        """例外の文字列表現テスト"""
        error = ValidationError("Test validation error")
        
        self.assertEqual(str(error), "Test validation error")
        self.assertIn("ValidationError", repr(error))
    
    def test_exception_with_none_values(self):
        """None値を含む例外のテスト"""
        error = FileOperationError("Error", file_path=None, operation=None)
        
        self.assertEqual(str(error), "Error")
        self.assertIsNone(error.file_path)
        self.assertIsNone(error.operation)


if __name__ == '__main__':
    unittest.main() 