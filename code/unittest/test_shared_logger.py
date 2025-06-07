"""
共有ロガーモジュールのテスト

ObsClippingsManager ログ管理システムのテストスイート
"""

import unittest
import sys
import os
import tempfile
import logging
import shutil
from pathlib import Path

# テスト対象モジュールのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'py'))

from modules.shared.logger import (
    IntegratedLogger,
    get_integrated_logger
)


class TestIntegratedLogger(unittest.TestCase):
    """IntegratedLoggerクラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")
        
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # ログハンドラーをクリア
        logger = logging.getLogger("ObsClippingsManager")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
        
        # 一時ディレクトリクリーンアップ
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_logger_initialization(self):
        """ロガー初期化のテスト"""
        logger = IntegratedLogger(
            log_file=self.log_file,
            log_level="INFO",
            console_output=True
        )
        
        # ロガーインスタンスが正しく作成されることを確認
        self.assertIsNotNone(logger.root_logger)
        self.assertEqual(logger.root_logger.name, "ObsClippingsManager")
        self.assertEqual(logger.log_level, logging.INFO)
    
    def test_console_logging_setup(self):
        """コンソールログ設定のテスト"""
        logger = IntegratedLogger(
            log_level="INFO",
            console_output=True
        )
        
        # コンソールハンドラーが追加されていることを確認
        console_handlers = [h for h in logger.root_logger.handlers 
                          if isinstance(h, logging.StreamHandler)]
        self.assertGreater(len(console_handlers), 0)
    
    def test_file_logging_setup(self):
        """ファイルログ設定のテスト"""
        logger = IntegratedLogger(
            log_file=self.log_file,
            log_level="DEBUG",
            console_output=False
        )
        
        # ファイルハンドラーが追加されていることを確認
        file_handlers = [h for h in logger.root_logger.handlers 
                        if isinstance(h, (logging.FileHandler, logging.handlers.RotatingFileHandler))]
        self.assertGreater(len(file_handlers), 0)
        
        # ログファイルが作成されることを確認
        self.assertTrue(Path(self.log_file).exists())
    
    def test_log_message_writing(self):
        """ログメッセージ書き込みのテスト"""
        logger = IntegratedLogger(
            log_file=self.log_file,
            log_level="DEBUG",
            console_output=False
        )
        
        # テストロガーでログ出力
        test_logger = logger.get_logger("TestModule")
        test_logger.info("Test info message")
        test_logger.warning("Test warning message")
        test_logger.error("Test error message")
        
        # ファイル出力確認
        self.assertTrue(Path(self.log_file).exists())
        
        with open(self.log_file, 'r') as f:
            log_content = f.read()
        
        # メッセージがファイルに記録されていることを確認
        self.assertIn("Test info message", log_content)
        self.assertIn("Test warning message", log_content)
        self.assertIn("Test error message", log_content)
    
    def test_get_logger_method(self):
        """get_loggerメソッドのテスト"""
        integrated_logger = IntegratedLogger(
            log_file=self.log_file,
            log_level="INFO"
        )
        
        # 同じロガーインスタンスが返されることを確認
        logger1 = integrated_logger.get_logger("TestModule")
        logger2 = integrated_logger.get_logger("TestModule")
        
        self.assertIs(logger1, logger2)
        self.assertEqual(logger1.name, "ObsClippingsManager.TestModule")
    
    def test_different_module_loggers(self):
        """異なるモジュール用ロガーのテスト"""
        integrated_logger = IntegratedLogger(
            log_file=self.log_file,
            log_level="INFO"
        )
        
        # 異なるモジュール名で取得
        module1_logger = integrated_logger.get_logger("Module1")
        module2_logger = integrated_logger.get_logger("Module2")
        
        self.assertNotEqual(module1_logger, module2_logger)
        self.assertEqual(module1_logger.name, "ObsClippingsManager.Module1")
        self.assertEqual(module2_logger.name, "ObsClippingsManager.Module2")
    
    def test_operation_logging(self):
        """操作ログのテスト"""
        logger = IntegratedLogger(
            log_file=self.log_file,
            log_level="INFO",
            console_output=False
        )
        
        # 操作開始・終了のログ
        logger.log_operation_start("test_operation", {"param": "value"})
        logger.log_operation_end("test_operation", True, {"result": "success"})
        
        # ログファイル確認
        with open(self.log_file, 'r') as f:
            log_content = f.read()
        
        self.assertIn("Operation started: test_operation", log_content)
        self.assertIn("Operation test_operation completed successfully", log_content)
    
    def test_error_logging_with_context(self):
        """コンテキスト付きエラーログのテスト"""
        logger = IntegratedLogger(
            log_file=self.log_file,
            log_level="DEBUG",
            console_output=False
        )
        
        # エラーログ出力
        test_error = ValueError("Test error")
        logger.log_error_with_context("TestModule", test_error, {"file": "test.txt"})
        
        # ログファイル確認
        with open(self.log_file, 'r') as f:
            log_content = f.read()
        
        self.assertIn("ValueError: Test error", log_content)
        self.assertIn("Context: file=test.txt", log_content)
    
    def test_statistics_logging(self):
        """統計ログのテスト"""
        logger = IntegratedLogger(
            log_file=self.log_file,
            log_level="INFO",
            console_output=False
        )
        
        # 統計ログ出力
        stats = {"processed": 10, "successful": 8, "failed": 2}
        logger.log_statistics("TestModule", stats)
        
        # ログファイル確認
        with open(self.log_file, 'r') as f:
            log_content = f.read()
        
        self.assertIn("Statistics:", log_content)
        self.assertIn("processed: 10", log_content)
        self.assertIn("successful: 8", log_content)
    
    def test_log_level_change(self):
        """ログレベル動的変更のテスト"""
        logger = IntegratedLogger(
            log_file=self.log_file,
            log_level="INFO",
            console_output=False
        )
        
        # 初期レベル確認
        self.assertEqual(logger.log_level, logging.INFO)
        
        # レベル変更
        logger.set_log_level("DEBUG")
        self.assertEqual(logger.log_level, logging.DEBUG)
        
        # ルートロガーレベル確認
        self.assertEqual(logger.root_logger.level, logging.DEBUG)


class TestModuleFunctions(unittest.TestCase):
    """モジュールレベル関数のテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        
        # グローバルインスタンスのリセット
        import modules.shared.logger as logger_module
        logger_module._logger_instance = None
        
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # ログハンドラーをクリア
        logger = logging.getLogger("ObsClippingsManager")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
        
        # グローバルインスタンスのリセット
        import modules.shared.logger as logger_module
        logger_module._logger_instance = None
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_integrated_logger_function(self):
        """get_integrated_logger関数のテスト"""
        log_file = os.path.join(self.temp_dir, "function_test.log")
        
        # 関数によるロガー取得
        logger = get_integrated_logger(
            log_level="INFO",
            log_file=log_file,
            console_output=True
        )
        
        # 正しいロガーが返されることを確認
        self.assertIsInstance(logger, IntegratedLogger)
        self.assertEqual(logger.log_level, logging.INFO)
        
        # シングルトンの確認
        logger2 = get_integrated_logger()
        self.assertIs(logger, logger2)
    
    def test_singleton_behavior(self):
        """シングルトン動作のテスト"""
        logger1 = get_integrated_logger(log_level="INFO")
        logger2 = get_integrated_logger(log_level="DEBUG")  # 2回目の呼び出し
        
        # 同じインスタンスが返されることを確認
        self.assertIs(logger1, logger2)
        
        # 最初の設定が保持されることを確認
        self.assertEqual(logger1.log_level, logging.INFO)


class TestLoggerIntegration(unittest.TestCase):
    """ロガーの統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "integration_test.log")
        
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # ログハンドラーをクリア
        logger = logging.getLogger("ObsClippingsManager")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_multiple_modules_logging(self):
        """複数モジュールでのログ出力テスト"""
        logger = IntegratedLogger(
            log_file=self.log_file,
            log_level="INFO",
            console_output=False
        )
        
        # 複数のモジュールロガーを取得してログ出力
        modules = ["CitationFetcher", "BibtexParser", "WorkflowManager"]
        
        for module in modules:
            module_logger = logger.get_logger(module)
            module_logger.info(f"Info message from {module}")
            module_logger.warning(f"Warning message from {module}")
        
        # ログファイル内容確認
        with open(self.log_file, 'r') as f:
            log_content = f.read()
        
        # すべてのモジュールからのメッセージが記録されていることを確認
        for module in modules:
            self.assertIn(f"Info message from {module}", log_content)
            self.assertIn(f"Warning message from {module}", log_content)
    
    def test_log_format_consistency(self):
        """ログフォーマットの一貫性テスト"""
        logger = IntegratedLogger(
            log_file=self.log_file,
            log_level="INFO",
            console_output=False
        )
        
        test_logger = logger.get_logger("TestModule")
        test_logger.info("Test message for format check")
        
        # ログファイル内容確認
        with open(self.log_file, 'r') as f:
            log_lines = f.readlines()
        
        # ログフォーマットが期待通りであることを確認
        self.assertGreater(len(log_lines), 0)
        
        log_line = log_lines[0].strip()
        # 基本的なフォーマット要素の存在確認
        self.assertIn("TestModule", log_line)
        self.assertIn("Test message for format check", log_line)
        self.assertIn("INFO", log_line)


if __name__ == '__main__':
    unittest.main() 