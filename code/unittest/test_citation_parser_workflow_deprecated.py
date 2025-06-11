"""
引用文献パーサーワークフローのテスト

ObsClippingsManager Citation Parser Workflow のテストスイート
"""

import unittest
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# テスト対象モジュールのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'py'))

from modules.workflows.citation_parser_workflow import CitationParserWorkflow
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.shared.exceptions import CitationParserError, InvalidCitationPatternError


class TestCitationParserWorkflow(unittest.TestCase):
    """引用文献パーサーワークフローのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        # モック設定管理
        self.mock_config = Mock(spec=ConfigManager)
        self.mock_config.get_citation_parser_config.return_value = {
            'default_pattern_type': 'all',
            'default_output_format': 'unified',
            'enable_link_extraction': False,
            'expand_ranges': True,
            'max_file_size_mb': 10,
            'output_encoding': 'utf-8',
            'processing_timeout': 60
        }
        
        # モックロガー
        self.mock_logger = Mock(spec=IntegratedLogger)
        self.mock_logger.get_logger.return_value = Mock()
        
        # ワークフロー初期化
        self.workflow = CitationParserWorkflow(self.mock_config, self.mock_logger)
    
    def test_workflow_initialization(self):
        """ワークフロー初期化のテスト"""
        self.assertIsNotNone(self.workflow.config_manager)
        self.assertIsNotNone(self.workflow.logger)
        self.assertIsNotNone(self.workflow.config)
    
    def test_validate_inputs_valid_file(self):
        """入力ファイル検証のテスト（正常）"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Paper\n\nThis study [1] shows...\n")
            f.flush()
            
            try:
                result = self.workflow.validate_inputs(f.name)
                self.assertTrue(result)
            finally:
                os.unlink(f.name)
    
    def test_validate_inputs_nonexistent_file(self):
        """入力ファイル検証のテスト（存在しないファイル）"""
        with self.assertRaises(CitationParserError):
            self.workflow.validate_inputs("/nonexistent/file.md")
    
    def test_validate_inputs_large_file(self):
        """入力ファイル検証のテスト（ファイルサイズ制限）"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            # 設定されたサイズ制限を超えるファイルサイズを模擬
            large_content = "x" * (11 * 1024 * 1024)  # 11MB
            f.write(large_content)
            f.flush()
            
            try:
                with self.assertRaises(CitationParserError):
                    self.workflow.validate_inputs(f.name)
            finally:
                os.unlink(f.name)
    
    def test_execute_successful(self):
        """ワークフロー実行のテスト（成功）"""
        # 実際のCitationParserを使ってテストする（モック無し）
        
        # テスト用ファイル作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Paper\n\nThis study [1] shows...\n")
            f.flush()
            
            try:
                success, result = self.workflow.execute(
                    input_file=f.name,
                    output_format='unified',
                    enable_link_extraction=False
                )
                
                self.assertTrue(success)
                self.assertIn('converted_text', result)
                self.assertIn('statistics', result)
                # 実際のパーサーの結果に基づく検証
                self.assertGreater(result['statistics']['total_citations'], 0)
                
            finally:
                os.unlink(f.name)
    
    def test_execute_with_output_file(self):
        """ワークフロー実行のテスト（出力ファイル指定）"""
        
        # テスト用ファイル作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as input_f:
            input_f.write("# Test Paper\n\nThis study [1, 2] shows...\n")
            input_f.flush()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as output_f:
                try:
                    success, result = self.workflow.execute(
                        input_file=input_f.name,
                        output_file=output_f.name,
                        output_format='unified'
                    )
                    
                    self.assertTrue(success)
                    self.assertIn('output_file', result)
                    self.assertEqual(result['output_file'], output_f.name)
                    
                    # 出力ファイルが作成されていることを確認
                    self.assertTrue(Path(output_f.name).exists())
                    
                finally:
                    os.unlink(input_f.name)
                    if Path(output_f.name).exists():
                        os.unlink(output_f.name)
    
    def test_generate_report(self):
        """レポート生成のテスト"""
        # モック結果データ
        mock_result = {
            'converted_text': "Test [1,2,3] converted",
            'statistics': {
                'total_citations': 3,
                'converted_citations': 3,
                'processing_time': 0.5
            },
            'input_file': 'test.md',
            'output_format': 'unified'
        }
        
        report = self.workflow.generate_report(mock_result)
        
        self.assertIn('Citation Parser Workflow Report', report)
        self.assertIn('Total citations found: 3', report)
        self.assertIn('test.md', report)
    
    def test_dry_run_execution(self):
        """ドライラン実行のテスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Paper\n\nThis study [1] shows...\n")
            f.flush()
            
            try:
                success, result = self.workflow.execute(
                    input_file=f.name,
                    dry_run=True
                )
                
                self.assertTrue(success)
                self.assertTrue(result.get('dry_run', False))
                self.assertIn('dry_run_analysis', result)
                
            finally:
                os.unlink(f.name)


def run_citation_parser_workflow_tests():
    """引用パーサーワークフローテストを実行"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_classes = [TestCitationParserWorkflow]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=== Citation Parser Workflow Tests ===")
    success = run_citation_parser_workflow_tests()
    
    if success:
        print("\n✅ All citation parser workflow tests passed!")
    else:
        print("\n❌ Some citation parser workflow tests failed!")
    
    sys.exit(0 if success else 1) 