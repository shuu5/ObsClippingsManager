#!/usr/bin/env python3
"""
IntegratedLoggerクラスのユニットテスト

構造化ログ、レベル管理、ファイルローテーション、エラートラッキング機能のテスト
"""

import unittest
import tempfile
import os
import shutil
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import time


class TestIntegratedLoggerImport(unittest.TestCase):
    """IntegratedLoggerクラスのインポートテスト"""
    
    def test_integrated_logger_import(self):
        """IntegratedLoggerクラスのインポートテスト"""
        try:
            from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
            self.assertTrue(True, "IntegratedLogger successfully imported")
        except ImportError:
            self.fail("IntegratedLogger should be importable")


class TestIntegratedLoggerBasic(unittest.TestCase):
    """IntegratedLoggerクラスの基本機能テスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_integrated_logger_"))
        self.log_file = self.test_dir / "logs" / "test.log"
        
        # Mock設定
        self.mock_config_manager = MagicMock()
        self.mock_config_manager.get_config.return_value = {
            'logging': {
                'log_level': 'INFO',
                'max_file_size': '10MB',
                'backup_count': 5,
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            }
        }
    
    def tearDown(self):
        """テスト後クリーンアップ"""
        # ロガーのクリーンアップ
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)
        
        # ファイルクリーンアップ
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_integrated_logger_initialization(self):
        """IntegratedLoggerクラスの初期化テスト"""
        from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
        
        logger = IntegratedLogger(self.mock_config_manager, str(self.log_file))
        
        self.assertIsInstance(logger, IntegratedLogger)
        self.assertTrue(self.log_file.parent.exists())
    
    def test_get_logger_module_specific(self):
        """モジュール別ロガー取得テスト"""
        from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
        
        logger = IntegratedLogger(self.mock_config_manager, str(self.log_file))
        
        # 異なるモジュールのロガー取得
        workflow_logger = logger.get_logger('WorkflowManager')
        config_logger = logger.get_logger('ConfigManager')
        
        self.assertIsNotNone(workflow_logger)
        self.assertIsNotNone(config_logger)
        self.assertNotEqual(workflow_logger, config_logger)
        
        # 同じモジュール名では同じロガーを返す
        workflow_logger2 = logger.get_logger('WorkflowManager')
        self.assertEqual(workflow_logger, workflow_logger2)
    
    def test_log_levels(self):
        """ログレベル機能テスト"""
        from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
        
        logger = IntegratedLogger(self.mock_config_manager, str(self.log_file))
        module_logger = logger.get_logger('TestModule')
        
        # 各レベルでのログ出力
        module_logger.debug("Debug message")
        module_logger.info("Info message")
        module_logger.warning("Warning message")
        module_logger.error("Error message")
        
        # ログファイル存在確認
        self.assertTrue(self.log_file.exists())
        
        # ログ内容確認
        with open(self.log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            self.assertIn("Info message", log_content)
            self.assertIn("Warning message", log_content)
            self.assertIn("Error message", log_content)
    
    def test_structured_logging(self):
        """構造化ログ出力テスト"""
        from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
        
        logger = IntegratedLogger(self.mock_config_manager, str(self.log_file))
        module_logger = logger.get_logger('TestModule')
        
        # 構造化データ付きログ
        extra_data = {
            'citation_key': 'smith2023test',
            'operation': 'processing',
            'duration': 12.5
        }
        
        logger.log_structured('info', 'Paper processing completed', module_logger.name, extra_data)
        
        # ログファイル確認
        with open(self.log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            self.assertIn("Paper processing completed", log_content)
            self.assertIn("smith2023test", log_content)
    
    def test_log_format_consistency(self):
        """ログフォーマット一貫性テスト"""
        from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
        
        logger = IntegratedLogger(self.mock_config_manager, str(self.log_file))
        module_logger = logger.get_logger('TestModule')
        
        module_logger.info("Test log message")
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            log_line = f.readline().strip()
            
            # フォーマット確認（timestamp [level] module: message）
            import re
            pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \[INFO\] TestModule: Test log message'
            self.assertRegex(log_line, pattern)


class TestIntegratedLoggerAdvanced(unittest.TestCase):
    """IntegratedLoggerクラスの高度な機能テスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_integrated_logger_advanced_"))
        self.log_file = self.test_dir / "logs" / "test.log"
        
        self.mock_config_manager = MagicMock()
        self.mock_config_manager.get_config.return_value = {
            'logging': {
                'log_level': 'DEBUG',
                'max_file_size': '1MB',
                'backup_count': 3,
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                'enable_rotation': True
            }
        }
    
    def tearDown(self):
        """テスト後クリーンアップ"""
        # ロガーのクリーンアップ
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)
        
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_file_rotation_functionality(self):
        """ファイルローテーション機能テスト"""
        from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
        
        # 小さなファイルサイズでローテーションテスト
        small_config = self.mock_config_manager.get_config.return_value.copy()
        small_config['logging']['max_file_size'] = '1KB'
        self.mock_config_manager.get_config.return_value = small_config
        
        logger = IntegratedLogger(self.mock_config_manager, str(self.log_file))
        module_logger = logger.get_logger('TestModule')
        
        # 大量のログ出力でローテーション発生
        for i in range(100):
            module_logger.info(f"Large log message number {i} " + "x" * 100)
        
        # バックアップファイルの存在確認
        log_dir = self.log_file.parent
        backup_files = list(log_dir.glob("test.log.*"))
        self.assertTrue(len(backup_files) > 0, "Backup log files should be created")
    
    def test_error_tracking_functionality(self):
        """エラートラッキング機能テスト"""
        from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
        
        logger = IntegratedLogger(self.mock_config_manager, str(self.log_file))
        
        # 例外付きエラーログ
        try:
            1 / 0
        except ZeroDivisionError as e:
            logger.log_error_with_traceback('Division error occurred', 'TestModule', e)
        
        # ログファイル確認（実際のログファイルパスから取得）
        actual_log_file = logger.get_log_file_path()
        with open(actual_log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            self.assertIn("Division error occurred", log_content)
            self.assertIn("ZeroDivisionError", log_content)
            self.assertIn("Traceback", log_content)
    
    def test_performance_logging(self):
        """パフォーマンスログ機能テスト"""
        from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
        
        logger = IntegratedLogger(self.mock_config_manager, str(self.log_file))
        
        # パフォーマンス測定
        with logger.performance_context('TestOperation', 'TestModule') as perf:
            time.sleep(0.1)  # 短時間の処理をシミュレート
            perf.add_metric('processed_items', 5)
            perf.add_metric('api_calls', 2)
        
        # ログファイル確認（実際のログファイルパスから取得）
        actual_log_file = logger.get_log_file_path()
        with open(actual_log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            self.assertIn("TestOperation", log_content)
            self.assertIn("duration", log_content)
            self.assertIn("processed_items", log_content)
    
    def test_log_level_dynamic_change(self):
        """ログレベル動的変更テスト"""
        from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
        
        logger = IntegratedLogger(self.mock_config_manager, str(self.log_file))
        module_logger = logger.get_logger('TestModule')
        
        # 初期レベルでDEBUGログ出力
        module_logger.debug("Debug message 1")
        
        # レベルをWARNINGに変更
        logger.set_level('WARNING')
        module_logger.debug("Debug message 2")  # 出力されないはず
        module_logger.warning("Warning message")  # 出力されるはず
        
        # ログファイル確認（実際のログファイルパスから取得）
        actual_log_file = logger.get_log_file_path()
        with open(actual_log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            self.assertIn("Debug message 1", log_content)
            self.assertNotIn("Debug message 2", log_content)
            self.assertIn("Warning message", log_content)
    
    def test_concurrent_logging(self):
        """並行ログ出力テスト"""
        from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
        import threading
        
        logger = IntegratedLogger(self.mock_config_manager, str(self.log_file))
        
        def log_worker(worker_id):
            module_logger = logger.get_logger(f'Worker{worker_id}')
            for i in range(10):
                module_logger.info(f"Worker {worker_id} - Message {i}")
        
        # 複数スレッドでの並行ログ出力
        threads = []
        for i in range(3):
            thread = threading.Thread(target=log_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # ログファイル確認
        with open(self.log_file, 'r', encoding='utf-8') as f:
            log_lines = f.readlines()
            self.assertEqual(len(log_lines), 30)  # 3 workers × 10 messages


class TestIntegratedLoggerIntegration(unittest.TestCase):
    """IntegratedLoggerクラスの統合テスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_integrated_logger_integration_"))
        self.log_file = self.test_dir / "logs" / "integration.log"
        
        # 実際のConfigManagerを模倣した設定
        self.mock_config_manager = MagicMock()
        self.mock_config_manager.get_config.return_value = {
            'logging': {
                'log_level': 'INFO',
                'max_file_size': '10MB',
                'backup_count': 5,
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                'enable_rotation': True,
                'enable_structured_logging': True
            }
        }
    
    def tearDown(self):
        """テスト後クリーンアップ"""
        # ロガーのクリーンアップ
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)
        
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_full_workflow_logging(self):
        """完全なワークフローログテスト"""
        from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
        
        logger = IntegratedLogger(self.mock_config_manager, str(self.log_file))
        
        # 様々なモジュールからのログ出力をシミュレート
        workflow_logger = logger.get_logger('IntegratedWorkflow')
        config_logger = logger.get_logger('ConfigManager')
        parser_logger = logger.get_logger('BibTeXParser')
        
        # ワークフロー開始
        workflow_logger.info("Starting integrated workflow")
        
        # 設定読み込み
        config_logger.info("Loading configuration from config.yaml")
        
        # BibTeX解析
        parser_logger.info("Parsing BibTeX file")
        parser_logger.warning("Citation key 'smith2023' has missing DOI")
        
        # エラー発生のシミュレート
        try:
            raise ValueError("Test error for logging")
        except ValueError as e:
            logger.log_error_with_traceback("Processing error occurred", 'TestModule', e)
        
        # パフォーマンス測定
        with logger.performance_context('PaperProcessing', 'WorkflowManager') as perf:
            time.sleep(0.05)
            perf.add_metric('papers_processed', 3)
            perf.add_metric('total_citations', 15)
        
        # ワークフロー完了
        workflow_logger.info("Integrated workflow completed successfully")
        
        # ログファイル内容の包括的確認
        with open(self.log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            
            # 各モジュールのログが含まれることを確認
            self.assertIn("IntegratedWorkflow", log_content)
            self.assertIn("ConfigManager", log_content)
            self.assertIn("BibTeXParser", log_content)
            
            # 異なるレベルのログが含まれることを確認
            self.assertIn("[INFO]", log_content)
            self.assertIn("[WARNING]", log_content)
            self.assertIn("[ERROR]", log_content)
            
            # エラートラッキングが含まれることを確認
            self.assertIn("ValueError", log_content)
            self.assertIn("Traceback", log_content)
            
            # パフォーマンスメトリクスが含まれることを確認
            self.assertIn("PaperProcessing", log_content)
            self.assertIn("papers_processed", log_content)
    
    def test_config_manager_integration(self):
        """ConfigManagerとの統合テスト"""
        from code.py.modules.shared_modules.integrated_logger import IntegratedLogger
        
        # ConfigManagerからの設定でロガー初期化
        logger = IntegratedLogger(self.mock_config_manager)
        
        # ConfigManagerの設定が適用されていることを確認
        test_logger = logger.get_logger('TestModule')
        self.assertIsNotNone(test_logger)
        
        # ログレベルが設定から適用されていることを確認
        test_logger.info("Test message")
        
        with open(logger.log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            self.assertIn("Test message", log_content)


if __name__ == '__main__':
    unittest.main() 