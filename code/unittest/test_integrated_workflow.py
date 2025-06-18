"""
IntegratedWorkflowクラスのユニットテスト

統合ワークフロー実行システムの動作確認
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# テスト対象
from modules.integrated_workflow.integrated_workflow import IntegratedWorkflow


class TestIntegratedWorkflow(unittest.TestCase):
    """IntegratedWorkflowクラスのテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.mock_config_manager = Mock()
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
        self.mock_ai_controller = Mock()
        self.mock_ai_controller.get_summary.return_value = "AI機能: すべて有効"
        self.mock_ai_controller.get_enabled_features.return_value = ['tagger', 'translate', 'ochiai']
        self.mock_ai_controller.is_tagger_enabled.return_value = True
        self.mock_ai_controller.is_translate_enabled.return_value = True
        self.mock_ai_controller.is_ochiai_enabled.return_value = True
    
    def test_init(self):
        """初期化テスト"""
        workflow = IntegratedWorkflow(
            self.mock_config_manager, 
            self.mock_logger, 
            self.mock_ai_controller
        )
        
        self.assertIsNotNone(workflow.config_manager)
        self.assertIsNotNone(workflow.logger)
        self.assertIsNotNone(workflow.ai_feature_controller)
        self.assertEqual(workflow._workflow_modules, {})
    
    def test_init_with_default_ai_controller(self):
        """デフォルトAI制御での初期化テスト"""
        workflow = IntegratedWorkflow(self.mock_config_manager, self.mock_logger)
        
        self.assertIsNotNone(workflow.ai_feature_controller)
        # デフォルトAI制御が正しく動作することを確認
        self.assertTrue(workflow.ai_feature_controller.is_tagger_enabled())
        self.assertTrue(workflow.ai_feature_controller.is_translate_enabled())
        self.assertTrue(workflow.ai_feature_controller.is_ochiai_enabled())
    
    def test_get_workflow_steps_all_enabled(self):
        """全機能有効時のワークフローステップ取得テスト"""
        workflow = IntegratedWorkflow(
            self.mock_config_manager, 
            self.mock_logger, 
            self.mock_ai_controller
        )
        
        steps = workflow._get_workflow_steps()
        step_names = [step[0] for step in steps]
        
        expected_steps = [
            'organize', 'sync', 'fetch', 'section_parsing', 'ai_citation_support',
            'enhanced-tagger', 'enhanced-translate', 'ochiai-format', 
            'citation_pattern_normalizer', 'final-sync'
        ]
        
        self.assertEqual(step_names, expected_steps)
    
    def test_get_workflow_steps_ai_disabled(self):
        """AI機能無効時のワークフローステップ取得テスト"""
        self.mock_ai_controller.is_tagger_enabled.return_value = False
        self.mock_ai_controller.is_translate_enabled.return_value = False
        self.mock_ai_controller.is_ochiai_enabled.return_value = False
        
        workflow = IntegratedWorkflow(
            self.mock_config_manager, 
            self.mock_logger, 
            self.mock_ai_controller
        )
        
        steps = workflow._get_workflow_steps()
        step_names = [step[0] for step in steps]
        
        expected_steps = [
            'organize', 'sync', 'fetch', 'section_parsing', 'ai_citation_support',
            'citation_pattern_normalizer', 'final-sync'
        ]
        
        self.assertEqual(step_names, expected_steps)
    
    @patch('modules.integrated_workflow.integrated_workflow.BibTeXParser')
    def test_detect_edge_cases_and_get_valid_papers(self, mock_bibtex_parser):
        """エッジケース検出テスト"""
        # BibTeXパーサーのモック設定
        mock_parser_instance = Mock()
        mock_parser_instance.parse_file.return_value = {
            'paper1': {}, 'paper2': {}, 'paper3': {}
        }
        mock_bibtex_parser.return_value = mock_parser_instance
        
        workflow = IntegratedWorkflow(
            self.mock_config_manager, 
            self.mock_logger, 
            self.mock_ai_controller
        )
        workflow.bibtex_parser = mock_parser_instance
        
        # テスト用パスの作成
        workspace_path = Path("/test/workspace")
        bibtex_file = workspace_path / "CurrentManuscript.bib"
        clippings_dir = workspace_path / "Clippings"
        
        # clippings_dirの存在確認をモック
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'rglob') as mock_rglob:
            
            # rglobの戻り値をモック（paper1, paper2のMarkdownファイルが存在）
            mock_files = [
                Path("/test/workspace/Clippings/paper1/paper1.md"),
                Path("/test/workspace/Clippings/paper2/paper2.md")
            ]
            mock_rglob.return_value = mock_files
            
            valid_papers, edge_cases = workflow._detect_edge_cases_and_get_valid_papers(
                bibtex_file, clippings_dir
            )
        
        # 結果検証
        self.assertEqual(set(valid_papers), {'paper1', 'paper2'})
        self.assertEqual(edge_cases['missing_in_clippings'], ['paper3'])
        self.assertEqual(edge_cases['orphaned_in_clippings'], [])
    
    def test_extract_citation_key_from_path(self):
        """Citation key抽出テスト"""
        workflow = IntegratedWorkflow(
            self.mock_config_manager, 
            self.mock_logger, 
            self.mock_ai_controller
        )
        
        # サブディレクトリのMarkdownファイル
        md_file = Path("/workspace/Clippings/paper123/paper123.md")
        citation_key = workflow._extract_citation_key_from_path(md_file)
        self.assertEqual(citation_key, "paper123")
        
        # Clippings直下のMarkdownファイル
        md_file_direct = Path("/workspace/Clippings/orphaned.md")
        citation_key_direct = workflow._extract_citation_key_from_path(md_file_direct)
        self.assertIsNone(citation_key_direct)
    
    def test_execute_dry_run(self):
        """ドライラン実行テスト"""
        workflow = IntegratedWorkflow(
            self.mock_config_manager, 
            self.mock_logger, 
            self.mock_ai_controller
        )
        
        # _detect_edge_cases_and_get_valid_papersをモック
        with patch.object(workflow, '_detect_edge_cases_and_get_valid_papers') as mock_detect:
            mock_detect.return_value = (['paper1', 'paper2'], {})
            
            result = workflow.execute("/test/workspace", dry_run=True)
        
        self.assertEqual(result['status'], 'dry_run_completed')
        self.assertEqual(result['total_papers_processed'], 2)
    
    def test_execute_show_plan(self):
        """実行計画表示テスト"""
        workflow = IntegratedWorkflow(
            self.mock_config_manager, 
            self.mock_logger, 
            self.mock_ai_controller
        )
        
        # _detect_edge_cases_and_get_valid_papersをモック
        with patch.object(workflow, '_detect_edge_cases_and_get_valid_papers') as mock_detect, \
             patch.object(workflow, '_show_execution_plan') as mock_show_plan:
            
            mock_detect.return_value = (['paper1'], {})
            
            result = workflow.execute("/test/workspace", show_plan=True)
        
        mock_show_plan.assert_called_once()
        self.assertEqual(result['total_papers_processed'], 1)
    
    def test_get_workflow_module_lazy_initialization(self):
        """ワークフローモジュールの遅延初期化テスト"""
        workflow = IntegratedWorkflow(
            self.mock_config_manager, 
            self.mock_logger, 
            self.mock_ai_controller
        )
        
        # 初回取得
        with patch('modules.integrated_workflow.integrated_workflow.FileOrganizer') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            module1 = workflow._get_workflow_module('organize', mock_class)
            
            # クラスが1回だけ初期化されること
            mock_class.assert_called_once()
            self.assertEqual(module1, mock_instance)
        
        # 2回目取得（キャッシュから）
        with patch('modules.integrated_workflow.integrated_workflow.FileOrganizer') as mock_class2:
            module2 = workflow._get_workflow_module('organize', mock_class2)
            
            # 2回目はクラス初期化されないこと
            mock_class2.assert_not_called()
            self.assertEqual(module2, mock_instance)  # 同じインスタンス


class TestIntegratedWorkflowStepExecution(unittest.TestCase):
    """IntegratedWorkflowのステップ実行テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        self.mock_config_manager = Mock()
        self.mock_logger = Mock()
        self.mock_logger.get_logger.return_value = Mock()
        self.mock_ai_controller = Mock()
        self.mock_ai_controller.get_summary.return_value = "AI機能: すべて有効"
        self.mock_ai_controller.get_enabled_features.return_value = ['tagger', 'translate', 'ochiai']
        
        self.workflow = IntegratedWorkflow(
            self.mock_config_manager, 
            self.mock_logger, 
            self.mock_ai_controller
        )
        
        self.workspace_path = Path("/test/workspace")
        self.target_papers = ['paper1', 'paper2']
    
    def test_execute_organize(self):
        """organize実行テスト"""
        mock_organizer = Mock()
        mock_organizer.organize_workspace.return_value = {'status': 'success'}
        
        with patch.object(self.workflow, '_get_workflow_module', return_value=mock_organizer):
            result = self.workflow._execute_organize(self.workspace_path, self.target_papers)
        
        mock_organizer.organize_workspace.assert_called_once()
        self.assertEqual(result['status'], 'success')
    
    def test_execute_sync(self):
        """sync実行テスト"""
        mock_sync_checker = Mock()
        mock_sync_checker.check_workspace_consistency.return_value = {'consistency_status': 'validated'}
        
        with patch.object(self.workflow, '_get_workflow_module', return_value=mock_sync_checker):
            result = self.workflow._execute_sync(self.workspace_path, self.target_papers)
        
        mock_sync_checker.check_workspace_consistency.assert_called_once()
        self.assertEqual(result['consistency_status'], 'validated')
    
    def test_execute_fetch(self):
        """fetch実行テスト"""
        mock_citation_fetcher = Mock()
        mock_citation_fetcher.process_items.return_value = None
        
        with patch.object(self.workflow, '_get_workflow_module', return_value=mock_citation_fetcher):
            result = self.workflow._execute_fetch(self.workspace_path, self.target_papers)
        
        mock_citation_fetcher.process_items.assert_called_once()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['papers_processed'], 2)


if __name__ == '__main__':
    unittest.main()