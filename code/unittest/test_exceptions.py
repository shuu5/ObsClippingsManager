#!/usr/bin/env python3
"""
例外処理システム（Exception Handling System）テストスイート

テスト対象:
- ObsClippingsManagerError基底例外
- 専用例外クラス群
- エラーハンドリングユーティリティ
- リトライ機構
"""

import unittest
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# テスト環境のセットアップ
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from code.py.modules.shared_modules.exceptions import (
    ObsClippingsManagerError,
    ConfigurationError,
    ValidationError,
    ProcessingError,
    APIError,
    FileSystemError,
    YAMLError,
    BibTeXError,
    standard_error_handler,
    create_error_context,
    format_error_for_logging
)


class TestObsClippingsManagerError(unittest.TestCase):
    """ObsClippingsManagerError基底例外クラステスト"""
    
    def test_basic_error_creation(self):
        """基本的なエラー作成テスト"""
        error = ObsClippingsManagerError("Test error message")
        self.assertEqual(error.message, "Test error message")
        self.assertEqual(error.error_code, "UNKNOWN_ERROR")
        self.assertEqual(error.context, {})
        self.assertIsNone(error.__cause__)
    
    def test_error_with_code_and_context(self):
        """エラーコードとコンテキスト付きエラー作成テスト"""
        context = {"operation": "test_operation", "file": "test.yaml"}
        error = ObsClippingsManagerError(
            "Test error with context",
            error_code="TEST_ERROR",
            context=context
        )
        self.assertEqual(error.error_code, "TEST_ERROR")
        self.assertEqual(error.context, context)
    
    def test_error_with_cause(self):
        """根本原因付きエラー作成テスト"""
        original_error = ValueError("Original error")
        error = ObsClippingsManagerError(
            "Wrapped error",
            cause=original_error
        )
        self.assertEqual(error.__cause__, original_error)
    
    def test_error_string_representation(self):
        """エラー文字列表現テスト"""
        error = ObsClippingsManagerError(
            "Test message",
            error_code="TEST_CODE"
        )
        self.assertEqual(str(error), "[TEST_CODE] Test message")


class TestSpecificExceptions(unittest.TestCase):
    """専用例外クラス群テスト"""
    
    def test_configuration_error(self):
        """ConfigurationErrorテスト"""
        error = ConfigurationError("Config error")
        self.assertIsInstance(error, ObsClippingsManagerError)
        self.assertEqual(error.message, "Config error")
    
    def test_validation_error(self):
        """ValidationErrorテスト"""
        error = ValidationError("Validation failed")
        self.assertIsInstance(error, ObsClippingsManagerError)
        self.assertEqual(error.message, "Validation failed")
    
    def test_processing_error(self):
        """ProcessingErrorテスト"""
        error = ProcessingError("Processing failed")
        self.assertIsInstance(error, ObsClippingsManagerError)
        self.assertEqual(error.message, "Processing failed")
    
    def test_api_error(self):
        """APIErrorテスト"""
        error = APIError("API call failed")
        self.assertIsInstance(error, ObsClippingsManagerError)
        self.assertEqual(error.message, "API call failed")
    
    def test_filesystem_error(self):
        """FileSystemErrorテスト"""
        error = FileSystemError("File operation failed")
        self.assertIsInstance(error, ObsClippingsManagerError)
        self.assertEqual(error.message, "File operation failed")
    
    def test_yaml_error(self):
        """YAMLErrorテスト"""
        error = YAMLError("YAML parsing failed")
        self.assertIsInstance(error, ObsClippingsManagerError)
        self.assertEqual(error.message, "YAML parsing failed")
    
    def test_bibtex_error(self):
        """BibTeXErrorテスト"""
        error = BibTeXError("BibTeX parsing failed")
        self.assertIsInstance(error, ObsClippingsManagerError)
        self.assertEqual(error.message, "BibTeX parsing failed")


class TestErrorHandlingUtilities(unittest.TestCase):
    """エラーハンドリングユーティリティテスト"""
    
    def test_standard_error_handler_known_error(self):
        """標準エラーハンドラー（既知エラー）テスト"""
        @standard_error_handler
        def test_function():
            raise ConfigurationError("Known error")
        
        with self.assertRaises(ConfigurationError):
            test_function()
    
    def test_standard_error_handler_unknown_error(self):
        """標準エラーハンドラー（未知エラー）テスト"""
        @standard_error_handler
        def test_function():
            raise ValueError("Unknown error")
        
        with self.assertRaises(ProcessingError) as context:
            test_function()
        
        error = context.exception
        self.assertIn("test_function", error.message)
        self.assertEqual(error.error_code, "UNEXPECTED_ERROR")
        self.assertIsInstance(error.__cause__, ValueError)
    
    def test_create_error_context(self):
        """エラーコンテキスト作成テスト"""
        context = create_error_context(
            "test_operation",
            file_path="/path/to/file.yaml",
            additional_info="test_info"
        )
        
        expected = {
            "operation": "test_operation",
            "timestamp": None,
            "file_path": "/path/to/file.yaml",
            "additional_info": "test_info"
        }
        self.assertEqual(context, expected)
    
    def test_format_error_for_logging(self):
        """ログ用エラーフォーマットテスト"""
        original_error = ValueError("Original error")
        error = ProcessingError(
            "Processing failed",
            error_code="PROC_ERROR",
            context={"operation": "test"},
            cause=original_error
        )
        
        formatted = format_error_for_logging(error)
        expected = {
            "error_type": "ProcessingError",
            "message": "Processing failed",
            "error_code": "PROC_ERROR",
            "context": {"operation": "test"},
            "root_cause": "Original error"
        }
        self.assertEqual(formatted, expected)


class TestRetryMechanism(unittest.TestCase):
    """リトライ機構テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.call_count = 0
        self.successful_call_count = 3  # 3回目で成功する設定
    
    def _failing_function(self):
        """失敗する関数（テスト用）"""
        self.call_count += 1
        if self.call_count < self.successful_call_count:
            raise APIError("API call failed")
        return "success"
    
    def _always_failing_function(self):
        """常に失敗する関数（テスト用）"""
        self.call_count += 1
        raise APIError("API call always fails")
    
    @patch('time.sleep')  # sleepをモック化してテストを高速化
    def test_retry_decorator_success(self, mock_sleep):
        """リトライデコレーター成功テスト"""
        from code.py.modules.shared_modules.exceptions import retry_on_error
        
        @retry_on_error(max_attempts=5, delay=0.1)
        def test_function():
            return self._failing_function()
        
        result = test_function()
        self.assertEqual(result, "success")
        self.assertEqual(self.call_count, self.successful_call_count)
        # 2回失敗後成功なので、2回のsleepが呼ばれる
        self.assertEqual(mock_sleep.call_count, 2)
    
    @patch('time.sleep')
    def test_retry_decorator_max_attempts_exceeded(self, mock_sleep):
        """リトライデコレーター最大試行回数超過テスト"""
        from code.py.modules.shared_modules.exceptions import retry_on_error
        
        @retry_on_error(max_attempts=2, delay=0.1)
        def test_function():
            return self._always_failing_function()
        
        with self.assertRaises(APIError):
            test_function()
        
        self.assertEqual(self.call_count, 2)  # 最大2回試行
        self.assertEqual(mock_sleep.call_count, 1)  # 1回目失敗後のsleep
    
    @patch('time.sleep')
    def test_retry_with_exponential_backoff(self, mock_sleep):
        """指数バックオフリトライテスト"""
        from code.py.modules.shared_modules.exceptions import retry_on_error
        
        @retry_on_error(max_attempts=4, delay=0.1, backoff_factor=2.0, jitter=False)
        def test_function():
            return self._always_failing_function()
        
        with self.assertRaises(APIError):
            test_function()
        
        # 指数バックオフ: 0.1, 0.2, 0.4秒
        expected_delays = [0.1, 0.2, 0.4]
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertEqual(actual_delays, expected_delays)
    
    def test_retry_with_specific_exceptions(self):
        """特定例外タイプでのリトライテスト"""
        from code.py.modules.shared_modules.exceptions import retry_on_error
        
        @retry_on_error(max_attempts=3, delay=0.1, 
                       retry_exceptions=(APIError, ProcessingError))
        def test_function_api_error():
            raise APIError("API error")
        
        @retry_on_error(max_attempts=3, delay=0.1,
                       retry_exceptions=(APIError, ProcessingError))
        def test_function_config_error():
            raise ConfigurationError("Config error")
        
        # APIErrorはリトライされる
        with self.assertRaises(APIError):
            test_function_api_error()
        
        # ConfigurationErrorはリトライされずに即座に例外発生
        with self.assertRaises(ConfigurationError):
            test_function_config_error()
    
    def test_retry_configuration_integration(self):
        """リトライ設定統合テスト"""
        from code.py.modules.shared_modules.exceptions import retry_on_error
        
        # 設定から取得されるリトライパラメータをテスト
        @retry_on_error()  # デフォルト設定使用
        def test_function():
            return self._failing_function()
        
        result = test_function()
        self.assertEqual(result, "success")


if __name__ == '__main__':
    # テスト実行時に詳細出力
    unittest.main(verbosity=2) 