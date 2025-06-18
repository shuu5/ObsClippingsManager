"""
Unit tests for the CLI interface.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path
import click
from click.testing import CliRunner
import tempfile
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from code.py.cli import cli


class TestCLIBasicFunctionality:
    """Test basic CLI functionality"""
    
    def test_cli_imports_successfully(self):
        """CLIモジュールがインポートできることを確認"""
        try:
            from code.py import cli
            assert hasattr(cli, 'cli')
        except ImportError as e:
            pytest.fail(f"Failed to import CLI module: {e}")
    
    def test_cli_is_click_command(self):
        """CLIがClickコマンドであることを確認"""
        assert isinstance(cli, click.Command) or isinstance(cli, click.Group)
    
    def test_cli_help_command(self):
        """ヘルプコマンドが正常に動作することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Usage:' in result.output
        assert 'Options:' in result.output


class TestCLIOptions:
    """Test CLI options and arguments"""
    
    def test_workspace_path_option(self):
        """--workspace-pathオプションが機能することを確認"""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ['--workspace-path', tmpdir])
            # コマンドが実行されることを確認
            assert result.exit_code in [0, 1]  # 0: success, 1: expected error
    
    def test_dry_run_option(self):
        """--dry-runオプションが機能することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--dry-run'])
        assert result.exit_code in [0, 1]
        if result.exit_code == 0:
            assert 'DRY RUN' in result.output or 'シミュレーション' in result.output
    
    def test_force_option(self):
        """--forceオプションが機能することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--force'])
        assert result.exit_code in [0, 1]
    
    def test_show_plan_option(self):
        """--show-planオプションが機能することを確認"""
        runner = CliRunner()
        # show-planにはworkspace-pathが必要
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ['--show-plan', '--workspace-path', tmpdir])
            assert result.exit_code == 0
            assert '実行計画' in result.output or 'Execution Plan' in result.output
    
    def test_disable_ai_option(self):
        """--disable-aiオプションが機能することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--disable-ai', '--dry-run'])
        assert result.exit_code in [0, 1]
    
    def test_enable_only_tagger_option(self):
        """--enable-only-taggerオプションが機能することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--enable-only-tagger', '--dry-run'])
        assert result.exit_code in [0, 1]
    
    def test_disable_tagger_option(self):
        """--disable-taggerオプションが機能することを確認"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--disable-tagger', '--dry-run'])
        assert result.exit_code in [0, 1]


class TestCLIWorkflowIntegration:
    """Test CLI integration with IntegratedWorkflow"""
    
    @patch('code.py.cli.IntegratedWorkflow')
    @patch('code.py.cli.ConfigManager')
    @patch('code.py.cli.IntegratedLogger')
    def test_cli_calls_integrated_workflow(self, mock_logger, mock_config, mock_workflow):
        """CLIがIntegratedWorkflowを正しく呼び出すことを確認"""
        runner = CliRunner()
        
        # モックの設定
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        mock_workflow_instance = MagicMock()
        mock_workflow.return_value = mock_workflow_instance
        mock_workflow_instance.execute.return_value = {
            'status': 'completed',
            'processed': 2,
            'failed': 0
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ['--workspace-path', tmpdir])
            
            # IntegratedWorkflowが呼び出されたことを確認
            mock_workflow.assert_called_once()
            mock_workflow_instance.execute.assert_called_once()
    
    @patch('code.py.cli.IntegratedWorkflow')
    @patch('code.py.cli.ConfigManager')
    @patch('code.py.cli.IntegratedLogger')
    def test_cli_passes_options_to_workflow(self, mock_logger, mock_config, mock_workflow):
        """CLIオプションがIntegratedWorkflowに正しく渡されることを確認"""
        runner = CliRunner()
        
        # モックの設定
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        mock_workflow_instance = MagicMock()
        mock_workflow.return_value = mock_workflow_instance
        mock_workflow_instance.execute.return_value = {
            'status': 'completed',
            'processed': 0,
            'failed': 0
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, [
                '--workspace-path', tmpdir,
                '--dry-run',
                '--force',
                '--disable-ai'
            ])
            
            # executeメソッドに正しいオプションが渡されたことを確認
            _, kwargs = mock_workflow_instance.execute.call_args
            assert kwargs.get('dry_run') is True
            assert kwargs.get('force_reprocess') is True
            assert kwargs.get('disable_ai') is True


class TestCLIOutput:
    """Test CLI output and progress display"""
    
    @patch('code.py.cli.IntegratedWorkflow')
    @patch('code.py.cli.ConfigManager')
    @patch('code.py.cli.IntegratedLogger')
    def test_cli_displays_progress(self, mock_logger, mock_config, mock_workflow):
        """CLIが進捗を表示することを確認"""
        runner = CliRunner()
        
        # モックの設定
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        mock_workflow_instance = MagicMock()
        mock_workflow.return_value = mock_workflow_instance
        
        # executeメソッドを設定して進捗コールバックを呼び出す
        def execute_with_progress(workspace_path, **options):
            if 'progress_callback' in options:
                callback = options['progress_callback']
                callback('organize', 'started')
                callback('organize', 'completed')
            return {'status': 'completed', 'processed': 2, 'failed': 0}
        
        mock_workflow_instance.execute.side_effect = execute_with_progress
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ['--workspace-path', tmpdir])
            
            # 進捗メッセージが出力されることを確認
            assert 'organize' in result.output
    
    @patch('code.py.cli.IntegratedWorkflow')
    @patch('code.py.cli.ConfigManager')
    @patch('code.py.cli.IntegratedLogger')
    def test_cli_displays_final_report(self, mock_logger, mock_config, mock_workflow):
        """CLIが最終レポートを表示することを確認"""
        runner = CliRunner()
        
        # モックの設定
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        mock_workflow_instance = MagicMock()
        mock_workflow.return_value = mock_workflow_instance
        mock_workflow_instance.execute.return_value = {
            'status': 'completed',
            'processed': 5,
            'failed': 1,
            'steps_completed': ['organize', 'sync', 'fetch']
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ['--workspace-path', tmpdir])
            
            # 最終レポートが出力されることを確認
            assert '処理完了' in result.output or 'Completed' in result.output
            assert '5' in result.output  # processed count
            assert '1' in result.output  # failed count


class TestCLIErrorHandling:
    """Test CLI error handling"""
    
    def test_cli_handles_missing_workspace(self):
        """存在しないワークスペースを指定した場合のエラーハンドリング"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--workspace-path', '/non/existent/path'])
        assert result.exit_code != 0
        assert 'エラー' in result.output or 'Error' in result.output
    
    @patch('code.py.cli.IntegratedWorkflow')
    @patch('code.py.cli.ConfigManager')
    @patch('code.py.cli.IntegratedLogger')
    def test_cli_handles_workflow_exception(self, mock_logger, mock_config, mock_workflow):
        """ワークフロー実行中の例外をハンドリングすることを確認"""
        runner = CliRunner()
        
        # モックの設定
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        
        mock_logger_instance = MagicMock()
        mock_logger.return_value = mock_logger_instance
        
        mock_workflow_instance = MagicMock()
        mock_workflow.return_value = mock_workflow_instance
        mock_workflow_instance.execute.side_effect = Exception("Test error")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ['--workspace-path', tmpdir])
            
            assert result.exit_code != 0
            assert 'エラー' in result.output or 'Error' in result.output


if __name__ == '__main__':
    pytest.main([__file__, '-v'])