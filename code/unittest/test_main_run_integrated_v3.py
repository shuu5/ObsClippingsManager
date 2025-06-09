#!/usr/bin/env python3
"""
テスト: main.py run-integrated コマンド v3.0仕様準拠

このテストは、ObsClippingsManager v3.0の run-integrated コマンドが
仕様書通りに動作することを検証します。

主要テスト項目:
- workspace_pathベースの統一設定システム
- デフォルト引数なし実行
- IntegratedWorkflowクラス使用
- 新しいオプション体系
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import sys
import os
from click.testing import CliRunner

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent / "py"
sys.path.insert(0, str(project_root))

from main import cli
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.workflows.integrated_workflow import IntegratedWorkflow


class TestMainRunIntegratedV3(unittest.TestCase):
    """main.py run-integrated コマンド v3.0仕様テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.test_dir = tempfile.mkdtemp()
        self.workspace_path = str(Path(self.test_dir) / "workspace")
        self.bibtex_file = str(Path(self.workspace_path) / "CurrentManuscript.bib")
        self.clippings_dir = str(Path(self.workspace_path) / "Clippings")
        
        # テスト環境作成
        Path(self.workspace_path).mkdir(parents=True, exist_ok=True)
        Path(self.clippings_dir).mkdir(parents=True, exist_ok=True)
        Path(self.bibtex_file).touch()
        
        # ランナー初期化
        self.runner = CliRunner()
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('main.IntegratedWorkflow')
    def test_workspace_path_option_exists(self, mock_workflow_class):
        """--workspace オプションが存在し、workspace_pathベースの統一設定が動作する"""
        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = {'status': 'success'}
        mock_workflow_class.return_value = mock_workflow
        
        result = self.runner.invoke(cli, [
            'run-integrated',
            '--workspace', self.workspace_path
        ])
        
        # コマンドが成功すること
        self.assertEqual(result.exit_code, 0)
        
        # IntegratedWorkflowが呼び出されること
        mock_workflow_class.assert_called_once()
        mock_workflow.execute.assert_called_once()
        
        # workspace_pathが引数に含まれること
        call_args = mock_workflow.execute.call_args[1]
        self.assertEqual(call_args['workspace_path'], self.workspace_path)
    
    @patch('main.IntegratedWorkflow')
    def test_default_execution_without_arguments(self, mock_workflow_class):
        """引数なしのデフォルト実行が可能"""
        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = {'status': 'success'}
        mock_workflow_class.return_value = mock_workflow
        
        result = self.runner.invoke(cli, ['run-integrated'])
        
        # コマンドが成功すること
        self.assertEqual(result.exit_code, 0)
        
        # IntegratedWorkflowが呼び出されること
        mock_workflow_class.assert_called_once()
        mock_workflow.execute.assert_called_once()
    
    @patch('main.IntegratedWorkflow')
    def test_show_plan_option(self, mock_workflow_class):
        """--show-plan オプションが正しく動作する"""
        mock_workflow = MagicMock()
        mock_plan_result = {
            'status': 'success',
            'plan': {
                'total_papers': 5,
                'execution_plan': {
                    'organize': {'papers_count': 2, 'status': 'planned'},
                    'sync': {'papers_count': 0, 'status': 'completed'},
                    'fetch': {'papers_count': 3, 'status': 'planned'},
                    'parse': {'papers_count': 1, 'status': 'planned'}
                },
                'estimated_total_time': '5 minutes 30 seconds'
            }
        }
        mock_workflow.show_execution_plan.return_value = mock_plan_result
        mock_workflow_class.return_value = mock_workflow
        
        result = self.runner.invoke(cli, [
            'run-integrated',
            '--workspace', self.workspace_path,
            '--show-plan'
        ])
        
        # コマンドが成功すること
        self.assertEqual(result.exit_code, 0)
        
        # show_execution_planが呼び出されること
        mock_workflow.show_execution_plan.assert_called_once()
        
        # executeは呼び出されないこと（プラン表示のみ）
        mock_workflow.execute.assert_not_called()
    
    @patch('main.IntegratedWorkflow')
    def test_force_reprocess_option(self, mock_workflow_class):
        """--force-reprocess オプションが正しく動作する"""
        mock_workflow = MagicMock()
        mock_workflow.force_reprocess.return_value = {'status': 'success'}
        mock_workflow_class.return_value = mock_workflow
        
        result = self.runner.invoke(cli, [
            'run-integrated',
            '--workspace', self.workspace_path,
            '--force-reprocess'
        ])
        
        # コマンドが成功すること
        self.assertEqual(result.exit_code, 0)
        
        # force_reprocessが呼び出されること
        mock_workflow.force_reprocess.assert_called_once()
        
        # 通常のexecuteは呼び出されないこと
        mock_workflow.execute.assert_not_called()
    
    @patch('main.IntegratedWorkflow')
    def test_papers_filter_option(self, mock_workflow_class):
        """--papers オプションで特定論文のフィルタリングが可能"""
        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = {'status': 'success'}
        mock_workflow_class.return_value = mock_workflow
        
        target_papers = "smith2023test,jones2024neural"
        
        result = self.runner.invoke(cli, [
            'run-integrated',
            '--workspace', self.workspace_path,
            '--papers', target_papers
        ])
        
        # コマンドが成功すること
        self.assertEqual(result.exit_code, 0)
        
        # executeが呼び出されること
        mock_workflow.execute.assert_called_once()
        
        # papers引数が正しく渡されること
        call_args = mock_workflow.execute.call_args[1]
        self.assertEqual(call_args['papers'], target_papers)
    
    @patch('main.IntegratedWorkflow')
    def test_skip_steps_option(self, mock_workflow_class):
        """--skip-steps オプションでステップのスキップが可能"""
        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = {'status': 'success'}
        mock_workflow_class.return_value = mock_workflow
        
        skip_steps = "organize,sync"
        
        result = self.runner.invoke(cli, [
            'run-integrated',
            '--workspace', self.workspace_path,
            '--skip-steps', skip_steps
        ])
        
        # コマンドが成功すること
        self.assertEqual(result.exit_code, 0)
        
        # executeが呼び出されること
        mock_workflow.execute.assert_called_once()
        
        # skip_steps引数が正しく渡されること
        call_args = mock_workflow.execute.call_args[1]
        self.assertEqual(call_args['skip_steps'], skip_steps)
    
    @patch('main.IntegratedWorkflow')
    def test_individual_path_options_override_workspace(self, mock_workflow_class):
        """個別パス指定がworkspace_pathベースの設定を上書きする"""
        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = {'status': 'success'}
        mock_workflow_class.return_value = mock_workflow
        
        custom_bibtex = str(Path(self.test_dir) / "custom.bib")
        custom_clippings = str(Path(self.test_dir) / "custom_clippings")
        Path(custom_bibtex).touch()
        Path(custom_clippings).mkdir()
        
        result = self.runner.invoke(cli, [
            'run-integrated',
            '--workspace', self.workspace_path,
            '--bibtex-file', custom_bibtex,
            '--clippings-dir', custom_clippings
        ])
        
        # コマンドが成功すること
        self.assertEqual(result.exit_code, 0)
        
        # executeが呼び出されること
        mock_workflow.execute.assert_called_once()
        
        # 個別指定パスが渡されること
        call_args = mock_workflow.execute.call_args[1]
        self.assertEqual(call_args['workspace_path'], self.workspace_path)
        self.assertEqual(call_args['bibtex_file'], custom_bibtex)
        self.assertEqual(call_args['clippings_dir'], custom_clippings)
    
    @patch('main.IntegratedWorkflow')
    def test_dry_run_mode(self, mock_workflow_class):
        """--dry-run モードが正しく動作する"""
        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = {'status': 'success'}
        mock_workflow_class.return_value = mock_workflow
        
        result = self.runner.invoke(cli, [
            '--dry-run',
            'run-integrated',
            '--workspace', self.workspace_path
        ])
        
        # コマンドが成功すること
        self.assertEqual(result.exit_code, 0)
        
        # executeが呼び出されること
        mock_workflow.execute.assert_called_once()
        
        # dry_runフラグが設定されること
        call_args = mock_workflow.execute.call_args[1]
        self.assertTrue(call_args['dry_run'])
    
    @patch('main.IntegratedWorkflow')
    def test_verbose_mode(self, mock_workflow_class):
        """--verbose モードが正しく動作する"""
        mock_workflow = MagicMock()
        mock_workflow.execute.return_value = {'status': 'success'}
        mock_workflow_class.return_value = mock_workflow
        
        result = self.runner.invoke(cli, [
            '--verbose',
            'run-integrated',
            '--workspace', self.workspace_path
        ])
        
        # コマンドが成功すること
        self.assertEqual(result.exit_code, 0)
        
        # executeが呼び出されること
        mock_workflow.execute.assert_called_once()
        
        # verboseフラグが設定されること
        call_args = mock_workflow.execute.call_args[1]
        self.assertTrue(call_args['verbose'])
    
    def test_integrated_workflow_import(self):
        """IntegratedWorkflowクラスが正しくインポートされる"""
        # IntegratedWorkflowクラスがインポート可能であること
        from modules.workflows.integrated_workflow import IntegratedWorkflow
        
        # クラスが存在し、必要なメソッドを持つこと
        self.assertTrue(hasattr(IntegratedWorkflow, 'execute'))
        self.assertTrue(hasattr(IntegratedWorkflow, 'show_execution_plan'))
        self.assertTrue(hasattr(IntegratedWorkflow, 'force_reprocess'))


if __name__ == '__main__':
    unittest.main() 