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
        mock_workflow_instance.execute.return_value = (True, {"enriched_successes": 5})
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'fetch-citations',
            '--bibtex-file', self.bibtex_file,
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.execute.assert_called_once()
        
        # enable_enrichmentがデフォルトでTrueになっていることを確認
        call_args = mock_workflow_instance.execute.call_args
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
        mock_workflow_instance.execute.return_value = (True, {"successful_fetches": 3})
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'fetch-citations',
            '--bibtex-file', self.bibtex_file,
            '--no-enable-enrichment',  # 明示的に無効化
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.execute.assert_called_once()
        
        # enable_enrichmentが明示的にFalseになっていることを確認
        call_args = mock_workflow_instance.execute.call_args
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





class TestIntegratedCommand(TestMainCLI):
    """run-integratedコマンドのテスト"""
    
    @patch('main.IntegratedWorkflow')
    @patch('main.IntegratedLogger')
    def test_run_integrated_basic(self, mock_logger, mock_workflow):
        """基本的な統合ワークフローのテスト"""
        # モックの設定
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute.return_value = {
            "status": "success",
            "success": True,
            "completed_steps": ["organize", "sync", "fetch", "ai-citation-support"],
            "processed_papers": 1
        }
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'run-integrated',
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.execute.assert_called_once()
    

    
    @patch('main.IntegratedWorkflow')
    @patch('main.IntegratedLogger')
    def test_run_integrated_enrichment_auto_enabled(self, mock_logger, mock_workflow):
        """run-integratedでデフォルトでenrichmentが有効になることのテスト"""
        # モックの設定
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute.return_value = {
            "status": "success",
            "success": True,
            "completed_steps": ["organize", "sync", "fetch", "ai-citation-support"],
            "processed_papers": 2
        }
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'run-integrated',
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        
        # integratedワークフローが呼ばれていることを確認
        mock_workflow.assert_called_once()
        mock_workflow_instance.execute.assert_called_once()
        
        # executeの呼び出し引数を確認してenrichmentが有効になっているかチェック
        call_args = mock_workflow_instance.execute.call_args
        options = call_args[1] if call_args and len(call_args) > 1 else {}
        # デフォルトでenrichmentが有効になっていることを確認（v3.1では常に有効）
        self.assertTrue(options.get('enable_enrichment', True), 
                       "enrichment should be auto-enabled in integrated workflow v3.1")
    
    @patch('main.IntegratedWorkflow')
    @patch('main.IntegratedLogger')
    def test_run_integrated_enrichment_can_be_disabled(self, mock_logger, mock_workflow):
        """run-integratedでenrichmentを明示的に無効化できることのテスト"""
        # モックの設定
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute.return_value = {
            "status": "success",
            "success": True,
            "completed_steps": ["organize", "sync", "fetch", "ai-citation-support"],
            "processed_papers": 2
        }
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'run-integrated',
            '--disable-enrichment',
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        
        # integratedワークフローが呼ばれていることを確認
        mock_workflow.assert_called_once()
        mock_workflow_instance.execute.assert_called_once()
        
        # executeの呼び出し引数を確認してenrichmentが無効になっているかチェック
        call_args = mock_workflow_instance.execute.call_args
        options = call_args[1] if call_args and len(call_args) > 1 else {}
        # enrichmentが無効になっていることを確認
        self.assertFalse(options.get('enable_enrichment', True), 
                        "enrichment should be disabled when --disable-enrichment is used")

    @patch('main.IntegratedWorkflow')
    @patch('main.IntegratedLogger')
    def test_run_integrated_with_tagger_enabled(self, mock_logger, mock_workflow):
        """run-integratedで--enable-taggerオプションが正しく動作することのテスト"""
        # モックの設定
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute.return_value = {
            "status": "success",
            "success": True,
            "completed_steps": ["organize", "sync", "fetch", "ai-citation-support", "tagger"],
            "processed_papers": 2
        }
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'run-integrated',
            '--enable-tagger',
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        
        # integratedワークフローが呼ばれていることを確認
        mock_workflow.assert_called_once()
        mock_workflow_instance.execute.assert_called_once()
        
        # executeの呼び出し引数を確認してtaggerが有効になっているかチェック
        call_args = mock_workflow_instance.execute.call_args
        options = call_args[1] if call_args and len(call_args) > 1 else {}
        # taggerが有効になっていることを確認
        self.assertTrue(options.get('enable_tagger', False), 
                       "tagger should be enabled when --enable-tagger is used")

    @patch('main.IntegratedWorkflow')
    @patch('main.IntegratedLogger')
    def test_run_integrated_with_translate_abstract_enabled(self, mock_logger, mock_workflow):
        """run-integratedで--enable-translate-abstractオプションが正しく動作することのテスト"""
        # モックの設定
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute.return_value = {
            "status": "success",
            "success": True,
            "completed_steps": ["organize", "sync", "fetch", "ai-citation-support", "translate_abstract"],
            "processed_papers": 2
        }
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'run-integrated',
            '--enable-translate-abstract',
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        
        # integratedワークフローが呼ばれていることを確認
        mock_workflow.assert_called_once()
        mock_workflow_instance.execute.assert_called_once()
        
        # executeの呼び出し引数を確認してtranslate_abstractが有効になっているかチェック
        call_args = mock_workflow_instance.execute.call_args
        options = call_args[1] if call_args and len(call_args) > 1 else {}
        # translate_abstractが有効になっていることを確認
        self.assertTrue(options.get('enable_translate_abstract', False), 
                       "translate_abstract should be enabled when --enable-translate-abstract is used")

    @patch('main.IntegratedWorkflow')
    @patch('main.IntegratedLogger')
    def test_run_integrated_with_both_ai_features_enabled(self, mock_logger, mock_workflow):
        """run-integratedでAI機能両方を有効化できることのテスト"""
        # モックの設定
        mock_logger_instance = Mock()
        mock_workflow_instance = Mock()
        
        mock_logger.return_value = mock_logger_instance
        mock_workflow.return_value = mock_workflow_instance
        
        # ワークフロー実行の成功をモック
        mock_workflow_instance.execute.return_value = {
            "status": "success",
            "success": True,
            "completed_steps": ["organize", "sync", "fetch", "ai-citation-support", "tagger", "translate_abstract"],
            "processed_papers": 2
        }
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'run-integrated',
            '--enable-tagger',
            '--enable-translate-abstract',
            '--auto-approve'
        ])
        
        self.assertEqual(result.exit_code, 0)
        
        # integratedワークフローが呼ばれていることを確認
        mock_workflow.assert_called_once()
        mock_workflow_instance.execute.assert_called_once()
        
        # executeの呼び出し引数を確認して両方が有効になっているかチェック
        call_args = mock_workflow_instance.execute.call_args
        options = call_args[1] if call_args and len(call_args) > 1 else {}
        # 両方が有効になっていることを確認
        self.assertTrue(options.get('enable_tagger', False), 
                       "tagger should be enabled when --enable-tagger is used")
        self.assertTrue(options.get('enable_translate_abstract', False), 
                       "translate_abstract should be enabled when --enable-translate-abstract is used")


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
        mock_workflow_instance.validate_workflow_configuration.return_value = (True, [])
        
        result = self.runner.invoke(main.cli, [
            '--config', self.config_file,
            'validate-config',
            '--workflow-type', 'citation_fetching'
        ])
        
        self.assertEqual(result.exit_code, 0)
        mock_workflow_instance.validate_workflow_configuration.assert_called_once()
    
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
            {
                "timestamp": "2023-01-01T10:00:00", 
                "workflow_type": "sync_check", 
                "success": True,
                "execution_time": 15.5
            }
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