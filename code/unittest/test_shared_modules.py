#!/usr/bin/env python3
"""
Unit tests for shared modules (config, logger, parser, utils)
"""

import unittest
import tempfile
import os
from pathlib import Path

class TestConfigManager(unittest.TestCase):
    """ConfigManagerクラスのテスト"""
    
    def setUp(self):
        """テスト前準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.yaml"
    
    def tearDown(self):
        """テスト後クリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_manager_import(self):
        """ConfigManagerクラスのインポートテスト"""
        try:
            # ConfigManagerが正常にインポートできることを確認
            from code.py.modules.shared.config_manager import ConfigManager
            self.assertTrue(True, "ConfigManager successfully imported")
        except ImportError:
            self.fail("ConfigManager should be importable")

class TestIntegratedLogger(unittest.TestCase):
    """IntegratedLoggerクラスのテスト"""
    
    def test_integrated_logger_import(self):
        """IntegratedLoggerクラスのインポートテスト"""
        try:
            from code.py.modules.shared.integrated_logger import IntegratedLogger
            self.assertTrue(True, "IntegratedLogger successfully imported")
        except ImportError:
            self.fail("IntegratedLogger should be importable")

class TestBibTeXParser(unittest.TestCase):
    """BibTeXParserクラスのテスト"""
    
    def test_bibtex_parser_import(self):
        """BibTeXParserクラスのインポートテスト"""
        try:
            # BibTeXParserが正常にインポートできることを確認
            from code.py.modules.shared.bibtex_parser import BibTeXParser
            self.assertTrue(True, "BibTeXParser successfully imported")
        except ImportError:
            self.fail("BibTeXParser should be importable")

class TestClaudeAPIClient(unittest.TestCase):
    """ClaudeAPIClientクラスのテスト"""
    
    def test_claude_api_client_import(self):
        """ClaudeAPIClientクラスのインポートテスト"""
        with self.assertRaises(ImportError):
            # まだ実装されていないため、ImportError が発生することを確認
            from code.py.modules.shared.claude_api_client import ClaudeAPIClient

if __name__ == '__main__':
    unittest.main() 