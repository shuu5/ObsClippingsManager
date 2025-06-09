"""
メインCLI機能のテスト

ObsClippingsManager CLI インターフェースのテストスイート
"""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

# テスト対象モジュールのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'py'))

# CLIモジュールをインポート
import main
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.workflows.workflow_manager import WorkflowManager


class TestMainCLI(unittest.TestCase):
    """メインCLI機能のテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        
        # テスト用設定ファイル作成
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write('{"common": {"bibtex_file": "test.bib", "clippings_dir": "clippings"}}')
        
        # テスト用BibTeXファイル作成
        self.bibtex_file = os.path.join(self.temp_dir, "test.bib")
        with open(self.bibtex_file, 'w', encoding='utf-8') as f:
            f.write('@article{test2023,\n  title={Test Paper},\n  author={Test, Author},\n  doi={10.1000/test}\n}')
        
        # テスト用Clippingsディレクトリ作成
        self.clippings_dir = os.path.join(self.temp_dir, "clippings")
        os.makedirs(self.clippings_dir, exist_ok=True)
        
        # テスト用Markdownファイル作成
        self.markdown_file = os.path.join(self.temp_dir, "test.md")
        with open(self.markdown_file, 'w', encoding='utf-8') as f:
            f.write('# Test Paper\n\nThis study [1] shows...')
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestCLIInitialization(TestMainCLI):
    """CLI初期化のテスト"""
    
    def test_cli_help(self):
        """CLIヘルプ表示のテスト"""
        result = self.runner.invoke(main.cli, ['--help'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('ObsClippingsManager', result.output)
        self.assertIn('学術文献管理システム', result.output)
    
    def test_cli_version(self):
        """バージョン表示のテスト"""
        result = self.runner.invoke(main.cli, ['version'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('ObsClippingsManager', result.output)
    
    @patch('main.ConfigManager')
    @patch('main.IntegratedLogger')
    @patch('main.WorkflowManager')
    def test_cli_initialization_success(self, mock_workflow, mock_logger, mock_config):
        """CLI初期化成功のテスト"""
        # モックの設定
        mock_config.return_value = Mock()
        mock_logger.return_value = Mock()
        mock_workflow.return_value = Mock()
        
        result = self.runner.invoke(main.cli, ['--config', self.config_file, '--verbose'])
        
        # 初期化が成功すること
        self.assertEqual(result.exit_code, 0)
        mock_config.assert_called_once()
        mock_logger.assert_called_once()
        mock_workflow.assert_called_once()
    
    def test_cli_initialization_invalid_config(self):
        """不正な設定ファイル時の初期化エラーテスト"""
        invalid_config = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_config, 'w') as f:
            f.write('invalid json content')
        
        result = self.runner.invoke(main.cli, ['--config', invalid_config, 'version'])
        
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('Initialization failed', result.output)


class TestFetchCitationsCommand(TestMainCLI):
    """fetch-citationsコマンドのテスト"""
    
    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_fetch_citations_basic(self, mock_config, mock_logger, mock_workflow):
        """基本的な引用文献取得のテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute.return_value = (True, {"processed_papers": 1})
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'fetch-citations',
            '--bibtex-file', self.bibtex_file,
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.execute.assert_called_once()
    
    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_fetch_citations_with_enrichment(self, mock_config, mock_logger, mock_workflow):
        """メタデータ補完有効時の引用文献取得テスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute.return_value = (True, {"processed_papers": 1})
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'fetch-citations',
            '--bibtex-file', self.bibtex_file,
            '--enable-enrichment',
            '--enrichment-field-type', 'computer_science',
            '--enrichment-quality-threshold', '0.9',
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.execute.assert_called_once()
        
        # 呼び出された引数を確認
        call_args = mock_workflow_instance.execute.call_args
        options = call_args[1]  # キーワード引数
        self.assertTrue(options.get('enable_enrichment'))
        self.assertEqual(options.get('enrichment_field_type'), 'computer_science')
        self.assertEqual(options.get('enrichment_quality_threshold'), 0.9)
    
    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_fetch_citations_dry_run(self, mock_config, mock_logger, mock_workflow):
        """ドライラン実行のテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute.return_value = (True, {"dry_run": True})
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            '--dry-run',
            'fetch-citations',
            '--bibtex-file', self.bibtex_file,
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.execute.assert_called_once()
        
        # ドライランオプションが渡されることを確認
        call_args = mock_workflow_instance.execute.call_args
        options = call_args[1]
        self.assertTrue(options.get('dry_run'))

    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_fetch_citations_enrichment_default_enabled(self, mock_config, mock_logger, mock_workflow):
        """メタデータ補完がデフォルトで有効になっているかのテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute_workflow.return_value = (True, {"enriched_successes": 5})
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'fetch-citations',
            '--bibtex-file', self.bibtex_file,
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.execute_workflow.assert_called_once()
        
        # enable_enrichmentがデフォルトでTrueになっていることを確認
        call_args = mock_workflow_instance.execute_workflow.call_args
        options = call_args[1]
        self.assertTrue(options.get('enable_enrichment', False))

    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_fetch_citations_enrichment_can_be_disabled(self, mock_config, mock_logger, mock_workflow):
        """メタデータ補完を明示的に無効化できることのテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute_workflow.return_value = (True, {"successful_fetches": 3})
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'fetch-citations',
            '--bibtex-file', self.bibtex_file,
            '--no-enable-enrichment',  # 明示的に無効化
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.execute_workflow.assert_called_once()
        
        # enable_enrichmentが明示的にFalseになっていることを確認
        call_args = mock_workflow_instance.execute_workflow.call_args
        options = call_args[1]
        self.assertFalse(options.get('enable_enrichment', True))
        
     
class TestSyncCheckCommand(TestMainCLI):
    """sync-checkコマンドのテスト"""
    
    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_sync_check_basic(self, mock_config, mock_logger, mock_workflow):
        """基本的な同期チェックのテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute.return_value = (True, {
            "missing_in_clippings": [],
            "missing_in_bib": [],
            "statistics": {"total_papers": 1}
        })
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'sync-check',
            '--bibtex-file', self.bibtex_file,
            '--clippings-dir', self.clippings_dir
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.execute.assert_called_once()
    
    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_sync_check_with_options(self, mock_config, mock_logger, mock_workflow):
        """オプション指定時の同期チェックテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute.return_value = (True, {
            "missing_in_clippings": [],
            "missing_in_bib": [],
            "statistics": {"total_papers": 1}
        })
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'sync-check',
            '--bibtex-file', self.bibtex_file,
            '--clippings-dir', self.clippings_dir,
            '--max-displayed-files', '20',
            '--no-show-clickable-links',
            '--no-sort-by-year'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.execute.assert_called_once()
        
        # オプションが正しく渡されることを確認
        call_args = mock_workflow_instance.execute.call_args
        options = call_args[1]
        self.assertEqual(options.get('max_displayed_files'), 20)
        self.assertFalse(options.get('show_clickable_links'))
        self.assertFalse(options.get('sort_by_year'))


class TestParseCitationsCommand(TestMainCLI):
    """parse-citationsコマンドのテスト"""
    
    @patch('main.CitationParserWorkflow')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_parse_citations_basic(self, mock_config, mock_logger, mock_parser):
        """基本的な引用文献解析のテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_parser_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_parser.return_value = mock_parser_instance
        
        # ワークフロー実行の成功をモック
        mock_parser_instance.execute.return_value = (True, {
            "converted_citations": 3,
            "processed_content": "Test output"
        })
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'parse-citations',
            '--input-file', self.markdown_file,
            '--pattern-type', 'all',
            '--output-format', 'unified'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_parser_instance.execute.assert_called_once()
    
    @patch('main.CitationParserWorkflow')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_parse_citations_with_output_file(self, mock_config, mock_logger, mock_parser):
        """出力ファイル指定時の引用文献解析テスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_parser_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_parser.return_value = mock_parser_instance
        
        # ワークフロー実行の成功をモック
        mock_parser_instance.execute.return_value = (True, {
            "converted_citations": 3,
            "processed_content": "Test output"
        })
        
        output_file = os.path.join(self.temp_dir, "output.md")
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'parse-citations',
            '--input-file', self.markdown_file,
            '--output-file', output_file,
            '--pattern-type', 'basic',
            '--output-format', 'table',
            '--enable-link-extraction'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_parser_instance.execute.assert_called_once()
        
        # オプションが正しく渡されることを確認
        call_args = mock_parser_instance.execute.call_args
        kwargs = call_args[1] if len(call_args) > 1 else call_args[0]
        self.assertEqual(kwargs.get('output_file'), output_file)
        self.assertEqual(kwargs.get('pattern_type'), 'basic')
        self.assertEqual(kwargs.get('output_format'), 'table')
        self.assertTrue(kwargs.get('enable_link_extraction'))


class TestIntegratedCommand(TestMainCLI):
    """run-integratedコマンドのテスト"""
    
    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_run_integrated_basic(self, mock_config, mock_logger, mock_workflow):
        """基本的な統合ワークフローのテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute.return_value = (True, {
            "sync_check": {"missing_files": 0},
            "citation_fetching": {"processed_papers": 1},
            "file_organization": {"organized_files": 1}
        })
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'run-integrated',
            '--sync-first',
            '--fetch-citations',
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.execute.assert_called_once()
    
    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_run_integrated_with_citation_parser(self, mock_config, mock_logger, mock_workflow):
        """引用文献解析を含む統合ワークフローのテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute.return_value = (True, {
            "citation_parser": {"converted_citations": 3},
            "citation_fetching": {"processed_papers": 1}
        })
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'run-integrated',
            '--include-citation-parser',
            '--citation-parser-input', self.markdown_file,
            '--fetch-citations',
            '--continue-on-failure'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.execute.assert_called_once()
    
    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_run_integrated_enrichment_auto_enabled(self, mock_config, mock_logger, mock_workflow):
        """run-integratedでfetch-citationsが呼ばれる際に自動でenrichmentが有効になることのテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute_workflow.return_value = (True, {
            "sync_integration": {"synced_papers": 2},
            "enriched_successes": 2
        })
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'run-integrated',
            '--fetch-citations',
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        
        # citation_fetchingワークフローが呼ばれていることを確認
        workflow_calls = mock_workflow_instance.execute_workflow.call_args_list
        citation_call = None
        for call in workflow_calls:
            if len(call[0]) > 0 and str(call[0][0]) == 'WorkflowType.CITATION_FETCHING':
                citation_call = call
                break
        
        self.assertIsNotNone(citation_call, "citation_fetching workflow should be called")
        
        # enrichmentが自動で有効になっていることを確認
        options = citation_call[1]
        self.assertTrue(options.get('enable_enrichment', False), 
                       "enrichment should be auto-enabled in integrated workflow")
    
    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_run_integrated_enrichment_can_be_disabled(self, mock_config, mock_logger, mock_workflow):
        """run-integratedでenrichmentを明示的に無効化できることのテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute_workflow.return_value = (True, {
            "sync_integration": {"synced_papers": 2},
            "successful_fetches": 2
        })
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'run-integrated',
            '--fetch-citations',
            '--disable-enrichment',
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        
        # citation_fetchingワークフローが呼ばれていることを確認
        workflow_calls = mock_workflow_instance.execute_workflow.call_args_list
        citation_call = None
        for call in workflow_calls:
            if len(call[0]) > 0 and str(call[0][0]) == 'WorkflowType.CITATION_FETCHING':
                citation_call = call
                break
        
        self.assertIsNotNone(citation_call, "citation_fetching workflow should be called")
        
        # enrichmentが無効になっていることを確認
        options = citation_call[1]
        self.assertFalse(options.get('enable_enrichment', True), 
                        "enrichment should be disabled when --disable-enrichment is used")


class TestUtilityCommands(TestMainCLI):
    """ユーティリティコマンドのテスト"""
    
    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_validate_config_command(self, mock_config, mock_logger, mock_workflow):
        """設定検証コマンドのテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # 設定検証の成功をモック
        mock_workflow_instance.validate_configuration.return_value = (True, [])
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'validate-config',
            '--workflow-type', 'citation_fetching'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.validate_configuration.assert_called_once()
    
    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_show_history_command(self, mock_config, mock_logger, mock_workflow):
        """実行履歴表示コマンドのテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # 履歴データのモック
        mock_workflow_instance.get_execution_history.return_value = [
            {"timestamp": "2023-01-01", "workflow_type": "sync_check", "success": True}
        ]
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'show-history',
            '--limit', '5',
            '--workflow-type', 'sync_check'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.get_execution_history.assert_called_once()
    
    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_show_stats_command(self, mock_config, mock_logger, mock_workflow):
        """統計情報表示コマンドのテスト"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # 統計データのモック
        mock_workflow_instance.get_workflow_statistics.return_value = {
            "total_executions": 10,
            "success_rate": 0.9
        }
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'show-stats'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.get_workflow_statistics.assert_called_once()


class TestCLIErrorHandling(TestMainCLI):
    """CLIエラーハンドリングのテスト"""
    
    def test_missing_required_file(self):
        """必須ファイル不在時のエラーハンドリング"""
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'parse-citations',
            '--input-file', '/nonexistent/file.md'
        ])
        
        self.assertNotEqual(result.exit_code, 0)
    
    @patch('main.WorkflowManager')
    @patch('main.IntegratedLogger')
    @patch('main.ConfigManager')
    def test_workflow_execution_failure(self, mock_config, mock_logger, mock_workflow):
        """ワークフロー実行失敗時のエラーハンドリング"""
        # モックの設定
        mock_config_instance = Mock()
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_config.return_value = mock_config_instance
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の失敗をモック
        mock_workflow_instance.execute.return_value = (False, {"error": "Test error"})
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'fetch-citations',
            '--bibtex-file', self.bibtex_file,
            '--auto-approve'
        ])
        
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('error', result.output.lower())


if __name__ == '__main__':
    unittest.main() 